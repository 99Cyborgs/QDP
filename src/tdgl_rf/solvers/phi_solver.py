"""Scalar-potential solve with zero-mean gauge fixing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tdgl_rf.fields.currents import CurrentField, divergence
from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.exceptions import SolverDivergenceError
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.solvers.linear_ops import ActiveCellMap, build_active_scalar_laplacian_matrix
from tdgl_rf.solvers.scipy_backend import LinearSolveResult, LinearSolverBackend


@dataclass(frozen=True)
class PhiSolveStats:
    iterations: int
    residual_norm: float
    mean_removed: float
    method: str


def _count_connected_components(cell_active: np.ndarray) -> int:
    active = np.asarray(cell_active, dtype=bool)
    if not np.any(active):
        return 0

    visited = np.zeros_like(active, dtype=bool)
    component_count = 0
    starts = np.argwhere(active)
    for start_i, start_j in starts:
        if visited[start_i, start_j]:
            continue
        component_count += 1
        stack = [(int(start_i), int(start_j))]
        visited[start_i, start_j] = True
        while stack:
            i, j = stack.pop()
            if i > 0 and active[i - 1, j] and not visited[i - 1, j]:
                visited[i - 1, j] = True
                stack.append((i - 1, j))
            if i + 1 < active.shape[0] and active[i + 1, j] and not visited[i + 1, j]:
                visited[i + 1, j] = True
                stack.append((i + 1, j))
            if j > 0 and active[i, j - 1] and not visited[i, j - 1]:
                visited[i, j - 1] = True
                stack.append((i, j - 1))
            if j + 1 < active.shape[1] and active[i, j + 1] and not visited[i, j + 1]:
                visited[i, j + 1] = True
                stack.append((i, j + 1))
    return component_count


class ScalarPotentialSolver:
    """Cached scalar-potential solver with zero-mean gauge fixing."""

    def __init__(
        self,
        grid: StructuredGrid2D,
        mask: GeometryMask,
        sigma_n: float,
        backend: LinearSolverBackend,
    ) -> None:
        self.grid = grid
        self.mask = mask
        self.sigma_n = sigma_n
        self.backend = backend
        self.active_cells = ActiveCellMap.from_mask(mask)
        self.reference_index = 0
        self.cache_key = f"phi:{id(self)}"
        if sigma_n == 0.0 or self.active_cells.count == 0:
            self.laplacian_active = None
            self.reduced_matrix = None
            return
        component_count = _count_connected_components(mask.cell_active)
        if component_count > 1:
            raise SolverDivergenceError(
                f"scalar-potential solve requires a connected active mask; found {component_count} disconnected components"
            )
        self.laplacian_active = (-sigma_n) * build_active_scalar_laplacian_matrix(grid, mask, self.active_cells)
        self.reduced_matrix = self._build_reference_reduced_matrix() if self.active_cells.count > 1 else None

    def _build_reference_reduced_matrix(self):
        assert self.laplacian_active is not None
        if self.active_cells.count <= 1:
            return None
        keep = np.arange(1, self.active_cells.count, dtype=np.int64)
        return self.laplacian_active[keep][:, keep].tocsr()

    def _build_rhs(self, supercurrent: CurrentField, a_dot: VectorPotential) -> np.ndarray:
        rhs = divergence(self.grid, supercurrent) - self.sigma_n * divergence(self.grid, CurrentField(jx=a_dot.ax, jy=a_dot.ay))
        return self.active_cells.flatten_active(rhs)

    def solve(
        self,
        supercurrent: CurrentField,
        a_dot: VectorPotential,
        linear_solver: str,
        rtol: float,
        atol: float,
        max_it: int,
    ) -> tuple[np.ndarray, PhiSolveStats]:
        """Solve for phi on the current RHS with cached linear operators."""

        phi = np.zeros((self.grid.nx, self.grid.ny), dtype=float)
        if self.sigma_n == 0.0 or self.active_cells.count == 0:
            return phi, PhiSolveStats(iterations=0, residual_norm=0.0, mean_removed=0.0, method="disabled")

        rhs_active = self._build_rhs(supercurrent, a_dot)
        rhs_mean = float(np.mean(rhs_active))
        rhs_active = rhs_active - rhs_mean
        if np.allclose(rhs_active, 0.0, atol=atol, rtol=rtol):
            return phi, PhiSolveStats(iterations=0, residual_norm=0.0, mean_removed=rhs_mean, method="zero_rhs")

        if rhs_active.size == 1:
            return phi, PhiSolveStats(iterations=0, residual_norm=float(abs(rhs_active[0])), mean_removed=rhs_mean, method="single_cell")

        assert self.laplacian_active is not None
        assert self.reduced_matrix is not None
        reduced_rhs = rhs_active[1:]
        result: LinearSolveResult = self.backend.solve(
            self.reduced_matrix,
            reduced_rhs,
            method=linear_solver,
            rtol=rtol,
            atol=atol,
            max_it=max_it,
            cache_key=self.cache_key,
        )
        phi_active = np.zeros(self.active_cells.count, dtype=float)
        phi_active[1:] = np.asarray(result.solution, dtype=float)
        phi_active -= np.mean(phi_active)
        phi = self.active_cells.scatter_active(phi_active, dtype=float)
        residual = self.laplacian_active @ phi_active - rhs_active
        return phi, PhiSolveStats(
            iterations=result.iterations,
            residual_norm=float(np.linalg.norm(residual)),
            mean_removed=rhs_mean,
            method=result.method,
        )


def solve_scalar_potential(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    supercurrent: CurrentField,
    a_dot: VectorPotential,
    sigma_n: float,
    linear_solver: str,
    rtol: float,
    atol: float,
    max_it: int,
    backend: LinearSolverBackend,
) -> tuple[np.ndarray, PhiSolveStats]:
    """Solve the discrete scalar-potential equation with zero-mean gauge fixing."""

    solver = ScalarPotentialSolver(grid=grid, mask=mask, sigma_n=sigma_n, backend=backend)
    return solver.solve(
        supercurrent=supercurrent,
        a_dot=a_dot,
        linear_solver=linear_solver,
        rtol=rtol,
        atol=atol,
        max_it=max_it,
    )
