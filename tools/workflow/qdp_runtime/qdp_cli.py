#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[3]
QDP_CONTROL_SRC = ROOT / "packages" / "qdp_control" / "src"
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_VALIDATION_SRC = ROOT / "packages" / "qdp_validation" / "src"

for path in (QDP_CONTROL_SRC, QDP_IO_SRC, QDP_VALIDATION_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_io.artifacts import stable_hash
from qdp_io.serialization import load_json_object
from qdp_validation import emit_artifact_validation_result, validate_artifact_file as validate_file
from qdp_control.campaign_planner import (
    normalize_repo_path,
    plan_campaign,
    prepare_campaign,
    write_campaign_plan,
    write_prepare_report,
)
from qdp_control.control_plane import (
    claim_next_queue_item,
    get_queue_item,
    list_queue_items,
    recover_expired_queue_leases,
    update_queue_item,
)
from qdp_control.lab_workflows import default_instrument_profile, ingest_lab_result, pack_lab_request
from qdp_control.queue import (
    BLOCKED_REASON_CODES,
    RETRYABLE_REASON_CODES,
    append_queue_log,
    build_error_record,
    enqueue_manifest,
    filtered_queue_items,
    lease_expiration,
    load_queue_log,
    mark_blocked,
    mark_failed_retryable,
    mark_failed_terminal,
    mark_running,
    mark_succeeded,
    queue_show_payload,
    record_lease_recovery,
    refresh_queue_report,
    requeue,
    utc_now as queue_utc_now,
)
from qdp_control.run_ledger import record_run
from tools.workflow.qdp_runtime.qdp_module_sdk import run_module
from tools.workflow.qdp_runtime.qdp_module_workflows import module_selftest_keys, report_all_passed, report_all_validator_valid, run_module_selftests
from tools.workflow.qdp_runtime.qdp_paths import (
    BASE_TEMPLATE,
    CALIBRATION_SNAPSHOT_SCHEMA,
    CAMPAIGN_PLAN_REPORT,
    CAMPAIGN_PREPARE_REPORT,
    CANDIDATE_ARTIFACT_MANIFEST_SCHEMA,
    CANDIDATE_VALIDATOR,
    CONTROL_PLANE_DB,
    EXPERIMENT_REQUEST_SCHEMA,
    FORK_INTAKE_VALIDATOR,
    INSTRUMENT_PROFILE_SCHEMA,
    LAB_INGESTIONS_DIR,
    LAB_REQUESTS_DIR,
    LINEAGE_RECORD_SCHEMA,
    MODULES,
    OUTPUTS_DIR,
    QUEUE_REPORT,
    ROOT,
    RUN_LEDGER_REPORT,
    RUN_RESULT_PACKET_SCHEMA,
    SCHEMA,
    SUBSYSTEM_VERDICT_SCHEMA,
    resolve_simulation_partition,
    resolve_module,
    simulation_campaign_prepare_report_path,
    simulation_campaign_report_path,
    simulation_lab_ingest_path,
    simulation_lab_requests_dir,
    simulation_module_candidate_path,
    simulation_module_report_path,
    simulation_outputs_root,
)
from tools.workflow.qdp_runtime.qdp_validation import (
    emit_validation_result,
    validate_all_mind_interface_file,
    validate_candidate_file,
)


SELFTEST_REPORT_CACHE: Dict[str, Dict[str, object]] = {}


def run_cmd(cmd: List[str]) -> int:
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def add_common_validation_args(cmd: List[str]) -> None:
    cmd.extend(["--base-template", str(BASE_TEMPLATE), "--validator", str(CANDIDATE_VALIDATOR), "--schema", str(SCHEMA)])


def load_json(path: Path) -> Dict[str, object]:
    return load_json_object(path)


def normalize_deterministic_payload(payload):
    if isinstance(payload, dict):
        out = {}
        for key, value in payload.items():
            if key in {"timestamp_utc", "date", "first_seen_utc", "last_seen_utc"}:
                continue
            out[key] = normalize_deterministic_payload(value)
        return out
    if isinstance(payload, list):
        return [normalize_deterministic_payload(item) for item in payload]
    return payload


def candidate_is_expected_invalid_selftest(candidate_path: Path) -> bool:
    candidate_path = normalize_repo_path(candidate_path)
    try:
        relative = candidate_path.relative_to(OUTPUTS_DIR.resolve())
    except ValueError:
        return False
    parts = relative.parts
    if len(parts) < 4 or parts[1] != "selftests":
        return False
    module_key = parts[0]
    module = MODULES.get(module_key)
    if not module:
        return False
    report_path = module.get("selftest_report")
    if not isinstance(report_path, Path) or not report_path.exists():
        return False
    cache_key = str(report_path)
    if cache_key not in SELFTEST_REPORT_CACHE:
        SELFTEST_REPORT_CACHE[cache_key] = load_json(report_path)
    report = SELFTEST_REPORT_CACHE[cache_key]
    case_id = parts[2]
    for case in report.get("cases", []):
        if not isinstance(case, dict):
            continue
        if case.get("case_id") == case_id and case.get("expected_valid") is False and case.get("passed", False):
            return True
    return False


def run_bootstrap_once() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(resolve_module("m06")["runner"])],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def handle_module_selftest(module_key: str) -> int:
    if module_key.strip().lower() == "all":
        ordered = module_selftest_keys()
        results = run_module_selftests(ordered)
        failures = []
        for key in ordered:
            result = results[key]
            module = resolve_module(key)
            report = result.get("report", {})
            passed = result["execution"]["ok"] and report_all_passed(report) and report_all_validator_valid(report)
            print(f"{key}: {module['module_id']} {'PASS' if passed else 'FAIL'}")
            if not passed:
                failures.append(key)
        return 0 if not failures else 1

    single = run_module_selftests([module_key])
    result = single.get(module_key.lower()) or single.get(module_key)
    if not result:
        raise SystemExit(f"Unknown module selftest target: {module_key}")
    report = result.get("report", {})
    print(json.dumps(report, indent=2))
    return 0 if result["execution"]["ok"] and report_all_passed(report) and report_all_validator_valid(report) else 1


def handle_module_run(args: argparse.Namespace) -> int:
    module = resolve_module(args.module)
    if module["module_id"] == "M06":
        if args.batch is not None or args.variant is not None:
            raise SystemExit("error: M06 does not support --batch/--variant via qdp.py module run.")
        return run_cmd([sys.executable, str(module["runner"])])

    batch, variant = resolve_partition_or_exit(args.batch, args.variant, require_variant=True)
    result = run_module(
        args.module,
        candidate=args.candidate,
        output=args.output or (simulation_module_candidate_path(batch, args.module, variant) if batch else None),
        report=args.report or (simulation_module_report_path(batch, args.module, variant) if batch else None),
        intake=args.intake,
        mode=args.mode,
        stage_inputs=args.stage_inputs,
        case_id=args.case_id,
        matrix=args.matrix,
    )
    print(json.dumps(result.get("report", result), indent=2))
    if "report" in result and isinstance(result["report"], dict):
        candidate_validation = result["report"].get("candidate_validation")
        if isinstance(candidate_validation, dict):
            return 0 if candidate_validation.get("valid", False) else 1
    return 0


def kind_schema(kind: str) -> Path:
    mapping = {
        "experiment-request": EXPERIMENT_REQUEST_SCHEMA,
        "instrument-profile": INSTRUMENT_PROFILE_SCHEMA,
        "run-result": RUN_RESULT_PACKET_SCHEMA,
        "calibration-snapshot": CALIBRATION_SNAPSHOT_SCHEMA,
        "lineage-record": LINEAGE_RECORD_SCHEMA,
        "candidate-manifest": CANDIDATE_ARTIFACT_MANIFEST_SCHEMA,
        "subsystem-verdict": SUBSYSTEM_VERDICT_SCHEMA,
    }
    return mapping[kind]


def resolve_partition_or_exit(
    batch: str | None,
    variant: str | None = None,
    *,
    require_variant: bool = False,
) -> tuple[str | None, str | None]:
    try:
        return resolve_simulation_partition(batch, variant, require_variant=require_variant)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


def run_check_workflow(args: argparse.Namespace) -> int:
    batch, _ = resolve_partition_or_exit(args.batch)
    bootstrap_hashes: List[str] = []
    for _ in range(max(1, args.repeat)):
        if args.skip_bootstrap:
            break
        bootstrap_proc = run_bootstrap_once()
        if bootstrap_proc.returncode != 0:
            print("CHECK FAILED")
            print(f"- bootstrap_exit_code: {bootstrap_proc.returncode}")
            if bootstrap_proc.stdout:
                print(bootstrap_proc.stdout, end="" if bootstrap_proc.stdout.endswith("\n") else "\n")
            if bootstrap_proc.stderr:
                print(bootstrap_proc.stderr, file=sys.stderr, end="" if bootstrap_proc.stderr.endswith("\n") else "\n")
            return bootstrap_proc.returncode
        bootstrap_report_path = resolve_module("m06")["bootstrap_report"]
        if Path(bootstrap_report_path).exists():
            bootstrap_hashes.append(stable_hash(normalize_deterministic_payload(load_json(Path(bootstrap_report_path)))))

    outputs_root = normalize_repo_path(args.outputs_root or (simulation_outputs_root(batch) if batch else OUTPUTS_DIR))
    if not outputs_root.exists():
        print("CHECK FAILED")
        print(f"- outputs_root_missing: {outputs_root}")
        return 1

    candidates = sorted(
        path
        for path in outputs_root.rglob("*_candidate.json")
        if path.is_file() and not candidate_is_expected_invalid_selftest(path)
    )
    if not candidates:
        print("CHECK FAILED")
        print("- candidates_total: 0")
        print(f"- outputs_root: {outputs_root}")
        return 1

    max_workers = max(1, min(args.max_workers, len(candidates)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(lambda path: validate_candidate_file(path, CANDIDATE_VALIDATOR, SCHEMA, mode="final"), candidates))

    failed = [result for result in results if not result["valid"]]
    bootstrap_report = load_json(Path(resolve_module("m06")["bootstrap_report"]))
    readiness_field = "ordinary_recovery_ready" if args.lane == "recovery" else "ordinary_authoritative_ready"
    blockers_field = "ordinary_recovery_blockers" if args.lane == "recovery" else "ordinary_authoritative_blockers"
    ready = bool(bootstrap_report.get(readiness_field, False))
    blockers = bootstrap_report.get(blockers_field, [])
    deterministic = len(set(bootstrap_hashes)) <= 1
    status = "CHECK PASSED" if not failed and ready and deterministic else "CHECK FAILED"
    print(status)
    print(f"- lane: {args.lane}")
    print(f"- readiness_field: {readiness_field}")
    print(f"- lane_ready: {str(ready).lower()}")
    print(f"- lane_blockers: {blockers}")
    print(f"- determinism_repeats: {max(1, args.repeat)}")
    print(f"- deterministic_hash_match: {str(deterministic).lower()}")
    print(f"- candidates_total: {len(results)}")
    print(f"- candidates_failed: {len(failed)}")
    if failed:
        for result in failed:
            print(f"- failed_candidate: {result['candidate_path']}")
            emit_validation_result(result)
    record = record_run(
        operation="check",
        lane=args.lane,
        status="READY" if status == "CHECK PASSED" else "FAILED",
        summary={
            "candidates_total": len(results),
            "candidates_failed": len(failed),
            "lane_ready": ready,
            "lane_blockers": blockers,
            "deterministic_hash_match": deterministic,
            **({"batch": batch} if batch else {}),
        },
        artifacts=[Path(resolve_module("m06")["bootstrap_report"]), RUN_LEDGER_REPORT, CONTROL_PLANE_DB],
    )
    print(f"- run_id: {record['run_id']}")
    return 0 if status == "CHECK PASSED" else 1


def run_campaign_prepare_workflow(args: argparse.Namespace) -> int:
    batch, _ = resolve_partition_or_exit(args.batch)
    input_root = args.input_root or (simulation_outputs_root(batch) if batch else OUTPUTS_DIR)
    write_report = args.write_report or (simulation_campaign_prepare_report_path(batch) if batch else CAMPAIGN_PREPARE_REPORT)
    try:
        report = prepare_campaign(args.candidate, input_root, batch=batch)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    write_prepare_report(report, write_report)
    print(json.dumps(report, indent=2))
    return 0


def run_campaign_plan_workflow(args: argparse.Namespace) -> int:
    batch, _ = resolve_partition_or_exit(args.batch)
    if args.include_selftests:
        raise SystemExit(
            "error: --include-selftests is not supported for prepared-M12 campaign planning. "
            "Use 'python qdp.py campaign prepare --candidate <raw-source>' for targeted fixture materialization."
        )
    input_root = args.input_root or (simulation_outputs_root(batch) if batch else OUTPUTS_DIR)
    write_report = args.write_report or (simulation_campaign_report_path(batch) if batch else CAMPAIGN_PLAN_REPORT)
    try:
        report = plan_campaign(args.candidate, input_root, budget=args.budget, batch=batch)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    write_campaign_plan(report, write_report)
    print(json.dumps(report, indent=2))
    return 0


def run_lab_pack_workflow(args: argparse.Namespace) -> int:
    batch, _ = resolve_partition_or_exit(args.batch)
    from modules.m12_experiment_design.runner import run_experiment_design

    candidate = load_json(args.candidate)
    candidate, _ = run_experiment_design(candidate)
    instrument_profile = load_json(args.instrument_profile) if args.instrument_profile else default_instrument_profile(candidate)
    result = pack_lab_request(
        candidate_path=args.candidate,
        candidate=candidate,
        lane=args.lane,
        instrument_profile=instrument_profile,
        output_dir=args.output_dir or (simulation_lab_requests_dir(batch) if batch else LAB_REQUESTS_DIR),
    )
    print(json.dumps(result["report"], indent=2))
    return 0 if all(item.get("valid", False) for item in result["report"]["validations"]) else 1


def run_lab_ingest_workflow(args: argparse.Namespace) -> int:
    batch, variant = resolve_partition_or_exit(args.batch, args.variant, require_variant=True)
    result = ingest_lab_result(
        candidate_path=args.candidate,
        request_pack_path=args.request_pack,
        result_packet_path=args.result_packet,
        calibration_snapshot_path=args.calibration_snapshot,
        lineage_record_path=args.lineage_record,
        updated_candidate_path=args.output or (simulation_lab_ingest_path(batch, variant) if batch else LAB_INGESTIONS_DIR / "updated_candidate.json"),
    )
    print(json.dumps(result["report"], indent=2))
    return 0 if result["report"]["candidate_validation"]["valid"] else 1


def build_queue_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def queue_execution_result(
    *,
    status: str,
    reason_code: str,
    operator_hint: str,
    artifacts: List[str],
    details: Dict[str, object] | None = None,
) -> Dict[str, object]:
    return {
        "status": status,
        "reason_code": reason_code,
        "operator_hint": operator_hint,
        "artifacts": artifacts,
        "details": details or {},
    }


def check_expected_artifacts(args: argparse.Namespace) -> List[Path]:
    return [Path(resolve_module("m06")["bootstrap_report"])]


def campaign_prepare_expected_artifacts(args: argparse.Namespace) -> List[Path]:
    batch, _ = resolve_partition_or_exit(args.batch)
    return [args.write_report or (simulation_campaign_prepare_report_path(batch) if batch else CAMPAIGN_PREPARE_REPORT)]


def campaign_plan_expected_artifacts(args: argparse.Namespace) -> List[Path]:
    batch, _ = resolve_partition_or_exit(args.batch)
    return [args.write_report or (simulation_campaign_report_path(batch) if batch else CAMPAIGN_PLAN_REPORT)]


def lab_pack_expected_artifacts(args: argparse.Namespace, request_pack_path: Path | None = None) -> List[Path]:
    if request_pack_path is not None:
        return [request_pack_path]
    return []


def lab_ingest_expected_artifacts(args: argparse.Namespace) -> List[Path]:
    batch, variant = resolve_partition_or_exit(args.batch, args.variant, require_variant=True)
    output = args.output or (simulation_lab_ingest_path(batch, variant) if batch else LAB_INGESTIONS_DIR / "updated_candidate.json")
    return [Path(output)]


def build_queue_job_args(item: Dict[str, object]) -> argparse.Namespace:
    payload = dict(item["job_payload"])
    job_type = str(item["job_type"])
    if job_type == "check":
        return argparse.Namespace(
            lane=payload.get("lane", "recovery"),
            skip_bootstrap=bool(payload.get("skip_bootstrap", False)),
            batch=payload.get("batch"),
            outputs_root=Path(payload["outputs_root"]) if payload.get("outputs_root") else None,
            max_workers=int(payload.get("max_workers", 8)),
            repeat=int(payload.get("repeat", 1)),
        )
    if job_type == "campaign_prepare":
        return argparse.Namespace(
            batch=payload.get("batch"),
            candidate=[Path(path) for path in payload.get("candidate_paths", [])],
            input_root=Path(payload["input_root"]) if payload.get("input_root") else None,
            write_report=Path(payload["write_report"]) if payload.get("write_report") else None,
        )
    if job_type == "campaign_plan":
        return argparse.Namespace(
            batch=payload.get("batch"),
            candidate=[Path(path) for path in payload.get("candidate_paths", [])],
            input_root=Path(payload["input_root"]) if payload.get("input_root") else None,
            budget=int(payload.get("budget", 5)),
            include_selftests=False,
            write_report=Path(payload["write_report"]) if payload.get("write_report") else None,
        )
    if job_type == "lab_pack":
        return argparse.Namespace(
            candidate=Path(payload["candidate_path"]),
            lane=payload.get("lane", "recovery"),
            batch=payload.get("batch"),
            instrument_profile=Path(payload["instrument_profile"]) if payload.get("instrument_profile") else None,
            output_dir=Path(payload["output_dir"]) if payload.get("output_dir") else None,
        )
    if job_type == "lab_ingest":
        return argparse.Namespace(
            candidate=Path(payload["candidate_path"]),
            request_pack=Path(payload["request_pack_path"]),
            result_packet=Path(payload["result_packet_path"]),
            calibration_snapshot=Path(payload["calibration_snapshot_path"]),
            lineage_record=Path(payload["lineage_record_path"]),
            batch=payload.get("batch"),
            variant=payload.get("variant"),
            output=Path(payload["output"]) if payload.get("output") else None,
        )
    raise SystemExit(f"error: unsupported queue job_type: {job_type}")


def execute_queue_check_job(item: Dict[str, object], args: argparse.Namespace) -> Dict[str, object]:
    exit_code = run_check_workflow(args)
    expected = [str(path) for path in check_expected_artifacts(args)]
    if exit_code == 0:
        return queue_execution_result(
            status="SUCCEEDED",
            reason_code="CHECK_READY",
            operator_hint="No operator action required.",
            artifacts=expected,
            details={"exit_code": 0},
        )
    outputs_root = normalize_repo_path(args.outputs_root or OUTPUTS_DIR)
    if not outputs_root.exists():
        return queue_execution_result(
            status="BLOCKED",
            reason_code="MISSING_REQUIRED_INPUT",
            operator_hint="Create or point to a valid outputs root before retrying this queue item.",
            artifacts=expected,
            details={"outputs_root": str(outputs_root), "exit_code": exit_code},
        )
    candidates = sorted(path for path in outputs_root.rglob("*_candidate.json") if path.is_file() and not candidate_is_expected_invalid_selftest(path))
    if not candidates:
        return queue_execution_result(
            status="BLOCKED",
            reason_code="MISSING_REQUIRED_INPUT",
            operator_hint="Emit candidate artifacts under the outputs root before retrying this queue item.",
            artifacts=expected,
            details={"outputs_root": str(outputs_root), "exit_code": exit_code},
        )
    bootstrap_report = Path(resolve_module("m06")["bootstrap_report"])
    if bootstrap_report.exists():
        report = load_json(bootstrap_report)
        blockers_field = "ordinary_authoritative_blockers" if args.lane == "authoritative" else "ordinary_recovery_blockers"
        blockers = report.get(blockers_field, [])
        if blockers:
            return queue_execution_result(
                status="BLOCKED",
                reason_code="AUTHORITATIVE_BLOCKERS",
                operator_hint="Resolve readiness blockers recorded in the bootstrap report before retrying.",
                artifacts=expected,
                details={"blockers": blockers, "exit_code": exit_code},
            )
    return queue_execution_result(
        status="BLOCKED",
        reason_code="VALIDATION_FAILED",
        operator_hint="Inspect candidate validation failures from the check output before retrying.",
        artifacts=expected,
        details={"exit_code": exit_code},
    )


def execute_queue_campaign_prepare_job(item: Dict[str, object], args: argparse.Namespace) -> Dict[str, object]:
    try:
        batch, _ = resolve_partition_or_exit(args.batch)
        input_root = args.input_root or (simulation_outputs_root(batch) if batch else OUTPUTS_DIR)
        write_report = args.write_report or (simulation_campaign_prepare_report_path(batch) if batch else CAMPAIGN_PREPARE_REPORT)
        report = prepare_campaign(args.candidate, input_root, batch=batch)
        write_prepare_report(report, write_report)
        print(json.dumps(report, indent=2))
        return queue_execution_result(
            status="SUCCEEDED",
            reason_code="CAMPAIGN_PREPARED",
            operator_hint="No operator action required.",
            artifacts=[str(Path(write_report))],
            details={"prepared_candidate_count": report.get("prepared_candidate_count", 0)},
        )
    except ValueError as exc:
        return queue_execution_result(
            status="BLOCKED",
            reason_code="INVALID_CAMPAIGN_STATE",
            operator_hint="Fix the campaign input state, then retry this queue item.",
            artifacts=[str(path) for path in campaign_prepare_expected_artifacts(args)],
            details={"message": str(exc)},
        )


def execute_queue_campaign_plan_job(item: Dict[str, object], args: argparse.Namespace) -> Dict[str, object]:
    try:
        batch, _ = resolve_partition_or_exit(args.batch)
        input_root = args.input_root or (simulation_outputs_root(batch) if batch else OUTPUTS_DIR)
        write_report = args.write_report or (simulation_campaign_report_path(batch) if batch else CAMPAIGN_PLAN_REPORT)
        report = plan_campaign(args.candidate, input_root, budget=args.budget, batch=batch)
        write_campaign_plan(report, write_report)
        print(json.dumps(report, indent=2))
        return queue_execution_result(
            status="SUCCEEDED",
            reason_code="CAMPAIGN_PLANNED",
            operator_hint="No operator action required.",
            artifacts=[str(Path(write_report))],
            details={"candidate_count": report.get("candidate_count", 0)},
        )
    except ValueError as exc:
        return queue_execution_result(
            status="BLOCKED",
            reason_code="INVALID_CAMPAIGN_STATE",
            operator_hint="Prepare or refresh campaign-ready M12 candidates before retrying this queue item.",
            artifacts=[str(path) for path in campaign_plan_expected_artifacts(args)],
            details={"message": str(exc)},
        )


def execute_queue_lab_pack_job(item: Dict[str, object], args: argparse.Namespace) -> Dict[str, object]:
    batch, _ = resolve_partition_or_exit(args.batch)
    from modules.m12_experiment_design.runner import run_experiment_design

    candidate = load_json(args.candidate)
    candidate, _ = run_experiment_design(candidate)
    instrument_profile = load_json(args.instrument_profile) if args.instrument_profile else default_instrument_profile(candidate)
    result = pack_lab_request(
        candidate_path=args.candidate,
        candidate=candidate,
        lane=args.lane,
        instrument_profile=instrument_profile,
        output_dir=args.output_dir or (simulation_lab_requests_dir(batch) if batch else LAB_REQUESTS_DIR),
    )
    print(json.dumps(result["report"], indent=2))
    validations = result["report"]["validations"]
    request_pack_path = Path(result["request_pack_path"])
    if all(item_result.get("valid", False) for item_result in validations):
        return queue_execution_result(
            status="SUCCEEDED",
            reason_code="LAB_REQUEST_READY",
            operator_hint="No operator action required.",
            artifacts=[str(request_pack_path)],
            details={"request_id": result["report"].get("request_id", "")},
        )
    return queue_execution_result(
        status="BLOCKED",
        reason_code="SCHEMA_INVALID",
        operator_hint="Repair invalid lab request artifacts before retrying this queue item.",
        artifacts=[str(request_pack_path)],
        details={"validations": validations},
    )


def execute_queue_lab_ingest_job(item: Dict[str, object], args: argparse.Namespace) -> Dict[str, object]:
    batch, variant = resolve_partition_or_exit(args.batch, args.variant, require_variant=True)
    output_path = args.output or (simulation_lab_ingest_path(batch, variant) if batch else LAB_INGESTIONS_DIR / "updated_candidate.json")
    result = ingest_lab_result(
        candidate_path=args.candidate,
        request_pack_path=args.request_pack,
        result_packet_path=args.result_packet,
        calibration_snapshot_path=args.calibration_snapshot,
        lineage_record_path=args.lineage_record,
        updated_candidate_path=output_path,
    )
    print(json.dumps(result["report"], indent=2))
    candidate_validation = result["report"]["candidate_validation"]
    governance_outcome = str(result["report"]["result_summary"].get("governance_outcome", "") or "")
    if not candidate_validation.get("valid", False):
        return queue_execution_result(
            status="BLOCKED",
            reason_code="VALIDATION_FAILED",
            operator_hint="Fix candidate validation failures before retrying this queue item.",
            artifacts=[str(Path(output_path))],
            details={"candidate_validation": candidate_validation},
        )
    if governance_outcome not in {"", "PROCEED"}:
        return queue_execution_result(
            status="BLOCKED",
            reason_code="GOVERNANCE_BLOCKED",
            operator_hint="Inspect the ingested candidate governance outcome before retrying this queue item.",
            artifacts=[str(Path(output_path))],
            details={"governance_outcome": governance_outcome, "result_summary": result["report"]["result_summary"]},
        )
    return queue_execution_result(
        status="SUCCEEDED",
        reason_code="LAB_INGESTED",
        operator_hint="No operator action required.",
        artifacts=[str(Path(output_path))],
        details={"result_summary": result["report"]["result_summary"]},
    )


def execute_queue_job(item: Dict[str, object]) -> Dict[str, object]:
    args = build_queue_job_args(item)
    job_type = str(item["job_type"])
    if job_type == "check":
        return execute_queue_check_job(item, args)
    elif job_type == "campaign_prepare":
        return execute_queue_campaign_prepare_job(item, args)
    elif job_type == "campaign_plan":
        return execute_queue_campaign_plan_job(item, args)
    elif job_type == "lab_pack":
        return execute_queue_lab_pack_job(item, args)
    elif job_type == "lab_ingest":
        return execute_queue_lab_ingest_job(item, args)
    raise ValueError(f"Unsupported queue job_type: {job_type}")


def verify_queue_success_artifacts(item: Dict[str, object], outcome: Dict[str, object]) -> Dict[str, object]:
    artifacts = [Path(path) for path in outcome.get("artifacts", [])]
    missing = [str(path) for path in artifacts if not path.exists()]
    if not missing:
        details = dict(outcome.get("details", {}))
        details["artifacts_verified"] = True
        outcome["details"] = details
        return outcome
    return queue_execution_result(
        status="RETRYABLE",
        reason_code="MISSING_EXPECTED_REPORT",
        operator_hint="Expected queue output artifacts were not created; inspect the job and retry if the failure was transient.",
        artifacts=[str(path) for path in artifacts],
        details={"missing_artifacts": missing, "artifacts_verified": False},
    )


def persist_manual_queue_action(
    queue_id: str,
    *,
    event: str,
    previous_state: str,
    new_state: str,
    operator_hint: str,
) -> Dict[str, object]:
    item = get_queue_item(queue_id)
    result_summary = dict(item.get("result_summary", {}) or {})
    manual_action = {
        "event": event,
        "previous_state": previous_state,
        "state_after": new_state,
        "timestamp_utc": queue_utc_now(),
        "operator_hint": operator_hint,
    }
    result_summary["last_manual_action"] = manual_action
    update_queue_item(queue_id, result_summary=result_summary)
    append_queue_log(
        queue_id,
        event,
        {"operator_action": manual_action},
        state_before=previous_state,
        state_after=new_state,
        operator_hint=operator_hint,
    )
    refresh_queue_report()
    return get_queue_item(queue_id)


def process_queue_item(item: Dict[str, object], *, worker_id: str) -> int:
    queue_id = str(item["queue_id"])
    attempt_count = int(item["attempt_count"]) + 1
    mark_running(queue_id, worker_id=worker_id, attempt_count=attempt_count)
    try:
        outcome = execute_queue_job(item)
    except BaseException as exc:  # pragma: no cover - unexpected crash path
        if isinstance(exc, OSError):
            error = build_error_record(
                reason_code="TEMPORARY_FILE_LOCK",
                operator_hint="The queue will retry this operational filesystem failure automatically.",
                message=str(exc),
                classification="RETRYABLE",
            )
        else:
            error = build_error_record(
                reason_code="PROCESS_CRASH",
                operator_hint="Inspect the unexpected queue execution crash before retrying.",
                message=str(exc),
                classification="RETRYABLE",
            )
        current = get_queue_item(queue_id)
        if int(current.get("attempt_count", attempt_count)) >= int(current.get("max_attempts", attempt_count)):
            mark_failed_terminal(queue_id, error=error)
        else:
            mark_failed_retryable(queue_id, error=error)
            requeue(queue_id, error=error)
        raise

    if outcome["status"] == "SUCCEEDED":
        outcome = verify_queue_success_artifacts(item, outcome)

    if outcome["status"] == "SUCCEEDED":
        summary = {
            "job_type": item["job_type"],
            "attempt_count": attempt_count,
            "reason_code": outcome["reason_code"],
            "operator_hint": outcome["operator_hint"],
            "artifacts": outcome["artifacts"],
            "details": outcome.get("details", {}),
            "artifacts_verified": bool(outcome.get("details", {}).get("artifacts_verified", False)),
        }
        mark_succeeded(queue_id, summary=summary)
        record_run(
            operation="queue_execute",
            lane="recovery",
            status="READY",
            summary={"queue_id": queue_id, "job_type": item["job_type"], "attempt_count": attempt_count},
            artifacts=[Path(path) for path in outcome["artifacts"] if Path(path).exists()],
        )
        return 0

    error = build_error_record(
        reason_code=str(outcome["reason_code"]),
        operator_hint=str(outcome["operator_hint"]),
        message=str(outcome.get("details", {}).get("message", outcome["reason_code"])),
        details=dict(outcome.get("details", {})),
        classification="BLOCKED" if outcome["status"] == "BLOCKED" else "RETRYABLE",
    )
    current = get_queue_item(queue_id)
    if outcome["status"] == "BLOCKED":
        mark_blocked(queue_id, error=error)
    elif int(current.get("attempt_count", attempt_count)) >= int(current.get("max_attempts", attempt_count)):
        mark_failed_terminal(queue_id, error=error)
    else:
        mark_failed_retryable(queue_id, error=error)
        requeue(queue_id, error=error)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified QDP workflow entrypoint.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="Run the M06 bootstrap harness.")

    def bootstrap_handler(_args: argparse.Namespace) -> int:
        proc = run_bootstrap_once()
        if proc.stdout:
            print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        if proc.stderr:
            print(proc.stderr, file=sys.stderr, end="" if proc.stderr.endswith("\n") else "\n")
        return proc.returncode

    bootstrap.set_defaults(handler=bootstrap_handler)

    check = subparsers.add_parser("check", help="Run bootstrap and a final validation sweep over emitted candidates.")
    check.add_argument("--lane", choices=["recovery", "authoritative"], default="recovery", help="Readiness lane to enforce.")
    check.add_argument("--skip-bootstrap", action="store_true", help="Reuse existing artifacts instead of rerunning bootstrap first.")
    check.add_argument("--batch", help="Simulation batch namespace for partitioned output defaults.")
    check.add_argument("--outputs-root", type=Path, help="Root directory to scan for emitted candidate JSON files.")
    check.add_argument("--max-workers", type=int, default=8, help="Maximum parallel candidate validations to run.")
    check.add_argument("--repeat", type=int, default=1, help="How many bootstrap passes to compare for deterministic hashes.")
    check.set_defaults(handler=run_check_workflow)

    validate = subparsers.add_parser("validate", help="Validate a candidate, intake, or lab artifact.")
    validate.add_argument("target", type=Path, help="Path to the file to validate.")
    validate.add_argument(
        "--kind",
        choices=[
            "candidate",
            "fork-intake",
            "experiment-request",
            "instrument-profile",
            "run-result",
            "calibration-snapshot",
            "lineage-record",
            "candidate-manifest",
            "subsystem-verdict",
            "all-mind-interface",
        ],
        default="candidate",
    )
    validate.add_argument("--mode", choices=["template", "final"], default="final")

    def validate_handler(args: argparse.Namespace) -> int:
        if args.kind == "candidate":
            result = validate_candidate_file(args.target, CANDIDATE_VALIDATOR, SCHEMA, mode=args.mode)
            emit_validation_result(result)
            return int(result["returncode"])
        if args.kind == "fork-intake":
            return run_cmd([sys.executable, str(FORK_INTAKE_VALIDATOR), str(args.target)])
        if args.kind == "all-mind-interface":
            result = validate_all_mind_interface_file(args.target)
            emit_artifact_validation_result(result)
            return 0 if result["valid"] else 1
        result = validate_file(args.target, kind_schema(args.kind), artifact_kind=args.kind)
        emit_artifact_validation_result(result)
        return 0 if result["valid"] else 1

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
    selftest.add_argument("module", nargs="?", default="all", help="Module key, such as m05 or s19, or all.")
    selftest.set_defaults(handler=lambda args: handle_module_selftest(args.module))

    run = module_subparsers.add_parser("run", help="Run a module directly.")
    run.add_argument("module", help="Module key, such as m03, m05, m10, or s19.")
    run.add_argument("--candidate", type=Path)
    run.add_argument("--output", type=Path)
    run.add_argument("--report", type=Path)
    run.add_argument("--intake", type=Path)
    run.add_argument("--mode", choices=["ordinary", "subsystem"], default="ordinary")
    run.add_argument("--stage-inputs", type=Path)
    run.add_argument("--case-id")
    run.add_argument("--matrix", type=Path)
    run.add_argument("--batch", help="Simulation batch namespace for derived output/report defaults.")
    run.add_argument("--variant", help="Simulation variant name within the batch namespace.")
    run.set_defaults(handler=handle_module_run)

    campaign = subparsers.add_parser("campaign", help="Campaign planning workflows.")
    campaign_subparsers = campaign.add_subparsers(dest="campaign_command", required=True)
    campaign_prepare = campaign_subparsers.add_parser("prepare", help="Materialize campaign-ready M12 candidates from raw source candidates.")
    campaign_prepare.add_argument("--batch", help="Simulation batch namespace for derived input/report defaults.")
    campaign_prepare.add_argument("--candidate", type=Path, action="append", default=[])
    campaign_prepare.add_argument("--input-root", type=Path)
    campaign_prepare.add_argument("--write-report", type=Path)

    campaign_prepare.set_defaults(handler=run_campaign_prepare_workflow)

    campaign_plan = campaign_subparsers.add_parser("plan", help="Build a ranked candidate campaign plan.")
    campaign_plan.add_argument("--batch", help="Simulation batch namespace for derived input/report defaults.")
    campaign_plan.add_argument("--candidate", type=Path, action="append", default=[])
    campaign_plan.add_argument("--input-root", type=Path)
    campaign_plan.add_argument("--budget", type=int, default=5)
    campaign_plan.add_argument("--include-selftests", action="store_true", help="Include module selftest outputs when scanning an input root.")
    campaign_plan.add_argument("--write-report", type=Path)

    campaign_plan.set_defaults(handler=run_campaign_plan_workflow)

    lab = subparsers.add_parser("lab", help="Lab integration workflows.")
    lab_subparsers = lab.add_subparsers(dest="lab_command", required=True)

    lab_pack = lab_subparsers.add_parser("pack", help="Build a file-backed lab request pack from a candidate.")
    lab_pack.add_argument("candidate", type=Path)
    lab_pack.add_argument("--lane", choices=["recovery", "authoritative"], default="recovery")
    lab_pack.add_argument("--batch", help="Simulation batch namespace for derived lab request output defaults.")
    lab_pack.add_argument("--instrument-profile", type=Path)
    lab_pack.add_argument("--output-dir", type=Path)

    lab_pack.set_defaults(handler=run_lab_pack_workflow)

    lab_ingest = lab_subparsers.add_parser("ingest", help="Ingest lab results back into a surfaced candidate.")
    lab_ingest.add_argument("candidate", type=Path)
    lab_ingest.add_argument("--request-pack", type=Path, required=True)
    lab_ingest.add_argument("--result-packet", type=Path, required=True)
    lab_ingest.add_argument("--calibration-snapshot", type=Path, required=True)
    lab_ingest.add_argument("--lineage-record", type=Path, required=True)
    lab_ingest.add_argument("--batch", help="Simulation batch namespace for derived ingestion output defaults.")
    lab_ingest.add_argument("--variant", help="Simulation variant name within the batch namespace.")
    lab_ingest.add_argument("--output", type=Path)

    lab_ingest.set_defaults(handler=run_lab_ingest_workflow)

    queue = subparsers.add_parser("queue", help="Repo-local execution queue workflows.")
    queue_subparsers = queue.add_subparsers(dest="queue_command", required=True)

    queue_enqueue = queue_subparsers.add_parser("enqueue", help="Validate and enqueue jobs from a queue manifest.")
    queue_enqueue.add_argument("--manifest", type=Path, required=True)

    def queue_enqueue_handler(args: argparse.Namespace) -> int:
        result = enqueue_manifest(args.manifest)
        if not result.get("valid", False):
            print("QUEUE ENQUEUE FAILED")
            for error in result.get("errors", []):
                print(f"- {error}")
            return 1
        print(json.dumps(result, indent=2))
        return 0

    queue_enqueue.set_defaults(handler=queue_enqueue_handler)

    queue_list = queue_subparsers.add_parser("list", help="List current queue items.")
    queue_list.add_argument("--limit", type=int, default=200)
    queue_list.add_argument("--state")
    queue_list.add_argument("--job-type")
    queue_list.add_argument("--reason-code")

    def queue_list_handler(args: argparse.Namespace) -> int:
        report = refresh_queue_report()
        items = filtered_queue_items(limit=args.limit, state=args.state, job_type=args.job_type, reason_code=args.reason_code)
        print(
            json.dumps(
                {
                    "filters": {
                        "state": args.state,
                        "job_type": args.job_type,
                        "reason_code": args.reason_code,
                    },
                    "state_counts": report["state_counts"],
                    "reason_code_summary": report["reason_code_summary"],
                    "items": items,
                },
                indent=2,
            )
        )
        return 0

    queue_list.set_defaults(handler=queue_list_handler)

    queue_show = queue_subparsers.add_parser("show", help="Show one queue item with payload, history, and latest state.")
    queue_show.add_argument("queue_id")

    def queue_show_handler(args: argparse.Namespace) -> int:
        item = get_queue_item(args.queue_id)
        if not item:
            raise SystemExit(f"error: queue item not found: {args.queue_id}")
        print(json.dumps(queue_show_payload(item), indent=2))
        return 0

    queue_show.set_defaults(handler=queue_show_handler)

    queue_log = queue_subparsers.add_parser("log", help="Print the chronological audit log for one queue item.")
    queue_log.add_argument("queue_id")

    def queue_log_handler(args: argparse.Namespace) -> int:
        item = get_queue_item(args.queue_id)
        if not item:
            raise SystemExit(f"error: queue item not found: {args.queue_id}")
        print(json.dumps({"queue_id": args.queue_id, "entries": load_queue_log(args.queue_id)}, indent=2))
        return 0

    queue_log.set_defaults(handler=queue_log_handler)

    queue_run = queue_subparsers.add_parser("run", help="Run queued jobs with a single local worker.")
    run_mode = queue_run.add_mutually_exclusive_group(required=True)
    run_mode.add_argument("--once", action="store_true")
    run_mode.add_argument("--daemon", action="store_true")
    queue_run.add_argument("--poll-seconds", type=float, default=2.0)
    queue_run.add_argument("--lease-seconds", type=int, default=300)

    def queue_run_handler(args: argparse.Namespace) -> int:
        worker_id = build_queue_worker_id()
        exit_code = 0
        while True:
            recovered = recover_expired_queue_leases()
            for record in recovered:
                record_lease_recovery(record)
            item = claim_next_queue_item(lease_owner=worker_id, lease_expires_utc=lease_expiration(args.lease_seconds))
            if not item:
                refresh_queue_report()
                if args.once:
                    return exit_code
                time.sleep(max(0.1, args.poll_seconds))
                continue
            append_queue_log(
                str(item["queue_id"]),
                "LEASED",
                {"worker_id": worker_id},
                state_before="QUEUED",
                state_after="LEASED",
            )
            try:
                exit_code = process_queue_item(item, worker_id=worker_id)
            except SystemExit as exc:
                exit_code = int(exc.code) if isinstance(exc.code, int) else 1
            except Exception:
                exit_code = 1
            if args.once:
                return exit_code

    queue_run.set_defaults(handler=queue_run_handler)

    queue_retry = queue_subparsers.add_parser("retry", help="Requeue a blocked or terminal queue item.")
    queue_retry.add_argument("queue_id")

    def queue_retry_handler(args: argparse.Namespace) -> int:
        item = get_queue_item(args.queue_id)
        if not item:
            raise SystemExit(f"error: queue item not found: {args.queue_id}")
        update_queue_item(args.queue_id, state="QUEUED", clear_lease=True)
        updated = persist_manual_queue_action(
            args.queue_id,
            event="MANUAL_RETRY",
            previous_state=str(item["state"]),
            new_state="QUEUED",
            operator_hint="Operator manually requeued this item for another attempt.",
        )
        print(json.dumps(updated, indent=2))
        return 0

    queue_retry.set_defaults(handler=queue_retry_handler)

    queue_cancel = queue_subparsers.add_parser("cancel", help="Cancel a queued or blocked queue item.")
    queue_cancel.add_argument("queue_id")

    def queue_cancel_handler(args: argparse.Namespace) -> int:
        item = get_queue_item(args.queue_id)
        if not item:
            raise SystemExit(f"error: queue item not found: {args.queue_id}")
        if item["state"] == "SUCCEEDED":
            raise SystemExit("error: cannot cancel a succeeded queue item.")
        update_queue_item(args.queue_id, state="CANCELLED", clear_lease=True)
        updated = persist_manual_queue_action(
            args.queue_id,
            event="MANUAL_CANCEL",
            previous_state=str(item["state"]),
            new_state="CANCELLED",
            operator_hint="Operator manually cancelled this queue item.",
        )
        print(json.dumps(updated, indent=2))
        return 0

    queue_cancel.set_defaults(handler=queue_cancel_handler)

    queue_unblock = queue_subparsers.add_parser("unblock", help="Force a blocked queue item back to QUEUED.")
    queue_unblock.add_argument("queue_id")
    queue_unblock.add_argument("--force", action="store_true", required=True)

    def queue_unblock_handler(args: argparse.Namespace) -> int:
        item = get_queue_item(args.queue_id)
        if not item:
            raise SystemExit(f"error: queue item not found: {args.queue_id}")
        if item["state"] != "BLOCKED":
            raise SystemExit("error: queue unblock --force only applies to BLOCKED items.")
        update_queue_item(args.queue_id, state="QUEUED", clear_lease=True)
        updated = persist_manual_queue_action(
            args.queue_id,
            event="MANUAL_UNBLOCK",
            previous_state=str(item["state"]),
            new_state="QUEUED",
            operator_hint="Operator forced this blocked queue item back to QUEUED.",
        )
        print(json.dumps(updated, indent=2))
        return 0

    queue_unblock.set_defaults(handler=queue_unblock_handler)

    readiness = subparsers.add_parser("readiness", help="Print a condensed readiness summary from current bootstrap artifacts.")

    def readiness_handler(_args: argparse.Namespace) -> int:
        bootstrap_report = load_json(Path(resolve_module("m06")["bootstrap_report"]))
        summary = {
            "system_status": bootstrap_report.get("system_status", ""),
            "ordinary_recovery_ready": bootstrap_report.get("ordinary_recovery_ready", False),
            "ordinary_authoritative_ready": bootstrap_report.get("ordinary_authoritative_ready", False),
            "ordinary_testing_ready": bootstrap_report.get("ordinary_testing_ready", False),
            "subsystem_recovery_ready": bootstrap_report.get("subsystem_recovery_ready", False),
            "subsystem_authoritative_ready": bootstrap_report.get("subsystem_authoritative_ready", False),
            "subsystem_testing_ready": bootstrap_report.get("subsystem_testing_ready", False),
            "ordinary_recovery_blockers": bootstrap_report.get("ordinary_recovery_blockers", []),
            "ordinary_authoritative_blockers": bootstrap_report.get("ordinary_authoritative_blockers", []),
            "subsystem_recovery_blockers": bootstrap_report.get("subsystem_recovery_blockers", []),
            "subsystem_authoritative_blockers": bootstrap_report.get("subsystem_authoritative_blockers", []),
        }
        print(json.dumps(summary, indent=2))
        return 0

    readiness.set_defaults(handler=readiness_handler)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())

