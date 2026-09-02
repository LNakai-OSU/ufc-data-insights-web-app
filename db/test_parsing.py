"""Run: python db/test_parsing.py"""
from parsing import (
    parse_control_seconds,
    parse_dob,
    parse_event_date,
    parse_height_in,
    parse_int,
    parse_reach_in,
    parse_round_number,
    parse_weight_class,
    parse_weight_lbs,
    parse_x_of_y,
)


def check(label, actual, expected):
    status = "OK" if actual == expected else "FAIL"
    print(f"[{status}] {label}: {actual!r} (expected {expected!r})")
    if actual != expected:
        raise AssertionError(label)


check("height", parse_height_in("6' 4\""), 76.0)
check("height blank", parse_height_in("--"), None)
check("weight", parse_weight_lbs("248 lbs."), 248.0)
check("reach", parse_reach_in('84.5"'), 84.5)
check("reach blank", parse_reach_in("--"), None)
check("dob", parse_dob("Jul 19, 1987"), __import__("datetime").date(1987, 7, 19))
check("event date", parse_event_date("August 29, 2026"), __import__("datetime").date(2026, 8, 29))

check("weight class plain", parse_weight_class("Lightweight Bout"), ("Lightweight", False, False))
check(
    "weight class title",
    parse_weight_class("UFC Light Heavyweight Title Bout"),
    ("Light Heavyweight", True, False),
)
check(
    "weight class interim",
    parse_weight_class("UFC Interim Heavyweight Title Bout"),
    ("Heavyweight", True, True),
)
check(
    "weight class TUF tournament is NOT a title fight",
    parse_weight_class("Ultimate Fighter 33 Welterweight Tournament Title Bout"),
    ("Welterweight", False, False),
)
check(
    "weight class women's title",
    parse_weight_class("UFC Women's Strawweight Title Bout"),
    ("Women's Strawweight", True, False),
)
check(
    "weight class old-UFC numbered tournament, no weight class mentioned",
    parse_weight_class("UFC 10 Tournament Title Bout"),
    (None, False, False),
)
check("weight class super heavyweight", parse_weight_class("Super Heavyweight Bout"), ("Super Heavyweight", False, False))

check("x of y", parse_x_of_y("7 of 10"), (7, 10))
check("x of y blank", parse_x_of_y(""), (None, None))
check("x of y dashes", parse_x_of_y("---"), (None, None))

check("control seconds", parse_control_seconds("1:58"), 118)
check("control seconds blank", parse_control_seconds("--"), None)

check("int with trailing .0 (source quirk)", parse_int("0.0"), 0)
check("int plain", parse_int("5"), 5)
check("round number", parse_round_number("Round 1"), 1)
check("round number blank", parse_round_number(""), None)

print("\nAll parsing checks passed.")
