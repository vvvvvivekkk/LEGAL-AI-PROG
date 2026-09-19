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
