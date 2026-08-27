"""Recommendation endpoint — product description to applicable IS codes."""

import time

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models import RecommendRequest, RecommendResponse, SpecAnalyzeRequest, SpecAnalyzeResponse
from app.rag import vectorstore
from app.services import analytics
from app.services import pdfdoc
from app.services import recommend as recommend_service
from app.services import spec as spec_service

router = APIRouter(tags=["recommend"])


def _require_index() -> None:
    if vectorstore.count() == 0:
        raise HTTPException(
            status_code=503,
            detail="Index is empty. Build it with: python -m app.ingestion.build_index",
        )


@router.post(
    "/recommend",
    response_model=RecommendResponse,
    summary="Recommend applicable Indian Standards for a product or procurement spec",
)
def post_recommend(request: RecommendRequest) -> RecommendResponse:
    """Map a plain-language product description to the IS codes that apply.

    Each result carries its certification obligation, so a mandatory standard is
    distinguishable from a merely relevant one. With `include_related` the
    reference graph is walked one hop, surfacing standards that the direct
    matches normatively require.

    Try: *"I manufacture stainless steel insulated water bottles for retail sale"*
    """
    _require_index()

    started = time.perf_counter()
    response = recommend_service.recommend(
        request.description,
        top_n=request.top_n,
        lang=request.lang,
        include_related=request.include_related,
    )
    analytics.record(
        query=request.description,
        endpoint="recommend",
        grounded=bool(response.recommendations),
        top_score=response.recommendations[0].confidence if response.recommendations else 0.0,
        latency_ms=int((time.perf_counter() - started) * 1000),
        used_model=response.used_model,
    )
    return response


@router.post(
    "/analyze-spec",
    response_model=SpecAnalyzeResponse,
    summary="Analyse a tender or specification line by line",
)
def post_analyze_spec(request: SpecAnalyzeRequest) -> SpecAnalyzeResponse:
    """Check a procurement specification for the two defects that cause disputes.

    Returns per-line-item standard matches, every IS number the document already
    cites with whether it is the current edition, the normative references those
    citations require but the document omits, and which applicable standards
    carry mandatory certification.
    """
    _require_index()

    started = time.perf_counter()
    response = spec_service.analyze(request.text, max_lines=request.max_lines)
    analytics.record(
        query=request.text[:200],
        endpoint="analyze-spec",
        grounded=bool(response.cited_standards or any(l.matches for l in response.lines)),
        top_score=response.completeness,
        latency_ms=int((time.perf_counter() - started) * 1000),
        used_model=response.used_model,
    )
    return response


@router.post(
    "/analyze-spec/upload",
    response_model=SpecAnalyzeResponse,
    summary="Analyse a tender supplied as a PDF",
)
async def post_analyze_spec_upload(
    file: UploadFile = File(..., description="A digital (text-layer) PDF tender"),
) -> SpecAnalyzeResponse:
    """Same analysis as `/analyze-spec`, but takes the document itself.

    Real tenders are PDFs, so requiring copy-paste was the gap between this
    feature and the way procurement actually works.

    The file is parsed **in memory and never written to disk** — tender
    documents are frequently confidential and often pre-award. Scanned PDFs are
    detected and reported rather than silently returning an empty analysis;
    optical character recognition is not enabled.
    """
    _require_index()

    data = await file.read()
    started = time.perf_counter()
    try:
        response = spec_service.analyze_pdf(data, filename=file.filename or "")
    except pdfdoc.PdfError as exc:
        # These messages are written to be shown to the user as-is.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    analytics.record(
        query=f"[pdf] {file.filename or 'upload'}",
        endpoint="analyze-spec-upload",
        grounded=bool(response.cited_standards or any(l.matches for l in response.lines)),
        top_score=response.completeness,
        latency_ms=int((time.perf_counter() - started) * 1000),
        used_model=response.used_model,
    )
    return response
