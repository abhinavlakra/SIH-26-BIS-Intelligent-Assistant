"""Browse, facets, coverage, reference graph and certification pathway."""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app
from app.rag import vectorstore
from app.services import catalogue, certification

client = TestClient(app)


def test_parallel_first_requests_do_not_race_the_chroma_client():
    """The dashboard fires four endpoints at once on mount.

    FastAPI runs sync endpoints in a threadpool, so those land on separate
    threads. `functools.lru_cache` does not serialise the call it wraps — every
    thread that misses runs the body — so guarding the client with one produced
    several `PersistentClient`s racing Chroma's process-global registry, and
    intermittent 500s on page load. Construction is now lock-guarded.
    """
    # Force a cold start so the construction path is the one under test.
    vectorstore._client.cache_clear()

    paths = ["/api/coverage", "/api/facets", "/api/stats", "/api/analytics/queries"] * 3
    with ThreadPoolExecutor(max_workers=len(paths)) as pool:
        responses = list(pool.map(lambda path: client.get(path), paths))

    failures = [(r.request.url.path, r.status_code) for r in responses if r.status_code != 200]
    assert not failures, f"parallel cold-start requests failed: {failures}"


# --- browse ---------------------------------------------------------------


def test_browse_returns_every_standard_by_default(corpus_size):
    payload = client.get("/api/standards").json()
    assert payload["total"] == corpus_size
    assert len(payload["items"]) == corpus_size


def test_browse_filters_by_department_code():
    payload = client.get("/api/standards", params={"department": "CED"}).json()
    assert payload["total"] >= 1
    assert {item["department_code"] for item in payload["items"]} == {"CED"}


def test_browse_substring_matches_title_and_keywords():
    by_title = client.get("/api/standards", params={"q": "concrete"}).json()
    assert any(i["is_number"] == "IS 456:2000" for i in by_title["items"])

    # "water bottle" appears only in IS 5522's keywords, not its title.
    by_keyword = client.get("/api/standards", params={"q": "water bottle"}).json()
    assert [i["is_number"] for i in by_keyword["items"]] == ["IS 5522:2014"]


def test_browse_paginates(corpus_size):
    first = client.get("/api/standards", params={"page_size": 2, "page": 1}).json()
    second = client.get("/api/standards", params={"page_size": 2, "page": 2}).json()
    assert first["total"] == second["total"] == corpus_size
    assert len(first["items"]) == 2
    assert {i["is_number"] for i in first["items"]}.isdisjoint(
        {i["is_number"] for i in second["items"]}
    )


def test_browse_ics_filter_uses_a_hierarchical_prefix():
    # 77 is the metallurgy group; both steel records sit under it.
    payload = client.get("/api/standards", params={"ics": "77"}).json()
    assert {i["is_number"] for i in payload["items"]} == {"IS 5522:2014", "IS 1786:2008"}


# --- facets and coverage --------------------------------------------------


def test_facets_count_every_standard(corpus_size):
    payload = client.get("/api/facets").json()
    assert payload["total"] == corpus_size
    assert sum(f["count"] for f in payload["sectors"]) == corpus_size
    assert sum(f["count"] for f in payload["statuses"]) == corpus_size


def test_coverage_reports_against_the_real_bis_totals(corpus_size):
    payload = client.get("/api/coverage").json()
    # The denominators are the published BIS figures, not our corpus size.
    assert payload["total_published"] == 23461
    assert payload["departments_total"] == 17
    assert payload["total_indexed"] == corpus_size
    assert len(payload["departments"]) == 17
    # Every department appears, including ones we have nothing for — an honest
    # zero is the point of this endpoint.
    assert any(d["indexed"] == 0 for d in payload["departments"])
    for department in payload["departments"]:
        assert department["indexed"] <= department["published"]


# --- detail and graph -----------------------------------------------------


def test_detail_resolves_normative_references():
    payload = client.get("/api/standards/IS 456:2000").json()
    relations = {r["is_number"]: r for r in payload["related"]}
    assert "IS 1786:2008" in relations
    assert relations["IS 1786:2008"]["relation"] == "normative_ref"
    # Resolved against the index, so the title comes back too.
    assert relations["IS 1786:2008"]["in_corpus"] is True
    assert relations["IS 1786:2008"]["title"]


def test_detail_reports_unindexed_references_as_gaps_not_errors():
    payload = client.get("/api/standards/IS 456:2000").json()
    missing = [r for r in payload["related"] if not r["in_corpus"]]
    # IS 383 is referenced by the fixture's IS 456 but is not in the test corpus.
    assert missing, "expected at least one reference we do not index"
    assert all(r["title"] == "" for r in missing)


def test_detail_reports_the_reverse_edge():
    payload = client.get("/api/standards/IS 1786:2008").json()
    assert "IS 456:2000" in payload["cited_by"]


def test_detail_404s_for_an_unknown_standard():
    assert client.get("/api/standards/IS 99999:2020").status_code == 404


def test_graph_returns_typed_edges():
    payload = client.get("/api/graph/IS 456:2000").json()
    assert payload["root"] == "IS 456:2000"
    assert len(payload["nodes"]) > 1
    assert {e["relation"] for e in payload["edges"]} <= {
        "normative_ref",
        "test_method",
        "supersedes",
        "superseded_by",
    }
    assert any(e["target"] == "IS 1786:2008" for e in payload["edges"])


def test_graph_404s_for_an_unknown_standard():
    assert client.get("/api/graph/IS 99999:2020").status_code == 404


# --- certification --------------------------------------------------------


def test_certification_reports_a_mandatory_qco():
    payload = client.get("/api/certification/IS 1786:2008").json()
    assert payload["mandatory"] is True
    assert payload["qco_name"]
    assert payload["steps"]
    assert "MANDATORY" in payload["note"]


def test_certification_defaults_to_voluntary_and_says_so():
    payload = client.get("/api/certification/IS 10500:2012").json()
    assert payload["mandatory"] is False
    assert "voluntary" in payload["note"].lower()


def test_certification_never_claims_mandatory_without_a_qco():
    """The one error a BIS jury would spot instantly."""
    for standard in catalogue.browse(page_size=200).items:
        pathway = certification.pathway(standard.is_number)
        if pathway.mandatory:
            assert pathway.qco_name, f"{standard.is_number} claims mandatory with no QCO named"
