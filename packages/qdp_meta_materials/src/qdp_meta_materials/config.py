from __future__ import annotations

import os
from pathlib import Path


def default_seed_root() -> Path:
    """Resolve the extracted seed data directory in a repo-friendly way."""
    candidates = []

    for env_name in ["QDP_META_MATERIALS_SEED_ROOT", "MMM_STUDIO_SEED_ROOT"]:
        env_root = os.getenv(env_name)
        if env_root:
            candidates.append(Path(env_root))

    cwd = Path.cwd()
    package_root = Path(__file__).resolve().parents[2]
    repo_root = Path(__file__).resolve().parents[4]
    candidates.append(cwd / "packages" / "qdp_meta_materials" / "data" / "seed" / "stable")
    candidates.append(cwd / "data" / "seed" / "stable")
    candidates.append(package_root / "data" / "seed" / "stable")
    candidates.append(repo_root / "packages" / "qdp_meta_materials" / "data" / "seed" / "stable")
    candidates.append(cwd / "data" / "mmm_seed")
    candidates.append(package_root / "data" / "mmm_seed")

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not locate qdp_meta_materials seed data. Set QDP_META_MATERIALS_SEED_ROOT or run from the QDP repository root."
    )
