from __future__ import annotations

import numpy as np

from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.fields.observables import build_weight_profile, compute_frequency_shift_proxy
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.solvers.state import SimulationState


def _state_with_psi(grid: StructuredGrid2D, psi: np.ndarray) -> SimulationState:
    zero = VectorPotential.zeros(grid)
    return SimulationState(
        grid=grid,
        t=0.0,
        step=0,
        psi=psi,
        phi=np.zeros((grid.nx, grid.ny), dtype=float),
        A=zero,
        A_dot=zero,
    )


def test_build_weight_profile_excludes_inactive_cells_from_normalization() -> None:
    grid = StructuredGrid2D(nx=8, ny=8, lx=8.0, ly=8.0)
    full_mask = GeometryMask(cell_active=np.ones((grid.nx, grid.ny), dtype=bool))
    masked_cells = np.ones((grid.nx, grid.ny), dtype=bool)
    masked_cells[2:6, 2:6] = False
    masked_mask = GeometryMask(cell_active=masked_cells)

    full_weights = build_weight_profile(grid, "uniform", mask=full_mask)
    masked_weights = build_weight_profile(grid, "uniform", mask=masked_mask)

    psi_full = np.ones((grid.nx, grid.ny), dtype=np.complex128)
    psi_masked = np.ones((grid.nx, grid.ny), dtype=np.complex128)
    psi_masked[~masked_mask.cell_active] = 0.0

    full_shift = compute_frequency_shift_proxy(_state_with_psi(grid, psi_full), full_weights, {"c_f": 1.0})
    masked_shift = compute_frequency_shift_proxy(_state_with_psi(grid, psi_masked), masked_weights, {"c_f": 1.0})

    assert np.isclose(np.sum(full_weights) * grid.cell_area, 1.0)
    assert np.isclose(np.sum(masked_weights[masked_mask.cell_active]) * grid.cell_area, 1.0)
    assert np.all(masked_weights[~masked_mask.cell_active] == 0.0)
    assert np.isclose(full_shift, 0.0)
    assert np.isclose(masked_shift, 0.0)


def test_build_weight_profile_handles_empty_active_mask() -> None:
    grid = StructuredGrid2D(nx=8, ny=8, lx=8.0, ly=8.0)
    empty_mask = GeometryMask(cell_active=np.zeros((grid.nx, grid.ny), dtype=bool))

    weights = build_weight_profile(grid, "uniform", mask=empty_mask)

    assert np.all(weights == 0.0)
