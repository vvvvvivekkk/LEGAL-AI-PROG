"""Thin, swappable embedding interface.

Every embedding backend implements `embed(texts) -> np.ndarray`. Downstream
code (src/indexing, src/retrieval) depends only on this interface, not on
any specific model, so swapping in BGE-M3 / GTE-Large for real experiments
(see docs/architecture.md §5) means adding a new backend module, not
touching the callers.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class EmbeddingModel(Protocol):
    """Anything with this method can be used as an embedding backend."""

    def embed(self, texts: list[str]) -> np.ndarray:
        ...
