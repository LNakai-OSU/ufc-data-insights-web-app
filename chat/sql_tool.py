"""Validated, read-only SQL execution for the NL-to-SQL chat assistant.

The Postgres role used here (ufc_stats_readonly, see db/readonly_role.sql)
is what actually prevents writes - GRANT SELECT only, everything else
denied at the database level. The checks in this file are a second,
faster-failing layer: they catch obviously-wrong queries (multiple
statements, non-SELECT) before a round trip to Postgres, and they turn a
rejection into a tool_result the model can read and self-correct from,
instead of an opaque permission-denied error.
"""
from __future__ import annotations

import re

import psycopg2
import psycopg2.extras

READONLY_DSN = "postgresql:///ufc_stats?user=ufc_stats_readonly"
MAX_ROWS = 200
STATEMENT_TIMEOUT_MS = 5000

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|COPY|"
    r"VACUUM|EXECUTE|CALL|MERGE|REPLACE|SET|RESET|LISTEN|NOTIFY)\b",
    re.IGNORECASE,
)


class SQLValidationError(ValueError):
    pass


def _validate(query: str) -> str:
    stripped = query.strip().rstrip(";").strip()
    if not stripped:
        raise SQLValidationError("Query is empty.")

    if ";" in stripped:
        raise SQLValidationError(
            "Only a single SQL statement is allowed (no ';' inside the query)."
        )

    if not re.match(r"^(SELECT|WITH)\b", stripped, re.IGNORECASE):
        raise SQLValidationError("Only SELECT (or WITH ... SELECT) statements are allowed.")

    forbidden = _FORBIDDEN_KEYWORDS.search(stripped)
    if forbidden:
        raise SQLValidationError(
            f"Query contains a disallowed keyword: {forbidden.group(0)}. "
            "Only read-only SELECT queries are permitted."
        )

    if not re.search(r"\bLIMIT\b", stripped, re.IGNORECASE):
        stripped = f"{stripped} LIMIT {MAX_ROWS}"

    return stripped


def run_sql(query: str, dsn: str = READONLY_DSN) -> tuple[list[str], list[dict]]:
    """Validates and executes a read-only query. Returns (column_names, rows).

    Raises SQLValidationError for queries that fail validation, or
    psycopg2.Error for queries Postgres itself rejects (bad column name,
    permission denied, syntax error, etc.) - both are caught by the caller
    and turned into a tool_result so the model can retry.
    """
    safe_query = _validate(query)

    conn = psycopg2.connect(dsn)
    try:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
            cur.execute(safe_query)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return columns, [dict(r) for r in rows]
    finally:
        conn.close()
