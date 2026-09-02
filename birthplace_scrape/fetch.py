"""Rate-limited, disk-cached fetching for ufc.com athlete pages.

robots.txt mandates a 15-second crawl-delay for all user agents on this
site - CRAWL_DELAY_SECONDS honors that exactly, not a shortened version of
it. Both hits and misses are cached, so re-running after an interruption
doesn't re-spend the 15s delay re-discovering a page that's already known
to exist or not exist.

A wrong slug guess does NOT 404 - it 302-redirects to /search (which
robots.txt disallows crawling, so we don't follow it). We disable
redirect-following and treat any 3xx the same as a 404: the guessed slug
was wrong. Without this, requests' default redirect-following would
silently land on the search results page, cache it, and we'd misreport
"page exists but has no bio field" for what's actually just a bad slug
guess.

A 403 is a distinct case - real UFC.com content behind a page-level
access restriction (confirmed via response headers: this is an
application-level Drupal decision, not a network-layer bot-block or rate
limit - retrying or slowing down doesn't change it). It's surfaced as a
raised HTTPError, not cached as not-found.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_html_ufc_com"
CRAWL_DELAY_SECONDS = 15
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
NOT_FOUND_MARKER = "__NOT_FOUND__"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})
_last_request_time = 0.0


def _cache_path(slug: str) -> Path:
    digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.html"


def fetch_athlete_page(slug: str) -> str | None:
    """Returns the page HTML, or None if the slug doesn't resolve to a
    real profile (404, or a redirect - typically to /search). Cached on
    disk either way."""
    cache_path = _cache_path(slug)
    if cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
        return None if text == NOT_FOUND_MARKER else text

    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < CRAWL_DELAY_SECONDS:
        time.sleep(CRAWL_DELAY_SECONDS - elapsed)

    response = _session.get(
        f"https://www.ufc.com/athlete/{slug}", timeout=20, allow_redirects=False
    )
    _last_request_time = time.monotonic()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if response.status_code == 404 or response.is_redirect:
        cache_path.write_text(NOT_FOUND_MARKER, encoding="utf-8")
        return None

    response.raise_for_status()
    cache_path.write_text(response.text, encoding="utf-8")
    return response.text
