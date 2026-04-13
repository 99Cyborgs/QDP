"""Sparse linear operators for TDGL and scalar-potential solves."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse

from qdp_tdgl.fields.linkvars import LinkVariables
from qdp_tdgl.geometry.masks import GeometryMask, StructuredGrid2D


def _flat_index(i: int, j: int, ny: int) -> int:
    return i * ny + j


@dataclass(frozen=True)
class ActiveCellMap:
    """Indexing helper for active cells on the structured grid."""

    cell_active: np.ndarray
    flat_mask: np.ndarray
    indices: np.ndarray
    lookup: np.ndarray

    @classmethod
    def from_mask(cls, mask: GeometryMask) -> "ActiveCellMap":
        cell_active = mask.cell_active
        flat_mask = cell_active.ravel(order="C")
        indices = np.flatnonzero(flat_mask)
        lookup = np.full(cell_active.shape, -1, dtype=np.int64)
        lookup.ravel(order="C")[flat_mask] = np.arange(indices.size, dtype=np.int64)
        return cls(cell_active=cell_active, flat_mask=flat_mask, indices=indices, lookup=lookup)

    @property
    def count(self) -> int:
        return int(self.indices.size)

    def flatten_active(self, field: np.ndarray) -> np.ndarray:
        """Extract active entries from a cell-centered field."""

        return np.take(np.asarray(field).ravel(order="C"), self.indices)

    def scatter_active(self, values: np.ndarray, dtype) -> np.ndarray:
        """Scatter active values back onto the full cell grid."""

        full = np.zeros(self.cell_active.shape, dtype=dtype)
        full.ravel(order="C")[self.flat_mask] = np.asarray(values)
        return full

    def restrict_matrix(self, matrix: sparse.spmatrix) -> sparse.csr_matrix:
        """Restrict a full cell-centered matrix to the active-cell subspace."""

        indices = self.indices
        return matrix[indices][:, indices].tocsr()


@dataclass(frozen=True)
class MeanZeroReducer:
    """Reduction helper for zero-mean constrained linear solves.

    The basis spans the subspace whose entries sum to zero by expressing the final degree of
    freedom as the negative sum of the others. This removes the null mode without introducing a
    separate Lagrange-multiplier block.
    """

    size: int
    basis: sparse.csr_matrix

    @classmethod
    def from_size(cls, size: int) -> "MeanZeroReducer":
        if size < 2:
            basis = sparse.csr_matrix((size, 0), dtype=float)
        else:
            base = np.arange(size - 1, dtype=np.int64)
            cols = np.concatenate([base, base])
            rows = np.concatenate([base, np.full(size - 1, size - 1, dtype=np.int64)])
            data = np.concatenate([np.ones(size - 1, dtype=float), -np.ones(size - 1, dtype=float)])
            basis = sparse.csr_matrix((data, (rows, cols)), shape=(size, size - 1))
        return cls(size=size, basis=basis)

    def reduce_rhs(self, rhs: np.ndarray) -> np.ndarray:
        """Project a mean-zero right-hand side into the reduced coordinates."""

        return np.asarray(self.basis.T @ rhs).reshape(-1)

    def reduce_matrix(self, matrix: sparse.spmatrix) -> sparse.csr_matrix:
        """Project a mean-zero-constrained matrix into the reduced coordinates."""

        return (self.basis.T @ matrix @ self.basis).tocsr()

    def expand_solution(self, reduced_solution: np.ndarray) -> np.ndarray:
        """Lift a reduced solution back into the constrained full space."""

        return np.asarray(self.basis @ reduced_solution).reshape(-1)


def apply_covariant_laplacian(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    psi: np.ndarray,
    links: LinkVariables,
) -> np.ndarray:
    """Apply the covariant Laplacian directly to a complex field."""

    result = np.zeros_like(psi, dtype=np.complex128)
    hx2 = grid.hx**2
    hy2 = grid.hy**2
    x_active = mask.x_edge_active[1:-1, :]
    y_active = mask.y_edge_active[:, 1:-1]

    x_forward = x_active * (links.ux[1:-1, :] * psi[1:, :] / hx2)
    x_backward = x_active * (np.conj(links.ux[1:-1, :]) * psi[:-1, :] / hx2)
    result[:-1, :] += x_forward
    result[1:, :] += x_backward
    result[:-1, :] -= x_active * psi[:-1, :] / hx2
    result[1:, :] -= x_active * psi[1:, :] / hx2

    y_forward = y_active * (links.uy[:, 1:-1] * psi[:, 1:] / hy2)
    y_backward = y_active * (np.conj(links.uy[:, 1:-1]) * psi[:, :-1] / hy2)
    result[:, :-1] += y_forward
    result[:, 1:] += y_backward
    result[:, :-1] -= y_active * psi[:, :-1] / hy2
    result[:, 1:] -= y_active * psi[:, 1:] / hy2
    result[~mask.cell_active] = 0.0
    return result


def _assemble_pairwise_matrix(
    size: int,
    diag: np.ndarray,
    left_x: np.ndarray,
    right_x: np.ndarray,
    data_x: np.ndarray,
    left_y: np.ndarray,
    right_y: np.ndarray,
    data_y: np.ndarray,
    dtype,
    conjugate_pairs: bool,
) -> sparse.csr_matrix:
    """Assemble a sparse operator from symmetric nearest-neighbor couplings and a diagonal."""

    row_parts: list[np.ndarray] = []
    col_parts: list[np.ndarray] = []
    data_parts: list[np.ndarray] = []

    if left_x.size:
        row_parts.extend([left_x, right_x])
        col_parts.extend([right_x, left_x])
        data_parts.extend([data_x, np.conj(data_x) if conjugate_pairs else data_x])
    if left_y.size:
        row_parts.extend([left_y, right_y])
        col_parts.extend([right_y, left_y])
        data_parts.extend([data_y, np.conj(data_y) if conjugate_pairs else data_y])

    diag_mask = diag != 0
    if np.any(diag_mask):
        diag_indices = np.flatnonzero(diag_mask)
        row_parts.append(diag_indices)
        col_parts.append(diag_indices)
        data_parts.append(diag[diag_mask])

    if not row_parts:
        return sparse.csr_matrix((size, size), dtype=dtype)

    rows = np.concatenate(row_parts)
    cols = np.concatenate(col_parts)
    data = np.concatenate(data_parts).astype(dtype, copy=False)
    return sparse.coo_matrix((data, (rows, cols)), shape=(size, size), dtype=dtype).tocsr()


def build_covariant_laplacian_matrix(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    links: LinkVariables,
) -> sparse.csr_matrix:
    """Build the sparse covariant Laplacian matrix on the full grid."""

    n = grid.nx * grid.ny
    index_grid = np.arange(n, dtype=np.int64).reshape(mask.cell_active.shape, order="C")
    hx2 = grid.hx**2
    hy2 = grid.hy**2
    x_active = mask.x_edge_active[1:-1, :]
    y_active = mask.y_edge_active[:, 1:-1]

    left_x = index_grid[:-1, :][x_active]
    right_x = index_grid[1:, :][x_active]
    left_y = index_grid[:, :-1][y_active]
    right_y = index_grid[:, 1:][y_active]
    data_x = links.ux[1:-1, :][x_active] / hx2
    data_y = links.uy[:, 1:-1][y_active] / hy2

    diag = np.zeros(n, dtype=np.complex128)
    np.add.at(diag, left_x, -1.0 / hx2)
    np.add.at(diag, right_x, -1.0 / hx2)
    np.add.at(diag, left_y, -1.0 / hy2)
    np.add.at(diag, right_y, -1.0 / hy2)

    return _assemble_pairwise_matrix(
        size=n,
        diag=diag,
        left_x=left_x,
        right_x=right_x,
        data_x=data_x,
        left_y=left_y,
        right_y=right_y,
        data_y=data_y,
        dtype=np.complex128,
        conjugate_pairs=True,
    )


def build_active_covariant_laplacian_matrix(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    links: LinkVariables,
    active_cells: ActiveCellMap,
) -> sparse.csr_matrix:
    """Build the sparse covariant Laplacian directly on active cells.

    This form avoids allocating masked full-grid rows and columns, which keeps the phase-1 IMEX
    solve aligned with the active-domain unknown count.
    """

    hx2 = grid.hx**2
    hy2 = grid.hy**2
    x_active = mask.x_edge_active[1:-1, :]
    y_active = mask.y_edge_active[:, 1:-1]

    left_x = active_cells.lookup[:-1, :][x_active]
    right_x = active_cells.lookup[1:, :][x_active]
    left_y = active_cells.lookup[:, :-1][y_active]
    right_y = active_cells.lookup[:, 1:][y_active]
    data_x = links.ux[1:-1, :][x_active] / hx2
    data_y = links.uy[:, 1:-1][y_active] / hy2

    diag = np.zeros(active_cells.count, dtype=np.complex128)
    np.add.at(diag, left_x, -1.0 / hx2)
    np.add.at(diag, right_x, -1.0 / hx2)
    np.add.at(diag, left_y, -1.0 / hy2)
    np.add.at(diag, right_y, -1.0 / hy2)

    return _assemble_pairwise_matrix(
        size=active_cells.count,
        diag=diag,
        left_x=left_x,
        right_x=right_x,
        data_x=data_x,
        left_y=left_y,
        right_y=right_y,
        data_y=data_y,
        dtype=np.complex128,
        conjugate_pairs=True,
    )


def build_psi_operator(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    links: LinkVariables,
    u: float,
    dt: float,
) -> sparse.csr_matrix:
    """Build the linear IMEX operator for the psi update."""

    laplacian = build_covariant_laplacian_matrix(grid, mask, links)
    identity = sparse.identity(grid.nx * grid.ny, dtype=np.complex128, format="csr")
    return (u / dt) * identity - laplacian


def build_active_psi_operator(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    links: LinkVariables,
    active_cells: ActiveCellMap,
    u: float,
    dt: float,
) -> sparse.csr_matrix:
    """Build the active-cell IMEX operator for the psi update."""

    laplacian = build_active_covariant_laplacian_matrix(grid, mask, links, active_cells)
    identity = sparse.identity(active_cells.count, dtype=np.complex128, format="csr")
    return (u / dt) * identity - laplacian


def build_scalar_laplacian_matrix(grid: StructuredGrid2D, mask: GeometryMask) -> sparse.csr_matrix:
    """Build the real Neumann Laplacian on active cells with masked neighbors excluded."""

    n = grid.nx * grid.ny
    index_grid = np.arange(n, dtype=np.int64).reshape(mask.cell_active.shape, order="C")
    hx2 = grid.hx**2
    hy2 = grid.hy**2
    x_active = mask.x_edge_active[1:-1, :]
    y_active = mask.y_edge_active[:, 1:-1]

    left_x = index_grid[:-1, :][x_active]
    right_x = index_grid[1:, :][x_active]
    left_y = index_grid[:, :-1][y_active]
    right_y = index_grid[:, 1:][y_active]
    data_x = np.full(left_x.size, 1.0 / hx2, dtype=float)
    data_y = np.full(left_y.size, 1.0 / hy2, dtype=float)

    diag = np.zeros(n, dtype=float)
    np.add.at(diag, left_x, -1.0 / hx2)
    np.add.at(diag, right_x, -1.0 / hx2)
    np.add.at(diag, left_y, -1.0 / hy2)
    np.add.at(diag, right_y, -1.0 / hy2)

    return _assemble_pairwise_matrix(
        size=n,
        diag=diag,
        left_x=left_x,
        right_x=right_x,
        data_x=data_x,
        left_y=left_y,
        right_y=right_y,
        data_y=data_y,
        dtype=float,
        conjugate_pairs=False,
    )


def build_active_scalar_laplacian_matrix(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    active_cells: ActiveCellMap,
) -> sparse.csr_matrix:
    """Build the real Neumann Laplacian directly on active cells.

    The operator excludes masked neighbors rather than inserting ghost values, so disconnected
    masks retain the expected per-component null space and must be rejected upstream when a
    unique gauge-fixed solution is required.
    """

    hx2 = grid.hx**2
    hy2 = grid.hy**2
    x_active = mask.x_edge_active[1:-1, :]
    y_active = mask.y_edge_active[:, 1:-1]

    left_x = active_cells.lookup[:-1, :][x_active]
    right_x = active_cells.lookup[1:, :][x_active]
    left_y = active_cells.lookup[:, :-1][y_active]
    right_y = active_cells.lookup[:, 1:][y_active]
    data_x = np.full(left_x.size, 1.0 / hx2, dtype=float)
    data_y = np.full(left_y.size, 1.0 / hy2, dtype=float)

    diag = np.zeros(active_cells.count, dtype=float)
    np.add.at(diag, left_x, -1.0 / hx2)
    np.add.at(diag, right_x, -1.0 / hx2)
    np.add.at(diag, left_y, -1.0 / hy2)
    np.add.at(diag, right_y, -1.0 / hy2)

    return _assemble_pairwise_matrix(
        size=active_cells.count,
        diag=diag,
        left_x=left_x,
        right_x=right_x,
        data_x=data_x,
        left_y=left_y,
        right_y=right_y,
        data_y=data_y,
        dtype=float,
        conjugate_pairs=False,
    )

