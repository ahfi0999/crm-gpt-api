from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query

from app import database
from app.auth import require_api_key
from app.services import leads, reporting


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.open_pool()
    try:
        yield
    finally:
        database.close_pool()


app = FastAPI(
    title="CRM GPT API",
    description="A read-only, authenticated bridge to the CRM.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", operation_id="healthCheck", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/leads/latest", operation_id="getLatestLeads", tags=["Leads"])
def get_latest_leads(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_api_key),
):
    records = leads.latest(limit, offset)
    total = leads.total_count()
    next_offset = offset + len(records)
    has_more = next_offset < total
    return {"leads": records, "limit": limit, "offset": offset,
            "returned": len(records), "total": total, "has_more": has_more,
            "next_offset": next_offset if has_more else None}


@app.get("/leads/count", operation_id="getTotalLeadCount", tags=["Leads"])
def get_total_lead_count(_: None = Depends(require_api_key)):
    return {"count": leads.total_count()}


@app.get("/leads/today", operation_id="getTodaysLeads", tags=["Leads"])
def get_todays_leads(limit: int = Query(20, ge=1, le=100), _: None = Depends(require_api_key)):
    return {"leads": leads.today(limit), "limit": limit}


@app.get("/leads/count/today", operation_id="getTodaysLeadCount", tags=["Leads"])
def get_todays_lead_count(_: None = Depends(require_api_key)):
    return {"count": leads.count_today()}


@app.get("/leads/search", operation_id="searchLeads", tags=["Leads"])
def search_leads(
    query: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(20, ge=1, le=100),
    _: None = Depends(require_api_key),
):
    return {"leads": leads.search(query, limit), "query": query, "limit": limit}


@app.get("/leads/status/{status}", operation_id="getLeadsByStatus", tags=["Leads"])
def get_leads_by_status(
    status: str, limit: int = Query(20, ge=1, le=100), _: None = Depends(require_api_key)
):
    return {"leads": leads.by_status(status, limit), "status": status, "limit": limit}


@app.get("/leads/assigned/{person}", operation_id="getLeadsByAssignee", tags=["Leads"])
def get_leads_by_assignee(
    person: str, limit: int = Query(20, ge=1, le=100), _: None = Depends(require_api_key)
):
    return {"leads": leads.by_assignee(person, limit), "person": person, "limit": limit}

@app.get("/reports/today", operation_id="getTodaysCRMReport", tags=["Reports"])
def get_todays_crm_report(_: None = Depends(require_api_key)):
    return reporting.today_report()

@app.get("/learners/latest", operation_id="getLatestLearners", tags=["Learners"])
def get_latest_learners(limit: int = Query(20, ge=1, le=100), _: None = Depends(require_api_key)):
    return {"learners": reporting.learners(limit), "limit": limit}

@app.get("/learners/today", operation_id="getTodaysLearners", tags=["Learners"])
def get_todays_learners(limit: int = Query(20, ge=1, le=100), _: None = Depends(require_api_key)):
    return {"learners": reporting.learners(limit, today_only=True), "limit": limit}

@app.get("/learners/search", operation_id="searchLearners", tags=["Learners"])
def search_learners(query: str = Query(..., min_length=2, max_length=200), limit: int = Query(20, ge=1, le=100), _: None = Depends(require_api_key)):
    return {"learners": reporting.learners(limit, query=query), "query": query, "limit": limit}

@app.get("/messages/latest", operation_id="getLatestMessages", tags=["Communications"])
def get_latest_messages(channel: str | None = Query(None, pattern="^(whatsapp|email|voice)$"), direction: str | None = Query(None, pattern="^(inbound|outbound)$"), limit: int = Query(20, ge=1, le=100), _: None = Depends(require_api_key)):
    return {"messages": reporting.messages(limit, channel, direction, False), "limit": limit}

@app.get("/messages/today", operation_id="getTodaysMessages", tags=["Communications"])
def get_todays_messages(channel: str | None = Query(None, pattern="^(whatsapp|email|voice)$"), direction: str | None = Query(None, pattern="^(inbound|outbound)$"), limit: int = Query(20, ge=1, le=100), _: None = Depends(require_api_key)):
    return {"messages": reporting.messages(limit, channel, direction, True), "limit": limit}

@app.get("/conversations/latest", operation_id="getLatestConversations", tags=["Communications"])
def get_latest_conversations(channel: str | None = Query(None, pattern="^(whatsapp|email|voice)$"), limit: int = Query(20, ge=1, le=100), _: None = Depends(require_api_key)):
    return {"conversations": reporting.conversations(limit, channel), "limit": limit}

@app.get("/activities/today", operation_id="getTodaysActivities", tags=["Reports"])
def get_todays_activities(limit: int = Query(50, ge=1, le=100), _: None = Depends(require_api_key)):
    return {"activities": reporting.activities_today(limit), "limit": limit}