"""Read-only DB access for the dashboard API.

Dashboard queries are all fixed, hand-written SQL (not model-generated),
so they don't need chat/sql_tool.py's text validation - but they still
run through the same read-only Postgres role, for the same reason: an API
that only ever needs to read data shouldn't hold write privileges at all.
"""
from __future__ import annotations

from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from chat.sql_tool import READONLY_DSN


@contextmanager
def get_cursor():
    conn = psycopg2.connect(READONLY_DSN)
    try:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
    finally:
        conn.close()
