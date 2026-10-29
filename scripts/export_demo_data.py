"""Export the dashboard's API responses as static JSON for the GitHub Pages demo.

Run from the project root with Postgres up and the DB loaded:
    venv/bin/python scripts/export_demo_data.py

Calls the real FastAPI app in-process, so the snapshot is exactly what the live
backend returns. Files land in frontend/public/demo-data/, named by
demoKey() - keep it identical to demoKey() in frontend/src/api.js.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.db import get_cursor  # noqa: E402
from backend.main import app  # noqa: E402

OUT = ROOT / "frontend" / "public" / "demo-data"
MONTHS = range(1, 13)
METRICS = ["sig_strikes", "accuracy", "ko_wins", "sub_wins", "control_time", "takedowns"]
NO_PARAM = [
    "/api/overview", "/api/stats/stance-win-rate", "/api/stats/weight-classes",
    "/api/stats/methods", "/api/stats/fights-by-year", "/api/stats/finish-rate-by-year",
    "/api/stats/active-years", "/api/stats/championship-rounds-fade",
    "/api/stats/first-round-finish-rate", "/api/stats/reach-advantage",
    "/api/stats/stance-matchups", "/api/stats/striking-style-win-rate",
    "/api/stats/age-performance-curve", "/api/stats/win-streaks",
    "/api/stats/fight-pace-by-year", "/api/stats/split-decision-rate-by-year",
    "/api/stats/country-styles", "/api/stats/home-country-effect",
    "/api/stats/title-insights", "/api/stats/fastest-finishes", "/api/stats/rivalries",
]


def demo_key(url: str) -> str:
    """Decoded path plus sorted, decoded query. Mirrors demoKey() in api.js."""
    parts = urlsplit(url)
    query = "&".join(f"{k}={v}" for k, v in sorted(parse_qsl(parts.query)))
    return unquote(parts.path) + ("?" + query if query else "")


client = TestClient(app)
written = 0
failed: list[str] = []
core: dict[str, object] = {}


def fetch(url: str) -> object | None:
    global written
    res = client.get(url)
    if res.status_code != 200:
        failed.append(f"{res.status_code} {url}")
        return None
    written += 1
    return res.json()


def save(url: str) -> object | None:
    """Fetch into the core snapshot. Empty lists are omitted; the frontend
    treats a missing core key as []."""
    data = fetch(url)
    if data != [] and data is not None:
        core[demo_key(url)] = data
    return data


def write(name: str, data: object) -> None:
    (OUT / name).write_text(json.dumps(data, separators=(",", ":"), default=str))


def q(url_path: str, **params) -> str:
    return url_path + "?" + urlencode(params)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for path in NO_PARAM:
        save(path)

    classes = [r["name"] for r in client.get("/api/stats/weight-classes").json()]
    years = client.get("/api/stats/active-years").json()
    year_range = range(years["min_year"], years["max_year"] + 1)

    for metric in METRICS:
        save(q("/api/stats/leaderboard", metric=metric, limit=10))
        for wc in classes:
            save(q("/api/stats/leaderboard", metric=metric, weight_class=wc, limit=10))

    for wc in classes:
        save(q("/api/stats/title-history", weight_class=wc))
        save(q("/api/stats/division-rankings", weight_class=wc))
        for y in year_range:
            save(q("/api/stats/division-leaderboard", weight_class=wc, year=y))
            for m in MONTHS:
                save(q("/api/stats/division-leaderboard", weight_class=wc, year=y, month=m))

    for y in year_range:
        countries = save(q("/api/stats/fighters-by-country", year=y)) or []
        for c in countries:
            save(f"/api/stats/fighters-by-country/{quote(c['country'], safe='')}?year={y}")

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT f.fighter_id, f.first_name, f.last_name, f.nickname, f.stance,
                   count(fi.fight_id) AS wins
            FROM fighters f
            LEFT JOIN fights fi ON fi.winner_id = f.fighter_id
            GROUP BY f.fighter_id ORDER BY f.last_name, f.first_name
            """
        )
        fighters = cur.fetchall()
        cur.execute("SELECT event_id FROM events")
        events = [r["event_id"] for r in cur.fetchall()]

    write("core.json", core)
    write("fighters-index.json", fighters)

    # Detail pages are sharded by the first character of the id.
    for kind, ids, route in (
        ("fighters", [f["fighter_id"] for f in fighters], "/api/fighters/"),
        ("events", events, "/api/events/"),
    ):
        shards: dict[str, dict[str, object]] = {}
        for i in ids:
            data = fetch(route + quote(i, safe=""))
            if data is not None:
                shards.setdefault(i[0], {})[i] = data
        for ch, body in shards.items():
            write(f"{kind}-{ch}.json", body)

    size = sum(p.stat().st_size for p in OUT.iterdir()) / 1e6
    print(sorted((p.stat().st_size // 1000, p.name) for p in OUT.iterdir())[-6:])
    print(f"wrote {written} files, {size:.1f} MB; {len(failed)} failed")
    for line in failed[:20]:
        print("  ", line)


if __name__ == "__main__":
    main()
