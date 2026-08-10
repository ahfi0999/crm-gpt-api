"""Read-only learner, communications, activity, and daily reporting queries."""

import os
from typing import Any
from uuid import UUID

from app.database import get_connection


def _tenant() -> UUID:
    return UUID(os.environ["CRM_TENANT_ID"])


def _tz() -> str:
    return os.getenv("CRM_TIMEZONE", "Asia/Kolkata")


def _rows(sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(sql, params).fetchall()]


def learners(limit: int, today_only: bool = False, query: str | None = None):
    filters = ["e.tenant_id = %s"]
    params: list[Any] = [_tenant()]
    if today_only:
        filters.append("(e.created_at AT TIME ZONE %s)::date = (CURRENT_TIMESTAMP AT TIME ZONE %s)::date")
        params.extend([_tz(), _tz()])
    if query:
        filters.append("(p.name ILIKE %s OR p.phone ILIKE %s OR p.email ILIKE %s OR e.number ILIKE %s)")
        params.extend([f"%{query}%"] * 4)
    params.append(limit)
    return _rows("""SELECT e.id, e.number AS enrolment_number, p.name, p.phone, p.email,
      e.status, e.payment_status, e.registered_date, e.created_at,
      e.fee_quoted, e.fee_paid, e.fee_due, pr.name AS program, c.name AS cohort
      FROM public.enrolment e JOIN public.party p ON p.id=e.party_id AND p.tenant_id=e.tenant_id
      LEFT JOIN public.program pr ON pr.id=e.program_id AND pr.tenant_id=e.tenant_id
      LEFT JOIN public.cohort c ON c.id=e.cohort_id AND c.tenant_id=e.tenant_id
      WHERE """ + " AND ".join(filters) + " ORDER BY e.created_at DESC LIMIT %s", tuple(params))


def messages(limit: int, channel: str | None, direction: str | None, today_only: bool):
    filters = ["m.tenant_id = %s"]
    params: list[Any] = [_tenant()]
    if channel:
        filters.append("m.channel = %s")
        params.append(channel)
    if direction:
        filters.append("m.direction = %s")
        params.append(direction)
    if today_only:
        filters.append("(COALESCE(m.sent_at, m.delivered_at, c.last_message_at) AT TIME ZONE %s)::date = (CURRENT_TIMESTAMP AT TIME ZONE %s)::date")
        params.extend([_tz(), _tz()])
    params.append(limit)
    return _rows("""SELECT m.id, m.channel, m.direction, m.kind, m.status, m.subject,
      left(m.body, 500) AS message_preview, m.from_number, m.to_number,
      m.sent_at, m.delivered_at, p.name AS contact_name, p.phone AS contact_phone,
      sender.name AS sent_by
      FROM public.tw_message m JOIN public.tw_conversation c
        ON c.id=m.conversation_id AND c.tenant_id=m.tenant_id
      LEFT JOIN public.party p ON p.id=c.party_id AND p.tenant_id=m.tenant_id
      LEFT JOIN public.party sender ON sender.id=m.sender_user_id AND sender.tenant_id=m.tenant_id
      WHERE """ + " AND ".join(filters) + " ORDER BY COALESCE(m.sent_at,m.delivered_at,c.last_message_at) DESC NULLS LAST LIMIT %s", tuple(params))


def conversations(limit: int, channel: str | None):
    channel_sql = " AND c.channel = %s" if channel else ""
    params: tuple[Any, ...] = (_tenant(), channel, limit) if channel else (_tenant(), limit)
    return _rows("""SELECT c.id, c.channel, c.status, p.name AS contact_name, p.phone,
      p.email, c.last_message_text, c.last_message_at, c.last_inbound_at,
      c.unread_count, assignee.name AS assigned_to
      FROM public.tw_conversation c
      LEFT JOIN public.party p ON p.id=c.party_id AND p.tenant_id=c.tenant_id
      LEFT JOIN public.party assignee ON assignee.id=c.assigned_user_id AND assignee.tenant_id=c.tenant_id
      WHERE c.tenant_id=%s""" + channel_sql + " ORDER BY c.last_message_at DESC NULLS LAST LIMIT %s", params)


def activities_today(limit: int):
    return _rows("""SELECT a.id, a.ts, a.channel, a.verb, a.detail, a.tag,
      a.actor_name, p.name AS contact_name
      FROM public.activity a LEFT JOIN public.party p
        ON p.id=a.party_id AND p.tenant_id=a.tenant_id
      WHERE a.tenant_id=%s AND (a.ts AT TIME ZONE %s)::date=(CURRENT_TIMESTAMP AT TIME ZONE %s)::date
      ORDER BY a.ts DESC LIMIT %s""", (_tenant(), _tz(), _tz(), limit))


def today_report():
    sql = """SELECT
      (SELECT count(*) FROM public.lead l JOIN public.work_item w ON w.id=l.work_item_id WHERE l.tenant_id=%s AND (w.created_at AT TIME ZONE %s)::date=(CURRENT_TIMESTAMP AT TIME ZONE %s)::date) leads_created,
      (SELECT count(*) FROM public.enrolment e WHERE e.tenant_id=%s AND (e.created_at AT TIME ZONE %s)::date=(CURRENT_TIMESTAMP AT TIME ZONE %s)::date) enrolments_created,
      (SELECT count(*) FROM public.tw_message m JOIN public.tw_conversation c ON c.id=m.conversation_id WHERE m.tenant_id=%s AND m.channel='whatsapp' AND (COALESCE(m.sent_at,m.delivered_at,c.last_message_at) AT TIME ZONE %s)::date=(CURRENT_TIMESTAMP AT TIME ZONE %s)::date) whatsapp_messages,
      (SELECT count(*) FROM public.tw_message m JOIN public.tw_conversation c ON c.id=m.conversation_id WHERE m.tenant_id=%s AND m.channel='email' AND (COALESCE(m.sent_at,m.delivered_at,c.last_message_at) AT TIME ZONE %s)::date=(CURRENT_TIMESTAMP AT TIME ZONE %s)::date) email_messages,
      (SELECT count(*) FROM public.activity a WHERE a.tenant_id=%s AND (a.ts AT TIME ZONE %s)::date=(CURRENT_TIMESTAMP AT TIME ZONE %s)::date) activities,
      (SELECT count(*) FROM public.tw_conversation c WHERE c.tenant_id=%s AND c.status='open' AND c.unread_count>0) unread_conversations"""
    args = (_tenant(),_tz(),_tz()) * 5 + (_tenant(),)
    with get_connection() as connection:
        return dict(connection.execute(sql, args).fetchone())
