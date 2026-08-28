"""Build the vector index from the active corpus.

Usage:
    python -m app.ingestion.build_index            # incremental upsert
    python -m app.ingestion.build_index --rebuild  # drop and rebuild
"""

import argparse

from app.config import get_settings
from ingestion.normalize import load_jsonl
from rag import vectorstore
from rag.embeddings import embed_texts

BATCH_SIZE = 64


def build_index(rebuild: bool = False) -> int:
    """Embed and index every standard in the active corpus. Returns the count."""
    settings = get_settings()
    corpus_path = settings.active_corpus()
    if not corpus_path.exists():
        raise FileNotFoundError(f"No corpus found at {corpus_path}")

    standards = load_jsonl(corpus_path)
    if not standards:
        raise ValueError(f"Corpus {corpus_path} is empty")

    if rebuild:
        vectorstore.reset()

    for start in range(0, len(standards), BATCH_SIZE):
        batch = standards[start : start + BATCH_SIZE]
        embeddings = embed_texts([s.embedding_text() for s in batch])
        vectorstore.add_standards(batch, embeddings)

    return len(standards)


def main() -> None:
    parser = argparse.ArgumentParser(description="Index the BIS catalogue corpus.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop the existing collection before indexing.",
    )
    args = parser.parse_args()

    settings = get_settings()
    print(f"Corpus:    {settings.active_corpus()}")
    print(f"Embedding: {settings.embedding_model}")
    print("Indexing (first run downloads the embedding model, ~90 MB)...")

    count = build_index(rebuild=args.rebuild)

    print(f"\nIndexed {count} standards into {settings.chroma_dir}")
    print(f"Total in collection: {vectorstore.count()}")
    for sector, sector_count in vectorstore.sector_counts().items():
        print(f"  {sector_count:>4}  {sector}")
    print("\nNext: uvicorn app.main:app --reload   ->   http://localhost:8000/docs")


if __name__ == "__main__":
    main()
