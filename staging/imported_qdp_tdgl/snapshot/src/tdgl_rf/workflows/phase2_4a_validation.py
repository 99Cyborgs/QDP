"""Phase-2.4A same-stack validation workflow for the committed ensemble pack."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import yaml

from tdgl_rf.config.loaders import repo_root
from tdgl_rf.exceptions import ManifestValidationError, TDGLRFError
from tdgl_rf.io.reports import write_csv, write_json
from tdgl_rf.workflows.experiment_sweep import (
    SeededVortexExperimentPack,
    load_seeded_vortex_experiment_pack,
    run_seeded_vortex_experiment_pack,
)

PHASE2_4A_VALIDATION_SCHEMA_VERSION = "tdgl_rf.seeded_vortex_phase2_4a_validation.v1"
PHASE2_4A_REQUIRED_NON_CLAIMS = {
    "scientific_robustness": "not established by this validation surface",
    "long_time_dynamics": "not established by this validation surface",
    "cross_stack_portability": "not established by this validation surface",
}
PHASE2_4A_TOP_LEVEL_FIELDS = (
    "mode",
    "pack_name",
    "parent_manifest_hash",
    "expected_member_count",
    "parameter_point_count",
    "run_count",
    "overall_status",
)
PHASE2_4A_PARAMETER_POINT_FIELDS = (
    "param_set_hash",
    "ensemble_id",
    "parameters",
    "case_class",
    "run_count",
    "successful_run_count",
    "member_indices",
    "noise_seeds",
    "aggregates",
    "robustness_summary",
)


@dataclass(frozen=True)
class Phase24AValidationManifest:
    schema_version: str
    validation_id: str
    claim_scope: str
    validation_manifest_path: str
    experiment_pack_ref: str
    experiment_pack_path: str
    expected_top_level: dict[str, Any]
    expected_parameter_points: list[dict[str, Any]]
    expected_members: list[dict[str, Any]]


@dataclass(frozen=True)
class Phase24AValidationSummary:
    status: str
    manifest_path: str
    experiment_pack_path: str
    output_dir: str
    validation_json_path: str
    validation_markdown_path: str
    validation_cases_csv_path: str
    experiment_results_json_path: str
    experiment_results_markdown_path: str
    parameter_point_count: int
    member_count: int
    mismatch_count: int


def default_phase2_4a_validation_manifest_path() -> Path:
    return (repo_root() / "validation" / "seeded_vortex_phase2_4a_validation_manifest.yaml").resolve()


def _phase2_4a_validation_schema_path() -> Path:
    return repo_root() / "configs" / "seeded_vortex_phase2_4a_validation_manifest.schema.json"


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


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except FileNotFoundError as exc:
        raise ManifestValidationError(f"validation manifest does not exist: {path}") from exc
    except yaml.YAMLError as exc:
        raise ManifestValidationError(f"invalid YAML payload at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ManifestValidationError(f"expected mapping at top level of {path}")
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
        raise ManifestValidationError(
            f"{label} schema validation failed at {_schema_error_location(list(first.absolute_path))}: {first.message}"
        )


def _resolve_path(reference_path: str, *, source_dir: Path) -> Path:
    candidate = Path(reference_path)
    if candidate.is_absolute():
        return candidate.resolve()
    source_relative = (source_dir / candidate).resolve()
    repo_relative = (repo_root() / candidate).resolve()
    return source_relative if source_relative.exists() else repo_relative


def _member_provenance_projection(provenance_payload: dict[str, Any]) -> dict[str, Any]:
    experiment_payload = provenance_payload.get("experiment")
    if not isinstance(experiment_payload, dict):
        raise TDGLRFError("ensemble provenance is missing the experiment block")
    seeds_payload = provenance_payload.get("seeds")
    if not isinstance(seeds_payload, dict):
        raise TDGLRFError("ensemble provenance is missing the seeds block")
    noise_payload = provenance_payload.get("noise")
    if not isinstance(noise_payload, dict):
        raise TDGLRFError("ensemble provenance is missing the noise block")
    determinism_payload = provenance_payload.get("determinism")
    if not isinstance(determinism_payload, dict):
        raise TDGLRFError("ensemble provenance is missing the determinism block")
    initialization_payload = provenance_payload.get("initialization")
    if not isinstance(initialization_payload, dict):
        raise TDGLRFError("ensemble provenance is missing the initialization block")
    ensemble_payload = provenance_payload.get("ensemble")
    if not isinstance(ensemble_payload, dict):
        raise TDGLRFError("ensemble provenance is missing the ensemble block")
    return {
        "schema_version": provenance_payload.get("schema_version"),
        "experiment": {
            "base_case_hash": experiment_payload.get("base_case_hash"),
        },
        "seeds": {
            "master_seed": seeds_payload.get("master_seed"),
            "noise_seed": seeds_payload.get("noise_seed"),
            "initial_condition": seeds_payload.get("initial_condition"),
            "vortex_seed_count": seeds_payload.get("vortex_seed_count"),
        },
        "noise": {
            "enabled": noise_payload.get("enabled"),
            "strength": noise_payload.get("strength"),
            "seed": noise_payload.get("seed"),
            "contract_kind": noise_payload.get("contract_kind"),
            "sampling": noise_payload.get("sampling"),
        },
        "determinism": {
            "noise_enabled": determinism_payload.get("noise_enabled"),
            "deterministic_expected": determinism_payload.get("deterministic_expected"),
            "master_seed": determinism_payload.get("master_seed"),
            "noise_seed": determinism_payload.get("noise_seed"),
            "pinning_seed": determinism_payload.get("pinning_seed"),
            "reproducibility_scope": determinism_payload.get("reproducibility_scope"),
        },
        "ensemble": {
            "mode": ensemble_payload.get("mode"),
            "member_count": ensemble_payload.get("member_count"),
            "master_seed": ensemble_payload.get("master_seed"),
            "parent_manifest_hash": ensemble_payload.get("parent_manifest_hash"),
        },
        "initialization": {
            "mode": initialization_payload.get("mode"),
            "configured_vortex_seeds": initialization_payload.get("configured_vortex_seeds"),
            "resolved_vortex_seeds": initialization_payload.get("resolved_vortex_seeds"),
            "seed_resolution_policy": initialization_payload.get("seed_resolution_policy"),
            "seed_rejection_taxonomy_version": initialization_payload.get("seed_rejection_taxonomy_version"),
        },
    }


def _top_level_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: payload.get(field) for field in PHASE2_4A_TOP_LEVEL_FIELDS}


def _parameter_point_projection(point_payload: dict[str, Any]) -> dict[str, Any]:
    return {field: point_payload.get(field) for field in PHASE2_4A_PARAMETER_POINT_FIELDS}


def _member_projection(record_payload: dict[str, Any], provenance_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record_payload.get("run_id"),
        "ensemble_id": record_payload.get("ensemble_id"),
        "member_index": record_payload.get("member_index"),
        "noise_seed": record_payload.get("noise_seed"),
        "param_set_hash": record_payload.get("param_set_hash"),
        "status": record_payload.get("status"),
        "observables": record_payload.get("observables"),
        "provenance": _member_provenance_projection(provenance_payload),
    }


def _exact_mismatch(
    *,
    surface: str,
    subject_id: str,
    path: str,
    expected: Any,
    observed: Any,
    assessment: str,
) -> dict[str, Any]:
    return {
        "surface": surface,
        "subject_id": subject_id,
        "path": path,
        "expected": expected,
        "observed": observed,
        "assessment": assessment,
    }


def _collect_exact_mismatches(
    expected: Any,
    observed: Any,
    *,
    surface: str,
    subject_id: str,
    path_prefix: str = "",
) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    current_path = path_prefix or "<root>"
    if isinstance(expected, dict):
        if not isinstance(observed, dict):
            return [
                _exact_mismatch(
                    surface=surface,
                    subject_id=subject_id,
                    path=current_path,
                    expected="mapping",
                    observed=observed,
                    assessment="type_mismatch",
                )
            ]
        expected_keys = set(expected)
        observed_keys = set(observed)
        for key in sorted(expected_keys - observed_keys):
            child_path = key if not path_prefix else f"{path_prefix}.{key}"
            mismatches.append(
                _exact_mismatch(
                    surface=surface,
                    subject_id=subject_id,
                    path=child_path,
                    expected=expected[key],
                    observed="<missing>",
                    assessment="missing_value",
                )
            )
        for key in sorted(observed_keys - expected_keys):
            child_path = key if not path_prefix else f"{path_prefix}.{key}"
            mismatches.append(
                _exact_mismatch(
                    surface=surface,
                    subject_id=subject_id,
                    path=child_path,
                    expected="<unexpected>",
                    observed=observed[key],
                    assessment="unexpected_value",
                )
            )
        for key in sorted(expected_keys & observed_keys):
            child_path = key if not path_prefix else f"{path_prefix}.{key}"
            mismatches.extend(
                _collect_exact_mismatches(
                    expected[key],
                    observed[key],
                    surface=surface,
                    subject_id=subject_id,
                    path_prefix=child_path,
                )
            )
        return mismatches
    if isinstance(expected, list):
        if not isinstance(observed, list):
            return [
                _exact_mismatch(
                    surface=surface,
                    subject_id=subject_id,
                    path=current_path,
                    expected="list",
                    observed=observed,
                    assessment="type_mismatch",
                )
            ]
        if len(expected) != len(observed):
            mismatches.append(
                _exact_mismatch(
                    surface=surface,
                    subject_id=subject_id,
                    path=current_path,
                    expected=f"length={len(expected)}",
                    observed=f"length={len(observed)}",
                    assessment="length_mismatch",
                )
            )
        shared_length = min(len(expected), len(observed))
        for index in range(shared_length):
            child_path = f"{path_prefix}[{index}]" if path_prefix else f"[{index}]"
            mismatches.extend(
                _collect_exact_mismatches(
                    expected[index],
                    observed[index],
                    surface=surface,
                    subject_id=subject_id,
                    path_prefix=child_path,
                )
            )
        return mismatches
    if observed != expected:
        mismatches.append(
            _exact_mismatch(
                surface=surface,
                subject_id=subject_id,
                path=current_path,
                expected=expected,
                observed=observed,
                assessment="value_mismatch",
            )
        )
    return mismatches


def _mismatch_note(mismatch_records: list[dict[str, Any]], success_message: str) -> str:
    if not mismatch_records:
        return success_message
    head = mismatch_records[:3]
    summary = "; ".join(
        f"{record['path']} expected {record['expected']!r} observed {record['observed']!r}" for record in head
    )
    if len(mismatch_records) > len(head):
        summary += f"; +{len(mismatch_records) - len(head)} more"
    return summary


def load_phase2_4a_validation_manifest(manifest_path: str | Path) -> Phase24AValidationManifest:
    path = Path(manifest_path).resolve()
    payload = _read_yaml(path)
    _validate_payload_against_schema(
        payload,
        _phase2_4a_validation_schema_path(),
        label="Phase-2.4A validation manifest",
    )
    expected_results = payload["expected_results"]
    experiment_pack_ref = str(payload["experiment_pack"]).strip()
    experiment_pack_path = _resolve_path(experiment_pack_ref, source_dir=path.parent)
    if not experiment_pack_path.exists():
        raise ManifestValidationError(f"Phase-2.4A validation manifest experiment_pack does not exist: {experiment_pack_ref}")
    pack = load_seeded_vortex_experiment_pack(experiment_pack_path)
    if pack.mode != "stochastic_ensemble":
        raise ManifestValidationError("Phase-2.4A validation manifest requires a 4.x stochastic ensemble experiment pack")

    expected_parameter_points = list(expected_results["parameter_points"])
    seen_param_hashes: set[str] = set()
    for item in expected_parameter_points:
        param_set_hash = str(item["param_set_hash"])
        if param_set_hash in seen_param_hashes:
            raise ManifestValidationError(f"Phase-2.4A validation manifest duplicates param_set_hash '{param_set_hash}'")
        seen_param_hashes.add(param_set_hash)

    expected_members = list(expected_results["members"])
    seen_run_ids: set[str] = set()
    for item in expected_members:
        run_id = str(item["run_id"])
        if run_id in seen_run_ids:
            raise ManifestValidationError(f"Phase-2.4A validation manifest duplicates run_id '{run_id}'")
        seen_run_ids.add(run_id)

    return Phase24AValidationManifest(
        schema_version=str(payload["schema_version"]),
        validation_id=str(payload["validation_id"]),
        claim_scope=str(payload["claim_scope"]),
        validation_manifest_path=str(path),
        experiment_pack_ref=experiment_pack_ref,
        experiment_pack_path=str(experiment_pack_path),
        expected_top_level=dict(expected_results["top_level"]),
        expected_parameter_points=expected_parameter_points,
        expected_members=expected_members,
    )


def _build_phase2_4a_case_rows(
    *,
    top_level_mismatches: list[dict[str, Any]],
    point_rows: list[dict[str, Any]],
    member_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [
        {
            "surface": "top_level",
            "subject_id": "overall",
            "overall_pass": not top_level_mismatches,
            "mismatch_count": len(top_level_mismatches),
            "notes": _mismatch_note(top_level_mismatches, "matched frozen top-level aggregate surface"),
        }
    ]
    rows.extend(point_rows)
    rows.extend(member_rows)
    return rows


def _phase2_4a_markdown(
    *,
    manifest: Phase24AValidationManifest,
    case_rows: list[dict[str, Any]],
    mismatch_records: list[dict[str, Any]],
    summary: Phase24AValidationSummary,
) -> str:
    lines = [
        "# Phase-2.4A Same-Stack Validation",
        "",
        "This report validates the committed fixed-seed Phase-2.4A ensemble pack as a same-stack runtime/control-plane surface only.",
        "It freezes member identity, selected replay metadata, aggregate observables, and robustness summaries.",
        "",
        f"- Validation manifest: `{manifest.validation_manifest_path}`",
        f"- Experiment pack: `{manifest.experiment_pack_path}`",
        f"- Overall status: `{summary.status}`",
        f"- Parameter points: `{summary.parameter_point_count}`",
        f"- Members: `{summary.member_count}`",
        f"- Mismatch count: `{summary.mismatch_count}`",
        "",
        "## Boundary",
        "",
        f"- Claim scope: {manifest.claim_scope}",
    ]
    for key, value in PHASE2_4A_REQUIRED_NON_CLAIMS.items():
        lines.append(f"- {key.replace('_', ' ')}: {value}")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| surface | subject_id | pass | mismatch_count | notes |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in case_rows:
        lines.append(
            "| {surface} | {subject_id} | {passed} | {mismatch_count} | {notes} |".format(
                surface=row["surface"],
                subject_id=row["subject_id"],
                passed="yes" if row["overall_pass"] else "no",
                mismatch_count=row["mismatch_count"],
                notes=str(row["notes"]).replace("\n", " "),
            )
        )
    if mismatch_records:
        lines.extend(
            [
                "",
                "## Mismatches",
                "",
                "| surface | subject_id | path | assessment | expected | observed |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for record in mismatch_records:
            lines.append(
                "| {surface} | {subject_id} | {path} | {assessment} | `{expected}` | `{observed}` |".format(
                    surface=record["surface"],
                    subject_id=record["subject_id"],
                    path=record["path"],
                    assessment=record["assessment"],
                    expected=json.dumps(record["expected"], sort_keys=True, ensure_ascii=True),
                    observed=json.dumps(record["observed"], sort_keys=True, ensure_ascii=True),
                )
            )
    lines.append("")
    return "\n".join(lines)


def _observed_member_surfaces(
    experiment_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    members: list[dict[str, Any]] = []
    mismatch_records: list[dict[str, Any]] = []
    for record in experiment_payload.get("run_records", []):
        run_dir = record.get("run_dir")
        run_id = str(record.get("run_id", "<unknown>"))
        if not run_dir:
            mismatch_records.append(
                _exact_mismatch(
                    surface="member",
                    subject_id=run_id,
                    path="run_dir",
                    expected="<present>",
                    observed=run_dir,
                    assessment="missing_value",
                )
            )
            continue
        provenance_payload = _read_json(Path(str(run_dir)) / "provenance.json", error_cls=TDGLRFError)
        members.append(_member_projection(record, provenance_payload))
    return members, mismatch_records


def _compare_indexed_surfaces(
    *,
    surface: str,
    subject_label: str,
    expected_items: list[dict[str, Any]],
    observed_items: list[dict[str, Any]],
    identity_key: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mismatch_records: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    expected_index = {str(item[identity_key]): item for item in expected_items}
    observed_index = {str(item[identity_key]): item for item in observed_items}
    for subject_id in sorted(expected_index.keys() - observed_index.keys()):
        mismatch_records.append(
            _exact_mismatch(
                surface=surface,
                subject_id=subject_id,
                path="<root>",
                expected=expected_index[subject_id],
                observed="<missing>",
                assessment="missing_item",
            )
        )
    for subject_id in sorted(observed_index.keys() - expected_index.keys()):
        mismatch_records.append(
            _exact_mismatch(
                surface=surface,
                subject_id=subject_id,
                path="<root>",
                expected="<unexpected>",
                observed=observed_index[subject_id],
                assessment="unexpected_item",
            )
        )
    for subject_id in sorted(expected_index.keys() & observed_index.keys()):
        item_mismatches = _collect_exact_mismatches(
            expected_index[subject_id],
            observed_index[subject_id],
            surface=surface,
            subject_id=subject_id,
        )
        mismatch_records.extend(item_mismatches)
        case_rows.append(
            {
                "surface": surface,
                "subject_id": subject_id,
                "overall_pass": not item_mismatches,
                "mismatch_count": len(item_mismatches),
                "notes": _mismatch_note(item_mismatches, f"matched frozen {subject_label} surface"),
            }
        )
    for subject_id in sorted(expected_index.keys() - observed_index.keys()):
        case_rows.append(
            {
                "surface": surface,
                "subject_id": subject_id,
                "overall_pass": False,
                "mismatch_count": 1,
                "notes": f"missing observed {subject_label} surface",
            }
        )
    for subject_id in sorted(observed_index.keys() - expected_index.keys()):
        case_rows.append(
            {
                "surface": surface,
                "subject_id": subject_id,
                "overall_pass": False,
                "mismatch_count": 1,
                "notes": f"unexpected observed {subject_label} surface",
            }
        )
    return case_rows, mismatch_records


def _load_experiment_pack(manifest: Phase24AValidationManifest) -> SeededVortexExperimentPack:
    pack = load_seeded_vortex_experiment_pack(manifest.experiment_pack_path)
    if pack.mode != "stochastic_ensemble":
        raise ManifestValidationError("validate-phase2-4a requires a stochastic Phase-2.4A experiment pack")
    return pack


def run_phase2_4a_validation(
    manifest_path: str | Path = default_phase2_4a_validation_manifest_path(),
    *,
    output_dir: str | Path | None = None,
) -> Phase24AValidationSummary:
    manifest = load_phase2_4a_validation_manifest(manifest_path)
    pack = _load_experiment_pack(manifest)
    destination = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (repo_root() / "runs" / "phase2_4a_validation" / Path(manifest.validation_manifest_path).stem / datetime.now().strftime("%Y%m%d-%H%M%S")).resolve()
    )
    destination.mkdir(parents=True, exist_ok=True)

    experiment_summary = run_seeded_vortex_experiment_pack(pack.manifest_path, output_dir=destination / "experiment_run")
    experiment_payload = _read_json(Path(experiment_summary.results_json_path))
    observed_top_level = _top_level_projection(experiment_payload)
    observed_parameter_points = [
        _parameter_point_projection(point_payload) for point_payload in experiment_payload.get("parameter_points", [])
    ]
    observed_members, member_projection_mismatches = _observed_member_surfaces(experiment_payload)

    top_level_mismatches = _collect_exact_mismatches(
        manifest.expected_top_level,
        observed_top_level,
        surface="top_level",
        subject_id="overall",
    )
    point_rows, point_mismatches = _compare_indexed_surfaces(
        surface="parameter_point",
        subject_label="parameter-point",
        expected_items=manifest.expected_parameter_points,
        observed_items=observed_parameter_points,
        identity_key="param_set_hash",
    )
    member_rows, member_mismatches = _compare_indexed_surfaces(
        surface="member",
        subject_label="member",
        expected_items=manifest.expected_members,
        observed_items=observed_members,
        identity_key="run_id",
    )
    mismatch_records = top_level_mismatches + point_mismatches + member_projection_mismatches + member_mismatches
    case_rows = _build_phase2_4a_case_rows(
        top_level_mismatches=top_level_mismatches,
        point_rows=point_rows,
        member_rows=member_rows,
    )
    overall_status = "success" if not mismatch_records else "failed"

    validation_json_path = destination / "phase2_4a_validation.json"
    validation_markdown_path = destination / "phase2_4a_validation.md"
    validation_cases_csv_path = destination / "phase2_4a_validation_cases.csv"
    payload = {
        "schema_version": manifest.schema_version,
        "validation_id": manifest.validation_id,
        "manifest_path": manifest.validation_manifest_path,
        "experiment_pack_path": manifest.experiment_pack_path,
        "claim_scope": manifest.claim_scope,
        "non_claims": dict(PHASE2_4A_REQUIRED_NON_CLAIMS),
        "experiment_run": {
            "status": experiment_summary.status,
            "output_dir": experiment_summary.output_dir,
            "results_json_path": experiment_summary.results_json_path,
            "results_csv_path": experiment_summary.results_csv_path,
            "results_markdown_path": experiment_summary.results_markdown_path,
        },
        "top_level": {
            "expected": manifest.expected_top_level,
            "observed": observed_top_level,
        },
        "parameter_points": {
            "expected": manifest.expected_parameter_points,
            "observed": observed_parameter_points,
        },
        "members": {
            "expected": manifest.expected_members,
            "observed": observed_members,
        },
        "case_count": len(case_rows),
        "pass_count": sum(int(bool(row["overall_pass"])) for row in case_rows),
        "mismatch_count": len(mismatch_records),
        "case_rows": case_rows,
        "mismatch_records": mismatch_records,
        "overall_status": overall_status,
    }
    write_json(validation_json_path, payload)
    write_csv(validation_cases_csv_path, case_rows)
    summary = Phase24AValidationSummary(
        status=overall_status,
        manifest_path=manifest.validation_manifest_path,
        experiment_pack_path=manifest.experiment_pack_path,
        output_dir=str(destination),
        validation_json_path=str(validation_json_path),
        validation_markdown_path=str(validation_markdown_path),
        validation_cases_csv_path=str(validation_cases_csv_path),
        experiment_results_json_path=experiment_summary.results_json_path,
        experiment_results_markdown_path=experiment_summary.results_markdown_path,
        parameter_point_count=len(observed_parameter_points),
        member_count=len(observed_members),
        mismatch_count=len(mismatch_records),
    )
    validation_markdown_path.write_text(
        _phase2_4a_markdown(
            manifest=manifest,
            case_rows=case_rows,
            mismatch_records=mismatch_records,
            summary=summary,
        ),
        encoding="utf-8",
    )
    return summary
