from __future__ import annotations

import numpy as np

from tdgl_rf.fields.currents import compute_normal_current, compute_supercurrent
from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.fields.linkvars import build_link_variables
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D


def test_constant_state_currents_are_zero() -> None:
    grid = StructuredGrid2D(nx=12, ny=10, lx=6.0, ly=5.0)
    mask = GeometryMask(cell_active=np.ones((grid.nx, grid.ny), dtype=bool))
    psi = np.ones((grid.nx, grid.ny), dtype=np.complex128)
    phi = np.zeros((grid.nx, grid.ny), dtype=float)
    potential = VectorPotential.zeros(grid)
    supercurrent = compute_supercurrent(grid, mask, psi, build_link_variables(grid, potential))
    normal_current = compute_normal_current(grid, mask, phi, potential, sigma_n=1.0)
    assert np.linalg.norm(supercurrent.jx) < 1.0e-12
    assert np.linalg.norm(supercurrent.jy) < 1.0e-12
    assert np.linalg.norm(normal_current.jx) < 1.0e-12
    assert np.linalg.norm(normal_current.jy) < 1.0e-12

