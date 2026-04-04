"""Phase-2.3 deterministic seeded-vortex experiment harness."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from itertools import product
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Sequence

from jsonschema import Draft202012Validator
import yaml

from tdgl_rf.analysis.experiment_aggregation import (
    ALLOWED_EXPERIMENT_AGGREGATION_METRICS,
    aggregate_ensemble_results,
    aggregate_experiment_results,
    classify_experiment_observable,
    write_experiment_result_artifacts,
)
from tdgl_rf.config.loaders import load_raw_config, repo_root, write_expanded_config
from tdgl_rf.config.validators import validate_case_config
from tdgl_rf.diagnostics.seeded_vortex import SUPPORTED_TIER2_OBSERVABLES, extract_observables
from tdgl_rf.exceptions import (
    ManifestValidationError,
    OutputDirectoryError,
    TDGLRFError,
    Tier2ContractError,
)
from tdgl_rf.io.metadata import config_hash
from tdgl_rf.runtime_capabilities import require_phase2_4a_stochastic_runtime
from tdgl_rf.utils.seeds import derive_seed
from tdgl_rf.workflows.run_case import run_simulation
from tdgl_rf.workflows.run_ensemble import execute_ensemble_plan

SEEDED_VORTEX_EXPERIMENT_PACK_SCHEMA_VERSION_PREFIX = "3."
SEEDED_VORTEX_ENSEMBLE_PACK_SCHEMA_VERSION_PREFIX = "4."


@dataclass(frozen=True)
class ExperimentSweepParameter:
    name: str
    values: list[Any]


@dataclass(frozen=True)
class ExperimentEnsembleSettings:
    member_count: int
    master_seed: int


@dataclass(frozen=True)
class SeededVortexExperimentPack:
    schema_version: str
    pack_name: str
    manifest_path: str
    mode: str
    base_case_ref: str
    base_case_path: str
    sweep_parameters: list[ExperimentSweepParameter]
    observables: list[str]
    aggregation_metrics: list[str]
    parent_manifest_hash: str
    repetitions: int | None = None
    ensemble: ExperimentEnsembleSettings | None = None


@dataclass(frozen=True)
class ExperimentSweepSummary:
    status: str
    manifest_path: str
    output_dir: str
    results_json_path: str
    results_csv_path: str
    results_markdown_path: str
    parameter_point_count: int
    run_count: int


@dataclass(frozen=True)
class EnsembleMemberPlan:
    """One planned Phase-2.4A ensemble member execution."""

    run_id: str
    run_dir: str
    ensemble_id: str
    param_set_hash: str
    member_index: int
    noise_seed: int
    parent_manifest_hash: str
    swept_parameters: dict[str, Any]
    experiment_metadata: dict[str, Any]
    ensemble_metadata: dict[str, Any]


@dataclass(frozen=True)
class EnsembleExecutionPlan:
    """Accepted manifest plus planned provenance/control-plane surface for a gated ensemble."""

    manifest_path: str
    pack_name: str
    base_case_path: str
    output_dir: str
    parameter_point_count: int
    planned_run_count: int
    members: list[EnsembleMemberPlan]


def _read_json(path: Path, *, error_cls: type[Exception] = TDGLRFError) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise error_cls(f"missing JSON payload: {path}") from exc
    except json.JSONDecodeError as exc:
        raise error_cls(f"invalid JSON payload at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise error_cls(f"expected mapping payload at {path}")
    return payload


def _read_yaml(path: Path, *, error_cls: type[Exception] = ManifestValidationError) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except FileNotFoundError as exc:
        raise error_cls(f"manifest does not exist: {path}") from exc
    except yaml.YAMLError as exc:
        raise error_cls(f"invalid YAML payload at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise error_cls(f"expected mapping at top level of {path}")
    return payload


def _schema_error_location(parts: list[Any]) -> str:
    return ".".join(str(part) for part in parts) or "<root>"


def _validate_payload_against_schema(
    payload: dict[str, Any],
    schema_path: Path,
    *,
    label: str,
    error_cls: type[Exception] = ManifestValidationError,
) -> None:
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    if errors:
        first = errors[0]
        raise error_cls(
            f"{label} schema validation failed at {_schema_error_location(list(first.absolute_path))}: {first.message}"
        )


def _resolve_path(reference_path: str, *, source_dir: Path) -> Path:
    candidate = Path(reference_path)
    if candidate.is_absolute():
        return candidate.resolve()
    source_relative = (source_dir / candidate).resolve()
    repo_relative = (repo_root() / candidate).resolve()
    return source_relative if source_relative.exists() else repo_relative


def _experiment_pack_schema_path() -> Path:
    return repo_root() / "configs" / "seeded_vortex_experiment_pack.schema.json"


def _experiment_pack_v4_schema_path() -> Path:
    return repo_root() / "configs" / "seeded_vortex_experiment_pack_v4.schema.json"


def _provenance_schema_path() -> Path:
    return repo_root() / "configs" / "tdgl_run_provenance.schema.json"


def _tier2_schema_path() -> Path:
    return repo_root() / "configs" / "seeded_vortex_tier2.schema.json"


def is_seeded_vortex_experiment_pack_manifest(manifest_path: str | Path) -> bool:
    """Return True when the manifest validates as an explicit Phase-2.3 or Phase-2.4A experiment pack."""

    try:
        load_seeded_vortex_experiment_pack(manifest_path)
    except ManifestValidationError:
        return False
    return True


def _parameter_tokens(parameter_name: str) -> list[str | int]:
    parts = [part.strip() for part in str(parameter_name).split(".")]
    if not parts or any(part == "" for part in parts):
        raise ManifestValidationError(
            f"experiment parameter name must be a non-empty dot path; observed {parameter_name!r}"
        )
    tokens: list[str | int] = []
    for part in parts:
        tokens.append(int(part) if part.isdigit() else part)
    return tokens


def _validate_parameter_path_exists(payload: Any, parameter_name: str) -> None:
    current = payload
    for token in _parameter_tokens(parameter_name):
        if isinstance(token, int):
            if not isinstance(current, list) or token < 0 or token >= len(current):
                raise ManifestValidationError(f"experiment parameter path '{parameter_name}' does not exist in base_case")
            current = current[token]
            continue
        if not isinstance(current, dict) or token not in current:
            raise ManifestValidationError(f"experiment parameter path '{parameter_name}' does not exist in base_case")
        current = current[token]


def _set_parameter_value(payload: Any, parameter_name: str, value: Any) -> None:
    tokens = _parameter_tokens(parameter_name)
    current = payload
    for token in tokens[:-1]:
        current = current[token]
    leaf = tokens[-1]
    current[leaf] = deepcopy(value)


def _absolutize_optional_path(payload: dict[str, Any], section: str, key: str, source_dir: Path) -> None:
    section_payload = payload.get(section)
    if not isinstance(section_payload, dict):
        return
    value = section_payload.get(key)
    if not value:
        return
    resolved = Path(value)
    if not resolved.is_absolute():
        section_payload[key] = str((source_dir / resolved).resolve())


def _normalised_base_payload(base_case_path: Path) -> dict[str, Any]:
    payload = deepcopy(load_raw_config(base_case_path))
    payload["base_config"] = None
    noise_payload = payload.get("noise")
    if isinstance(noise_payload, dict):
        if "strength" not in noise_payload and "gamma_psi" in noise_payload:
            noise_payload["strength"] = noise_payload["gamma_psi"]
        if "seed" not in noise_payload and "master_seed" in noise_payload:
            noise_payload["seed"] = noise_payload["master_seed"]
        noise_payload.pop("gamma_psi", None)
        noise_payload.pop("master_seed", None)
    _absolutize_optional_path(payload, "physics", "restart_file", base_case_path.parent)
    _absolutize_optional_path(payload, "geometry", "mask_file", base_case_path.parent)
    _absolutize_optional_path(payload, "forcing", "rf_profile_file", base_case_path.parent)
    _absolutize_optional_path(payload, "inference", "dataset_path", base_case_path.parent)
    return payload


def canonicalize_parameter_point(value: Any) -> Any:
    """Recursively sort mappings so swept-parameter identity is stable under key reordering."""

    if isinstance(value, dict):
        return {key: canonicalize_parameter_point(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [canonicalize_parameter_point(item) for item in value]
    if isinstance(value, tuple):
        return [canonicalize_parameter_point(item) for item in value]
    return value


def _stable_json(payload: Any) -> str:
    return json.dumps(
        canonicalize_parameter_point(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _payload_hash(payload: Any) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def compute_param_set_hash(parameters: dict[str, Any]) -> str:
    """Hash canonical swept-parameter content only."""

    return _payload_hash(parameters)[:16]


def _normalise_experiment_name(experiment_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", experiment_name).strip("_")
    return cleaned or "experiment"


def build_run_id(
    experiment_name: str,
    param_set_hash: str,
    *,
    repetition_index: int | None = None,
    member_index: int | None = None,
) -> str:
    """Build a deterministic run identifier from experiment name, point hash, and member index."""

    if (repetition_index is None) == (member_index is None):
        raise ManifestValidationError("build_run_id requires exactly one of repetition_index or member_index")
    suffix = f"r{int(repetition_index)}" if repetition_index is not None else f"m{int(member_index)}"
    return f"{_normalise_experiment_name(experiment_name)}__{param_set_hash}__{suffix}"


def build_run_dir(output_dir: str | Path, param_set_hash: str, run_id: str) -> Path:
    """Build the deterministic run-directory path for one experiment run."""

    return Path(output_dir).resolve() / f"param_{param_set_hash}" / run_id


def stage_config(
    base_payload: dict[str, Any],
    *,
    run_dir: str | Path,
    output_root: str | Path,
    swept_parameters: dict[str, Any],
    run_id: str,
    noise_seed: int | None = None,
) -> Path:
    """Stage one expanded config under the scheduled run directory."""

    staged_payload = _build_staged_payload(
        base_payload,
        output_root=output_root,
        swept_parameters=swept_parameters,
        run_id=run_id,
        noise_seed=noise_seed,
    )
    staged_config_path = Path(run_dir) / "source_config.yaml"
    write_expanded_config(staged_payload, staged_config_path)
    return staged_config_path


def expand_parameter_grid(parameters: Sequence[ExperimentSweepParameter]) -> list[dict[str, Any]]:
    """Expand the Cartesian product of experiment sweep parameters."""

    if not parameters:
        return [{}]
    names = [parameter.name for parameter in parameters]
    value_lists = [parameter.values for parameter in parameters]
    grid: list[dict[str, Any]] = []
    for combination in product(*value_lists):
        grid.append({name: deepcopy(value) for name, value in zip(names, combination, strict=True)})
    return grid


def _load_schema_validated_payload(path: Path) -> tuple[dict[str, Any], Path]:
    payload = _read_yaml(path, error_cls=ManifestValidationError)
    schema_version = str(payload.get("schema_version", "")).strip()
    if schema_version.startswith(SEEDED_VORTEX_EXPERIMENT_PACK_SCHEMA_VERSION_PREFIX):
        schema_path = _experiment_pack_schema_path()
    elif schema_version.startswith(SEEDED_VORTEX_ENSEMBLE_PACK_SCHEMA_VERSION_PREFIX):
        schema_path = _experiment_pack_v4_schema_path()
    else:
        raise ManifestValidationError(
            "seeded-vortex experiment pack schema_version must start with '3.' or '4.'"
        )
    _validate_payload_against_schema(
        payload,
        schema_path,
        label="seeded-vortex experiment pack",
        error_cls=ManifestValidationError,
    )
    return payload, schema_path


def load_seeded_vortex_experiment_pack(manifest_path: str | Path) -> SeededVortexExperimentPack:
    """Load and validate an explicit Phase-2.3 or Phase-2.4A experiment-pack manifest."""

    path = Path(manifest_path).resolve()
    payload, _ = _load_schema_validated_payload(path)
    parent_manifest_hash = _payload_hash(payload)
    pack_payload = payload["experiment_pack"]
    base_case_ref = str(pack_payload["base_case"]).strip()
    base_case_path = _resolve_path(base_case_ref, source_dir=path.parent)
    if not base_case_path.exists():
        raise ManifestValidationError(f"experiment pack base_case does not exist: {base_case_ref}")

    base_payload = _normalised_base_payload(base_case_path)
    seen_parameters: set[str] = set()
    sweep_parameters: list[ExperimentSweepParameter] = []
    for item in pack_payload["sweep"]["parameters"]:
        parameter_name = str(item["name"]).strip()
        if parameter_name in seen_parameters:
            raise ManifestValidationError(f"experiment pack contains duplicate sweep parameter '{parameter_name}'")
        _validate_parameter_path_exists(base_payload, parameter_name)
        seen_parameters.add(parameter_name)
        sweep_parameters.append(
            ExperimentSweepParameter(
                name=parameter_name,
                values=[deepcopy(value) for value in item["values"]],
            )
        )

    observables = [str(name).strip() for name in pack_payload["observables"]]
    for observable_name in observables:
        if observable_name not in SUPPORTED_TIER2_OBSERVABLES:
            raise ManifestValidationError(f"unsupported experiment observable '{observable_name}'")
        classify_experiment_observable(observable_name)

    aggregation_metrics = [str(metric).strip() for metric in pack_payload["aggregation"]["metrics"]]
    for metric_name in aggregation_metrics:
        if metric_name not in ALLOWED_EXPERIMENT_AGGREGATION_METRICS:
            raise ManifestValidationError(f"unsupported experiment aggregation metric '{metric_name}'")

    mode = str(pack_payload["mode"])
    ensemble = None
    repetitions = None
    if mode == "deterministic_sweep":
        repetitions = int(pack_payload["repetitions"])
    elif mode == "stochastic_ensemble":
        ensemble_payload = pack_payload["ensemble"]
        ensemble = ExperimentEnsembleSettings(
            member_count=int(ensemble_payload["member_count"]),
            master_seed=int(ensemble_payload["master_seed"]),
        )
    else:  # pragma: no cover - schema already constrains this
        raise ManifestValidationError(f"unsupported experiment pack mode '{mode}'")

    return SeededVortexExperimentPack(
        schema_version=str(payload["schema_version"]),
        pack_name=path.stem,
        manifest_path=str(path),
        mode=mode,
        base_case_ref=base_case_ref,
        base_case_path=str(base_case_path),
        sweep_parameters=sweep_parameters,
        observables=observables,
        aggregation_metrics=aggregation_metrics,
        parent_manifest_hash=parent_manifest_hash,
        repetitions=repetitions,
        ensemble=ensemble,
    )


def _prepare_destination(destination: Path) -> Path:
    if destination.exists():
        if any(destination.iterdir()):
            raise OutputDirectoryError(
                f"experiment output directory already exists and is not empty: {destination}"
            )
    else:
        destination.mkdir(parents=True, exist_ok=True)
    return destination


def _begin_output_transaction(destination: Path) -> tuple[Path, Path]:
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if any(destination.iterdir()):
            raise OutputDirectoryError(
                f"experiment output directory already exists and is not empty: {destination}"
            )
        destination.rmdir()
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent))
    return destination, staging_dir


def _cleanup_staging_directory(staging_dir: Path) -> None:
    shutil.rmtree(staging_dir, ignore_errors=True)


def _cleanup_destination_directory(destination: Path) -> None:
    shutil.rmtree(destination, ignore_errors=True)


def _promote_staging_directory(staging_dir: Path, destination: Path) -> None:
    try:
        staging_dir.replace(destination)
    except Exception:
        _cleanup_destination_directory(destination)
        raise


def _promoted_artifact_paths(artifact_paths: dict[str, str], *, staging_dir: Path, destination: Path) -> dict[str, str]:
    promoted: dict[str, str] = {}
    for key, value in artifact_paths.items():
        path = Path(value).resolve()
        promoted[key] = str(destination / path.relative_to(staging_dir))
    return promoted


def _prepare_run_directory(run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    if any(run_dir.iterdir()):
        raise OutputDirectoryError(f"experiment run directory must be empty before execution: {run_dir}")
    return run_dir


def _selected_observables(tier2_payload: dict[str, Any], observable_names: Sequence[str]) -> dict[str, Any]:
    extracted = extract_observables(tier2_payload, required=observable_names)
    return {observable_name: extracted[observable_name] for observable_name in observable_names}


def _build_experiment_metadata(
    *,
    experiment_name: str,
    mode: str,
    manifest_path: str,
    base_case_path: str,
    parent_manifest_hash: str,
    base_case_hash: str,
    param_set_hash: str,
    swept_parameters: dict[str, Any],
    run_id: str,
    repetition_index: int | None,
) -> dict[str, Any]:
    return {
        "experiment_name": experiment_name,
        "mode": mode,
        "manifest_path": manifest_path,
        "base_case_path": base_case_path,
        "parent_manifest_hash": parent_manifest_hash,
        "base_case_hash": base_case_hash,
        "param_set_hash": param_set_hash,
        "repetition_index": repetition_index,
        "run_id": run_id,
        "swept_parameters": deepcopy(swept_parameters),
    }


def _validate_experiment_provenance(
    provenance_payload: dict[str, Any],
    *,
    experiment_name: str,
    mode: str,
    manifest_path: str,
    base_case_path: str,
    parent_manifest_hash: str,
    base_case_hash: str,
    param_set_hash: str,
    swept_parameters: dict[str, Any],
    run_id: str,
    repetition_index: int | None,
    ensemble_metadata: dict[str, Any] | None = None,
) -> None:
    experiment_payload = provenance_payload.get("experiment")
    if not isinstance(experiment_payload, dict):
        raise TDGLRFError("experiment run provenance is missing the experiment block")
    expected_experiment = _build_experiment_metadata(
        experiment_name=experiment_name,
        mode=mode,
        manifest_path=manifest_path,
        base_case_path=base_case_path,
        parent_manifest_hash=parent_manifest_hash,
        base_case_hash=base_case_hash,
        param_set_hash=param_set_hash,
        swept_parameters=swept_parameters,
        run_id=run_id,
        repetition_index=repetition_index,
    )
    if experiment_payload != expected_experiment:
        raise TDGLRFError(
            f"experiment provenance mismatch: expected {expected_experiment!r} observed {experiment_payload!r}"
        )
    if ensemble_metadata is None:
        if "ensemble" in provenance_payload:
            raise TDGLRFError("deterministic experiment provenance unexpectedly included an ensemble block")
        return
    if provenance_payload.get("ensemble") != ensemble_metadata:
        raise TDGLRFError(
            f"ensemble provenance mismatch: expected {ensemble_metadata!r} observed {provenance_payload.get('ensemble')!r}"
        )


def _schedule_member_seeds(
    *,
    master_seed: int,
    experiment_name: str,
    param_set_hash: str,
    parent_manifest_hash: str,
    member_count: int,
) -> list[int]:
    return [
        derive_seed(master_seed, experiment_name, param_set_hash, parent_manifest_hash, member_index)
        for member_index in range(int(member_count))
    ]


def _build_ensemble_metadata(
    *,
    ensemble_id: str,
    member_index: int,
    noise_seed: int,
    member_count: int,
    master_seed: int,
    parent_manifest_hash: str,
) -> dict[str, Any]:
    return {
        "mode": "stochastic_ensemble",
        "ensemble_id": ensemble_id,
        "member_index": int(member_index),
        "noise_seed": int(noise_seed),
        "member_count": int(member_count),
        "master_seed": int(master_seed),
        "parent_manifest_hash": parent_manifest_hash,
    }


def _compute_ensemble_id(*, pack: SeededVortexExperimentPack, param_set_hash: str) -> str:
    return _payload_hash(
        {
            "pack_name": pack.pack_name,
            "param_set_hash": param_set_hash,
            "parent_manifest_hash": pack.parent_manifest_hash,
        }
    )[:16]


def _build_staged_payload(
    base_payload: dict[str, Any],
    *,
    output_root: str | Path,
    swept_parameters: dict[str, Any],
    run_id: str,
    noise_seed: int | None = None,
) -> dict[str, Any]:
    staged_payload = deepcopy(base_payload)
    for parameter_name, parameter_value in swept_parameters.items():
        _set_parameter_value(staged_payload, parameter_name, parameter_value)
    staged_payload.setdefault("metadata", {})
    staged_payload["metadata"]["case_id"] = run_id
    staged_payload.setdefault("output", {})
    staged_payload["output"]["root_dir"] = str(Path(output_root).resolve())
    if noise_seed is not None:
        staged_payload.setdefault("noise", {})
        staged_payload["noise"]["seed"] = int(noise_seed)
        staged_payload["noise"].pop("master_seed", None)
    return staged_payload


def _validate_planned_member_identity(plans: Sequence[EnsembleMemberPlan]) -> None:
    seen_run_ids: set[str] = set()
    seen_run_dirs: set[str] = set()
    per_ensemble_member_indices: dict[str, set[int]] = {}
    per_ensemble_noise_seeds: dict[str, set[int]] = {}
    for plan in plans:
        if plan.run_id in seen_run_ids:
            raise TDGLRFError(f"duplicate ensemble run_id detected in plan: {plan.run_id}")
        seen_run_ids.add(plan.run_id)
        if plan.run_dir in seen_run_dirs:
            raise TDGLRFError(f"duplicate ensemble run_dir detected in plan: {plan.run_dir}")
        seen_run_dirs.add(plan.run_dir)
        member_indices = per_ensemble_member_indices.setdefault(plan.ensemble_id, set())
        if plan.member_index in member_indices:
            raise TDGLRFError(
                f"duplicate member_index {plan.member_index} detected for ensemble_id {plan.ensemble_id}"
            )
        member_indices.add(plan.member_index)
        noise_seeds = per_ensemble_noise_seeds.setdefault(plan.ensemble_id, set())
        if plan.noise_seed in noise_seeds:
            raise TDGLRFError(
                f"duplicate noise_seed {plan.noise_seed} detected for ensemble_id {plan.ensemble_id}"
            )
        noise_seeds.add(plan.noise_seed)


def _validate_success_metadata(run_dir: Path, *, run_id: str) -> None:
    status_payload = _read_json(run_dir / "status.json", error_cls=TDGLRFError)
    if str(status_payload.get("status")) != "success":
        raise TDGLRFError(f"run '{run_id}' did not finish with success status metadata")
    summary_payload = _read_json(run_dir / "diagnostics" / "run_summary.json", error_cls=TDGLRFError)
    if str(summary_payload.get("status")) != "success":
        raise TDGLRFError(f"run '{run_id}' is missing successful run_summary metadata")


def derive_noise_seed_from_provenance(provenance_payload: dict[str, Any]) -> int:
    """Re-derive the executed noise seed from provenance identity fields."""

    ensemble_payload = provenance_payload.get("ensemble")
    if not isinstance(ensemble_payload, dict):
        noise_payload = provenance_payload.get("noise")
        if not isinstance(noise_payload, dict) or "seed" not in noise_payload:
            raise TDGLRFError("provenance is missing the normalized noise contract")
        return int(noise_payload["seed"])

    experiment_payload = provenance_payload.get("experiment")
    if not isinstance(experiment_payload, dict):
        raise TDGLRFError("ensemble provenance is missing the experiment block")
    return derive_seed(
        int(ensemble_payload["master_seed"]),
        str(experiment_payload["experiment_name"]),
        str(experiment_payload["param_set_hash"]),
        str(ensemble_payload["parent_manifest_hash"]),
        int(ensemble_payload["member_index"]),
    )


def rebuild_member_config_from_provenance(provenance_payload: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the executed expanded config payload from replay-relevant provenance only."""

    experiment_payload = provenance_payload.get("experiment")
    if not isinstance(experiment_payload, dict):
        raise TDGLRFError("provenance is missing the replay experiment block")
    config_payload = provenance_payload.get("config")
    if not isinstance(config_payload, dict):
        raise TDGLRFError("provenance is missing the config block")
    output_root_dir = config_payload.get("output_root_dir")
    if not output_root_dir:
        raise TDGLRFError("provenance is missing config.output_root_dir")

    base_case_path = Path(str(experiment_payload["base_case_path"])).resolve()
    base_payload = _normalised_base_payload(base_case_path)
    noise_seed = None
    noise_payload = provenance_payload.get("noise")
    if isinstance(noise_payload, dict) and bool(noise_payload.get("enabled")):
        noise_seed = derive_noise_seed_from_provenance(provenance_payload)
    return _build_staged_payload(
        base_payload,
        output_root=str(output_root_dir),
        swept_parameters=dict(experiment_payload["swept_parameters"]),
        run_id=str(experiment_payload["run_id"]),
        noise_seed=noise_seed,
    )


def _validate_replayable_provenance(provenance_payload: dict[str, Any]) -> None:
    rebuilt_payload = rebuild_member_config_from_provenance(provenance_payload)
    experiment_payload = provenance_payload.get("experiment")
    assert isinstance(experiment_payload, dict)  # narrowed by rebuild_member_config_from_provenance
    rebuilt_config = validate_case_config(
        rebuilt_payload,
        _provenance_schema_path().parent / "tdgl_case.schema.json",
        Path(str(experiment_payload["base_case_path"])).resolve().parent,
    )
    observed_config_hash = str(provenance_payload.get("config_hash"))
    rebuilt_hash = config_hash(rebuilt_config)
    if rebuilt_hash != observed_config_hash:
        raise TDGLRFError(
            f"replay config_hash mismatch: expected {observed_config_hash} observed {rebuilt_hash}"
        )
    derived_noise_seed = derive_noise_seed_from_provenance(provenance_payload)
    noise_payload = provenance_payload.get("noise")
    if not isinstance(noise_payload, dict) or int(noise_payload["seed"]) != derived_noise_seed:
        raise TDGLRFError(
            f"replay noise seed mismatch: expected {derived_noise_seed} observed {noise_payload!r}"
        )
    ensemble_payload = provenance_payload.get("ensemble")
    if isinstance(ensemble_payload, dict) and int(ensemble_payload["noise_seed"]) != derived_noise_seed:
        raise TDGLRFError(
            f"ensemble noise_seed mismatch: expected {derived_noise_seed} observed {ensemble_payload['noise_seed']}"
        )


def build_stochastic_ensemble_plan(
    pack: SeededVortexExperimentPack,
    *,
    output_dir: str | Path | None = None,
) -> EnsembleExecutionPlan:
    """Define the accepted-manifest and planned-provenance contract for a gated Phase-2.4A pack."""

    if pack.mode != "stochastic_ensemble" or pack.ensemble is None:
        raise ManifestValidationError("build_stochastic_ensemble_plan requires a stochastic ensemble manifest")

    destination = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (repo_root() / "runs" / f"experiment_{pack.pack_name}").resolve()
    )
    parameter_grid = expand_parameter_grid(pack.sweep_parameters)
    members: list[EnsembleMemberPlan] = []
    base_case_hash = _payload_hash(_normalised_base_payload(Path(pack.base_case_path)))
    for parameter_values in parameter_grid:
        canonical_parameters = canonicalize_parameter_point(parameter_values)
        param_set_hash = compute_param_set_hash(canonical_parameters)
        ensemble_id = _compute_ensemble_id(pack=pack, param_set_hash=param_set_hash)
        member_seeds = _schedule_member_seeds(
            master_seed=pack.ensemble.master_seed,
            experiment_name=pack.pack_name,
            param_set_hash=param_set_hash,
            parent_manifest_hash=pack.parent_manifest_hash,
            member_count=pack.ensemble.member_count,
        )
        for member_index, noise_seed in enumerate(member_seeds):
            run_id = build_run_id(
                pack.pack_name,
                param_set_hash,
                member_index=member_index,
            )
            experiment_metadata = _build_experiment_metadata(
                experiment_name=pack.pack_name,
                mode=pack.mode,
                manifest_path=pack.manifest_path,
                base_case_path=pack.base_case_path,
                parent_manifest_hash=pack.parent_manifest_hash,
                base_case_hash=base_case_hash,
                param_set_hash=param_set_hash,
                swept_parameters=canonical_parameters,
                run_id=run_id,
                repetition_index=None,
            )
            ensemble_metadata = _build_ensemble_metadata(
                ensemble_id=ensemble_id,
                member_index=member_index,
                noise_seed=noise_seed,
                member_count=pack.ensemble.member_count,
                master_seed=pack.ensemble.master_seed,
                parent_manifest_hash=pack.parent_manifest_hash,
            )
            members.append(
                EnsembleMemberPlan(
                    run_id=run_id,
                    run_dir=str(build_run_dir(destination, param_set_hash, run_id)),
                    ensemble_id=ensemble_id,
                    param_set_hash=param_set_hash,
                    member_index=member_index,
                    noise_seed=noise_seed,
                    parent_manifest_hash=pack.parent_manifest_hash,
                    swept_parameters=deepcopy(canonical_parameters),
                    experiment_metadata=experiment_metadata,
                    ensemble_metadata=ensemble_metadata,
                )
            )
    _validate_planned_member_identity(members)
    return EnsembleExecutionPlan(
        manifest_path=pack.manifest_path,
        pack_name=pack.pack_name,
        base_case_path=pack.base_case_path,
        output_dir=str(destination),
        parameter_point_count=len(parameter_grid),
        planned_run_count=len(members),
        members=members,
    )


def execute_deterministic_sweep(
    pack: SeededVortexExperimentPack,
    *,
    output_dir: str | Path | None = None,
) -> ExperimentSweepSummary:
    """Execute a deterministic Phase-2.3 seeded-vortex experiment pack."""

    if pack.mode != "deterministic_sweep" or pack.repetitions is None:
        raise ManifestValidationError("execute_deterministic_sweep requires a deterministic experiment-pack manifest")

    destination = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (repo_root() / "runs" / f"experiment_{pack.pack_name}").resolve()
    )
    destination, staging_destination = _begin_output_transaction(destination)
    base_payload = _normalised_base_payload(Path(pack.base_case_path))
    base_case_hash = _payload_hash(base_payload)
    parameter_grid = expand_parameter_grid(pack.sweep_parameters)
    run_records: list[dict[str, Any]] = []
    try:
        for parameter_values in parameter_grid:
            canonical_parameters = canonicalize_parameter_point(parameter_values)
            param_set_hash = compute_param_set_hash(canonical_parameters)
            for repetition_index in range(pack.repetitions):
                run_id = build_run_id(
                    pack.pack_name,
                    param_set_hash,
                    repetition_index=repetition_index,
                )
                final_run_dir = build_run_dir(destination, param_set_hash, run_id)
                run_dir = _prepare_run_directory(build_run_dir(staging_destination, param_set_hash, run_id))
                staged_config_path = stage_config(
                    base_payload,
                    run_dir=run_dir,
                    output_root=destination,
                    swept_parameters=canonical_parameters,
                    run_id=run_id,
                )
                summary = run_simulation(
                    staged_config_path,
                    run_dir_override=run_dir,
                    experiment_metadata=_build_experiment_metadata(
                        experiment_name=pack.pack_name,
                        mode=pack.mode,
                        manifest_path=pack.manifest_path,
                        base_case_path=pack.base_case_path,
                        parent_manifest_hash=pack.parent_manifest_hash,
                        base_case_hash=base_case_hash,
                        param_set_hash=param_set_hash,
                        swept_parameters=canonical_parameters,
                        run_id=run_id,
                        repetition_index=repetition_index,
                    ),
                )
                actual_run_dir = Path(summary.run_dir)
                _validate_success_metadata(actual_run_dir, run_id=run_id)
                provenance_payload = _read_json(actual_run_dir / "provenance.json", error_cls=TDGLRFError)
                tier2_payload = _read_json(
                    actual_run_dir / "diagnostics" / "seeded_vortex_tier2.json",
                    error_cls=Tier2ContractError,
                )
                _validate_payload_against_schema(
                    provenance_payload,
                    _provenance_schema_path(),
                    label=f"experiment provenance for {run_id}",
                    error_cls=TDGLRFError,
                )
                _validate_payload_against_schema(
                    tier2_payload,
                    _tier2_schema_path(),
                    label=f"experiment tier2 payload for {run_id}",
                    error_cls=Tier2ContractError,
                )
                _validate_experiment_provenance(
                    provenance_payload,
                    experiment_name=pack.pack_name,
                    mode=pack.mode,
                    manifest_path=pack.manifest_path,
                    base_case_path=pack.base_case_path,
                    parent_manifest_hash=pack.parent_manifest_hash,
                    base_case_hash=base_case_hash,
                    param_set_hash=param_set_hash,
                    swept_parameters=canonical_parameters,
                    run_id=run_id,
                    repetition_index=repetition_index,
                )
                _validate_replayable_provenance(provenance_payload)
                run_records.append(
                    {
                        "run_id": run_id,
                        "param_set_hash": param_set_hash,
                        "parameters": deepcopy(canonical_parameters),
                        "repetition_index": repetition_index,
                        "run_dir": str(final_run_dir),
                        "case_class": tier2_payload.get("case_class"),
                        "status": "success",
                        "observables": _selected_observables(tier2_payload, pack.observables),
                        "notes": "completed deterministic same-stack experiment repetition",
                    }
                )

        payload = aggregate_experiment_results(
            schema_version=pack.schema_version,
            pack_name=pack.pack_name,
            manifest_path=pack.manifest_path,
            base_case_path=pack.base_case_path,
            repetitions=pack.repetitions,
            sweep_parameters=[parameter.name for parameter in pack.sweep_parameters],
            observables=pack.observables,
            aggregation_metrics=pack.aggregation_metrics,
            run_records=run_records,
        )
        artifact_paths = write_experiment_result_artifacts(staging_destination, payload)
        _promote_staging_directory(staging_destination, destination)
        promoted_artifact_paths = _promoted_artifact_paths(
            artifact_paths,
            staging_dir=staging_destination,
            destination=destination,
        )
        return ExperimentSweepSummary(
            status=str(payload["overall_status"]),
            manifest_path=pack.manifest_path,
            output_dir=str(destination),
            results_json_path=promoted_artifact_paths["results_json_path"],
            results_csv_path=promoted_artifact_paths["results_csv_path"],
            results_markdown_path=promoted_artifact_paths["results_markdown_path"],
            parameter_point_count=int(payload["parameter_point_count"]),
            run_count=int(payload["run_count"]),
        )
    except Exception:
        _cleanup_staging_directory(staging_destination)
        _cleanup_destination_directory(destination)
        raise


def execute_stochastic_ensemble(
    pack: SeededVortexExperimentPack,
    *,
    output_dir: str | Path | None = None,
) -> ExperimentSweepSummary:
    """Execute a strict Phase-2.4A stochastic ensemble with fail-fast artifact semantics."""

    if pack.mode != "stochastic_ensemble" or pack.ensemble is None:
        raise ManifestValidationError("execute_stochastic_ensemble requires a stochastic ensemble manifest")

    require_phase2_4a_stochastic_runtime(context="Phase-2.4A ensemble execution")
    plan = build_stochastic_ensemble_plan(pack, output_dir=output_dir)
    destination, staging_destination = _begin_output_transaction(Path(plan.output_dir))
    base_payload = _normalised_base_payload(Path(pack.base_case_path))
    base_case_hash = _payload_hash(base_payload)
    planned_members = []

    try:
        for member in plan.members:
            final_run_dir = Path(member.run_dir)
            staging_run_dir = _prepare_run_directory(
                staging_destination / final_run_dir.relative_to(destination)
            )
            staged_config_path = stage_config(
                base_payload,
                run_dir=staging_run_dir,
                output_root=destination,
                swept_parameters=member.swept_parameters,
                run_id=member.run_id,
                noise_seed=member.noise_seed,
            )
            planned_members.append(
                {
                    "plan": member,
                    "config_path": str(staged_config_path),
                    "staging_run_dir": staging_run_dir,
                    "final_run_dir": final_run_dir,
                }
            )

        execute_ensemble_plan(
            [
                {
                    "run_id": item["plan"].run_id,
                    "run_dir": str(item["staging_run_dir"]),
                    "config_path": item["config_path"],
                    "member_index": item["plan"].member_index,
                    "noise_seed": item["plan"].noise_seed,
                    "experiment_metadata": item["plan"].experiment_metadata,
                    "ensemble_metadata": item["plan"].ensemble_metadata,
                }
                for item in planned_members
            ]
        )

        run_records: list[dict[str, Any]] = []
        for item in planned_members:
            member = item["plan"]
            actual_run_dir = Path(item["staging_run_dir"])
            _validate_success_metadata(actual_run_dir, run_id=member.run_id)
            provenance_payload = _read_json(actual_run_dir / "provenance.json", error_cls=TDGLRFError)
            tier2_payload = _read_json(
                actual_run_dir / "diagnostics" / "seeded_vortex_tier2.json",
                error_cls=Tier2ContractError,
            )
            _validate_payload_against_schema(
                provenance_payload,
                _provenance_schema_path(),
                label=f"ensemble provenance for {member.run_id}",
                error_cls=TDGLRFError,
            )
            _validate_payload_against_schema(
                tier2_payload,
                _tier2_schema_path(),
                label=f"ensemble tier2 payload for {member.run_id}",
                error_cls=Tier2ContractError,
            )
            _validate_experiment_provenance(
                provenance_payload,
                experiment_name=pack.pack_name,
                mode=pack.mode,
                manifest_path=pack.manifest_path,
                base_case_path=pack.base_case_path,
                parent_manifest_hash=pack.parent_manifest_hash,
                base_case_hash=base_case_hash,
                param_set_hash=member.param_set_hash,
                swept_parameters=member.swept_parameters,
                run_id=member.run_id,
                repetition_index=None,
                ensemble_metadata=member.ensemble_metadata,
            )
            _validate_replayable_provenance(provenance_payload)
            run_records.append(
                {
                    "run_id": member.run_id,
                    "ensemble_id": member.ensemble_id,
                    "param_set_hash": member.param_set_hash,
                    "parent_manifest_hash": pack.parent_manifest_hash,
                    "parameters": deepcopy(member.swept_parameters),
                    "member_index": member.member_index,
                    "noise_seed": member.noise_seed,
                    "run_dir": str(item["final_run_dir"]),
                    "case_class": tier2_payload.get("case_class"),
                    "status": "success",
                    "observables": _selected_observables(tier2_payload, pack.observables),
                    "notes": "completed stochastic same-stack ensemble member",
                }
            )

        payload = aggregate_ensemble_results(
            schema_version=pack.schema_version,
            pack_name=pack.pack_name,
            manifest_path=pack.manifest_path,
            base_case_path=pack.base_case_path,
            parent_manifest_hash=pack.parent_manifest_hash,
            expected_member_count=pack.ensemble.member_count,
            sweep_parameters=[parameter.name for parameter in pack.sweep_parameters],
            observables=pack.observables,
            aggregation_metrics=pack.aggregation_metrics,
            run_records=run_records,
        )
        artifact_paths = write_experiment_result_artifacts(staging_destination, payload)
        _promote_staging_directory(staging_destination, destination)
        promoted_artifact_paths = _promoted_artifact_paths(
            artifact_paths,
            staging_dir=staging_destination,
            destination=destination,
        )
        return ExperimentSweepSummary(
            status=str(payload["overall_status"]),
            manifest_path=pack.manifest_path,
            output_dir=str(destination),
            results_json_path=promoted_artifact_paths["results_json_path"],
            results_csv_path=promoted_artifact_paths["results_csv_path"],
            results_markdown_path=promoted_artifact_paths["results_markdown_path"],
            parameter_point_count=int(payload["parameter_point_count"]),
            run_count=int(payload["run_count"]),
        )
    except Exception:
        _cleanup_staging_directory(staging_destination)
        _cleanup_destination_directory(destination)
        raise


def run_seeded_vortex_experiment_pack(
    manifest_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> ExperimentSweepSummary:
    """Execute an explicit deterministic experiment pack or gate the unsupported ensemble mode."""

    pack = load_seeded_vortex_experiment_pack(manifest_path)
    if pack.mode == "deterministic_sweep":
        return execute_deterministic_sweep(pack, output_dir=output_dir)
    return execute_stochastic_ensemble(pack, output_dir=output_dir)
