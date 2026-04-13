"""Gauge-invariant vortex diagnostics."""

from __future__ import annotations

from typing import Any

import numpy as np

from qdp_tdgl.fields.linkvars import LinkVariables
from qdp_tdgl.geometry.masks import GeometryMask


def _wrap_phase(theta: np.ndarray) -> np.ndarray:
    return (theta + np.pi) % (2.0 * np.pi) - np.pi


def compute_vortex_map(psi: np.ndarray, links: LinkVariables, mask: GeometryMask) -> np.ndarray:
    """Compute signed plaquette winding numbers."""

    nx, ny = psi.shape
    if nx < 2 or ny < 2:
        return np.zeros((max(nx - 1, 0), max(ny - 1, 0)), dtype=int)

    phase_x = np.angle(np.conj(psi[:-1, :]) * links.ux[1:-1, :] * psi[1:, :])
    phase_y = np.angle(np.conj(psi[:, :-1]) * links.uy[:, 1:-1] * psi[:, 1:])

    bottom = _wrap_phase(phase_x[:, :-1])
    right = _wrap_phase(phase_y[1:, :])
    top = _wrap_phase(-phase_x[:, 1:])
    left = _wrap_phase(-phase_y[:-1, :])
    plaquette_phase = bottom + right + top + left

    active = (
        mask.cell_active[:-1, :-1]
        & mask.cell_active[1:, :-1]
        & mask.cell_active[:-1, 1:]
        & mask.cell_active[1:, 1:]
    )
    vortex_map = np.zeros_like(plaquette_phase, dtype=int)
    vortex_map[active] = np.rint(plaquette_phase[active] / (2.0 * np.pi)).astype(int)
    return vortex_map


def track_vortices(prev_map: np.ndarray, curr_map: np.ndarray, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Track exact-cell births and deaths between two plaquette maps."""

    metadata = metadata or {}
    events: list[dict[str, Any]] = []
    prev_nonzero = set(map(tuple, np.argwhere(prev_map != 0)))
    curr_nonzero = set(map(tuple, np.argwhere(curr_map != 0)))
    for coord in sorted(curr_nonzero - prev_nonzero):
        events.append({"event": "birth", "x_idx": int(coord[0]), "y_idx": int(coord[1]), **metadata})
    for coord in sorted(prev_nonzero - curr_nonzero):
        events.append({"event": "death", "x_idx": int(coord[0]), "y_idx": int(coord[1]), **metadata})
    return events

