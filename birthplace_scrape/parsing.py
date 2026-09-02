from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup


_SUFFIX_PATTERN = re.compile(r"\s+(Jr\.?|Sr\.?|II|III|IV)$", re.IGNORECASE)


def _slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def slugify_name(first_name: str, last_name: str) -> str:
    """Guesses a UFC.com athlete slug from a fighter's name.

    UFC.com URLs are firstname-lastname, lowercased, accents stripped
    (e.g. "Jose Aldo" -> "jose-aldo"). This is a guess, not a lookup - see
    the module docstring in scrape_birthplaces.py for why, and how
    failures are handled.
    """
    return _slugify(f"{first_name} {last_name}")


def candidate_slugs(first_name: str, last_name: str) -> list[str]:
    """The primary slug guess, plus a suffix-stripped fallback - UFC.com
    sometimes omits a Jr./Sr./II/III/IV that ufcstats.com includes (e.g.
    ufcstats has "Michael Aswell Jr." but UFC.com's slug is just
    "michael-aswell"). Tried in order by scrape_birthplaces.py; stops at
    the first one that resolves to a real page."""
    full_name = f"{first_name} {last_name}"
    candidates = [_slugify(full_name)]

    stripped_name = _SUFFIX_PATTERN.sub("", full_name).strip()
    if stripped_name and stripped_name != full_name:
        stripped_slug = _slugify(stripped_name)
        if stripped_slug not in candidates:
            candidates.append(stripped_slug)

    return candidates


def parse_birthplace(html: str) -> str | None:
    """Extracts the raw "Place of Birth" bio field text, or None if absent."""
    soup = BeautifulSoup(html, "lxml")
    for field in soup.find_all("div", class_="c-bio__field"):
        label = field.find("div", class_="c-bio__label")
        value = field.find("div", class_="c-bio__text")
        if label and value and label.get_text(strip=True) == "Place of Birth":
            text = value.get_text(strip=True)
            return text or None
    return None


def parse_country(birthplace_raw: str) -> str | None:
    """"Rochester, United States" -> "United States". Takes the text after
    the last comma, since US/Canada birthplaces include a state
    ("City, State, Country" has no state for international fighters, but
    the country is reliably the last comma-separated segment either way)."""
    if not birthplace_raw or "," not in birthplace_raw:
        return birthplace_raw or None
    return birthplace_raw.rsplit(",", 1)[-1].strip() or None
