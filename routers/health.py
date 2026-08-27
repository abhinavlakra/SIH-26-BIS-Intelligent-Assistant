"""Health, statistics and query analytics endpoints."""

from fastapi import APIRouter, Query

from app import bis_reference as bis
from app.config import get_settings
from app.models import AnalyticsResponse, HealthResponse, StatsResponse
from app.rag import vectorstore
from app.rag.llm import get_provider
from app.services import analytics

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse, summary="Liveness and index readiness")
def get_health() -> HealthResponse:
    indexed = vectorstore.count()
    return HealthResponse(
        status="ok",
        index_ready=indexed > 0,
        indexed_standards=indexed,
    )


@router.get("/stats", response_model=StatsResponse, summary="Corpus and model configuration")
def get_stats() -> StatsResponse:
    """Handy during a demo: proves what is indexed and which model is answering."""
    settings = get_settings()
    provider = get_provider()
    standards = vectorstore.all_standards()
    departments = {s.department_code() for s in standards if s.department_code()}

    return StatsResponse(
        indexed_standards=vectorstore.count(),
        sectors=vectorstore.sector_counts(),
        embedding_model=settings.embedding_model,
        llm_model=provider.name,
        llm_enabled=provider.available,
        llm_endpoint=settings.anthropic_base_url.strip() or "https://api.anthropic.com (direct)",
        corpus_path=str(settings.active_corpus()),
        catalogue_total=bis.TOTAL_PUBLISHED_STANDARDS,
        departments_covered=len(departments),
        departments_total=len(bis.DEPARTMENTS),
        qco_mandatory=sum(1 for s in standards if s.qco_mandatory),
    )


@router.get(
    "/analytics/queries",
    response_model=AnalyticsResponse,
    summary="What users have asked, and what the catalogue could not answer",
)
def get_analytics(limit: int = Query(10, ge=1, le=50)) -> AnalyticsResponse:
    """Query telemetry.

    `unanswered` is the interesting field: queries that matched nothing are a
    standards-development gap signal for BIS, generated from real demand rather
    than from a survey.

    Only the query text, timing and outcome are stored — no IP address, no user
    identifier, no session token.
    """
    return analytics.summary(limit=limit)
