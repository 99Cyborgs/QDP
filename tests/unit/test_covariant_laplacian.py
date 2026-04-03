from __future__ import annotations

import numpy as np

from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.fields.linkvars import build_link_variables
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.solvers.linear_ops import apply_covariant_laplacian


def test_constant_state_covariant_laplacian_is_zero() -> None:
    grid = StructuredGrid2D(nx=12, ny=9, lx=6.0, ly=4.5)
    mask = GeometryMask(cell_active=np.ones((grid.nx, grid.ny), dtype=bool))
    psi = np.ones((grid.nx, grid.ny), dtype=np.complex128)
    potential = VectorPotential.zeros(grid)
    laplacian = apply_covariant_laplacian(grid, mask, psi, build_link_variables(grid, potential))
    assert np.linalg.norm(laplacian) < 1.0e-12

