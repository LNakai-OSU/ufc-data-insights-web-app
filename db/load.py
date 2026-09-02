"""Load data/raw/*.csv into the normalized ufc_stats Postgres schema.

Usage:
    python db/load.py [--dsn postgresql:///ufc_stats]

Idempotent: truncates all tables before loading, so it's safe to re-run
after `fetch_data.py` pulls a fresh CSV snapshot.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import psycopg2
import psycopg2.extras

from parsing import (
    id_from_url,
    parse_control_seconds,
    parse_dob,
    parse_event_date,
    parse_height_in,
    parse_int,
    parse_reach_in,
    parse_round_number,
    parse_stance,
    parse_time_seconds,
    parse_weight_class,
    parse_weight_lbs,
    parse_x_of_y,
)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

_OUTCOME_TO_RESULT = {
    "W/L": "fighter_1_win",
    "L/W": "fighter_2_win",
    "D/D": "draw",
    "NC/NC": "no_contest",
}


def read_csv(name: str) -> list[dict]:
    with open(RAW_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_fighters(cur) -> dict[str, list[str]]:
    """Loads fighters table. Returns {full_name: [fighter_id, ...]} for
    resolving fighter names in fight-level tables (a name maps to more
    than one id when two fighters share a full name)."""
    details = {r["URL"]: r for r in read_csv("ufc_fighter_details.csv")}
    tott = {r["URL"]: r for r in read_csv("ufc_fighter_tott.csv")}

    rows = []
    name_to_ids: dict[str, list[str]] = defaultdict(list)
    for url, d in details.items():
        t = tott.get(url, {})
        fighter_id = id_from_url(url)
        first, last = d["FIRST"].strip(), d["LAST"].strip()
        full_name = f"{first} {last}".strip()
        name_to_ids[full_name].append(fighter_id)

        rows.append(
            (
                fighter_id,
                first,
                last,
                d["NICKNAME"].strip() or None,
                parse_height_in(t.get("HEIGHT", "")),
                parse_weight_lbs(t.get("WEIGHT", "")),
                parse_reach_in(t.get("REACH", "")),
                parse_stance(t.get("STANCE", "")),
                parse_dob(t.get("DOB", "")),
                url,
            )
        )

    psycopg2.extras.execute_values(
        cur,
        """INSERT INTO fighters
           (fighter_id, first_name, last_name, nickname, height_in,
            weight_lbs, reach_in, stance, dob, url)
           VALUES %s""",
        rows,
    )
    print(f"fighters: {len(rows)} loaded")
    return name_to_ids


def resolve_fighter(name_to_ids: dict[str, list[str]], name: str, stats: dict) -> str | None:
    ids = name_to_ids.get(name.strip())
    if not ids:
        stats["unmatched"] += 1
        return None
    if len(ids) > 1:
        stats["ambiguous"] += 1
        return None
    return ids[0]


def load_events(cur) -> dict[str, str]:
    rows = []
    name_to_id = {}
    for r in read_csv("ufc_event_details.csv"):
        event_id = id_from_url(r["URL"])
        name = r["EVENT"].strip()
        name_to_id[name] = event_id
        rows.append((event_id, name, parse_event_date(r["DATE"]), r["LOCATION"].strip() or None, r["URL"]))

    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO events (event_id, name, event_date, location, url) VALUES %s",
        rows,
    )
    print(f"events: {len(rows)} loaded")
    return name_to_id


def load_weight_classes(cur, fight_results: list[dict]) -> dict[str, int]:
    names = set()
    for r in fight_results:
        name, _, _ = parse_weight_class(r["WEIGHTCLASS"])
        if name:
            names.add(name)

    cur.executemany(
        "INSERT INTO weight_classes (name) VALUES (%s)", [(n,) for n in sorted(names)]
    )
    cur.execute("SELECT name, weight_class_id FROM weight_classes")
    name_to_id = dict(cur.fetchall())
    print(f"weight_classes: {len(name_to_id)} loaded")
    return name_to_id


def load_fights(
    cur,
    fight_results: list[dict],
    event_name_to_id: dict[str, str],
    weight_class_name_to_id: dict[str, int],
    fighter_name_to_ids: dict[str, list[str]],
) -> dict[tuple[str, str], str]:
    rows = []
    bout_to_fight_id: dict[tuple[str, str], str] = {}
    stats = {
        "unmatched": 0,
        "ambiguous": 0,
        "skipped_no_event": 0,
    }

    for r in fight_results:
        event_name = r["EVENT"].strip()
        event_id = event_name_to_id.get(event_name)
        if event_id is None:
            stats["skipped_no_event"] += 1
            continue

        bout = r["BOUT"].strip()
        name_1, name_2 = (n.strip() for n in bout.split(" vs. ", 1))
        fighter_1_id = resolve_fighter(fighter_name_to_ids, name_1, stats)
        fighter_2_id = resolve_fighter(fighter_name_to_ids, name_2, stats)

        result = _OUTCOME_TO_RESULT[r["OUTCOME"].strip()]
        winner_id = None
        if result == "fighter_1_win":
            winner_id = fighter_1_id
        elif result == "fighter_2_win":
            winner_id = fighter_2_id

        weight_class_name, is_title, is_interim = parse_weight_class(r["WEIGHTCLASS"])
        weight_class_id = weight_class_name_to_id.get(weight_class_name) if weight_class_name else None

        fight_id = id_from_url(r["URL"])
        bout_to_fight_id[(event_name, bout)] = fight_id

        rows.append(
            (
                fight_id,
                event_id,
                fighter_1_id,
                name_1,
                fighter_2_id,
                name_2,
                result,
                winner_id,
                weight_class_id,
                is_title,
                is_interim,
                r["METHOD"].strip() or None,
                r["DETAILS"].strip() or None,
                parse_int(r["ROUND"]),
                parse_time_seconds(r["TIME"]),
                r["TIME FORMAT"].strip() or None,
                r["REFEREE"].strip() or None,
                r["URL"],
            )
        )

    psycopg2.extras.execute_values(
        cur,
        """INSERT INTO fights
           (fight_id, event_id, fighter_1_id, fighter_1_name_raw,
            fighter_2_id, fighter_2_name_raw, result, winner_id,
            weight_class_id, is_title_bout, is_interim_title,
            method, method_detail, round, time_seconds, time_format,
            referee, url)
           VALUES %s""",
        rows,
    )
    print(
        f"fights: {len(rows)} loaded "
        f"(skipped {stats['skipped_no_event']} with no matching event; "
        f"fighter refs: {stats['unmatched']} unmatched, {stats['ambiguous']} ambiguous by name)"
    )
    return bout_to_fight_id


def load_fight_stats(
    cur,
    bout_to_fight_id: dict[tuple[str, str], str],
    fighter_name_to_ids: dict[str, list[str]],
) -> None:
    rows = []
    stats = {"unmatched": 0, "ambiguous": 0}
    skipped_blank_round = 0
    skipped_no_fight = 0
    skipped_duplicate_key = 0
    seen_keys: set[tuple[str, str, int]] = set()

    for r in read_csv("ufc_fight_stats.csv"):
        round_num = parse_round_number(r["ROUND"])
        if round_num is None:
            skipped_blank_round += 1
            continue

        key = (r["EVENT"].strip(), r["BOUT"].strip())
        fight_id = bout_to_fight_id.get(key)
        if fight_id is None:
            skipped_no_fight += 1
            continue

        fighter_name = r["FIGHTER"].strip()
        # A handful of rows in the source (all from 1990s events) share the
        # same (fight, fighter, round) key with differing, conflicting stats -
        # there's no way to know which is correct, so keep the first and
        # drop the rest rather than guess or violate the table's unique
        # constraint.
        dedup_key = (fight_id, fighter_name, round_num)
        if dedup_key in seen_keys:
            skipped_duplicate_key += 1
            continue
        seen_keys.add(dedup_key)

        fighter_id = resolve_fighter(fighter_name_to_ids, fighter_name, stats)

        sig_landed, sig_attempted = parse_x_of_y(r["SIG.STR."])
        tot_landed, tot_attempted = parse_x_of_y(r["TOTAL STR."])
        td_landed, td_attempted = parse_x_of_y(r["TD"])
        head_landed, head_attempted = parse_x_of_y(r["HEAD"])
        body_landed, body_attempted = parse_x_of_y(r["BODY"])
        leg_landed, leg_attempted = parse_x_of_y(r["LEG"])
        dist_landed, dist_attempted = parse_x_of_y(r["DISTANCE"])
        clinch_landed, clinch_attempted = parse_x_of_y(r["CLINCH"])
        ground_landed, ground_attempted = parse_x_of_y(r["GROUND"])

        rows.append(
            (
                fight_id,
                fighter_id,
                fighter_name,
                round_num,
                parse_int(r["KD"]),
                sig_landed,
                sig_attempted,
                tot_landed,
                tot_attempted,
                td_landed,
                td_attempted,
                parse_int(r["SUB.ATT"]),
                parse_int(r["REV."]),
                parse_control_seconds(r["CTRL"]),
                head_landed,
                head_attempted,
                body_landed,
                body_attempted,
                leg_landed,
                leg_attempted,
                dist_landed,
                dist_attempted,
                clinch_landed,
                clinch_attempted,
                ground_landed,
                ground_attempted,
            )
        )

    psycopg2.extras.execute_values(
        cur,
        """INSERT INTO fight_stats
           (fight_id, fighter_id, fighter_name_raw, round, knockdowns,
            sig_str_landed, sig_str_attempted, total_str_landed, total_str_attempted,
            td_landed, td_attempted, sub_attempts, reversals, control_seconds,
            head_landed, head_attempted, body_landed, body_attempted,
            leg_landed, leg_attempted, distance_landed, distance_attempted,
            clinch_landed, clinch_attempted, ground_landed, ground_attempted)
           VALUES %s""",
        rows,
    )
    print(
        f"fight_stats: {len(rows)} loaded "
        f"(skipped {skipped_blank_round} with blank round, {skipped_no_fight} with no matching fight, "
        f"{skipped_duplicate_key} conflicting duplicate rows; "
        f"fighter refs: {stats['unmatched']} unmatched, {stats['ambiguous']} ambiguous by name)"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default="postgresql:///ufc_stats")
    args = parser.parse_args()

    conn = psycopg2.connect(args.dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE fight_stats, fights, weight_classes, fighters, events RESTART IDENTITY CASCADE"
            )

            fighter_name_to_ids = load_fighters(cur)
            event_name_to_id = load_events(cur)

            fight_results = read_csv("ufc_fight_results.csv")
            weight_class_name_to_id = load_weight_classes(cur, fight_results)
            bout_to_fight_id = load_fights(
                cur, fight_results, event_name_to_id, weight_class_name_to_id, fighter_name_to_ids
            )
            load_fight_stats(cur, bout_to_fight_id, fighter_name_to_ids)

        conn.commit()
        print("Committed.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
