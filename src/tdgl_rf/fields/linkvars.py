"""Link-variable construction and discrete gauge transforms."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.geometry.masks import StructuredGrid2D


@dataclass(frozen=True)
class LinkVariables:
    """Gauge link variables stored on grid edges."""

    ux: np.ndarray
    uy: np.ndarray


def build_link_variables(grid: StructuredGrid2D, potential: VectorPotential) -> LinkVariables:
    """Construct link variables from edge-centered vector potential."""

    return LinkVariables(
        ux=np.exp(-1j * grid.hx * potential.ax),
        uy=np.exp(-1j * grid.hy * potential.ay),
    )


def apply_gauge_transform(
    grid: StructuredGrid2D,
    psi: np.ndarray,
    potential: VectorPotential,
    chi: np.ndarray,
) -> tuple[np.ndarray, VectorPotential]:
    """Apply a discrete gauge transformation to psi and A."""

    psi_t = np.exp(1j * chi) * psi
    ax = potential.ax.copy()
    ay = potential.ay.copy()
    ax[1:-1, :] += (chi[1:, :] - chi[:-1, :]) / grid.hx
    ay[:, 1:-1] += (chi[:, 1:] - chi[:, :-1]) / grid.hy
    return psi_t, VectorPotential(ax=ax, ay=ay)

