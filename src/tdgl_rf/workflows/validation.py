"""Deterministic phase-1 validation workflows and evidence generation."""

from __future__ import annotations

from copy import deepcopy
import csv
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import yaml

from tdgl_rf.config.loaders import load_case_config, load_raw_config, repo_root, write_expanded_config
from tdgl_rf.diagnostics.seeded_vortex import (
    SEEDED_CASE_CLASS_INITIALIZATION_ONLY,
    SEEDED_CASE_CLASS_SHORT_HORIZON,
    SEEDED_SAMPLING_POLICY_ALL_OBSERVABLE_SAMPLES,
    SEEDED_SAMPLING_POLICY_INITIALIZATION_SURFACE,
)
from tdgl_rf.exceptions import (
    ConfigError,
    SEED_REJECTION_TAXONOMY_VERSION,
    SeedRejectionError,
)
from tdgl_rf.geometry.masks import build_geometry, grid_from_config
from tdgl_rf.io.reports import write_csv, write_json
from tdgl_rf.solvers.seeded_vortices import (
    SEED_RESOLUTION_POLICY,
    configured_seed_payloads,
    resolve_vortex_seeds,
    resolved_seed_payloads,
)
from tdgl_rf.workflows.postprocess import summarize_campaign
from tdgl_rf.workflows.refinement import run_refinement_sanity
from tdgl_rf.workflows.run_case import run_simulation
from tdgl_rf.workflows.run_matrix import load_experiment_matrix, run_experiment_matrix


@dataclass(frozen=True)
class ReferenceRunSpec:
    reference_id: str
    kind: str
    config_ref: str
    config_path: str
    command: str
    expected_files: list[str]
    expected_summary: dict[str, Any]
    expected_final_observables: dict[str, Any]
    expected_payload_sha256: str
    selected_result_case_id: str | None = None
    expected_tier2_diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReferenceCheckSummary:
    status: str
    manifest_path: str
    output_dir: str
    results_json_path: str
    results_markdown_path: str
    reference_case_count: int
    passed_case_count: int
    failed_case_count: int


@dataclass(frozen=True)
class SeededVortexValidationSummary:
    status: str
    manifest_path: str
    output_dir: str
    results_json_path: str
    results_markdown_path: str
    case_table_csv_path: str
    case_count: int
    pass_count: int
    reference_check_json_path: str | None = None
    reference_check_markdown_path: str | None = None


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


@dataclass(frozen=True)
class ReproducibilityCheckSummary:
    status: str
    config_path: str
    output_dir: str
    comparison_json_path: str
    comparison_markdown_path: str
    exact_match: bool
    compared_metric_count: int


@dataclass(frozen=True)
class Phase1ValidationSummary:
    status: str
    matrix_path: str
    thresholds_path: str
    reference_manifest_path: str
    refinement_config_path: str
    output_dir: str
    validation_summary_csv_path: str
    validation_summary_json_path: str
    validation_report_path: str
    campaign_dir: str
    refinement_dir: str
    reference_output_dir: str
    reproducibility_output_dir: str
    campaign_case_count: int
    campaign_pass_count: int
    refinement_case_count: int
    refinement_pass_count: int
    reference_case_count: int
    reference_pass_count: int
    reproducibility_passed: bool


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


def _range_mismatch(expected: dict[str, Any], observed: Any, label: str) -> str | None:
    if observed is None or not isinstance(observed, (int, float)):
        return f"{label} expected bounded numeric value but observed {observed!r}"
    if "min" in expected and float(observed) < float(expected["min"]):
        return f"{label}={observed!r} fell below lower bound {expected['min']!r}"
    if "max" in expected and float(observed) > float(expected["max"]):
        return f"{label}={observed!r} exceeded upper bound {expected['max']!r}"
    return None


def _compare_expected_mapping(expected: dict[str, Any], observed: dict[str, Any], *, label: str) -> list[str]:
    mismatches: list[str] = []
    for key, expected_value in expected.items():
        observed_value = observed.get(key)
        if isinstance(expected_value, dict) and set(expected_value).issubset({"min", "max"}):
            mismatch = _range_mismatch(expected_value, observed_value, f"{label}.{key}")
            if mismatch is not None:
                mismatches.append(mismatch)
            continue
        if isinstance(expected_value, dict):
            if not isinstance(observed_value, dict):
                mismatches.append(f"{label}.{key} expected mapping observed {observed_value!r}")
                continue
            mismatches.extend(_compare_expected_mapping(expected_value, observed_value, label=f"{label}.{key}"))
            continue
        if observed_value != expected_value:
            mismatches.append(f"{label}.{key} expected {expected_value!r} observed {observed_value!r}")
    return mismatches


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
    return repo_root() / "configs" / "seeded_vortex_experiment_manifest.schema.json"


def _seeded_vortex_tier2_schema_path() -> Path:
    return repo_root() / "configs" / "seeded_vortex_tier2.schema.json"


def _seeded_vortex_rejection_schema_path() -> Path:
    return repo_root() / "configs" / "seeded_vortex_rejection.schema.json"


def _seeded_vortex_provenance_schema_path() -> Path:
    return repo_root() / "configs" / "tdgl_run_provenance.schema.json"


def _build_seeded_horizon_contract(payload: dict[str, Any]) -> SeededVortexHorizonContract:
    return SeededVortexHorizonContract(
        n_steps=int(payload["n_steps"]),
        sampling_policy=str(payload["sampling_policy"]),
    )


def _load_seeded_vortex_experiment_suite(manifest_path: str | Path) -> SeededVortexExperimentSuite:
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


def _row_lookup(matrix_path: Path) -> dict[int, dict[str, Any]]:
    return {row.row_index: row.values for row in load_experiment_matrix(matrix_path)}


def load_threshold_spec(thresholds_path: str | Path) -> dict[str, Any]:
    path = Path(thresholds_path).resolve()
    payload = _read_yaml(path)
    for section in ("campaign", "refinement", "reproducibility"):
        if section not in payload or not isinstance(payload[section], dict):
            raise ConfigError(f"threshold spec is missing '{section}' section: {path}")
    return payload


def load_reference_manifest(manifest_path: str | Path) -> list[ReferenceRunSpec]:
    path = Path(manifest_path).resolve()
    payload = _read_yaml(path)
    reference_runs = payload.get("reference_runs")
    if not isinstance(reference_runs, list) or not reference_runs:
        raise ConfigError(f"reference manifest must define a non-empty reference_runs list: {path}")

    seen_ids: set[str] = set()
    specs: list[ReferenceRunSpec] = []
    for index, item in enumerate(reference_runs, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"reference manifest row {index} must be a mapping")
        reference_id = str(item.get("reference_id", "")).strip()
        if not reference_id:
            raise ConfigError(f"reference manifest row {index} is missing reference_id")
        if reference_id in seen_ids:
            raise ConfigError(f"reference manifest contains duplicate reference_id '{reference_id}'")
        seen_ids.add(reference_id)

        kind = str(item.get("kind", "config")).strip()
        if kind not in {"config", "refinement_sanity"}:
            raise ConfigError(f"reference '{reference_id}' has unsupported kind '{kind}'")

        config_ref = str(item.get("config_path", "")).strip()
        if not config_ref:
            raise ConfigError(f"reference '{reference_id}' is missing config_path")
        config_path = _resolve_path(config_ref, source_dir=path.parent)
        if not config_path.exists():
            raise ConfigError(f"reference '{reference_id}' config_path does not exist: {config_ref}")

        command = str(item.get("command", "")).strip()
        if not command:
            raise ConfigError(f"reference '{reference_id}' is missing command")

        expected_files = item.get("expected_files")
        if not isinstance(expected_files, list) or not expected_files:
            raise ConfigError(f"reference '{reference_id}' must define expected_files")

        expected_summary = item.get("expected_summary") or {}
        expected_final_observables = item.get("expected_final_observables") or {}
        expected_tier2_diagnostics = item.get("expected_tier2_diagnostics") or {}
        if (
            not isinstance(expected_summary, dict)
            or not isinstance(expected_final_observables, dict)
            or not isinstance(expected_tier2_diagnostics, dict)
        ):
            raise ConfigError(f"reference '{reference_id}' expected summary payloads must be mappings")

        expected_payload_sha256 = str(item.get("expected_payload_sha256", "")).strip()
        if not expected_payload_sha256:
            raise ConfigError(f"reference '{reference_id}' is missing expected_payload_sha256")

        selected_result_case_id = item.get("selected_result_case_id")
        if kind == "refinement_sanity" and selected_result_case_id is not None:
            selected_result_case_id = str(selected_result_case_id).strip() or None

        specs.append(
            ReferenceRunSpec(
                reference_id=reference_id,
                kind=kind,
                config_ref=config_ref,
                config_path=str(config_path),
                command=command,
                expected_files=[str(entry) for entry in expected_files],
                expected_summary=expected_summary,
                expected_final_observables=expected_final_observables,
                expected_tier2_diagnostics=expected_tier2_diagnostics,
                expected_payload_sha256=expected_payload_sha256,
                selected_result_case_id=selected_result_case_id,
            )
        )
    return specs


def _extract_run_payload(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    summary_path = run_dir / "observables" / "summary.json"
    timeseries_path = run_dir / "observables" / "timeseries.csv"
    run_summary_path = run_dir / "diagnostics" / "run_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"missing observables summary: {summary_path}")
    if not timeseries_path.exists():
        raise FileNotFoundError(f"missing observables timeseries: {timeseries_path}")
    if not run_summary_path.exists():
        raise FileNotFoundError(f"missing diagnostic summary: {run_summary_path}")

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


def _extract_refinement_payload(output_dir: Path, *, selected_case_id: str | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    comparison_csv = output_dir / "comparison_table.csv"
    comparison_json = output_dir / "comparison_table.json"
    if not comparison_csv.exists():
        raise FileNotFoundError(f"missing refinement comparison CSV: {comparison_csv}")
    if not comparison_json.exists():
        raise FileNotFoundError(f"missing refinement comparison JSON: {comparison_json}")

    payload = _read_json(comparison_json)
    results = payload.get("results", [])
    if not isinstance(results, list) or not results:
        raise ConfigError(f"refinement comparison payload has no results: {comparison_json}")

    reference_case_id = str(payload.get("reference_case_id", ""))
    target_case_id = selected_case_id or reference_case_id
    if not target_case_id:
        raise ConfigError(f"refinement comparison payload is missing reference_case_id: {comparison_json}")

    selected_row = next((row for row in results if str(row.get("case_id")) == target_case_id), None)
    if selected_row is None:
        raise ConfigError(f"refinement comparison payload has no case_id '{target_case_id}'")

    observed_summary = {
        "reference_case_id": reference_case_id,
        "selected_case_id": target_case_id,
        "comparison_count": len(results),
        "final_mean_abs2": selected_row.get("final_mean_abs2"),
        "final_charge_residual_inf": selected_row.get("final_charge_residual_inf"),
        "final_delta_f_over_f0": selected_row.get("final_delta_f_over_f0"),
        "final_qinv": selected_row.get("final_qinv"),
        "delta_mean_abs2_vs_reference": selected_row.get("delta_mean_abs2_vs_reference"),
        "delta_charge_residual_inf_vs_reference": selected_row.get("delta_charge_residual_inf_vs_reference"),
        "delta_delta_f_over_f0_vs_reference": selected_row.get("delta_delta_f_over_f0_vs_reference"),
        "delta_qinv_vs_reference": selected_row.get("delta_qinv_vs_reference"),
    }
    payload_for_hash = {
        "reference_case_id": reference_case_id,
        "selected_case_id": target_case_id,
        "mesh_levels": payload.get("mesh_levels", []),
        "dt_levels": payload.get("dt_levels", []),
        "selected_result": observed_summary,
    }
    return observed_summary, {}, payload_for_hash


def _extract_seeded_tier2_payload(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "diagnostics" / "seeded_vortex_tier2.json"
    if not path.exists():
        raise FileNotFoundError(f"missing seeded-vortex Tier-2 diagnostics: {path}")
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ConfigError(f"seeded-vortex Tier-2 payload must be a mapping: {path}")
    return payload


def _reference_markdown(records: list[dict[str, Any]], manifest_path: Path) -> str:
    intro = [
        "# Frozen Reference Check",
        "",
        f"Manifest: `{manifest_path}`",
        "",
        "This report regenerates the committed canonical deterministic reference cases and compares compact payload hashes plus selected summary values.",
        "",
        "| reference_id | kind | files_complete | hash_match | status | notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    rows: list[str] = []
    for record in records:
        rows.append(
            "| {reference_id} | {kind} | {files_complete} | {hash_match} | {status} | {notes} |".format(
                reference_id=record["reference_id"],
                kind=record["kind"],
                files_complete="yes" if record["files_complete"] else "no",
                hash_match="yes" if record["payload_sha256_match"] else "no",
                status=record["status"],
                notes=record["notes"].replace("\n", " "),
            )
        )
    return "\n".join(intro + rows + [""])


def run_reference_check(manifest_path: str | Path, *, output_dir: str | Path | None = None) -> ReferenceCheckSummary:
    manifest = Path(manifest_path).resolve()
    specs = load_reference_manifest(manifest)
    destination = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (repo_root() / "runs" / "reference_checks" / manifest.stem / datetime.now().strftime("%Y%m%d-%H%M%S")).resolve()
    )
    destination.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for spec in specs:
        spec_dir = destination / spec.reference_id
        spec_dir.mkdir(parents=True, exist_ok=True)
        notes: list[str] = []
        observed_summary: dict[str, Any] = {}
        observed_final_observables: dict[str, Any] = {}
        payload_sha256 = ""
        files_complete = False
        payload_sha256_match = False
        workflow_root = ""
        generated_from = ""
        try:
            if spec.kind == "config":
                staged_config = _stage_config(Path(spec.config_path), spec_dir / "configs", spec_dir / "case_runs")
                generated_from = str(staged_config)
                summary = run_simulation(staged_config)
                workflow_root = str(Path(summary.run_dir))
                observed_summary, observed_final_observables, payload_for_hash = _extract_run_payload(Path(summary.run_dir))
            else:
                generated_from = spec.config_path
                refinement = run_refinement_sanity(Path(spec.config_path), output_dir=spec_dir / "refinement")
                workflow_root = str(refinement.output_dir)
                observed_summary, observed_final_observables, payload_for_hash = _extract_refinement_payload(
                    Path(refinement.output_dir),
                    selected_case_id=spec.selected_result_case_id,
                )
            payload_sha256 = _canonical_sha256(payload_for_hash)
            files_present = {entry: (Path(workflow_root) / entry).exists() for entry in spec.expected_files}
            files_complete = all(files_present.values())
            if not files_complete:
                missing = [entry for entry, present in files_present.items() if not present]
                notes.append(f"missing expected files: {', '.join(missing)}")
            notes.extend(_compare_expected_mapping(spec.expected_summary, observed_summary, label="summary"))
            notes.extend(
                _compare_expected_mapping(
                    spec.expected_final_observables,
                    observed_final_observables,
                    label="final_observables",
                )
            )
            payload_sha256_match = payload_sha256 == spec.expected_payload_sha256
            if not payload_sha256_match:
                notes.append(f"payload sha256 expected {spec.expected_payload_sha256} observed {payload_sha256}")
            status = "success" if files_complete and not notes else "failed"
        except Exception as exc:
            status = "failed"
            notes.append(str(exc))
            files_present = {entry: False for entry in spec.expected_files}

        records.append(
            {
                "reference_id": spec.reference_id,
                "kind": spec.kind,
                "config_path": spec.config_ref,
                "command": spec.command,
                "generated_from": generated_from,
                "workflow_root": workflow_root,
                "files_complete": files_complete,
                "files_present": files_present,
                "expected_payload_sha256": spec.expected_payload_sha256,
                "payload_sha256": payload_sha256,
                "payload_sha256_match": payload_sha256_match,
                "status": status,
                "notes": "; ".join(notes) if notes else "matched manifest",
                "observed_summary": observed_summary,
                "observed_final_observables": observed_final_observables,
            }
        )

    results_json_path = destination / "reference_check.json"
    results_markdown_path = destination / "reference_check.md"
    write_json(
        results_json_path,
        {
            "manifest_path": str(manifest),
            "reference_case_count": len(records),
            "passed_case_count": sum(record["status"] == "success" for record in records),
            "failed_case_count": sum(record["status"] != "success" for record in records),
            "records": records,
        },
    )
    results_markdown_path.write_text(_reference_markdown(records, manifest), encoding="utf-8")

    passed = sum(record["status"] == "success" for record in records)
    failed = len(records) - passed
    return ReferenceCheckSummary(
        status="success" if failed == 0 else "failed",
        manifest_path=str(manifest),
        output_dir=str(destination),
        results_json_path=str(results_json_path),
        results_markdown_path=str(results_markdown_path),
        reference_case_count=len(records),
        passed_case_count=passed,
        failed_case_count=failed,
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


def _seeded_vortex_validation_markdown(records: list[dict[str, Any]], manifest_path: Path, reference_summary: ReferenceCheckSummary) -> str:
    lines = [
        "# Seeded-Vortex Validation Note",
        "",
        "This note records the narrow deterministic seeded-vortex initialization hook. It checks canonical ansatz cases for expected step-0 winding content, Tier-2 short-horizon diagnostics, and frozen short-run outputs.",
        "",
        f"- Manifest: `{manifest_path}`",
        f"- Frozen reference check status: `{reference_summary.status}`",
        f"- Passing canonical cases: `{sum(record['overall_pass'] for record in records)}/{len(records)}`",
        "",
        "| reference_id | case_id | configured abs/signed | observed abs/signed | Tier-2 | reference check | assessment | notes |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            "| {reference_id} | {case_id} | {configured_abs}/{configured_signed} | {observed_abs}/{observed_signed} | {tier2_status} | {reference_status} | {assessment} | {notes} |".format(
                reference_id=record["reference_id"],
                case_id=record["case_id"],
                configured_abs=record["configured_abs_winding"],
                configured_signed=record["configured_signed_winding"],
                observed_abs=record["observed_abs_winding"],
                observed_signed=record["observed_signed_winding"],
                tier2_status="pass" if record["tier2_overall_pass"] else "flagged",
                reference_status=record["reference_check_status"],
                assessment="pass" if record["overall_pass"] else "flagged",
                notes=record["notes"].replace("\n", " "),
            )
        )
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- These seeded states are deterministic initialization ansatze, not relaxed equilibrium vortex solutions.",
            "- The Tier-2 diagnostics are limited to local winding verification, core-amplitude detection, and short-horizon finite/stable behavior.",
            "- This hook does not establish long-horizon dynamics, asymptotic convergence, PETSc parity, stochastic robustness, or broad physical validity.",
            "- Supported placements are limited to seeds that lie strictly inside fully active plaquettes so the existing gauge-invariant vortex map remains interpretable at initialization.",
            "",
        ]
    )
    return "\n".join(lines)


def run_seeded_vortex_validation(
    manifest_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> SeededVortexValidationSummary:
    manifest = Path(manifest_path).resolve()
    raw_manifest = _read_yaml(manifest)
    if "reference_runs" not in raw_manifest:
        from tdgl_rf.workflows.seeded_vortex_suite import run_seeded_vortex_validation_suite

        suite_summary = run_seeded_vortex_validation_suite(manifest, output_dir=output_dir)
        return SeededVortexValidationSummary(
            status=str(suite_summary["status"]),
            manifest_path=str(suite_summary["manifest_path"]),
            output_dir=str(suite_summary["output_dir"]),
            results_json_path=str(suite_summary["results_json_path"]),
            results_markdown_path=str(suite_summary["results_markdown_path"]),
            case_table_csv_path=str(suite_summary["case_table_csv_path"]),
            case_count=int(suite_summary["case_count"]),
            pass_count=int(suite_summary["pass_count"]),
        )

    specs = load_reference_manifest(manifest)
    destination = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (repo_root() / "runs" / "seeded_vortex_validation" / manifest.stem / datetime.now().strftime("%Y%m%d-%H%M%S")).resolve()
    )
    destination.mkdir(parents=True, exist_ok=True)

    reference_summary = run_reference_check(manifest, output_dir=destination / "reference_check")
    reference_payload = _read_json(Path(reference_summary.results_json_path))
    reference_records = {
        str(record["reference_id"]): record
        for record in reference_payload.get("records", [])
        if isinstance(record, dict) and record.get("reference_id") is not None
    }

    records: list[dict[str, Any]] = []
    for spec in specs:
        notes: list[str] = []
        config = load_case_config(spec.config_path)
        if config.physics.initial_condition != "seeded_vortices":
            raise ConfigError(
                f"seeded-vortex validation manifest requires physics.initial_condition == 'seeded_vortices'; "
                f"{spec.reference_id} used {config.physics.initial_condition!r}"
            )

        configured = _configured_seeded_vortex_totals(config)
        reference_record = reference_records.get(spec.reference_id, {})
        reference_status = str(reference_record.get("status", "missing"))
        if reference_status != "success":
            notes.append(f"reference check status was {reference_status}")
        workflow_root = reference_record.get("workflow_root")
        if not workflow_root:
            notes.append("reference check record was missing workflow_root")
            tier2_payload = {}
        else:
            try:
                tier2_payload = _extract_seeded_tier2_payload(Path(str(workflow_root)))
            except Exception as exc:
                tier2_payload = {}
                notes.append(str(exc))

        host_series = tier2_payload.get("local_winding_verification", {}).get("host_winding_series", [])
        observed = {
            "observed_positive_winding": int(sum(max(int(value), 0) for value in host_series)),
            "observed_negative_winding": int(sum(max(-int(value), 0) for value in host_series)),
            "observed_signed_winding": int(tier2_payload.get("local_winding_verification", {}).get("initial_total_signed_winding", 0)),
            "observed_abs_winding": int(tier2_payload.get("local_winding_verification", {}).get("initial_total_abs_winding", 0)),
        }
        if configured["configured_abs_winding"] != observed["observed_abs_winding"]:
            notes.append(f"configured abs winding {configured['configured_abs_winding']} observed {observed['observed_abs_winding']}")
        if configured["configured_signed_winding"] != observed["observed_signed_winding"]:
            notes.append(f"configured signed winding {configured['configured_signed_winding']} observed {observed['observed_signed_winding']}")
        tier2_mismatches = _compare_expected_mapping(spec.expected_tier2_diagnostics, tier2_payload, label="tier2")
        notes.extend(tier2_mismatches)
        tier2_overall_pass = bool(tier2_payload.get("tier2_overall_pass"))
        if tier2_payload and not tier2_overall_pass:
            notes.append("Tier-2 diagnostics reported tier2_overall_pass=false")

        records.append(
            {
                "reference_id": spec.reference_id,
                "case_id": config.metadata.case_id,
                **configured,
                **observed,
                "reference_check_status": reference_status,
                "reference_check_notes": str(reference_record.get("notes", "")),
                "tier2_overall_pass": tier2_overall_pass,
                "tier2_expected_defined": bool(spec.expected_tier2_diagnostics),
                "tier2_diagnostics": tier2_payload,
                "overall_pass": reference_status == "success" and tier2_overall_pass and not notes,
                "notes": "; ".join(notes) if notes else "matched configured seeded winding, Tier-2 diagnostics, and frozen reference outputs",
            }
        )

    results_json_path = destination / "seeded_vortex_validation.json"
    results_markdown_path = destination / "seeded_vortex_validation.md"
    case_table_csv_path = destination / "seeded_vortex_validation_cases.csv"
    pass_count = sum(record["overall_pass"] for record in records)
    write_csv(case_table_csv_path, records)
    write_json(
        results_json_path,
        {
            "manifest_path": str(manifest),
            "reference_check": {
                "status": reference_summary.status,
                "results_json_path": reference_summary.results_json_path,
                "results_markdown_path": reference_summary.results_markdown_path,
            },
            "case_count": len(records),
            "pass_count": pass_count,
            "records": records,
            "overall_status": "success" if pass_count == len(records) and reference_summary.status == "success" else "failed",
        },
    )
    results_markdown_path.write_text(
        _seeded_vortex_validation_markdown(records, manifest, reference_summary),
        encoding="utf-8",
    )
    return SeededVortexValidationSummary(
        status="success" if pass_count == len(records) and reference_summary.status == "success" else "failed",
        manifest_path=str(manifest),
        output_dir=str(destination),
        results_json_path=str(results_json_path),
        results_markdown_path=str(results_markdown_path),
        case_table_csv_path=str(case_table_csv_path),
        reference_check_json_path=reference_summary.results_json_path,
        reference_check_markdown_path=reference_summary.results_markdown_path,
        case_count=len(records),
        pass_count=pass_count,
    )


def _metric_comparison_rows(
    first: dict[str, Any],
    second: dict[str, Any],
    tolerances: dict[str, Any],
    *,
    label: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric, tolerance_value in tolerances.items():
        tolerance = float(tolerance_value)
        observed_first = first.get(metric)
        observed_second = second.get(metric)
        abs_delta: float | None
        passes = False
        if isinstance(observed_first, (int, float)) and isinstance(observed_second, (int, float)):
            abs_delta = abs(float(observed_first) - float(observed_second))
            passes = abs_delta <= tolerance
        else:
            abs_delta = None
        rows.append(
            {
                "label": label,
                "metric": metric,
                "first_value": observed_first,
                "second_value": observed_second,
                "tolerance": tolerance,
                "abs_delta": abs_delta,
                "pass": passes,
            }
        )
    return rows


def _reproducibility_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Deterministic Reproducibility Check",
        "",
        f"Config: `{payload['config_path']}`",
        "",
        f"Overall status: `{payload['status']}`",
        f"Payload hash match: `{'yes' if payload['payload_hash_match'] else 'no'}`",
        "",
        "| label | metric | first_value | second_value | tolerance | abs_delta | pass |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["comparison_rows"]:
        abs_delta = "n/a" if row["abs_delta"] is None else f"{float(row['abs_delta']):.12g}"
        lines.append(
            "| {label} | {metric} | {first_value} | {second_value} | {tolerance} | {abs_delta} | {passed} |".format(
                label=row["label"],
                metric=row["metric"],
                first_value=row["first_value"],
                second_value=row["second_value"],
                tolerance=row["tolerance"],
                abs_delta=abs_delta,
                passed="yes" if row["pass"] else "no",
            )
        )
    lines.extend(["", payload["notes"], ""])
    return "\n".join(lines)


def run_reproducibility_check(
    config_path: str | Path,
    *,
    tolerances_path: str | Path,
    output_dir: str | Path | None = None,
) -> ReproducibilityCheckSummary:
    resolved_config = Path(config_path).resolve()
    thresholds = load_threshold_spec(tolerances_path)
    reproducibility = thresholds["reproducibility"]
    summary_tolerances = reproducibility.get("summary_metric_tolerances", {})
    final_tolerances = reproducibility.get("final_observable_tolerances", {})
    require_payload_hash_match = bool(reproducibility.get("require_payload_hash_match", False))

    destination = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (repo_root() / "runs" / "reproducibility" / resolved_config.stem / datetime.now().strftime("%Y%m%d-%H%M%S")).resolve()
    )
    destination.mkdir(parents=True, exist_ok=True)

    staged_one = _stage_config(resolved_config, destination / "configs" / "first", destination / "case_runs" / "first")
    staged_two = _stage_config(resolved_config, destination / "configs" / "second", destination / "case_runs" / "second")
    first_summary = run_simulation(staged_one)
    second_summary = run_simulation(staged_two)

    first_summary_metrics, first_final, first_hash_payload = _extract_run_payload(Path(first_summary.run_dir))
    second_summary_metrics, second_final, second_hash_payload = _extract_run_payload(Path(second_summary.run_dir))
    comparison_rows = _metric_comparison_rows(first_summary_metrics, second_summary_metrics, summary_tolerances, label="summary")
    comparison_rows.extend(_metric_comparison_rows(first_final, second_final, final_tolerances, label="final_observables"))

    first_payload_sha256 = _canonical_sha256(first_hash_payload)
    second_payload_sha256 = _canonical_sha256(second_hash_payload)
    payload_hash_match = first_payload_sha256 == second_payload_sha256
    exact_match = (
        first_summary.status == second_summary.status
        and all(row["pass"] for row in comparison_rows)
        and (payload_hash_match if require_payload_hash_match else True)
    )

    notes = (
        "Deterministic reproducibility is defined here as identical success status and identical compact observable payloads on the same local software stack."
        if exact_match
        else "Deterministic reproducibility failed under the committed tolerances."
    )
    payload = {
        "status": "success" if exact_match else "failed",
        "config_path": str(resolved_config),
        "first_run_dir": first_summary.run_dir,
        "second_run_dir": second_summary.run_dir,
        "first_status": first_summary.status,
        "second_status": second_summary.status,
        "first_payload_sha256": first_payload_sha256,
        "second_payload_sha256": second_payload_sha256,
        "payload_hash_match": payload_hash_match,
        "comparison_rows": comparison_rows,
        "notes": notes,
    }
    comparison_json_path = destination / "reproducibility_check.json"
    comparison_markdown_path = destination / "reproducibility_check.md"
    write_json(comparison_json_path, payload)
    comparison_markdown_path.write_text(_reproducibility_markdown(payload), encoding="utf-8")

    return ReproducibilityCheckSummary(
        status=payload["status"],
        config_path=str(resolved_config),
        output_dir=str(destination),
        comparison_json_path=str(comparison_json_path),
        comparison_markdown_path=str(comparison_markdown_path),
        exact_match=exact_match,
        compared_metric_count=len(comparison_rows),
    )


def evaluate_campaign_results(
    campaign_dir: str | Path,
    *,
    matrix_path: str | Path,
    thresholds_path: str | Path,
) -> dict[str, Any]:
    campaign_path = Path(campaign_dir).resolve()
    resolved_matrix_path = Path(matrix_path).resolve()
    thresholds = load_threshold_spec(thresholds_path)["campaign"]
    state = _read_json(campaign_path / "campaign_state.json")
    matrix_lookup = _row_lookup(resolved_matrix_path)

    charge_limit = float(thresholds.get("max_charge_residual_inf", math.inf))
    max_vortex_count = int(thresholds.get("max_vortex_count", 0))
    required_case_status = str(thresholds.get("required_case_status", "success"))
    required_campaign_status = str(thresholds.get("required_campaign_status", "success"))

    records: list[dict[str, Any]] = []
    rows = list(state.get("rows", []))
    for row_payload in rows:
        row_index = int(row_payload["row_index"])
        matrix_values = matrix_lookup.get(row_index)
        base_record = {
            "row_index": row_index,
            "case_id": str(row_payload.get("case_id")),
            "campaign_row_status": str(row_payload.get("status")),
            "campaign_status_pass": str(row_payload.get("status")) == required_case_status,
            "files_complete": False,
            "charge_residual_limit": charge_limit,
            "max_vortex_count_limit": max_vortex_count,
            "charge_residual_pass": False,
            "vortex_pass": False,
            "overall_pass": False,
            "classification": "flagged",
            "notes": "",
            "run_dir": str(row_payload.get("run_dir") or ""),
            "geometry_family": None,
            "a_rf": None,
            "omega": None,
            "nx": None,
            "ny": None,
            "dt": None,
            "final_mean_abs2": None,
            "final_charge_residual_inf": None,
            "final_delta_f_over_f0": None,
            "final_qinv": None,
            "max_vortex_count": None,
        }
        if matrix_values is None:
            base_record["notes"] = "row index missing from source matrix"
            records.append(base_record)
            continue

        for key in ("geometry_family", "a_rf", "omega", "nx", "ny", "dt"):
            base_record[key] = matrix_values.get(key)

        if base_record["campaign_row_status"] != required_case_status:
            base_record["notes"] = f"campaign row status was {base_record['campaign_row_status']!r}"
            records.append(base_record)
            continue

        run_dir_value = row_payload.get("run_dir")
        if not run_dir_value:
            base_record["notes"] = "successful row is missing run_dir"
            records.append(base_record)
            continue

        try:
            summary_metrics, final_observables, _ = _extract_run_payload(Path(run_dir_value))
        except Exception as exc:
            base_record["notes"] = f"partial outputs: {exc}"
            records.append(base_record)
            continue

        charge_residual = summary_metrics.get("final_charge_residual_inf")
        vortex_count = summary_metrics.get("max_vortex_count")
        charge_pass = isinstance(charge_residual, (int, float)) and math.isfinite(float(charge_residual)) and float(charge_residual) <= charge_limit
        vortex_pass = isinstance(vortex_count, (int, float)) and int(vortex_count) <= max_vortex_count
        base_record.update(
            {
                "files_complete": True,
                "charge_residual_pass": charge_pass,
                "vortex_pass": vortex_pass,
                "final_mean_abs2": summary_metrics.get("final_mean_abs2"),
                "final_charge_residual_inf": charge_residual,
                "max_vortex_count": vortex_count,
                "final_delta_f_over_f0": final_observables.get("delta_f_over_f0"),
                "final_qinv": final_observables.get("qinv"),
                "overall_pass": charge_pass and vortex_pass,
                "classification": "acceptable" if charge_pass and vortex_pass else "flagged",
                "notes": "passed campaign thresholds" if charge_pass and vortex_pass else "failed one or more campaign thresholds",
            }
        )
        records.append(base_record)

    campaign_status = str(state.get("summary", {}).get("status"))
    campaign_status_pass = campaign_status == required_campaign_status
    overall_pass = campaign_status_pass and bool(records) and all(record["overall_pass"] for record in records)
    return {
        "campaign_dir": str(campaign_path),
        "matrix_path": str(resolved_matrix_path),
        "campaign_status": campaign_status,
        "campaign_status_pass": campaign_status_pass,
        "required_campaign_status": required_campaign_status,
        "records": records,
        "case_count": len(records),
        "pass_count": sum(record["overall_pass"] for record in records),
        "overall_pass": overall_pass,
    }


def evaluate_refinement_results(
    refinement_dir: str | Path,
    *,
    thresholds_path: str | Path,
) -> dict[str, Any]:
    refinement_path = Path(refinement_dir).resolve()
    thresholds = load_threshold_spec(thresholds_path)["refinement"]
    payload = _read_json(refinement_path / "comparison_table.json")
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ConfigError(f"refinement comparison payload is malformed: {refinement_path / 'comparison_table.json'}")

    records: list[dict[str, Any]] = []
    for row in results:
        mean_limit = float(thresholds.get("delta_mean_abs2_max", math.inf))
        charge_limit = float(thresholds.get("delta_charge_residual_inf_max", math.inf))
        delta_f_limit = float(thresholds.get("delta_delta_f_over_f0_max", math.inf))
        qinv_limit = float(thresholds.get("delta_qinv_max", math.inf))

        mean_delta = row.get("delta_mean_abs2_vs_reference")
        charge_delta = row.get("delta_charge_residual_inf_vs_reference")
        delta_f_delta = row.get("delta_delta_f_over_f0_vs_reference")
        qinv_delta = row.get("delta_qinv_vs_reference")
        record = {
            "case_id": row.get("case_id"),
            "mesh_level": row.get("mesh_level"),
            "dt": row.get("dt"),
            "delta_mean_abs2_vs_reference": mean_delta,
            "delta_charge_residual_inf_vs_reference": charge_delta,
            "delta_delta_f_over_f0_vs_reference": delta_f_delta,
            "delta_qinv_vs_reference": qinv_delta,
            "delta_mean_abs2_limit": mean_limit,
            "delta_charge_residual_inf_limit": charge_limit,
            "delta_delta_f_over_f0_limit": delta_f_limit,
            "delta_qinv_limit": qinv_limit,
            "delta_mean_abs2_pass": isinstance(mean_delta, (int, float)) and float(mean_delta) <= mean_limit,
            "delta_charge_residual_inf_pass": isinstance(charge_delta, (int, float)) and float(charge_delta) <= charge_limit,
            "delta_delta_f_over_f0_pass": isinstance(delta_f_delta, (int, float)) and float(delta_f_delta) <= delta_f_limit,
            "delta_qinv_pass": isinstance(qinv_delta, (int, float)) and float(qinv_delta) <= qinv_limit,
        }
        record["overall_pass"] = all(
            record[key]
            for key in (
                "delta_mean_abs2_pass",
                "delta_charge_residual_inf_pass",
                "delta_delta_f_over_f0_pass",
                "delta_qinv_pass",
            )
        )
        record["notes"] = "within refinement drift limits" if record["overall_pass"] else "exceeded one or more refinement drift limits"
        records.append(record)

    return {
        "refinement_dir": str(refinement_path),
        "reference_case_id": payload.get("reference_case_id"),
        "records": records,
        "case_count": len(records),
        "pass_count": sum(record["overall_pass"] for record in records),
        "overall_pass": bool(records) and all(record["overall_pass"] for record in records),
    }


def _validation_markdown(
    *,
    campaign: dict[str, Any],
    refinement: dict[str, Any],
    reference: dict[str, Any],
    reproducibility: dict[str, Any],
    thresholds_path: Path,
    manifest_path: Path,
) -> str:
    status = "PASS" if all((campaign["overall_pass"], refinement["overall_pass"], reference["overall_pass"], reproducibility["overall_pass"])) else "FLAGGED"
    lines = [
        "# Phase-1 Validation Report",
        "",
        "This report characterizes the deterministic phase-1 TDGL-RF baseline with conservative numerical gates. It is a regression-quality validation surface, not a publication-grade physics certification.",
        "",
        "## Overall Status",
        "",
        f"- Overall: `{status}`",
        f"- Campaign: `{campaign['pass_count']}/{campaign['case_count']}` acceptable cases, campaign state `{campaign['campaign_status']}`",
        f"- Refinement sanity: `{refinement['pass_count']}/{refinement['case_count']}` rows within drift limits",
        f"- Frozen references: `{reference['pass_count']}/{reference['case_count']}` matched",
        f"- Deterministic reproducibility: `{'pass' if reproducibility['overall_pass'] else 'fail'}`",
        f"- Threshold spec: `{thresholds_path}`",
        f"- Reference manifest: `{manifest_path}`",
        "",
        "## Campaign Cases",
        "",
        "| case_id | geometry | mesh | dt | a_rf | omega | charge_residual_inf | max_vortex_count | status | assessment |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    if campaign["records"]:
        for row in campaign["records"]:
            mesh = "n/a" if row["nx"] is None or row["ny"] is None else f"{row['nx']}x{row['ny']}"
            charge = "n/a" if row["final_charge_residual_inf"] is None else f"{float(row['final_charge_residual_inf']):.6f}"
            vortex = "n/a" if row["max_vortex_count"] is None else str(int(row["max_vortex_count"]))
            lines.append(
                "| {case_id} | {geometry} | {mesh} | {dt} | {a_rf} | {omega} | {charge} | {vortex} | {status} | {assessment} |".format(
                    case_id=row["case_id"],
                    geometry=row["geometry_family"] or "n/a",
                    mesh=mesh,
                    dt="n/a" if row["dt"] is None else f"{float(row['dt']):.4f}",
                    a_rf="n/a" if row["a_rf"] is None else f"{float(row['a_rf']):.3f}",
                    omega="n/a" if row["omega"] is None else f"{float(row['omega']):.3f}",
                    charge=charge,
                    vortex=vortex,
                    status=row["campaign_row_status"],
                    assessment=row["classification"],
                )
            )
    else:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no rows |")

    lines.extend(
        [
            "",
            "## Refinement Sanity",
            "",
            "| case_id | mesh | dt | d(mean_abs2) | d(charge_residual) | d(delta_f_over_f0) | d(qinv) | assessment |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    if refinement["records"]:
        for row in refinement["records"]:
            lines.append(
                "| {case_id} | {mesh} | {dt:.4f} | {dm:.6f} | {dc:.6f} | {df:.6f} | {dq:.6f} | {assessment} |".format(
                    case_id=row["case_id"],
                    mesh=row["mesh_level"],
                    dt=float(row["dt"]),
                    dm=float(row["delta_mean_abs2_vs_reference"]),
                    dc=float(row["delta_charge_residual_inf_vs_reference"]),
                    df=float(row["delta_delta_f_over_f0_vs_reference"]),
                    dq=float(row["delta_qinv_vs_reference"]),
                    assessment="acceptable" if row["overall_pass"] else "flagged",
                )
            )
    else:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | no rows |")

    lines.extend(
        [
            "",
            "## Frozen References",
            "",
            "| reference_id | kind | hash_match | status | notes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if reference["records"]:
        for row in reference["records"]:
            lines.append(
                "| {reference_id} | {kind} | {hash_match} | {status} | {notes} |".format(
                    reference_id=row["reference_id"],
                    kind=row["kind"],
                    hash_match="yes" if row["payload_sha256_match"] else "no",
                    status=row["status"],
                    notes=row["notes"].replace("\n", " "),
                )
            )
    else:
        lines.append("| n/a | n/a | n/a | no rows | no rows |")

    lines.extend(
        [
            "",
            "## Deterministic Reproducibility",
            "",
            f"- Status: `{'pass' if reproducibility['overall_pass'] else 'fail'}`",
            f"- Payload hash match: `{'yes' if reproducibility['payload_hash_match'] else 'no'}`",
            f"- Notes: {reproducibility['notes']}",
            "",
            "## Interpretation",
            "",
        ]
    )
    if status == "PASS":
        lines.append(
            "The deterministic phase-1 runtime is characterized here as a stable local baseline across the committed validation matrix, the refinement sanity harness, the frozen reference cases, and a same-stack reproducibility check."
        )
    else:
        lines.append(
            "One or more conservative quality gates were flagged. The baseline remains useful for controlled debugging, but proposal-facing claims should be limited to the specific passing surfaces recorded above."
        )
    lines.extend(
        [
            "",
            "## Scope Limits",
            "",
            "- These checks do not establish asymptotic convergence, stochastic robustness, PETSc parity, or publication-grade physics validation.",
            "- The reproducibility statement applies to the same local deterministic software stack used for this report.",
            "",
        ]
    )
    return "\n".join(lines)


def _reference_overview(reference_summary: ReferenceCheckSummary) -> dict[str, Any]:
    payload = _read_json(Path(reference_summary.results_json_path))
    return {
        "overall_pass": reference_summary.status == "success",
        "case_count": reference_summary.reference_case_count,
        "pass_count": reference_summary.passed_case_count,
        "records": payload.get("records", []),
    }


def _reproducibility_overview(summary: ReproducibilityCheckSummary) -> dict[str, Any]:
    payload = _read_json(Path(summary.comparison_json_path))
    return {
        "overall_pass": summary.status == "success",
        "payload_hash_match": bool(payload.get("payload_hash_match")),
        "records": payload.get("comparison_rows", []),
        "notes": str(payload.get("notes", "")),
    }


def run_phase1_validation(
    matrix_path: str | Path,
    *,
    thresholds_path: str | Path,
    reference_manifest_path: str | Path,
    refinement_config_path: str | Path,
    output_dir: str | Path | None = None,
) -> Phase1ValidationSummary:
    resolved_matrix_path = Path(matrix_path).resolve()
    resolved_thresholds_path = Path(thresholds_path).resolve()
    resolved_manifest_path = Path(reference_manifest_path).resolve()
    resolved_refinement_config = Path(refinement_config_path).resolve()
    thresholds = load_threshold_spec(resolved_thresholds_path)

    destination = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (repo_root() / "runs" / "validation" / resolved_matrix_path.stem / datetime.now().strftime("%Y%m%d-%H%M%S")).resolve()
    )
    destination.mkdir(parents=True, exist_ok=True)

    campaign_summary = run_experiment_matrix(resolved_matrix_path)
    summarize_campaign(campaign_summary.campaign_dir, output_dir=destination / "campaign_summary")
    refinement_summary = run_refinement_sanity(resolved_refinement_config, output_dir=destination / "refinement_sanity")
    reference_summary = run_reference_check(resolved_manifest_path, output_dir=destination / "reference_checks")

    reproducibility_config_ref = thresholds["reproducibility"].get("config_path")
    if not reproducibility_config_ref:
        raise ConfigError(f"reproducibility.config_path missing from threshold spec: {resolved_thresholds_path}")
    reproducibility_config_path = _resolve_path(str(reproducibility_config_ref), source_dir=resolved_thresholds_path.parent)
    reproducibility_summary = run_reproducibility_check(
        reproducibility_config_path,
        tolerances_path=resolved_thresholds_path,
        output_dir=destination / "reproducibility",
    )

    campaign = evaluate_campaign_results(
        campaign_summary.campaign_dir,
        matrix_path=resolved_matrix_path,
        thresholds_path=resolved_thresholds_path,
    )
    refinement = evaluate_refinement_results(
        refinement_summary.output_dir,
        thresholds_path=resolved_thresholds_path,
    )
    reference = _reference_overview(reference_summary)
    reproducibility = _reproducibility_overview(reproducibility_summary)

    validation_summary_csv_path = destination / "validation_summary.csv"
    validation_summary_json_path = destination / "validation_summary.json"
    validation_report_path = destination / "validation_report.md"
    write_csv(validation_summary_csv_path, campaign["records"])
    write_json(
        validation_summary_json_path,
        {
            "matrix_path": str(resolved_matrix_path),
            "thresholds_path": str(resolved_thresholds_path),
            "reference_manifest_path": str(resolved_manifest_path),
            "refinement_config_path": str(resolved_refinement_config),
            "campaign": campaign,
            "refinement": refinement,
            "reference": reference,
            "reproducibility": reproducibility,
            "overall_status": "success"
            if all((campaign["overall_pass"], refinement["overall_pass"], reference["overall_pass"], reproducibility["overall_pass"]))
            else "failed",
        },
    )
    validation_report_path.write_text(
        _validation_markdown(
            campaign=campaign,
            refinement=refinement,
            reference=reference,
            reproducibility=reproducibility,
            thresholds_path=resolved_thresholds_path,
            manifest_path=resolved_manifest_path,
        ),
        encoding="utf-8",
    )

    overall_status = "success" if all((campaign["overall_pass"], refinement["overall_pass"], reference["overall_pass"], reproducibility["overall_pass"])) else "failed"
    return Phase1ValidationSummary(
        status=overall_status,
        matrix_path=str(resolved_matrix_path),
        thresholds_path=str(resolved_thresholds_path),
        reference_manifest_path=str(resolved_manifest_path),
        refinement_config_path=str(resolved_refinement_config),
        output_dir=str(destination),
        validation_summary_csv_path=str(validation_summary_csv_path),
        validation_summary_json_path=str(validation_summary_json_path),
        validation_report_path=str(validation_report_path),
        campaign_dir=str(campaign_summary.campaign_dir),
        refinement_dir=str(refinement_summary.output_dir),
        reference_output_dir=str(reference_summary.output_dir),
        reproducibility_output_dir=str(reproducibility_summary.output_dir),
        campaign_case_count=campaign["case_count"],
        campaign_pass_count=campaign["pass_count"],
        refinement_case_count=refinement["case_count"],
        refinement_pass_count=refinement["pass_count"],
        reference_case_count=reference["case_count"],
        reference_pass_count=reference["pass_count"],
        reproducibility_passed=reproducibility["overall_pass"],
    )
