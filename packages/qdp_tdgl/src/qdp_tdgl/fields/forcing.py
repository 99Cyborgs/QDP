"""Prescribed vector-potential forcing fields."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from qdp_tdgl.config.models import ForcingConfig
from qdp_tdgl.geometry.masks import StructuredGrid2D


@dataclass(frozen=True)
class VectorPotential:
    """Edge-centered vector potential."""

    ax: np.ndarray
    ay: np.ndarray

    @classmethod
    def zeros(cls, grid: StructuredGrid2D) -> "VectorPotential":
        return cls(
            ax=np.zeros((grid.nx + 1, grid.ny), dtype=float),
            ay=np.zeros((grid.nx, grid.ny + 1), dtype=float),
        )


def _load_profile_from_file(grid: StructuredGrid2D, profile_path: Path) -> VectorPotential:
    suffix = profile_path.suffix.lower()
    if suffix != ".npz":
        raise ValueError("phase-1 forcing files must be .npz archives with ax and ay arrays")
    with np.load(profile_path) as handle:
        ax = np.asarray(handle["ax"], dtype=float)
        ay = np.asarray(handle["ay"], dtype=float)
    if ax.shape != (grid.nx + 1, grid.ny) or ay.shape != (grid.nx, grid.ny + 1):
        raise ValueError("forcing profile shape does not match the configured grid")
    return VectorPotential(ax=ax, ay=ay)


def build_dc_potential(grid: StructuredGrid2D, forcing: ForcingConfig) -> VectorPotential:
    """Return a divergence-free static vector potential for the uniform DC field."""

    if forcing.b_dc == 0.0:
        return VectorPotential.zeros(grid)
    x_edge, y_edge = grid.x_edge_mesh
    x_y, y_y = grid.y_edge_mesh
    x0 = 0.5 * grid.lx
    y0 = 0.5 * grid.ly
    ax = -0.5 * forcing.b_dc * (y_edge - y0)
    ay = 0.5 * forcing.b_dc * (x_y - x0)
    return VectorPotential(ax=ax, ay=ay)


def build_rf_profile(grid: StructuredGrid2D, forcing: ForcingConfig, config_dir: Path | None = None) -> VectorPotential:
    """Return the normalized RF spatial profile."""

    if forcing.rf_profile == "uniform_x":
        return VectorPotential(ax=np.ones((grid.nx + 1, grid.ny), dtype=float), ay=np.zeros((grid.nx, grid.ny + 1), dtype=float))
    if forcing.rf_profile == "uniform_y":
        return VectorPotential(ax=np.zeros((grid.nx + 1, grid.ny), dtype=float), ay=np.ones((grid.nx, grid.ny + 1), dtype=float))
    if forcing.rf_profile == "edge_crowding":
        _, y_edge = grid.x_edge_mesh
        distance = np.minimum(y_edge, grid.ly - y_edge)
        scale = 1.0 / np.maximum(distance, 0.5 * min(grid.hx, grid.hy))
        scale /= np.max(scale)
        return VectorPotential(ax=scale, ay=np.zeros((grid.nx, grid.ny + 1), dtype=float))
    if forcing.rf_profile == "from_file":
        if config_dir is None or forcing.rf_profile_file is None:
            raise ValueError("config_dir and forcing.rf_profile_file are required for forcing file loading")
        return _load_profile_from_file(grid, (config_dir / forcing.rf_profile_file).resolve())
    raise ValueError(f"unsupported RF profile: {forcing.rf_profile}")


def evaluate_forcing(
    grid: StructuredGrid2D,
    forcing: ForcingConfig,
    t: float,
    config_dir: Path | None = None,
) -> tuple[VectorPotential, VectorPotential]:
    """Evaluate A(t) and dA/dt at the requested time."""

    dc = build_dc_potential(grid, forcing)
    rf_profile = build_rf_profile(grid, forcing, config_dir=config_dir)
    phase = forcing.omega * t + forcing.phase
    amplitude = forcing.a_rf * np.cos(phase)
    amplitude_dot = -forcing.a_rf * forcing.omega * np.sin(phase)
    a = VectorPotential(ax=dc.ax + amplitude * rf_profile.ax, ay=dc.ay + amplitude * rf_profile.ay)
    a_dot = VectorPotential(ax=amplitude_dot * rf_profile.ax, ay=amplitude_dot * rf_profile.ay)
    return a, a_dot


