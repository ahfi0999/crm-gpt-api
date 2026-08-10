"""Predefined, read-only lead queries for the inspected CRM schema."""

import os
from typing import Any
from uuid import UUID

from app.database import get_connection

SELECT_LEAD = """
SELECT l.work_item_id AS id, wi.number AS lead_number, p.name, p.phone, p.email,
       wi.created_at, l.lead_status, l.stage, l.stage_label, l.source,
       l.source_label, l.program, l.heat, l.score, assignee.name AS assigned_to
FROM public.lead AS l
JOIN public.work_item AS wi
  ON wi.id = l.work_item_id AND wi.tenant_id = l.tenant_id
LEFT JOIN public.party AS p
  ON p.id = wi.party_id AND p.tenant_id = l.tenant_id
LEFT JOIN public.party AS assignee
  ON assignee.id = wi.assignee_id AND assignee.tenant_id = l.tenant_id
"""


def _tenant_id() -> UUID:
    value = os.getenv("CRM_TENANT_ID", "")
    if not value:
        raise RuntimeError("CRM_TENANT_ID is not configured")
    return UUID(value)


def _timezone() -> str:
    return os.getenv("CRM_TIMEZONE", "Asia/Kolkata")


def _fetch(sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(sql, params).fetchall()]


def latest(limit: int) -> list[dict[str, Any]]:
    return _fetch(SELECT_LEAD + " WHERE l.tenant_id = %s ORDER BY wi.created_at DESC LIMIT %s", (_tenant_id(), limit))


def today(limit: int) -> list[dict[str, Any]]:
    return _fetch(
        SELECT_LEAD + """ WHERE l.tenant_id = %s
          AND (wi.created_at AT TIME ZONE %s)::date = (CURRENT_TIMESTAMP AT TIME ZONE %s)::date
          ORDER BY wi.created_at DESC LIMIT %s""",
        (_tenant_id(), _timezone(), _timezone(), limit),
    )


def count_today() -> int:
    sql = """SELECT count(*) AS count FROM public.lead AS l
    JOIN public.work_item AS wi ON wi.id = l.work_item_id AND wi.tenant_id = l.tenant_id
    WHERE l.tenant_id = %s AND (wi.created_at AT TIME ZONE %s)::date = (CURRENT_TIMESTAMP AT TIME ZONE %s)::date"""
    with get_connection() as connection:
        return int(connection.execute(sql, (_tenant_id(), _timezone(), _timezone())).fetchone()["count"])


def search(query: str, limit: int) -> list[dict[str, Any]]:
    pattern = f"%{query}%"
    return _fetch(
        SELECT_LEAD + """ WHERE l.tenant_id = %s AND
          (p.name ILIKE %s OR p.phone ILIKE %s OR p.email ILIKE %s OR wi.number ILIKE %s)
          ORDER BY wi.created_at DESC LIMIT %s""",
        (_tenant_id(), pattern, pattern, pattern, pattern, limit),
    )


def by_status(status: str, limit: int) -> list[dict[str, Any]]:
    return _fetch(
        SELECT_LEAD + """ WHERE l.tenant_id = %s AND
          (l.lead_status ILIKE %s OR l.stage ILIKE %s OR l.stage_label ILIKE %s)
          ORDER BY wi.created_at DESC LIMIT %s""",
        (_tenant_id(), status, status, status, limit),
    )


def by_assignee(person: str, limit: int) -> list[dict[str, Any]]:
    return _fetch(
        SELECT_LEAD + """ WHERE l.tenant_id = %s AND assignee.name ILIKE %s
          ORDER BY wi.created_at DESC LIMIT %s""",
        (_tenant_id(), f"%{person}%", limit),
    )
