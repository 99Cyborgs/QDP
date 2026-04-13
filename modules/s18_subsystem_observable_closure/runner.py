#!/usr/bin/env python3
"""
QDP subsystem S18 finite-horizon and observable-closure module.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from tools.workflow.qdp_runtime.qdp_paths import GKSL_SUBSYSTEM_CASE_MATRIX, MODULES, SUBSYSTEM_VERDICT_SCHEMA
from tools.workflow.qdp_runtime.qdp_subsystem import get_case, load_matrix, observable_closure_payload, run_selftests as run_subsystem_selftests, summarize_payload


MODULE_PATHS = MODULES["s18"]


def run_subsystem_module(case_id: str, matrix_path: Path = GKSL_SUBSYSTEM_CASE_MATRIX) -> tuple[Dict[str, Any], Dict[str, Any]]:
    matrix = load_matrix(matrix_path)
    case = get_case(matrix, case_id)
    payload = observable_closure_payload(case, MODULE_PATHS["module_id"])
    report = {
        "artifact_id": "QDP_V10_6_S18_REPORT",
        "module_id": MODULE_PATHS["module_id"],
        "case_id": case_id,
        "result_summary": summarize_payload(payload),
    }
    return payload, report


def run_selftests(cases_path: Path, matrix_path: Path, schema_path: Path, output_dir: Path, write_report_path: Path) -> Dict[str, Any]:
    return run_subsystem_selftests(
        module_id=MODULE_PATHS["module_id"],
        cases_path=cases_path,
        matrix_path=matrix_path,
        schema_path=schema_path,
        output_dir=output_dir,
        write_report_path=write_report_path,
        payload_builder=observable_closure_payload,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP subsystem S18 observable-closure module.")
    parser.add_argument("--case-id")
    parser.add_argument("--matrix", type=Path, default=GKSL_SUBSYSTEM_CASE_MATRIX)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write-report", type=Path, default=MODULE_PATHS["selftest_report"])
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--selftest-cases", type=Path, default=MODULE_PATHS["selftest_cases"])
    parser.add_argument("--selftest-output-dir", type=Path, default=MODULE_PATHS["selftest_output_dir"])
    parser.add_argument("--schema", type=Path, default=SUBSYSTEM_VERDICT_SCHEMA)
    args = parser.parse_args()

    if args.selftest:
        report = run_selftests(args.selftest_cases, args.matrix, args.schema, args.selftest_output_dir, args.write_report)
        print(json.dumps(report, indent=2))
        return 0 if report.get("all_passed", False) and report.get("schema_valid_all", False) else 1

    if not args.case_id:
        raise SystemExit("S18 run requires --case-id unless --selftest is set.")
    payload, report = run_subsystem_module(args.case_id, args.matrix)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2))
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

