"""Shared pytest fixtures for the Legal-RAG test suite."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA_DIR = REPO_ROOT / "data" / "sample"


@pytest.fixture
def sample_data_dir() -> Path:
    """Path to the small synthetic statute corpus under data/sample/."""
    return SAMPLE_DATA_DIR


@pytest.fixture
def sample_files(sample_data_dir: Path) -> list[Path]:
    """All .txt files in the sample corpus."""
    return sorted(sample_data_dir.glob("*.txt"))


@pytest.fixture(scope="session")
def real_embedder():
    """The real default embedding backend, shared across the whole test session.

    Loading `all-MiniLM-L6-v2` needs network access to huggingface.co on
    first use. Any test that needs actual embeddings should depend on this
    fixture; if the model can't be fetched (e.g. an environment's egress
    policy blocks huggingface.co), every dependent test skips with a clear
    reason instead of failing -- this exercises real code, not a mock, and
    just can't complete without a reachable model source.
    """
    from src.embedding.sentence_transformer import SentenceTransformerEmbedder

    model = SentenceTransformerEmbedder()
    try:
        model.embed(["warmup"])
    except Exception as exc:  # noqa: BLE001 - network/environment errors vary by backend
        pytest.skip(f"sentence-transformers model unavailable in this environment: {exc}")
    return model
