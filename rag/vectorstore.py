"""Persistent Chroma vector store holding the BIS catalogue.

Chroma metadata values must be scalars, so list fields are stored as
comma-joined strings and split back on read. Adding a list field to `Standard`
means adding it to `_LIST_FIELDS` here — both directions are driven off that one
tuple, so there is no second place to forget.
"""

import threading
from typing import Any

from app.config import get_settings
from app.models import Standard

_LIST_FIELDS = (
    "ics_codes",
    "keywords",
    "normative_refs",
    "test_methods",
    "supersedes",
)

# Chroma rejects None, so optional scalars need a sentinel on write and a
# reverse mapping on read.
_NULLABLE_SCALARS = ("certification_scheme",)

# Populated lazily by `all_standards()`; dropped whenever the index changes.
_ALL_CACHE: list[Standard] | None = None
# Lookup index over the same data, keyed by normalised IS number. At 95 records
# a linear scan was free; at 24k it is not — graph expansion alone does ~20
# lookups per request.
_BY_REF_CACHE: dict[str, Standard] | None = None

# Guards construction of the Chroma client.
#
# This is NOT decoration. FastAPI runs sync endpoints in a threadpool, and the
# dashboard fires /coverage, /facets, /stats and /analytics in parallel on
# mount. `functools.lru_cache` does not serialise the call it wraps — on a cache
# miss every waiting thread runs the body — so several threads would each build
# a `PersistentClient` at once and race Chroma's process-global
# `SharedSystemClient._identifier_to_system` registry. That surfaced as
# intermittent 500s: `KeyError: '<chroma dir>'` and
# `AttributeError: 'RustBindingsAPI' object has no attribute 'bindings'`,
# on some page loads and not others.
_CLIENT_LOCK = threading.Lock()
_CLIENT: Any = None


def _client():
    """The process-wide Chroma client, built exactly once."""
    global _CLIENT
    # Fast path: an already-built client needs no lock (reference reads are
    # atomic under the GIL).
    if _CLIENT is not None:
        return _CLIENT

    with _CLIENT_LOCK:
        # Re-check: another thread may have built it while we waited.
        if _CLIENT is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            settings = get_settings()
            settings.chroma_dir.mkdir(parents=True, exist_ok=True)
            _CLIENT = chromadb.PersistentClient(
                path=str(settings.chroma_dir),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
            )
    return _CLIENT


def _client_cache_clear() -> None:
    """Drop the client so the next call rebuilds it.

    Named to match the `lru_cache` API this replaced — `tests/conftest.py`
    calls `vectorstore._client.cache_clear()` after pointing the settings at a
    temporary directory.
    """
    global _CLIENT
    with _CLIENT_LOCK:
        _CLIENT = None


_client.cache_clear = _client_cache_clear


def get_collection():
    """The single collection of indexed standards (created on first access)."""
    return _client().get_or_create_collection(
        name=get_settings().collection_name,
        # Cosine distance pairs with the normalized embeddings we produce.
        metadata={"hnsw:space": "cosine"},
    )


def to_metadata(standard: Standard) -> dict[str, Any]:
    data = standard.model_dump()
    for field in _LIST_FIELDS:
        # IS numbers contain commas ("IS 1893 (Part 1) : 2016" does not, but
        # some titles do), so use a separator that cannot appear in a reference.
        data[field] = " | ".join(data.get(field) or [])
    # Chroma rejects None values.
    data["year"] = data.get("year") or 0
    for field in _NULLABLE_SCALARS:
        data[field] = data.get(field) or ""
    # Denormalised for cheap filtering without re-parsing the committee code.
    data["department_code"] = standard.department_code()
    return data


def from_metadata(metadata: dict[str, Any]) -> Standard:
    data = dict(metadata)
    for field in _LIST_FIELDS:
        raw = data.get(field) or ""
        separator = "|" if "|" in raw else ","
        data[field] = [part.strip() for part in raw.split(separator) if part.strip()]
    if not data.get("year"):
        data["year"] = None
    for field in _NULLABLE_SCALARS:
        if not data.get(field):
            data[field] = None
    # Not a Standard field — it is derived on write for filtering only.
    data.pop("department_code", None)
    return Standard.model_validate(data)


def add_standards(standards: list[Standard], embeddings: list[list[float]]) -> None:
    """Upsert standards, keyed by IS number so re-indexing is idempotent."""
    if not standards:
        return
    global _ALL_CACHE, _BY_REF_CACHE
    _ALL_CACHE = _BY_REF_CACHE = None
    get_collection().upsert(
        ids=[s.is_number for s in standards],
        embeddings=embeddings,
        documents=[s.embedding_text() for s in standards],
        metadatas=[to_metadata(s) for s in standards],
    )


def query(
    embedding: list[float],
    top_k: int,
    where: dict[str, Any] | None = None,
) -> list[tuple[Standard, float]]:
    """Nearest standards as `(standard, score)`, score in 0-1 (higher is closer)."""
    collection = get_collection()
    if collection.count() == 0:
        return []

    result = collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, collection.count()),
        where=where or None,
        include=["metadatas", "distances"],
    )

    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    hits: list[tuple[Standard, float]] = []
    for metadata, distance in zip(metadatas, distances):
        # Cosine distance is in [0, 2]; map to a 0-1 similarity score.
        score = max(0.0, min(1.0, 1.0 - float(distance)))
        hits.append((from_metadata(metadata), score))
    return hits


def count() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0


def all_standards() -> list[Standard]:
    """Every indexed standard.

    The corpus is small enough (hundreds, not millions) that browse, facets and
    graph traversal are all cheaper as in-process scans than as a second store.
    Cached per-process and invalidated by `reset()`.

    Concurrent callers may both rebuild the cache on a cold start. That is
    wasted work, not a correctness problem — the list is immutable once built
    and the rebind is atomic — so it is not worth a lock on the read path.
    """
    global _ALL_CACHE
    if _ALL_CACHE is not None:
        return _ALL_CACHE

    collection = get_collection()
    if collection.count() == 0:
        return []
    metadatas = collection.get(include=["metadatas"]).get("metadatas") or []
    standards = [from_metadata(m) for m in metadatas if m]
    standards.sort(key=lambda s: s.is_number)
    _ALL_CACHE = standards
    return standards


def by_reference() -> dict[str, Standard]:
    """Every standard keyed by its normalised IS number.

    Built once per corpus load. Callers that need many lookups (graph
    traversal, spec analysis, the detail view) should use this rather than
    calling `get_one` in a loop.
    """
    global _BY_REF_CACHE
    if _BY_REF_CACHE is not None:
        return _BY_REF_CACHE
    index = {_normalise_ref(s.is_number): s for s in all_standards()}
    _BY_REF_CACHE = index
    return index


def get_one(is_number: str) -> Standard | None:
    """Exact lookup by IS number, case- and whitespace-insensitive."""
    return by_reference().get(_normalise_ref(is_number))


def _normalise_ref(is_number: str) -> str:
    """Canonical form for comparing IS references.

    The catalogue writes the same standard as 'IS 1893 (Part 1):2016',
    'IS 1893 (Part 1) : 2016' and 'IS 1893(Part 1):2016'. Strip spacing and
    case so cross-references resolve regardless of which form was authored.
    """
    return "".join((is_number or "").split()).upper()


def sector_counts() -> dict[str, int]:
    """Standards per sector — surfaced by /api/stats for the demo."""
    counts: dict[str, int] = {}
    for standard in all_standards():
        sector = standard.sector or "Unclassified"
        counts[sector] = counts.get(sector, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def reset() -> None:
    """Drop the collection so the index can be rebuilt from scratch."""
    global _ALL_CACHE, _BY_REF_CACHE
    _ALL_CACHE = _BY_REF_CACHE = None
    try:
        _client().delete_collection(get_settings().collection_name)
    except Exception:
        # Nothing to delete on a first run.
        pass
