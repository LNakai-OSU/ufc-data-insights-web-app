"""Download the pre-scraped UFC stats CSVs into data/raw/.

Source: https://github.com/Greco1899/scrape_ufc_stats (GPL-3.0), an
open-source project that scrapes ufcstats.com and republishes the
result as CSVs, refreshed daily. We use this instead of scraping
ufcstats.com ourselves: it's already-consented-to republished data,
avoids ufcstats.com's bot-challenge gate, and covers more ground
(round-by-round strike/grapple stats included) than a first-pass
scraper would have.

Usage:
    python fetch_data.py
"""
from __future__ import annotations

from pathlib import Path

import requests

REPO_RAW_BASE = "https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main"
FILES = [
    "ufc_event_details.csv",
    "ufc_fight_details.csv",
    "ufc_fight_results.csv",
    "ufc_fight_stats.csv",
    "ufc_fighter_details.csv",
    "ufc_fighter_tott.csv",
]
OUTPUT_DIR = Path("data/raw")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        url = f"{REPO_RAW_BASE}/{filename}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        out_path = OUTPUT_DIR / filename
        out_path.write_bytes(response.content)
        print(f"{filename}: {len(response.content):,} bytes -> {out_path}")


if __name__ == "__main__":
    main()
