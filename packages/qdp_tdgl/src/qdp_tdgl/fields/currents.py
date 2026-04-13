"""Discrete supercurrent, normal current, and divergence operators."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qdp_tdgl.fields.forcing import VectorPotential
from qdp_tdgl.fields.linkvars import LinkVariables
from qdp_tdgl.geometry.masks import GeometryMask, StructuredGrid2D


@dataclass(frozen=True)
class CurrentField:
    """Edge-centered current field."""

    jx: np.ndarray
    jy: np.ndarray


def compute_supercurrent(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    psi: np.ndarray,
    links: LinkVariables,
) -> CurrentField:
    """Compute the gauge-invariant supercurrent on internal edges."""

    jx = np.zeros((grid.nx + 1, grid.ny), dtype=float)
    jy = np.zeros((grid.nx, grid.ny + 1), dtype=float)
    active_x = mask.x_edge_active[1:-1, :]
    active_y = mask.y_edge_active[:, 1:-1]
    jx_interior = jx[1:-1, :]
    jy_interior = jy[:, 1:-1]

    link_x = np.conj(psi[:-1, :]) * links.ux[1:-1, :] * psi[1:, :]
    link_y = np.conj(psi[:, :-1]) * links.uy[:, 1:-1] * psi[:, 1:]
    jx_interior[active_x] = np.imag(link_x[active_x]) / grid.hx
    jy_interior[active_y] = np.imag(link_y[active_y]) / grid.hy
    return CurrentField(jx=jx, jy=jy)


def compute_normal_current(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    phi: np.ndarray,
    a_dot: VectorPotential,
    sigma_n: float,
) -> CurrentField:
    """Compute the normal current on internal edges."""

    jx = np.zeros((grid.nx + 1, grid.ny), dtype=float)
    jy = np.zeros((grid.nx, grid.ny + 1), dtype=float)
    active_x = mask.x_edge_active[1:-1, :]
    active_y = mask.y_edge_active[:, 1:-1]
    jx_interior = jx[1:-1, :]
    jy_interior = jy[:, 1:-1]

    dphi_x = (phi[1:, :] - phi[:-1, :]) / grid.hx
    dphi_y = (phi[:, 1:] - phi[:, :-1]) / grid.hy
    jx_interior[active_x] = -sigma_n * (dphi_x[active_x] + a_dot.ax[1:-1, :][active_x])
    jy_interior[active_y] = -sigma_n * (dphi_y[active_y] + a_dot.ay[:, 1:-1][active_y])
    return CurrentField(jx=jx, jy=jy)


def add_currents(lhs: CurrentField, rhs: CurrentField) -> CurrentField:
    """Add two edge-centered current fields."""

    return CurrentField(jx=lhs.jx + rhs.jx, jy=lhs.jy + rhs.jy)


def divergence(grid: StructuredGrid2D, current: CurrentField) -> np.ndarray:
    """Compute the cell-centered divergence of an edge current field."""

    return (current.jx[1:, :] - current.jx[:-1, :]) / grid.hx + (current.jy[:, 1:] - current.jy[:, :-1]) / grid.hy


def edge_to_cell_magnitude_squared(grid: StructuredGrid2D, current: CurrentField) -> np.ndarray:
    """Average edge currents to cell centers and return |J|^2."""

    jx_center = 0.5 * (current.jx[:-1, :] + current.jx[1:, :])
    jy_center = 0.5 * (current.jy[:, :-1] + current.jy[:, 1:])
    return jx_center**2 + jy_center**2

