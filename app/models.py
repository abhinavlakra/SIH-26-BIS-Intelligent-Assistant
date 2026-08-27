"""Domain records and API request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["active", "withdrawn", "superseded"]

# How far a record has been checked against the official BIS catalogue.
# Surfaced in the UI so provenance is never implied where it does not exist.
Verification = Literal["verified", "unverified"]

SchemeKey = Literal[
    "scheme_i", "fmcs", "crs", "hallmarking", "scheme_x", "eco_mark"
]


class Standard(BaseModel):
    """One Indian Standard, as published in the public BIS catalogue.

    Catalogue *metadata* only — IS number, title, a scope summary and
    classification. Full standard texts are copyrighted and deliberately
    excluded from this corpus.

    Every field beyond the original core set is optional, so older corpus files
    keep loading unchanged while records are enriched incrementally.
    """

    is_number: str = Field(..., description="e.g. 'IS 10500:2012'")
    title: str
    scope: str = ""
    ics_codes: list[str] = Field(default_factory=list)
    sector: str = ""
    technical_committee: str = Field("", description="BIS division/committee, e.g. 'CHD 13'")
    status: Status = "active"
    year: int | None = None
    keywords: list[str] = Field(default_factory=list)

    # --- Certification & compulsion --------------------------------------
    # A standard is only *mandatory* when a Quality Control Order names it.
    # This distinction is the single most useful thing we can tell a user.
    qco_mandatory: bool = Field(
        False, description="True when a Quality Control Order makes conformity mandatory"
    )
    qco_name: str = Field("", description="e.g. 'Electronics and IT Goods (CRO), 2021'")
    certification_scheme: SchemeKey | None = Field(
        None, description="Which BIS conformity assessment scheme applies"
    )

    # --- Reference graph --------------------------------------------------
    # Standards cite each other. Modelling that lets retrieval walk one hop out
    # from a semantic hit and surface standards no embedding would ever match.
    normative_refs: list[str] = Field(
        default_factory=list, description="Standards this one normatively requires"
    )
    test_methods: list[str] = Field(
        default_factory=list, description="Standards giving the test methods for conformity"
    )

    # --- Version currency -------------------------------------------------
    amendment_count: int = 0
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: str = Field("", description="IS number of the edition that replaced this")

    # --- BIS subject taxonomy --------------------------------------------
    # The sector/sub-sector a standard is filed under on the BIS catalogue
    # portal ("Abrasives" / "Coated and Bonded Abrasives"). This is *subject*
    # classification and is orthogonal to `sector`, which is the owning
    # technical department. Collected by `ingestion/taxonomy.py`.
    bis_sector: str = ""
    bis_subsector: str = ""

    # --- Provenance -------------------------------------------------------
    verification: Verification = "unverified"

    def department_code(self) -> str:
        """'CHD 13' -> 'CHD'. Empty when the committee is unknown."""
        committee = (self.technical_committee or "").strip()
        return committee.split()[0].upper() if committee else ""

    def related(self) -> list[str]:
        """Every standard this one points at, de-duplicated, order preserved."""
        seen: dict[str, None] = {}
        for group in (self.normative_refs, self.test_methods, self.supersedes):
            for ref in group:
                seen.setdefault(ref, None)
        if self.superseded_by:
            seen.setdefault(self.superseded_by, None)
        return list(seen)

    def embedding_text(self) -> str:
        """The text actually embedded for semantic search.

        Title and scope carry the retrieval signal; keywords and sector widen
        recall for colloquial phrasing ("water bottle" -> food-grade steel).

        Reference numbers are deliberately excluded: they are noise in vector
        space and are traversed as a graph after retrieval instead.
        """
        parts = [self.is_number, self.title, self.scope]
        if self.keywords:
            parts.append("Keywords: " + ", ".join(self.keywords))
        if self.sector:
            parts.append("Sector: " + self.sector)
        # The BIS subject taxonomy is the only real topical signal most records
        # have — the portal publishes no scope text, so without this the
        # embedding sees little beyond the title.
        subject = " / ".join(p for p in (self.bis_sector, self.bis_subsector) if p)
        if subject:
            parts.append("Subject: " + subject)
        return "\n".join(p for p in parts if p)


class Citation(BaseModel):
    is_number: str
    title: str
    scope: str = ""
    sector: str = ""
    status: Status = "active"
    score: float = Field(..., description="Semantic relevance, 0-1 (higher is closer)")


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=3, examples=["What standard covers drinking water quality?"])
    top_k: int | None = Field(None, ge=1, le=20)
    sector: str | None = Field(None, description="Optional filter, e.g. 'Civil Engineering'")
    lang: str = Field("en", description="Reply language: 'en' or 'hi'")


class ServiceAnswer(BaseModel):
    """One entry from the BIS services knowledge base, with its source."""

    key: str
    topic: str
    topic_label: str = ""
    question: str
    answer: str
    source: str = Field("", description="Page on bis.gov.in this was taken from")
    score: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    used_model: str
    grounded: bool = Field(..., description="False when no standard cleared the relevance floor")
    # Populated when the question was about a BIS *service* — certification,
    # hallmarking, laboratories, consumer protection — rather than about a
    # standard. Sourced to bis.gov.in rather than to an IS number.
    services: list[ServiceAnswer] = Field(default_factory=list)


class RecommendRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=5,
        examples=["I manufacture stainless steel insulated water bottles for retail sale"],
    )
    top_n: int | None = Field(None, ge=1, le=20)
    lang: str = Field("en", description="Reply language: 'en' or 'hi'")
    include_related: bool = Field(
        True, description="Expand one hop along normative references"
    )


class Recommendation(BaseModel):
    is_number: str
    title: str
    sector: str = ""
    status: Status = "active"
    why: str = Field(..., description="Why this standard applies to the described product")
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Compliance signal: the reason a user cares which of these is which.
    qco_mandatory: bool = False
    qco_name: str = ""
    certification_scheme: SchemeKey | None = None

    # Provenance of the recommendation itself.
    via: str = Field(
        "semantic",
        description="'semantic' when retrieved directly, else the IS number it was pulled in from",
    )
    normative_refs: list[str] = Field(default_factory=list)


class RecommendResponse(BaseModel):
    description: str
    recommendations: list[Recommendation]
    used_model: str

    @property
    def mandatory(self) -> list[Recommendation]:
        return [r for r in self.recommendations if r.qco_mandatory]


# --- Catalogue browse -----------------------------------------------------


class StandardSummary(BaseModel):
    """Row shape for the browse table — lighter than the full record."""

    is_number: str
    title: str
    sector: str = ""
    department_code: str = ""
    technical_committee: str = ""
    status: Status = "active"
    year: int | None = None
    ics_codes: list[str] = Field(default_factory=list)
    qco_mandatory: bool = False
    verification: Verification = "unverified"
    bis_sector: str = ""
    bis_subsector: str = ""


class BrowseResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[StandardSummary]


class RelatedStandard(BaseModel):
    """A graph neighbour, resolved against the index where possible."""

    is_number: str
    title: str = ""
    relation: Literal["normative_ref", "test_method", "supersedes", "superseded_by"]
    in_corpus: bool = False


class StandardDetail(BaseModel):
    standard: Standard
    department_name: str = ""
    related: list[RelatedStandard] = Field(default_factory=list)
    cited_by: list[str] = Field(
        default_factory=list, description="Indexed standards that reference this one"
    )


class FacetCount(BaseModel):
    value: str
    count: int


class FacetsResponse(BaseModel):
    departments: list[FacetCount]
    sectors: list[FacetCount]
    statuses: list[FacetCount]
    ics_groups: list[FacetCount]
    decades: list[FacetCount]
    qco_mandatory: int
    total: int
    # BIS subject taxonomy — the sectors a user actually browses by on the
    # portal, as opposed to the owning technical department.
    bis_sectors: list[FacetCount] = Field(default_factory=list)
    classified: int = Field(
        0, description="Records carrying a BIS subject sector"
    )


class DepartmentCoverage(BaseModel):
    code: str
    name: str
    indexed: int
    published: int = Field(..., description="Real BIS total for this department")


class CoverageResponse(BaseModel):
    as_of: str
    total_published: int
    total_indexed: int
    unclassified: int = Field(
        0, description="Indexed records the BIS portal gives no department for"
    )
    departments_covered: int
    departments_total: int
    sectional_committees: int
    departments: list[DepartmentCoverage]


# --- Certification pathway ------------------------------------------------


class CertificationResponse(BaseModel):
    is_number: str
    title: str
    mandatory: bool
    qco_name: str = ""
    scheme_key: str = ""
    scheme_name: str = ""
    applies_to: str = ""
    steps: list[str] = Field(default_factory=list)
    note: str = ""


# --- Specification / tender analysis --------------------------------------


class SpecAnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=20,
        description="Tender text or a specification, one line item per line",
    )
    max_lines: int | None = Field(None, ge=1, le=200)


class CitedStandard(BaseModel):
    """An IS number found verbatim in the submitted text."""

    cited_as: str
    resolved: str = ""
    in_corpus: bool = False
    current: bool = True
    superseded_by: str = ""
    amendment_count: int = 0


class SpecLineResult(BaseModel):
    line_no: int
    text: str
    matches: list[Recommendation] = Field(default_factory=list)
    # Set for PDF uploads. "page 14, item 4.2" is auditable in a 40-page tender
    # where a running line number is not.
    page: int | None = None


class SpecSource(BaseModel):
    """Where the analysed text came from, so the UI can be specific about it."""

    kind: Literal["text", "pdf"] = "text"
    filename: str = ""
    pages: int = 0
    truncated: bool = Field(
        False, description="True when the document had more line items than the cap"
    )


class SpecAnalyzeResponse(BaseModel):
    line_count: int
    lines: list[SpecLineResult]
    cited_standards: list[CitedStandard]
    missing_normative_refs: list[str] = Field(
        default_factory=list,
        description="Standards normatively required by the cited ones but absent from the spec",
    )
    outdated_citations: list[CitedStandard] = Field(default_factory=list)
    mandatory_standards: list[str] = Field(default_factory=list)
    completeness: float = Field(..., ge=0.0, le=1.0)
    used_model: str
    source: SpecSource = Field(default_factory=SpecSource)


# --- Meta -----------------------------------------------------------------


class StatsResponse(BaseModel):
    indexed_standards: int
    sectors: dict[str, int]
    embedding_model: str
    llm_model: str
    llm_enabled: bool
    llm_endpoint: str
    corpus_path: str
    # Honest scale context: what fraction of the real catalogue is indexed.
    catalogue_total: int = 0
    departments_covered: int = 0
    departments_total: int = 0
    qco_mandatory: int = 0
    retrieval_mode: str = "hybrid"


class HealthResponse(BaseModel):
    status: str
    index_ready: bool
    indexed_standards: int


class QueryLogEntry(BaseModel):
    query: str
    endpoint: str
    grounded: bool
    top_score: float
    latency_ms: int
    used_model: str
    at: str


class AnalyticsResponse(BaseModel):
    total_queries: int
    grounded_rate: float
    median_latency_ms: int
    top_queries: list[FacetCount]
    unanswered: list[FacetCount] = Field(
        default_factory=list,
        description="Queries that matched nothing — a standards-development gap signal for BIS",
    )
    recent: list[QueryLogEntry] = Field(default_factory=list)
