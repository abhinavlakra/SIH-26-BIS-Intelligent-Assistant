"""Retrieval over the BIS *services* knowledge base.

Separate from the catalogue on purpose. The catalogue answers "which standard
applies"; this answers "how do I get certified", "where do I test it", "is my
hallmark genuine", "how do I complain". Mixing them into one index would let a
service FAQ outrank a real standard for a product query, which is the wrong
trade in the surface that matters most.

There are a few dozen entries, so the whole thing is an in-memory cosine scan
against the same local embedding model the catalogue uses. No Chroma
collection, no second store — at this size an index would cost more than it
saves.
"""

import re

from app import bis_services
from app.models import ServiceAnswer
from rag.embeddings import embed_query, embed_texts

# Questions whose *intent* is a BIS service, whatever product noun they carry.
#
# This exists because similarity alone gets it wrong in the case that matters:
# "which laboratory can test my drinking water sample" is dominated by
# "drinking water" and retrieves IS 3025 and IS 17614 — water *test-method*
# standards — so the user asking where to get something tested is handed a
# reading list. The product noun is the loudest token but the question is not
# about the product.
#
# An explicit, inspectable router beats trying to tune that out of the
# embedding, and it fails safe: no match simply means the catalogue answers.
_SERVICE_INTENT = re.compile(
    r"""
      \b(?:lab|labs|laboratory|laboratories)\b
    | \bwhere\s+(?:can|do|should)\s+i\s+(?:get|have|send)\b
    | \b(?:get|got|have)\s+(?:it|this|my|the)\s+\w+\s*tested\b
    | \btest(?:ing)?\s+(?:centre|center|facility|facilities|house)\b
    | \bcomplain(?:t|ts|ing)?\b | \bgrievance\b | \bredressal\b
    | \b(?:fake|counterfeit|duplicate|genuine|authentic)\b
    | \bhallmark\w*\b | \bhuid\b | \bcarat\b | \bkarat\b | \bjewell?er\w*\b
    | \bbis\s*care\b
    | \bverify\b | \bverification\b
    | \bhow\s+do\s+i\s+(?:apply|register|get\s+(?:a\s+)?(?:licence|license|certified|registration))\b
    | \b(?:isi|crs|fmcs)\s+(?:mark|licence|license|registration)\b
    | \bstandards?\s+club\b
    | \b(?:buy|purchase|download|obtain)\s+(?:a\s+)?(?:copy|standard)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def looks_like_service_question(query: str) -> bool:
    """True when the question is about a BIS service rather than a standard."""
    return bool(_SERVICE_INTENT.search(query or ""))

# The services base is small and its language is close to how people ask, so
# scores run higher than catalogue retrieval. This floor was picked the same
# way: above what unrelated questions score, below what real ones do.
SERVICE_FLOOR = 0.45

_VECTORS: list[list[float]] | None = None


def _vectors() -> list[list[float]]:
    """Embeddings for every entry, computed once per process."""
    global _VECTORS
    if _VECTORS is None:
        _VECTORS = embed_texts([e.embedding_text() for e in bis_services.ALL_ENTRIES])
    return _VECTORS


def _cosine(a: list[float], b: list[float]) -> float:
    # Both sides come from the same sentence-transformers model, which returns
    # normalised vectors, so the dot product is already the cosine.
    return sum(x * y for x, y in zip(a, b))


def search(
    query: str, topic: str = "", top_k: int = 3, floor: float | None = None
) -> list[tuple[bis_services.ServiceEntry, float]]:
    """Best-matching service entries, most relevant first."""
    if not query.strip():
        return []

    cutoff = SERVICE_FLOOR if floor is None else floor
    embedding = embed_query(query)
    vectors = _vectors()

    scored: list[tuple[bis_services.ServiceEntry, float]] = []
    for entry, vector in zip(bis_services.ALL_ENTRIES, vectors):
        if topic and entry.topic != topic:
            continue
        score = max(0.0, min(1.0, _cosine(embedding, vector)))
        if score >= cutoff:
            scored.append((entry, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]


def to_answer(entry: bis_services.ServiceEntry, score: float) -> ServiceAnswer:
    return ServiceAnswer(
        key=entry.key,
        topic=entry.topic,
        topic_label=bis_services.TOPIC_LABELS.get(entry.topic, entry.topic),
        question=entry.question,
        answer=entry.answer,
        source=entry.source,
        score=round(score, 3),
    )


def format_context(hits: list[tuple[bis_services.ServiceEntry, float]]) -> str:
    """Render hits as a grounding block for the LLM, sources included."""
    return "\n\n".join(
        f"[{entry.topic}] {entry.question}\n{entry.answer}\nSource: {entry.source}"
        for entry, _ in hits
    )
