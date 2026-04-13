"""Circular moat and hole mask utilities."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

import numpy as np

from qdp_tdgl.config.models import CircularFeatureConfig

if TYPE_CHECKING:
    from qdp_tdgl.geometry.masks import StructuredGrid2D


def apply_circular_exclusions(
    cell_mask: np.ndarray,
    grid: StructuredGrid2D,
    features: Iterable[CircularFeatureConfig],
) -> np.ndarray:
    """Deactivate circular subsets of the active cell mask."""

    result = cell_mask.copy()
    x, y = grid.cell_center_mesh
    for feature in features:
        distance_sq = (x - feature.x0) ** 2 + (y - feature.y0) ** 2
        result &= distance_sq > feature.radius**2
    return result

