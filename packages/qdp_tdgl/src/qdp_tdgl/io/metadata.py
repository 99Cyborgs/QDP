"""Run-directory and provenance management."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

import numpy as np
from qdp_io.runtime_metadata import build_runtime_snapshot

from qdp_meta_materials.adapters.tdgl import resolve_tdgl_material_reference
from qdp_meta_materials.errors import DatasetLoadError

from qdp_tdgl.config.models import TDGLRFCaseConfig

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


def _material_registry_runtime_root(config: TDGLRFCaseConfig, source_config_path: str | Path | None) -> Path | None:
    if config.materials is None or not config.materials.registry_root:
        return None
    candidate = Path(config.materials.registry_root)
    if candidate.is_absolute():
        return candidate.resolve()
    if source_config_path is None:
        return candidate.resolve()
    return (Path(source_config_path).resolve().parent / candidate).resolve()


def _materials_provenance_payload(
    config: TDGLRFCaseConfig,
    *,
    source_config_path: str | Path | None,
) -> dict[str, Any] | None:
    if config.materials is None:
        return None

    runtime_registry_root = _material_registry_runtime_root(config, source_config_path)
    material_payload: dict[str, Any] = {
        "registry_source": config.materials.registry_source,
        "registry_root": str(runtime_registry_root) if runtime_registry_root is not None else None,
        "adapter_id": config.materials.adapter_id,
        "adapter_version": config.materials.adapter_version,
        "material_system_id": config.materials.material_system_id,
        "material_system_name": config.materials.material_system_name,
        "genome_id": config.materials.genome_id,
        "runtime_family": config.materials.runtime_family,
        "source_artifacts": list(config.materials.source_artifacts),
        "supported_geometry_families": list(config.materials.supported_geometry_families),
        "resolved_tdgl_parameters": (
            None
            if config.materials.resolved_tdgl_parameters is None
            else config.materials.resolved_tdgl_parameters.model_dump(mode="json")
        ),
        "notes": config.materials.notes,
    }
    try:
        resolved = resolve_tdgl_material_reference(
            config.materials.adapter_id,
            registry_root=runtime_registry_root,
            material_system_id=config.materials.material_system_id,
            genome_id=config.materials.genome_id,
            geometry_family=config.geometry.family,
        )
    except (DatasetLoadError, FileNotFoundError):
        return material_payload

    material_payload["registry_root"] = str(resolved.registry_root)
    material_payload["adapter_version"] = resolved.adapter_version
    material_payload["material_system_id"] = resolved.material_system_id
    material_payload["material_system_name"] = resolved.material_system_name
    material_payload["runtime_family"] = resolved.runtime_family
    material_payload["source_artifacts"] = list(resolved.source_artifacts)
    material_payload["supported_geometry_families"] = list(resolved.supported_geometry_families)
    material_payload["resolved_tdgl_parameters"] = resolved.tdgl_parameters.model_dump(mode="json")
    material_payload["notes"] = resolved.notes
    return material_payload


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

    runtime_snapshot = build_runtime_snapshot(
        repo_root,
        package_names=["numpy", "scipy", "pydantic", "PyYAML", "jsonschema", "h5py", "typer"],
    )
    git_revision = runtime_snapshot["git_revision"]
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
        "hostname": runtime_snapshot["hostname"],
        "platform": runtime_snapshot["platform"],
        "python_version": runtime_snapshot["python_version"],
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
        "packages": runtime_snapshot["packages"],
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
            "python_version": runtime_snapshot["python_version"],
            "platform": runtime_snapshot["platform"],
            "hostname": runtime_snapshot["hostname"],
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
    materials_payload = _materials_provenance_payload(
        config,
        source_config_path=source_config_path,
    )
    if materials_payload is not None:
        payload["materials"] = materials_payload
    if experiment_metadata is not None:
        payload["experiment"] = deepcopy(experiment_metadata)
    if ensemble_metadata is not None:
        payload["ensemble"] = deepcopy(ensemble_metadata)
    return payload


