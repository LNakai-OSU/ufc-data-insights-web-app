"""Additional analytical endpoints - one per "interesting question" idea.
Kept in their own router/module rather than growing main.py further.

Several of these compute a defensible proxy rather than the exact ideal
metric, because the ideal version isn't cleanly derivable from the data
we have. Each such simplification is called out in that endpoint's
docstring - read it before trusting the number at face value.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.db import get_cursor

router = APIRouter()


@router.get("/api/stats/championship-rounds-fade")
def championship_rounds_fade():
    """Rounds 1-3 vs rounds 4-5 output, restricted to fights that actually
    reached round 4+ (i.e. 5-round/main-event fights), so both phases are
    measured across the same set of fights - not "all rounds 1-3 ever"
    vs. a rarer subset."""
    with get_cursor() as cur:
        cur.execute(
            """
            WITH five_round_fights AS (
                SELECT DISTINCT fight_id FROM fight_stats WHERE round >= 4
            )
            SELECT
                CASE WHEN fs.round <= 3 THEN 'early' ELSE 'late' END AS phase,
                round(avg(fs.sig_str_landed), 1) AS avg_sig_str_landed,
                round(100.0 * sum(fs.sig_str_landed) / NULLIF(sum(fs.sig_str_attempted), 0), 1) AS sig_str_accuracy,
                round(avg(fs.td_landed), 2) AS avg_td_landed,
                count(*) AS rounds_counted
            FROM fight_stats fs
            JOIN five_round_fights f5 ON fs.fight_id = f5.fight_id
            WHERE fs.round IS NOT NULL
            GROUP BY phase
            """
        )
        rows = cur.fetchall()
    return {r["phase"]: r for r in rows}


@router.get("/api/stats/first-round-finish-rate")
def first_round_finish_rate():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT wc.name,
                   count(*) FILTER (
                     WHERE fi.round = 1 AND (fi.method ILIKE 'KO/TKO%' OR fi.method ILIKE 'Submission%')
                   ) AS first_round_finishes,
                   count(*) AS total_fights,
                   round(100.0 * count(*) FILTER (
                     WHERE fi.round = 1 AND (fi.method ILIKE 'KO/TKO%' OR fi.method ILIKE 'Submission%')
                   ) / count(*), 1) AS first_round_finish_pct
            FROM fights fi
            JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
            GROUP BY wc.name
            ORDER BY first_round_finish_pct DESC
            """
        )
        return cur.fetchall()


@router.get("/api/stats/reach-advantage")
def reach_advantage():
    """Win rate by reach differential vs. the opponent, in 5 buckets.
    Each decided fight contributes two rows (one per fighter's
    perspective) so the buckets are symmetric by construction."""
    with get_cursor() as cur:
        cur.execute(
            """
            WITH fight_reach AS (
                SELECT (f1.reach_in - f2.reach_in) AS reach_diff, (fi.winner_id = fi.fighter_1_id) AS won
                FROM fights fi
                JOIN fighters f1 ON fi.fighter_1_id = f1.fighter_id
                JOIN fighters f2 ON fi.fighter_2_id = f2.fighter_id
                WHERE fi.result IN ('fighter_1_win', 'fighter_2_win')
                  AND f1.reach_in IS NOT NULL AND f2.reach_in IS NOT NULL
                UNION ALL
                SELECT (f2.reach_in - f1.reach_in), (fi.winner_id = fi.fighter_2_id)
                FROM fights fi
                JOIN fighters f1 ON fi.fighter_1_id = f1.fighter_id
                JOIN fighters f2 ON fi.fighter_2_id = f2.fighter_id
                WHERE fi.result IN ('fighter_1_win', 'fighter_2_win')
                  AND f1.reach_in IS NOT NULL AND f2.reach_in IS NOT NULL
            ),
            bucketed AS (
                SELECT
                    CASE
                        WHEN reach_diff <= -4 THEN '4+ shorter'
                        WHEN reach_diff < -1 THEN '2-3 shorter'
                        WHEN reach_diff <= 1 THEN 'Even'
                        WHEN reach_diff < 4 THEN '2-3 longer'
                        ELSE '4+ longer'
                    END AS reach_bucket,
                    won
                FROM fight_reach
            )
            SELECT reach_bucket,
                   count(*) FILTER (WHERE won) AS wins,
                   count(*) AS total,
                   round(100.0 * count(*) FILTER (WHERE won) / count(*), 1) AS win_pct
            FROM bucketed
            GROUP BY reach_bucket
            ORDER BY CASE reach_bucket
                WHEN '4+ shorter' THEN 1 WHEN '2-3 shorter' THEN 2 WHEN 'Even' THEN 3
                WHEN '2-3 longer' THEN 4 ELSE 5 END
            """
        )
        return cur.fetchall()


@router.get("/api/stats/stance-matchups")
def stance_matchups():
    """Win rate of stance A against stance B specifically (not just each
    stance's overall win rate) - filtered to combinations with at least
    20 fights, since rare pairings (e.g. Sideways vs. Open Stance) are
    too small a sample to mean anything."""
    with get_cursor() as cur:
        cur.execute(
            """
            WITH stance_pairs AS (
                SELECT f1.stance AS my_stance, f2.stance AS opp_stance, (fi.winner_id = fi.fighter_1_id) AS won
                FROM fights fi
                JOIN fighters f1 ON fi.fighter_1_id = f1.fighter_id
                JOIN fighters f2 ON fi.fighter_2_id = f2.fighter_id
                WHERE fi.result IN ('fighter_1_win', 'fighter_2_win')
                  AND f1.stance IS NOT NULL AND f2.stance IS NOT NULL
                UNION ALL
                SELECT f2.stance, f1.stance, (fi.winner_id = fi.fighter_2_id)
                FROM fights fi
                JOIN fighters f1 ON fi.fighter_1_id = f1.fighter_id
                JOIN fighters f2 ON fi.fighter_2_id = f2.fighter_id
                WHERE fi.result IN ('fighter_1_win', 'fighter_2_win')
                  AND f1.stance IS NOT NULL AND f2.stance IS NOT NULL
            )
            SELECT my_stance, opp_stance,
                   count(*) FILTER (WHERE won) AS wins, count(*) AS total,
                   round(100.0 * count(*) FILTER (WHERE won) / count(*), 1) AS win_pct
            FROM stance_pairs
            GROUP BY my_stance, opp_stance
            HAVING count(*) >= 20
            ORDER BY my_stance, opp_stance
            """
        )
        return cur.fetchall()


@router.get("/api/stats/striking-style-win-rate")
def striking_style_win_rate():
    """Fighters bucketed high/low on career strike volume (landed per
    fight) and separately high/low on career accuracy, split at the
    median of fighters with >=5 fights recorded - then each of the 4
    combinations' overall win rate. Answers "does volume or accuracy
    correlate more with winning" without needing a fixed threshold."""
    with get_cursor() as cur:
        cur.execute(
            """
            WITH fighter_stats AS (
                SELECT fighter_id,
                       sum(sig_str_landed)::float / NULLIF(count(DISTINCT fight_id), 0) AS landed_per_fight,
                       100.0 * sum(sig_str_landed) / NULLIF(sum(sig_str_attempted), 0) AS accuracy
                FROM fight_stats
                WHERE fighter_id IS NOT NULL
                GROUP BY fighter_id
                HAVING count(DISTINCT fight_id) >= 5
            ),
            fighter_record AS (
                SELECT f.fighter_id,
                       count(*) FILTER (
                         WHERE (fi.result = 'fighter_1_win' AND fi.fighter_1_id = f.fighter_id)
                            OR (fi.result = 'fighter_2_win' AND fi.fighter_2_id = f.fighter_id)
                       ) AS wins,
                       count(*) AS total
                FROM fighters f
                JOIN fights fi ON f.fighter_id IN (fi.fighter_1_id, fi.fighter_2_id)
                WHERE fi.result IN ('fighter_1_win', 'fighter_2_win')
                GROUP BY f.fighter_id
            ),
            medians AS (
                SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY landed_per_fight) AS median_volume,
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY accuracy) AS median_accuracy
                FROM fighter_stats
            )
            SELECT
                CASE WHEN fs.landed_per_fight >= m.median_volume THEN 'High volume' ELSE 'Low volume' END AS volume_group,
                CASE WHEN fs.accuracy >= m.median_accuracy THEN 'High accuracy' ELSE 'Low accuracy' END AS accuracy_group,
                sum(fr.wins) AS wins, sum(fr.total) AS total,
                round(100.0 * sum(fr.wins) / NULLIF(sum(fr.total), 0), 1) AS win_pct
            FROM fighter_stats fs
            JOIN fighter_record fr ON fs.fighter_id = fr.fighter_id
            CROSS JOIN medians m
            GROUP BY volume_group, accuracy_group
            ORDER BY volume_group, accuracy_group
            """
        )
        return cur.fetchall()


@router.get("/api/stats/age-performance-curve")
def age_performance_curve():
    with get_cursor() as cur:
        cur.execute(
            """
            WITH per_round AS (
                SELECT fs.sig_str_landed, fs.sig_str_attempted,
                       EXTRACT(YEAR FROM age(e.event_date, f.dob)) AS age_years
                FROM fight_stats fs
                JOIN fighters f ON fs.fighter_id = f.fighter_id
                JOIN fights fi ON fs.fight_id = fi.fight_id
                JOIN events e ON fi.event_id = e.event_id
                WHERE f.dob IS NOT NULL AND e.event_date IS NOT NULL
            )
            SELECT
                CASE
                    WHEN age_years < 25 THEN 'Under 25'
                    WHEN age_years < 30 THEN '25-29'
                    WHEN age_years < 35 THEN '30-34'
                    WHEN age_years < 40 THEN '35-39'
                    ELSE '40+'
                END AS age_bucket,
                round(100.0 * sum(sig_str_landed) / NULLIF(sum(sig_str_attempted), 0), 1) AS accuracy,
                count(*) AS rounds_counted
            FROM per_round
            GROUP BY age_bucket
            ORDER BY min(age_years)
            """
        )
        return cur.fetchall()


@router.get("/api/stats/win-streaks")
def win_streaks():
    with get_cursor() as cur:
        cur.execute(
            """
            WITH fighter_fights AS (
                SELECT f.fighter_id,
                       CASE WHEN fi.fighter_1_id = f.fighter_id THEN fi.fighter_2_id ELSE fi.fighter_1_id END AS opponent_id,
                       -- Not "winner_id = f.fighter_id": winner_id can be NULL
                       -- even for a decided fight, when the WINNING side's own
                       -- fighter_id was never resolved (the opponent's ambiguous-
                       -- name cases noted in db/schema.sql). That makes the
                       -- naive comparison NULL (not false) for the *losing*
                       -- fighter here, and `WHERE NOT won` below would then
                       -- silently fail to recognize the loss as a streak-
                       -- breaker. Deriving "won" from `result` instead is
                       -- always true/false, never null, for a decided fight.
                       ((fi.result = 'fighter_1_win' AND fi.fighter_1_id = f.fighter_id)
                        OR (fi.result = 'fighter_2_win' AND fi.fighter_2_id = f.fighter_id)) AS won,
                       ROW_NUMBER() OVER (PARTITION BY f.fighter_id ORDER BY e.event_date DESC) AS rn
                FROM fighters f
                JOIN fights fi ON f.fighter_id IN (fi.fighter_1_id, fi.fighter_2_id)
                JOIN events e ON fi.event_id = e.event_id
                WHERE e.event_date IS NOT NULL AND fi.result IN ('fighter_1_win', 'fighter_2_win')
            ),
            breaks AS (
                SELECT fighter_id, MIN(rn) AS break_rn FROM fighter_fights WHERE NOT won GROUP BY fighter_id
            ),
            streak_fights AS (
                SELECT ff.fighter_id, ff.opponent_id
                FROM fighter_fights ff
                LEFT JOIN breaks b ON b.fighter_id = ff.fighter_id
                WHERE ff.won AND (b.break_rn IS NULL OR ff.rn < b.break_rn)
            )
            SELECT sf.fighter_id, f.first_name, f.last_name, count(*) AS current_streak,
                   array_agg(sf.opponent_id) AS opponent_ids
            FROM streak_fights sf
            JOIN fighters f ON f.fighter_id = sf.fighter_id
            GROUP BY sf.fighter_id, f.first_name, f.last_name
            ORDER BY current_streak DESC
            LIMIT 10
            """
        )
        streaks = cur.fetchall()

        all_opponent_ids = {oid for s in streaks for oid in s["opponent_ids"] if oid}
        opponent_win_pct = {}
        if all_opponent_ids:
            cur.execute(
                """
                SELECT f.fighter_id,
                       round(100.0 * count(*) FILTER (
                         WHERE (fi.result = 'fighter_1_win' AND fi.fighter_1_id = f.fighter_id)
                            OR (fi.result = 'fighter_2_win' AND fi.fighter_2_id = f.fighter_id)
                       ) / NULLIF(count(*), 0), 1) AS win_pct
                FROM fighters f
                JOIN fights fi ON f.fighter_id IN (fi.fighter_1_id, fi.fighter_2_id)
                WHERE f.fighter_id = ANY(%s) AND fi.result IN ('fighter_1_win', 'fighter_2_win')
                GROUP BY f.fighter_id
                """,
                (list(all_opponent_ids),),
            )
            opponent_win_pct = {r["fighter_id"]: float(r["win_pct"]) for r in cur.fetchall() if r["win_pct"] is not None}

    result = []
    for s in streaks:
        opp_pcts = [opponent_win_pct[oid] for oid in s["opponent_ids"] if oid in opponent_win_pct]
        result.append(
            {
                "fighter_id": s["fighter_id"],
                "first_name": s["first_name"],
                "last_name": s["last_name"],
                "current_streak": s["current_streak"],
                "avg_opponent_win_pct": round(sum(opp_pcts) / len(opp_pcts), 1) if opp_pcts else None,
            }
        )
    return result


@router.get("/api/stats/fight-pace-by-year")
def fight_pace_by_year():
    """Significant strikes landed per minute, by year. Approximation:
    every round is treated as a full 5 minutes, since we don't store how
    much of a round elapsed before a finish - this overstates total fight
    time slightly (rounds that ended in a finish get charged a full 5
    minutes), but the resulting trend across years is still meaningful."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT EXTRACT(YEAR FROM e.event_date)::int AS year,
                   round(sum(fs.sig_str_landed)::numeric / NULLIF(count(*) * 5.0, 0), 2) AS sig_strikes_per_minute
            FROM fight_stats fs
            JOIN fights fi ON fs.fight_id = fi.fight_id
            JOIN events e ON fi.event_id = e.event_id
            WHERE e.event_date IS NOT NULL
            GROUP BY year
            ORDER BY year
            """
        )
        return cur.fetchall()


@router.get("/api/stats/split-decision-rate-by-year")
def split_decision_rate_by_year():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT EXTRACT(YEAR FROM e.event_date)::int AS year,
                   count(*) FILTER (WHERE fi.method ILIKE 'Decision - Split%') AS split_decisions,
                   count(*) FILTER (WHERE fi.method ILIKE 'Decision%') AS total_decisions,
                   round(100.0 * count(*) FILTER (WHERE fi.method ILIKE 'Decision - Split%')
                     / NULLIF(count(*) FILTER (WHERE fi.method ILIKE 'Decision%'), 0), 1) AS split_pct
            FROM fights fi
            JOIN events e ON fi.event_id = e.event_id
            WHERE e.event_date IS NOT NULL AND fi.method IS NOT NULL
            GROUP BY year
            HAVING count(*) FILTER (WHERE fi.method ILIKE 'Decision%') > 0
            ORDER BY year
            """
        )
        return cur.fetchall()


@router.get("/api/stats/country-styles")
def country_styles():
    """Submission-win-rate and KO-win-rate by birthplace country, among
    a fighter's own wins (not all their fights) - restricted to
    countries with >=15 fighters so a single prolific fighter can't
    define their whole country's "style"."""
    with get_cursor() as cur:
        cur.execute(
            """
            WITH fighter_finish AS (
                SELECT f.fighter_id, f.birthplace_country,
                       count(*) FILTER (WHERE
                         (fi.result = 'fighter_1_win' AND fi.fighter_1_id = f.fighter_id)
                         OR (fi.result = 'fighter_2_win' AND fi.fighter_2_id = f.fighter_id)
                       ) AS wins,
                       count(*) FILTER (WHERE (
                         (fi.result = 'fighter_1_win' AND fi.fighter_1_id = f.fighter_id)
                         OR (fi.result = 'fighter_2_win' AND fi.fighter_2_id = f.fighter_id)
                       ) AND fi.method ILIKE 'Submission%') AS sub_wins,
                       count(*) FILTER (WHERE (
                         (fi.result = 'fighter_1_win' AND fi.fighter_1_id = f.fighter_id)
                         OR (fi.result = 'fighter_2_win' AND fi.fighter_2_id = f.fighter_id)
                       ) AND fi.method ILIKE 'KO/TKO%') AS ko_wins
                FROM fighters f
                JOIN fights fi ON f.fighter_id IN (fi.fighter_1_id, fi.fighter_2_id)
                WHERE f.birthplace_country IS NOT NULL AND fi.result IN ('fighter_1_win', 'fighter_2_win')
                GROUP BY f.fighter_id, f.birthplace_country
            )
            SELECT birthplace_country AS country,
                   count(DISTINCT fighter_id) AS fighter_count,
                   sum(wins) AS total_wins,
                   round(100.0 * sum(sub_wins) / NULLIF(sum(wins), 0), 1) AS sub_win_pct,
                   round(100.0 * sum(ko_wins) / NULLIF(sum(wins), 0), 1) AS ko_win_pct
            FROM fighter_finish
            GROUP BY birthplace_country
            HAVING count(DISTINCT fighter_id) >= 15
            ORDER BY sub_win_pct DESC
            """
        )
        return cur.fetchall()


_COUNTRY_ALIASES = {
    "United States": ["usa", "united states"],
    "United Kingdom": ["england", "scotland", "wales", "united kingdom", "northern ireland"],
    "Russia": ["russia"],
    "Brazil": ["brazil"],
    "Canada": ["canada"],
    "Australia": ["australia"],
    "Japan": ["japan"],
    "Mexico": ["mexico"],
    "China": ["china"],
}


def _is_home_fight(country: str, location: str) -> bool:
    location_lower = location.lower()
    names = _COUNTRY_ALIASES.get(country, [country.lower()])
    return any(name in location_lower for name in names)


@router.get("/api/stats/home-country-effect")
def home_country_effect():
    """Win rate when a fighter's event location matches their own
    birthplace country vs. everywhere else. Country-name matching is
    done in Python (not SQL) against a small alias table (the same
    USA/UK-constituent-country issue as the map's countryNameMap.js) -
    countries without an explicit alias fall back to a plain substring
    match, which is fine for the vast majority of single-word country
    names but won't be perfect for every possible location phrasing.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT f.birthplace_country, e.location, (fi.result = 'fighter_1_win') AS won
            FROM fights fi
            JOIN fighters f ON f.fighter_id = fi.fighter_1_id
            JOIN events e ON fi.event_id = e.event_id
            WHERE f.birthplace_country IS NOT NULL AND e.location IS NOT NULL
              AND fi.result IN ('fighter_1_win', 'fighter_2_win')
            UNION ALL
            SELECT f.birthplace_country, e.location, (fi.result = 'fighter_2_win')
            FROM fights fi
            JOIN fighters f ON f.fighter_id = fi.fighter_2_id
            JOIN events e ON fi.event_id = e.event_id
            WHERE f.birthplace_country IS NOT NULL AND e.location IS NOT NULL
              AND fi.result IN ('fighter_1_win', 'fighter_2_win')
            """
        )
        rows = cur.fetchall()

    home_wins = home_total = away_wins = away_total = 0
    for r in rows:
        if _is_home_fight(r["birthplace_country"], r["location"]):
            home_total += 1
            home_wins += r["won"]
        else:
            away_total += 1
            away_wins += r["won"]

    return {
        "home": {
            "wins": home_wins,
            "total": home_total,
            "win_pct": round(100 * home_wins / home_total, 1) if home_total else None,
        },
        "away": {
            "wins": away_wins,
            "total": away_total,
            "win_pct": round(100 * away_wins / away_total, 1) if away_total else None,
        },
    }


@router.get("/api/stats/title-insights")
def title_insights():
    """Two things: (1) avg title reign length by division, and (2) finish
    rate for title fights vs. non-title fights.

    Reign length is measured from a champion's first title-fight win to
    their last successful title-fight defense (gaps-and-islands on
    consecutive same-winner title fights per division) - a still-reigning
    champion who hasn't had a title defense yet shows as a 0-day reign,
    since there's no later date to measure to. That's a real
    undercount for currently-active, undefended title runs, not a bug.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            WITH title_fights AS (
                SELECT wc.weight_class_id, wc.name AS weight_class, e.event_date, fi.winner_id
                FROM fights fi
                JOIN events e ON fi.event_id = e.event_id
                JOIN weight_classes wc ON fi.weight_class_id = wc.weight_class_id
                WHERE fi.is_title_bout = true AND fi.is_interim_title = false
                  AND fi.result IN ('fighter_1_win', 'fighter_2_win') AND e.event_date IS NOT NULL
            ),
            with_change AS (
                SELECT *,
                    CASE WHEN winner_id = LAG(winner_id) OVER (PARTITION BY weight_class_id ORDER BY event_date)
                         THEN 0 ELSE 1 END AS is_new_reign
                FROM title_fights
            ),
            grouped AS (
                SELECT *, SUM(is_new_reign) OVER (PARTITION BY weight_class_id ORDER BY event_date) AS reign_group
                FROM with_change
            ),
            reigns AS (
                SELECT weight_class, MIN(event_date) AS reign_start, MAX(event_date) AS last_defense
                FROM grouped
                GROUP BY weight_class_id, weight_class, winner_id, reign_group
            )
            SELECT weight_class, round(avg(last_defense - reign_start)) AS avg_reign_days, count(*) AS reigns_counted
            FROM reigns
            GROUP BY weight_class
            ORDER BY avg_reign_days DESC NULLS LAST
            """
        )
        reign_lengths = cur.fetchall()

        cur.execute(
            """
            SELECT is_title_bout,
                   count(*) FILTER (WHERE method ILIKE 'KO/TKO%' OR method ILIKE 'Submission%') AS finishes,
                   count(*) AS total,
                   round(100.0 * count(*) FILTER (WHERE method ILIKE 'KO/TKO%' OR method ILIKE 'Submission%') / count(*), 1) AS finish_pct
            FROM fights
            WHERE method IS NOT NULL
            GROUP BY is_title_bout
            """
        )
        finish_rates = cur.fetchall()

    return {"reign_lengths": reign_lengths, "finish_rates": finish_rates}


@router.get("/api/stats/fastest-finishes")
def fastest_finishes():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT fi.fight_id, e.name AS event_name, e.event_date,
                   fi.fighter_1_id, fi.fighter_1_name_raw, fi.fighter_2_id, fi.fighter_2_name_raw,
                   fi.winner_id, fi.method, fi.round, fi.time_seconds
            FROM fights fi
            JOIN events e ON fi.event_id = e.event_id
            WHERE fi.round = 1 AND fi.time_seconds IS NOT NULL
              AND (fi.method ILIKE 'KO/TKO%' OR fi.method ILIKE 'Submission%')
            ORDER BY fi.time_seconds ASC
            LIMIT 10
            """
        )
        return cur.fetchall()


@router.get("/api/stats/rivalries")
def rivalries():
    with get_cursor() as cur:
        cur.execute(
            """
            WITH pairs AS (
                SELECT LEAST(fighter_1_id, fighter_2_id) AS fa, GREATEST(fighter_1_id, fighter_2_id) AS fb,
                       count(*) AS fight_count
                FROM fights
                WHERE fighter_1_id IS NOT NULL AND fighter_2_id IS NOT NULL
                GROUP BY fa, fb
                HAVING count(*) >= 2
            )
            SELECT p.fight_count,
                   fa.fighter_id AS a_id, fa.first_name AS a_first, fa.last_name AS a_last,
                   fb.fighter_id AS b_id, fb.first_name AS b_first, fb.last_name AS b_last
            FROM pairs p
            JOIN fighters fa ON fa.fighter_id = p.fa
            JOIN fighters fb ON fb.fighter_id = p.fb
            ORDER BY p.fight_count DESC
            LIMIT 15
            """
        )
        return cur.fetchall()
