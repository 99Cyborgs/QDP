from __future__ import annotations

import numpy as np

from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.fields.linkvars import build_link_variables
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.solvers.linear_ops import (
    ActiveCellMap,
    apply_covariant_laplacian,
    build_active_covariant_laplacian_matrix,
    build_active_scalar_laplacian_matrix,
    build_covariant_laplacian_matrix,
    build_scalar_laplacian_matrix,
)


def _masked_geometry() -> tuple[StructuredGrid2D, GeometryMask]:
    grid = StructuredGrid2D(nx=7, ny=6, lx=3.5, ly=3.0)
    cell_active = np.ones((grid.nx, grid.ny), dtype=bool)
    cell_active[3, 2] = False
    cell_active[1, 4] = False
    return grid, GeometryMask(cell_active=cell_active)


def test_covariant_matrix_matches_direct_application_on_masked_grid() -> None:
    grid, mask = _masked_geometry()
    rng = np.random.default_rng(123)
    psi = rng.standard_normal((grid.nx, grid.ny)) + 1j * rng.standard_normal((grid.nx, grid.ny))
    psi[~mask.cell_active] = 0.0

    potential = VectorPotential(
        ax=0.1 * rng.standard_normal((grid.nx + 1, grid.ny)),
        ay=0.1 * rng.standard_normal((grid.nx, grid.ny + 1)),
    )
    links = build_link_variables(grid, potential)

    direct = apply_covariant_laplacian(grid, mask, psi, links)
    matrix = build_covariant_laplacian_matrix(grid, mask, links)
    matrix_applied = (matrix @ psi.ravel(order="C")).reshape((grid.nx, grid.ny), order="C")

    np.testing.assert_allclose(matrix_applied, direct, rtol=1.0e-12, atol=1.0e-12)


def test_active_operators_match_restricted_full_operators() -> None:
    grid, mask = _masked_geometry()
    rng = np.random.default_rng(321)
    potential = VectorPotential(
        ax=0.1 * rng.standard_normal((grid.nx + 1, grid.ny)),
        ay=0.1 * rng.standard_normal((grid.nx, grid.ny + 1)),
    )
    links = build_link_variables(grid, potential)
    active_cells = ActiveCellMap.from_mask(mask)

    full_covariant = build_covariant_laplacian_matrix(grid, mask, links)
    active_covariant = build_active_covariant_laplacian_matrix(grid, mask, links, active_cells)
    np.testing.assert_allclose(
        active_covariant.toarray(),
        active_cells.restrict_matrix(full_covariant).toarray(),
        rtol=1.0e-12,
        atol=1.0e-12,
    )

    full_scalar = build_scalar_laplacian_matrix(grid, mask)
    active_scalar = build_active_scalar_laplacian_matrix(grid, mask, active_cells)
    np.testing.assert_allclose(
        active_scalar.toarray(),
        active_cells.restrict_matrix(full_scalar).toarray(),
        rtol=1.0e-12,
        atol=1.0e-12,
    )

