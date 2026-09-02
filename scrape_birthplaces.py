"""Backfill fighters.birthplace_raw/birthplace_country from UFC.com.

ufcstats.com (our primary data source) has no nationality/birthplace field
at all. UFC.com's athlete pages do, under a "Place of Birth" bio field, so
this scrapes those pages to backfill the two columns added in
db/migrations/001_add_fighter_birthplace.sql.

Respects UFC.com's robots.txt: /athlete/<slug> pages are allowed, but all
user agents get a mandatory 15-second crawl-delay - so a full run over
~4,600 fighters takes about a day of wall-clock time. Fully resumable and
safe to interrupt: only fighters with birthplace_country IS NULL are
selected each run, and each fighter's result is committed to the database
immediately, not batched at the end.

URL slugs are guessed (firstname-lastname, lowercased/hyphenated, accents
stripped) since we have no direct mapping to UFC.com's URLs - see
birthplace_scrape/parsing.py:candidate_slugs. For each fighter we try the
primary guess, then a suffix-stripped fallback (UFC.com sometimes omits a
Jr./Sr./II/III/IV that ufcstats.com includes) before giving up. This
can't guess UFC.com's "-2" disambiguation suffix for fighters who share a
name with someone else already on the site, or recover fighters whose
UFC.com slug differs for other reasons - every failure is logged to
data/birthplace_scrape_failures.csv for manual review rather than
silently skipped.

Two known, distinct failure modes that retrying won't fix:
- Some UFC.com athlete pages return HTTP 403 - a real Drupal-level access
  restriction on that specific content (confirmed via response headers),
  not a bot-block or rate limit. No amount of pacing/retrying changes it.
- Some fighters simply have no resolvable UFC.com slug under any guess
  tried here. Resolving these further would mean querying UFC.com's own
  /search - which robots.txt explicitly disallows, so we don't.

Usage:
    python scrape_birthplaces.py [--limit N]
"""
from __future__ import annotations

import argparse
import csv

import psycopg2
import psycopg2.extras

from birthplace_scrape.fetch import fetch_athlete_page
from birthplace_scrape.parsing import candidate_slugs, parse_birthplace, parse_country

DSN = "postgresql:///ufc_stats"
FAILURES_PATH = "data/birthplace_scrape_failures.csv"


def scrape_one(first_name: str, last_name: str) -> tuple[str | None, str | None, str]:
    """Tries each candidate slug in order. Returns (birthplace_raw,
    country, reason) - the first two are None on failure, in which case
    `reason` explains why."""
    last_error = "no matching UFC.com profile found"

    for slug in candidate_slugs(first_name, last_name):
        try:
            html = fetch_athlete_page(slug)
        except Exception as e:
            last_error = f"fetch error ({slug}): {e}"
            continue

        if html is None:
            continue  # this candidate slug didn't resolve - try the next one

        birthplace_raw = parse_birthplace(html)
        if birthplace_raw is None:
            return None, None, f"profile page found ({slug}) but no Place of Birth field on it"

        return birthplace_raw, parse_country(birthplace_raw), ""

    return None, None, last_error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    conn = psycopg2.connect(DSN)
    conn.autocommit = True

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT fighter_id, first_name, last_name
            FROM fighters
            WHERE birthplace_country IS NULL
            ORDER BY fighter_id
            """
        )
        fighters = cur.fetchall()

    if args.limit:
        fighters = fighters[: args.limit]

    print(f"{len(fighters)} fighters to process")

    failures = []
    succeeded = 0

    with conn.cursor() as cur:
        for i, fighter in enumerate(fighters, 1):
            birthplace_raw, country, reason = scrape_one(fighter["first_name"], fighter["last_name"])

            if birthplace_raw is None:
                tried = "/".join(candidate_slugs(fighter["first_name"], fighter["last_name"]))
                failures.append((fighter["fighter_id"], fighter["first_name"], fighter["last_name"], tried, reason))
                continue

            cur.execute(
                "UPDATE fighters SET birthplace_raw = %s, birthplace_country = %s WHERE fighter_id = %s",
                (birthplace_raw, country, fighter["fighter_id"]),
            )
            succeeded += 1

            if i % 50 == 0 or i == len(fighters):
                print(f"  {i}/{len(fighters)} processed ({succeeded} succeeded, {len(failures)} failed)")

    conn.close()

    if failures:
        with open(FAILURES_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["fighter_id", "first_name", "last_name", "tried_slugs", "reason"])
            writer.writerows(failures)
        print(f"{len(failures)} failures logged to {FAILURES_PATH}")

    print(f"Done: {succeeded} succeeded, {len(failures)} failed")


if __name__ == "__main__":
    main()
