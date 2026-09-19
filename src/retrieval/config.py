"""Retrieval configuration knobs.

These are the ablation dials phase 6 will sweep: retrieval mode (dense-only /
FTS-only / hybrid), whether cross-encoder reranking is applied, and the k / N
sizes (N = fused candidates fetched before reranking, k = final context size
handed to generation).
"""

from __future__ import annotations

from dataclasses import dataclass

VALID_MODES = ("dense", "fts", "hybrid")

DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-base"


@dataclass
class RetrievalConfig:
    mode: str = "hybrid"
    use_reranker: bool = True
    k: int = 5
    n: int = 20
    reranker_model: str = DEFAULT_RERANKER_MODEL

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {self.mode!r}")
        if self.k < 1:
            raise ValueError(f"k must be >= 1, got {self.k}")
        if self.n < self.k:
            raise ValueError(f"n ({self.n}) must be >= k ({self.k})")
