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


# Candidate pool depth. The cross-encoder can only reorder what the bi-encoder
# fetched, so n has to be deep enough that *it* decides the top-k rather than
# the fused RRF ranking. On the NDA corpus the clause answering "what happens
# if the receiving party discloses..." sits at fused rank 39 -- a pool of 20
# never reaches it, whatever the reranker does.
DEFAULT_N = 50


@dataclass
class RetrievalConfig:
    mode: str = "hybrid"
    use_reranker: bool = True
    k: int = 5
    n: int = DEFAULT_N
    reranker_model: str = DEFAULT_RERANKER_MODEL

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {self.mode!r}")
        if self.k < 1:
            raise ValueError(f"k must be >= 1, got {self.k}")
        if self.n < self.k:
            raise ValueError(f"n ({self.n}) must be >= k ({self.k})")
