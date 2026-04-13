"""Simulation state container."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from qdp_tdgl.config.models import TDGLRFCaseConfig
from qdp_tdgl.fields.forcing import VectorPotential, evaluate_forcing
from qdp_tdgl.geometry.masks import GeometryMask, StructuredGrid2D
from qdp_tdgl.io.checkpoints import read_checkpoint
from qdp_tdgl.solvers.seeded_vortices import (
    SEED_REJECTION_TAXONOMY_VERSION,
    SEED_RESOLUTION_POLICY,
    build_seeded_vortex_psi,
    configured_seed_payloads,
    resolve_vortex_seeds,
    resolved_seed_payloads,
)


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
    rng_state: np.random.Generator | None = None
    checkpoint_id: str | None = None


def _build_local_rng(config: TDGLRFCaseConfig) -> np.random.Generator | None:
    if not config.noise.enabled:
        return None
    return np.random.default_rng(int(config.noise.seed))


def initialize_state(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    config: TDGLRFCaseConfig,
    config_dir: Path,
) -> SimulationState:
    """Construct the initial simulation state from config."""

    local_rng = _build_local_rng(config)

    if config.physics.initial_condition == "meissner":
        psi = np.ones((grid.nx, grid.ny), dtype=np.complex128)
        psi[~mask.cell_active] = 0.0
        phi = np.zeros((grid.nx, grid.ny), dtype=float)
        a, a_dot = evaluate_forcing(grid, config.forcing, 0.0, config_dir=config_dir)
        return SimulationState(
            grid=grid,
            t=0.0,
            step=0,
            psi=psi,
            phi=phi,
            A=a,
            A_dot=a_dot,
            diagnostics={"initialization": {"mode": "meissner"}},
            rng_state=local_rng,
        )

    if config.physics.initial_condition == "seeded_vortices":
        resolved_seeds = resolve_vortex_seeds(grid, mask, config.physics.vortex_seeds)
        psi = build_seeded_vortex_psi(grid, mask, resolved_seeds)
        phi = np.zeros((grid.nx, grid.ny), dtype=float)
        a, a_dot = evaluate_forcing(grid, config.forcing, 0.0, config_dir=config_dir)
        return SimulationState(
            grid=grid,
            t=0.0,
            step=0,
            psi=psi,
            phi=phi,
            A=a,
            A_dot=a_dot,
            diagnostics={
                "initialization": {
                    "mode": "seeded_vortices",
                    "configured_vortex_seeds": configured_seed_payloads(config.physics.vortex_seeds),
                    "resolved_vortex_seeds": resolved_seed_payloads(resolved_seeds),
                    "seed_resolution_policy": SEED_RESOLUTION_POLICY,
                    "seed_rejection_taxonomy_version": SEED_REJECTION_TAXONOMY_VERSION,
                }
            },
            rng_state=local_rng,
        )

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
            diagnostics={"initialization": {"mode": "restart"}},
            rng_state=local_rng,
            checkpoint_id=restart_path.stem,
        )

    raise ValueError(f"unsupported initial condition: {config.physics.initial_condition}")

