from __future__ import annotations

import os
from pathlib import Path


def default_seed_root() -> Path:
    """Resolve the seed data directory in a repo-friendly way."""
    candidates = []

    env_root = os.getenv("MMM_STUDIO_SEED_ROOT")
    if env_root:
        candidates.append(Path(env_root))

    cwd = Path.cwd()
    candidates.append(cwd / "data" / "mmm_seed")
    candidates.append(Path(__file__).resolve().parents[2] / "data" / "mmm_seed")
    candidates.append(Path(__file__).resolve().parents[3] / "data" / "mmm_seed")

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not locate MMM seed data. Set MMM_STUDIO_SEED_ROOT or run from the repository root."
    )
