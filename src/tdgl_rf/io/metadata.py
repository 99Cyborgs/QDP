"""Run-directory and provenance management."""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from copy import deepcopy
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np

from tdgl_rf.config.models import TDGLRFCaseConfig

RUN_PROVENANCE_SCHEMA_VERSION = "tdgl_rf.run_provenance.v3"
RUN_PROVENANCE_EXPERIMENT_SCHEMA_VERSION = "tdgl_rf.run_provenance.v3.2"
RUN_PROVENANCE_REPLAY_SCHEMA_VERSION = "tdgl_rf.run_provenance.v3.3"
NOISE_CONTRACT_KIND = "additive_complex_gaussian"
NOISE_CONTRACT_SAMPLING = "run_local_complex_standard_normal"


def create_run_directory(
    root_dir: str | Path,
    case_id: str,
    timestamp: datetime | None = None,
    *,
    explicit_path: str | Path | None = None,
) -> Path:
    """Create the standard run directory."""

    if explicit_path is not None:
        path = Path(explicit_path).resolve()
    else:
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


def build_provenance(
    config: TDGLRFCaseConfig,
    repo_root: Path,
    *,
    source_config_path: str | Path | None = None,
    expanded_config_path: str | Path | None = None,
    initialization_metadata: dict[str, Any] | None = None,
    experiment_metadata: dict[str, Any] | None = None,
    ensemble_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect provenance metadata required by the artifact pack."""

    git_revision = _git_revision(repo_root)
    ensemble_noise_seed = (
        int(ensemble_metadata["noise_seed"])
        if isinstance(ensemble_metadata, dict) and "noise_seed" in ensemble_metadata
        else int(config.noise.seed)
    )
    ensemble_master_seed = (
        int(ensemble_metadata["master_seed"])
        if isinstance(ensemble_metadata, dict) and "master_seed" in ensemble_metadata
        else int(config.noise.seed)
    )
    seeds_payload = {
        "master_seed": ensemble_master_seed,
        "noise_seed": ensemble_noise_seed,
        "pinning_seed": config.physics.pinning.seed,
        "initial_condition": config.physics.initial_condition,
        "vortex_seed_count": len(config.physics.vortex_seeds),
    }
    initialization_payload = dict(initialization_metadata or {"mode": config.physics.initial_condition})
    payload = {
        "schema_version": RUN_PROVENANCE_SCHEMA_VERSION,
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "git_revision": git_revision,
        "rank_count": 1,
        "config_hash": config_hash(config),
        "seeds": seeds_payload,
        "noise": {
            "enabled": bool(config.noise.enabled),
            "strength": float(config.noise.strength),
            "seed": ensemble_noise_seed,
            "contract_kind": NOISE_CONTRACT_KIND,
            "sampling": NOISE_CONTRACT_SAMPLING,
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
        "numeric_environment": {
            "real_dtype": np.dtype(np.float64).name,
            "complex_dtype": np.dtype(np.complex128).name,
            "float_epsilon": float(np.finfo(np.float64).eps),
            "byteorder": sys.byteorder,
        },
        "case_id": config.metadata.case_id,
        "matrix_row_id": config.campaign.matrix_row_id,
        "execution": {
            "repo_root": str(repo_root),
            "git_revision": git_revision,
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": platform.node(),
            "rank_count": 1,
        },
        "config": {
            "case_id": config.metadata.case_id,
            "phase": config.metadata.phase,
            "version": config.metadata.version,
            "base_config": config.base_config,
            "config_hash": config_hash(config),
            "source_config_path": None if source_config_path is None else str(Path(source_config_path).resolve()),
            "expanded_config_path": None if expanded_config_path is None else str(Path(expanded_config_path).resolve()),
            "output_root_dir": str(Path(config.output.root_dir).resolve()),
        },
        "determinism": {
            "noise_enabled": bool(config.noise.enabled),
            "deterministic_expected": not bool(config.noise.enabled),
            "master_seed": ensemble_master_seed,
            "noise_seed": ensemble_noise_seed,
            "pinning_seed": config.physics.pinning.seed,
            "reproducibility_scope": (
                "same-stack seeded stochastic" if config.noise.enabled else "same-stack deterministic"
            ),
        },
        "initialization": initialization_payload,
    }
    if experiment_metadata is not None or ensemble_metadata is not None:
        payload["schema_version"] = RUN_PROVENANCE_EXPERIMENT_SCHEMA_VERSION
    if isinstance(payload.get("experiment"), dict) or experiment_metadata is not None:
        payload["schema_version"] = RUN_PROVENANCE_REPLAY_SCHEMA_VERSION
    if experiment_metadata is not None:
        payload["experiment"] = deepcopy(experiment_metadata)
    if ensemble_metadata is not None:
        payload["ensemble"] = deepcopy(ensemble_metadata)
    return payload

