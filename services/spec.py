"""Tender / specification analysis.

Procurement disputes are caused by incomplete specifications and outdated
standard references. This service attacks both, and extends SIH26107's
"recommend applicable standards based on product descriptions" from a typed
sentence to a whole tender document.

Given a tender document or a specification, per line item it:

- recommends the Indian Standards that apply (semantic + graph, per line, so
  attribution survives — "clause 4.2 -> IS 2062", not one flat list);
- extracts every IS number already cited in the text and checks whether it is
  the current edition;
- reports normative references required by the cited standards but missing from
  the specification;
- flags which of the applicable standards carry mandatory certification.

Embedding a whole document as one vector produces mush, so the text is split
into line items and retrieved per line, then unioned.
"""

import re

from app.models import (
    CitedStandard,
    Recommendation,
    SpecAnalyzeResponse,
    SpecLineResult,
    SpecSource,
    Standard,
)
from app.services import pdfdoc
from app.rag import vectorstore
from app.rag.llm import get_provider
from app.rag.retriever import RECOMMEND_FLOOR, search
from app.rag.vectorstore import _normalise_ref

# Matches the ways a tender writes a standard reference:
#   IS 456, IS 456:2000, IS 1893 (Part 1) : 2016, IS/ISO 9001:2015
_IS_PATTERN = re.compile(
    r"\bIS(?:/(?:ISO|IEC|ISO/IEC))?\s*\d{2,5}"          # IS 456 / IS/ISO 9001
    r"(?:\s*\(\s*Part\s*[\w/\s]+?\s*\))?"                # optional (Part 1/Sec 1)
    r"(?:\s*:\s*\d{4})?",                                 # optional :2000
    re.IGNORECASE,
)

# Lines shorter than this are headings, numbering or noise, not line items.
_MIN_LINE_CHARS = 15

MAX_LINES = 40

# A PDF tender is far longer than a pasted snippet, so it gets a bigger cap.
# Each line item costs one vector search (~10 ms), so this is a latency budget
# as much as a size limit.
MAX_PDF_LINES = 120


def _split_lines(text: str, limit: int) -> list[tuple[int, str]]:
    """Line items worth analysing, with their original 1-based line numbers.

    This is the *pasted text* path, where the author's own line breaks are the
    line items and should be trusted. PDF text needs reflowing first — that
    lives in `services/pdfdoc.py`, because a PDF's line breaks are visual
    rather than logical.
    """
    out: list[tuple[int, str]] = []
    for index, raw in enumerate(text.splitlines(), start=1):
        # Drop leading list markers: "1.", "4.2)", "-", "*", "(a)"
        line = re.sub(r"^\s*(?:[-*•]|\(?[a-z0-9]{1,4}[.)])\s*", "", raw).strip()
        if len(line) < _MIN_LINE_CHARS:
            continue
        out.append((index, line))
        if len(out) >= limit:
            break
    return out


def extract_citations(text: str) -> list[str]:
    """Every IS reference appearing verbatim in the text, in order, de-duplicated."""
    seen: dict[str, None] = {}
    for match in _IS_PATTERN.finditer(text):
        # Collapse internal whitespace so 'IS  456 : 2000' reads as one token.
        cited = re.sub(r"\s+", " ", match.group()).strip()
        cited = re.sub(r"\s*:\s*", ":", cited)
        seen.setdefault(cited, None)
    return list(seen)


_FAMILY = re.compile(
    r"^\s*(IS(?:/(?:ISO/IEC|ISO|IEC))?)\s*(\d+)"      # IS 1893 / IS/ISO 9001
    r"(?:\s*\(\s*Part\s*([\w/\s]+?)\s*\))?",           # optional (Part 1/Sec 1)
    re.IGNORECASE,
)


def _family_key(is_number: str) -> tuple[str, str, str] | None:
    """Split a reference into (prefix, number, part) ignoring the year.

    'IS 1893:2002' -> ('IS', '1893', '')
    'IS 1893 (Part 1):2016' -> ('IS', '1893', 'PART1')
    """
    match = _FAMILY.match(is_number or "")
    if match is None:
        return None
    prefix, number, part = match.groups()
    return (
        prefix.upper().replace(" ", ""),
        number,
        "".join((part or "").split()).upper(),
    )


# Standards grouped by (prefix, number), so a citation that omits the year or
# the part can still find its family. Rebuilt whenever the corpus changes: the
# dict returned by `vectorstore.by_reference()` is replaced on invalidation, so
# its identity is a reliable cache key. A linear scan per citation was fine at
# 95 records and is not at 24,000.
_FAMILY_CACHE: tuple[int, dict[tuple[str, str], list[Standard]]] | None = None


def _families() -> dict[tuple[str, str], list[Standard]]:
    global _FAMILY_CACHE
    index = vectorstore.by_reference()
    if _FAMILY_CACHE is not None and _FAMILY_CACHE[0] == id(index):
        return _FAMILY_CACHE[1]

    grouped: dict[tuple[str, str], list[Standard]] = {}
    for standard in index.values():
        key = _family_key(standard.is_number)
        if key is not None:
            grouped.setdefault((key[0], key[1]), []).append(standard)
    _FAMILY_CACHE = (id(index), grouped)
    return grouped


def _resolve(cited: str) -> Standard | None:
    """Find the indexed standard a citation refers to.

    Tolerates the two ways tenders under-specify a reference, both of which are
    the point of this feature:

    - a stale year — 'IS 1893:2002' must still reach 'IS 1893 (Part 1):2016'
      so we can report that it has moved on;
    - a missing Part — a tender citing bare 'IS 1893' is ambiguous about which
      part applies, so match the family and let the currency check flag it.

    A citation that *does* name a Part only matches that same Part.
    """
    exact = vectorstore.get_one(cited)
    if exact is not None:
        return exact

    wanted = _family_key(cited)
    if wanted is None:
        return None
    prefix, number, part = wanted

    family = _families().get((prefix, number), [])
    if part:
        family = [s for s in family if (_family_key(s.is_number) or ("", "", ""))[2] == part]
    if not family:
        return None
    # Prefer the most recent edition — that is the one the user should be citing.
    return max(family, key=lambda s: s.year or 0)


def _cited_standard(cited: str) -> CitedStandard:
    resolved = _resolve(cited)
    if resolved is None:
        return CitedStandard(cited_as=cited, in_corpus=False)

    cited_year = re.search(r":\s*(\d{4})", cited)
    current = True
    superseded_by = ""

    if resolved.superseded_by:
        current = False
        superseded_by = resolved.superseded_by
    elif cited_year and resolved.year:
        # The tender names an older edition than the one we hold.
        if int(cited_year.group(1)) < resolved.year:
            current = False
            superseded_by = resolved.is_number
    elif not cited_year:
        # No year at all is a real defect in a tender: it is ambiguous about
        # which edition applies, which is exactly how disputes start.
        current = False
        superseded_by = resolved.is_number

    return CitedStandard(
        cited_as=cited,
        resolved=resolved.is_number,
        in_corpus=True,
        current=current,
        superseded_by=superseded_by,
        amendment_count=resolved.amendment_count,
    )


def _as_recommendation(standard: Standard, score: float, via: str) -> Recommendation:
    return Recommendation(
        is_number=standard.is_number,
        title=standard.title,
        sector=standard.sector,
        status=standard.status,
        why=(
            f"Matches this line item in the {standard.sector or 'catalogue'} sector."
            if via == "semantic"
            else f"Normatively referenced by {via}."
        ),
        confidence=round(score, 3),
        qco_mandatory=standard.qco_mandatory,
        qco_name=standard.qco_name,
        certification_scheme=standard.certification_scheme,
        via=via,
        normative_refs=standard.normative_refs,
    )


def analyze(text: str, max_lines: int | None = None) -> SpecAnalyzeResponse:
    """Analyse pasted specification text."""
    limit = max_lines or MAX_LINES
    items = [(line_no, None, line) for line_no, line in _split_lines(text, limit)]
    return _run(text, items, SpecSource(kind="text"))


def analyze_pdf(
    data: bytes, filename: str = "", max_lines: int | None = None
) -> SpecAnalyzeResponse:
    """Analyse an uploaded tender PDF.

    The bytes are parsed in memory and never written to disk: tender documents
    are frequently confidential, and often pre-award.
    """
    limit = max_lines or MAX_PDF_LINES
    parsed = pdfdoc.parse(data, limit)
    items = [(line.line_no, line.page, line.text) for line in parsed.lines]
    return _run(
        parsed.text,
        items,
        SpecSource(
            kind="pdf",
            filename=filename,
            pages=parsed.pages,
            truncated=parsed.truncated,
        ),
    )


def _run(
    text: str,
    items: list[tuple[int, int | None, str]],
    source: SpecSource,
) -> SpecAnalyzeResponse:
    """Shared analysis over already-segmented line items."""
    provider = get_provider()

    line_results: list[SpecLineResult] = []
    matched: dict[str, Recommendation] = {}

    for line_no, page, line in items:
        hits = search(line, top_k=3, floor=RECOMMEND_FLOOR)
        matches = [_as_recommendation(s, score, "semantic") for s, score in hits]
        line_results.append(
            SpecLineResult(line_no=line_no, page=page, text=line, matches=matches)
        )
        for item in matches:
            # Keep the strongest evidence for any standard seen more than once.
            if item.is_number not in matched or item.confidence > matched[item.is_number].confidence:
                matched[item.is_number] = item

    cited = [_cited_standard(c) for c in extract_citations(text)]
    outdated = [c for c in cited if c.in_corpus and not c.current]

    # What the cited standards normatively require but the spec never mentions.
    cited_keys = {_normalise_ref(c.resolved or c.cited_as) for c in cited}
    missing: dict[str, None] = {}
    for entry in cited:
        if not entry.in_corpus:
            continue
        resolved = vectorstore.get_one(entry.resolved)
        if resolved is None:
            continue
        for ref in resolved.normative_refs:
            if _normalise_ref(ref) in cited_keys:
                continue
            # Never advise adding a standard that is itself superseded or
            # withdrawn. This feature exists to stop outdated citations; it
            # must not create them.
            neighbour = vectorstore.get_one(ref)
            if neighbour is not None and (
                neighbour.superseded_by or neighbour.status != "active"
            ):
                continue
            missing.setdefault(ref, None)

    mandatory = sorted(
        {item.is_number for item in matched.values() if item.qco_mandatory}
        | {
            standard.is_number
            for entry in cited
            if entry.in_corpus and (standard := vectorstore.get_one(entry.resolved))
            and standard.qco_mandatory
        }
    )

    return SpecAnalyzeResponse(
        line_count=len(items),
        lines=line_results,
        cited_standards=cited,
        missing_normative_refs=list(missing),
        outdated_citations=outdated,
        mandatory_standards=mandatory,
        completeness=_completeness(items, cited, outdated, missing),
        used_model=provider.name,
        source=source,
    )


def _completeness(
    lines: list[tuple[int, int | None, str]],
    cited: list[CitedStandard],
    outdated: list[CitedStandard],
    missing: dict[str, None],
) -> float:
    """A blunt 0-1 score for how well-specified the document is.

    Three equally weighted components: does it cite standards at all, are the
    citations current, and does it carry the normative references its own
    citations require. Deliberately simple — it is a prompt to look, not a
    verdict, and the panel below it shows every input.

    All three collapse to zero when the document cites nothing. An earlier
    version defaulted currency and reference-completeness to 1.0 in that case,
    on the reasoning that there was nothing to find wrong — which scored a
    tender citing *no standards at all* at 0.67, against 0.75 for a properly
    specified one. Absence of evidence was reading as evidence of quality.
    """
    if not lines or not cited:
        return 0.0

    cites_anything = 1.0
    currency = 1.0 - len(outdated) / len(cited)
    completeness_of_refs = 1.0 / (1.0 + len(missing))
    return round((cites_anything + currency + completeness_of_refs) / 3, 3)
