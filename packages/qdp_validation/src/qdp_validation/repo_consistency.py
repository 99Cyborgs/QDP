from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .artifact_contracts import validate_file as validate_artifact_file
from tools.workflow.qdp_runtime.qdp_paths import (
    ALL_MIND_INTERFACE_CALLABLE_SURFACES,
    ALL_MIND_INTERFACE_PROMOTION_NOTE,
    ALL_MIND_INTERFACE_REPORT,
    ALL_MIND_INTERFACE_SCHEMA,
    CANDIDATE_VALIDATOR,
    MODULES,
    OUTPUTS_DIR,
    ROOT,
    SCHEMA,
)


def load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def load_schema(schema_path_str: str) -> Dict[str, Any]:
    schema_path = Path(schema_path_str)
    data = load_json_file(schema_path)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {schema_path}")
    return data


@lru_cache(maxsize=None)
def load_validator_module(validator_path_str: str):
    validator_path = Path(validator_path_str)
    if not validator_path.exists():
        raise FileNotFoundError(f"validator file not found: {validator_path}")
    module_name = f"qdp_validator_{abs(hash(validator_path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import validator module from {validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fatal_result(
    message: str,
    *,
    candidate_path: Path | None,
    validator_path: Path,
    schema_path: Path,
    mode: str,
    returncode: int = 2,
) -> Dict[str, Any]:
    return {
        "candidate_path": str(candidate_path) if candidate_path else "",
        "returncode": returncode,
        "stdout": "",
        "stderr": f"{message}\n",
        "valid": False,
        "errors": [],
        "mode": mode,
        "schema_path": str(schema_path),
        "validator_path": str(validator_path),
    }


def _invalid_root_result(
    *,
    candidate_path: Path | None,
    validator_path: Path,
    schema_path: Path,
    mode: str,
) -> Dict[str, Any]:
    return {
        "candidate_path": str(candidate_path) if candidate_path else "",
        "returncode": 1,
        "stdout": "",
        "stderr": "INVALID: candidate root must be exactly one JSON object\n",
        "valid": False,
        "errors": ["candidate root must be exactly one JSON object"],
        "mode": mode,
        "schema_path": str(schema_path),
        "validator_path": str(validator_path),
    }


def _invalid_result(
    errors: Iterable[str],
    *,
    candidate_path: Path | None,
    validator_path: Path,
    schema_path: Path,
    mode: str,
) -> Dict[str, Any]:
    error_list = list(errors)
    lines = ["INVALID", *[f"- {msg}" for msg in error_list]]
    return {
        "candidate_path": str(candidate_path) if candidate_path else "",
        "returncode": 1,
        "stdout": "\n".join(lines) + "\n",
        "stderr": "",
        "valid": False,
        "errors": error_list,
        "mode": mode,
        "schema_path": str(schema_path),
        "validator_path": str(validator_path),
    }


def _valid_result(
    *,
    candidate_path: Path | None,
    validator_path: Path,
    schema_path: Path,
    mode: str,
) -> Dict[str, Any]:
    candidate_label = str(candidate_path) if candidate_path else "<in-memory>"
    lines = [
        "VALID",
        f"- mode: {mode}",
        f"- candidate: {candidate_label}",
        f"- schema: {schema_path}",
    ]
    return {
        "candidate_path": str(candidate_path) if candidate_path else "",
        "returncode": 0,
        "stdout": "\n".join(lines) + "\n",
        "stderr": "",
        "valid": True,
        "errors": [],
        "mode": mode,
        "schema_path": str(schema_path),
        "validator_path": str(validator_path),
    }


def validate_candidate_instance(
    instance: Any,
    validator_path: Path,
    schema_path: Path,
    mode: str = "final",
    *,
    candidate_path: Path | None = None,
) -> Dict[str, Any]:
    validator_path = Path(validator_path)
    schema_path = Path(schema_path)

    if not schema_path.exists():
        return _fatal_result(
            f"FATAL: schema file not found: {schema_path}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )
    if not isinstance(instance, dict):
        return _invalid_root_result(
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    try:
        validator_module = load_validator_module(str(validator_path.resolve()))
    except Exception as exc:
        return _fatal_result(
            f"FATAL: could not import validator module: {exc}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    try:
        schema = load_schema(str(schema_path.resolve()))
    except Exception as exc:
        return _fatal_result(
            f"FATAL: could not parse schema JSON: {exc}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    errors: List[str] = validator_module.schema_validate(instance, schema)
    errors.extend(validator_module.semantic_validate(instance, mode))
    if errors:
        return _invalid_result(
            errors,
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )
    return _valid_result(
        candidate_path=candidate_path,
        validator_path=validator_path,
        schema_path=schema_path,
        mode=mode,
    )


def validate_candidate_file(
    candidate_path: Path,
    validator_path: Path,
    schema_path: Path,
    mode: str = "final",
) -> Dict[str, Any]:
    candidate_path = Path(candidate_path)
    validator_path = Path(validator_path)
    schema_path = Path(schema_path)

    if not candidate_path.exists():
        return _fatal_result(
            f"FATAL: candidate file not found: {candidate_path}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    try:
        instance = load_json_file(candidate_path)
    except Exception as exc:
        return _fatal_result(
            f"FATAL: could not parse candidate JSON: {exc}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    return validate_candidate_instance(
        instance,
        validator_path,
        schema_path,
        mode=mode,
        candidate_path=candidate_path,
    )


def emit_validation_result(result: Dict[str, Any]) -> None:
    stdout = str(result.get("stdout", "") or "")
    stderr = str(result.get("stderr", "") or "")
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")


def validate_all_mind_interface_semantics(instance: Any) -> List[str]:
    if not isinstance(instance, dict):
        return ["interface payload must be a JSON object."]

    errors: List[str] = []
    callable_surfaces = instance.get("callable_surfaces")
    if callable_surfaces != ALL_MIND_INTERFACE_CALLABLE_SURFACES:
        errors.append("callable_surfaces must match the frozen ALL-MIND contract.")

    promotion_posture = instance.get("promotion_posture")
    if not isinstance(promotion_posture, dict):
        errors.append("promotion_posture must be an object.")
    else:
        if promotion_posture.get("suggested_mode") != instance.get("promotion_mode"):
            errors.append("promotion_posture.suggested_mode must match promotion_mode.")
        if promotion_posture.get("note") != ALL_MIND_INTERFACE_PROMOTION_NOTE:
            errors.append("promotion_posture.note must preserve the narrow-interface boundary note.")

    readiness = instance.get("readiness")
    blockers = instance.get("blockers")
    if isinstance(readiness, dict) and isinstance(blockers, dict):
        for ready_key, blocker_key in (
            ("ordinary_recovery_ready", "ordinary_recovery_blockers"),
            ("ordinary_authoritative_ready", "ordinary_authoritative_blockers"),
            ("subsystem_recovery_ready", "subsystem_recovery_blockers"),
            ("subsystem_authoritative_ready", "subsystem_authoritative_blockers"),
        ):
            ready = readiness.get(ready_key)
            blocker_list = blockers.get(blocker_key)
            if isinstance(ready, bool) and isinstance(blocker_list, list) and ready and blocker_list:
                errors.append(f"{ready_key} cannot be true when {blocker_key} is non-empty.")

    module_readiness_summary = instance.get("module_readiness_summary")
    module_closure_limitations = instance.get("module_closure_limitations")
    if isinstance(module_readiness_summary, dict) and isinstance(module_closure_limitations, dict):
        unknown_keys = sorted(key for key in module_closure_limitations if key not in module_readiness_summary)
        if unknown_keys:
            errors.append(
                "module_closure_limitations keys must also exist in module_readiness_summary: "
                + ", ".join(unknown_keys)
            )

    return errors


def validate_all_mind_interface_file(path: Path = ALL_MIND_INTERFACE_REPORT) -> Dict[str, Any]:
    return validate_artifact_file(
        path,
        ALL_MIND_INTERFACE_SCHEMA,
        artifact_kind="all-mind-interface",
        semantic_validate=validate_all_mind_interface_semantics,
    )


def normalize_repo_path(path: Path | str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def discover_candidate_outputs(outputs_root: Path) -> List[Path]:
    outputs_root = normalize_repo_path(outputs_root)
    if not outputs_root.exists():
        return []
    return sorted(
        path
        for path in outputs_root.rglob("*_candidate.json")
        if path.is_file() and not candidate_is_expected_invalid_selftest(path)
    )


def candidate_is_expected_invalid_selftest(candidate_path: Path) -> bool:
    path = normalize_repo_path(candidate_path)
    try:
        relative = path.relative_to(OUTPUTS_DIR.resolve())
    except ValueError:
        return False
    parts = relative.parts
    if len(parts) < 4 or parts[1] != "selftests":
        return False
    module = MODULES.get(parts[0])
    if not module:
        return False
    report_path = module.get("selftest_report")
    if not isinstance(report_path, Path) or not report_path.exists():
        return False
    report = load_json_file(report_path)
    case_id = parts[2]
    for case in report.get("cases", []):
        if not isinstance(case, dict):
            continue
        if case.get("case_id") == case_id and case.get("expected_valid") is False and case.get("passed", False):
            return True
    return False


def run_bootstrap() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "modules" / "m06_bootstrap_harness" / "runner.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def run_repo_audit(*, phase: str, emit_all_mind_interface: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(ROOT / "tools" / "migration" / "repo_audit.py"), "--phase", phase]
    if emit_all_mind_interface:
        cmd.append("--emit-all-mind-interface")
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def validate_output_candidates(outputs_root: Path, max_workers: int = 8) -> Dict[str, Any]:
    candidates = discover_candidate_outputs(outputs_root)
    if not candidates:
        return {
            "outputs_root": str(outputs_root),
            "candidates_total": 0,
            "candidates_failed": 0,
            "valid": False,
            "results": [],
            "error": "no emitted candidate artifacts were found under the outputs root",
        }

    worker_count = max(1, min(max_workers, len(candidates)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(
            executor.map(
                lambda path: validate_candidate_file(path, CANDIDATE_VALIDATOR, SCHEMA, mode="final"),
                candidates,
            )
        )
    failed = [result for result in results if not result.get("valid", False)]
    return {
        "outputs_root": str(outputs_root),
        "candidates_total": len(results),
        "candidates_failed": len(failed),
        "valid": not failed,
        "results": results,
    }


def structural_consistency_from_blockers(blocker_ledger: Dict[str, Any]) -> bool:
    blockers = blocker_ledger.get("blockers", [])
    return not any(
        isinstance(blocker, dict) and blocker.get("severity") not in {"informational", "info"}
        for blocker in blockers
    )


def run_repo_consistency(
    *,
    outputs_root: Path = OUTPUTS_DIR,
    skip_bootstrap: bool = False,
    emit_all_mind_interface: bool = True,
    max_workers: int = 8,
) -> Dict[str, Any]:
    outputs_root = normalize_repo_path(outputs_root)
    bootstrap_proc = None
    if not skip_bootstrap:
        bootstrap_proc = run_bootstrap()

    audit_proc = run_repo_audit(phase="post", emit_all_mind_interface=emit_all_mind_interface)
    blocker_ledger = load_json_file(ROOT / "artifacts" / "reports" / "system" / "post_overhaul_blocker_ledger.json")
    bootstrap_report = load_json_file(ROOT / "artifacts" / "reports" / "m06" / "bootstrap_report.json")
    candidate_validation = validate_output_candidates(outputs_root, max_workers=max_workers)
    all_mind_interface_validation = {
        "artifact_kind": "all-mind-interface",
        "path": str(ALL_MIND_INTERFACE_REPORT),
        "schema_path": str(ALL_MIND_INTERFACE_SCHEMA),
        "valid": True,
        "errors": [],
        "skipped": not emit_all_mind_interface,
    }
    if emit_all_mind_interface:
        all_mind_interface_validation = validate_all_mind_interface_file(ALL_MIND_INTERFACE_REPORT)
    all_mind_interface = (
        load_json_file(ALL_MIND_INTERFACE_REPORT)
        if emit_all_mind_interface and all_mind_interface_validation.get("valid", False)
        else {}
    )

    structural_consistency_passed = (
        (bootstrap_proc is None or bootstrap_proc.returncode == 0)
        and audit_proc.returncode == 0
        and candidate_validation.get("valid", False)
        and (not emit_all_mind_interface or all_mind_interface_validation.get("valid", False))
        and structural_consistency_from_blockers(blocker_ledger)
    )

    return {
        "artifact_id": "QDP_REPO_VALIDATION_REPORT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "repo_consistency",
        "structural_consistency_passed": structural_consistency_passed,
        "bootstrap": {
            "executed": not skip_bootstrap,
            "returncode": None if bootstrap_proc is None else bootstrap_proc.returncode,
            "stdout": "" if bootstrap_proc is None else bootstrap_proc.stdout,
            "stderr": "" if bootstrap_proc is None else bootstrap_proc.stderr,
        },
        "readiness": {
            "ordinary_recovery_ready": bool(bootstrap_report.get("ordinary_recovery_ready", False)),
            "ordinary_authoritative_ready": bool(bootstrap_report.get("ordinary_authoritative_ready", False)),
            "subsystem_recovery_ready": bool(bootstrap_report.get("subsystem_recovery_ready", False)),
            "subsystem_authoritative_ready": bool(bootstrap_report.get("subsystem_authoritative_ready", False)),
            "ordinary_recovery_blockers": bootstrap_report.get("ordinary_recovery_blockers", []),
            "ordinary_authoritative_blockers": bootstrap_report.get("ordinary_authoritative_blockers", []),
            "subsystem_recovery_blockers": bootstrap_report.get("subsystem_recovery_blockers", []),
            "subsystem_authoritative_blockers": bootstrap_report.get("subsystem_authoritative_blockers", []),
        },
        "candidate_validation": candidate_validation,
        "all_mind_interface_validation": all_mind_interface_validation,
        "post_overhaul_blocker_ledger": blocker_ledger,
        "all_mind_interface": all_mind_interface,
        "artifacts": {
            "bootstrap_report": "artifacts/reports/m06/bootstrap_report.json",
            "post_overhaul_blocker_ledger": "artifacts/reports/system/post_overhaul_blocker_ledger.json",
            "all_mind_interface": "artifacts/reports/system/all_mind_interface.json" if emit_all_mind_interface else "",
            "all_mind_interface_schema": "config/schema/all_mind_interface_schema.json" if emit_all_mind_interface else "",
            "repo_validation_report": "artifacts/reports/system/repo_validation_report.json",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the QDP repo-consistency validation sweep.")
    parser.add_argument("--outputs-root", type=Path, default=OUTPUTS_DIR)
    parser.add_argument("--skip-bootstrap", action="store_true")
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument(
        "--write-report",
        type=Path,
        default=ROOT / "artifacts" / "reports" / "system" / "repo_validation_report.json",
    )
    parser.add_argument("--no-all-mind-interface", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_repo_consistency(
        outputs_root=args.outputs_root,
        skip_bootstrap=args.skip_bootstrap,
        emit_all_mind_interface=not args.no_all_mind_interface,
        max_workers=args.max_workers,
    )
    args.write_report.parent.mkdir(parents=True, exist_ok=True)
    args.write_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report.get("structural_consistency_passed", False) else 1
