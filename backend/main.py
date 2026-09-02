"""FastAPI backend for the UFC stats dashboard.

Run from the project root:
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.db import get_cursor
from backend.insights import router as insights_router
from chat.agent import ask as chat_ask

app = FastAPI(title="UFC Stats API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights_router)


@app.get("/api/overview")
def overview():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
              (SELECT count(*) FROM fighters) AS fighters,
              (SELECT count(*) FROM fights) AS fights,
              (SELECT count(*) FROM events) AS events,
              (SELECT count(*) FROM weight_classes) AS weight_classes
            """
        )
        return cur.fetchone()


@app.get("/api/stats/stance-win-rate")
def stance_win_rate():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT f.stance,
                   -- Not "winner_id = f.fighter_id": winner_id is NULL for a
                   -- decided fight if the WINNING side's own fighter_id was
                   -- never resolved (ambiguous-name cases). Deriving "won"
                   -- from `result` instead is always true/false, never null.
                   count(*) FILTER (WHERE
                     (fi.result = 'fighter_1_win' AND fi.fighter_1_id = f.fighter_id)
                     OR (fi.result = 'fighter_2_win' AND fi.fighter_2_id = f.fighter_id)
                   ) AS wins,
                   count(*) AS total_fights,
                   round(
                     100.0 * count(*) FILTER (WHERE
                       (fi.result = 'fighter_1_win' AND fi.fighter_1_id = f.fighter_id)
                       OR (fi.result = 'fighter_2_win' AND fi.fighter_2_id = f.fighter_id)
                     ) / count(*), 1
                   ) AS win_pct
            FROM fighters f
            JOIN fights fi ON f.fighter_id IN (fi.fighter_1_id, fi.fighter_2_id)
            WHERE f.stance IS NOT NULL
              AND fi.result IN ('fighter_1_win', 'fighter_2_win')
            GROUP BY f.stance
            ORDER BY win_pct DESC
            """
        )
        return cur.fetchall()


@app.get("/api/stats/weight-classes")
def weight_class_fight_counts():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT wc.name, count(*) AS fight_count
            FROM fights fi
            JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
            GROUP BY wc.name
            ORDER BY fight_count DESC
            """
        )
        return cur.fetchall()


@app.get("/api/stats/methods")
def method_breakdown():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
              CASE
                WHEN method ILIKE 'KO/TKO%' THEN 'KO/TKO'
                WHEN method ILIKE 'Submission%' THEN 'Submission'
                WHEN method ILIKE 'Decision%' THEN 'Decision'
                ELSE 'Other'
              END AS method_category,
              count(*) AS fight_count
            FROM fights
            WHERE method IS NOT NULL
            GROUP BY method_category
            ORDER BY fight_count DESC
            """
        )
        return cur.fetchall()


@app.get("/api/stats/fights-by-year")
def fights_by_year():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT EXTRACT(YEAR FROM e.event_date)::int AS year, count(*) AS fight_count
            FROM fights fi
            JOIN events e ON fi.event_id = e.event_id
            WHERE e.event_date IS NOT NULL
            GROUP BY year
            ORDER BY year
            """
        )
        return cur.fetchall()


@app.get("/api/stats/finish-rate-by-year")
def finish_rate_by_year():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT EXTRACT(YEAR FROM e.event_date)::int AS year,
                   count(*) AS total_fights,
                   count(*) FILTER (
                     WHERE fi.method ILIKE 'KO/TKO%' OR fi.method ILIKE 'Submission%'
                   ) AS finishes,
                   round(
                     100.0 * count(*) FILTER (
                       WHERE fi.method ILIKE 'KO/TKO%' OR fi.method ILIKE 'Submission%'
                     ) / count(*), 1
                   ) AS finish_pct
            FROM fights fi
            JOIN events e ON fi.event_id = e.event_id
            WHERE e.event_date IS NOT NULL AND fi.method IS NOT NULL
            GROUP BY year
            ORDER BY year
            """
        )
        return cur.fetchall()


# Each query takes named params (weight_class, limit); weight_class is
# nullable and the "%(weight_class)s IS NULL OR ..." clause makes the same
# query work filtered or unfiltered, rather than maintaining two variants
# per metric.
_LEADERBOARD_QUERIES = {
    "sig_strikes": """
        SELECT f.fighter_id, f.first_name, f.last_name,
               sum(fs.sig_str_landed) AS value
        FROM fight_stats fs
        JOIN fighters f ON fs.fighter_id = f.fighter_id
        JOIN fights fi ON fs.fight_id = fi.fight_id
        LEFT JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
        WHERE %(weight_class)s IS NULL OR wc.name = %(weight_class)s
        GROUP BY f.fighter_id, f.first_name, f.last_name
        ORDER BY value DESC NULLS LAST
        LIMIT %(limit)s
    """,
    # Minimum-attempts floor so a fighter with e.g. 3 of 3 significant
    # strikes in one round doesn't outrank fighters with hundreds of fights
    # worth of attempts.
    "accuracy": """
        SELECT f.fighter_id, f.first_name, f.last_name,
               round(100.0 * sum(fs.sig_str_landed) / sum(fs.sig_str_attempted), 1) AS value
        FROM fight_stats fs
        JOIN fighters f ON fs.fighter_id = f.fighter_id
        JOIN fights fi ON fs.fight_id = fi.fight_id
        LEFT JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
        WHERE %(weight_class)s IS NULL OR wc.name = %(weight_class)s
        GROUP BY f.fighter_id, f.first_name, f.last_name
        HAVING sum(fs.sig_str_attempted) >= 150
        ORDER BY value DESC NULLS LAST
        LIMIT %(limit)s
    """,
    "ko_wins": """
        SELECT f.fighter_id, f.first_name, f.last_name, count(*) AS value
        FROM fighters f
        JOIN fights fi ON fi.winner_id = f.fighter_id
        LEFT JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
        WHERE fi.method ILIKE 'KO/TKO%%'
          AND (%(weight_class)s IS NULL OR wc.name = %(weight_class)s)
        GROUP BY f.fighter_id, f.first_name, f.last_name
        ORDER BY value DESC NULLS LAST
        LIMIT %(limit)s
    """,
    "sub_wins": """
        SELECT f.fighter_id, f.first_name, f.last_name, count(*) AS value
        FROM fighters f
        JOIN fights fi ON fi.winner_id = f.fighter_id
        LEFT JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
        WHERE fi.method ILIKE 'Submission%%'
          AND (%(weight_class)s IS NULL OR wc.name = %(weight_class)s)
        GROUP BY f.fighter_id, f.first_name, f.last_name
        ORDER BY value DESC NULLS LAST
        LIMIT %(limit)s
    """,
    # "Grinder" metrics - high career control time or takedown volume,
    # independent of whether those fighters actually finish fights.
    "control_time": """
        SELECT f.fighter_id, f.first_name, f.last_name,
               sum(fs.control_seconds) AS value
        FROM fight_stats fs
        JOIN fighters f ON fs.fighter_id = f.fighter_id
        JOIN fights fi ON fs.fight_id = fi.fight_id
        LEFT JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
        WHERE %(weight_class)s IS NULL OR wc.name = %(weight_class)s
        GROUP BY f.fighter_id, f.first_name, f.last_name
        ORDER BY value DESC NULLS LAST
        LIMIT %(limit)s
    """,
    "takedowns": """
        SELECT f.fighter_id, f.first_name, f.last_name,
               sum(fs.td_landed) AS value
        FROM fight_stats fs
        JOIN fighters f ON fs.fighter_id = f.fighter_id
        JOIN fights fi ON fs.fight_id = fi.fight_id
        LEFT JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
        WHERE %(weight_class)s IS NULL OR wc.name = %(weight_class)s
        GROUP BY f.fighter_id, f.first_name, f.last_name
        ORDER BY value DESC NULLS LAST
        LIMIT %(limit)s
    """,
}


@app.get("/api/stats/leaderboard")
def leaderboard(
    metric: str = Query(..., pattern="^(sig_strikes|accuracy|ko_wins|sub_wins|control_time|takedowns)$"),
    weight_class: Optional[str] = Query(None),
    limit: int = Query(10, le=50),
):
    with get_cursor() as cur:
        cur.execute(_LEADERBOARD_QUERIES[metric], {"weight_class": weight_class, "limit": limit})
        return cur.fetchall()


@app.get("/api/stats/active-years")
def active_years():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT EXTRACT(YEAR FROM min(event_date))::int AS min_year,
                   EXTRACT(YEAR FROM max(event_date))::int AS max_year
            FROM events
            WHERE event_date IS NOT NULL
            """
        )
        return cur.fetchone()


@app.get("/api/stats/fighters-by-country")
def fighters_by_country(year: int = Query(..., ge=1993, le=2100)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT f.birthplace_country AS country, count(DISTINCT f.fighter_id) AS fighter_count
            FROM fighters f
            JOIN fights fi ON f.fighter_id IN (fi.fighter_1_id, fi.fighter_2_id)
            JOIN events e ON fi.event_id = e.event_id
            WHERE f.birthplace_country IS NOT NULL
              AND EXTRACT(YEAR FROM e.event_date) = %s
            GROUP BY f.birthplace_country
            ORDER BY fighter_count DESC
            """,
            (year,),
        )
        return cur.fetchall()


@app.get("/api/stats/fighters-by-country/{country}")
def fighters_from_country(country: str, year: int = Query(..., ge=1993, le=2100)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT f.fighter_id, f.first_name, f.last_name, f.nickname, f.stance,
                   count(*) AS fights_that_year
            FROM fighters f
            JOIN fights fi ON f.fighter_id IN (fi.fighter_1_id, fi.fighter_2_id)
            JOIN events e ON fi.event_id = e.event_id
            WHERE f.birthplace_country = %s
              AND EXTRACT(YEAR FROM e.event_date) = %s
            GROUP BY f.fighter_id, f.first_name, f.last_name, f.nickname, f.stance
            ORDER BY f.last_name, f.first_name
            """,
            (country, year),
        )
        return cur.fetchall()


@app.get("/api/stats/division-leaderboard")
def division_leaderboard(
    weight_class: str,
    year: int = Query(..., ge=1993, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
):
    conditions = ["wc.name = %(weight_class)s", "EXTRACT(YEAR FROM e.event_date) = %(year)s"]
    params = {"weight_class": weight_class, "year": year}
    if month is not None:
        conditions.append("EXTRACT(MONTH FROM e.event_date) = %(month)s")
        params["month"] = month

    with get_cursor() as cur:
        cur.execute(
            f"""
            SELECT f.fighter_id, f.first_name, f.last_name, f.nickname,
                   count(*) AS fights_in_period,
                   count(*) FILTER (WHERE
                     (fi.result = 'fighter_1_win' AND fi.fighter_1_id = f.fighter_id)
                     OR (fi.result = 'fighter_2_win' AND fi.fighter_2_id = f.fighter_id)
                   ) AS wins_in_period
            FROM fighters f
            JOIN fights fi ON f.fighter_id IN (fi.fighter_1_id, fi.fighter_2_id)
            JOIN events e ON fi.event_id = e.event_id
            JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
            WHERE {' AND '.join(conditions)}
            GROUP BY f.fighter_id, f.first_name, f.last_name, f.nickname
            ORDER BY wins_in_period DESC, fights_in_period DESC
            """,
            params,
        )
        return cur.fetchall()


@app.get("/api/stats/title-history")
def title_history(weight_class: str):
    # Returns every title fight in the division in order, which reads as
    # a championship lineage (each winner becomes/retains champion) - we
    # don't try to compute an explicit "champion as of date X" because
    # vacated/stripped titles aren't reliably distinguishable from the
    # fight-level data alone.
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT fi.fight_id, e.event_date, e.name AS event_name,
                   fi.fighter_1_id, fi.fighter_1_name_raw,
                   fi.fighter_2_id, fi.fighter_2_name_raw,
                   fi.winner_id, fi.result, fi.method, fi.is_interim_title
            FROM fights fi
            JOIN events e ON fi.event_id = e.event_id
            JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
            WHERE wc.name = %s AND fi.is_title_bout = true
            ORDER BY e.event_date ASC NULLS LAST
            """,
            (weight_class,),
        )
        return cur.fetchall()


@app.get("/api/stats/division-rankings")
def division_rankings(weight_class: str):
    """The official UFC rankings (champion + ranked contenders) for a
    division, from the current_rankings table (see
    db/migrations/002_add_current_rankings.sql and scrape_rankings.py).
    This is a live current-only snapshot - UFC.com doesn't publish a
    historical rankings archive, so there's no "as of year X" here; the
    response includes when the snapshot was last scraped.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT fighter_id, fighter_name_raw, rank, scraped_at
            FROM current_rankings
            JOIN weight_classes USING (weight_class_id)
            WHERE weight_classes.name = %s
            ORDER BY rank
            """,
            (weight_class,),
        )
        rows = cur.fetchall()

    if not rows:
        return {"champion": None, "contenders": [], "scraped_at": None}

    champion_row = rows[0] if rows[0]["rank"] == 0 else None
    champion = (
        {"fighter_id": champion_row["fighter_id"], "name": champion_row["fighter_name_raw"]}
        if champion_row
        else None
    )
    contenders = [
        {"fighter_id": r["fighter_id"], "name": r["fighter_name_raw"], "rank": r["rank"]}
        for r in rows
        if r["rank"] != 0
    ]
    return {"champion": champion, "contenders": contenders, "scraped_at": rows[0]["scraped_at"]}


@app.get("/api/fighters")
def search_fighters(q: str = Query("", max_length=100), limit: int = Query(20, le=100)):
    if not q.strip():
        return []
    with get_cursor() as cur:
        pattern = f"%{q.strip()}%"
        cur.execute(
            """
            SELECT fighter_id, first_name, last_name, nickname, stance,
                   (SELECT count(*) FROM fights WHERE winner_id = f.fighter_id) AS wins
            FROM fighters f
            WHERE (first_name || ' ' || last_name) ILIKE %s
               OR nickname ILIKE %s
            ORDER BY last_name, first_name
            LIMIT %s
            """,
            (pattern, pattern, limit),
        )
        return cur.fetchall()


@app.get("/api/fighters/{fighter_id}")
def fighter_detail(fighter_id: str):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT fighter_id, first_name, last_name, nickname,
                   height_in, weight_lbs, reach_in, stance, dob
            FROM fighters WHERE fighter_id = %s
            """,
            (fighter_id,),
        )
        fighter = cur.fetchone()
        if fighter is None:
            raise HTTPException(status_code=404, detail="Fighter not found")

        cur.execute(
            """
            SELECT fi.fight_id, fi.event_id, e.name AS event_name, e.event_date,
                   CASE WHEN fi.fighter_1_id = %(fid)s
                        THEN fi.fighter_2_name_raw ELSE fi.fighter_1_name_raw END AS opponent_name,
                   CASE WHEN fi.fighter_1_id = %(fid)s
                        THEN fi.fighter_2_id ELSE fi.fighter_1_id END AS opponent_id,
                   CASE
                     WHEN fi.result = 'draw' THEN 'draw'
                     WHEN fi.result = 'no_contest' THEN 'no_contest'
                     WHEN fi.winner_id = %(fid)s THEN 'win'
                     ELSE 'loss'
                   END AS outcome,
                   fi.method, fi.round, wc.name AS weight_class
            FROM fights fi
            JOIN events e ON fi.event_id = e.event_id
            LEFT JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
            WHERE fi.fighter_1_id = %(fid)s OR fi.fighter_2_id = %(fid)s
            ORDER BY e.event_date DESC NULLS LAST
            """,
            {"fid": fighter_id},
        )
        fighter["fights"] = cur.fetchall()
        return fighter


@app.get("/api/events/{event_id}")
def event_detail(event_id: str):
    with get_cursor() as cur:
        cur.execute(
            "SELECT event_id, name, event_date, location FROM events WHERE event_id = %s",
            (event_id,),
        )
        event = cur.fetchone()
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")

        # No true fight-card order is stored (ufcstats.com's original
        # top-to-bottom card order wasn't captured), so ordering title
        # fights first is a reasonable approximation, not the real
        # broadcast order.
        cur.execute(
            """
            SELECT fi.fight_id,
                   fi.fighter_1_id, fi.fighter_1_name_raw,
                   fi.fighter_2_id, fi.fighter_2_name_raw,
                   fi.result, fi.winner_id, fi.is_title_bout,
                   fi.method, fi.round, wc.name AS weight_class
            FROM fights fi
            LEFT JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
            WHERE fi.event_id = %s
            ORDER BY fi.is_title_bout DESC, fi.fight_id
            """,
            (event_id,),
        )
        event["fights"] = cur.fetchall()
        return event


class ChatRequest(BaseModel):
    question: str


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")
    try:
        return chat_ask(req.question)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Chat assistant unavailable: {e}",
        )
