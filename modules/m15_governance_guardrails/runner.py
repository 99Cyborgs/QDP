#!/usr/bin/env python3
"""
QDP v10.6 M15 calibration, drift, identifiability, and dataset-governance guardrails.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = REPO_ROOT / "packages" / "qdp_io" / "src"
for path in (REPO_ROOT, QDP_IO_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_io.artifacts import candidate_result_summary_report, dump_json, module_selftest_report_payload, utc_now
from tools.workflow.qdp_runtime.qdp_governance import ensure_governance_structures, list_of_strings, strongest_governance_cap
from tools.workflow.qdp_runtime.qdp_paths import BASE_TEMPLATE, CANDIDATE_VALIDATOR, MODULES, SCHEMA
from tools.workflow.qdp_runtime.qdp_validation import validate_candidate_file


MODULE_PATHS = MODULES["m15"]
DEFAULT_BASE_TEMPLATE = BASE_TEMPLATE
DEFAULT_SCHEMA = SCHEMA
DEFAULT_VALIDATOR = CANDIDATE_VALIDATOR
DEFAULT_SELFTEST_CASES = MODULE_PATHS["selftest_cases"]
DEFAULT_SELFTEST_REPORT = MODULE_PATHS["selftest_report"]
DEFAULT_SELFTEST_OUTPUT_DIR = MODULE_PATHS["selftest_output_dir"]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = copy.deepcopy(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    return copy.deepcopy(override)


def make_minimal_final_candidate(base_template: Dict[str, Any]) -> Dict[str, Any]:
    candidate = copy.deepcopy(base_template)
    candidate["candidate_id"] = candidate.get("candidate_id", "") or "M15_WORKING_PATCH_CANDIDATE"
    candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or "M15_WORKING_PATCH_BRANCH"
    ensure_governance_structures(candidate)
    return candidate


def count_orthogonal_axes(candidate: Dict[str, Any]) -> int:
    scaling = candidate.get("scaling_analysis", {})
    explicit = scaling.get("orthogonal_axes_count")
    if isinstance(explicit, int):
        return explicit
    return len(list_of_strings(scaling.get("axes_used", [])))


def independent_constraints_satisfied(candidate: Dict[str, Any]) -> bool:
    params = list_of_strings(candidate.get("new_free_parameters", []))
    sources = candidate.get("independent_constraint_source_per_parameter", {})
    if not params:
        return True
    if not isinstance(sources, dict):
        return False
    return all(str(sources.get(param, "") or "").strip() for param in params)


def run_governance_guardrails(candidate: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    out = copy.deepcopy(candidate)
    ensure_governance_structures(out)

    calibration_status = out.setdefault("calibration_status", {})
    score = calibration_status.get("validity_score")
    if score is None:
        score = out.get("calibration_validity_score")
    threshold = calibration_status.get("threshold", 70.0)
    below_threshold = isinstance(score, (int, float)) and score < threshold
    calibration_status["validity_score"] = score
    out["calibration_validity_score"] = score
    calibration_status["threshold"] = threshold
    calibration_status["below_threshold"] = below_threshold
    if isinstance(score, (int, float)):
        calibration_status["status"] = "VALID" if score >= threshold else "INVALID"
    else:
        calibration_status["status"] = str(calibration_status.get("status", "") or "PENDING_REVIEW")
    calibration_status["notes"] = str(calibration_status.get("notes", "") or "")

    identifiability_status = out.setdefault("identifiability_status", {})
    orthogonal_axes_ok = count_orthogonal_axes(out) >= 2
    independent_constraints_ok = independent_constraints_satisfied(out)
    identifiability_status["orthogonal_axes_satisfied"] = orthogonal_axes_ok
    identifiability_status["independent_constraints_satisfied"] = independent_constraints_ok
    if orthogonal_axes_ok and independent_constraints_ok and count_orthogonal_axes(out) >= 3:
        identifiability_status["status"] = "SUFFICIENT"
    elif orthogonal_axes_ok and independent_constraints_ok:
        identifiability_status["status"] = "PROVISIONAL"
    else:
        identifiability_status["status"] = "INSUFFICIENT"
    identifiability_status["notes"] = str(identifiability_status.get("notes", "") or "")

    residuals = out.get("residual_analysis", {})
    drift_ledger = out.setdefault("drift_ledger", {})
    hierarchical_required = bool(residuals.get("structured_residuals", False)) or bool(drift_ledger.get("hierarchical_model_required", False))
    hierarchical_applied = bool(residuals.get("drift_aware_fit_applied", False)) or bool(drift_ledger.get("hierarchical_model_applied", False))
    drift_ledger["hierarchical_model_required"] = hierarchical_required
    drift_ledger["hierarchical_model_applied"] = hierarchical_applied
    if not hierarchical_required:
        drift_ledger["status"] = "NOT_REQUIRED"
    elif hierarchical_applied:
        drift_ledger["status"] = "ASSESSED"
    else:
        drift_ledger["status"] = "MISSING_MODEL"
    drift_ledger["notes"] = str(drift_ledger.get("notes", "") or "")

    dataset_governance = out.setdefault("dataset_governance", {})
    device_lineage = bool(dataset_governance.get("device_lineage_recorded", out.get("device_lineage_recorded", False)))
    calibration_context = bool(dataset_governance.get("calibration_context_recorded", out.get("calibration_context_recorded", False)))
    protocol_metadata = bool(dataset_governance.get("protocol_metadata_recorded", out.get("protocol_metadata_recorded", False)))
    dataset_governance["device_lineage_recorded"] = device_lineage
    dataset_governance["calibration_context_recorded"] = calibration_context
    dataset_governance["protocol_metadata_recorded"] = protocol_metadata
    dataset_governance["status"] = "COMPLETE" if all([device_lineage, calibration_context, protocol_metadata]) else "INCOMPLETE"
    dataset_governance["independent_evidence_eligible"] = all([device_lineage, calibration_context, protocol_metadata]) and bool(
        out.get("multi_device_data_available", False)
    )
    dataset_governance["notes"] = str(dataset_governance.get("notes", "") or "")

    notes: List[str] = []
    flags = out.setdefault("automatic_flags_triggered", [])

    if calibration_status.get("status") == "INVALID" or calibration_status.get("below_threshold", False):
        out["promotion_cap_governance"] = strongest_governance_cap(str(out.get("promotion_cap_governance", "") or ""), "SANDBOX_ONLY")
        out["governance_outcome"] = "DEFER"
        notes.append("Calibration validity is below threshold or invalid.")
        if "CALIBRATION_INVALID_OR_BELOW_THRESHOLD" not in flags:
            flags.append("CALIBRATION_INVALID_OR_BELOW_THRESHOLD")

    if dataset_governance.get("status") != "COMPLETE":
        out["promotion_cap_governance"] = strongest_governance_cap(str(out.get("promotion_cap_governance", "") or ""), "SANDBOX_ONLY")
        out["governance_outcome"] = "DEFER"
        notes.append("Dataset governance is incomplete.")
        if "DATASET_GOVERNANCE_INCOMPLETE" not in flags:
            flags.append("DATASET_GOVERNANCE_INCOMPLETE")

    if identifiability_status.get("status") == "INSUFFICIENT":
        out["promotion_cap_governance"] = strongest_governance_cap(str(out.get("promotion_cap_governance", "") or ""), "SANDBOX_ONLY")
        notes.append("Identifiability remains insufficient for promotion.")
        if "IDENTIFIABILITY_INSUFFICIENT" not in flags:
            flags.append("IDENTIFIABILITY_INSUFFICIENT")

    if drift_ledger.get("status") == "MISSING_MODEL":
        out["promotion_cap_governance"] = strongest_governance_cap(str(out.get("promotion_cap_governance", "") or ""), "SANDBOX_ONLY")
        notes.append("Drift required a hierarchical model that has not yet been applied.")
        if "DRIFT_MODEL_MISSING" not in flags:
            flags.append("DRIFT_MODEL_MISSING")

    diagnostics = candidate_result_summary_report(
        "QDP_V10_6_M15_REPORT",
        "M15",
        out.get("candidate_id", ""),
        {
            "calibration_status": out.get("calibration_status", {}),
            "identifiability_status": out.get("identifiability_status", {}),
            "drift_ledger": out.get("drift_ledger", {}),
            "dataset_governance": out.get("dataset_governance", {}),
            "promotion_cap_governance": out.get("promotion_cap_governance", ""),
            "governance_outcome": out.get("governance_outcome", ""),
            "notes": notes,
        },
    )
    return out, diagnostics


def summarize_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "calibration_status": candidate.get("calibration_status", {}),
        "identifiability_status": candidate.get("identifiability_status", {}),
        "drift_ledger": candidate.get("drift_ledger", {}),
        "dataset_governance": candidate.get("dataset_governance", {}),
        "promotion_cap_governance": candidate.get("promotion_cap_governance", ""),
        "governance_outcome": candidate.get("governance_outcome", ""),
    }


def compare_expected(actual: Any, expected: Any, path: str = "$") -> List[str]:
    failures: List[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, found {type(actual).__name__}"]
        for key, value in expected.items():
            next_path = f"{path}.{key}"
            if key not in actual:
                failures.append(f"{next_path}: missing")
                continue
            failures.extend(compare_expected(actual[key], value, next_path))
        return failures
    if actual != expected:
        failures.append(f"{path}: expected {expected!r}, found {actual!r}")
    return failures


def run_selftests(
    cases_path: Path,
    base_template_path: Path,
    validator_path: Path,
    schema_path: Path,
    output_dir: Path,
    write_report_path: Path,
) -> Dict[str, Any]:
    cases_obj = load_json(cases_path)
    base_template = load_json(base_template_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []

    for case in cases_obj.get("cases", []):
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip() or "UNNAMED_CASE"
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        candidate = deep_merge(make_minimal_final_candidate(base_template), case.get("candidate_overrides", {}))
        candidate, report = run_governance_guardrails(candidate)
        candidate_path = case_dir / f"{case_id}_candidate.json"
        report_path = case_dir / f"{case_id}_report.json"
        dump_json(candidate_path, candidate)
        dump_json(report_path, report)
        validator_result = validate_candidate_file(candidate_path, validator_path, schema_path, mode="final")
        actual_summary = summarize_candidate(candidate)
        expected_summary = case.get("expected", {})
        comparison_failures = compare_expected(actual_summary, expected_summary)
        comparison_ok = not comparison_failures
        passed = comparison_ok and validator_result["valid"]
        results.append(
            {
                "case_id": case_id,
                "description": case.get("description", ""),
                "passed": passed,
                "comparison_ok": comparison_ok,
                "comparison_failures": comparison_failures,
                "validator_result": validator_result,
                "expected_summary": expected_summary,
                "actual_summary": actual_summary,
                "report_path": str(report_path),
                "output_candidate_path": str(candidate_path),
            }
        )

    cases_total = len(results)
    cases_passed = sum(1 for result in results if result["passed"])
    report = module_selftest_report_payload(
        "QDP_V10_6_M15_SELFTEST_REPORT",
        "M15",
        results,
        visible_source_only=True,
        all_passed=cases_total > 0 and cases_passed == cases_total,
        schema_valid_all=all(result["validator_result"]["valid"] for result in results),
    )
    dump_json(write_report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M15 governance guardrails module.")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write-report", type=Path, default=DEFAULT_SELFTEST_REPORT)
    parser.add_argument("--base-template", type=Path, default=DEFAULT_BASE_TEMPLATE)
    parser.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--selftest-cases", type=Path, default=DEFAULT_SELFTEST_CASES)
    parser.add_argument("--selftest-output-dir", type=Path, default=DEFAULT_SELFTEST_OUTPUT_DIR)
    args = parser.parse_args()

    if args.selftest:
        report = run_selftests(args.selftest_cases, args.base_template, args.validator, args.schema, args.selftest_output_dir, args.write_report)
        print(json.dumps(report, indent=2))
        return 0 if report.get("all_passed", False) and report.get("schema_valid_all", False) else 1

    if not args.candidate:
        raise SystemExit("M15 run requires --candidate unless --selftest is set.")

    candidate = load_json(args.candidate)
    out_candidate, report = run_governance_guardrails(candidate)
    if args.output:
        dump_json(args.output, out_candidate)
    else:
        print(json.dumps(out_candidate, indent=2))
    if args.write_report:
        dump_json(args.write_report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

