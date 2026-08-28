"""Chat endpoint — grounded Q&A over the indexed catalogue."""

import time

from fastapi import APIRouter, HTTPException

from app.models import ChatRequest, ChatResponse
from rag import vectorstore
from services import analytics, chat

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse, summary="Ask a question about Indian Standards")
def post_chat(request: ChatRequest) -> ChatResponse:
    """Answer a natural-language question, citing the standards used.

    Try: *"What standard covers drinking water quality?"*
    Set `lang: "hi"` to ask and be answered in Hindi.
    """
    if vectorstore.count() == 0:
        raise HTTPException(
            status_code=503,
            detail="Index is empty. Build it with: python -m app.ingestion.build_index",
        )

    started = time.perf_counter()
    response = chat.answer(
        request.query,
        top_k=request.top_k,
        sector=request.sector,
        lang=request.lang,
    )
    analytics.record(
        query=request.query,
        endpoint="chat",
        grounded=response.grounded,
        top_score=response.citations[0].score if response.citations else 0.0,
        latency_ms=int((time.perf_counter() - started) * 1000),
        used_model=response.used_model,
    )
    return response
