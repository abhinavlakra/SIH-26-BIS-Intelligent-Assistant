"""LLM adapter behaviour — the degradation paths that keep a demo alive."""

import pytest

from app.rag.llm import AnthropicProvider, LLMUnavailable, NullProvider


def test_null_provider_reports_unavailable_and_raises():
    provider = NullProvider()
    assert provider.available is False
    with pytest.raises(LLMUnavailable):
        provider.generate("system", "user")


def _provider(**kwargs) -> AnthropicProvider:
    defaults = dict(
        api_key="sk-ant-not-a-real-key",
        model="claude-haiku-4-5",
        max_tokens=16,
        cooldown=30.0,
    )
    return AnthropicProvider(**{**defaults, **kwargs})


def test_open_circuit_fails_instantly_without_calling_the_api():
    """Once tripped, generate() must short-circuit before any network call.

    This is what stops a dead API from stalling every request: the first
    failure trips the breaker, the rest degrade immediately.
    """
    provider = _provider()
    provider._trip_circuit()
    with pytest.raises(LLMUnavailable, match="retrying in"):
        provider.generate("system", "user")


def test_circuit_starts_closed():
    provider = _provider()
    assert provider._circuit_open_until == 0.0


def test_provider_advertises_the_configured_model():
    assert _provider(model="claude-sonnet-5").name == "claude-sonnet-5"
