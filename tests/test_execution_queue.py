from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
QDP_CONTROL_SRC = ROOT / "packages" / "qdp_control" / "src"
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_VALIDATION_SRC = ROOT / "packages" / "qdp_validation" / "src"

for path in (QDP_CONTROL_SRC, QDP_IO_SRC, QDP_VALIDATION_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow.qdp_runtime import qdp_cli
from qdp_control import campaign_planner as planner
from qdp_control import control_plane
from qdp_control import lab_workflows as lab
from qdp_control import queue as qdp_queue
from qdp_io.artifacts import stable_hash


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def copy_fixture(relative_source: str, destination: Path) -> Path:
    source = ROOT / relative_source
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


@pytest.fixture
def queue_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    state_dir = tmp_path / "state"
    reports_dir = tmp_path / "reports" / "system"
    manifests_dir = state_dir / "queue_manifests"
    logs_dir = state_dir / "queue_logs"
    db_path = state_dir / "control_plane.sqlite3"
    queue_report = reports_dir / "queue_report.json"

    monkeypatch.setattr(control_plane, "CONTROL_PLANE_DB", db_path)
    monkeypatch.setattr(qdp_queue, "QUEUE_MANIFESTS_DIR", manifests_dir)
    monkeypatch.setattr(qdp_queue, "QUEUE_LOGS_DIR", logs_dir)
    monkeypatch.setattr(qdp_queue, "QUEUE_REPORT", queue_report)
    monkeypatch.setattr(qdp_cli, "CONTROL_PLANE_DB", db_path)
    monkeypatch.setattr(qdp_cli, "QUEUE_REPORT", queue_report)
    monkeypatch.setattr(qdp_cli, "RUN_LEDGER_REPORT", reports_dir / "run_ledger.json")
    monkeypatch.setattr(qdp_cli, "record_run", lambda **kwargs: {"run_id": "QDPRUN-TEST"})
    original_resolve_module = qdp_cli.resolve_module

    def patched_resolve_module(module_key: str):
        module = original_resolve_module(module_key)
        if module_key.lower() == "m06":
            updated = dict(module)
            updated["bootstrap_report"] = tmp_path / "reports" / "m06" / "bootstrap_report.json"
            return updated
        return module

    monkeypatch.setattr(qdp_cli, "resolve_module", patched_resolve_module)
    control_plane.initialize()
    return {
        "tmp_path": tmp_path,
        "db_path": db_path,
        "queue_report": queue_report,
    }


def test_control_plane_recovers_stale_queue_leases(queue_env: dict) -> None:
    control_plane.insert_queue_item(
        {
            "queue_id": "QDPQUE-STALE0000000001",
            "job_type": "check",
            "job_payload": {"lane": "recovery"},
            "state": "QUEUED",
            "priority": 100,
            "attempt_count": 0,
            "max_attempts": 3,
        }
    )

    leased = control_plane.claim_next_queue_item(lease_owner="worker-a", lease_expires_utc="2000-01-01T00:00:00+00:00")
    assert leased["state"] == "LEASED"

    expired = control_plane.recover_expired_queue_leases()
    assert expired[0]["queue_id"] == "QDPQUE-STALE0000000001"
    assert control_plane.get_queue_item("QDPQUE-STALE0000000001")["state"] == "QUEUED"

    qdp_queue.record_lease_recovery(expired[0])
    report = json.loads(queue_env["queue_report"].read_text(encoding="utf-8"))
    assert report["lease_recoveries"] == 1
    assert report["latest_reason_code_counts"]["STALE_LEASE_RECOVERED"] == 1
    assert report["recent_recoveries"][0]["event"] == "LEASE_RECOVERED"
    assert report["latest_activity"][-1]["event"] == "LEASE_RECOVERED"


def test_manifest_validation_rejects_missing_paths_and_cycles(queue_env: dict, tmp_path: Path) -> None:
    manifest_path = write_json(
        tmp_path / "queue_manifest.json",
        {
            "manifest_id": "queue-invalid",
            "jobs": [
                {
                    "job_id": "pack",
                    "job_type": "lab_pack",
                    "payload": {"candidate_path": "missing_candidate.json"},
                    "depends_on": "ingest",
                },
                {
                    "job_id": "ingest",
                    "job_type": "lab_ingest",
                    "payload": {
                        "candidate_path": str(tmp_path / "candidate.json"),
                        "request_pack_path": str(tmp_path / "request_pack.json"),
                        "result_packet_path": str(tmp_path / "missing_result.json"),
                        "calibration_snapshot_path": str(tmp_path / "missing_calibration.json"),
                        "lineage_record_path": str(tmp_path / "missing_lineage.json"),
                    },
                    "depends_on": "pack",
                },
            ],
        },
    )

    result = qdp_queue.load_queue_manifest(manifest_path)

    assert result["valid"] is False
    assert any("candidate_path does not exist" in error for error in result["errors"])
    assert any("dependency cycle detected" in error for error in result["errors"])


def test_manifest_validation_allows_declared_dependency_artifact(queue_env: dict, tmp_path: Path) -> None:
    candidate_path = copy_fixture(
        "artifacts/outputs/m06/bootstrap/run_1/CASE_7_CONFIRMED_READY_BRANCH/CASE_7_CONFIRMED_READY_BRANCH_candidate.json",
        tmp_path / "inputs" / "candidate.json",
    )
    result_packet_path = copy_fixture(
        "artifacts/lab/fixtures/QDPLAB-77FC92FFD3214625_result_packet.json",
        tmp_path / "fixtures" / "result_packet.json",
    )
    calibration_snapshot_path = copy_fixture(
        "artifacts/lab/fixtures/QDPLAB-77FC92FFD3214625_calibration_snapshot.json",
        tmp_path / "fixtures" / "calibration_snapshot.json",
    )
    lineage_record_path = copy_fixture(
        "artifacts/lab/fixtures/QDPLAB-77FC92FFD3214625_lineage_record.json",
        tmp_path / "fixtures" / "lineage_record.json",
    )
    manifest_path = write_json(
        tmp_path / "manifest.json",
        {
            "manifest_id": "dependency-artifact",
            "jobs": [
                {
                    "job_id": "pack",
                    "job_type": "lab_pack",
                    "payload": {"candidate_path": str(candidate_path), "output_dir": str(tmp_path / "requests")},
                },
                {
                    "job_id": "ingest",
                    "job_type": "lab_ingest",
                    "payload": {
                        "candidate_path": str(candidate_path),
                        "request_pack_path": str(tmp_path / "requests" / "future_request_pack.json"),
                        "result_packet_path": str(result_packet_path),
                        "calibration_snapshot_path": str(calibration_snapshot_path),
                        "lineage_record_path": str(lineage_record_path),
                        "output": str(tmp_path / "updated_candidate.json"),
                    },
                    "depends_on": "pack",
                    "dependency_artifacts": ["request_pack_path"],
                },
            ],
        },
    )

    result = qdp_queue.load_queue_manifest(manifest_path)
    assert result["valid"] is True


def test_manifest_validation_rejects_ambiguous_dependency_artifact(queue_env: dict, tmp_path: Path) -> None:
    candidate_path = copy_fixture(
        "artifacts/outputs/m06/bootstrap/run_1/CASE_7_CONFIRMED_READY_BRANCH/CASE_7_CONFIRMED_READY_BRANCH_candidate.json",
        tmp_path / "inputs" / "candidate.json",
    )
    result_packet_path = copy_fixture(
        "artifacts/lab/fixtures/QDPLAB-77FC92FFD3214625_result_packet.json",
        tmp_path / "fixtures" / "result_packet.json",
    )
    calibration_snapshot_path = copy_fixture(
        "artifacts/lab/fixtures/QDPLAB-77FC92FFD3214625_calibration_snapshot.json",
        tmp_path / "fixtures" / "calibration_snapshot.json",
    )
    lineage_record_path = copy_fixture(
        "artifacts/lab/fixtures/QDPLAB-77FC92FFD3214625_lineage_record.json",
        tmp_path / "fixtures" / "lineage_record.json",
    )
    manifest_path = write_json(
        tmp_path / "manifest_ambiguous.json",
        {
            "manifest_id": "dependency-artifact-ambiguous",
            "jobs": [
                {
                    "job_id": "pack",
                    "job_type": "lab_pack",
                    "payload": {"candidate_path": str(candidate_path), "output_dir": str(tmp_path / "requests")},
                },
                {
                    "job_id": "ingest",
                    "job_type": "lab_ingest",
                    "payload": {
                        "candidate_path": str(candidate_path),
                        "request_pack_path": str(tmp_path / "requests" / "future_request_pack.json"),
                        "result_packet_path": str(result_packet_path),
                        "calibration_snapshot_path": str(calibration_snapshot_path),
                        "lineage_record_path": str(lineage_record_path),
                        "output": str(tmp_path / "updated_candidate.json"),
                    },
                    "depends_on": "pack",
                },
            ],
        },
    )

    result = qdp_queue.load_queue_manifest(manifest_path)
    assert result["valid"] is False
    assert any("dependency-produced" in error for error in result["errors"])


def test_queue_cli_enqueue_and_list(queue_env: dict, tmp_path: Path) -> None:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    manifest_path = write_json(
        tmp_path / "queue_manifest.json",
        {
            "manifest_id": "queue-list",
            "jobs": [
                {
                    "job_id": "check-1",
                    "job_type": "check",
                    "payload": {"lane": "recovery", "outputs_root": str(outputs_root), "skip_bootstrap": True},
                }
            ],
        },
    )

    assert qdp_cli.main(["queue", "enqueue", "--manifest", str(manifest_path)]) == 0
    assert qdp_cli.main(["queue", "list"]) == 0

    listed = control_plane.list_queue_items()
    assert listed[0]["state"] == "QUEUED"
    assert listed[0]["job_type"] == "check"


def test_queue_list_filters_show_and_log(queue_env: dict, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    manifest_path = write_json(
        tmp_path / "queue_manifest_filters.json",
        {
            "manifest_id": "queue-filters",
            "jobs": [
                {
                    "job_id": "check-1",
                    "job_type": "check",
                    "payload": {"lane": "recovery", "outputs_root": str(outputs_root), "skip_bootstrap": True},
                }
            ],
        },
    )

    assert qdp_cli.main(["queue", "enqueue", "--manifest", str(manifest_path)]) == 0
    capsys.readouterr()
    queue_id = control_plane.list_queue_items()[0]["queue_id"]
    control_plane.update_queue_item(
        queue_id,
        state="BLOCKED",
        last_error={
            "reason_code": "VALIDATION_FAILED",
            "operator_hint": "Inspect readiness blockers.",
            "message": "blocked",
            "details": {},
            "classification": "BLOCKED",
            "timestamp_utc": qdp_queue.utc_now(),
        },
        result_summary={
            "status": "BLOCKED",
            "reason_code": "VALIDATION_FAILED",
            "operator_hint": "Inspect readiness blockers.",
            "artifacts_verified": False,
        },
    )
    qdp_queue.append_queue_log(
        queue_id,
        "BLOCKED",
        {"message": "blocked"},
        state_before="RUNNING",
        state_after="BLOCKED",
        reason_code="VALIDATION_FAILED",
        operator_hint="Inspect readiness blockers.",
    )
    qdp_queue.refresh_queue_report()

    assert qdp_cli.main(["queue", "list", "--state", "BLOCKED", "--job-type", "check", "--reason-code", "VALIDATION_FAILED"]) == 0
    list_output = json.loads(capsys.readouterr().out)
    assert list_output["filters"] == {
        "state": "BLOCKED",
        "job_type": "check",
        "reason_code": "VALIDATION_FAILED",
    }
    assert len(list_output["items"]) == 1
    assert list_output["items"][0]["queue_id"] == queue_id
    assert list_output["reason_code_summary"]["VALIDATION_FAILED"] == 1

    assert qdp_cli.main(["queue", "show", queue_id]) == 0
    show_output = json.loads(capsys.readouterr().out)
    assert show_output["queue_id"] == queue_id
    assert show_output["state"] == "BLOCKED"
    assert show_output["latest_error"]["reason_code"] == "VALIDATION_FAILED"
    assert show_output["artifacts_verified"] is False

    assert qdp_cli.main(["queue", "log", queue_id]) == 0
    log_output = json.loads(capsys.readouterr().out)
    assert log_output["queue_id"] == queue_id
    assert [entry["event"] for entry in log_output["entries"]] == ["ENQUEUED", "BLOCKED"]
    assert log_output["entries"][-1]["state_before"] == "RUNNING"
    assert log_output["entries"][-1]["state_after"] == "BLOCKED"
    assert log_output["entries"][-1]["reason_code"] == "VALIDATION_FAILED"


def patch_campaign_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    outputs_root = tmp_path / "outputs"
    reports_root = tmp_path / "reports"
    monkeypatch.setattr(planner, "ROOT", tmp_path)
    monkeypatch.setattr(planner, "OUTPUTS_DIR", outputs_root)
    monkeypatch.setattr(planner, "REPORTS_DIR", reports_root)
    monkeypatch.setattr(planner, "CAMPAIGN_PREPARE_REPORT", reports_root / "campaigns" / "latest_prepare.json")
    monkeypatch.setattr(planner, "CAMPAIGN_PLAN_REPORT", reports_root / "campaigns" / "latest_plan.json")
    monkeypatch.setattr(planner, "load_latest_campaign", lambda: {})
    monkeypatch.setattr(planner, "upsert_campaign", lambda payload: None)
    monkeypatch.setattr(planner, "record_run", lambda **kwargs: None)
    monkeypatch.setattr(qdp_cli, "simulation_campaign_prepare_report_path", lambda batch: reports_root / "simulations" / batch / "campaign_prepare.json")
    monkeypatch.setattr(qdp_cli, "simulation_campaign_report_path", lambda batch: reports_root / "simulations" / batch / "campaign_plan.json")
    return outputs_root, reports_root


def test_queue_run_executes_campaign_prepare_then_plan(
    queue_env: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs_root, reports_root = patch_campaign_runtime(monkeypatch, tmp_path)
    batch = "sim_smoke_20260317"
    copy_fixture(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/confirmed_ready_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "confirmed_ready_candidate.json",
    )
    copy_fixture(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/scheduled_cross_device_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "scheduled_cross_device_candidate.json",
    )
    copy_fixture(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/baseline_reject_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "baseline_reject_candidate.json",
    )
    manifest_path = write_json(
        tmp_path / "campaign_queue_manifest.json",
        {
            "manifest_id": "campaign-chain",
            "jobs": [
                {
                    "job_id": "prepare",
                    "job_type": "campaign_prepare",
                    "payload": {"input_root": str(outputs_root), "batch": batch},
                },
                {
                    "job_id": "plan",
                    "job_type": "campaign_plan",
                    "payload": {"input_root": str(outputs_root), "batch": batch, "budget": 5},
                    "depends_on": "prepare",
                },
            ],
        },
    )

    assert qdp_cli.main(["queue", "enqueue", "--manifest", str(manifest_path)]) == 0
    assert qdp_cli.main(["queue", "run", "--once"]) == 0
    queued_items = control_plane.list_queue_items()
    assert [item["state"] for item in queued_items] == ["QUEUED", "SUCCEEDED"]

    assert qdp_cli.main(["queue", "run", "--once"]) == 0
    states = {item["job_type"]: item["state"] for item in control_plane.list_queue_items()}
    assert states["campaign_prepare"] == "SUCCEEDED"
    assert states["campaign_plan"] == "SUCCEEDED"
    assert (reports_root / "simulations" / batch / "m12" / "confirmed_ready_report.json").exists()
    assert (reports_root / "simulations" / batch / "campaign_plan.json").exists()


def patch_lab_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(lab, "LAB_REQUEST_REPORT", tmp_path / "reports" / "lab" / "latest_request_pack.json")
    monkeypatch.setattr(lab, "LAB_INGEST_REPORT", tmp_path / "reports" / "lab" / "latest_ingestion_report.json")
    monkeypatch.setattr(lab, "upsert_lab_request", lambda payload: None)
    monkeypatch.setattr(lab, "record_run", lambda **kwargs: None)


def expected_request_pack_path(candidate_path: Path, output_dir: Path, lane: str) -> Path:
    from modules.m12_experiment_design.runner import run_experiment_design

    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate, _ = run_experiment_design(candidate)
    instrument_profile = lab.default_instrument_profile(candidate)
    request_hash = stable_hash(
        {
            "candidate_id": candidate.get("candidate_id", ""),
            "lane": lane,
            "candidate_sha256": lab.sha256_file(candidate_path),
            "instrument_profile_id": instrument_profile["instrument_profile_id"],
        }
    )
    request_id = f"QDPLAB-{request_hash[:16].upper()}"
    return output_dir / str(candidate.get("candidate_id", "unnamed")) / f"{request_id}_request_pack.json"


def test_queue_run_executes_lab_pack_then_ingest(
    queue_env: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_lab_runtime(monkeypatch, tmp_path)
    candidate_path = copy_fixture(
        "artifacts/outputs/m06/bootstrap/run_1/CASE_7_CONFIRMED_READY_BRANCH/CASE_7_CONFIRMED_READY_BRANCH_candidate.json",
        tmp_path / "inputs" / "candidate.json",
    )
    output_dir = tmp_path / "lab_requests"
    request_pack_path = expected_request_pack_path(candidate_path, output_dir, "recovery")
    result_packet_path = copy_fixture(
        "artifacts/lab/fixtures/QDPLAB-77FC92FFD3214625_result_packet.json",
        tmp_path / "fixtures" / "result_packet.json",
    )
    calibration_snapshot_path = copy_fixture(
        "artifacts/lab/fixtures/QDPLAB-77FC92FFD3214625_calibration_snapshot.json",
        tmp_path / "fixtures" / "calibration_snapshot.json",
    )
    lineage_record_path = copy_fixture(
        "artifacts/lab/fixtures/QDPLAB-77FC92FFD3214625_lineage_record.json",
        tmp_path / "fixtures" / "lineage_record.json",
    )
    updated_candidate_path = tmp_path / "outputs" / "updated_candidate.json"
    manifest_path = write_json(
        tmp_path / "lab_queue_manifest.json",
        {
            "manifest_id": "lab-chain",
            "jobs": [
                {
                    "job_id": "pack",
                    "job_type": "lab_pack",
                    "payload": {"candidate_path": str(candidate_path), "lane": "recovery", "output_dir": str(output_dir)},
                },
                {
                    "job_id": "ingest",
                    "job_type": "lab_ingest",
                    "payload": {
                        "candidate_path": str(candidate_path),
                        "request_pack_path": str(request_pack_path),
                        "result_packet_path": str(result_packet_path),
                        "calibration_snapshot_path": str(calibration_snapshot_path),
                        "lineage_record_path": str(lineage_record_path),
                        "output": str(updated_candidate_path),
                    },
                    "depends_on": "pack",
                    "dependency_artifacts": ["request_pack_path"],
                },
            ],
        },
    )

    assert qdp_cli.main(["queue", "enqueue", "--manifest", str(manifest_path)]) == 0
    assert qdp_cli.main(["queue", "run", "--once"]) == 0
    assert request_pack_path.exists()

    assert qdp_cli.main(["queue", "run", "--once"]) == 0
    updated_candidate = json.loads(updated_candidate_path.read_text(encoding="utf-8"))
    states = {item["job_type"]: item["state"] for item in control_plane.list_queue_items()}
    assert states["lab_pack"] == "SUCCEEDED"
    assert states["lab_ingest"] == "SUCCEEDED"
    assert updated_candidate["cross_device_status"] == "CONFIRMED"
    assert updated_candidate["governance_outcome"] == "PROCEED"


def test_retryable_failure_requeues_then_succeeds(
    queue_env: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    copy_fixture(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/confirmed_ready_candidate.json",
        outputs_root / "confirmed_ready_candidate.json",
    )
    manifest_path = write_json(
        tmp_path / "retry_queue_manifest.json",
        {
            "manifest_id": "retryable-check",
            "jobs": [
                {
                    "job_id": "check-1",
                    "job_type": "check",
                    "payload": {"lane": "recovery", "outputs_root": str(outputs_root), "skip_bootstrap": True},
                }
            ],
        },
    )
    attempts = {"count": 0}

    def flaky_check(args):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise OSError("temporary file lock")
        write_json(qdp_cli.resolve_module("m06")["bootstrap_report"], {"ordinary_recovery_ready": True, "ordinary_recovery_blockers": []})
        return 0

    monkeypatch.setattr(qdp_cli, "run_check_workflow", flaky_check)
    assert qdp_cli.main(["queue", "enqueue", "--manifest", str(manifest_path)]) == 0
    assert qdp_cli.main(["queue", "run", "--once"]) == 1
    first = control_plane.list_queue_items()[0]
    assert first["state"] == "QUEUED"
    assert first["failure_history"][-1]["reason_code"] == "TEMPORARY_FILE_LOCK"
    assert qdp_cli.main(["queue", "run", "--once"]) == 0
    assert control_plane.list_queue_items()[0]["state"] == "SUCCEEDED"


def test_blocked_failure_stays_blocked_without_auto_retry(
    queue_env: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_path = copy_fixture(
        "artifacts/outputs/m06/bootstrap/run_1/CASE_7_CONFIRMED_READY_BRANCH/CASE_7_CONFIRMED_READY_BRANCH_candidate.json",
        tmp_path / "inputs" / "candidate.json",
    )
    request_pack_path = write_json(tmp_path / "inputs" / "request_pack.json", {"request_id": "QDPTEST"})
    result_packet_path = write_json(tmp_path / "inputs" / "result_packet.json", {"request_id": "QDPTEST"})
    calibration_snapshot_path = write_json(tmp_path / "inputs" / "calibration_snapshot.json", {"request_id": "QDPTEST"})
    lineage_record_path = write_json(tmp_path / "inputs" / "lineage_record.json", {"request_id": "QDPTEST"})
    manifest_path = write_json(
        tmp_path / "blocked_queue_manifest.json",
        {
            "manifest_id": "blocked-lab-ingest",
            "jobs": [
                {
                    "job_id": "ingest",
                    "job_type": "lab_ingest",
                    "payload": {
                        "candidate_path": str(candidate_path),
                        "request_pack_path": str(request_pack_path),
                        "result_packet_path": str(result_packet_path),
                        "calibration_snapshot_path": str(calibration_snapshot_path),
                        "lineage_record_path": str(lineage_record_path),
                        "output": str(tmp_path / "updated_candidate.json"),
                    },
                }
            ],
        },
    )

    monkeypatch.setattr(
        qdp_cli,
        "execute_queue_lab_ingest_job",
        lambda item, args: qdp_cli.queue_execution_result(
            status="BLOCKED",
            reason_code="GOVERNANCE_BLOCKED",
            operator_hint="Inspect governance outcome.",
            artifacts=[str(tmp_path / "updated_candidate.json")],
            details={"message": "blocked for governance"},
        ),
    )
    assert qdp_cli.main(["queue", "enqueue", "--manifest", str(manifest_path)]) == 0
    assert qdp_cli.main(["queue", "run", "--once"]) == 1
    item = control_plane.list_queue_items()[0]
    assert item["state"] == "BLOCKED"
    assert item["last_error"]["reason_code"] in {"GOVERNANCE_BLOCKED", "VALIDATION_FAILED"}


def test_missing_expected_artifact_retries_then_goes_terminal(
    queue_env: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    manifest_path = write_json(
        tmp_path / "missing_artifact_manifest.json",
        {
            "manifest_id": "missing-artifact",
            "jobs": [
                {
                    "job_id": "check-1",
                    "job_type": "check",
                    "payload": {"lane": "recovery", "outputs_root": str(outputs_root), "skip_bootstrap": True},
                    "max_attempts": 2,
                }
            ],
        },
    )
    monkeypatch.setattr(
        qdp_cli,
        "execute_queue_check_job",
        lambda item, args: qdp_cli.queue_execution_result(
            status="SUCCEEDED",
            reason_code="CHECK_READY",
            operator_hint="No operator action required.",
            artifacts=[str(tmp_path / "missing_bootstrap_report.json")],
            details={},
        ),
    )

    assert qdp_cli.main(["queue", "enqueue", "--manifest", str(manifest_path)]) == 0
    queue_id = control_plane.list_queue_items()[0]["queue_id"]
    assert qdp_cli.main(["queue", "run", "--once"]) == 1
    first = control_plane.get_queue_item(queue_id)
    assert first["state"] == "QUEUED"
    assert first["last_error"]["reason_code"] == "MISSING_EXPECTED_REPORT"
    assert qdp_cli.main(["queue", "run", "--once"]) == 1
    second = control_plane.get_queue_item(queue_id)
    assert second["state"] == "FAILED_TERMINAL"


def test_failure_history_is_bounded_and_manual_retry_preserves_history(
    queue_env: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    manifest_path = write_json(
        tmp_path / "history_manifest.json",
        {
            "manifest_id": "history-check",
            "jobs": [
                {
                    "job_id": "check-1",
                    "job_type": "check",
                    "payload": {"lane": "recovery", "outputs_root": str(outputs_root), "skip_bootstrap": True},
                    "max_attempts": 10,
                }
            ],
        },
    )
    def always_lock(item, args):
        raise OSError("temporary file lock")

    monkeypatch.setattr(qdp_cli, "execute_queue_check_job", always_lock)
    assert qdp_cli.main(["queue", "enqueue", "--manifest", str(manifest_path)]) == 0
    queue_id = control_plane.list_queue_items()[0]["queue_id"]
    for _ in range(6):
        assert qdp_cli.main(["queue", "run", "--once"]) == 1
    item = control_plane.get_queue_item(queue_id)
    assert item["state"] == "QUEUED"
    assert len(item["failure_history"]) == 5
    assert all(entry["reason_code"] == "TEMPORARY_FILE_LOCK" for entry in item["failure_history"])

    assert qdp_cli.main(["queue", "retry", queue_id]) == 0
    retried = control_plane.get_queue_item(queue_id)
    assert len(retried["failure_history"]) == 5
    assert retried["result_summary"]["last_manual_action"]["event"] == "MANUAL_RETRY"


def test_manual_unblock_and_cancel_append_audit_events(
    queue_env: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    manifest_path = write_json(
        tmp_path / "manual_actions_manifest.json",
        {
            "manifest_id": "manual-actions",
            "jobs": [
                {
                    "job_id": "check-1",
                    "job_type": "check",
                    "payload": {"lane": "recovery", "outputs_root": str(outputs_root), "skip_bootstrap": True},
                }
            ],
        },
    )
    monkeypatch.setattr(
        qdp_cli,
        "execute_queue_check_job",
        lambda item, args: qdp_cli.queue_execution_result(
            status="BLOCKED",
            reason_code="VALIDATION_FAILED",
            operator_hint="Inspect readiness blockers.",
            artifacts=[str(tmp_path / "missing_bootstrap_report.json")],
            details={"message": "blocked"},
        ),
    )

    assert qdp_cli.main(["queue", "enqueue", "--manifest", str(manifest_path)]) == 0
    queue_id = control_plane.list_queue_items()[0]["queue_id"]
    assert qdp_cli.main(["queue", "run", "--once"]) == 1

    blocked = control_plane.get_queue_item(queue_id)
    assert blocked["state"] == "BLOCKED"
    assert blocked["failure_history"][-1]["reason_code"] == "VALIDATION_FAILED"

    assert qdp_cli.main(["queue", "unblock", queue_id, "--force"]) == 0
    unblocked = control_plane.get_queue_item(queue_id)
    assert unblocked["state"] == "QUEUED"
    assert unblocked["result_summary"]["last_manual_action"]["event"] == "MANUAL_UNBLOCK"
    assert unblocked["failure_history"][-1]["reason_code"] == "VALIDATION_FAILED"

    assert qdp_cli.main(["queue", "cancel", queue_id]) == 0
    cancelled = control_plane.get_queue_item(queue_id)
    assert cancelled["state"] == "CANCELLED"
    assert cancelled["result_summary"]["last_manual_action"]["event"] == "MANUAL_CANCEL"
    assert cancelled["failure_history"][-1]["reason_code"] == "VALIDATION_FAILED"

    entries = qdp_queue.load_queue_log(queue_id)
    assert [entry["event"] for entry in entries][-3:] == ["BLOCKED", "MANUAL_UNBLOCK", "MANUAL_CANCEL"]
    assert entries[-2]["state_before"] == "BLOCKED"
    assert entries[-2]["state_after"] == "QUEUED"
    assert entries[-1]["state_before"] == "QUEUED"
    assert entries[-1]["state_after"] == "CANCELLED"

    report = json.loads(queue_env["queue_report"].read_text(encoding="utf-8"))
    assert report["blocked_items"] == []
    assert any(entry["event"] == "MANUAL_CANCEL" for entry in report["latest_activity"])
