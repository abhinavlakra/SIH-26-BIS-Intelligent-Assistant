"""Retrieval behaviour: the layer everything else is grounded on."""

from app.rag import vectorstore
from app.rag.retriever import (
    RECOMMEND_FLOOR,
    RELEVANCE_FLOOR,
    _stem,
    expand_related,
    search,
)


def test_index_contains_every_standard(corpus_size):
    assert vectorstore.count() == corpus_size


def test_drinking_water_query_retrieves_is_10500():
    hits = search("What standard covers drinking water quality?")
    assert hits, "expected at least one hit"
    top_standard, top_score = hits[0]
    assert top_standard.is_number == "IS 10500:2012"
    assert top_score >= RELEVANCE_FLOOR


def test_results_are_ranked_and_above_the_relevance_floor():
    hits = search("concrete structural design")
    assert hits
    scores = [score for _standard, score in hits]
    assert scores == sorted(scores, reverse=True)
    assert all(score >= RELEVANCE_FLOOR for score in scores)


def test_sector_filter_restricts_results():
    hits = search("reinforced concrete design code", sector="Civil Engineering")
    assert hits
    assert {standard.sector for standard, _ in hits} == {"Civil Engineering"}


def test_top_k_is_respected():
    hits = search("safety requirements", top_k=2)
    assert len(hits) <= 2


def test_off_topic_queries_are_rejected_by_the_relevance_floor():
    """The floor must sit above the embedding model's noise ceiling.

    Measured on the seed corpus: genuinely relevant queries score 0.57-0.68,
    off-topic queries top out around 0.21. A floor inside that gap is what makes
    "not in the catalogue" answers possible instead of confident nonsense.
    """
    off_topic = [
        "who won the 2018 football world cup",
        "best pizza recipe with sourdough base",
        "python asyncio event loop debugging",
        "customs duty rates for importing textiles into Brazil",
    ]
    for query in off_topic:
        assert search(query) == [], f"{query!r} should match no standard"


def test_relevant_queries_score_well_clear_of_the_floor():
    for query in ["drinking water quality limits", "reinforced concrete design code"]:
        hits = search(query)
        assert hits, f"{query!r} should match at least one standard"
        assert hits[0][1] > RELEVANCE_FLOOR + 0.1


def test_metadata_round_trips_through_the_store():
    hits = search("stainless steel utensils for food contact")
    standards = {standard.is_number: standard for standard, _ in hits}
    subject = standards.get("IS 5522:2014")
    assert subject is not None
    # Lists are flattened to strings for Chroma and must come back as lists.
    assert isinstance(subject.keywords, list)
    assert "water bottle" in subject.keywords
    assert subject.ics_codes == ["77.140.50"]
    assert subject.year == 2014


def test_v2_list_fields_round_trip_through_the_store():
    """Every list field needs handling on *both* sides of the Chroma boundary.

    Chroma metadata must be scalar, so lists are joined on write and split on
    read. Adding a list field and only updating the write path fails silently.
    """
    concrete = vectorstore.get_one("IS 456:2000")
    assert concrete is not None
    assert concrete.normative_refs == ["IS 1786:2008", "IS 383:2016"]
    assert concrete.amendment_count == 4

    rebar = vectorstore.get_one("IS 1786:2008")
    assert rebar.qco_mandatory is True
    assert rebar.certification_scheme == "scheme_i"

    seismic = vectorstore.get_one("IS 1893 (Part 1):2016")
    assert seismic.supersedes == ["IS 1893 (Part 1):2002"]

    # An optional scalar with no value must come back as None, not "".
    assert vectorstore.get_one("IS 10500:2012").certification_scheme is None


def test_lookup_tolerates_spacing_and_case_in_is_numbers():
    """'IS 1893 (Part 1):2016' and 'IS 1893(Part 1) : 2016' are the same standard."""
    for variant in (
        "IS 1893 (Part 1):2016",
        "IS 1893(Part 1):2016",
        "is 1893 (part 1) : 2016",
        "  IS 1893 (Part 1) : 2016  ",
    ):
        found = vectorstore.get_one(variant)
        assert found is not None, variant
        assert found.is_number == "IS 1893 (Part 1):2016"


# --- hybrid re-ranking ----------------------------------------------------


def test_hybrid_ranking_prefers_the_product_over_the_subject():
    """The documented failure of pure semantic ranking.

    For "stainless steel water bottle", cosine similarity puts IS 14543
    (packaged drinking *water*) above IS 5522 (steel for utensils) — lexically
    close, but the product is the bottle, not the water. The lexical and ICS
    re-rankers exist to correct exactly this.
    """
    query = "I manufacture stainless steel insulated water bottles for retail sale"
    ranked = [s.is_number for s, _ in search(query, floor=0.0, top_k=5)]
    assert "IS 5522:2014" in ranked
    assert ranked[0] == "IS 5522:2014"


def test_plurals_in_a_description_match_singular_catalogue_keywords():
    """'bottles' has to match the keyword 'water bottle' or the signal is lost."""
    assert _stem("bottles") == "bottle"
    assert _stem("batteries") == "battery"
    assert _stem("boxes") == "box"
    # Words that merely end in 's' must survive intact.
    assert _stem("gas") == "gas"
    assert _stem("stainless") == "stainless"
    assert _stem("analysis") == "analysis"
    assert _stem("steel") == "steel"


def test_reranking_does_not_lift_off_topic_queries_over_the_floor():
    """A regression guard on the blend.

    An additive blend raises every score by a constant, which silently
    invalidates the calibrated floors and lets noise back through. The blend is
    multiplicative and centred so neutral evidence changes nothing.
    """
    for query in ["who won the 2018 football world cup", "best pizza recipe"]:
        assert search(query, floor=RELEVANCE_FLOOR) == []
        assert search(query, floor=RECOMMEND_FLOOR) == []


def test_hybrid_can_be_disabled():
    plain = search("concrete", hybrid=False, floor=0.0)
    assert plain, "semantic-only search must still work"


# --- graph expansion ------------------------------------------------------


def test_expand_related_follows_normative_references():
    hits = search("earthquake resistant design of structures", floor=RECOMMEND_FLOOR)
    assert hits
    expanded = expand_related(hits)
    assert expanded, "expected the graph walk to find something"

    for standard, score, via in expanded:
        assert standard.is_number not in {h.is_number for h, _ in hits}
        assert via in {h.is_number for h, _ in hits}
        # Neighbours inherit a decayed score so they rank below direct hits.
        assert score < max(s for _, s in hits)


def test_expand_related_skips_references_we_do_not_index():
    """IS 456 references IS 383, which is not in the test corpus."""
    hits = [(vectorstore.get_one("IS 456:2000"), 0.9)]
    expanded = expand_related(hits)
    assert "IS 383:2016" not in {s.is_number for s, _, _ in expanded}
    assert "IS 1786:2008" in {s.is_number for s, _, _ in expanded}


def test_expand_related_respects_its_limit():
    hits = search("concrete design", floor=RECOMMEND_FLOOR)
    assert len(expand_related(hits, limit=1)) <= 1
