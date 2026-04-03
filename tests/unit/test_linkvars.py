from __future__ import annotations

import numpy as np

from tdgl_rf.fields.currents import compute_supercurrent
from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.fields.linkvars import apply_gauge_transform, build_link_variables
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.solvers.linear_ops import apply_covariant_laplacian


def test_link_variables_and_gauge_covariance() -> None:
    grid = StructuredGrid2D(nx=10, ny=8, lx=5.0, ly=4.0)
    mask = GeometryMask(cell_active=np.ones((grid.nx, grid.ny), dtype=bool))
    rng = np.random.default_rng(42)

    amplitude = 0.75 + 0.05 * rng.standard_normal((grid.nx, grid.ny))
    phase = 0.3 * rng.standard_normal((grid.nx, grid.ny))
    psi = amplitude * np.exp(1j * phase)
    ax = 0.05 * rng.standard_normal((grid.nx + 1, grid.ny))
    ay = 0.05 * rng.standard_normal((grid.nx, grid.ny + 1))
    potential = VectorPotential(ax=ax, ay=ay)

    chi = np.zeros((grid.nx, grid.ny))
    chi[1:-1, 1:-1] = 0.2 * rng.standard_normal((grid.nx - 2, grid.ny - 2))
    psi_t, potential_t = apply_gauge_transform(grid, psi, potential, chi)

    lap = apply_covariant_laplacian(grid, mask, psi, build_link_variables(grid, potential))
    lap_t = apply_covariant_laplacian(grid, mask, psi_t, build_link_variables(grid, potential_t))
    rel_err = np.linalg.norm(lap_t - np.exp(1j * chi) * lap) / np.linalg.norm(lap)
    assert rel_err < 1.0e-10

    j = compute_supercurrent(grid, mask, psi, build_link_variables(grid, potential))
    j_t = compute_supercurrent(grid, mask, psi_t, build_link_variables(grid, potential_t))
    assert np.linalg.norm(j.jx - j_t.jx) / np.linalg.norm(j.jx) < 1.0e-10
    assert np.linalg.norm(j.jy - j_t.jy) / np.linalg.norm(j.jy) < 1.0e-10

