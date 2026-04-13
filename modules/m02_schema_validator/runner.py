#!/usr/bin/env python3
"""
QDP v10.6 M02 schema extension and validator contract module.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
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

from qdp_io.artifacts import dump_json, module_report_header, module_selftest_report_payload, utc_now
from tools.workflow.qdp_runtime.qdp_governance import ensure_governance_structures
from tools.workflow.qdp_runtime.qdp_paths import BASE_TEMPLATE, CANDIDATE_VALIDATOR, MODULES, SCHEMA
from tools.workflow.qdp_runtime.qdp_validation import validate_candidate_file, validate_candidate_instance


MODULE_PATHS = MODULES["m02"]
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


def load_validator_module(path: Path):
    spec = importlib.util.spec_from_file_location("qdp_m02_validator_contract", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import validator module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_minimal_final_candidate(base_template: Dict[str, Any]) -> Dict[str, Any]:
    candidate = copy.deepcopy(base_template)
    candidate["candidate_id"] = candidate.get("candidate_id", "") or "M02_WORKING_PATCH_CANDIDATE"
    candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or "M02_WORKING_PATCH_BRANCH"
    ensure_governance_structures(candidate)
    return candidate


def contract_checks(base_template_path: Path, validator_path: Path, schema_path: Path) -> Dict[str, Any]:
    template = load_json(base_template_path)
    schema = load_json(schema_path)
    validator_module = load_validator_module(validator_path)
    required_typed_fields = ["calibration_status", "identifiability_status", "drift_ledger", "dataset_governance"]
    template_check = validate_candidate_instance(template, validator_path, schema_path, mode="template")
    validator_enums = {
        "calibration_status": set(getattr(validator_module, "CALIBRATION_STATUS_VALUES", set())),
        "identifiability_status": set(getattr(validator_module, "IDENTIFIABILITY_STATUS_VALUES", set())),
        "drift_ledger": set(getattr(validator_module, "DRIFT_STATUS_VALUES", set())),
        "dataset_governance": set(getattr(validator_module, "DATASET_GOVERNANCE_STATUS_VALUES", set())),
    }
    enum_mirror_ok = True
    enum_details: Dict[str, Any] = {}
    for field in required_typed_fields:
        schema_values = set(schema.get("properties", {}).get(field, {}).get("properties", {}).get("status", {}).get("enum", []))
        enum_details[field] = {
            "schema": sorted(schema_values),
            "validator": sorted(validator_enums.get(field, set())),
        }
        if schema_values != validator_enums.get(field, set()):
            enum_mirror_ok = False

    return {
        "template_validation": template_check,
        "typed_fields_present_in_template": all(field in template for field in required_typed_fields),
        "typed_fields_present_in_schema": all(field in schema.get("properties", {}) for field in required_typed_fields),
        "typed_fields_required_in_schema": all(field in schema.get("required", []) for field in required_typed_fields),
        "validator_exports_present": all(hasattr(validator_module, name) for name in ["schema_validate", "semantic_validate"]),
        "enum_mirror_ok": enum_mirror_ok,
        "enum_details": enum_details,
    }


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
    contract = contract_checks(base_template_path, validator_path, schema_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []

    for case in cases_obj.get("cases", []):
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip() or "UNNAMED_CASE"
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        candidate = deep_merge(make_minimal_final_candidate(base_template), case.get("candidate_overrides", {}))
        candidate_path = case_dir / f"{case_id}_candidate.json"
        dump_json(candidate_path, candidate)
        validator_result = validate_candidate_file(candidate_path, validator_path, schema_path, mode="final")
        expect_valid = bool(case.get("expect_valid", False))
        error_fragments = [str(item) for item in case.get("expected_error_fragments", [])]
        error_match = all(any(fragment in err for err in validator_result.get("errors", [])) for fragment in error_fragments)
        passed = validator_result["valid"] == expect_valid and error_match
        results.append(
            {
                "case_id": case_id,
                "description": case.get("description", ""),
                "passed": passed,
                "expected_valid": expect_valid,
                "actual_valid": validator_result["valid"],
                "error_match": error_match,
                "expected_error_fragments": error_fragments,
                "validator_result": validator_result,
                "output_candidate_path": str(candidate_path),
            }
        )

    cases_total = len(results)
    cases_passed = sum(1 for result in results if result["passed"])
    report = module_selftest_report_payload(
        "QDP_V10_6_M02_SELFTEST_REPORT",
        "M02",
        results,
        visible_source_only=True,
        metadata={"contract_checks": contract},
        all_passed=(
            cases_total > 0
            and cases_passed == cases_total
            and contract["template_validation"]["valid"]
            and contract["typed_fields_present_in_template"]
            and contract["typed_fields_present_in_schema"]
            and contract["typed_fields_required_in_schema"]
            and contract["validator_exports_present"]
            and contract["enum_mirror_ok"]
        ),
        schema_valid_all=all((result["actual_valid"] if result["expected_valid"] else True) for result in results),
    )
    dump_json(write_report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M02 schema-validator module.")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--base-template", type=Path, default=DEFAULT_BASE_TEMPLATE)
    parser.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--write-report", type=Path, default=DEFAULT_SELFTEST_REPORT)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--selftest-cases", type=Path, default=DEFAULT_SELFTEST_CASES)
    parser.add_argument("--selftest-output-dir", type=Path, default=DEFAULT_SELFTEST_OUTPUT_DIR)
    args = parser.parse_args()

    if args.selftest:
        report = run_selftests(args.selftest_cases, args.base_template, args.validator, args.schema, args.selftest_output_dir, args.write_report)
        print(json.dumps(report, indent=2))
        return 0 if report.get("all_passed", False) else 1

    report = {
        **module_report_header("QDP_V10_6_M02_REPORT", "M02"),
        "contract_checks": contract_checks(args.base_template, args.validator, args.schema),
    }
    if args.candidate:
        report["candidate_validation"] = validate_candidate_file(args.candidate, args.validator, args.schema, mode="final")
    dump_json(args.write_report, report)
    print(json.dumps(report, indent=2))
    if args.candidate:
        return 0 if report["candidate_validation"]["valid"] else 1
    contract = report["contract_checks"]
    return 0 if (
        contract["template_validation"]["valid"]
        and contract["typed_fields_present_in_template"]
        and contract["typed_fields_present_in_schema"]
        and contract["typed_fields_required_in_schema"]
        and contract["validator_exports_present"]
        and contract["enum_mirror_ok"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())

