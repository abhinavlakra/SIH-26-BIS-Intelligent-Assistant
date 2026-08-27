"""Swappable LLM provider adapter.

Generation is the only stage that calls a hosted model — embeddings and
retrieval run locally. When no key is configured, `NullProvider` keeps the
service answering in extractive mode instead of failing the request.

To add a provider: implement `generate()` and register it in `get_provider()`.
"""

from functools import lru_cache
import time
from typing import Protocol

from app.config import get_settings


class LLMUnavailable(RuntimeError):
    """The provider could not serve this request; the caller should degrade."""


class LLMProvider(Protocol):
    name: str
    available: bool

    def generate(self, system: str, user: str) -> str: ...


class NullProvider:
    """Used when no API key is set — every call degrades to extractive mode."""

    name = "extractive (no LLM key configured)"
    available = False

    def generate(self, system: str, user: str) -> str:
        raise LLMUnavailable("No LLM API key configured")


class AnthropicProvider:
    """Claude via the Messages API.

    Works against api.anthropic.com directly (x-api-key) or any
    Anthropic-COMPATIBLE router such as agentrouter.org (`base_url` +
    `auth_token`, sent as `Authorization: Bearer`). Passing `auth_token` makes
    the SDK ignore any `ANTHROPIC_API_KEY` in the environment and send Bearer
    auth only — which is what those routers expect.

    Note: no `thinking` or `output_config.effort` is sent. Haiku 4.5 rejects
    those parameters, and omitting them is also correct on the Opus/Sonnet 5
    models (which run adaptive thinking by default), so the same adapter works
    whichever model is configured.

    Carries a small circuit breaker. If the API becomes unreachable — venue
    Wi-Fi dies mid-demo, say — only the first request pays the timeout; for the
    next `cooldown` seconds every call fails instantly, so the service degrades
    to extractive mode with no visible stall.
    """

    available = True

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int,
        timeout: float = 10.0,
        max_retries: int = 0,
        cooldown: float = 60.0,
        auth_token: str = "",
        base_url: str = "",
    ) -> None:
        import anthropic

        self._sdk = anthropic
        client_kwargs: dict = {"timeout": timeout, "max_retries": max_retries}
        if base_url.strip():
            client_kwargs["base_url"] = base_url.strip()
            # Some Anthropic-compatible routers (e.g. agentrouter.org) resell
            # Claude Code access and fingerprint the client: a request whose
            # User-Agent isn't the CLI is rejected with an
            # `unauthorized_client_error`. Presenting as the CLI clears that
            # gate. Only applied in router mode — api.anthropic.com direct keeps
            # the SDK's own User-Agent untouched.
            #
            # `Accept-Encoding: identity` disables response compression: this
            # env's httpx build has a broken decompressor (`process() takes no
            # keyword arguments`) that crashes on the gzip/br bodies the router
            # returns for larger answers. Asking for uncompressed bytes avoids
            # that decode path entirely.
            client_kwargs["default_headers"] = {
                "User-Agent": "claude-cli/2.1.0 (external, cli)",
                "x-app": "cli",
                "Accept-Encoding": "identity",
            }
        # Prefer a Bearer auth_token (third-party routers) over an x-api-key.
        # Pass exactly one: with only auth_token set, the SDK sends
        # `Authorization: Bearer` and does NOT read ANTHROPIC_API_KEY from the
        # environment, so a stray key in the shell can't shadow the router.
        if auth_token.strip():
            client_kwargs["auth_token"] = auth_token.strip()
        else:
            client_kwargs["api_key"] = api_key
        self._client = anthropic.Anthropic(**client_kwargs)
        self._model = model
        self._max_tokens = max_tokens
        self._cooldown = cooldown
        self._circuit_open_until = 0.0
        self.name = model

    def _trip_circuit(self) -> None:
        self._circuit_open_until = time.monotonic() + self._cooldown

    def generate(self, system: str, user: str) -> str:
        cooling_off = self._circuit_open_until - time.monotonic()
        if cooling_off > 0:
            raise LLMUnavailable(f"API unavailable, retrying in {cooling_off:.0f}s")

        sdk = self._sdk
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except sdk.AuthenticationError as exc:
            self._trip_circuit()
            raise LLMUnavailable("Anthropic rejected the API key") from exc
        except sdk.NotFoundError as exc:
            self._trip_circuit()
            raise LLMUnavailable(f"Unknown model {self._model!r}") from exc
        except sdk.RateLimitError as exc:
            self._trip_circuit()
            raise LLMUnavailable("Rate limited by the Anthropic API") from exc
        except sdk.APIStatusError as exc:
            self._trip_circuit()
            raise LLMUnavailable(f"Anthropic API error {exc.status_code}") from exc
        except sdk.APIConnectionError as exc:
            # Also covers APITimeoutError, which subclasses it.
            self._trip_circuit()
            raise LLMUnavailable("Could not reach the Anthropic API") from exc

        if response.stop_reason == "refusal":
            raise LLMUnavailable("The model declined to answer this request")

        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        if not text:
            raise LLMUnavailable("Model returned no text")

        self._circuit_open_until = 0.0
        return text


@lru_cache
def get_provider() -> LLMProvider:
    settings = get_settings()
    if not settings.llm_enabled:
        return NullProvider()
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            cooldown=settings.llm_circuit_cooldown_seconds,
            auth_token=settings.anthropic_auth_token,
            base_url=settings.anthropic_base_url,
        )
    # Unknown provider name: degrade rather than crash the service at import.
    return NullProvider()
