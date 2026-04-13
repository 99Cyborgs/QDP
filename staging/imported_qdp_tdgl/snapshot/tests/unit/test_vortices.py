from __future__ import annotations

import numpy as np

from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.fields.linkvars import build_link_variables
from tdgl_rf.fields.vortices import compute_vortex_map
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D


def _analytic_vortex_field(grid: StructuredGrid2D, charge: int, x0: float, y0: float) -> np.ndarray:
    x, y = grid.cell_center_mesh
    angle = np.arctan2(y - y0, x - x0)
    return np.exp(1j * charge * angle)


def test_compute_vortex_map_detects_single_charge_vortices() -> None:
    grid = StructuredGrid2D(nx=16, ny=16, lx=16.0, ly=16.0)
    mask = GeometryMask(cell_active=np.ones((grid.nx, grid.ny), dtype=bool))
    links = build_link_variables(grid, VectorPotential.zeros(grid))
    core_x = grid.x_edges[8]
    core_y = grid.y_edges[8]

    positive = compute_vortex_map(_analytic_vortex_field(grid, charge=1, x0=core_x, y0=core_y), links, mask)
    negative = compute_vortex_map(_analytic_vortex_field(grid, charge=-1, x0=core_x, y0=core_y), links, mask)

    assert int(np.sum(positive)) == 1
    assert int(np.sum(np.abs(positive))) == 1
    assert positive[7, 7] == 1

    assert int(np.sum(negative)) == -1
    assert int(np.sum(np.abs(negative))) == 1
    assert negative[7, 7] == -1
