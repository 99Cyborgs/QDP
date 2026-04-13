"""Pinning landscape and alpha-field generation."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from qdp_tdgl.config.models import PhysicsConfig
from qdp_tdgl.geometry.masks import GeometryMask, StructuredGrid2D


def build_alpha_field(grid: StructuredGrid2D, mask: GeometryMask, physics: PhysicsConfig) -> np.ndarray:
    """Construct the alpha(x) field from the configured pinning model."""

    alpha = np.full((grid.nx, grid.ny), physics.alpha_background, dtype=float)
    model = physics.pinning.model
    if model == "none":
        alpha[~mask.cell_active] = 0.0
        return alpha

    x, y = grid.cell_center_mesh
    chi = np.zeros_like(alpha)
    if model == "gaussian_defects":
        for defect in physics.pinning.defects:
            radius_sq = (x - defect.x0) ** 2 + (y - defect.y0) ** 2
            chi += defect.amplitude * np.exp(-0.5 * radius_sq / defect.width**2)
    elif model == "random_field":
        seed = physics.pinning.seed if physics.pinning.seed is not None else 0
        rng = np.random.default_rng(seed)
        raw = rng.standard_normal(size=alpha.shape)
        sigma_x = max(physics.pinning.lcorr / grid.hx, 1e-12)
        sigma_y = max(physics.pinning.lcorr / grid.hy, 1e-12)
        filtered = gaussian_filter(raw, sigma=(sigma_x, sigma_y), mode="nearest")
        filtered -= np.mean(filtered[mask.cell_active])
        std = np.std(filtered[mask.cell_active])
        if std > 0:
            filtered *= physics.pinning.sigma / std
        chi = physics.pinning.mu + filtered
    else:  # pragma: no cover - exhaustive by validator
        raise ValueError(f"unsupported pinning model: {model}")

    alpha -= chi
    alpha[~mask.cell_active] = 0.0
    return alpha

