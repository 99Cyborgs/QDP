from __future__ import annotations

import numpy as np

from tdgl_rf.config.models import CircularFeatureConfig
from tdgl_rf.fields.currents import CurrentField
from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.geometry.moat import apply_circular_exclusions
from tdgl_rf.solvers.phi_solver import ScalarPotentialSolver
from tdgl_rf.solvers.scipy_backend import SciPyLinearBackend


def test_scalar_potential_solver_enforces_zero_mean_gauge() -> None:
    grid = StructuredGrid2D(nx=6, ny=5, lx=3.0, ly=2.5)
    mask = GeometryMask(cell_active=np.ones((grid.nx, grid.ny), dtype=bool))
    backend = SciPyLinearBackend()
    solver = ScalarPotentialSolver(grid=grid, mask=mask, sigma_n=1.0, backend=backend)

    jx = np.zeros((grid.nx + 1, grid.ny), dtype=float)
    jy = np.zeros((grid.nx, grid.ny + 1), dtype=float)
    jx[2, 2] = 1.0
    jx[3, 2] = -1.0
    supercurrent = CurrentField(jx=jx, jy=jy)
    a_dot = VectorPotential.zeros(grid)

    phi, stats = solver.solve(supercurrent, a_dot, linear_solver="cg", rtol=1.0e-10, atol=1.0e-12, max_it=500)

    assert abs(np.mean(phi[mask.cell_active])) < 1.0e-12
    assert stats.residual_norm < 1.0e-8


def test_scalar_potential_solver_keeps_sparse_reference_reduction_for_masked_geometry() -> None:
    grid = StructuredGrid2D(nx=64, ny=32, lx=32.0, ly=16.0)
    cell_active = np.ones((grid.nx, grid.ny), dtype=bool)
    moat = CircularFeatureConfig(x0=16.0, y0=8.0, radius=2.0)
    cell_active = apply_circular_exclusions(cell_active, grid, [moat])
    mask = GeometryMask(cell_active=cell_active)
    backend = SciPyLinearBackend()
    solver = ScalarPotentialSolver(grid=grid, mask=mask, sigma_n=1.0, backend=backend)

    assert solver.reduced_matrix is not None
    assert solver.reduced_matrix.shape == (solver.active_cells.count - 1, solver.active_cells.count - 1)
    assert solver.reduced_matrix.nnz < 10 * solver.active_cells.count
