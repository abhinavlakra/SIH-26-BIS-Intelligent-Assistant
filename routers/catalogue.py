"""Catalogue endpoints — browse, inspect, and see what is actually indexed.

These answer the question a user has *before* they ask anything, which the chat
and recommend endpoints structurally cannot: what is in this catalogue, how much
of the real one does it cover, and what does any given standard depend on.
"""

from fastapi import APIRouter, HTTPException, Query

from app import bis_services
from app.models import (
    BrowseResponse,
    CertificationResponse,
    CoverageResponse,
    FacetsResponse,
    ServiceAnswer,
    StandardDetail,
)
from services import catalogue, certification, knowledge

router = APIRouter(tags=["catalogue"])


@router.get(
    "/standards",
    response_model=BrowseResponse,
    summary="Browse and filter the indexed catalogue",
)
def get_standards(
    q: str = Query("", description="Substring match on IS number, title, scope or keywords"),
    department: str = Query("", description="BIS department code, e.g. 'CED'"),
    sector: str = Query("", description="Full sector name, e.g. 'Civil Engineering'"),
    status: str = Query("", description="active | withdrawn | superseded"),
    ics: str = Query("", description="ICS code prefix, e.g. '77' or '77.140'"),
    qco: bool | None = Query(None, description="True: only standards under a Quality Control Order"),
    bis_sector: str = Query("", description="BIS subject sector, e.g. 'Abrasives'"),
    year_from: int | None = Query(None, ge=1900, le=2100),
    year_to: int | None = Query(None, ge=1900, le=2100),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    sort: str = Query("is_number", description="is_number | year | title"),
) -> BrowseResponse:
    """Plain filtered listing. For meaning-based search use /api/chat or /api/recommend."""
    return catalogue.browse(
        q=q,
        department=department,
        sector=sector,
        status=status,
        ics=ics,
        qco=qco,
        bis_sector=bis_sector,
        year_from=year_from,
        year_to=year_to,
        page=page,
        page_size=page_size,
        sort=sort,
    )


@router.get(
    "/facets",
    response_model=FacetsResponse,
    summary="Counts per filter value, for the browse UI",
)
def get_facets() -> FacetsResponse:
    return catalogue.facets()


@router.get(
    "/coverage",
    response_model=CoverageResponse,
    summary="Indexed standards against the real BIS published totals",
)
def get_coverage() -> CoverageResponse:
    """Honest coverage: our count per department beside the official BIS count.

    The denominators come from the BIS *Standard catalogue — July '25* figures
    (23,461 standards across 17 departments, as of June 2025).
    """
    return catalogue.coverage()


# Registered before /standards/{is_number} would otherwise be a problem — it is
# not, because the graph route is a distinct prefix, but keep detail routes last
# so a literal segment is never shadowed by the path parameter.
@router.get(
    "/graph/{is_number:path}",
    summary="Reference-graph neighbourhood of one standard",
)
def get_graph(is_number: str, depth: int = Query(1, ge=1, le=2)) -> dict:
    """Nodes and edges around a standard, for the detail-drawer visualisation.

    Edges are typed: `normative_ref`, `test_method`, `supersedes`,
    `superseded_by`. Nodes carry `in_corpus` — a referenced standard we have not
    indexed is a coverage gap, and the UI shows it as such rather than hiding it.
    """
    result = catalogue.graph(is_number, depth=depth)
    if not result.get("nodes"):
        raise HTTPException(status_code=404, detail=f"{is_number} is not in the index")
    return result


@router.get(
    "/certification/{is_number:path}",
    response_model=CertificationResponse,
    summary="Certification pathway for one standard",
)
def get_certification(is_number: str) -> CertificationResponse:
    """Which BIS conformity assessment scheme applies, and the steps it involves.

    Reports whether certification is *mandatory* (a Quality Control Order names
    the product) or voluntary — the distinction users most often get wrong.
    """
    result = certification.pathway(is_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"{is_number} is not in the index")
    return result


@router.get(
    "/standards/{is_number:path}",
    response_model=StandardDetail,
    summary="One standard with its resolved reference graph",
)
def get_standard(is_number: str) -> StandardDetail:
    result = catalogue.detail(is_number)
    if result is None:
        raise HTTPException(status_code=404, detail=f"{is_number} is not in the index")
    return result


@router.get(
    "/services",
    response_model=list[ServiceAnswer],
    summary="Search BIS service guidance (certification, hallmarking, labs, consumer)",
)
def get_services(
    q: str = Query("", description="Free-text question about a BIS service"),
    topic: str = Query("", description="hallmarking | laboratories | consumer | services"),
) -> list[ServiceAnswer]:
    """Guidance on BIS *services*, separate from the standards catalogue.

    The catalogue answers "which standard applies". This answers "where do I get
    it tested", "is my hallmark genuine", "how do I complain". Every entry
    carries the page on bis.gov.in it came from.

    With no `q`, returns the entries for a topic — which is what the UI uses to
    show what is covered before the user asks anything.
    """
    if not q.strip():
        entries = (
            bis_services.BY_TOPIC.get(topic, ())
            if topic
            else bis_services.ALL_ENTRIES
        )
        return [knowledge.to_answer(entry, 0.0) for entry in entries]

    return [
        knowledge.to_answer(entry, score)
        for entry, score in knowledge.search(q, topic=topic, top_k=5)
    ]
