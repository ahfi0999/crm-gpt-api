"""Predefined, read-only lead queries for the inspected CRM schema."""

import os
from typing import Any
from uuid import UUID

from app.database import get_connection

SELECT_LEAD = """
SELECT l.work_item_id AS id, wi.number AS lead_number, p.name, p.phone, p.email,
       p.city, p.phone_country_code, wi.created_at, wi.updated_at,
       wi.state AS workflow_state, wi.priority, l.lead_status, l.stage,
       l.stage_label, l.source, l.source_label, l.source_url, l.program,
       program.name AS program_name, l.heat, l.score, l.score_label,
       l.score_desc, l.value, l.rating, l.description, l.delivery_mode,
       l.time_zone, l.next_followup_at, l.demo_attended_at, l.visited_date,
       l.visiting_date, assignee.name AS assigned_to, advisor.name AS advisor
FROM public.lead AS l
JOIN public.work_item AS wi
  ON wi.id = l.work_item_id AND wi.tenant_id = l.tenant_id
LEFT JOIN public.party AS p
  ON p.id = wi.party_id AND p.tenant_id = l.tenant_id
LEFT JOIN public.party AS assignee
  ON assignee.id = wi.assignee_id AND assignee.tenant_id = l.tenant_id
LEFT JOIN public.party AS advisor
  ON advisor.id = l.advisor_id AND advisor.tenant_id = l.tenant_id
LEFT JOIN public.program AS program
  ON program.id = l.program_id AND program.tenant_id = l.tenant_id
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


def latest(limit: int, offset: int = 0) -> list[dict[str, Any]]:
    return _fetch(
        SELECT_LEAD + " WHERE l.tenant_id = %s ORDER BY wi.created_at DESC LIMIT %s OFFSET %s",
        (_tenant_id(), limit, offset),
    )


def total_count() -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT count(*) AS count FROM public.lead WHERE tenant_id = %s",
            (_tenant_id(),),
        ).fetchone()
        return int(row["count"])


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
