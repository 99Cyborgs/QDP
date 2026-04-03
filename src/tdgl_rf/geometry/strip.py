"""Strip-geometry helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from tdgl_rf.geometry.masks import StructuredGrid2D


def build_strip_mask(grid: StructuredGrid2D) -> np.ndarray:
    """Return the fully active strip mask."""

    return np.ones((grid.nx, grid.ny), dtype=bool)
