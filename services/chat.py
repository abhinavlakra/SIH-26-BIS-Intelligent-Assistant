"""Grounded question answering over the BIS catalogue.

Retrieval always runs locally. Generation is an enhancement: if no key is
configured, or the API call fails, we still return the retrieved standards as
an extractive answer rather than erroring out. That keeps a live demo alive
through an API outage.
"""

from app.models import Citation, ChatResponse, Standard
from rag.llm import LLMUnavailable, get_provider
from rag.retriever import format_context, search
from services import knowledge, language

SERVICES_SYSTEM_PROMPT = """You are ManakMitra, an assistant for the Bureau of \
Indian Standards (BIS). You are answering a question about BIS *services* — \
certification, hallmarking, testing laboratories, or consumer protection — \
rather than about the content of an Indian Standard.

Rules you must follow:
1. Answer ONLY from the reference entries provided in the user message. Do not \
use outside knowledge.
2. Never state a fee, a processing time or a helpline number: those change, and \
the entries deliberately omit them.
3. Where certification is described, keep the distinction between voluntary \
certification and conformity made mandatory by a Quality Control Order.
4. Be concise and practical: 2-5 sentences, plain language, no preamble.
5. Tell the user to confirm the current position on the BIS website, and do not \
invent a URL beyond the sources given."""

SYSTEM_PROMPT = """You are ManakMitra, an assistant for the Bureau of Indian \
Standards (BIS). You help MSMEs, manufacturers and procurement officers \
understand which Indian Standards (IS) apply to them.

Rules you must follow:
1. Answer ONLY from the catalogue entries provided in the user message. Do not \
use outside knowledge about standards, and never invent an IS number.
2. Cite the IS number in square brackets, e.g. [IS 10500:2012], each time you \
rely on an entry.
3. If the provided entries do not answer the question, say plainly that the \
indexed catalogue does not cover it, and name the closest related standards.
4. You have catalogue metadata (title, scope summary, sector, committee) — not \
the full text of the standard. If asked for a specific clause, limit or test \
value, say that it must be read from the standard itself, and point the user to \
the IS number to purchase or consult via the BIS portal.
5. Be concise and practical: 2-5 sentences, plain language, no preamble.
6. If an entry is marked as mandatory under a Quality Control Order, say so \
explicitly — whether certification is compulsory matters more to the reader \
than the technical scope. Never describe certification as mandatory unless the \
entry says it is."""


def _extractive_answer(hits: list[tuple[Standard, float]], reason: str) -> str:
    """Deterministic answer used when no LLM is available."""
    lines = [
        f"{len(hits)} standard(s) in the indexed BIS catalogue match your query:",
        "",
    ]
    for standard, _score in hits:
        summary = standard.scope or standard.title
        lines.append(f"- [{standard.is_number}] {standard.title} — {summary}")
    lines += [
        "",
        f"(Extractive mode — {reason}. These are the retrieved catalogue "
        "entries verbatim rather than a synthesised answer.)",
    ]
    return "\n".join(lines)


def answer(
    query: str,
    top_k: int | None = None,
    sector: str | None = None,
    lang: str = "en",
) -> ChatResponse:
    provider = get_provider()
    # The index is English-only, so a Devanagari question is translated before
    # retrieval rather than embedded as-is. See services/language.py.
    retrieval_query, note = language.prepare_query(query, lang)

    # Route service questions before touching the catalogue. "Which laboratory
    # can test my drinking water sample" otherwise retrieves water test-method
    # standards and answers a question nobody asked — see
    # `knowledge.looks_like_service_question`.
    if knowledge.looks_like_service_question(retrieval_query):
        routed = _service_answer(query, retrieval_query, lang, note, provider)
        if routed.services:
            return routed

    hits = search(retrieval_query, top_k=top_k, sector=sector)

    if not hits:
        # The catalogue holds IS numbers and titles, so it correctly finds
        # nothing for "how do I complain about a fake ISI mark" — a refusal
        # that reads as a failure. Those questions are about BIS *services*,
        # which is a separate, sourced knowledge base.
        return _service_answer(query, retrieval_query, lang, note, provider)

    citations = [
        Citation(
            is_number=standard.is_number,
            title=standard.title,
            scope=standard.scope,
            sector=standard.sector,
            status=standard.status,
            score=round(score, 3),
        )
        for standard, score in hits
    ]

    used_model = provider.name
    if provider.available:
        user_prompt = (
            f"Catalogue entries retrieved for this question:\n\n"
            f"{format_context(hits)}\n\n"
            f"Question: {query}"
        )
        try:
            answer_text = provider.generate(
                SYSTEM_PROMPT + language.answer_instruction(lang), user_prompt
            )
        except LLMUnavailable as exc:
            answer_text = _extractive_answer(hits, str(exc))
            used_model = f"extractive fallback ({exc})"
    else:
        answer_text = _extractive_answer(hits, "no LLM key configured")

    if note:
        answer_text = f"{answer_text}\n\n{note}"

    return ChatResponse(
        answer=answer_text,
        citations=citations,
        used_model=used_model,
        grounded=True,
    )


def _extractive_services(hits) -> str:
    """Deterministic services answer when no LLM is available."""
    lines = []
    for entry, _score in hits:
        lines.append(entry.answer)
        lines.append(f"(Source: {entry.source})")
        lines.append("")
    lines.append(
        "This covers a BIS service rather than the content of an Indian "
        "Standard. Confirm the current position on the BIS website before "
        "relying on it."
    )
    return "\n".join(lines).strip()


def _service_answer(
    query: str,
    retrieval_query: str,
    lang: str,
    note: str,
    provider,
) -> ChatResponse:
    """Answer from the BIS services knowledge base, or decline honestly."""
    hits = knowledge.search(retrieval_query)

    if not hits:
        return ChatResponse(
            answer=(
                "No standard in the indexed BIS catalogue is a close match for "
                "that question, and it does not match the BIS service topics "
                "covered here either (certification, hallmarking, testing "
                "laboratories, consumer protection). Try rephrasing it around "
                "the physical product or material, or browse the catalogue to "
                "see what is covered."
                + (f"\n\n{note}" if note else "")
            ),
            citations=[],
            used_model=provider.name,
            grounded=False,
        )

    used_model = provider.name
    if provider.available:
        user_prompt = (
            f"Reference entries retrieved for this question:\n\n"
            f"{knowledge.format_context(hits)}\n\n"
            f"Question: {query}"
        )
        try:
            answer_text = provider.generate(
                SERVICES_SYSTEM_PROMPT + language.answer_instruction(lang), user_prompt
            )
        except LLMUnavailable as exc:
            answer_text = _extractive_services(hits)
            used_model = f"extractive fallback ({exc})"
    else:
        answer_text = _extractive_services(hits)

    if note:
        answer_text = f"{answer_text}\n\n{note}"

    return ChatResponse(
        answer=answer_text,
        citations=[],
        used_model=used_model,
        # Grounded, but in BIS service documentation rather than in the
        # catalogue — `services` carries the sources instead of `citations`.
        grounded=True,
        services=[knowledge.to_answer(entry, score) for entry, score in hits],
    )
