"""Simulation state container."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from tdgl_rf.config.models import TDGLRFCaseConfig
from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.io.checkpoints import read_checkpoint


@dataclass
class SimulationState:
    """Time-dependent TDGL state."""

    grid: StructuredGrid2D
    t: float
    step: int
    psi: np.ndarray
    phi: np.ndarray
    A: VectorPotential
    A_dot: VectorPotential
    diagnostics: dict[str, Any] = field(default_factory=dict)
    rng_state: dict[str, Any] | None = None
    checkpoint_id: str | None = None


def initialize_state(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    config: TDGLRFCaseConfig,
    config_dir: Path,
) -> SimulationState:
    """Construct the initial simulation state from config."""

    if config.physics.initial_condition == "meissner":
        psi = np.ones((grid.nx, grid.ny), dtype=np.complex128)
        psi[~mask.cell_active] = 0.0
        phi = np.zeros((grid.nx, grid.ny), dtype=float)
        a = VectorPotential.zeros(grid)
        return SimulationState(grid=grid, t=0.0, step=0, psi=psi, phi=phi, A=a, A_dot=a)

    if config.physics.initial_condition == "restart":
        restart_path = (config_dir / str(config.physics.restart_file)).resolve()
        payload = read_checkpoint(restart_path)
        return SimulationState(
            grid=grid,
            t=float(payload["t"]),
            step=int(payload["step"]),
            psi=np.asarray(payload["psi"], dtype=np.complex128),
            phi=np.asarray(payload["phi"], dtype=float),
            A=VectorPotential(ax=np.asarray(payload["ax"], dtype=float), ay=np.asarray(payload["ay"], dtype=float)),
            A_dot=VectorPotential(ax=np.asarray(payload["ax_dot"], dtype=float), ay=np.asarray(payload["ay_dot"], dtype=float)),
            checkpoint_id=restart_path.stem,
        )

    raise ValueError(f"unsupported phase-1 initial condition: {config.physics.initial_condition}")

