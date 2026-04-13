#!/usr/bin/env python3
"""
QDP v10.6 M14 promotion-cap clipping and fallback completion.
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
from tools.workflow.qdp_runtime.qdp_governance import clip_candidate_with_caps, complete_governance_fallback, ensure_governance_structures, set_cross_device_status
from tools.workflow.qdp_runtime.qdp_paths import BASE_TEMPLATE, CANDIDATE_VALIDATOR, MODULES, SCHEMA
from tools.workflow.qdp_runtime.qdp_validation import validate_candidate_file


MODULE_PATHS = MODULES["m14"]
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
    candidate["candidate_id"] = candidate.get("candidate_id", "") or "M14_WORKING_PATCH_CANDIDATE"
    candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or "M14_WORKING_PATCH_BRANCH"
    ensure_governance_structures(candidate)
    return candidate


def run_promotion_caps(candidate: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    out = copy.deepcopy(candidate)
    governance_outcome_was_set = bool(str(out.get("governance_outcome", "") or "").strip())
    ensure_governance_structures(out)
    if not governance_outcome_was_set:
        out["governance_outcome"] = ""

    if not str(out.get("cross_device_status", "") or "").strip():
        if out.get("governance_outcome", "") in {"REJECT", "DEFER"}:
            set_cross_device_status(out, "NOT_REQUIRED", "Cross-device evidence is not required for terminal blocked states.")
        elif bool(out.get("multi_device_data_available", False)):
            set_cross_device_status(out, "DEVICE_SPECIFIC", "Cross-device state defaulted from available surfaced device data.")
        else:
            set_cross_device_status(out, "SCHEDULED", "Cross-device evidence remains scheduled.")

    clip_decisions = clip_candidate_with_caps(out)
    fallback_decision = complete_governance_fallback(out)
    if fallback_decision != "NO_CHANGE" and out.get("governance_outcome", "") in {"DEFER", "REJECT"}:
        set_cross_device_status(out, "NOT_REQUIRED", "Cross-device evidence is not required after fallback to a blocked state.")

    if not str(out.get("cross_device_status", "") or "").strip():
        if out.get("governance_outcome", "") in {"REJECT", "DEFER"}:
            set_cross_device_status(out, "NOT_REQUIRED")
        elif bool(out.get("multi_device_data_available", False)):
            set_cross_device_status(out, "DEVICE_SPECIFIC")
        else:
            set_cross_device_status(out, "SCHEDULED")

    diagnostics = candidate_result_summary_report(
        "QDP_V10_6_M14_REPORT",
        "M14",
        out.get("candidate_id", ""),
        {
            "scientific_decision": out.get("scientific_decision", ""),
            "governance_outcome": out.get("governance_outcome", ""),
            "cross_device_status": out.get("cross_device_status", ""),
            "promotion_cap_governance": out.get("promotion_cap_governance", ""),
            "promotion_cap_scientific": out.get("promotion_cap_scientific", ""),
            "clip_decisions": clip_decisions,
            "fallback_decision": fallback_decision,
        },
    )
    return out, diagnostics


def summarize_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "scientific_decision": candidate.get("scientific_decision", ""),
        "governance_outcome": candidate.get("governance_outcome", ""),
        "cross_device_status": candidate.get("cross_device_status", ""),
        "promotion_cap_governance": candidate.get("promotion_cap_governance", ""),
        "promotion_cap_scientific": candidate.get("promotion_cap_scientific", ""),
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
        candidate, report = run_promotion_caps(candidate)
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
        "QDP_V10_6_M14_SELFTEST_REPORT",
        "M14",
        results,
        visible_source_only=True,
        all_passed=cases_total > 0 and cases_passed == cases_total,
        schema_valid_all=all(result["validator_result"]["valid"] for result in results),
    )
    dump_json(write_report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M14 promotion-cap manager.")
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
        raise SystemExit("M14 run requires --candidate unless --selftest is set.")

    candidate = load_json(args.candidate)
    out_candidate, report = run_promotion_caps(candidate)
    if args.output:
        dump_json(args.output, out_candidate)
    else:
        print(json.dumps(out_candidate, indent=2))
    if args.write_report:
        dump_json(args.write_report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

