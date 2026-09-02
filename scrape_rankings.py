"""Scrape the official UFC rankings (champion + top-15 contenders per
division) from https://www.ufc.com/rankings into the current_rankings
table (see db/migrations/002_add_current_rankings.sql).

This is fundamentally different from scrape_birthplaces.py: UFC.com
doesn't publish a historical rankings archive, only the current week's
snapshot - there's no "rankings as of year X" to scrape even in
principle. So this script is meant to be re-run periodically to refresh
a single current snapshot (it truncates and reloads the table each run),
not to backfill history.

Also unlike the per-fighter birthplace scrape, this is ONE page covering
every division, so there's no crawl-delay pacing concern - a single
request is all robots.txt's 15s-between-requests rule would ever apply
to anyway.

The rankings page actually contains two parallel ranking systems in one
document: a div block titled "All Rankings" (the traditional media-panel
rankings - what people mean by "UFC rankings") and a separate "All Meta
Rankings" block (a different, UFC.com-specific secondary system). Only
the "All Rankings" block is scraped here.

Fighters are matched to our `fighters` table by name (the rankings page
doesn't expose ufcstats.com IDs) - left NULL, with the raw name kept,
when a name has no match or an ambiguous (2+) match, same as elsewhere
in this project.

Usage:
    python scrape_rankings.py
"""
from __future__ import annotations

import re
import unicodedata

import psycopg2
import psycopg2.extras
import requests
from bs4 import BeautifulSoup

DSN = "postgresql:///ufc_stats"


# Letters NFKD does not decompose to their ASCII look-alike (they're not
# diacritic-on-base-letter, like é/e - they're distinct letterforms), so
# accent-stripping alone silently drops them (e.g. "Błachowicz" ->
# "Bachowicz", missing the L) rather than substituting the right letter.
_NON_DECOMPOSING_LETTERS = str.maketrans({
    "ł": "l", "Ł": "L",
    "đ": "d", "Đ": "D",
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "’": "'",
})


def normalize_name(name: str) -> str:
    """UFC.com's rankings page uses full Unicode (curly apostrophes,
    accented letters: "Jiří Procházka") while our fighters table has
    plain ASCII from ufcstats.com ("Jiri Prochazka") - strip accents and
    normalize apostrophe/letter style so the two sides can actually
    match."""
    name = name.translate(_NON_DECOMPOSING_LETTERS)
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_name).strip()


RANKINGS_URL = "https://www.ufc.com/rankings"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# UFC.com's Pound-for-Pound rankings span every weight class, not a real
# division - our weight_classes table has no matching row, so these two
# are intentionally not scraped. The header's actual text runs straight
# into a nested "Top Rank" span with no separating space in the markup
# (e.g. "Men's Pound-for-PoundTop Rank"), hence startswith rather than ==.
SKIP_DIVISION_PREFIXES = ("Men's Pound-for-Pound", "Women's Pound-for-Pound")


def fetch_all_rankings_section(html: str) -> str:
    """Isolates the "All Rankings" block from the "All Meta Rankings"
    block that follows it in the same document."""
    start = html.find("All Rankings")
    end = html.find("All Meta Rankings")
    if start == -1 or end == -1:
        raise ValueError("Could not find All Rankings / All Meta Rankings section markers")
    return html[start:end]


def parse_rankings(section_html: str) -> list[dict]:
    """Returns a list of {weight_class, rank, fighter_name} dicts,
    rank=0 for the champion."""
    soup = BeautifulSoup(section_html, "lxml")
    results = []

    for group in soup.find_all("div", class_="view-grouping"):
        header = group.find("div", class_="view-grouping-header")
        if header is None:
            continue
        division = header.get_text(strip=True)
        if division.startswith(SKIP_DIVISION_PREFIXES):
            continue

        champion_block = group.find("div", class_="rankings--athlete--champion")
        if champion_block:
            champ_link = champion_block.find("h5")
            if champ_link and champ_link.find("a"):
                results.append(
                    {"weight_class": division, "rank": 0, "fighter_name": champ_link.get_text(strip=True)}
                )

        for row in group.find_all("tr"):
            rank_cell = row.find("td", class_="views-field-weight-class-rank")
            name_cell = row.find("td", class_="views-field-title")
            if rank_cell is None or name_cell is None:
                continue
            rank_text = rank_cell.get_text(strip=True)
            if not rank_text.isdigit():
                continue
            link = name_cell.find("a")
            if link is None:
                continue
            results.append(
                {"weight_class": division, "rank": int(rank_text), "fighter_name": link.get_text(strip=True)}
            )

    return results


def main() -> None:
    response = requests.get(RANKINGS_URL, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()

    section = fetch_all_rankings_section(response.text)
    rankings = parse_rankings(section)
    print(f"Parsed {len(rankings)} ranking entries across {len({r['weight_class'] for r in rankings})} divisions")

    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT weight_class_id, name FROM weight_classes")
        weight_class_ids = {row["name"]: row["weight_class_id"] for row in cur.fetchall()}

        cur.execute("SELECT fighter_id, first_name, last_name, nickname FROM fighters")
        name_to_ids: dict[str, list[str]] = {}
        for row in cur.fetchall():
            full_name = normalize_name(f"{row['first_name']} {row['last_name']}")
            name_to_ids.setdefault(full_name, []).append(row["fighter_id"])
            # UFC.com sometimes inlines a fighter's nickname into their
            # display name (e.g. "Michael Venom Page" for our "Michael
            # Page" + nickname "Venom") - register that form too.
            if row["nickname"]:
                nickname_form = normalize_name(f"{row['first_name']} {row['nickname']} {row['last_name']}")
                name_to_ids.setdefault(nickname_form, []).append(row["fighter_id"])

    unmatched = []
    ambiguous = []
    unknown_division = []
    rows = []
    for entry in rankings:
        weight_class_id = weight_class_ids.get(entry["weight_class"])
        if weight_class_id is None:
            unknown_division.append(entry["weight_class"])
            continue

        ids = name_to_ids.get(normalize_name(entry["fighter_name"]))
        fighter_id = None
        if not ids:
            unmatched.append(entry["fighter_name"])
        elif len(ids) > 1:
            ambiguous.append(entry["fighter_name"])
        else:
            fighter_id = ids[0]

        rows.append((weight_class_id, entry["rank"], fighter_id, entry["fighter_name"]))

    with conn.cursor() as cur:
        cur.execute("TRUNCATE current_rankings RESTART IDENTITY")
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO current_rankings (weight_class_id, rank, fighter_id, fighter_name_raw) VALUES %s",
            rows,
        )
    conn.close()

    print(f"Loaded {len(rows)} rankings ({len(unmatched)} unmatched names, {len(ambiguous)} ambiguous, {len(unknown_division)} unknown divisions)")
    if unmatched:
        print("Unmatched:", unmatched)
    if ambiguous:
        print("Ambiguous:", ambiguous)
    if unknown_division:
        print("Unknown divisions:", set(unknown_division))


if __name__ == "__main__":
    main()
