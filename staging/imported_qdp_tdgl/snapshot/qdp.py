#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List

from qdp_paths import (
    BASE_TEMPLATE,
    CANDIDATE_VALIDATOR,
    FORK_INTAKE_VALIDATOR,
    MODULES,
    OUTPUTS_DIR,
    ROOT,
    SCHEMA,
    resolve_module,
)
from qdp_validation import emit_validation_result, run_candidate_sweep, validate_candidate_file


def run_cmd(cmd: List[str]) -> int:
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def add_common_validation_args(cmd: List[str]) -> None:
    cmd.extend(["--base-template", str(BASE_TEMPLATE), "--validator", str(CANDIDATE_VALIDATOR), "--schema", str(SCHEMA)])


def handle_module_selftest(module_key: str) -> int:
    module = resolve_module(module_key)
    if not module.get("supports_selftest", False):
        raise SystemExit(f"{module['module_id']} does not expose a self-test workflow through this CLI.")

    cmd = [sys.executable, str(module["runner"])]
    if module["selftest_style"] == "m05":
        cmd.extend(
            [
                "--selftest-cases",
                str(module["selftest_cases"]),
                "--base-template",
                str(BASE_TEMPLATE),
                "--validator",
                str(CANDIDATE_VALIDATOR),
                "--schema",
                str(SCHEMA),
                "--output-dir",
                str(module["selftest_output_dir"]),
                "--write-selftest-report",
                str(module["selftest_report"]),
            ]
        )
    else:
        cmd.extend(
            [
                "--selftest",
                "--selftest-cases",
                str(module["selftest_cases"]),
                "--base-template",
                str(BASE_TEMPLATE),
                "--validator",
                str(CANDIDATE_VALIDATOR),
                "--schema",
                str(SCHEMA),
                "--selftest-output-dir",
                str(module["selftest_output_dir"]),
                "--write-report",
                str(module["selftest_report"]),
            ]
        )
    return run_cmd(cmd)


def handle_module_run(args: argparse.Namespace) -> int:
    module = resolve_module(args.module)
    cmd = [sys.executable, str(module["runner"])]

    if module["module_id"] == "M03":
        defaults = module["run_defaults"]
        cmd.extend(
            [
                "--manifest",
                str(defaults["--manifest"]),
                "--registry",
                str(defaults["--registry"]),
                "--root",
                str(defaults["--root"]),
                "--mode",
                args.mode,
                "--write-report",
                str(args.report or defaults["--write-report"]),
            ]
        )
        if args.candidate:
            cmd.extend(["--candidate", str(args.candidate)])
        if args.output:
            cmd.extend(["--write-candidate", str(args.output)])
        return run_cmd(cmd)

    if module["module_id"] == "M04":
        defaults = module["run_defaults"]
        if not args.intake:
            raise SystemExit("M04 run requires --intake.")
        cmd.extend(
            [
                "--intake",
                str(args.intake),
                "--candidate-template",
                str(defaults["--candidate-template"]),
                "--registry",
                str(defaults["--registry"]),
                "--intake-schema",
                str(defaults["--intake-schema"]),
            ]
        )
        if args.output:
            cmd.extend(["--write-candidate", str(args.output)])
        if args.report:
            cmd.extend(["--write-registration", str(args.report)])
        return run_cmd(cmd)

    if module["module_id"] == "M06":
        return run_cmd(cmd)

    if module["module_id"] == "M05":
        if not args.candidate:
            raise SystemExit("M05 run requires --candidate.")
        cmd.append(str(args.candidate))
        add_common_validation_args(cmd)
        if args.output:
            cmd.extend(["--write-candidate", str(args.output)])
        if args.report:
            cmd.extend([module["run_report_flag"], str(args.report)])
        if args.stage_inputs:
            cmd.extend(["--stage-inputs", str(args.stage_inputs)])
        return run_cmd(cmd)

    if not args.candidate:
        raise SystemExit(f"{module['module_id']} run requires --candidate.")
    cmd.extend(["--candidate", str(args.candidate)])
    add_common_validation_args(cmd)
    if args.output:
        cmd.extend(["--output", str(args.output)])
    if args.report:
        cmd.extend([module["run_report_flag"], str(args.report)])
    return run_cmd(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified QDP workflow entrypoint.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="Run the M06 bootstrap harness.")
    bootstrap.set_defaults(handler=lambda _args: run_cmd([sys.executable, str(resolve_module("m06")["runner"])]))

    check = subparsers.add_parser("check", help="Run bootstrap and a final validation sweep over emitted candidates.")
    check.add_argument("--skip-bootstrap", action="store_true", help="Reuse existing artifacts instead of rerunning bootstrap first.")
    check.add_argument("--outputs-root", type=Path, default=OUTPUTS_DIR, help="Root directory to scan for emitted candidate JSON files.")
    check.add_argument("--max-workers", type=int, default=8, help="Maximum parallel candidate validations to run.")

    def check_handler(args: argparse.Namespace) -> int:
        if not args.skip_bootstrap:
            bootstrap_proc = subprocess.run(
                [sys.executable, str(resolve_module("m06")["runner"])],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            if bootstrap_proc.returncode != 0:
                print("CHECK FAILED")
                print(f"- bootstrap_exit_code: {bootstrap_proc.returncode}")
                if bootstrap_proc.stdout:
                    print(bootstrap_proc.stdout, end="" if bootstrap_proc.stdout.endswith("\n") else "\n")
                if bootstrap_proc.stderr:
                    print(bootstrap_proc.stderr, file=sys.stderr, end="" if bootstrap_proc.stderr.endswith("\n") else "\n")
                return bootstrap_proc.returncode

        summary = run_candidate_sweep(
            args.outputs_root,
            CANDIDATE_VALIDATOR,
            SCHEMA,
            mode="final",
            max_workers=args.max_workers,
        )
        failed = list(summary["failed_results"])
        print("CHECK PASSED" if not failed else "CHECK FAILED")
        print(f"- bootstrap: {'SKIPPED' if args.skip_bootstrap else 'PASSED'}")
        print(f"- candidates_total: {summary['candidates_total']}")
        print(f"- candidates_failed: {summary['candidates_failed']}")
        print(f"- outputs_root: {summary['outputs_root']}")
        if summary["error"]:
            print(f"- {summary['error']}")
        if failed:
            for result in failed:
                print(f"- failed_candidate: {result['candidate_path']}")
                emit_validation_result(result)
            return 1
        return int(summary["returncode"])

    check.set_defaults(handler=check_handler)

    validate = subparsers.add_parser("validate", help="Validate a candidate or intake file.")
    validate.add_argument("target", type=Path, help="Path to the file to validate.")
    validate.add_argument("--kind", choices=["candidate", "fork-intake"], default="candidate")
    validate.add_argument("--mode", choices=["template", "final"], default="final")

    def validate_handler(args: argparse.Namespace) -> int:
        if args.kind == "candidate":
            result = validate_candidate_file(args.target, CANDIDATE_VALIDATOR, SCHEMA, mode=args.mode)
            emit_validation_result(result)
            return int(result["returncode"])
        return run_cmd([sys.executable, str(FORK_INTAKE_VALIDATOR), str(args.target)])

    validate.set_defaults(handler=validate_handler)

    module = subparsers.add_parser("module", help="Run module workflows by module ID.")
    module_subparsers = module.add_subparsers(dest="module_command", required=True)

    list_parser = module_subparsers.add_parser("list", help="List supported modules.")

    def list_handler(_args: argparse.Namespace) -> int:
        for key, meta in MODULES.items():
            print(f"{key}: {meta['module_id']} {meta['name']}")
        return 0

    list_parser.set_defaults(handler=list_handler)

    selftest = module_subparsers.add_parser("selftest", help="Run a module self-test pack.")
    selftest.add_argument("module", help="Module key, such as m05 or m10.")
    selftest.set_defaults(handler=lambda args: handle_module_selftest(args.module))

    run = module_subparsers.add_parser("run", help="Run a module directly.")
    run.add_argument("module", help="Module key, such as m03, m05, or m10.")
    run.add_argument("--candidate", type=Path)
    run.add_argument("--output", type=Path)
    run.add_argument("--report", type=Path)
    run.add_argument("--intake", type=Path)
    run.add_argument("--mode", choices=["ordinary", "subsystem"], default="ordinary")
    run.add_argument("--stage-inputs", type=Path)
    run.set_defaults(handler=handle_module_run)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
