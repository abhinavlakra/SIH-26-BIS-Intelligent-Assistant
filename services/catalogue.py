"""Browse, facet, coverage and graph views over the indexed catalogue.

None of this touches the LLM. It answers the question a user has before they
ask anything — *"what is actually in here?"* — which the chat and recommend
endpoints cannot.

The corpus is hundreds of records, not millions, so every view here is an
in-process scan over `vectorstore.all_standards()`. That is far simpler than a
second store and fast enough that it never shows up in a request profile.
"""

from app import bis_reference as bis
from app.models import (
    BrowseResponse,
    CoverageResponse,
    DepartmentCoverage,
    FacetCount,
    FacetsResponse,
    RelatedStandard,
    StandardDetail,
    StandardSummary,
)
from rag import vectorstore
from rag.vectorstore import _normalise_ref


def _summary(standard) -> StandardSummary:
    return StandardSummary(
        is_number=standard.is_number,
        title=standard.title,
        sector=standard.sector,
        department_code=standard.department_code(),
        technical_committee=standard.technical_committee,
        status=standard.status,
        year=standard.year,
        ics_codes=standard.ics_codes,
        qco_mandatory=standard.qco_mandatory,
        verification=standard.verification,
        bis_sector=standard.bis_sector,
        bis_subsector=standard.bis_subsector,
    )


def browse(
    q: str = "",
    department: str = "",
    sector: str = "",
    status: str = "",
    ics: str = "",
    qco: bool | None = None,
    bis_sector: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
    page: int = 1,
    page_size: int = 25,
    sort: str = "is_number",
) -> BrowseResponse:
    """Filtered, paginated listing.

    `q` here is a plain substring match, not semantic search — this is the
    "I know roughly what I am looking for" path. Semantic search lives in
    /api/chat and /api/recommend.
    """
    items = vectorstore.all_standards()
    needle = q.strip().lower()

    if needle:
        items = [
            s
            for s in items
            if needle in s.is_number.lower()
            or needle in s.title.lower()
            or needle in s.scope.lower()
            or any(needle in k.lower() for k in s.keywords)
            or needle in s.bis_sector.lower()
            or needle in s.bis_subsector.lower()
        ]
    if department:
        wanted = department.strip().upper()
        items = [s for s in items if s.department_code() == wanted]
    if sector:
        items = [s for s in items if s.sector == sector]
    if status:
        items = [s for s in items if s.status == status]
    if ics:
        prefix = ics.strip()
        items = [s for s in items if any(c.startswith(prefix) for c in s.ics_codes)]
    if qco is not None:
        items = [s for s in items if s.qco_mandatory is qco]
    if bis_sector:
        items = [s for s in items if s.bis_sector == bis_sector]
    if year_from is not None:
        items = [s for s in items if (s.year or 0) >= year_from]
    if year_to is not None:
        items = [s for s in items if (s.year or 9999) <= year_to]

    if sort == "year":
        items = sorted(items, key=lambda s: (s.year or 0), reverse=True)
    elif sort == "title":
        items = sorted(items, key=lambda s: s.title)
    else:
        items = sorted(items, key=lambda s: s.is_number)

    total = len(items)
    page = max(1, page)
    start = (page - 1) * page_size
    return BrowseResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_summary(s) for s in items[start : start + page_size]],
    )


def facets() -> FacetsResponse:
    """Counts per filter value, so the browse UI can show what is worth clicking."""
    standards = vectorstore.all_standards()

    departments: dict[str, int] = {}
    sectors: dict[str, int] = {}
    statuses: dict[str, int] = {}
    ics_groups: dict[str, int] = {}
    decades: dict[str, int] = {}
    bis_sectors: dict[str, int] = {}
    qco = 0

    for standard in standards:
        code = standard.department_code()
        if code:
            departments[code] = departments.get(code, 0) + 1
        if standard.sector:
            sectors[standard.sector] = sectors.get(standard.sector, 0) + 1
        statuses[standard.status] = statuses.get(standard.status, 0) + 1
        # ICS is hierarchical; the leading field is the subject group.
        for code_ics in standard.ics_codes:
            group = code_ics.split(".")[0]
            ics_groups[group] = ics_groups.get(group, 0) + 1
        if standard.year:
            decade = f"{standard.year // 10 * 10}s"
            decades[decade] = decades.get(decade, 0) + 1
        if standard.bis_sector:
            bis_sectors[standard.bis_sector] = bis_sectors.get(standard.bis_sector, 0) + 1
        if standard.qco_mandatory:
            qco += 1

    def ranked(counts: dict[str, int]) -> list[FacetCount]:
        return [
            FacetCount(value=value, count=count)
            for value, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

    return FacetsResponse(
        departments=ranked(departments),
        sectors=ranked(sectors),
        statuses=ranked(statuses),
        ics_groups=ranked(ics_groups),
        decades=sorted(
            (FacetCount(value=v, count=c) for v, c in decades.items()),
            key=lambda f: f.value,
        ),
        qco_mandatory=qco,
        total=len(standards),
        bis_sectors=ranked(bis_sectors),
        classified=sum(bis_sectors.values()),
    )


def coverage() -> CoverageResponse:
    """Indexed count per department against the real BIS published total.

    Reporting "CED 26 / 2,005" rather than a flattering percentage is
    deliberate. A ministry audience can check the denominator, and an honest
    coverage claim survives scrutiny where a rounded-up one does not.
    """
    everything = vectorstore.all_standards()
    indexed: dict[str, int] = {}
    for standard in everything:
        code = standard.department_code()
        if code:
            indexed[code] = indexed.get(code, 0) + 1

    rows = [
        DepartmentCoverage(
            code=department.code,
            name=department.name,
            indexed=indexed.get(department.code, 0),
            published=department.published,
        )
        for department in bis.DEPARTMENTS
    ]

    return CoverageResponse(
        as_of=bis.CATALOGUE_AS_OF,
        total_published=bis.TOTAL_PUBLISHED_STANDARDS,
        # The true index size, not the sum of the department rows. One record
        # (IS/ISO 10823:2004) carries no department on the BIS portal, so the
        # rows sum to one less — and a headline figure that disagreed with the
        # status bar by one would look like a bug rather than a data gap.
        total_indexed=len(everything),
        unclassified=sum(1 for s in everything if not s.department_code()),
        departments_covered=sum(1 for r in rows if r.indexed > 0),
        departments_total=len(bis.DEPARTMENTS),
        sectional_committees=bis.TOTAL_SECTIONAL_COMMITTEES,
        departments=rows,
    )


def detail(is_number: str) -> StandardDetail | None:
    """One standard with its resolved graph neighbourhood."""
    standard = vectorstore.get_one(is_number)
    if standard is None:
        return None

    everything = vectorstore.all_standards()
    by_ref = vectorstore.by_reference()

    related: list[RelatedStandard] = []
    seen: set[str] = set()

    def add(ref: str, relation: str) -> None:
        key = _normalise_ref(ref)
        if not key or key in seen:
            return
        seen.add(key)
        neighbour = by_ref.get(key)
        related.append(
            RelatedStandard(
                is_number=ref,
                title=neighbour.title if neighbour else "",
                relation=relation,
                # A reference we have not indexed is a coverage gap, not an
                # error — the corpus is a subset of the catalogue. Say so.
                in_corpus=neighbour is not None,
            )
        )

    for ref in standard.normative_refs:
        add(ref, "normative_ref")
    for ref in standard.test_methods:
        add(ref, "test_method")
    for ref in standard.supersedes:
        add(ref, "supersedes")
    if standard.superseded_by:
        add(standard.superseded_by, "superseded_by")

    target = _normalise_ref(standard.is_number)
    cited_by = [
        other.is_number
        for other in everything
        if other.is_number != standard.is_number
        and any(_normalise_ref(r) == target for r in other.related())
    ]

    department = bis.resolve_department(standard.sector, standard.technical_committee)

    return StandardDetail(
        standard=standard,
        department_name=department.name if department else standard.sector,
        related=related,
        cited_by=sorted(cited_by),
    )


def graph(is_number: str, depth: int = 1) -> dict:
    """Nodes and edges around one standard, for the detail-drawer visualisation.

    Depth is capped at 2: beyond that the concrete cluster becomes a hairball
    and stops communicating anything.
    """
    root = vectorstore.get_one(is_number)
    if root is None:
        return {"nodes": [], "edges": []}

    depth = max(1, min(2, depth))
    by_ref = vectorstore.by_reference()

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def add_node(is_num: str, title: str, in_corpus: bool, level: int) -> None:
        key = _normalise_ref(is_num)
        if key in nodes:
            nodes[key]["level"] = min(nodes[key]["level"], level)
            return
        nodes[key] = {
            "is_number": is_num,
            "title": title,
            "in_corpus": in_corpus,
            "level": level,
        }

    def add_edge(source: str, target: str, relation: str) -> None:
        key = (_normalise_ref(source), _normalise_ref(target), relation)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append({"source": source, "target": target, "relation": relation})

    add_node(root.is_number, root.title, True, 0)

    frontier = [(root, 0)]
    while frontier:
        current, level = frontier.pop(0)
        if level >= depth:
            continue
        groups = (
            (current.normative_refs, "normative_ref"),
            (current.test_methods, "test_method"),
            (current.supersedes, "supersedes"),
            ([current.superseded_by] if current.superseded_by else [], "superseded_by"),
        )
        for refs, relation in groups:
            for ref in refs:
                neighbour = by_ref.get(_normalise_ref(ref))
                add_node(
                    ref,
                    neighbour.title if neighbour else "",
                    neighbour is not None,
                    level + 1,
                )
                add_edge(current.is_number, ref, relation)
                if neighbour is not None and level + 1 < depth:
                    frontier.append((neighbour, level + 1))

    return {"root": root.is_number, "nodes": list(nodes.values()), "edges": edges}
