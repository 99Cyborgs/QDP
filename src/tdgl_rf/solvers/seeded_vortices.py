"""Deterministic seeded-vortex initialization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from tdgl_rf.config.models import VortexSeedConfig
from tdgl_rf.exceptions import (
    SEED_REJECTION_TAXONOMY_VERSION,
    SeedRejectionCode,
    SeedRejectionError,
)
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D

SEED_RESOLUTION_POLICY = "strict_interior_fully_active_plaquette"


@dataclass(frozen=True)
class ResolvedVortexSeed:
    """Seed placement resolved onto one fully active plaquette."""

    x0: float
    y0: float
    winding: int
    core_radius: float
    plaquette_x: int
    plaquette_y: int

    def to_payload(self, *, seed_index: int | None = None) -> dict[str, float | int | None]:
        """Return a deterministic JSON-friendly resolved-seed payload."""

        return {
            "seed_index": seed_index,
            "x0": self.x0,
            "y0": self.y0,
            "winding": self.winding,
            "core_radius": self.core_radius,
            "plaquette_x": self.plaquette_x,
            "plaquette_y": self.plaquette_y,
        }


def configured_seed_payloads(seeds: Sequence[VortexSeedConfig]) -> list[dict[str, float | int | None]]:
    """Return configured seed payloads in stable input order."""

    return [
        {
            "seed_index": index,
            "x0": float(seed.x0),
            "y0": float(seed.y0),
            "winding": int(seed.winding),
            "core_radius": None if seed.core_radius is None else float(seed.core_radius),
        }
        for index, seed in enumerate(seeds)
    ]


def resolved_seed_payloads(seeds: Sequence[ResolvedVortexSeed]) -> list[dict[str, float | int | None]]:
    """Return resolved seed payloads in stable input order."""

    return [seed.to_payload(seed_index=index) for index, seed in enumerate(seeds)]


def _resolve_seed_axis(
    coordinate: float,
    centers: np.ndarray,
    *,
    axis_label: str,
    seed_label: str,
    seed_index: int,
) -> int:
    """Resolve one configured seed coordinate onto a unique host plaquette index."""

    lower = float(centers[0])
    upper = float(centers[-1])
    index = int(np.searchsorted(centers, coordinate, side="right") - 1)
    if index < 0 or index >= len(centers) - 1:
        raise SeedRejectionError(
            code=SeedRejectionCode.OUTSIDE_DOMAIN,
            seed_index=seed_index,
            field_path=f"{seed_label}.{axis_label}",
            message=(
                f"{seed_label} {axis_label}={coordinate:.6g} must lie strictly inside the modeled domain; "
                f"supported {axis_label} range is ({lower:.6g}, {upper:.6g})"
            ),
            details={"coordinate": float(coordinate), "lower": lower, "upper": upper},
        )
    if not (float(centers[index]) < coordinate < float(centers[index + 1])):
        raise SeedRejectionError(
            code=SeedRejectionCode.AMBIGUOUS_PLAQUETTE,
            seed_index=seed_index,
            field_path=f"{seed_label}.{axis_label}",
            message=(
                f"{seed_label} {axis_label}={coordinate:.6g} must lie strictly between neighboring cell centers "
                f"to define one seeded-vortex plaquette unambiguously"
            ),
            details={
                "coordinate": float(coordinate),
                "lower_center": float(centers[index]),
                "upper_center": float(centers[index + 1]),
            },
        )
    return index


def resolve_vortex_seeds(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    seeds: Sequence[VortexSeedConfig],
) -> list[ResolvedVortexSeed]:
    """Validate and resolve configured vortex seeds against the active geometry.

    Resolution is intentionally stricter than nearest-cell snapping: each seed must identify one
    fully active plaquette so later winding diagnostics have an unambiguous host location.
    """

    default_core_radius = 0.5 * min(grid.hx, grid.hy)
    resolved: list[ResolvedVortexSeed] = []
    seen_hosts: dict[tuple[int, int], str] = {}
    for index, seed in enumerate(seeds):
        seed_label = f"physics.vortex_seeds[{index}]"
        plaquette_x = _resolve_seed_axis(seed.x0, grid.x_centers, axis_label="x0", seed_label=seed_label, seed_index=index)
        plaquette_y = _resolve_seed_axis(seed.y0, grid.y_centers, axis_label="y0", seed_label=seed_label, seed_index=index)
        host = (plaquette_x, plaquette_y)
        previous = seen_hosts.get(host)
        if previous is not None:
            raise SeedRejectionError(
                code=SeedRejectionCode.OVERLAPPING_PLAQUETTE,
                seed_index=index,
                field_path=seed_label,
                message=(
                    f"{seed_label} and {previous} resolve to the same plaquette {host}; overlapping seeded vortices are unsupported"
                ),
                details={"plaquette_x": plaquette_x, "plaquette_y": plaquette_y, "previous_seed": previous},
            )
        active_block = mask.cell_active[plaquette_x : plaquette_x + 2, plaquette_y : plaquette_y + 2]
        if active_block.shape != (2, 2) or not bool(np.all(active_block)):
            raise SeedRejectionError(
                code=SeedRejectionCode.INACTIVE_PLAQUETTE,
                seed_index=index,
                field_path=seed_label,
                message=(
                    f"{seed_label} at ({seed.x0:.6g}, {seed.y0:.6g}) must lie inside a fully active plaquette; "
                    f"host plaquette {host} intersects inactive cells"
                ),
                details={"plaquette_x": plaquette_x, "plaquette_y": plaquette_y},
            )
        seen_hosts[host] = seed_label
        resolved.append(
            ResolvedVortexSeed(
                x0=float(seed.x0),
                y0=float(seed.y0),
                winding=int(seed.winding),
                core_radius=float(seed.core_radius if seed.core_radius is not None else default_core_radius),
                plaquette_x=plaquette_x,
                plaquette_y=plaquette_y,
            )
        )
    return resolved


def build_seeded_vortex_psi(
    grid: StructuredGrid2D,
    mask: GeometryMask,
    resolved_seeds: Sequence[ResolvedVortexSeed],
) -> np.ndarray:
    """Build a deterministic seeded-vortex ansatz on the cell-centered grid.

    The amplitude profile enforces a finite core suppression radius while the phase factor encodes
    winding. Multiple seeds are combined multiplicatively so the initialization remains
    deterministic and order-independent for disjoint hosts.
    """

    x, y = grid.cell_center_mesh
    psi = np.ones((grid.nx, grid.ny), dtype=np.complex128)
    for seed in resolved_seeds:
        dx = x - seed.x0
        dy = y - seed.y0
        radius_squared = dx * dx + dy * dy
        amplitude = np.sqrt(radius_squared / (radius_squared + seed.core_radius * seed.core_radius))
        phase = np.arctan2(dy, dx)
        psi *= amplitude * np.exp(1j * seed.winding * phase)
    psi[~mask.cell_active] = 0.0
    return psi
