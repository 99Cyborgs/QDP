"""Phase-2.2 seeded-vortex experiment-pack validation."""

from __future__ import annotations

from copy import deepcopy
import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from qdp_io.serialization import write_csv, write_json
import yaml

from qdp_tdgl.config.loaders import load_case_config, load_raw_config, repo_root, tdgl_config_root, write_expanded_config
from qdp_tdgl.diagnostics.seeded_vortex import (
    SEEDED_CASE_CLASS_INITIALIZATION_ONLY,
    SEEDED_CASE_CLASS_SHORT_HORIZON,
    SEEDED_SAMPLING_POLICY_ALL_OBSERVABLE_SAMPLES,
    SEEDED_SAMPLING_POLICY_INITIALIZATION_SURFACE,
)
from qdp_tdgl.exceptions import ConfigError, SEED_REJECTION_TAXONOMY_VERSION, SeedRejectionError
from qdp_tdgl.geometry.masks import build_geometry, grid_from_config
from qdp_tdgl.solvers.seeded_vortices import (
    SEED_RESOLUTION_POLICY,
    configured_seed_payloads,
    resolve_vortex_seeds,
    resolved_seed_payloads,
)
from qdp_tdgl.workflows.run_case import run_simulation


SEEDED_VORTEX_EXPERIMENT_MANIFEST_SCHEMA_VERSION = "tdgl_rf.seeded_vortex_experiment_pack.v1"
SEEDED_VORTEX_VALIDATED_SURFACES = {
    SEEDED_CASE_CLASS_INITIALIZATION_ONLY: "deterministic_seeded_initialization_same_stack",
    SEEDED_CASE_CLASS_SHORT_HORIZON: "deterministic_seeded_short_horizon_same_stack",
    "rejection_case": "seeded_input_rejection_taxonomy",
}
SEEDED_VORTEX_REQUIRED_NON_CLAIMS = {
    "equilibrium_preparation": "not established by this suite",
    "long_time_dynamics": "not established by this suite",
    "stochastic_behavior": "not established by this suite",
    "cross_stack_portability": "not established by this suite",
}


@dataclass(frozen=True)
class SeededVortexHorizonContract:
    n_steps: int
    sampling_policy: str


@dataclass(frozen=True)
class SeededVortexCanonicalCaseSpec:
    case_id: str
    case_class: str
    config_ref: str
    config_path: str
    expected_summary: dict[str, Any]
    expected_final_observables: dict[str, Any]
    expected_payload_sha256: str
    expected_tier2: dict[str, Any]


@dataclass(frozen=True)
class SeededVortexExerciseCaseSpec:
    case_id: str
    case_class: str
    config_ref: str
    config_path: str
    expected_invariants: dict[str, Any]


@dataclass(frozen=True)
class SeededVortexRejectionCaseSpec:
    case_id: str
    config_ref: str
    config_path: str
    expected_stage: str
    expected_rejection: dict[str, Any]


@dataclass(frozen=True)
class SeededVortexExperimentSuite:
    schema_version: str
    suite_id: str
    claim_scope: str
    horizon_contracts: dict[str, SeededVortexHorizonContract]
    canonical_cases: list[SeededVortexCanonicalCaseSpec]
    exercise_cases: list[SeededVortexExerciseCaseSpec]
    rejection_cases: list[SeededVortexRejectionCaseSpec]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ConfigError(f"expected mapping at top level of {path}")
    return payload


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _coerce_scalar(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return text
        try:
            if any(token in text for token in (".", "e", "E")):
                return float(text)
            return int(text)
        except ValueError:
            return text
    return value


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_path(reference_path: str, *, source_dir: Path) -> Path:
    candidate = Path(reference_path)
    if candidate.is_absolute():
        return candidate.resolve()
    source_relative = (source_dir / candidate).resolve()
    repo_relative = (repo_root() / candidate).resolve()
    return source_relative if source_relative.exists() else repo_relative


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


def _stage_config(config_path: Path, destination_dir: Path, output_root: Path) -> Path:
    raw = load_raw_config(config_path)
    payload = deepcopy(raw)
    payload["base_config"] = None
    payload.setdefault("output", {})
    payload["output"]["root_dir"] = str(output_root.resolve())
    _absolutize_optional_path(payload, "physics", "restart_file", config_path.parent)
    _absolutize_optional_path(payload, "geometry", "mask_file", config_path.parent)
    _absolutize_optional_path(payload, "forcing", "rf_profile_file", config_path.parent)
    _absolutize_optional_path(payload, "inference", "dataset_path", config_path.parent)
    staged_config = destination_dir / config_path.name
    write_expanded_config(payload, staged_config)
    return staged_config


def _extract_run_payload(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    summary_path = run_dir / "observables" / "summary.json"
    timeseries_path = run_dir / "observables" / "timeseries.csv"
    if not summary_path.exists():
        raise FileNotFoundError(f"missing observables summary: {summary_path}")
    if not timeseries_path.exists():
        raise FileNotFoundError(f"missing observables timeseries: {timeseries_path}")
    summary_metrics = _read_json(summary_path)
    timeseries_rows = _read_csv_rows(timeseries_path)
    if not timeseries_rows:
        raise FileNotFoundError(f"timeseries contained zero rows: {timeseries_path}")
    final_row_raw = timeseries_rows[-1]
    final_observables = {key: _coerce_scalar(value) for key, value in final_row_raw.items()}
    payload_for_hash = {
        "summary_metrics": summary_metrics,
        "final_observables": final_observables,
    }
    return summary_metrics, final_observables, payload_for_hash


def _extract_seeded_tier2_payload(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "diagnostics" / "seeded_vortex_tier2.json"
    if not path.exists():
        raise FileNotFoundError(f"missing seeded-vortex Tier-2 diagnostics: {path}")
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ConfigError(f"seeded-vortex Tier-2 payload must be a mapping: {path}")
    return payload


def _schema_error_location(parts: list[Any]) -> str:
    return ".".join(str(part) for part in parts) or "<root>"


def _validate_payload_against_schema(payload: dict[str, Any], schema_path: Path, *, label: str) -> None:
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    if errors:
        first = errors[0]
        raise ConfigError(f"{label} schema validation failed at {_schema_error_location(list(first.absolute_path))}: {first.message}")


def _seeded_vortex_manifest_schema_path() -> Path:
    return tdgl_config_root() / "seeded_vortex_experiment_manifest.schema.json"


def _seeded_vortex_tier2_schema_path() -> Path:
    return tdgl_config_root() / "seeded_vortex_tier2.schema.json"


def _seeded_vortex_rejection_schema_path() -> Path:
    return tdgl_config_root() / "seeded_vortex_rejection.schema.json"


def _seeded_vortex_provenance_schema_path() -> Path:
    return tdgl_config_root() / "tdgl_run_provenance.schema.json"


def _build_seeded_horizon_contract(payload: dict[str, Any]) -> SeededVortexHorizonContract:
    return SeededVortexHorizonContract(
        n_steps=int(payload["n_steps"]),
        sampling_policy=str(payload["sampling_policy"]),
    )


def load_seeded_vortex_experiment_suite(manifest_path: str | Path) -> SeededVortexExperimentSuite:
    path = Path(manifest_path).resolve()
    payload = _read_yaml(path)
    _validate_payload_against_schema(
        payload,
        _seeded_vortex_manifest_schema_path(),
        label="seeded-vortex experiment manifest",
    )

    defaults_payload = payload["defaults"]["horizon_contracts"]
    horizon_contracts = {
        SEEDED_CASE_CLASS_INITIALIZATION_ONLY: _build_seeded_horizon_contract(defaults_payload[SEEDED_CASE_CLASS_INITIALIZATION_ONLY]),
        SEEDED_CASE_CLASS_SHORT_HORIZON: _build_seeded_horizon_contract(defaults_payload[SEEDED_CASE_CLASS_SHORT_HORIZON]),
    }

    seen_case_ids: set[str] = set()

    def _check_case_id(case_id: str) -> None:
        if case_id in seen_case_ids:
            raise ConfigError(f"seeded-vortex experiment suite contains duplicate case_id '{case_id}'")
        seen_case_ids.add(case_id)

    canonical_cases: list[SeededVortexCanonicalCaseSpec] = []
    for item in payload.get("canonical_cases", []):
        case_id = str(item["case_id"]).strip()
        _check_case_id(case_id)
        config_ref = str(item["config_path"]).strip()
        config_path = _resolve_path(config_ref, source_dir=path.parent)
        if not config_path.exists():
            raise ConfigError(f"canonical case '{case_id}' config_path does not exist: {config_ref}")
        canonical_cases.append(
            SeededVortexCanonicalCaseSpec(
                case_id=case_id,
                case_class=str(item["case_class"]),
                config_ref=config_ref,
                config_path=str(config_path),
                expected_summary=dict(item["expected_summary"]),
                expected_final_observables=dict(item["expected_final_observables"]),
                expected_payload_sha256=str(item["expected_payload_sha256"]),
                expected_tier2=dict(item["expected_tier2"]),
            )
        )

    exercise_cases: list[SeededVortexExerciseCaseSpec] = []
    for item in payload.get("exercise_cases", []):
        case_id = str(item["case_id"]).strip()
        _check_case_id(case_id)
        config_ref = str(item["config_path"]).strip()
        config_path = _resolve_path(config_ref, source_dir=path.parent)
        if not config_path.exists():
            raise ConfigError(f"exercise case '{case_id}' config_path does not exist: {config_ref}")
        exercise_cases.append(
            SeededVortexExerciseCaseSpec(
                case_id=case_id,
                case_class=str(item["case_class"]),
                config_ref=config_ref,
                config_path=str(config_path),
                expected_invariants=dict(item["expected_invariants"]),
            )
        )

    rejection_cases: list[SeededVortexRejectionCaseSpec] = []
    for item in payload.get("rejection_cases", []):
        case_id = str(item["case_id"]).strip()
        _check_case_id(case_id)
        config_ref = str(item["config_path"]).strip()
        config_path = _resolve_path(config_ref, source_dir=path.parent)
        if not config_path.exists():
            raise ConfigError(f"rejection case '{case_id}' config_path does not exist: {config_ref}")
        rejection_cases.append(
            SeededVortexRejectionCaseSpec(
                case_id=case_id,
                config_ref=config_ref,
                config_path=str(config_path),
                expected_stage=str(item["expected_stage"]),
                expected_rejection=dict(item["expected_rejection"]),
            )
        )

    return SeededVortexExperimentSuite(
        schema_version=str(payload["schema_version"]),
        suite_id=str(payload["suite_id"]),
        claim_scope=str(payload["claim_scope"]),
        horizon_contracts=horizon_contracts,
        canonical_cases=canonical_cases,
        exercise_cases=exercise_cases,
        rejection_cases=rejection_cases,
    )


def _configured_seeded_vortex_totals(config) -> dict[str, int]:
    positive_winding = int(sum(max(int(seed.winding), 0) for seed in config.physics.vortex_seeds))
    negative_winding = int(sum(max(-int(seed.winding), 0) for seed in config.physics.vortex_seeds))
    total_abs = int(sum(abs(int(seed.winding)) for seed in config.physics.vortex_seeds))
    return {
        "configured_positive_winding": positive_winding,
        "configured_negative_winding": negative_winding,
        "configured_signed_winding": positive_winding - negative_winding,
        "configured_abs_winding": total_abs,
    }


def _seeded_case_mismatch(
    *,
    case_id: str,
    case_class: str,
    artifact: str,
    path: str,
    expected: Any,
    observed: Any,
    assessment: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "case_class": case_class,
        "artifact": artifact,
        "path": path,
        "expected": expected,
        "observed": observed,
        "assessment": assessment,
    }


def _collect_subset_mismatches(
    expected: Any,
    observed: Any,
    *,
    case_id: str,
    case_class: str,
    artifact: str,
    path_prefix: str = "",
) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    if isinstance(expected, dict):
        if not isinstance(observed, dict):
            mismatches.append(
                _seeded_case_mismatch(
                    case_id=case_id,
                    case_class=case_class,
                    artifact=artifact,
                    path=path_prefix or "<root>",
                    expected="mapping",
                    observed=observed,
                    assessment="type_mismatch",
                )
            )
            return mismatches
        for key, expected_value in expected.items():
            current_path = key if not path_prefix else f"{path_prefix}.{key}"
            if key not in observed:
                mismatches.append(
                    _seeded_case_mismatch(
                        case_id=case_id,
                        case_class=case_class,
                        artifact=artifact,
                        path=current_path,
                        expected=expected_value,
                        observed="<missing>",
                        assessment="missing_value",
                    )
                )
                continue
            mismatches.extend(
                _collect_subset_mismatches(
                    expected_value,
                    observed[key],
                    case_id=case_id,
                    case_class=case_class,
                    artifact=artifact,
                    path_prefix=current_path,
                )
            )
        return mismatches
    if observed != expected:
        mismatches.append(
            _seeded_case_mismatch(
                case_id=case_id,
                case_class=case_class,
                artifact=artifact,
                path=path_prefix or "<root>",
                expected=expected,
                observed=observed,
                assessment="value_mismatch",
            )
        )
    return mismatches


def _seeded_case_note(mismatch_records: list[dict[str, Any]], success_message: str) -> str:
    if not mismatch_records:
        return success_message
    head = mismatch_records[:3]
    summary = "; ".join(
        f"{record['artifact']}:{record['path']} expected {record['expected']!r} observed {record['observed']!r}"
        for record in head
    )
    if len(mismatch_records) > len(head):
        summary += f"; +{len(mismatch_records) - len(head)} more"
    return summary


def _seeded_validated_surfaces(suite: SeededVortexExperimentSuite) -> list[str]:
    surfaces: list[str] = []
    success_case_classes = {case.case_class for case in (*suite.canonical_cases, *suite.exercise_cases)}
    for case_class in (SEEDED_CASE_CLASS_INITIALIZATION_ONLY, SEEDED_CASE_CLASS_SHORT_HORIZON):
        if case_class in success_case_classes:
            surfaces.append(SEEDED_VORTEX_VALIDATED_SURFACES[case_class])
    if suite.rejection_cases:
        surfaces.append(SEEDED_VORTEX_VALIDATED_SURFACES["rejection_case"])
    return surfaces


def _seeded_case_class_counts(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts = {
        SEEDED_CASE_CLASS_INITIALIZATION_ONLY: {"total": 0, "passed": 0},
        SEEDED_CASE_CLASS_SHORT_HORIZON: {"total": 0, "passed": 0},
        "rejection_case": {"total": 0, "passed": 0},
    }
    for record in records:
        bucket = counts.setdefault(str(record["case_class"]), {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += int(bool(record["overall_pass"]))
    return counts


def _expected_observed_step_series(config, contract: SeededVortexHorizonContract) -> list[int]:
    if contract.sampling_policy == SEEDED_SAMPLING_POLICY_INITIALIZATION_SURFACE:
        return [0]
    steps = list(range(0, contract.n_steps + 1, int(config.time.obs_stride)))
    if contract.n_steps not in steps:
        steps.append(int(contract.n_steps))
    return sorted(dict.fromkeys(int(step) for step in steps))


def _expected_seeded_provenance_subset(config, config_path: Path) -> dict[str, Any]:
    grid = grid_from_config(config.mesh)
    geometry = build_geometry(grid, config.geometry, config_path.parent)
    resolved_seeds = resolve_vortex_seeds(grid, geometry, config.physics.vortex_seeds)
    return {
        "seeds": {
            "initial_condition": "seeded_vortices",
            "vortex_seed_count": len(config.physics.vortex_seeds),
        },
        "determinism": {
            "reproducibility_scope": "same-stack deterministic",
        },
        "numeric_environment": {
            "real_dtype": "float64",
            "complex_dtype": "complex128",
        },
        "initialization": {
            "mode": "seeded_vortices",
            "configured_vortex_seeds": configured_seed_payloads(config.physics.vortex_seeds),
            "resolved_vortex_seeds": resolved_seed_payloads(resolved_seeds),
            "seed_resolution_policy": SEED_RESOLUTION_POLICY,
            "seed_rejection_taxonomy_version": SEED_REJECTION_TAXONOMY_VERSION,
        },
    }


def _evaluate_seeded_provenance(
    provenance_payload: dict[str, Any],
    *,
    case_id: str,
    case_class: str,
    config,
    config_path: Path,
) -> list[dict[str, Any]]:
    mismatches = _collect_subset_mismatches(
        _expected_seeded_provenance_subset(config, config_path),
        provenance_payload,
        case_id=case_id,
        case_class=case_class,
        artifact="provenance",
    )
    packages = provenance_payload.get("packages", {})
    for package_name in ("numpy", "scipy", "pydantic", "pyyaml", "jsonschema", "h5py", "typer"):
        if package_name not in packages:
            mismatches.append(
                _seeded_case_mismatch(
                    case_id=case_id,
                    case_class=case_class,
                    artifact="provenance",
                    path=f"packages.{package_name}",
                    expected="<present>",
                    observed="<missing>",
                    assessment="missing_value",
                )
            )
    return mismatches


def _evaluate_seeded_horizon_contract(
    tier2_payload: dict[str, Any],
    *,
    case_id: str,
    case_class: str,
    config,
    contract: SeededVortexHorizonContract,
) -> list[dict[str, Any]]:
    expected_steps = _expected_observed_step_series(config, contract)
    expected_horizon = {
        "case_class": case_class,
        "horizon_contract": {
            "n_steps": int(contract.n_steps),
            "sampling_policy": contract.sampling_policy,
            "observed_sample_count": len(expected_steps),
            "observed_step_series": expected_steps,
        },
    }
    mismatches = _collect_subset_mismatches(
        expected_horizon,
        tier2_payload,
        case_id=case_id,
        case_class=case_class,
        artifact="tier2",
    )
    if case_class == SEEDED_CASE_CLASS_INITIALIZATION_ONLY and tier2_payload.get("early_window_observables") is not None:
        mismatches.append(
            _seeded_case_mismatch(
                case_id=case_id,
                case_class=case_class,
                artifact="tier2",
                path="early_window_observables",
                expected=None,
                observed=tier2_payload.get("early_window_observables"),
                assessment="case_class_mismatch",
            )
        )
    if case_class == SEEDED_CASE_CLASS_SHORT_HORIZON and tier2_payload.get("early_window_observables") is None:
        mismatches.append(
            _seeded_case_mismatch(
                case_id=case_id,
                case_class=case_class,
                artifact="tier2",
                path="early_window_observables",
                expected="<present>",
                observed=None,
                assessment="missing_value",
            )
        )
    return mismatches


def _evaluate_seeded_config_surface(
    config_payload: dict[str, Any],
    *,
    case_id: str,
    case_class: str,
    contract: SeededVortexHorizonContract,
) -> list[dict[str, Any]]:
    return _collect_subset_mismatches(
        {"physics": {"initial_condition": "seeded_vortices"}, "time": {"n_steps": int(contract.n_steps)}},
        config_payload,
        case_id=case_id,
        case_class=case_class,
        artifact="config",
    )


def _evaluate_seeded_observed_winding(
    tier2_payload: dict[str, Any],
    *,
    case_id: str,
    case_class: str,
    config,
) -> list[dict[str, Any]]:
    configured = _configured_seeded_vortex_totals(config)
    expected = {
        "initialization_observables": {
            "local_winding_verification": {
                "initial_total_signed_winding": configured["configured_signed_winding"],
                "initial_total_abs_winding": configured["configured_abs_winding"],
            }
        }
    }
    return _collect_subset_mismatches(
        expected,
        tier2_payload,
        case_id=case_id,
        case_class=case_class,
        artifact="tier2",
    )


def _failed_seeded_case_record(
    *,
    case_id: str,
    case_kind: str,
    case_class: str,
    config_ref: str,
    validated_surface: str,
    mismatch_records: list[dict[str, Any]],
    run_dir: str | None = None,
    expected_stage: str | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "case_kind": case_kind,
        "case_class": case_class,
        "config_path": config_ref,
        "run_dir": run_dir,
        "expected_stage": expected_stage,
        "validated_surface": validated_surface,
        "status": "failed",
        "overall_pass": False,
        "mismatch_count": len(mismatch_records),
        "mismatch_records": mismatch_records,
        "notes": _seeded_case_note(mismatch_records, "case failed"),
    }


def _evaluate_seeded_success_case(
    spec: SeededVortexCanonicalCaseSpec | SeededVortexExerciseCaseSpec,
    *,
    case_kind: str,
    destination: Path,
    suite: SeededVortexExperimentSuite,
) -> dict[str, Any]:
    contract = suite.horizon_contracts[spec.case_class]
    case_dir = destination / case_kind / spec.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    case_class = str(spec.case_class)
    try:
        config = load_case_config(spec.config_path)
    except Exception as exc:
        mismatch_records = [
            _seeded_case_mismatch(
                case_id=spec.case_id,
                case_class=case_class,
                artifact="config",
                path="<load>",
                expected="seeded_vortex_success_case",
                observed=type(exc).__name__,
                assessment=str(exc),
            )
        ]
        return _failed_seeded_case_record(
            case_id=spec.case_id,
            case_kind=case_kind,
            case_class=case_class,
            config_ref=spec.config_ref,
            validated_surface=SEEDED_VORTEX_VALIDATED_SURFACES[case_class],
            mismatch_records=mismatch_records,
        )

    mismatch_records = _evaluate_seeded_config_surface(
        config.model_dump(mode="json"),
        case_id=spec.case_id,
        case_class=case_class,
        contract=contract,
    )

    try:
        staged_config = _stage_config(Path(spec.config_path), case_dir / "configs", case_dir / "case_runs")
        summary = run_simulation(staged_config)
        run_dir = Path(summary.run_dir)
        observed_summary, observed_final_observables, payload_for_hash = _extract_run_payload(run_dir)
        observed_payload_sha256 = _canonical_sha256(payload_for_hash)
        tier2_payload = _extract_seeded_tier2_payload(run_dir)
        provenance_payload = _read_json(run_dir / "provenance.json")
    except Exception as exc:
        mismatch_records.append(
            _seeded_case_mismatch(
                case_id=spec.case_id,
                case_class=case_class,
                artifact="run_case",
                path="<run>",
                expected="successful deterministic seeded case",
                observed=type(exc).__name__,
                assessment=str(exc),
            )
        )
        return _failed_seeded_case_record(
            case_id=spec.case_id,
            case_kind=case_kind,
            case_class=case_class,
            config_ref=spec.config_ref,
            validated_surface=SEEDED_VORTEX_VALIDATED_SURFACES[case_class],
            mismatch_records=mismatch_records,
        )

    try:
        _validate_payload_against_schema(
            provenance_payload,
            _seeded_vortex_provenance_schema_path(),
            label=f"seeded-vortex provenance for {spec.case_id}",
        )
    except Exception as exc:
        mismatch_records.append(
            _seeded_case_mismatch(
                case_id=spec.case_id,
                case_class=case_class,
                artifact="provenance",
                path="<schema>",
                expected="schema-valid provenance payload",
                observed=str(exc),
                assessment="schema_failure",
            )
        )

    try:
        _validate_payload_against_schema(
            tier2_payload,
            _seeded_vortex_tier2_schema_path(),
            label=f"seeded-vortex tier2 payload for {spec.case_id}",
        )
    except Exception as exc:
        mismatch_records.append(
            _seeded_case_mismatch(
                case_id=spec.case_id,
                case_class=case_class,
                artifact="tier2",
                path="<schema>",
                expected="schema-valid tier2 payload",
                observed=str(exc),
                assessment="schema_failure",
            )
        )

    mismatch_records.extend(
        _evaluate_seeded_provenance(
            provenance_payload,
            case_id=spec.case_id,
            case_class=case_class,
            config=config,
            config_path=Path(spec.config_path),
        )
    )
    mismatch_records.extend(
        _evaluate_seeded_horizon_contract(
            tier2_payload,
            case_id=spec.case_id,
            case_class=case_class,
            config=config,
            contract=contract,
        )
    )
    mismatch_records.extend(
        _evaluate_seeded_observed_winding(
            tier2_payload,
            case_id=spec.case_id,
            case_class=case_class,
            config=config,
        )
    )

    if case_kind == "canonical":
        mismatch_records.extend(
            _collect_subset_mismatches(
                spec.expected_summary,
                observed_summary,
                case_id=spec.case_id,
                case_class=case_class,
                artifact="summary",
            )
        )
        mismatch_records.extend(
            _collect_subset_mismatches(
                spec.expected_final_observables,
                observed_final_observables,
                case_id=spec.case_id,
                case_class=case_class,
                artifact="final_observables",
            )
        )
        if observed_payload_sha256 != spec.expected_payload_sha256:
            mismatch_records.append(
                _seeded_case_mismatch(
                    case_id=spec.case_id,
                    case_class=case_class,
                    artifact="canonical_reference",
                    path="payload_sha256",
                    expected=spec.expected_payload_sha256,
                    observed=observed_payload_sha256,
                    assessment="hash_mismatch",
                )
            )
        mismatch_records.extend(
            _collect_subset_mismatches(
                spec.expected_tier2,
                tier2_payload,
                case_id=spec.case_id,
                case_class=case_class,
                artifact="tier2",
            )
        )
    else:
        mismatch_records.extend(
            _collect_subset_mismatches(
                spec.expected_invariants,
                tier2_payload,
                case_id=spec.case_id,
                case_class=case_class,
                artifact="tier2",
            )
        )

    overall_pass = not mismatch_records
    return {
        "case_id": spec.case_id,
        "case_kind": case_kind,
        "case_class": case_class,
        "config_path": spec.config_ref,
        "run_dir": str(run_dir),
        "expected_stage": None,
        "validated_surface": SEEDED_VORTEX_VALIDATED_SURFACES[case_class],
        "status": "success" if overall_pass else "failed",
        "overall_pass": overall_pass,
        "mismatch_count": len(mismatch_records),
        "mismatch_records": mismatch_records,
        "payload_sha256": observed_payload_sha256,
        "notes": _seeded_case_note(
            mismatch_records,
            "matched deterministic same-stack seeded initialization / short-horizon expectations",
        ),
    }


def _evaluate_seeded_rejection_case(spec: SeededVortexRejectionCaseSpec) -> dict[str, Any]:
    case_class = "rejection_case"
    mismatch_records: list[dict[str, Any]] = []
    try:
        if spec.expected_stage == "config_validation":
            load_case_config(spec.config_path)
        else:
            run_simulation(spec.config_path)
        mismatch_records.append(
            _seeded_case_mismatch(
                case_id=spec.case_id,
                case_class=case_class,
                artifact="rejection",
                path="expected_stage",
                expected=spec.expected_stage,
                observed="success",
                assessment="unexpected_success",
            )
        )
    except SeedRejectionError as exc:
        observed_payload = exc.to_payload()
        try:
            _validate_payload_against_schema(
                observed_payload,
                _seeded_vortex_rejection_schema_path(),
                label=f"seeded-vortex rejection payload for {spec.case_id}",
            )
        except Exception as schema_exc:
            mismatch_records.append(
                _seeded_case_mismatch(
                    case_id=spec.case_id,
                    case_class=case_class,
                    artifact="rejection",
                    path="<schema>",
                    expected="schema-valid rejection payload",
                    observed=str(schema_exc),
                    assessment="schema_failure",
                )
            )
        mismatch_records.extend(
            _collect_subset_mismatches(
                spec.expected_rejection,
                observed_payload,
                case_id=spec.case_id,
                case_class=case_class,
                artifact="rejection",
            )
        )
    except Exception as exc:
        mismatch_records.append(
            _seeded_case_mismatch(
                case_id=spec.case_id,
                case_class=case_class,
                artifact="rejection",
                path="exception_type",
                expected="SeedRejectionError",
                observed=type(exc).__name__,
                assessment=str(exc),
            )
        )

    overall_pass = not mismatch_records
    return {
        "case_id": spec.case_id,
        "case_kind": "rejection",
        "case_class": case_class,
        "config_path": spec.config_ref,
        "run_dir": None,
        "expected_stage": spec.expected_stage,
        "validated_surface": SEEDED_VORTEX_VALIDATED_SURFACES["rejection_case"],
        "status": "success" if overall_pass else "failed",
        "overall_pass": overall_pass,
        "mismatch_count": len(mismatch_records),
        "mismatch_records": mismatch_records,
        "notes": _seeded_case_note(
            mismatch_records,
            "matched expected seeded-input rejection taxonomy on the same stack",
        ),
    }


def _seeded_suite_case_rows(
    records: list[dict[str, Any]],
    *,
    suite_id: str,
    claim_scope: str,
    validated_surfaces: list[str],
    non_claims: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    surfaces_text = ";".join(validated_surfaces)
    non_claims_text = ";".join(f"{key}={value}" for key, value in non_claims.items())
    for record in records:
        rows.append(
            {
                "suite_id": suite_id,
                "claim_scope": claim_scope,
                "validated_surfaces": surfaces_text,
                "non_claims": non_claims_text,
                "case_id": record["case_id"],
                "case_kind": record["case_kind"],
                "case_class": record["case_class"],
                "config_path": record["config_path"],
                "expected_stage": record["expected_stage"],
                "validated_surface": record["validated_surface"],
                "status": record["status"],
                "overall_pass": record["overall_pass"],
                "run_dir": record["run_dir"],
                "mismatch_count": record["mismatch_count"],
                "mismatch_records_json": json.dumps(record["mismatch_records"], sort_keys=True),
                "notes": record["notes"],
            }
        )
    return rows


def _seeded_suite_markdown(
    *,
    suite: SeededVortexExperimentSuite,
    records: list[dict[str, Any]],
    manifest_path: Path,
    validated_surfaces: list[str],
    non_claims: dict[str, str],
    case_class_counts: dict[str, dict[str, int]],
) -> str:
    lines = [
        "# Seeded-Vortex Experiment Pack Validation",
        "",
        f"- Suite ID: `{suite.suite_id}`",
        f"- Manifest: `{manifest_path}`",
        f"- Claim scope: {suite.claim_scope}",
        f"- Overall status: `{'success' if all(record['overall_pass'] for record in records) else 'failed'}`",
        "",
        "## Case Counts",
        "",
        f"- initialization_only: `{case_class_counts[SEEDED_CASE_CLASS_INITIALIZATION_ONLY]['passed']}/{case_class_counts[SEEDED_CASE_CLASS_INITIALIZATION_ONLY]['total']}` passed",
        f"- short_horizon: `{case_class_counts[SEEDED_CASE_CLASS_SHORT_HORIZON]['passed']}/{case_class_counts[SEEDED_CASE_CLASS_SHORT_HORIZON]['total']}` passed",
        f"- rejection_case: `{case_class_counts['rejection_case']['passed']}/{case_class_counts['rejection_case']['total']}` passed",
        "",
    ]
    for section_name, case_kind in (
        ("Canonical Cases", "canonical"),
        ("Exercise Cases", "exercise"),
        ("Rejection Cases", "rejection"),
    ):
        section_records = [record for record in records if record["case_kind"] == case_kind]
        lines.extend(
            [
                f"## {section_name}",
                "",
                "| case_id | case_class | status | mismatches | notes |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        if section_records:
            for record in section_records:
                lines.append(
                    "| {case_id} | {case_class} | {status} | {mismatch_count} | {notes} |".format(
                        case_id=record["case_id"],
                        case_class=record["case_class"],
                        status="pass" if record["overall_pass"] else "failed",
                        mismatch_count=record["mismatch_count"],
                        notes=record["notes"].replace("\n", " "),
                    )
                )
        else:
            lines.append("| n/a | n/a | n/a | 0 | no cases |")
        lines.append("")

    mismatch_records = [mismatch for record in records for mismatch in record["mismatch_records"]]
    lines.extend(
        [
            "## Interpretation Boundary",
            "",
            "Success in this suite establishes only deterministic same-stack seeded initialization / short-horizon expectation matching, plus seeded-input rejection-taxonomy matching, on the committed software stack.",
            "",
            "Validated Surfaces",
            "",
        ]
    )
    lines.extend([f"- `{surface}`" for surface in validated_surfaces])
    lines.extend(
        [
            "",
            "Non-Claims",
            "",
            f"- `equilibrium_preparation`: {non_claims['equilibrium_preparation']}",
            f"- `long_time_dynamics`: {non_claims['long_time_dynamics']}",
            f"- `stochastic_behavior`: {non_claims['stochastic_behavior']}",
            f"- `cross_stack_portability`: {non_claims['cross_stack_portability']}",
            "",
        ]
    )
    if mismatch_records:
        lines.extend(
            [
                "## Mismatch Records",
                "",
                "| case_id | case_class | artifact | path | assessment |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for mismatch in mismatch_records:
            lines.append(
                "| {case_id} | {case_class} | {artifact} | {path} | {assessment} |".format(
                    case_id=mismatch["case_id"],
                    case_class=mismatch["case_class"],
                    artifact=mismatch["artifact"],
                    path=mismatch["path"],
                    assessment=mismatch["assessment"],
                )
            )
        lines.append("")
    return "\n".join(lines)


def _ensure_seeded_suite_output_contract(payload: dict[str, Any], markdown: str) -> None:
    if not payload.get("suite_id"):
        raise ConfigError("seeded-vortex suite output is missing suite_id")
    if not payload.get("claim_scope"):
        raise ConfigError("seeded-vortex suite output is missing claim_scope")
    validated_surfaces = payload.get("validated_surfaces")
    if not isinstance(validated_surfaces, list) or not validated_surfaces:
        raise ConfigError("seeded-vortex suite output is missing validated_surfaces")
    if not isinstance(payload.get("case_class_counts"), dict):
        raise ConfigError("seeded-vortex suite output is missing case_class_counts")
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, dict):
        raise ConfigError("seeded-vortex suite output is missing non_claims")
    for key in SEEDED_VORTEX_REQUIRED_NON_CLAIMS:
        if key not in non_claims:
            raise ConfigError(f"seeded-vortex suite output is missing required non-claim '{key}'")
    if "## Interpretation Boundary" not in markdown:
        raise ConfigError("seeded-vortex markdown report is missing Interpretation Boundary section")
    for key in SEEDED_VORTEX_REQUIRED_NON_CLAIMS:
        if key not in markdown:
            raise ConfigError(f"seeded-vortex markdown report is missing non-claim '{key}'")


def run_seeded_vortex_validation_suite(
    manifest_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    manifest = Path(manifest_path).resolve()
    suite = load_seeded_vortex_experiment_suite(manifest)
    destination = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (repo_root() / "runs" / "seeded_vortex_validation" / manifest.stem / datetime.now().strftime("%Y%m%d-%H%M%S")).resolve()
    )
    destination.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for spec in suite.canonical_cases:
        records.append(_evaluate_seeded_success_case(spec, case_kind="canonical", destination=destination, suite=suite))
    for spec in suite.exercise_cases:
        records.append(_evaluate_seeded_success_case(spec, case_kind="exercise", destination=destination, suite=suite))
    for spec in suite.rejection_cases:
        records.append(_evaluate_seeded_rejection_case(spec))

    validated_surfaces = _seeded_validated_surfaces(suite)
    case_class_counts = _seeded_case_class_counts(records)
    mismatch_records = [mismatch for record in records for mismatch in record["mismatch_records"]]
    case_rows = _seeded_suite_case_rows(
        records,
        suite_id=suite.suite_id,
        claim_scope=suite.claim_scope,
        validated_surfaces=validated_surfaces,
        non_claims=SEEDED_VORTEX_REQUIRED_NON_CLAIMS,
    )
    overall_pass = bool(records) and all(record["overall_pass"] for record in records)

    results_json_path = destination / "seeded_vortex_validation.json"
    results_markdown_path = destination / "seeded_vortex_validation.md"
    case_table_csv_path = destination / "seeded_vortex_validation_cases.csv"
    payload = {
        "schema_version": suite.schema_version,
        "suite_id": suite.suite_id,
        "manifest_path": str(manifest),
        "claim_scope": suite.claim_scope,
        "validated_surfaces": validated_surfaces,
        "non_claims": dict(SEEDED_VORTEX_REQUIRED_NON_CLAIMS),
        "case_class_counts": case_class_counts,
        "case_count": len(records),
        "pass_count": sum(record["overall_pass"] for record in records),
        "records": records,
        "mismatch_records": mismatch_records,
        "overall_status": "success" if overall_pass else "failed",
    }
    markdown = _seeded_suite_markdown(
        suite=suite,
        records=records,
        manifest_path=manifest,
        validated_surfaces=validated_surfaces,
        non_claims=SEEDED_VORTEX_REQUIRED_NON_CLAIMS,
        case_class_counts=case_class_counts,
    )
    _ensure_seeded_suite_output_contract(payload, markdown)
    write_json(results_json_path, payload)
    write_csv(case_table_csv_path, case_rows)
    results_markdown_path.write_text(markdown, encoding="utf-8")
    return {
        "status": "success" if overall_pass else "failed",
        "manifest_path": str(manifest),
        "output_dir": str(destination),
        "results_json_path": str(results_json_path),
        "results_markdown_path": str(results_markdown_path),
        "case_table_csv_path": str(case_table_csv_path),
        "case_count": len(records),
        "pass_count": sum(record["overall_pass"] for record in records),
    }

