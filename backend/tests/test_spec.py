"""Tender / specification analysis — the SIH26108 procurement-dispute features."""

from fastapi.testclient import TestClient

from app.main import app
from app.rag import vectorstore
from app.services.spec import extract_citations

client = TestClient(app)

TENDER = """
1. Construction of a reinforced concrete office building.
2. Concrete work shall conform to IS 456:2000 throughout the structure.
3. Seismic design of the frame shall follow IS 1893:2002.
4. Reinforcement bars for all structural members.
"""


def analyze(text: str) -> dict:
    response = client.post("/api/analyze-spec", json={"text": text})
    assert response.status_code == 200, response.text
    return response.json()


# --- citation extraction --------------------------------------------------


def test_extract_citations_handles_the_ways_tenders_write_is_numbers():
    found = extract_citations(
        "as per IS 456:2000 and IS 1893 (Part 1) : 2016, plus IS/ISO 9001:2015 and bare IS 13920"
    )
    assert "IS 456:2000" in found
    assert "IS/ISO 9001:2015" in found
    assert "IS 13920" in found
    assert any("1893" in c for c in found)


def test_extract_citations_deduplicates():
    assert extract_citations("IS 456:2000 ... again IS 456:2000") == ["IS 456:2000"]


# --- currency -------------------------------------------------------------


def test_a_stale_year_resolves_to_the_current_edition_and_is_flagged():
    """The headline case: a tender citing the superseded 1893 edition."""
    payload = analyze(TENDER)
    cited = {c["cited_as"]: c for c in payload["cited_standards"]}

    stale = cited["IS 1893:2002"]
    assert stale["in_corpus"] is True
    assert stale["resolved"] == "IS 1893 (Part 1):2016"
    assert stale["current"] is False
    assert stale["superseded_by"] == "IS 1893 (Part 1):2016"
    assert "IS 1893:2002" in [c["cited_as"] for c in payload["outdated_citations"]]


def test_a_current_citation_is_not_flagged():
    payload = analyze(TENDER)
    cited = {c["cited_as"]: c for c in payload["cited_standards"]}
    assert cited["IS 456:2000"]["current"] is True


def test_a_citation_with_no_year_is_flagged_as_ambiguous():
    payload = analyze(
        "1. Ductile detailing of the frame shall be as per IS 1893.\n"
        "2. Concrete grade M30 for all structural members."
    )
    cited = {c["cited_as"]: c for c in payload["cited_standards"]}
    assert cited["IS 1893"]["current"] is False


def test_an_uncited_standard_is_reported_as_not_in_corpus():
    payload = analyze(
        "1. Welding consumables shall conform to IS 99999:2020.\n"
        "2. All welds to be inspected before painting."
    )
    cited = {c["cited_as"]: c for c in payload["cited_standards"]}
    assert cited["IS 99999:2020"]["in_corpus"] is False


# --- completeness ---------------------------------------------------------


def test_missing_normative_references_are_reported():
    """IS 456 requires IS 1786; the tender never mentions it."""
    payload = analyze(TENDER)
    assert "IS 1786:2008" in payload["missing_normative_refs"]


def test_a_spec_that_cites_its_references_has_none_missing():
    payload = analyze(
        "1. Concrete work shall conform to IS 456:2000.\n"
        "2. Reinforcement shall conform to IS 1786:2008.\n"
        "3. Aggregate shall conform to IS 383:2016."
    )
    assert payload["missing_normative_refs"] == []


def test_completeness_rewards_a_better_specification():
    weak = analyze(
        "1. Supply of reinforced concrete for a building frame.\n"
        "2. All work to be carried out to good industry practice."
    )
    strong = analyze(
        "1. Concrete work shall conform to IS 456:2000.\n"
        "2. Reinforcement shall conform to IS 1786:2008.\n"
        "3. Aggregate shall conform to IS 383:2016."
    )
    assert strong["completeness"] > weak["completeness"]


def test_mandatory_certification_is_surfaced():
    payload = analyze(TENDER)
    # IS 1786 is under a Quality Control Order in the fixture corpus.
    assert "IS 1786:2008" in payload["mandatory_standards"]


# --- line attribution -----------------------------------------------------


def test_matches_are_attributed_to_individual_line_items():
    payload = analyze(TENDER)
    lines = {line["line_no"]: line for line in payload["lines"]}
    assert payload["line_count"] == len(lines)
    concrete_line = next(l for l in payload["lines"] if "Concrete work" in l["text"])
    assert any(m["is_number"] == "IS 456:2000" for m in concrete_line["matches"])


def test_short_lines_and_list_markers_are_stripped():
    payload = analyze("1.\n2.\n3. Supply of reinforced concrete for a building frame.\n")
    assert payload["line_count"] == 1
    assert payload["lines"][0]["text"].startswith("Supply of")


def test_short_input_is_rejected_by_validation():
    assert client.post("/api/analyze-spec", json={"text": "too short"}).status_code == 422


def test_a_tender_citing_no_standards_scores_zero():
    """Absence of citations must not read as absence of problems.

    An earlier scoring rule defaulted the currency and reference-completeness
    components to 1.0 when nothing was cited, so a tender naming no standards
    at all scored 0.67 against 0.75 for a properly specified one.
    """
    payload = analyze(
        "Supply and installation of galvanized steel roofing sheets.\n"
        "Provision of protective helmets for all site personnel.\n"
        "Internal electrical wiring for six classrooms including switches."
    )
    assert payload["cited_standards"] == []
    assert payload["completeness"] == 0.0
    # The line items are still segmented and returned — a tender citing nothing
    # is still analysable. Whether they *match* a standard depends on the
    # corpus, and the six-record test fixture cannot answer for roofing sheets,
    # so that is left to `samples/tenders/05-no-citations.pdf` against the real
    # index rather than asserted here.
    assert payload["line_count"] == 3


def test_missing_refs_never_suggest_a_superseded_standard():
    """The checker must not create the defect it exists to catch.

    IS 456 used to list IS 8112 and IS 12269 as normative references. Both were
    absorbed into IS 269:2015, so the analyser was advising procurement
    officers to add withdrawn standards to their tender.
    """
    payload = analyze("Concrete work shall conform to IS 456:2000 throughout the structure.")
    assert payload["missing_normative_refs"], "expected some missing references"
    for ref in payload["missing_normative_refs"]:
        standard = vectorstore.get_one(ref)
        if standard is not None:
            assert not standard.superseded_by, f"{ref} is superseded"
            assert standard.status == "active", f"{ref} is {standard.status}"
