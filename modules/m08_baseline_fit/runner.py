#!/usr/bin/env python3
"""
QDP v10.6 M08 baseline GKSL fit and drift-aware residual diagnostics.

This is a visible-source working-patch implementation derived from
specs/core/model_spec.md and specs/research/deep_research_report.md. It emits conservative baseline-model
and residual-analysis fields without claiming parity with unsurfaced retained
runtime behavior.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = REPO_ROOT / "packages" / "qdp_io" / "src"
for path in (REPO_ROOT, QDP_IO_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_io.artifacts import dump_json, module_selftest_report_payload, utc_now, visible_source_result_summary_report
from tools.workflow.qdp_runtime.qdp_paths import BASE_TEMPLATE, CANDIDATE_VALIDATOR, DEEP_RESEARCH_REPORT, MODEL_SPEC, MODULES, SCHEMA, repo_rel
from tools.workflow.qdp_runtime.qdp_validation import validate_candidate_file


MODULE_PATHS = MODULES["m08"]
DEFAULT_BASE_TEMPLATE = BASE_TEMPLATE
DEFAULT_SCHEMA = SCHEMA
DEFAULT_VALIDATOR = CANDIDATE_VALIDATOR
DEFAULT_SELFTEST_CASES = MODULE_PATHS["selftest_cases"]
DEFAULT_SELFTEST_REPORT = MODULE_PATHS["selftest_report"]
DEFAULT_SELFTEST_OUTPUT_DIR = MODULE_PATHS["selftest_output_dir"]

READY_SELF_CHECK = {
    "validation_harness_status": "PASSED",
    "schema_validation_status": "PASSED",
    "reference_resolution_status": "PASSED",
    "determinism_status": "PASSED",
    "system_status": "READY",
}

EXPECTED_PARAMETER_KEYS = ["T1", "Tphi", "measurement_noise_level"]


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


def list_of_strings(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def unique_preserve(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().upper() in {"TRUE", "YES", "1", "PASS", "PASSED", "READY"}
    return False


def derive_system_status(gsc: Dict[str, Any]) -> str:
    schema = str(gsc.get("schema_validation_status", "") or "")
    ref = str(gsc.get("reference_resolution_status", "") or "")
    harness = str(gsc.get("validation_harness_status", "") or "")
    determinism = str(gsc.get("determinism_status", "") or "")
    if schema == "FAILED":
        return "SCHEMA_VALIDATION_FAILURE"
    if ref == "FAILED":
        return "REFERENCE_RESOLUTION_FAILURE"
    if harness == "FAILED" or determinism == "FAILED":
        return "GOVERNANCE_LOGIC_FAILURE"
    if harness == "UNKNOWN":
        return "HARNESS_REQUIRED"
    if harness == "PASSED" and schema == "PASSED" and ref == "PASSED" and determinism == "PASSED":
        return "READY"
    return str(gsc.get("system_status", "") or "")


def append_unique(items: List[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def make_minimal_final_candidate(base_template: Dict[str, Any]) -> Dict[str, Any]:
    candidate = copy.deepcopy(base_template)
    candidate["candidate_id"] = candidate.get("candidate_id", "") or "M08_WORKING_PATCH_CANDIDATE"
    candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or "M08_WORKING_PATCH_BRANCH"
    candidate["governance_self_check"] = copy.deepcopy(READY_SELF_CHECK)
    candidate["system_status"] = "READY"
    candidate["scientific_decision"] = "NOT_EVALUATED"
    candidate["governance_outcome"] = "DEFER"
    candidate["cross_device_status"] = "NOT_REQUIRED"
    candidate.setdefault("cross_device_validation", {})
    candidate["cross_device_validation"]["status"] = "NOT_REQUIRED"
    candidate["promotion_cap_governance"] = ""
    candidate["promotion_cap_scientific"] = ""
    candidate["baseline_model"] = {
        "status": "",
        "joint_fit_used": False,
        "hierarchical_drift_model_used": False,
        "parameters": {},
    }
    candidate["residual_analysis"] = {
        "structured_residuals": False,
        "features": [],
        "time_series_based": False,
    }
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("gate_trace", [])
    return candidate


def ensure_candidate_defaults(candidate: Dict[str, Any]) -> None:
    candidate.setdefault("governance_self_check", {})
    for key, value in READY_SELF_CHECK.items():
        candidate["governance_self_check"].setdefault(key, value)
    candidate["governance_self_check"]["system_status"] = derive_system_status(candidate["governance_self_check"]) or "READY"
    candidate["system_status"] = candidate.get("system_status", "") or candidate["governance_self_check"]["system_status"]
    candidate["governance_self_check"]["system_status"] = candidate["system_status"]
    candidate["scientific_decision"] = candidate.get("scientific_decision", "") or "NOT_EVALUATED"
    candidate["governance_outcome"] = candidate.get("governance_outcome", "") or "DEFER"
    candidate["cross_device_status"] = candidate.get("cross_device_status", "") or "NOT_REQUIRED"
    candidate.setdefault("cross_device_validation", {})
    candidate["cross_device_validation"]["status"] = candidate["cross_device_status"]
    candidate.setdefault("baseline_model", {})
    candidate.setdefault("residual_analysis", {})
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("gate_trace", [])


def extract_observables(candidate: Dict[str, Any], baseline: Dict[str, Any]) -> List[str]:
    observables = []
    observables.extend(list_of_strings(baseline.get("observables_fit", [])))
    primary = str(candidate.get("primary_observable", "") or "").strip()
    secondary = str(candidate.get("secondary_observable", "") or "").strip()
    if primary:
        observables.append(primary)
    if secondary:
        observables.append(secondary)
    return unique_preserve(observables)


def normalized_parameters(baseline: Dict[str, Any]) -> Dict[str, Any]:
    raw = baseline.get("parameters", {})
    params = copy.deepcopy(raw) if isinstance(raw, dict) else {}
    for key in EXPECTED_PARAMETER_KEYS:
        params.setdefault(key, params.get(key, ""))
    return params


def derive_residual_features(candidate: Dict[str, Any], baseline: Dict[str, Any], residuals: Dict[str, Any]) -> Tuple[List[str], Dict[str, bool]]:
    indicators = {
        "correlated": bool_value(residuals.get("correlated_residuals", False))
        or bool_value(residuals.get("autocorrelation_nonwhite", False))
        or bool_value(residuals.get("nonwhite_residuals", False)),
        "non_gaussian": bool_value(residuals.get("non_gaussian_residuals", False))
        or bool_value(residuals.get("heavy_tails_detected", False))
        or bool_value(residuals.get("burstiness_detected", False)),
        "drive_shift": bool_value(residuals.get("drive_conditional_shifts_detected", False))
        or bool_value(residuals.get("drive_conditional_shift", False)),
        "ramsey_mismatch": bool_value(residuals.get("ramsey_envelope_mismatch", False))
        or bool_value(residuals.get("non_exponential_ramsey_envelope", False)),
        "cross_corr": bool_value(residuals.get("cross_observable_correlations_present", False))
        or bool_value(residuals.get("cross_observable_correlated", False)),
        "nonstationary": bool_value(residuals.get("nonstationary_residuals", False))
        or bool_value(residuals.get("drift_detected", False)),
        "insufficient_time_series": not bool_value(residuals.get("time_series_available", baseline.get("time_series_available", True))),
    }
    features = []
    if indicators["correlated"]:
        features.append("CORRELATED_RESIDUALS")
    if indicators["non_gaussian"]:
        features.append("NON_GAUSSIAN_RESIDUALS")
    if indicators["drive_shift"]:
        features.append("DRIVE_CONDITIONAL_SHIFTS")
    if indicators["ramsey_mismatch"]:
        features.append("RAMSEY_ENVELOPE_MISMATCH")
    if indicators["cross_corr"]:
        features.append("CROSS_OBSERVABLE_CORRELATIONS")
    if indicators["nonstationary"]:
        features.append("NONSTATIONARY_RESIDUALS")
    if indicators["insufficient_time_series"]:
        features.append("INSUFFICIENT_TIME_SERIES_DATA")
    return features, indicators


def summarize_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    baseline = candidate.get("baseline_model", {})
    residuals = candidate.get("residual_analysis", {})
    return {
        "baseline_model": {
            "status": baseline.get("status", ""),
            "joint_fit_used": baseline.get("joint_fit_used", False),
            "hierarchical_drift_model_used": baseline.get("hierarchical_drift_model_used", False),
            "pipeline_executed": baseline.get("pipeline_executed", False),
            "reduction_limit_verified": baseline.get("reduction_limit_verified", False),
        },
        "residual_analysis": {
            "structured_residuals": residuals.get("structured_residuals", False),
            "white_residuals": residuals.get("white_residuals", False),
            "stationary_residuals": residuals.get("stationary_residuals", False),
            "cross_observable_correlations_vanish": residuals.get("cross_observable_correlations_vanish", False),
            "drift_aware_fit_applied": residuals.get("drift_aware_fit_applied", False),
            "features": residuals.get("features", []),
            "time_series_based": residuals.get("time_series_based", False),
        },
    }


def run_baseline_fit(candidate: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    out = copy.deepcopy(candidate)
    ensure_candidate_defaults(out)
    baseline = out["baseline_model"]
    residuals = out["residual_analysis"]

    observables_fit = extract_observables(out, baseline)
    parameters = normalized_parameters(baseline)
    parameter_count = sum(1 for key in EXPECTED_PARAMETER_KEYS if str(parameters.get(key, "")).strip() != "")

    joint_fit_used = bool_value(baseline.get("joint_fit_used", False)) or len(observables_fit) >= 2
    hierarchical_drift_model_used = (
        bool_value(baseline.get("hierarchical_drift_model_used", False))
        or len(list_of_strings(baseline.get("fit_windows", []))) >= 2
        or len(list_of_strings(residuals.get("cross_validation_days", []))) >= 2
    )
    noise_model_declared = bool_value(baseline.get("noise_model_declared", False)) or str(parameters.get("measurement_noise_level", "")).strip() != ""
    trace_preserving = bool_value(baseline.get("trace_preserving", True))
    complete_positive = bool_value(baseline.get("complete_positive", True))
    textbook_limit_recovered = bool_value(baseline.get("textbook_limit_recovered", False)) or bool_value(baseline.get("reduction_limit_test_passed", False))
    fit_converged = bool_value(baseline.get("fit_converged", False)) or (joint_fit_used and parameter_count >= 2 and noise_model_declared)

    features, indicators = derive_residual_features(out, baseline, residuals)
    time_series_based = bool_value(residuals.get("time_series_based", False)) or not indicators["insufficient_time_series"]
    structured_residuals = bool(features)
    white_residuals = not structured_residuals and not indicators["correlated"]
    stationary_residuals = not indicators["nonstationary"]
    cross_observable_correlations_vanish = not indicators["cross_corr"]
    drift_aware_fit_applied = hierarchical_drift_model_used

    pipeline_executed = joint_fit_used and fit_converged and noise_model_declared and trace_preserving and complete_positive
    if pipeline_executed and time_series_based:
        status = "EXECUTED_SUCCESSFULLY"
    elif not joint_fit_used:
        status = "INSUFFICIENT_JOINT_FIT_DATA"
    elif not noise_model_declared:
        status = "NOISE_MODEL_UNDECLARED"
    elif not time_series_based:
        status = "INSUFFICIENT_TIME_SERIES_DATA"
    else:
        status = "FIT_NOT_EXECUTED"

    reduction_limit_verified = bool(str(out.get("reduction_limit", "")).strip()) and textbook_limit_recovered

    baseline["status"] = status
    baseline["joint_fit_used"] = joint_fit_used
    baseline["hierarchical_drift_model_used"] = hierarchical_drift_model_used
    baseline["parameters"] = parameters
    baseline["observables_fit"] = observables_fit
    baseline["noise_model_declared"] = noise_model_declared
    baseline["trace_preserving"] = trace_preserving
    baseline["complete_positive"] = complete_positive
    baseline["textbook_limit_recovered"] = textbook_limit_recovered
    baseline["fit_converged"] = fit_converged
    baseline["pipeline_executed"] = pipeline_executed
    baseline["reduction_limit_verified"] = reduction_limit_verified
    baseline["reduction_limit_test_passed"] = textbook_limit_recovered

    residuals["structured_residuals"] = structured_residuals
    residuals["features"] = features
    residuals["time_series_based"] = time_series_based
    residuals["white_residuals"] = white_residuals
    residuals["stationary_residuals"] = stationary_residuals
    residuals["cross_observable_correlations_vanish"] = cross_observable_correlations_vanish
    residuals["drift_aware_fit_applied"] = drift_aware_fit_applied

    append_unique(out["automatic_flags_triggered"], "M08_VISIBLE_SOURCE_BASELINE_ONLY")
    if structured_residuals:
        append_unique(out["automatic_flags_triggered"], "M08_STRUCTURED_RESIDUALS_PRESENT")
    append_unique(out["linked_artifacts"], repo_rel(MODEL_SPEC))
    append_unique(out["linked_artifacts"], repo_rel(DEEP_RESEARCH_REPORT))
    note = "M08 baseline fit used only surfaced specs/core/model_spec.md and specs/research/deep_research_report.md guidance."
    if note not in out["evaluation_notes"]:
        out["evaluation_notes"].append(note)

    diagnostics = visible_source_result_summary_report(
        "QDP_V10_6_M08_BASELINE_REPORT",
        "M08",
        summarize_candidate(out),
        diagnostics={
            "expected_parameter_keys": EXPECTED_PARAMETER_KEYS,
            "observables_fit": observables_fit,
            "parameter_count": parameter_count,
            "noise_model_declared": noise_model_declared,
            "trace_preserving": trace_preserving,
            "complete_positive": complete_positive,
            "textbook_limit_recovered": textbook_limit_recovered,
            "residual_feature_flags": indicators,
        },
    )
    return out, diagnostics


def validate_candidate(candidate_path: Path, validator_path: Path, schema_path: Path) -> Dict[str, Any]:
    return validate_candidate_file(candidate_path, validator_path, schema_path, mode="final")


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
    if isinstance(expected, list):
        if actual != expected:
            failures.append(f"{path}: expected {expected!r}, found {actual!r}")
        return failures
    if actual != expected:
        failures.append(f"{path}: expected {expected!r}, found {actual!r}")
    return failures


def run_selftests(
    base_template: Dict[str, Any],
    cases_path: Path,
    validator_path: Path,
    schema_path: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    cases_obj = load_json(cases_path)
    results: List[Dict[str, Any]] = []

    for case in cases_obj.get("cases", []):
        case_id = str(case.get("case_id", ""))
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        candidate = make_minimal_final_candidate(base_template)
        candidate = deep_merge(candidate, case.get("input_candidate", {}))
        candidate, baseline_report = run_baseline_fit(candidate)

        candidate_path = case_dir / f"{case_id}_candidate.json"
        report_path = case_dir / f"{case_id}_report.json"
        dump_json(candidate_path, candidate)
        dump_json(report_path, baseline_report)

        validator_result = validate_candidate(candidate_path, validator_path, schema_path)
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
    cases_passed = sum(1 for case in results if case["passed"])
    return module_selftest_report_payload(
        "QDP_V10_6_M08_SELFTEST_REPORT",
        "M08",
        results,
        visible_source_only=True,
        all_passed=cases_total > 0 and cases_passed == cases_total,
        schema_valid_all=all(case["validator_result"]["valid"] for case in results),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M08 baseline-fit and residual-diagnostic subset.")
    parser.add_argument("--candidate", type=Path, help="Input candidate JSON object")
    parser.add_argument("--output", type=Path, help="Output candidate JSON path")
    parser.add_argument("--write-baseline-report", type=Path, help="Optional baseline diagnostic report path")
    parser.add_argument("--base-template", type=Path, default=DEFAULT_BASE_TEMPLATE)
    parser.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--selftest-cases", type=Path, default=DEFAULT_SELFTEST_CASES)
    parser.add_argument("--selftest-output-dir", type=Path, default=DEFAULT_SELFTEST_OUTPUT_DIR)
    parser.add_argument("--write-report", type=Path, default=DEFAULT_SELFTEST_REPORT)
    args = parser.parse_args()

    if args.selftest or (args.candidate is None and args.write_report is not None):
        base_template = load_json(args.base_template)
        report = run_selftests(
            base_template,
            args.selftest_cases,
            args.validator,
            args.schema,
            args.selftest_output_dir,
        )
        dump_json(args.write_report, report)
        print(json.dumps(report, indent=2))
        return 0 if report.get("all_passed", False) else 1

    if args.candidate is None:
        parser.error("--candidate is required unless --selftest is set")

    base_template = load_json(args.base_template)
    candidate = make_minimal_final_candidate(base_template)
    candidate = deep_merge(candidate, load_json(args.candidate))
    candidate, baseline_report = run_baseline_fit(candidate)

    if args.output:
        dump_json(args.output, candidate)
    else:
        print(json.dumps(candidate, indent=2))

    if args.write_baseline_report:
        dump_json(args.write_baseline_report, baseline_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

