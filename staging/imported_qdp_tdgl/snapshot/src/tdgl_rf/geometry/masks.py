"""Structured grid and geometry masks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from tdgl_rf.config.models import GeometryConfig, MeshConfig
from tdgl_rf.exceptions import GeometryError
from tdgl_rf.geometry.moat import apply_circular_exclusions
from tdgl_rf.geometry.strip import build_strip_mask


@dataclass(frozen=True)
class StructuredGrid2D:
    """Structured Cartesian grid with cell-centered and edge-centered coordinates."""

    nx: int
    ny: int
    lx: float
    ly: float
    periodic_x: bool = False
    periodic_y: bool = False

    @property
    def hx(self) -> float:
        return self.lx / self.nx

    @property
    def hy(self) -> float:
        return self.ly / self.ny

    @property
    def cell_area(self) -> float:
        return self.hx * self.hy

    @property
    def x_centers(self) -> np.ndarray:
        return (np.arange(self.nx, dtype=float) + 0.5) * self.hx

    @property
    def y_centers(self) -> np.ndarray:
        return (np.arange(self.ny, dtype=float) + 0.5) * self.hy

    @property
    def x_edges(self) -> np.ndarray:
        return np.arange(self.nx + 1, dtype=float) * self.hx

    @property
    def y_edges(self) -> np.ndarray:
        return np.arange(self.ny + 1, dtype=float) * self.hy

    @property
    def cell_center_mesh(self) -> tuple[np.ndarray, np.ndarray]:
        return np.meshgrid(self.x_centers, self.y_centers, indexing="ij")

    @property
    def x_edge_mesh(self) -> tuple[np.ndarray, np.ndarray]:
        return np.meshgrid(self.x_edges, self.y_centers, indexing="ij")

    @property
    def y_edge_mesh(self) -> tuple[np.ndarray, np.ndarray]:
        return np.meshgrid(self.x_centers, self.y_edges, indexing="ij")


@dataclass(frozen=True)
class GeometryMask:
    """Cell and edge activity masks for structured TDGL domains."""

    cell_active: np.ndarray
    _x_edge_active: np.ndarray = field(init=False, repr=False)
    _y_edge_active: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        cell_active = np.ascontiguousarray(np.asarray(self.cell_active, dtype=bool))
        object.__setattr__(self, "cell_active", cell_active)

        x_mask = np.zeros((cell_active.shape[0] + 1, cell_active.shape[1]), dtype=bool)
        y_mask = np.zeros((cell_active.shape[0], cell_active.shape[1] + 1), dtype=bool)
        x_mask[1:-1, :] = cell_active[:-1, :] & cell_active[1:, :]
        y_mask[:, 1:-1] = cell_active[:, :-1] & cell_active[:, 1:]
        object.__setattr__(self, "_x_edge_active", np.ascontiguousarray(x_mask))
        object.__setattr__(self, "_y_edge_active", np.ascontiguousarray(y_mask))

    @property
    def shape(self) -> tuple[int, int]:
        return self.cell_active.shape

    @property
    def active_count(self) -> int:
        return int(np.count_nonzero(self.cell_active))

    @property
    def x_edge_active(self) -> np.ndarray:
        return self._x_edge_active

    @property
    def y_edge_active(self) -> np.ndarray:
        return self._y_edge_active


def _load_custom_mask(grid: StructuredGrid2D, mask_path: Path) -> np.ndarray:
    """Load a persisted cell-activity mask and enforce grid-shape compatibility."""

    suffix = mask_path.suffix.lower()
    if suffix == ".npy":
        mask = np.load(mask_path)
    elif suffix == ".npz":
        with np.load(mask_path) as handle:
            if "mask" not in handle:
                raise GeometryError(f"custom mask archive {mask_path} must contain a 'mask' array")
            mask = handle["mask"]
    else:
        raise GeometryError(f"unsupported custom mask format: {mask_path.suffix}")
    mask = np.asarray(mask, dtype=bool)
    if mask.shape != (grid.nx, grid.ny):
        raise GeometryError(f"custom mask shape {mask.shape} does not match grid {(grid.nx, grid.ny)}")
    return mask


def grid_from_config(mesh: MeshConfig) -> StructuredGrid2D:
    """Construct a structured grid from the mesh config."""

    return StructuredGrid2D(
        nx=mesh.nx,
        ny=mesh.ny,
        lx=mesh.lx,
        ly=mesh.ly,
        periodic_x=mesh.periodic_x,
        periodic_y=mesh.periodic_y,
    )


def build_geometry(grid: StructuredGrid2D, geometry: GeometryConfig, config_dir: Path) -> GeometryMask:
    """Build the phase-1 active-domain mask from the validated geometry contract."""

    if geometry.family == "strip":
        cell_active = build_strip_mask(grid)
    elif geometry.family in {"strip_with_moat", "strip_with_hole"}:
        cell_active = build_strip_mask(grid)
    elif geometry.family == "custom_mask":
        if geometry.mask_file is None:
            raise GeometryError("custom_mask geometry requires geometry.mask_file")
        cell_active = _load_custom_mask(grid, (config_dir / geometry.mask_file).resolve())
    else:  # pragma: no cover - exhaustive by validator
        raise GeometryError(f"unsupported geometry family: {geometry.family}")

    # Moats and holes both remove active cells; they remain separate in config because they
    # carry different experimental intent even though the runtime mask effect is identical.
    cell_active = apply_circular_exclusions(cell_active, grid, geometry.moats)
    cell_active = apply_circular_exclusions(cell_active, grid, geometry.holes)
    if not np.any(cell_active):
        raise GeometryError("geometry mask deactivates every cell")
    return GeometryMask(cell_active=cell_active)
