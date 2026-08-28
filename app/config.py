"""Central configuration, resolved from environment / `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM (generation only) -------------------------------------------
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    # For Anthropic-COMPATIBLE third-party routers (e.g. agentrouter.org):
    # a Bearer auth token + the router's base URL. When `anthropic_auth_token`
    # is set it takes precedence over `anthropic_api_key` — the SDK then sends
    # `Authorization: Bearer` instead of the `x-api-key` header. Leave
    # `anthropic_base_url` blank to talk to api.anthropic.com directly; when set
    # it must NOT include `/v1` (the SDK appends `/v1/messages`).
    anthropic_auth_token: str = ""
    anthropic_base_url: str = ""
    # Model IDs are complete as-is — never append a date suffix.
    anthropic_model: str = "claude-haiku-4-5"
    llm_max_tokens: int = 2048
    # Keep these tight: if the API is unreachable during a demo we want to fall
    # back to extractive mode in seconds, not sit through long SDK retries.
    llm_timeout_seconds: float = 10.0
    llm_max_retries: int = 0
    # After a failure, stop attempting the API for this long so that only the
    # first affected request pays the timeout and the rest degrade instantly.
    llm_circuit_cooldown_seconds: float = 60.0

    # --- Embeddings (local, offline, free) -------------------------------
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Vector store ----------------------------------------------------
    chroma_dir: Path = DATA_DIR / "chroma"
    collection_name: str = "bis_standards"

    # --- Corpus ----------------------------------------------------------
    seed_corpus: Path = DATA_DIR / "seed" / "standards.jsonl"
    processed_corpus: Path = DATA_DIR / "processed" / "standards.jsonl"
    raw_dir: Path = DATA_DIR / "raw"

    # --- Retrieval defaults ----------------------------------------------
    default_top_k: int = 5
    default_top_n: int = 5

    # --- Optional public-catalogue collector -----------------------------
    data_gov_in_api_key: str = ""
    data_gov_in_resource_id: str = ""

    @property
    def llm_enabled(self) -> bool:
        """True when a real LLM can be called; otherwise we degrade gracefully."""
        if self.llm_provider == "anthropic":
            return bool(
                self.anthropic_api_key.strip() or self.anthropic_auth_token.strip()
            )
        return False

    def active_corpus(self) -> Path:
        """Prefer the collector-built corpus, fall back to the bundled seed."""
        if self.processed_corpus.exists():
            return self.processed_corpus
        return self.seed_corpus


@lru_cache
def get_settings() -> Settings:
    return Settings()
