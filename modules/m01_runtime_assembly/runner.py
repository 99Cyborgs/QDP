#!/usr/bin/env python3
"""
QDP v10.6 M01 runtime assembly and provenance capture.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = REPO_ROOT / "packages" / "qdp_io" / "src"
for path in (REPO_ROOT, QDP_IO_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_io.artifacts import dump_json, module_report_header, module_selftest_report_payload, sha256_file, utc_now
from qdp_io.reference_manifest import (
    RETAINED_RUNTIME_REF_ID,
    find_reference_entry,
    reference_is_reconstructed_surrogate,
)
from qdp_io.serialization import load_json as load_any_json
from tools.workflow.qdp_runtime.qdp_paths import M01_ASSEMBLY_REPORT, M01_CLOSURE_REPORT, MODULES, REFERENCE_MANIFEST, RETAINED_OPERATIVE_BODY, RUNTIME_PROMPT, SURROGATE_OPERATIVE_BODY


MODULE_PATHS = MODULES["m01"]
DEFAULT_SELFTEST_CASES = MODULE_PATHS["selftest_cases"]
DEFAULT_SELFTEST_REPORT = MODULE_PATHS["selftest_report"]
DEFAULT_SELFTEST_OUTPUT_DIR = MODULE_PATHS["selftest_output_dir"]


def load_json(path: Path) -> Dict[str, object]:
    data = load_any_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def derive_runtime_state(
    manifest: Dict[str, object],
    runtime_prompt_path: Path,
    retained_runtime_path: Path,
    surrogate_runtime_path: Path,
    *,
    retained_provenance_override: str = "",
    runtime_prompt_exists_override: bool | None = None,
    retained_runtime_exists_override: bool | None = None,
    surrogate_runtime_exists_override: bool | None = None,
) -> Dict[str, object]:
    retained_entry = find_reference_entry(manifest, RETAINED_RUNTIME_REF_ID)
    retained_provenance = retained_provenance_override or str(retained_entry.get("provenance", "") or "missing")
    runtime_prompt_exists = runtime_prompt_path.exists() if runtime_prompt_exists_override is None else runtime_prompt_exists_override
    retained_runtime_exists = retained_runtime_path.exists() if retained_runtime_exists_override is None else retained_runtime_exists_override
    surrogate_runtime_exists = surrogate_runtime_path.exists() if surrogate_runtime_exists_override is None else surrogate_runtime_exists_override
    retained_authoritative = retained_runtime_exists and not reference_is_reconstructed_surrogate(
        {"provenance": retained_provenance}
    )

    if retained_authoritative and runtime_prompt_exists:
        lane = "AUTHORITATIVE_LANE"
        derived_status = "AUTHORITATIVE_CLOSURE"
    elif runtime_prompt_exists and (retained_runtime_exists or surrogate_runtime_exists):
        lane = "RECOVERY_LANE"
        derived_status = "RECOVERY_INTERIM"
    else:
        lane = "BLOCKED"
        derived_status = "BLOCKED"

    return {
        "runtime_prompt_exists": runtime_prompt_exists,
        "retained_runtime_exists": retained_runtime_exists,
        "surrogate_runtime_exists": surrogate_runtime_exists,
        "retained_runtime_source_provenance": retained_provenance,
        "retained_runtime_source_authoritative": retained_authoritative,
        "lane": lane,
        "derived_status": derived_status,
    }


def build_reports(
    manifest: Dict[str, object],
    runtime_prompt_path: Path,
    retained_runtime_path: Path,
    surrogate_runtime_path: Path,
    *,
    retained_provenance_override: str = "",
    runtime_prompt_exists_override: bool | None = None,
    retained_runtime_exists_override: bool | None = None,
    surrogate_runtime_exists_override: bool | None = None,
) -> tuple[Dict[str, object], Dict[str, object]]:
    state = derive_runtime_state(
        manifest,
        runtime_prompt_path,
        retained_runtime_path,
        surrogate_runtime_path,
        retained_provenance_override=retained_provenance_override,
        runtime_prompt_exists_override=runtime_prompt_exists_override,
        retained_runtime_exists_override=retained_runtime_exists_override,
        surrogate_runtime_exists_override=surrogate_runtime_exists_override,
    )
    retained_source_path = retained_runtime_path if state["retained_runtime_exists"] else surrogate_runtime_path
    assembly_report = {
        **module_report_header("QDP_V10_6_M01_ASSEMBLY_REPORT", "M01"),
        "runtime_prompt_path": str(runtime_prompt_path),
        "runtime_prompt_exists": state["runtime_prompt_exists"],
        "runtime_prompt_sha256": sha256_file(runtime_prompt_path) if state["runtime_prompt_exists"] and runtime_prompt_path.exists() else "",
        "retained_runtime_source_path": str(retained_source_path),
        "retained_runtime_source_exists": state["retained_runtime_exists"] or state["surrogate_runtime_exists"],
        "retained_runtime_source_provenance": state["retained_runtime_source_provenance"],
        "retained_runtime_source_authoritative": state["retained_runtime_source_authoritative"],
        "assembly_lane": state["lane"],
        "derived_status": state["derived_status"],
        "notes": [
            "M01 records runtime provenance and lane assignment for recovery versus authoritative execution.",
            "A reconstructed_surrogate retained source keeps this module in recovery-interim status even when the runtime prompt exists."
        ]
    }
    closure_report = {
        **module_report_header("QDP_V10_6_M01_CLOSURE_REPORT", "M01"),
        "runtime_prompt_path": str(runtime_prompt_path),
        "runtime_prompt_sha256": assembly_report["runtime_prompt_sha256"],
        "retained_runtime_source_path": str(retained_source_path),
        "retained_runtime_source_provenance": state["retained_runtime_source_provenance"],
        "retained_runtime_source_authoritative": state["retained_runtime_source_authoritative"],
        "assembly_lane": state["lane"],
        "derived_status": state["derived_status"],
        "notes": [
            "This closure report is provenance-aware and does not upgrade surrogate-retained recovery to authoritative closure."
        ]
    }
    return assembly_report, closure_report


def compare_expected(actual: Dict[str, object], expected: Dict[str, object]) -> List[str]:
    failures: List[str] = []
    for key, value in expected.items():
        if actual.get(key) != value:
            failures.append(f"{key}: expected {value!r}, found {actual.get(key)!r}")
    return failures


def run_selftests(
    cases_path: Path,
    manifest_path: Path,
    runtime_prompt_path: Path,
    retained_runtime_path: Path,
    surrogate_runtime_path: Path,
    output_dir: Path,
    write_report_path: Path,
) -> Dict[str, object]:
    cases_obj = load_json(cases_path)
    manifest = load_json(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, object]] = []

    for case in cases_obj.get("cases", []):
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip() or "UNNAMED_CASE"
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        assembly_report, closure_report = build_reports(
            manifest,
            runtime_prompt_path,
            retained_runtime_path,
            surrogate_runtime_path,
            retained_provenance_override=str(case.get("retained_runtime_source_provenance", "") or ""),
            runtime_prompt_exists_override=case.get("runtime_prompt_exists"),
            retained_runtime_exists_override=case.get("retained_runtime_exists"),
            surrogate_runtime_exists_override=case.get("surrogate_runtime_exists"),
        )
        assembly_path = case_dir / f"{case_id}_assembly_report.json"
        closure_path = case_dir / f"{case_id}_closure_report.json"
        dump_json(assembly_path, assembly_report)
        dump_json(closure_path, closure_report)
        actual_summary = {
            "assembly_lane": assembly_report.get("assembly_lane", ""),
            "derived_status": closure_report.get("derived_status", ""),
            "retained_runtime_source_authoritative": closure_report.get("retained_runtime_source_authoritative", False),
        }
        expected_summary = case.get("expected", {})
        comparison_failures = compare_expected(actual_summary, expected_summary)
        passed = not comparison_failures
        results.append(
            {
                "case_id": case_id,
                "description": case.get("description", ""),
                "passed": passed,
                "comparison_ok": passed,
                "comparison_failures": comparison_failures,
                "expected_summary": expected_summary,
                "actual_summary": actual_summary,
                "assembly_report_path": str(assembly_path),
                "closure_report_path": str(closure_path),
            }
        )

    cases_total = len(results)
    cases_passed = sum(1 for result in results if result["passed"])
    report = module_selftest_report_payload(
        "QDP_V10_6_M01_SELFTEST_REPORT",
        "M01",
        results,
        all_passed=cases_total > 0 and cases_passed == cases_total,
    )
    dump_json(write_report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M01 runtime assembly module.")
    parser.add_argument("--manifest", type=Path, default=REFERENCE_MANIFEST)
    parser.add_argument("--runtime-prompt", type=Path, default=RUNTIME_PROMPT)
    parser.add_argument("--retained-runtime-source", type=Path, default=RETAINED_OPERATIVE_BODY)
    parser.add_argument("--surrogate-runtime-source", type=Path, default=SURROGATE_OPERATIVE_BODY)
    parser.add_argument("--base-template", type=Path)
    parser.add_argument("--validator", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--write-report", type=Path, default=M01_ASSEMBLY_REPORT)
    parser.add_argument("--write-closure-report", type=Path, default=M01_CLOSURE_REPORT)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--selftest-cases", type=Path, default=DEFAULT_SELFTEST_CASES)
    parser.add_argument("--selftest-output-dir", type=Path, default=DEFAULT_SELFTEST_OUTPUT_DIR)
    args = parser.parse_args()

    if args.selftest:
        report = run_selftests(
            args.selftest_cases,
            args.manifest,
            args.runtime_prompt,
            args.retained_runtime_source,
            args.surrogate_runtime_source,
            args.selftest_output_dir,
            args.write_report,
        )
        print(json.dumps(report, indent=2))
        return 0 if report.get("all_passed", False) else 1

    manifest = load_json(args.manifest)
    assembly_report, closure_report = build_reports(
        manifest,
        args.runtime_prompt,
        args.retained_runtime_source,
        args.surrogate_runtime_source,
    )
    dump_json(args.write_report, assembly_report)
    dump_json(args.write_closure_report, closure_report)
    print(json.dumps(assembly_report, indent=2))
    return 0 if closure_report.get("derived_status") in {"AUTHORITATIVE_CLOSURE", "RECOVERY_INTERIM"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

