"""Run-directory and provenance management."""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from tdgl_rf.config.models import TDGLRFCaseConfig


def create_run_directory(root_dir: str | Path, case_id: str, timestamp: datetime | None = None) -> Path:
    """Create the standard run directory."""

    stamp = (timestamp or datetime.now()).strftime("%Y%m%d-%H%M%S")
    path = Path(root_dir) / case_id / stamp
    for relative in ["logs", "observables", "fields", "diagnostics"]:
        (path / relative).mkdir(parents=True, exist_ok=True)
    return path


def config_hash(config: TDGLRFCaseConfig) -> str:
    """Compute a stable hash for the expanded config."""

    payload = repr(config.model_dump(mode="json", round_trip=True)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _git_revision(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def build_provenance(config: TDGLRFCaseConfig, repo_root: Path) -> dict[str, Any]:
    """Collect provenance metadata required by the artifact pack."""

    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "git_revision": _git_revision(repo_root),
        "rank_count": 1,
        "config_hash": config_hash(config),
        "seeds": {
            "master_seed": config.noise.master_seed,
            "pinning_seed": config.physics.pinning.seed,
        },
        "packages": {
            "numpy": _package_version("numpy"),
            "scipy": _package_version("scipy"),
            "pydantic": _package_version("pydantic"),
            "pyyaml": _package_version("PyYAML"),
            "jsonschema": _package_version("jsonschema"),
            "h5py": _package_version("h5py"),
            "typer": _package_version("typer"),
        },
        "case_id": config.metadata.case_id,
        "matrix_row_id": config.campaign.matrix_row_id,
    }

