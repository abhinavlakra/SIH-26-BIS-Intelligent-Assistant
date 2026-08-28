"""API contract tests via FastAPI's TestClient (no live server needed)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_a_ready_index(client, corpus_size):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["index_ready"] is True
    assert body["indexed_standards"] == corpus_size


def test_stats_describes_the_corpus_and_models(client, corpus_size):
    response = client.get("/api/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["indexed_standards"] == corpus_size
    assert sum(body["sectors"].values()) == corpus_size
    assert body["embedding_model"]
    # No key is configured in tests, so the service must report degraded mode.
    assert body["llm_enabled"] is False


def test_chat_answers_with_citations(client):
    response = client.post("/api/chat", json={"query": "What standard covers drinking water quality?"})
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["answer"].strip()
    assert "IS 10500:2012" in [citation["is_number"] for citation in body["citations"]]
    assert all(0.0 <= citation["score"] <= 1.0 for citation in body["citations"])


def test_chat_declines_when_nothing_is_relevant(client):
    """Off-topic questions must be refused, not answered with weak matches.

    Regression test: an earlier relevance floor of 0.20 sat below the noise
    ceiling of the embedding model (~0.21), so unrelated queries came back
    "grounded" with irrelevant citations.
    """
    response = client.post(
        "/api/chat",
        json={"query": "customs duty rates for importing textiles into Brazil"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is False
    assert body["citations"] == []
    assert "no standard" in body["answer"].lower()


def test_recommend_returns_ranked_standards(client):
    response = client.post(
        "/api/recommend",
        json={"description": "I manufacture stainless steel insulated water bottles"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"]
    first = body["recommendations"][0]
    assert first["is_number"] and first["why"]
    assert 0.0 <= first["confidence"] <= 1.0


def test_short_inputs_are_rejected_by_validation(client):
    assert client.post("/api/chat", json={"query": "hi"}).status_code == 422
    assert client.post("/api/recommend", json={"description": "abc"}).status_code == 422


def test_root_serves_the_app_when_built_else_redirects_to_docs(client):
    """Root behaviour depends on whether the frontend has been built.

    With frontend/dist present the web app is served; without it, / redirects to
    the Swagger UI so the API stays explorable. Both are intended.
    """
    from app.main import FRONTEND_DIST

    response = client.get("/", follow_redirects=False)
    if (FRONTEND_DIST / "index.html").exists():
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    else:
        assert response.status_code in (307, 308)
        assert response.headers["location"] == "/docs"


def test_api_routes_are_not_shadowed_by_the_static_mount(client):
    """The frontend is mounted at '/', so /api/* must still resolve."""
    assert client.get("/api/health").status_code == 200
    assert client.get("/openapi.json").status_code == 200
