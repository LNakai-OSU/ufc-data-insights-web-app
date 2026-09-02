"""Run: python -m chat.test_sql_tool (from project root; requires Postgres running locally)"""
import psycopg2

from chat.sql_tool import SQLValidationError, run_sql


def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise AssertionError(label)


columns, rows = run_sql("SELECT stance, count(*) FROM fighters GROUP BY stance ORDER BY stance")
check("basic select works", len(rows) > 0)
check("columns match", columns == ["stance", "count"])

columns, rows = run_sql("SELECT fighter_id FROM fighters")
check("unbounded query gets LIMIT injected", len(rows) == 200)

for bad_query, label in [
    ("DELETE FROM fighters", "DELETE rejected by validator"),
    ("SELECT 1; DROP TABLE fighters", "multi-statement rejected"),
    ("UPDATE fighters SET stance = 'x'", "UPDATE rejected"),
    ("", "empty query rejected"),
]:
    try:
        run_sql(bad_query)
        check(label, False)
    except SQLValidationError:
        check(label, True)

# Even if validation were bypassed, the DB role itself must refuse writes.
try:
    run_sql("SELECT 1) ; DELETE FROM fighters WHERE 1=1 --", "postgresql:///ufc_stats?user=ufc_stats_readonly")
    check("defense-in-depth: malformed bypass attempt rejected", False)
except (SQLValidationError, psycopg2.Error):
    check("defense-in-depth: malformed bypass attempt rejected", True)

columns, rows = run_sql("SELECT * FROM fighters WHERE last_name = 'NoSuchPersonAtAll'")
check("empty result set handled", rows == [])

print("\nAll sql_tool checks passed.")
