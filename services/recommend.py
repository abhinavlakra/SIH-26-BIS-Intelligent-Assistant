"""Recommendation engine: product/procurement description -> applicable IS codes.

This is the differentiator over a plain RAG chatbot. Retrieval finds candidate
standards semantically; the reference graph then pulls in the standards those
candidates normatively require; a single batched LLM call explains *why* each
one applies and how confident that mapping is. Without an LLM key it still
ranks, expands and explains via keyword overlap, so the endpoint is never dead.

Each recommendation also carries its **certification obligation**. That is what
turns a list of search results into something a user can act on: knowing that
IS 4151 applies to your helmet matters far less than knowing that it is under a
Quality Control Order and the ISI mark is therefore compulsory before sale.
"""

import json
import re

from app.models import Recommendation, RecommendResponse, Standard
from app.rag.llm import LLMUnavailable, get_provider
from app.rag.retriever import RECOMMEND_FLOOR, expand_related, search
from app.services import language

SYSTEM_PROMPT = """You map products and procurement specifications to the \
Indian Standards (IS) that apply to them.

You are given a product description and candidate catalogue entries retrieved \
from the Bureau of Indian Standards catalogue. For each candidate, judge how \
directly it applies to the described product.

Return ONLY a JSON object, no prose, in exactly this shape:
{"items": [{"is_number": "<exact IS number from the candidate>", "why": \
"<one sentence, max 25 words, on what aspect of the product this standard \
governs>", "confidence": <number between 0 and 1>}]}

Rules:
- Use only the IS numbers given to you; never invent one.
- Include every candidate, even low-confidence ones (score them low).
- Confidence near 1.0 means the standard clearly governs this product; near \
0.2 means it is only tangentially related.
- Where a candidate is marked as having mandatory certification, say so in the \
"why" — that obligation matters more to the reader than the technical scope.
- A candidate included as a normative reference of another standard is still \
applicable; explain the dependency rather than scoring it down for it."""


def _extract_json_object(text: str) -> dict | None:
    """Pull the first balanced JSON object out of a model response."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : index + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _heuristic_why(standard: Standard, description: str) -> str:
    """Explanation used when no LLM is available: surface the lexical overlap."""
    words = {w for w in re.findall(r"[a-z]{4,}", description.lower())}
    matched = [
        keyword
        for keyword in standard.keywords
        if any(word in keyword.lower() for word in words)
    ]
    if matched:
        return (
            f"Catalogue scope overlaps '{', '.join(matched[:3])}' "
            f"in your description — review the scope for applicability."
        )
    return (
        f"Semantically close to the described product in the "
        f"{standard.sector or 'listed'} sector — review the scope for applicability."
    )


def _candidate_block(candidates: list[tuple[Standard, float, str]]) -> str:
    blocks = []
    for standard, score, via in candidates:
        lines = [
            f"IS number: {standard.is_number}",
            f"Title: {standard.title}",
            f"Scope: {standard.scope}",
            f"Sector: {standard.sector}",
            f"Retrieval similarity: {score:.2f}",
        ]
        if via != "semantic":
            lines.append(f"Included because {via} normatively references it.")
        if standard.qco_mandatory:
            lines.append(f"Certification is mandatory under: {standard.qco_name}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def recommend(
    description: str,
    top_n: int | None = None,
    lang: str = "en",
    include_related: bool = True,
) -> RecommendResponse:
    provider = get_provider()
    query, note = language.prepare_query(description, lang)
    hits = search(query, top_k=top_n, floor=RECOMMEND_FLOOR)

    if not hits:
        return RecommendResponse(
            description=description,
            recommendations=[],
            used_model=f"{provider.name} ({note})" if note else provider.name,
        )

    # Direct semantic hits first, then one hop along the reference graph. The
    # graph is what a vector index cannot do: a query about an apartment block
    # retrieves IS 456, and IS 456 pulls in the cement, aggregate and rebar
    # standards that no embedding of the description would ever surface.
    candidates: list[tuple[Standard, float, str]] = [(s, score, "semantic") for s, score in hits]
    if include_related:
        candidates.extend(expand_related(hits))

    rationales: dict[str, dict] = {}
    used_model = provider.name

    if provider.available:
        user_prompt = (
            f"Product / procurement description:\n{description}\n\n"
            f"Candidate catalogue entries:\n\n{_candidate_block(candidates)}"
        )
        try:
            raw = provider.generate(SYSTEM_PROMPT + language.answer_instruction(lang), user_prompt)
            parsed = _extract_json_object(raw)
            for item in (parsed or {}).get("items", []):
                is_number = str(item.get("is_number", "")).strip()
                if is_number:
                    rationales[is_number] = item
            if not rationales:
                used_model = f"{provider.name} (unparseable response, used heuristics)"
        except LLMUnavailable as exc:
            used_model = f"heuristic fallback ({exc})"

    recommendations = []
    for standard, score, via in candidates:
        item = rationales.get(standard.is_number)
        if item:
            why = str(item.get("why") or "").strip() or _heuristic_why(standard, description)
            try:
                confidence = float(item.get("confidence", score))
            except (TypeError, ValueError):
                confidence = score
        else:
            why = _heuristic_why(standard, description)
            confidence = score

        if via != "semantic":
            why = f"{why} Pulled in as a normative reference of {via}."

        recommendations.append(
            Recommendation(
                is_number=standard.is_number,
                title=standard.title,
                sector=standard.sector,
                status=standard.status,
                why=why,
                confidence=round(max(0.0, min(1.0, confidence)), 3),
                qco_mandatory=standard.qco_mandatory,
                qco_name=standard.qco_name,
                certification_scheme=standard.certification_scheme,
                via=via,
                normative_refs=standard.normative_refs,
            )
        )

    # Mandatory standards sort first: a compliance obligation outranks a
    # marginally better similarity score in usefulness to the reader.
    recommendations.sort(key=lambda r: (r.qco_mandatory, r.confidence), reverse=True)
    if note:
        used_model = f"{used_model} ({note})"
    return RecommendResponse(
        description=description,
        recommendations=recommendations,
        used_model=used_model,
    )
