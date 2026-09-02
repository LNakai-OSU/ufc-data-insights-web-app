"""CLI for the NL-to-SQL chat assistant.

Usage:
    python ask.py "Do southpaws have a higher win rate than orthodox fighters?"

Requires ANTHROPIC_API_KEY in the environment and Postgres running locally
with the ufc_stats_readonly role set up (see db/readonly_role.sql).
"""
from __future__ import annotations

import sys

from chat.agent import ask


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python ask.py "your question"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    result = ask(question)

    print(f"\n{result['answer']}\n")
    if result["queries"]:
        print("--- SQL used ---")
        for q in result["queries"]:
            print(f"[{q['row_count']} rows]  {q['sql']}")


if __name__ == "__main__":
    main()
