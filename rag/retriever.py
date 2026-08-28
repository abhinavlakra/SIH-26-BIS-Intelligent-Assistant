"""Retrieval over the indexed BIS catalogue.

Semantic search is the base signal. Two cheap, fully local re-rankers sit on top
of it, because pure cosine similarity confuses *subject* with *product*: for
"stainless steel water bottle" it ranks IS 14543 (packaged drinking **water**)
above IS 5522 (steel for utensils) — lexically close, but the product is the
bottle, not the water.

    final = cosine · (1 + 0.25·lexical + 0.15·ICS-affinity)

The re-rankers *modulate* the semantic score rather than being added to it, so
neutral evidence leaves a score exactly where it was. That is what keeps the two
calibrated relevance floors valid — an additive blend lifts every score by a
constant and quietly lets off-topic queries back over the floor.

`lexical` is the IDF-weighted fraction of the query covered by a candidate's
title and keywords. `ICS-affinity` exploits the fact that ICS is a
*hierarchical* code, so comparing leading segments encodes real domain distance:
77.140.* (steel products) vs 13.060.* (water quality) diverge at the first
segment and are penalised accordingly.

Everything here stays offline — no service, no API, no extra model.
"""

import math
import re
from collections import Counter

from app.config import get_settings
from app.models import Standard
from app.rag import vectorstore
from app.rag.embeddings import embed_query

# Below this similarity nothing in the catalogue is genuinely related to the
# query. Answering anyway is how RAG systems end up hallucinating.
#
# RE-CALIBRATED for the full 24,324-record catalogue collected from the BIS
# portal (`python -m app.ingestion.calibrate` prints the distributions):
#
#     relevant queries      0.677 - 1.000
#     product descriptions  0.488 - 0.797
#     domain-adjacent       0.383 - 0.490
#     clearly off-topic     0.142 - 0.290
#
# Two things moved these, and both are structural rather than incidental:
#
# 1. Scale. 24k documents give far more chances for a spurious near-match than
#    95 did, so every band widened downward.
# 2. Text. The BIS portal API publishes no scope text, so most records are
#    embedded from their title alone. Scores compress: the LED-bulb product
#    description retrieves exactly the right standards (IS 16103, IS 16101,
#    IS 16102) and still only scores 0.488, where a curated record with scope
#    text scores 0.95 for an equivalent query.
#
# The history is worth keeping: 51 records -> floors 0.35/0.15; 95 records ->
# 0.45/0.35; 24k -> the values below. Never carry these over a corpus change.
RELEVANCE_FLOOR = 0.58

# The recommendation endpoint deliberately uses a lower floor, and at this scale
# it sits *below* the domain-adjacent band on purpose. Its input is a product
# description, not a question: returning a weak candidate whose confidence meter
# visibly reads "Review needed" is more useful than refusing a real product. Chat
# is the surface that must refuse; recommend is the surface that must not
# stonewall. It still clears the clearly-off-topic ceiling (0.290) with margin.
RECOMMEND_FLOOR = 0.42

# Blend weights. Semantic stays dominant: the re-rankers break ties and correct
# subject/product confusion, they do not replace the embedding.
W_SEMANTIC = 0.60
W_LEXICAL = 0.25
W_ICS = 0.15

# Words that carry no retrieval signal in a product description.
_STOPWORDS = frozenset(
    """
    a an and are as at be by for from has have how i in is it its manufacture
    manufacturing make making my of on or our that the their they this to use
    used using want we what which who will with you your need require required
    small large new sale retail company business unit plant factory produce
    """.split()
)


def _stem(word: str) -> str:
    """Fold regular English plurals so 'bottles' matches the keyword 'bottle'.

    Not a real stemmer — deliberately. Product descriptions are plural
    ("we make water bottles") while catalogue keywords are singular
    ("water bottle"), and that single mismatch was enough to lose the lexical
    signal entirely. Anything more aggressive starts mangling technical terms.
    """
    if len(word) <= 3 or word.endswith(("ss", "us", "is")):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("ches", "shes", "xes", "zes", "ses")):
        return word[:-2]
    if word.endswith("s"):
        return word[:-1]
    return word


def _tokens(text: str) -> list[str]:
    return [
        _stem(w)
        for w in re.findall(r"[a-z0-9]{3,}", text.lower())
        if w not in _STOPWORDS
    ]


def _lexical_scores(query: str, candidates: list[Standard]) -> dict[str, float]:
    """IDF-weighted fraction of the query that each candidate's text covers.

    Deliberately *absolute*, not normalised against the best candidate. An
    earlier version divided by the peak score, which handed the top candidate a
    full 1.0 on this axis even when the overlap was meaningless — enough to lift
    an off-topic query back over the relevance floor. Query coverage keeps a
    weak match weak no matter what it is competing against.

    Scored over the candidate set only (a few dozen documents), which is all
    re-ranking needs and avoids maintaining a second index.
    """
    query_terms = set(_tokens(query))
    if not query_terms or not candidates:
        return {}

    docs = {
        s.is_number: set(_tokens(f"{s.title} {' '.join(s.keywords)} {s.sector}"))
        for s in candidates
    }
    n = len(docs)

    df = Counter()
    for terms in docs.values():
        for term in query_terms:
            if term in terms:
                df[term] += 1

    # Rare terms across the candidate set discriminate; ubiquitous ones do not.
    idf = {
        term: math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
        for term in query_terms
    }
    total = sum(idf.values()) or 1.0

    return {
        is_number: sum(idf[t] for t in query_terms if t in terms) / total
        for is_number, terms in docs.items()
    }


def _ics_scores(candidates: list[tuple[Standard, float]]) -> dict[str, float]:
    """Affinity between each candidate's ICS codes and the top semantic hit's.

    The best semantic match defines the subject area; candidates classified far
    from it in the ICS hierarchy are pushed down. Standards with no ICS code get
    a neutral 0.5 rather than a penalty — absence of data is not evidence.
    """
    if not candidates:
        return {}

    anchor_codes = [c for standard, _ in candidates[:2] for c in standard.ics_codes]
    if not anchor_codes:
        return {standard.is_number: 0.5 for standard, _ in candidates}

    def affinity(code: str) -> float:
        parts = code.split(".")
        best = 0.0
        for anchor in anchor_codes:
            anchor_parts = anchor.split(".")
            shared = 0
            for left, right in zip(parts, anchor_parts):
                if left != right:
                    break
                shared += 1
            # 0 segments shared -> 0.0, 1 -> 0.5, 2 -> 0.8, 3+ -> 1.0
            best = max(best, {0: 0.0, 1: 0.5, 2: 0.8}.get(shared, 1.0))
        return best

    scores: dict[str, float] = {}
    for standard, _ in candidates:
        if not standard.ics_codes:
            scores[standard.is_number] = 0.5
        else:
            scores[standard.is_number] = max(affinity(c) for c in standard.ics_codes)
    return scores


def _rerank(
    query: str,
    hits: list[tuple[Standard, float]],
) -> list[tuple[Standard, float]]:
    """Modulate the semantic score by the lexical and ICS signals.

    Multiplicative, not additive, and centred so that neutral evidence leaves a
    score untouched. That matters: an additive blend raises the floor of every
    score by a constant, which would silently invalidate the two calibrated
    relevance floors and let noise through. Here the semantic score remains the
    scale, and the re-rankers can move it within roughly 0.6x-1.4x.
    """
    if len(hits) < 2:
        return hits

    candidates = [standard for standard, _ in hits]
    lexical = _lexical_scores(query, candidates)
    ics = _ics_scores(hits)

    blended = []
    for standard, score in hits:
        lex = lexical.get(standard.is_number, 0.0)
        # ICS is centred on 0.5 (neutral / unknown), so map it to [-1, +1].
        ics_delta = (ics.get(standard.is_number, 0.5) - 0.5) * 2
        boost = 1.0 + W_LEXICAL * lex + W_ICS * ics_delta
        blended.append((standard, max(0.0, min(1.0, score * boost))))

    blended.sort(key=lambda pair: pair[1], reverse=True)
    return blended


def search(
    query: str,
    top_k: int | None = None,
    sector: str | None = None,
    floor: float | None = None,
    hybrid: bool = True,
) -> list[tuple[Standard, float]]:
    """Top standards for a free-text query, most relevant first.

    Over-fetches before re-ranking so the blend has room to reorder, then trims
    back to `top_k`. The floor is applied to the *blended* score.
    """
    settings = get_settings()
    k = top_k or settings.default_top_k
    where = {"sector": sector} if sector else None
    cutoff = RELEVANCE_FLOOR if floor is None else floor

    # Re-ranking can only promote what retrieval returned, so widen the pool.
    fetch = k * 3 if hybrid else k
    hits = vectorstore.query(embed_query(query), top_k=fetch, where=where)

    if hybrid:
        hits = _rerank(query, hits)

    return [(standard, score) for standard, score in hits if score >= cutoff][:k]


def expand_related(
    hits: list[tuple[Standard, float]],
    limit: int = 4,
    decay: float = 0.55,
) -> list[tuple[Standard, float, str]]:
    """Walk one hop along normative references and test methods.

    This is what a semantic index alone cannot do. A query about concrete design
    retrieves IS 456; IS 456 normatively requires IS 269 (cement), IS 383
    (aggregate) and IS 1786 (reinforcement) — none of which an embedding of
    "earthquake resistant apartment block" would ever surface on its own.

    Returns `(standard, score, via)` where `via` is the IS number that pulled it
    in. Neighbours inherit a decayed score so they always rank below a direct
    semantic hit of comparable strength.
    """
    already = {standard.is_number for standard, _ in hits}
    found: list[tuple[Standard, float, str]] = []

    for standard, score in hits:
        for ref in standard.related():
            if len(found) >= limit:
                return found
            if ref in already:
                continue
            neighbour = vectorstore.get_one(ref)
            # A reference we do not have indexed is not an error — the corpus is
            # a subset of the catalogue. It is reported separately as a gap.
            if neighbour is None:
                continue
            already.add(neighbour.is_number)
            found.append((neighbour, round(score * decay, 3), standard.is_number))

    return found


def format_context(hits: list[tuple[Standard, float]]) -> str:
    """Render hits as the grounding block handed to the LLM."""
    blocks = []
    for standard, score in hits:
        lines = [
            f"[{standard.is_number}] {standard.title}",
            f"Scope: {standard.scope}" if standard.scope else "",
            f"Sector: {standard.sector}" if standard.sector else "",
            f"Committee: {standard.technical_committee}" if standard.technical_committee else "",
            f"Status: {standard.status}",
        ]
        if standard.qco_mandatory:
            lines.append(
                f"Certification: MANDATORY under {standard.qco_name}"
                if standard.qco_name
                else "Certification: mandatory under a Quality Control Order"
            )
        if standard.normative_refs:
            lines.append("Normative references: " + ", ".join(standard.normative_refs))
        lines.append(f"Relevance: {score:.2f}")
        blocks.append("\n".join(line for line in lines if line))
    return "\n\n".join(blocks)
