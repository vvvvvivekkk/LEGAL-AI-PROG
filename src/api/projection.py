"""2D projection of embedding vectors for the Evaluation embedding-space view.

PCA via NumPy SVD — no extra dependency (sklearn/umap not required). Reduces the
chunk embedding matrix to two components so the index can be scatter-plotted,
colored by source document.
"""

from __future__ import annotations

import numpy as np


def pca_2d(vectors) -> np.ndarray:
    """Project an (N, D) matrix to (N, 2) via the top-2 principal components.

    Returns an (N, 2) float array. Degenerate inputs (0 rows, or fewer than 2
    usable components) are padded with zeros so the shape is always (N, 2).
    """
    X = np.asarray(vectors, dtype=float)
    if X.ndim != 2 or X.shape[0] == 0:
        return np.empty((0, 2), dtype=float)

    n = X.shape[0]
    centered = X - X.mean(axis=0, keepdims=True)
    try:
        _, _, vt = np.linalg.svd(centered, full_matrices=False)
    except np.linalg.LinAlgError:
        return np.zeros((n, 2), dtype=float)

    components = vt[:2]  # (<=2, D)
    coords = centered @ components.T  # (N, <=2)
    if coords.shape[1] < 2:
        coords = np.hstack([coords, np.zeros((n, 2 - coords.shape[1]))])
    return coords
