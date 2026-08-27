"""Local sentence-transformers embeddings.

Deliberately local rather than a hosted embedding API: it is free, works
offline, and keeps the judging demo independent of network availability.
The model (~90 MB) downloads once on first use and is then cached.
"""

from functools import lru_cache

from app.config import get_settings


@lru_cache
def _load_model():
    # Imported lazily so that merely importing this module (e.g. during test
    # collection) does not pay the model-loading cost.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed documents for indexing."""
    if not texts:
        return []
    vectors = _load_model().encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 64,
    )
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    """Embed a single search query."""
    return embed_texts([text])[0]


def embedding_dimension() -> int:
    return int(_load_model().get_sentence_embedding_dimension())
