"""Recommendation engine behaviour (heuristic mode — no LLM key in tests)."""

from app.services.recommend import _extract_json_object, recommend


def test_water_bottle_spec_surfaces_the_utensils_standard():
    result = recommend("I manufacture stainless steel insulated water bottles for retail sale")
    numbers = [item.is_number for item in result.recommendations]
    assert numbers, "expected recommendations"
    assert "IS 5522:2014" in numbers


def test_mandatory_standards_rank_above_merely_relevant_ones():
    """Compliance obligation outranks similarity score, deliberately.

    Knowing a standard applies matters less than knowing it is under a Quality
    Control Order and certification is therefore compulsory before sale, so the
    sort key is (mandatory, confidence) rather than confidence alone.
    """
    result = recommend("ready mix concrete supply for a housing project")
    flags = [item.qco_mandatory for item in result.recommendations]
    assert flags == sorted(flags, reverse=True), "mandatory standards must come first"

    # Within each group, confidence still orders the list.
    for mandatory in (True, False):
        group = [i.confidence for i in result.recommendations if i.qco_mandatory is mandatory]
        assert group == sorted(group, reverse=True)

    assert all(0.0 <= item.confidence <= 1.0 for item in result.recommendations)


def test_recommendations_carry_their_certification_obligation():
    result = recommend("steel reinforcement bars for a concrete frame")
    rebar = next(i for i in result.recommendations if i.is_number == "IS 1786:2008")
    assert rebar.qco_mandatory is True
    assert rebar.qco_name
    assert rebar.certification_scheme == "scheme_i"


def test_graph_expansion_surfaces_standards_semantics_would_miss():
    """The reference graph is what a vector index cannot do.

    A seismic-design query retrieves IS 1893, which normatively requires
    IS 456 — a link no embedding of "earthquake" would find on its own.
    """
    with_graph = recommend("earthquake resistant design of a building frame")
    pulled_in = {i.is_number: i for i in with_graph.recommendations if i.via != "semantic"}
    assert pulled_in, "expected at least one standard pulled in via the graph"
    for item in pulled_in.values():
        assert item.via in {i.is_number for i in with_graph.recommendations}
        assert "normative reference" in item.why

    without = recommend(
        "earthquake resistant design of a building frame", include_related=False
    )
    assert all(i.via == "semantic" for i in without.recommendations)
    assert len(without.recommendations) <= len(with_graph.recommendations)


def test_every_recommendation_carries_a_rationale():
    # Phrased close to the fixture's own wording on purpose. The six-record test
    # corpus is far too small to reproduce the score distribution the floors are
    # calibrated against, so an oblique query ("electric kettle") lands below
    # RECOMMEND_FLOOR here while retrieving correctly against the real 24k
    # corpus. This test is about rationales, not about retrieval sensitivity —
    # `test_retriever.py` and `app.ingestion.calibrate` cover that.
    result = recommend("household electrical appliance safety requirements")
    assert result.recommendations
    assert all(item.why.strip() for item in result.recommendations)


def test_top_n_is_respected():
    result = recommend("steel bars for construction", top_n=2)
    assert len(result.recommendations) <= 2


def test_verbose_first_person_descriptions_still_match():
    """Recommend uses a lower floor than chat, by design.

    Filler words in a natural product description dilute the embedding: this
    phrasing scores ~0.34 where the terse "stainless steel for food utensils"
    scores ~0.68. Refusing a real product spec would be worse than ranking it.
    """
    result = recommend(
        "I manufacture stainless steel insulated water bottles for retail sale"
    )
    assert result.recommendations


def test_pure_noise_still_returns_nothing():
    result = recommend("who won the 2018 football world cup final")
    assert result.recommendations == []


def test_extract_json_object_handles_surrounding_prose():
    payload = _extract_json_object(
        'Sure, here you go:\n```json\n{"items": [{"is_number": "IS 1:2000", '
        '"why": "because {nested} braces", "confidence": 0.8}]}\n```\nHope that helps!'
    )
    assert payload is not None
    assert payload["items"][0]["is_number"] == "IS 1:2000"
    assert payload["items"][0]["confidence"] == 0.8


def test_extract_json_object_returns_none_on_garbage():
    assert _extract_json_object("no json here at all") is None
    assert _extract_json_object('{"unbalanced": ') is None
