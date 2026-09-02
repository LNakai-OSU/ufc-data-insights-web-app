"""Parsing helpers for turning raw ufcstats.com CSV text into typed values.

Kept separate from load.py so these are independently testable - the raw
source formats (heights like `6' 4"`, stats like `7 of 10`, weight class
strings that conflate weight + title status) are the fiddliest part of
this pipeline and the easiest place to introduce silent bugs.
"""
from __future__ import annotations

import re
from datetime import date, datetime

# Ordered longest/most-specific first so e.g. "Light Heavyweight" is matched
# before the "Heavyweight" substring it contains.
_WEIGHT_CLASS_TERMS = [
    "Women's Strawweight",
    "Women's Flyweight",
    "Women's Bantamweight",
    "Women's Featherweight",
    "Super Heavyweight",
    "Light Heavyweight",
    "Heavyweight",
    "Welterweight",
    "Middleweight",
    "Lightweight",
    "Featherweight",
    "Bantamweight",
    "Flyweight",
    "Strawweight",
    "Open Weight",
    "Catch Weight",
]

_VALID_STANCES = {"Orthodox", "Southpaw", "Switch", "Open Stance", "Sideways"}


def id_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def parse_height_in(text: str) -> float | None:
    text = text.strip()
    if text in ("", "--"):
        return None
    match = re.match(r"(\d+)'\s*(\d+)", text)
    if not match:
        return None
    feet, inches = match.groups()
    return float(int(feet) * 12 + int(inches))


def parse_weight_lbs(text: str) -> float | None:
    text = text.strip()
    if text in ("", "--"):
        return None
    match = re.search(r"[\d.]+", text)
    return float(match.group()) if match else None


def parse_reach_in(text: str) -> float | None:
    text = text.strip()
    if text in ("", "--"):
        return None
    match = re.search(r"[\d.]+", text)
    return float(match.group()) if match else None


def parse_stance(text: str) -> str | None:
    text = text.strip()
    return text if text in _VALID_STANCES else None


def parse_dob(text: str) -> date | None:
    text = text.strip()
    if text in ("", "--"):
        return None
    return datetime.strptime(text, "%b %d, %Y").date()


def parse_event_date(text: str) -> date | None:
    text = text.strip()
    if text in ("", "--"):
        return None
    return datetime.strptime(text, "%B %d, %Y").date()


def parse_weight_class(raw: str) -> tuple[str | None, bool, bool]:
    """Returns (weight_class_name, is_title_bout, is_interim_title).

    The source WEIGHTCLASS column conflates the weight class with title
    status across ~120 distinct strings (e.g. "UFC Interim Heavyweight
    Title Bout", "Ultimate Fighter 33 Welterweight Tournament Title
    Bout"). A bout only counts as a genuine UFC title fight if it starts
    with "UFC " and says "Title Bout" but is NOT a TUF/tournament bracket
    bout (those also say "Title Bout" but aren't a championship fight).
    """
    raw = raw.strip()

    weight_class_name = None
    for term in _WEIGHT_CLASS_TERMS:
        if term in raw:
            weight_class_name = term
            break

    is_title_bout = (
        raw.startswith("UFC ") and "Title Bout" in raw and "Tournament" not in raw
    )
    is_interim_title = is_title_bout and "Interim" in raw

    return weight_class_name, is_title_bout, is_interim_title


def parse_x_of_y(text: str) -> tuple[int | None, int | None]:
    text = text.strip()
    if text in ("", "---", "--"):
        return None, None
    match = re.match(r"(\d+)\s+of\s+(\d+)", text)
    if not match:
        return None, None
    landed, attempted = match.groups()
    return int(landed), int(attempted)


def parse_int(text: str) -> int | None:
    text = text.strip()
    if text in ("", "---", "--"):
        return None
    return int(float(text))  # source sometimes writes e.g. "0.0" instead of "0"


def parse_control_seconds(text: str) -> int | None:
    text = text.strip()
    if text in ("", "---", "--"):
        return None
    match = re.match(r"(\d+):(\d\d)", text)
    if not match:
        return None
    minutes, seconds = match.groups()
    return int(minutes) * 60 + int(seconds)


def parse_time_seconds(text: str) -> int | None:
    return parse_control_seconds(text)


def parse_round_number(text: str) -> int | None:
    text = text.strip()
    match = re.match(r"Round (\d+)", text)
    return int(match.group(1)) if match else None
