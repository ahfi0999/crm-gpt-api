from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query

from app import database
from app.auth import require_api_key
from app.services import leads


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
def get_latest_leads(limit: int = Query(10, ge=1, le=100), _: None = Depends(require_api_key)):
    return {"leads": leads.latest(limit), "limit": limit}


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
