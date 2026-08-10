"""Safely inspect PostgreSQL metadata. This script never reads business rows."""

import json
import os
import sys
from collections import defaultdict

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()


def connection_kwargs() -> dict[str, object]:
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [
        name for name in required if not os.getenv(name) or os.getenv(name) == "CHANGE_ME"
    ]
    if missing:
        raise RuntimeError(f"Missing settings in .env: {', '.join(missing)}")
    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ["DB_PORT"]),
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "sslmode": "require",
        "connect_timeout": 10,
    }


METADATA_SQL = """
SELECT c.table_schema, c.table_name, c.column_name, c.data_type,
       c.udt_name, c.is_nullable, c.ordinal_position
FROM information_schema.columns AS c
JOIN information_schema.tables AS t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE t.table_type = 'BASE TABLE'
  AND c.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY c.table_schema, c.table_name, c.ordinal_position
"""

PRIMARY_KEY_SQL = """
SELECT tc.table_schema, tc.table_name, kcu.column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.constraint_schema = kcu.constraint_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY tc.table_schema, tc.table_name, kcu.ordinal_position
"""

FOREIGN_KEY_SQL = """
SELECT tc.table_schema, tc.table_name, kcu.column_name,
       ccu.table_schema AS referenced_schema,
       ccu.table_name AS referenced_table,
       ccu.column_name AS referenced_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.constraint_schema = kcu.constraint_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON tc.constraint_name = ccu.constraint_name
 AND tc.constraint_schema = ccu.constraint_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY tc.table_schema, tc.table_name, kcu.column_name
"""


def lead_score(table_name: str, columns: list[dict]) -> tuple[int, list[str]]:
    names = {column["column_name"].lower() for column in columns}
    reasons: list[str] = []
    score = 0
    if "lead" in table_name.lower():
        score += 5
        reasons.append("table name contains 'lead'")
    groups = {
        "identity": {"name", "full_name", "first_name", "lead_name"},
        "phone": {"phone", "phone_number", "mobile", "mobile_number"},
        "email": {"email", "email_address"},
        "created": {"created_at", "created_date", "date_created", "created_on"},
        "status": {"status", "lead_status", "stage"},
        "assignment": {"assigned_to", "assignee", "owner_id", "assigned_user_id"},
    }
    for label, candidates in groups.items():
        matches = sorted(names & candidates)
        if matches:
            score += 1
            reasons.append(f"{label}: {', '.join(matches)}")
    return score, reasons


def inspect() -> dict[str, object]:
    with psycopg.connect(**connection_kwargs(), row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        columns = connection.execute(METADATA_SQL).fetchall()
        primary_keys = connection.execute(PRIMARY_KEY_SQL).fetchall()
        foreign_keys = connection.execute(FOREIGN_KEY_SQL).fetchall()

    tables: dict[str, list[dict]] = defaultdict(list)
    for column in columns:
        key = f'{column["table_schema"]}.{column["table_name"]}'
        tables[key].append(dict(column))

    candidates = []
    for qualified_name, table_columns in tables.items():
        score, reasons = lead_score(qualified_name.split(".", 1)[1], table_columns)
        if score:
            candidates.append({"table": qualified_name, "score": score, "reasons": reasons})
    candidates.sort(key=lambda item: (-item["score"], item["table"]))
    return {
        "schemas": sorted({c["table_schema"] for c in columns}),
        "tables": tables,
        "primary_keys": [dict(row) for row in primary_keys],
        "foreign_keys": [dict(row) for row in foreign_keys],
        "possible_lead_tables": candidates,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(inspect(), indent=2, default=str))
    except Exception as exc:
        # Database credentials and connection strings are never included explicitly.
        print(f"Database inspection failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
