#!/usr/bin/env python3
"""
QDP v10.6 M10 artifact-equivalence audit.

This is a visible-source working-patch implementation derived from
specs/research/deep_research_report.md and the surfaced fork-intake artifact set. It fills
artifact_tests conservatively without claiming parity with unsurfaced retained
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
from tools.workflow.qdp_runtime.qdp_paths import BASE_TEMPLATE, CANDIDATE_VALIDATOR, DEEP_RESEARCH_REPORT, FORK_INTAKE_FORM, MODULES, SCHEMA, repo_rel
from tools.workflow.qdp_runtime.qdp_validation import validate_candidate_file


MODULE_PATHS = MODULES["m10"]
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

M10_OWNER_ARTIFACTS = {
    repo_rel(DEEP_RESEARCH_REPORT): DEEP_RESEARCH_REPORT,
    repo_rel(FORK_INTAKE_FORM): FORK_INTAKE_FORM,
    repo_rel(BASE_TEMPLATE): BASE_TEMPLATE,
}

GENERIC_NEGATIVE_TERMS = [
    "did not change",
    "did not move",
    "did not remove",
    "did not eliminate",
    "no artifact route",
    "artifact route remains unsupported",
    "survived recalibration",
    "survived readout power sweep",
    "survived filtering swap",
    "survived attenuation swap",
]

ARTIFACT_RULES: List[Dict[str, Any]] = [
    {
        "name": "CONTROL_CHAIN_DISTORTION",
        "field": "control_chain_distortion",
        "primary_terms": [
            "pulse distortion",
            "line attenuation",
            "attenuation swap",
            "filter swap",
            "line filtering",
            "microwave chain",
            "control chain",
            "classical distortion",
            "am/pm noise",
        ],
        "supporting_terms": [
            "control-line",
            "wiring",
            "filter-function",
            "noise spectroscopy",
        ],
        "trigger_flags": [
            "attenuation_swap_changes_signal",
            "filter_swap_changes_signal",
            "pulse_shape_variation_changes_signal",
            "distortion_measurement_matches_anomaly",
            "control_chain_setting_moves_peak",
        ],
        "minimum_discriminator": "Swap line filtering and attenuation, vary pulse shapes, and verify whether the anomaly follows measured chain distortion at the device.",
    },
    {
        "name": "READOUT_ALIAS",
        "field": "readout_alias",
        "primary_terms": [
            "readout nonlinearity",
            "digitizer saturation",
            "amplifier compression",
            "readout alias",
            "readout chain",
            "spam",
        ],
        "supporting_terms": [
            "readout power",
            "measurement chain",
            "dispersive fit artifact",
            "readout gain",
        ],
        "trigger_flags": [
            "readout_relinearization_removes_effect",
            "digitizer_linearity_failure_detected",
            "readout_power_only_dependency",
            "readout_gain_swap_changes_signal",
        ],
        "minimum_discriminator": "Sweep readout power and gain, check digitizer linearity, and re-fit with a relinearized readout model to see whether the anomaly disappears.",
    },
    {
        "name": "CALIBRATION_DRIFT",
        "field": "calibration_drift",
        "primary_terms": [
            "calibration drift",
            "same-day recalibration",
            "drift ledger",
            "recalibration removes",
            "gain drift",
            "frequency drift",
            "recalibration",
        ],
        "supporting_terms": [
            "drift",
            "retune",
            "interleaved calibration",
            "calibrated again",
        ],
        "trigger_flags": [
            "recalibration_eliminates_effect",
            "drift_replay_matches_anomaly",
            "calibration_drift_detected",
            "interleaved_calibration_breaks_effect",
        ],
        "minimum_discriminator": "Repeat the measurement with interleaved calibrations and a drift ledger to see whether recalibration removes the apparent anomaly.",
    },
    {
        "name": "REFRIGERATOR_CYCLE_ALIAS",
        "field": "refrigerator_cycle_alias",
        "primary_terms": [
            "pulse-tube cycle",
            "pulse tube cycle",
            "cryocooler cycle",
            "mechanical cycle",
            "phase-locked to pulse-tube",
            "phase-locked to pulse tube",
            "synchronized to pulse-tube",
            "synchronized to pulse tube",
            "classical heating",
        ],
        "supporting_terms": [
            "pulse tube",
            "pulse-tube",
            "vibration environment",
            "fridge cycle",
            "hold-time control",
        ],
        "trigger_flags": [
            "pulse_tube_sync_detected",
            "mechanical_cycle_phase_lock_detected",
            "hold_time_removes_effect",
        ],
        "minimum_discriminator": "Phase-bin the data against the pulse-tube or cryocooler cycle and test hold-time dependence to see whether the signal is a refrigerator alias.",
    },
    {
        "name": "POWER_CALIBRATION_ALIAS",
        "field": "power_calibration_alias",
        "primary_terms": [
            "in-situ power",
            "room-temperature generator settings",
            "power calibration",
            "attenuation map",
            "device power mismatch",
            "generator setting",
        ],
        "supporting_terms": [
            "amplitude dependence",
            "device power",
            "calibrated power",
            "attenuation chain",
        ],
        "trigger_flags": [
            "in_situ_power_mismatch_detected",
            "power_recalibration_eliminates_effect",
            "generator_setting_alias_detected",
        ],
        "minimum_discriminator": "Calibrate in-situ device power instead of generator settings and repeat the amplitude sweep across a checked attenuation map.",
    },
]


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


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().upper() in {"TRUE", "YES", "1", "PASS", "PASSED", "READY"}
    return False


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


def append_unique(items: List[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


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


def contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def match_terms(text: str, terms: List[str]) -> List[str]:
    return [term for term in terms if term in text]


def artifact_inputs(candidate: Dict[str, Any]) -> Dict[str, Any]:
    raw = candidate.get("artifact_audit_inputs", {})
    return copy.deepcopy(raw) if isinstance(raw, dict) else {}


def evidence_text(candidate: Dict[str, Any]) -> str:
    parts: List[str] = []
    parts.extend(list_of_strings(candidate.get("evaluation_notes", [])))
    parts.extend(list_of_strings(candidate.get("relevant_nuisance_controls_list", [])))
    parts.extend(list_of_strings(candidate.get("failure_modes", [])))
    parts.extend(list_of_strings(candidate.get("failure_mode_library_hits", [])))
    parts.extend(list_of_strings(candidate.get("signature_matches", [])))
    for key in [
        "primary_observable",
        "secondary_observable",
        "assigned_family_class",
        "declared_family_class",
        "declared_likely_bath_class",
    ]:
        value = str(candidate.get(key, "") or "").strip()
        if value:
            parts.append(value)
    inputs = artifact_inputs(candidate)
    for key in ["notes", "summary", "artifact_hypothesis", "control_summary"]:
        value = str(inputs.get(key, "") or "").strip()
        if value:
            parts.append(value)
    parts.extend(list_of_strings(inputs.get("evidence_notes", [])))
    return " ".join(parts).lower()


def make_minimal_final_candidate(base_template: Dict[str, Any]) -> Dict[str, Any]:
    candidate = copy.deepcopy(base_template)
    candidate["candidate_id"] = candidate.get("candidate_id", "") or "M10_WORKING_PATCH_CANDIDATE"
    candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or "M10_WORKING_PATCH_BRANCH"
    candidate["governance_self_check"] = copy.deepcopy(READY_SELF_CHECK)
    candidate["system_status"] = "READY"
    candidate["scientific_decision"] = "NOT_EVALUATED"
    candidate["governance_outcome"] = "DEFER"
    candidate["cross_device_status"] = "NOT_REQUIRED"
    candidate.setdefault("cross_device_validation", {})
    candidate["cross_device_validation"]["status"] = "NOT_REQUIRED"
    candidate["promotion_cap_governance"] = ""
    candidate["promotion_cap_scientific"] = ""
    candidate["artifact_tests"] = {}
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
    candidate.setdefault("artifact_tests", {})
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("gate_trace", [])


def initial_status(explains_data: bool, primary_hits: List[str], primary_flags: List[str], support_score: float, negative: bool) -> str:
    if explains_data:
        return "EXPLAINS_DATA"
    if negative and not primary_flags:
        return "SUPPORTING" if support_score > 0 else "NOT_SUPPORTED"
    if primary_hits or primary_flags:
        return "PRIMARY_DISCRIMINANT"
    if support_score > 0:
        return "SUPPORTING"
    return "NOT_SUPPORTED"


def control_chain_explains(text: str, primary_flags: List[str]) -> bool:
    explicit = contains_any(
        text,
        [
            "tracks the control chain",
            "follows the control chain",
            "moves with attenuation",
            "moves with the microwave chain",
            "account for the shift",
            "account for the amplitude dependence",
        ],
    )
    strong_context = sum(
        1
        for term in ["pulse distortion", "line attenuation", "attenuation swap", "filter swap", "control chain", "microwave chain"]
        if term in text
    ) >= 2
    return bool(primary_flags) and (strong_context or explicit)


def readout_alias_explains(text: str, primary_flags: List[str]) -> bool:
    explicit = contains_any(
        text,
        [
            "relinearized readout removed",
            "readout nonlinearity removed",
            "digitizer saturation removed",
            "reduced readout power removed",
            "readout gain swap removed",
        ],
    )
    return bool(primary_flags) or explicit


def calibration_drift_explains(text: str, primary_flags: List[str]) -> bool:
    explicit = contains_any(
        text,
        [
            "recalibration removes",
            "recalibration removed",
            "recalibration eliminates",
            "same-day recalibration",
            "drift ledger replay",
        ],
    ) and contains_any(text, ["remove", "removed", "eliminate", "eliminates", "matches"])
    return bool(primary_flags) or explicit


def refrigerator_alias_explains(text: str, primary_flags: List[str]) -> bool:
    explicit = contains_any(
        text,
        [
            "phase-locked to pulse-tube",
            "synchronized to pulse-tube",
            "pulse-tube cycle explains",
            "cryocooler cycle explains",
            "hold-time removes the effect",
        ],
    )
    return bool(primary_flags) or explicit


def power_alias_explains(text: str, primary_flags: List[str]) -> bool:
    explicit = contains_any(text, ["in-situ power", "device power mismatch"]) and contains_any(
        text,
        [
            "generator settings",
            "room-temperature generator settings",
            "power calibration",
            "attenuation map",
            "removed the amplitude dependence",
            "account for the amplitude dependence",
        ],
    )
    return bool(primary_flags) or explicit


def evaluate_artifact_rule(rule: Dict[str, Any], candidate: Dict[str, Any], text: str) -> Dict[str, Any]:
    inputs = artifact_inputs(candidate)
    primary_term_hits = match_terms(text, rule["primary_terms"])
    supporting_term_hits = match_terms(text, rule["supporting_terms"])
    primary_flag_hits = [flag for flag in rule["trigger_flags"] if bool_value(inputs.get(flag, False))]
    negative = contains_any(text, GENERIC_NEGATIVE_TERMS)

    support_score = float(
        3 * len(primary_flag_hits)
        + 2 * len(primary_term_hits)
        + len(supporting_term_hits)
    )

    name = rule["name"]
    if name == "CONTROL_CHAIN_DISTORTION":
        explains_data = control_chain_explains(text, primary_flag_hits) and not negative
    elif name == "READOUT_ALIAS":
        explains_data = readout_alias_explains(text, primary_flag_hits) and not negative
    elif name == "CALIBRATION_DRIFT":
        explains_data = calibration_drift_explains(text, primary_flag_hits) and not negative
    elif name == "REFRIGERATOR_CYCLE_ALIAS":
        local_negative = contains_any(
            text,
            [
                "no pulse-tube synchronization",
                "no pulse tube synchronization",
                "not phase-binned",
                "not yet phase-binned",
                "has not been run",
                "hasn't been run",
                "not synchronized",
                "not yet run",
                "no phase locking",
            ],
        )
        explains_data = refrigerator_alias_explains(text, primary_flag_hits) and not (negative or local_negative)
        if local_negative and not primary_flag_hits and support_score > 0:
            support_score = max(support_score, 1.0)
    elif name == "POWER_CALIBRATION_ALIAS":
        explains_data = power_alias_explains(text, primary_flag_hits) and not negative
    else:
        explains_data = False

    status = initial_status(explains_data, primary_term_hits, primary_flag_hits, support_score, negative)
    return {
        "status": status,
        "support_score": round(support_score, 6),
        "explains_data": explains_data,
        "primary_term_hits": unique_preserve(primary_term_hits),
        "supporting_term_hits": unique_preserve(supporting_term_hits),
        "primary_flag_hits": unique_preserve(primary_flag_hits),
        "minimal_discriminant_measurement": rule["minimum_discriminator"],
    }


def summarize_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    tests = candidate.get("artifact_tests", {})
    return {
        "artifact_tests": {
            "strongest_artifact_route_initial": tests.get("strongest_artifact_route_initial", ""),
            "strongest_artifact_route": tests.get("strongest_artifact_route", ""),
            "route_explains_data": tests.get("route_explains_data", False),
            "explains_data": tests.get("explains_data", False),
            "parsimonious_combination_explains": tests.get("parsimonious_combination_explains", False),
            "parsimonious_combination_label": tests.get("parsimonious_combination_label", ""),
            "control_chain_distortion": {
                "status": tests.get("control_chain_distortion", {}).get("status", ""),
                "explains_data": tests.get("control_chain_distortion", {}).get("explains_data", False),
            },
            "readout_alias": {
                "status": tests.get("readout_alias", {}).get("status", ""),
                "explains_data": tests.get("readout_alias", {}).get("explains_data", False),
            },
            "calibration_drift": {
                "status": tests.get("calibration_drift", {}).get("status", ""),
                "explains_data": tests.get("calibration_drift", {}).get("explains_data", False),
            },
            "refrigerator_cycle_alias": {
                "status": tests.get("refrigerator_cycle_alias", {}).get("status", ""),
                "explains_data": tests.get("refrigerator_cycle_alias", {}).get("explains_data", False),
            },
            "power_calibration_alias": {
                "status": tests.get("power_calibration_alias", {}).get("status", ""),
                "explains_data": tests.get("power_calibration_alias", {}).get("explains_data", False),
            },
        }
    }


def run_artifact_audit(candidate: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    out = copy.deepcopy(candidate)
    ensure_candidate_defaults(out)
    text = evidence_text(out)

    tests = out["artifact_tests"] = {}
    tests["visible_source_partial_suite"] = True
    tests["surfaced_source_artifacts"] = [
        repo_rel(DEEP_RESEARCH_REPORT),
        repo_rel(FORK_INTAKE_FORM),
        repo_rel(BASE_TEMPLATE),
    ]
    tests["missing_owner_artifacts"] = [name for name, path in M10_OWNER_ARTIFACTS.items() if not path.exists()]

    results_by_name: Dict[str, Dict[str, Any]] = {}
    support_ranking: List[Tuple[str, float]] = []
    explainers: List[Tuple[str, float]] = []
    for rule in ARTIFACT_RULES:
        result = evaluate_artifact_rule(rule, out, text)
        tests[rule["field"]] = result
        results_by_name[rule["name"]] = result
        support_ranking.append((rule["name"], result["support_score"]))
        if result["explains_data"]:
            explainers.append((rule["name"], result["support_score"]))

    strongest_initial = ""
    if support_ranking:
        best_name, best_score = max(support_ranking, key=lambda item: item[1])
        if best_score > 0:
            strongest_initial = best_name
    tests["strongest_artifact_route_initial"] = strongest_initial

    parsimonious_combination_explains = False
    parsimonious_combination_label = ""
    if (
        results_by_name["CONTROL_CHAIN_DISTORTION"]["explains_data"]
        and results_by_name["POWER_CALIBRATION_ALIAS"]["explains_data"]
        and contains_any(text, ["amplitude dependence", "generator settings", "in-situ power", "attenuation map"])
    ):
        parsimonious_combination_explains = True
        parsimonious_combination_label = "CONTROL_CHAIN_POWER_ALIAS"

    tests["parsimonious_combination_explains"] = parsimonious_combination_explains
    tests["parsimonious_combination_label"] = parsimonious_combination_label
    tests["route_explains_data"] = bool(explainers) or parsimonious_combination_explains
    tests["explains_data"] = tests["route_explains_data"]

    if parsimonious_combination_explains:
        strongest_route = parsimonious_combination_label
    elif explainers:
        strongest_route = max(explainers, key=lambda item: item[1])[0]
    else:
        strongest_route = ""
    tests["strongest_artifact_route"] = strongest_route

    alias_summary = [
        name
        for name, _score in sorted(support_ranking, key=lambda item: (-item[1], item[0]))
        if results_by_name[name]["status"] != "NOT_SUPPORTED"
    ]
    tests["alias_summary"] = alias_summary

    append_unique(out["automatic_flags_triggered"], "M10_VISIBLE_SOURCE_ARTIFACT_AUDIT")
    if tests["route_explains_data"]:
        append_unique(out["automatic_flags_triggered"], "M10_ARTIFACT_ROUTE_SURFACED")
    append_unique(out["linked_artifacts"], repo_rel(DEEP_RESEARCH_REPORT))
    if FORK_INTAKE_FORM.exists():
        append_unique(out["linked_artifacts"], repo_rel(FORK_INTAKE_FORM))
    note = "M10 artifact-equivalence auditing used only surfaced visible-source artifact-elimination cues and candidate nuisance-control fields."
    if note not in out["evaluation_notes"]:
        out["evaluation_notes"].append(note)

    diagnostics = visible_source_result_summary_report(
        "QDP_V10_6_M10_ARTIFACT_AUDIT_REPORT",
        "M10",
        summarize_candidate(out),
        diagnostics={
            "evidence_text_sample": text[:700],
            "missing_owner_artifacts": tests["missing_owner_artifacts"],
            "alias_summary": alias_summary,
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
        candidate, artifact_report = run_artifact_audit(candidate)

        candidate_path = case_dir / f"{case_id}_candidate.json"
        report_path = case_dir / f"{case_id}_report.json"
        dump_json(candidate_path, candidate)
        dump_json(report_path, artifact_report)

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
        "QDP_V10_6_M10_SELFTEST_REPORT",
        "M10",
        results,
        visible_source_only=True,
        all_passed=cases_total > 0 and cases_passed == cases_total,
        schema_valid_all=all(case["validator_result"]["valid"] for case in results),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M10 artifact-equivalence audit subset.")
    parser.add_argument("--candidate", type=Path, help="Input candidate JSON object")
    parser.add_argument("--output", type=Path, help="Output candidate JSON path")
    parser.add_argument("--write-artifact-report", type=Path, help="Optional artifact report path")
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
    candidate, artifact_report = run_artifact_audit(candidate)

    if args.output:
        dump_json(args.output, candidate)
    else:
        print(json.dumps(candidate, indent=2))
    if args.write_artifact_report:
        dump_json(args.write_artifact_report, artifact_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

