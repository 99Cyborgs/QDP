"""Observable extraction decoupled from the solver loop."""

from __future__ import annotations

from typing import Any

import numpy as np

from tdgl_rf.fields.currents import CurrentField, add_currents, divergence, edge_to_cell_magnitude_squared
from tdgl_rf.fields.linkvars import LinkVariables
from tdgl_rf.fields.vortices import compute_vortex_map
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.solvers.state import SimulationState


def build_weight_profile(grid: StructuredGrid2D, profile: str, mask: GeometryMask | None = None) -> np.ndarray:
    """Build normalized cell-centered weights for reduced observables."""

    x, y = grid.cell_center_mesh
    if profile == "uniform":
        weights = np.ones((grid.nx, grid.ny), dtype=float)
    elif profile == "edge_crowding":
        distance = np.minimum(y, grid.ly - y)
        weights = 1.0 / np.maximum(distance, 0.5 * min(grid.hx, grid.hy))
    else:
        raise ValueError(f"unsupported phase-1 weight profile: {profile}")
    active = mask.cell_active if mask is not None else np.ones((grid.nx, grid.ny), dtype=bool)
    weights = np.where(active, weights, 0.0)
    normalization = float(np.sum(weights) * grid.cell_area)
    if normalization <= 0.0 or not np.isfinite(normalization):
        return np.zeros_like(weights)
    weights /= normalization
    return weights


def compute_frequency_shift_proxy(state: SimulationState, weights: np.ndarray, params: dict[str, float]) -> float:
    """Compute the reduced frequency-shift proxy."""

    deficit = 1.0 - np.abs(state.psi) ** 2
    return float(-params["c_f"] * np.sum(weights * deficit) * state.grid.cell_area)


def compute_qinv_proxy(state: SimulationState, weights: np.ndarray, params: dict[str, float], normal_current: CurrentField) -> float:
    """Compute the reduced dissipation proxy."""

    return float(params["qinv_bg"] + params["c_q"] * np.sum(weights * edge_to_cell_magnitude_squared(state.grid, normal_current)) * state.grid.cell_area)


def compute_summary_stats(timeseries: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate a minimal run summary from stored observables and events."""

    if not timeseries:
        return {"n_samples": 0, "n_events": len(events)}
    final = timeseries[-1]
    return {
        "n_samples": len(timeseries),
        "n_events": len(events),
        "final_time": final["t"],
        "final_mean_abs2": final["mean_abs2"],
        "final_charge_residual_inf": final["charge_residual_inf"],
        "max_vortex_count": max(row["vortex_count"] for row in timeseries),
    }


def compute_basic_observables(
    state: SimulationState,
    mask: GeometryMask,
    links: LinkVariables,
    supercurrent: CurrentField,
    normal_current: CurrentField,
    weights_f: np.ndarray | None,
    weights_q: np.ndarray | None,
    track_vortices: bool,
    compute_freq: bool,
    compute_qinv: bool,
    c_f: float,
    c_q: float,
    qinv_bg: float,
) -> dict[str, Any]:
    """Compute the phase-1 observable bundle."""

    total_current = add_currents(supercurrent, normal_current)
    charge_residual = divergence(state.grid, total_current)
    active = mask.cell_active
    data: dict[str, Any] = {
        "step": state.step,
        "t": state.t,
        "mean_abs2": float(np.mean(np.abs(state.psi[active]) ** 2)),
        "min_abs2": float(np.min(np.abs(state.psi[active]) ** 2)),
        "max_abs2": float(np.max(np.abs(state.psi[active]) ** 2)),
        "supercurrent_l2": float(np.linalg.norm(np.concatenate([supercurrent.jx.ravel(), supercurrent.jy.ravel()]))),
        "normalcurrent_l2": float(np.linalg.norm(np.concatenate([normal_current.jx.ravel(), normal_current.jy.ravel()]))),
        "charge_residual_inf": float(np.max(np.abs(charge_residual[active]))),
        "vortex_count": 0,
    }
    if track_vortices:
        vortex_map = compute_vortex_map(state.psi, links, mask)
        data["vortex_count"] = int(np.sum(np.abs(vortex_map)))
    if compute_freq and weights_f is not None:
        data["delta_f_over_f0"] = compute_frequency_shift_proxy(state, weights_f, {"c_f": c_f})
    if compute_qinv and weights_q is not None:
        data["qinv"] = compute_qinv_proxy(state, weights_q, {"c_q": c_q, "qinv_bg": qinv_bg}, normal_current)
    return data
