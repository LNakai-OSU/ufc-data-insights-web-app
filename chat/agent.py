"""NL-to-SQL agent: answers plain-English questions about UFC stats by
having Claude write and run SQL against the read-only database.

Manual agentic loop rather than the SDK's (beta) tool runner - this is a
single bounded tool with a small number of iterations, so owning the loop
directly means no beta dependency and full visibility into each generated
query, which we want to surface back to the caller (and eventually the
dashboard) for transparency.
"""
from __future__ import annotations

import json

import anthropic
import psycopg2

from .schema_description import SCHEMA_DESCRIPTION
from .sql_tool import SQLValidationError, run_sql

MODEL = "claude-opus-5"
MAX_ITERATIONS = 5

SYSTEM_PROMPT = f"""You are a UFC statistics analyst assistant. You answer \
questions about UFC fighters and fights by writing and running SQL against \
a Postgres database, using the run_sql_query tool.

{SCHEMA_DESCRIPTION}

Guidelines:
- Always use the run_sql_query tool to get real data before answering - \
never guess or make up numbers.
- Match fighter/event names case-insensitively (ILIKE '%name%') since \
users won't type exact capitalization.
- After you get results, answer in plain English with the key numbers \
inline (e.g. "Southpaws win 52.5% of decided fights (1,755 of 3,345) \
compared to 49.4% for orthodox fighters"). Don't just dump a table.
- If a query returns no rows, say so plainly rather than guessing why.
- If the question is ambiguous (e.g. which fighter, when two share a \
name), ask for clarification instead of picking one arbitrarily.
"""

RUN_SQL_TOOL = {
    "name": "run_sql_query",
    "description": (
        "Execute a read-only SQL SELECT query against the UFC stats Postgres "
        "database and return the results as rows. Only SELECT/WITH statements "
        "are permitted; the database connection itself is read-only."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A single Postgres SELECT (or WITH ... SELECT) statement.",
            }
        },
        "required": ["query"],
    },
}


def _execute_tool(query: str) -> tuple[str, bool]:
    try:
        columns, rows = run_sql(query)
        return json.dumps({"columns": columns, "row_count": len(rows), "rows": rows}, default=str), False
    except SQLValidationError as e:
        return f"Query rejected: {e}", True
    except psycopg2.Error as e:
        return f"Database error: {e.pgerror or str(e)}", True


def ask(question: str, client: anthropic.Anthropic | None = None) -> dict:
    """Returns {"answer": str, "queries": [{"sql": str, "row_count": int}, ...]}."""
    client = client or anthropic.Anthropic()
    messages: list[dict] = [{"role": "user", "content": question}]
    executed_queries: list[dict] = []

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[RUN_SQL_TOOL],
            messages=messages,
        )

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            answer = next((b.text for b in response.content if b.type == "text"), "")
            return {"answer": answer, "queries": executed_queries}

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in tool_use_blocks:
            query = block.input.get("query", "")
            result_text, is_error = _execute_tool(query)
            if not is_error:
                row_count = json.loads(result_text)["row_count"]
                executed_queries.append({"sql": query, "row_count": row_count})
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return {
        "answer": "I wasn't able to settle on an answer within the allowed number of query attempts.",
        "queries": executed_queries,
    }
