"""BIS services knowledge base — the SIH26107 bullets the catalogue cannot answer.

Consumer protection, hallmarking and testing laboratories are BIS *services*.
The standards catalogue holds IS numbers and titles, so it correctly finds
nothing for "how do I complain about a fake ISI mark" — a refusal that reads as
a failure. These tests cover the separate, sourced knowledge base that answers
them, and the routing that decides which one replies.
"""

from fastapi.testclient import TestClient

from app import bis_services
from app.main import app
from app.services import knowledge

client = TestClient(app)


def ask(query: str) -> dict:
    response = client.post("/api/chat", json={"query": query})
    assert response.status_code == 200, response.text
    return response.json()


# --- the three previously unanswerable bullets ----------------------------


def test_consumer_complaint_is_answered_with_a_source():
    payload = ask("how do I file a complaint about a defective ISI marked product")
    assert payload["grounded"] is True
    assert payload["services"], "expected a services answer"
    assert payload["services"][0]["topic"] == "consumer"
    assert payload["services"][0]["source"].startswith("https://www.bis.gov.in")


def test_hallmarking_is_answered():
    payload = ask("how do I check if my gold jewellery hallmark is genuine")
    assert payload["grounded"] is True
    assert payload["services"][0]["topic"] == "hallmarking"


def test_laboratory_lookup_is_answered():
    payload = ask("which laboratory can test my drinking water sample")
    assert payload["grounded"] is True
    assert payload["services"], "a lab question must not be answered from the catalogue"
    assert payload["services"][0]["topic"] == "laboratories"


def test_a_lab_question_is_not_answered_with_test_method_standards():
    """The routing bug this feature exists to fix.

    "drinking water" dominates the embedding, so the catalogue used to return
    IS 3025 and IS 17614 — water *test-method* standards — to someone asking
    where to get a sample tested.
    """
    payload = ask("which laboratory can test my drinking water sample")
    assert payload["citations"] == [], payload["citations"]


# --- routing must not swallow ordinary standards questions ----------------


def test_a_product_question_still_reaches_the_catalogue():
    payload = ask("What standard covers drinking water quality?")
    assert payload["citations"], "a standards question must use the catalogue"
    assert not payload["services"]


def test_off_topic_questions_still_decline():
    """The honesty guard must survive the new fallback.

    Adding a second knowledge base is exactly how a system that used to refuse
    starts answering everything.
    """
    for query in [
        "who won the 2018 football world cup",
        "best pizza recipe with sourdough base",
        "cheapest flights from delhi to singapore",
    ]:
        payload = ask(query)
        assert payload["grounded"] is False, f"{query!r} should be declined"
        assert not payload["services"]
        assert payload["citations"] == []


# --- the knowledge base itself --------------------------------------------


def test_every_entry_carries_a_bis_source():
    """Source-backed answers are the point; an unsourced entry is a liability."""
    for entry in bis_services.ALL_ENTRIES:
        assert entry.source.startswith("https://"), entry.key
        assert "bis.gov.in" in entry.source, entry.key


def test_no_entry_quotes_a_fee_or_a_helpline_number():
    """Fees, timelines and phone numbers change and we cannot cite them.

    A stale number in front of a BIS jury is worse than no number.
    """
    import re

    for entry in bis_services.ALL_ENTRIES:
        text = f"{entry.question} {entry.answer}"
        assert not re.search(r"(?:Rs\.?|₹|INR)\s*\d", text), entry.key
        assert not re.search(r"\b1800[\s-]?\d", text), entry.key
        assert not re.search(r"\b\d+\s*(?:working\s*)?days\b", text, re.I), entry.key


def test_topics_are_all_represented():
    topics = {entry.topic for entry in bis_services.ALL_ENTRIES}
    assert topics == {"hallmarking", "laboratories", "consumer", "services"}


def test_intent_router_ignores_ordinary_product_questions():
    assert knowledge.looks_like_service_question("which laboratory tests cement") is True
    assert knowledge.looks_like_service_question("how do I complain about a mark") is True
    assert knowledge.looks_like_service_question("what is the HUID on my ring") is True
    # Must not fire on a normal standards question.
    assert knowledge.looks_like_service_question("what standard covers drinking water") is False
    assert knowledge.looks_like_service_question("cement for concrete construction") is False


def test_services_endpoint_lists_a_topic():
    response = client.get("/api/services", params={"topic": "hallmarking"})
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert all(item["topic"] == "hallmarking" for item in payload)


def test_services_endpoint_searches():
    response = client.get("/api/services", params={"q": "what is HUID"})
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["topic"] == "hallmarking"
