from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from .e01_mm_execution_sheet_sync import (
        ensure_sheet_sync_block,
        preview_execution_sheet_sync,
        sync_execution_sheet,
    )
    from .e01_mm_reconciliation import (
        RECONCILIATION_REASON_CODES,
        ensure_reconciliation_block,
        reconcile_queue_manifest,
    )
except ImportError:
    from e01_mm_execution_sheet_sync import (
        ensure_sheet_sync_block,
        preview_execution_sheet_sync,
        sync_execution_sheet,
    )
    from e01_mm_reconciliation import (
        RECONCILIATION_REASON_CODES,
        ensure_reconciliation_block,
        reconcile_queue_manifest,
    )

QUEUE_SCHEMA_VERSION = "1.1.0"
AUDIT_SNAPSHOT_VERSION = "1.0.0"
QUEUE_STATE_VALUES = {
    "QUEUED",
    "READY_FOR_PRECHECK",
    "BLOCKED_MISSING_BINDING",
    "READY_FOR_HARDWARE",
    "IN_PROGRESS",
    "BLOCKED_VALIDATION",
    "READY_FOR_AS_RUN_BINDING",
    "COMPLETE",
    "FAILED",
    "ESCALATED",
}
COMPLETE_STATES = {"COMPLETE", "FAILED", "ESCALATED"}
TRANSIENT_REASON_CODES = {
    "WAITING_FOR_AS_RUN_EVIDENCE",
    "MISSING_PROVENANCE_PATH",
    "PROVENANCE_PATH_NOT_FOUND",
    "OUTPUT_PATH_NOT_FOUND",
    "P_READ_NOT_CALIBRATED",
    "AS_RUN_BINDING_NOT_ACTIVE",
}
ESCALATION_REASON_CODES = {
    "NON_DISCRIMINATING_STOP",
    "SHAM_CONTROL_MISSING",
    "WITNESS_CHANNEL_MISSING",
    "BASELINE_DRIFT_OUT_OF_TOLERANCE",
    "FIELD_RETURN_CHECK_FAILED",
    "FIELD_CALIBRATION_UNTRUSTED",
}
TERMINAL_REASON_CODES = {
    "MALFORMED_QUEUE_MANIFEST",
    "MALFORMED_RUN_BINDING",
    "UNKNOWN_QUEUE_STATE",
    "SOURCE_PARSE_FAILED",
    "UNSUPPORTED_SOURCE_FORMAT",
}
PRE_RUN_EVIDENCE_KEYS = (
    "sample_map_path",
    "channel_map_path",
)
AS_RUN_EVIDENCE_KEYS = (
    "as_run_logbook_path",
    "fridge_log_path",
    "sample_map_path",
    "channel_map_path",
    "daq_record_path",
    "calibration_record_path",
)
OUTPUT_EVIDENCE_KEYS = (
    "raw_data_output_path",
    "metadata_output_path",
    "witness_trace_output_path",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def to_iso8601(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def from_iso8601(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="ascii"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")


def resolve_manifest_path(manifest_path: Path, linked_path: str) -> Path:
    path = Path(linked_path)
    if path.is_absolute():
        return path
    return (manifest_path.parent / path).resolve()


def record_event(manifest: dict[str, Any], state: str, event: str, reason_codes: list[str], checked_at: str) -> None:
    history = manifest.setdefault("history", [])
    history.append(
        {
            "state": state,
            "event": event,
            "reason_codes": reason_codes,
            "checked_at": checked_at,
        }
    )


def make_validator_result(
    validator_name: str,
    passed: bool,
    severity: str,
    reason_codes: list[str],
    details: list[str],
    checked_at: str,
) -> dict[str, Any]:
    return {
        "validator_name": validator_name,
        "passed": passed,
        "severity": severity,
        "reason_codes": reason_codes,
        "details": details,
        "checked_at": checked_at,
    }


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def has_suspected_onset_and_high_field(values: list[float]) -> bool:
    non_zero = sorted({abs(float(value)) for value in values if abs(float(value)) > 0.0})
    if len(non_zero) < 2:
        return False
    return non_zero[-1] > non_zero[0]


def validate_pre_run_binding(run_binding: dict[str, Any], evidence_paths: dict[str, Any] | None = None) -> dict[str, Any]:
    checked_at = to_iso8601(utc_now())
    reason_codes: list[str] = []
    details: list[str] = []
    evidence_paths = evidence_paths or {}

    if not isinstance(run_binding, dict):
        return make_validator_result(
            "pre_run_validator",
            False,
            "fail",
            ["MALFORMED_RUN_BINDING"],
            ["Run-binding payload is not a JSON object."],
            checked_at,
        )

    hardware_binding = run_binding.get("hardware_binding", {})
    target_device_ids = ensure_list(hardware_binding.get("target_device_ids"))
    if not target_device_ids:
        reason_codes.append("MISSING_HARDWARE_BINDING")
        details.append("target_device_ids must contain at least one device before pre-run readiness.")

    if not is_non_empty_string(hardware_binding.get("witness_channel_id")):
        reason_codes.append("MISSING_WITNESS_CHANNEL")
        details.append("witness_channel_id must be bound before acquisition.")

    matched_geometry_ids = hardware_binding.get("matched_geometry_device_ids")
    if matched_geometry_ids is None or not isinstance(matched_geometry_ids, list):
        reason_codes.append("MISSING_MATCHED_GEOMETRY_BINDING")
        details.append("matched_geometry_device_ids must be explicitly bound or set to [].")

    field_program = run_binding.get("field_program", {})
    field_steps = [float(value) for value in ensure_list(field_program.get("field_steps"))]
    selected_fields = [float(value) for value in ensure_list(field_program.get("selected_fields"))]
    probe_schedule = field_program.get("dwell_probe_schedule", {})
    probe_fields = [float(value) for value in ensure_list(probe_schedule.get("probe_fields"))]
    dwell_times = ensure_list(probe_schedule.get("dwell_times"))

    if not field_steps:
        reason_codes.append("MISSING_FIELD_PROGRAM")
        details.append("field_steps must define the minimum symmetric loop.")

    if not selected_fields:
        reason_codes.append("MISSING_SELECTED_FIELDS")
        details.append("selected_fields must include zero, onset, and high-field points.")

    if selected_fields and field_steps:
        field_step_set = {float(value) for value in field_steps}
        if any(float(value) not in field_step_set for value in selected_fields):
            reason_codes.append("SELECTED_FIELDS_NOT_SUBSET")
            details.append("selected_fields must remain a subset of field_steps.")

    if selected_fields:
        if 0.0 not in {float(value) for value in selected_fields} or not has_suspected_onset_and_high_field(selected_fields):
            reason_codes.append("MISSING_REQUIRED_SELECTED_FIELD_REGIONS")
            details.append("selected_fields must include zero, a suspected onset region, and a higher field.")

    if probe_fields:
        if len(probe_fields) != len(dwell_times):
            reason_codes.append("PROBE_SCHEDULE_LENGTH_MISMATCH")
            details.append("probe_fields and dwell_times must have equal length.")
        elif 0.0 not in {float(value) for value in probe_fields} or not has_suspected_onset_and_high_field(probe_fields):
            reason_codes.append("MISSING_REQUIRED_DWELL_REGIONS")
            details.append("probe_fields must include zero, onset, and high-field coverage.")
    else:
        reason_codes.append("MISSING_DWELL_PROBE_SCHEDULE")
        details.append("dwell_probe_schedule must be populated before pre-run readiness.")

    if not is_non_empty_string(field_program.get("field_unit")):
        reason_codes.append("FIELD_UNIT_INCONSISTENT")
        details.append("field_unit must be explicit before queueing hardware execution.")

    control_requirements = run_binding.get("control_requirements", {})
    if not bool(control_requirements.get("zfc_required")):
        reason_codes.append("TRUE_ZFC_REQUIRED")
        details.append("zfc_required must remain true.")
    if not bool(control_requirements.get("fc_required")):
        reason_codes.append("NONZERO_FC_REQUIRED")
        details.append("fc_required must remain true.")
    if not bool(control_requirements.get("sham_timing_required")):
        reason_codes.append("SHAM_CONTROL_MISSING")
        details.append("sham_timing_required cannot be disabled.")
    if not bool(control_requirements.get("package_witness_required")):
        reason_codes.append("WITNESS_CHANNEL_MISSING")
        details.append("package_witness_required cannot be disabled.")

    for evidence_key in PRE_RUN_EVIDENCE_KEYS:
        evidence_value = evidence_paths.get(evidence_key)
        if evidence_value is None:
            reason_codes.append("MISSING_PROVENANCE_PATH")
            details.append(f"{evidence_key} must be declared for pre-run binding provenance.")

    severity = "pass" if not reason_codes else "block"
    return make_validator_result("pre_run_validator", not reason_codes, severity, reason_codes, details, checked_at)


def detect_as_run_evidence(manifest_path: Path | None, manifest: dict[str, Any]) -> bool:
    evidence_paths = manifest.get("required_evidence_paths", {})
    candidate_paths: list[str] = []
    for key in OUTPUT_EVIDENCE_KEYS:
        value = evidence_paths.get(key)
        if is_non_empty_string(value):
            candidate_paths.append(value)

    run_binding = manifest.get("run_binding", {})
    data_capture = run_binding.get("data_capture", {})
    for key in OUTPUT_EVIDENCE_KEYS:
        value = data_capture.get(key)
        if is_non_empty_string(value):
            candidate_paths.append(value)

    if manifest_path is None:
        return False

    for candidate in candidate_paths:
        resolved = resolve_manifest_path(manifest_path, candidate)
        if resolved.exists():
            return True
    return False


def validate_as_run_binding(manifest_path: Path | None, manifest: dict[str, Any]) -> dict[str, Any]:
    checked_at = to_iso8601(utc_now())
    if not isinstance(manifest, dict):
        return make_validator_result(
            "as_run_validator",
            False,
            "fail",
            ["MALFORMED_QUEUE_MANIFEST"],
            ["Queue manifest is not a JSON object."],
            checked_at,
        )

    stop_condition_reasons = ensure_list(manifest.get("stop_condition_reasons"))
    if stop_condition_reasons:
        reason_codes = [str(code) for code in stop_condition_reasons]
        return make_validator_result(
            "as_run_validator",
            False,
            "escalate",
            reason_codes,
            ["The queue item was marked with stop-condition reasons and is therefore non-discriminating."],
            checked_at,
        )

    reconciliation = ensure_reconciliation_block(manifest)
    if reconciliation["status"] == "failed":
        return make_validator_result(
            "as_run_validator",
            False,
            "fail",
            reconciliation["reason_codes"],
            reconciliation["details"],
            checked_at,
        )
    if reconciliation["status"] == "blocked":
        return make_validator_result(
            "as_run_validator",
            False,
            "block",
            reconciliation["reason_codes"] or ["MISSING_REQUIRED_SOURCE_FIELD"],
            reconciliation["details"],
            checked_at,
        )

    run_binding = manifest.get("run_binding")
    if not isinstance(run_binding, dict):
        return make_validator_result(
            "as_run_validator",
            False,
            "fail",
            ["MALFORMED_RUN_BINDING"],
            ["Queue manifest is missing a valid run_binding payload."],
            checked_at,
        )

    reason_codes: list[str] = []
    details: list[str] = []

    if run_binding.get("binding_context") != "AS_RUN_BINDING":
        reason_codes.append("AS_RUN_BINDING_NOT_ACTIVE")
        details.append("binding_context must switch to AS_RUN_BINDING before as-run completion.")

    run_metadata = run_binding.get("run_metadata", {})
    for field_name in ("operator", "run_date", "lab_location"):
        if not is_non_empty_string(run_metadata.get(field_name)):
            reason_codes.append("MISSING_RUN_METADATA")
            details.append(f"run_metadata.{field_name} must be bound from as-run records.")

    cooldown_id = run_binding.get("cooldown_id")
    if not is_non_empty_string(cooldown_id):
        reason_codes.append("MISSING_COOLDOWN_ID")
        details.append("cooldown_id must be bound from the as-run logbook or fridge log.")

    evidence_paths = manifest.get("required_evidence_paths", {})
    if manifest_path is not None:
        for evidence_key in AS_RUN_EVIDENCE_KEYS:
            evidence_value = evidence_paths.get(evidence_key)
            if not is_non_empty_string(evidence_value):
                reason_codes.append("MISSING_PROVENANCE_PATH")
                details.append(f"{evidence_key} must be declared before as-run validation.")
                continue
            resolved = resolve_manifest_path(manifest_path, evidence_value)
            if not resolved.exists():
                reason_codes.append("PROVENANCE_PATH_NOT_FOUND")
                details.append(f"{evidence_key} does not exist: {resolved}")

    fixed_settings = run_binding.get("fixed_settings", {})
    if fixed_settings.get("P_read") is None or not bool(run_binding.get("binding_checks", {}).get("p_read_device_calibrated")):
        reason_codes.append("P_READ_NOT_CALIBRATED")
        details.append("P_read must be bound as the calibrated at-device readout power.")

    if fixed_settings.get("T_base") is None:
        reason_codes.append("MISSING_T_BASE")
        details.append("T_base must be bound from the stabilized measurement start.")

    field_program = run_binding.get("field_program", {})
    if not is_non_empty_string(field_program.get("field_unit")) or not bool(run_binding.get("binding_checks", {}).get("field_unit_consistent")):
        reason_codes.append("FIELD_UNIT_INCONSISTENT")
        details.append("field_unit must be explicit and the field_unit_consistent check must be true.")

    data_capture = run_binding.get("data_capture", {})
    if manifest_path is not None:
        for output_key in OUTPUT_EVIDENCE_KEYS:
            output_value = data_capture.get(output_key) or evidence_paths.get(output_key)
            if not is_non_empty_string(output_value):
                reason_codes.append("OUTPUT_PATH_NOT_FOUND")
                details.append(f"{output_key} must point to an existing as-run file or directory.")
                continue
            resolved = resolve_manifest_path(manifest_path, output_value)
            if not resolved.exists():
                reason_codes.append("OUTPUT_PATH_NOT_FOUND")
                details.append(f"{output_key} does not exist: {resolved}")

    binding_checks = run_binding.get("binding_checks", {})
    if not bool(binding_checks.get("selected_fields_subset_of_field_steps")):
        reason_codes.append("SELECTED_FIELDS_NOT_SUBSET")
        details.append("selected_fields_subset_of_field_steps must be true.")
    if not bool(binding_checks.get("probe_schedule_lengths_match")):
        reason_codes.append("PROBE_SCHEDULE_LENGTH_MISMATCH")
        details.append("probe_schedule_lengths_match must be true.")
    if not bool(binding_checks.get("output_paths_exist")):
        reason_codes.append("OUTPUT_PATH_NOT_FOUND")
        details.append("output_paths_exist must be true before completion.")

    if run_binding.get("binding_status") != "AS_RUN_BOUND":
        reason_codes.append("BINDING_STATUS_INCOMPLETE")
        details.append("binding_status must reach AS_RUN_BOUND before queue completion.")

    if any(code in ESCALATION_REASON_CODES for code in reason_codes):
        severity = "escalate"
    elif any(code in TERMINAL_REASON_CODES for code in reason_codes):
        severity = "fail"
    elif reason_codes:
        severity = "block"
    else:
        severity = "pass"

    return make_validator_result("as_run_validator", not reason_codes, severity, reason_codes, details, checked_at)


def create_queue_manifest(
    queue_item_id: str,
    branch_slug: str,
    run_binding_path: str,
    execution_sheet_path: str,
    run_binding: dict[str, Any],
    *,
    cooldown_id: str | None = None,
    required_evidence_paths: dict[str, Any] | None = None,
    max_retry_count: int = 3,
) -> dict[str, Any]:
    timestamp = to_iso8601(utc_now())
    return {
        "queue_schema_version": QUEUE_SCHEMA_VERSION,
        "queue_item_id": queue_item_id,
        "branch_slug": branch_slug,
        "cooldown_id": cooldown_id,
        "queue_state": "QUEUED",
        "run_binding_path": run_binding_path,
        "execution_sheet_path": execution_sheet_path,
        "required_evidence_paths": required_evidence_paths
        or {
            "as_run_logbook_path": None,
            "fridge_log_path": None,
            "sample_map_path": None,
            "channel_map_path": None,
            "daq_record_path": None,
            "calibration_record_path": None,
            "raw_data_output_path": None,
            "metadata_output_path": None,
            "witness_trace_output_path": None,
        },
        "retry_count": 0,
        "max_retry_count": max_retry_count,
        "last_validator_result": None,
        "escalation_reason": None,
        "lease_owner": None,
        "lease_acquired_at": None,
        "lease_expires_at": None,
        "created_at": timestamp,
        "updated_at": timestamp,
        "stop_condition_reasons": [],
        "reconciliation": {
            "status": "not_run",
            "reconciled_at": None,
            "populated_fields": [],
            "missing_fields": [],
            "source_conflicts": [],
            "evidence_summary": {},
            "reason_codes": [],
            "details": [],
        },
        "sheet_sync": {
            "status": "not_run",
            "synced_at": None,
            "updated_fields": [],
            "skipped_fields": [],
            "reason_codes": [],
        },
        "history": [
            {
                "state": "QUEUED",
                "event": "manifest_created",
                "reason_codes": [],
                "checked_at": timestamp,
            }
        ],
        "run_binding": deepcopy(run_binding),
    }


def load_queue_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    ensure_reconciliation_block(manifest)
    ensure_sheet_sync_block(manifest)
    run_binding_path = manifest.get("run_binding_path")
    if is_non_empty_string(run_binding_path):
        resolved = resolve_manifest_path(manifest_path, str(run_binding_path))
        if resolved.exists():
            manifest["run_binding"] = read_json(resolved)
    return manifest


def write_queue_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    write_json(manifest_path, manifest)


def persist_run_binding(manifest_path: Path, manifest: dict[str, Any]) -> bool:
    run_binding_path = manifest.get("run_binding_path")
    if not is_non_empty_string(run_binding_path):
        return False
    resolved = resolve_manifest_path(manifest_path, str(run_binding_path))
    write_json(resolved, manifest["run_binding"])
    return True


def build_audit_snapshot_path(audit_dir: Path, queue_item_id: str, processed_at: str) -> Path:
    safe_queue_item_id = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in queue_item_id)
    safe_timestamp = processed_at.replace(":", "").replace("-", "").replace(".", "").replace("Z", "Z_")
    return audit_dir / f"{safe_queue_item_id}_{safe_timestamp}.json"


def write_audit_snapshot(audit_dir: Path, snapshot: dict[str, Any]) -> Path:
    audit_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = build_audit_snapshot_path(audit_dir, str(snapshot["queue_item_id"]), str(snapshot["processed_at"]))
    collision_index = 1
    while snapshot_path.exists():
        snapshot_path = snapshot_path.with_name(f"{snapshot_path.stem}_{collision_index}{snapshot_path.suffix}")
        collision_index += 1
    write_json(snapshot_path, snapshot)
    return snapshot_path


def classify_item_outcome(updated_manifest: dict[str, Any], previous_state: str) -> str:
    queue_state = updated_manifest.get("queue_state")
    if queue_state == "COMPLETE":
        return "completed"
    if queue_state == "FAILED":
        return "failed"
    if queue_state == "ESCALATED":
        return "escalated"
    if queue_state in {"BLOCKED_MISSING_BINDING", "BLOCKED_VALIDATION"}:
        return "blocked"
    if queue_state != previous_state:
        return "advanced"
    return "unchanged"


def looks_like_queue_manifest(path: Path) -> bool:
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return isinstance(payload, dict) and "queue_item_id" in payload and "queue_schema_version" in payload


def process_queue_manifest(
    manifest_path: Path,
    *,
    worker_id: str,
    lease_duration_seconds: int = 300,
    audit_dir: Path | None = None,
) -> dict[str, Any]:
    manifest = load_queue_manifest(manifest_path)
    previous_state = str(manifest.get("queue_state"))
    processed_at = to_iso8601(utc_now())

    if lease_is_active(manifest, worker_id, from_iso8601(processed_at)):
        snapshot = {
            "snapshot_version": AUDIT_SNAPSHOT_VERSION,
            "queue_item_id": manifest.get("queue_item_id"),
            "worker_id": worker_id,
            "processed_at": processed_at,
            "queue_state_before": previous_state,
            "queue_state_after": previous_state,
            "reconciliation": manifest.get("reconciliation"),
            "sheet_sync": manifest.get("sheet_sync"),
            "last_validator_result": manifest.get("last_validator_result"),
            "escalation_reason": manifest.get("escalation_reason"),
            "run_binding_path": str(resolve_manifest_path(manifest_path, str(manifest.get("run_binding_path")))),
            "queue_manifest_path": str(manifest_path),
            "outcome": "skipped_leased",
            "skip_reason": f"active lease held by {manifest.get('lease_owner')}",
        }
        snapshot_path = write_audit_snapshot(audit_dir, snapshot) if audit_dir is not None else None
        return {
            "queue_item_id": manifest.get("queue_item_id"),
            "queue_state_before": previous_state,
            "queue_state_after": previous_state,
            "outcome": "skipped_leased",
            "audit_snapshot_path": str(snapshot_path) if snapshot_path is not None else None,
            "reason_codes": [],
            "last_validator_result": manifest.get("last_validator_result"),
        }

    updated_manifest = advance_queue_manifest(
        manifest_path,
        manifest,
        worker_id=worker_id,
        lease_duration_seconds=lease_duration_seconds,
    )
    persist_run_binding(manifest_path, updated_manifest)
    sync_execution_sheet(manifest_path, updated_manifest, write_changes=True)
    write_queue_manifest(manifest_path, updated_manifest)

    outcome = classify_item_outcome(updated_manifest, previous_state)
    snapshot = {
        "snapshot_version": AUDIT_SNAPSHOT_VERSION,
        "queue_item_id": updated_manifest.get("queue_item_id"),
        "worker_id": worker_id,
        "processed_at": processed_at,
        "queue_state_before": previous_state,
        "queue_state_after": updated_manifest.get("queue_state"),
        "reconciliation": updated_manifest.get("reconciliation"),
        "sheet_sync": updated_manifest.get("sheet_sync"),
        "last_validator_result": updated_manifest.get("last_validator_result"),
        "escalation_reason": updated_manifest.get("escalation_reason"),
        "run_binding_path": str(resolve_manifest_path(manifest_path, str(updated_manifest.get("run_binding_path")))),
        "queue_manifest_path": str(manifest_path),
        "outcome": outcome,
    }
    snapshot_path = None
    meaningful_snapshot = (
        previous_state != updated_manifest.get("queue_state")
        or updated_manifest.get("reconciliation", {}).get("status") in {"failed", "blocked"}
        or bool(updated_manifest.get("reconciliation", {}).get("source_conflicts"))
    )
    if audit_dir is not None and meaningful_snapshot:
        snapshot_path = write_audit_snapshot(audit_dir, snapshot)

    return {
        "queue_item_id": updated_manifest.get("queue_item_id"),
        "queue_state_before": previous_state,
        "queue_state_after": updated_manifest.get("queue_state"),
        "outcome": outcome,
        "audit_snapshot_path": str(snapshot_path) if snapshot_path is not None else None,
        "reason_codes": updated_manifest["last_validator_result"]["reason_codes"]
        if isinstance(updated_manifest.get("last_validator_result"), dict)
        else [],
        "last_validator_result": updated_manifest.get("last_validator_result"),
        "sheet_sync": updated_manifest.get("sheet_sync"),
    }


def process_queue_directory(
    queue_dir: Path,
    *,
    worker_id: str,
    lease_duration_seconds: int = 300,
    audit_dir: Path | None = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for manifest_path in sorted(queue_dir.glob("*.json")):
        if not looks_like_queue_manifest(manifest_path):
            continue
        results.append(
            process_queue_manifest(
                manifest_path,
                worker_id=worker_id,
                lease_duration_seconds=lease_duration_seconds,
                audit_dir=audit_dir,
            )
        )

    summary = {
        "processed_count": len(results),
        "completed_count": sum(1 for result in results if result["outcome"] == "completed"),
        "blocked_count": sum(1 for result in results if result["outcome"] == "blocked"),
        "failed_count": sum(1 for result in results if result["outcome"] == "failed"),
        "escalated_count": sum(1 for result in results if result["outcome"] == "escalated"),
        "skipped_leased_count": sum(1 for result in results if result["outcome"] == "skipped_leased"),
        "advanced_count": sum(1 for result in results if result["outcome"] == "advanced"),
        "unchanged_count": sum(1 for result in results if result["outcome"] == "unchanged"),
        "items": results,
    }
    return summary


def lease_is_active(manifest: dict[str, Any], worker_id: str, now: datetime) -> bool:
    owner = manifest.get("lease_owner")
    if owner is None:
        return False
    if owner == worker_id:
        return False
    expires_at = from_iso8601(manifest.get("lease_expires_at"))
    return expires_at is not None and expires_at > now


def claim_lease(manifest: dict[str, Any], worker_id: str, now: datetime, lease_duration_seconds: int) -> None:
    if lease_is_active(manifest, worker_id, now):
        raise RuntimeError(f"Queue item is already leased by {manifest['lease_owner']}.")
    manifest["lease_owner"] = worker_id
    manifest["lease_acquired_at"] = to_iso8601(now)
    manifest["lease_expires_at"] = to_iso8601(now + timedelta(seconds=lease_duration_seconds))


def clear_lease(manifest: dict[str, Any]) -> None:
    manifest["lease_owner"] = None
    manifest["lease_acquired_at"] = None
    manifest["lease_expires_at"] = None


def set_state(manifest: dict[str, Any], state: str, event: str, reason_codes: list[str], checked_at: str) -> None:
    manifest["queue_state"] = state
    manifest["updated_at"] = checked_at
    record_event(manifest, state, event, reason_codes, checked_at)


def advance_queue_manifest(
    manifest_path: Path | None,
    manifest: dict[str, Any],
    *,
    worker_id: str,
    lease_duration_seconds: int = 300,
) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise RuntimeError("Queue manifest payload must be a JSON object.")

    now = utc_now()
    checked_at = to_iso8601(now)
    claim_lease(manifest, worker_id, now, lease_duration_seconds)

    if manifest_path is not None:
        reconcile_queue_manifest(manifest_path, manifest)

    state = manifest.get("queue_state")
    if state not in QUEUE_STATE_VALUES:
        manifest["last_validator_result"] = make_validator_result(
            "queue_transition",
            False,
            "fail",
            ["UNKNOWN_QUEUE_STATE"],
            [f"Queue state is not supported: {state}"],
            checked_at,
        )
        manifest["escalation_reason"] = "UNKNOWN_QUEUE_STATE"
        set_state(manifest, "FAILED", "unknown_state", ["UNKNOWN_QUEUE_STATE"], checked_at)
        clear_lease(manifest)
        return manifest

    if state in COMPLETE_STATES:
        clear_lease(manifest)
        return manifest

    reconciliation = ensure_reconciliation_block(manifest)
    if reconciliation["status"] == "failed":
        manifest["last_validator_result"] = make_validator_result(
            "reconciliation",
            False,
            "fail",
            reconciliation["reason_codes"],
            reconciliation["details"],
            reconciliation["reconciled_at"] or checked_at,
        )
        manifest["escalation_reason"] = reconciliation["reason_codes"][0] if reconciliation["reason_codes"] else "SOURCE_PARSE_FAILED"
        set_state(manifest, "FAILED", "reconciliation_failed", reconciliation["reason_codes"], checked_at)
        clear_lease(manifest)
        return manifest

    if ensure_list(manifest.get("stop_condition_reasons")):
        reason_codes = [str(value) for value in ensure_list(manifest.get("stop_condition_reasons"))]
        manifest["last_validator_result"] = make_validator_result(
            "queue_transition",
            False,
            "escalate",
            reason_codes,
            ["Stop conditions are present; the queue item is escalated."],
            checked_at,
        )
        manifest["escalation_reason"] = reason_codes[0]
        set_state(manifest, "ESCALATED", "stop_condition", reason_codes, checked_at)
        clear_lease(manifest)
        return manifest

    if state == "QUEUED":
        set_state(manifest, "READY_FOR_PRECHECK", "automatic_precheck_entry", [], checked_at)
        clear_lease(manifest)
        return manifest

    if state in {"READY_FOR_PRECHECK", "BLOCKED_MISSING_BINDING"}:
        if reconciliation["status"] == "blocked":
            manifest["last_validator_result"] = make_validator_result(
                "reconciliation",
                False,
                "block",
                reconciliation["reason_codes"] or ["MISSING_REQUIRED_SOURCE_FIELD"],
                reconciliation["details"],
                reconciliation["reconciled_at"] or checked_at,
            )
            set_state(manifest, "BLOCKED_MISSING_BINDING", "reconciliation_blocked", reconciliation["reason_codes"], checked_at)
            clear_lease(manifest)
            return manifest

        result = validate_pre_run_binding(manifest.get("run_binding", {}), manifest.get("required_evidence_paths", {}))
        manifest["last_validator_result"] = result
        if result["passed"]:
            set_state(manifest, "READY_FOR_HARDWARE", "pre_run_validated", [], result["checked_at"])
        else:
            set_state(manifest, "BLOCKED_MISSING_BINDING", "pre_run_blocked", result["reason_codes"], result["checked_at"])
        clear_lease(manifest)
        return manifest

    if state == "READY_FOR_HARDWARE":
        if detect_as_run_evidence(manifest_path, manifest):
            set_state(manifest, "IN_PROGRESS", "as_run_evidence_detected", [], checked_at)
            manifest["last_validator_result"] = make_validator_result(
                "hardware_waiter",
                True,
                "pass",
                [],
                ["At least one as-run evidence path now exists."],
                checked_at,
            )
        else:
            manifest["last_validator_result"] = make_validator_result(
                "hardware_waiter",
                False,
                "block",
                ["WAITING_FOR_AS_RUN_EVIDENCE"],
                ["No as-run evidence paths exist yet; remain queued for hardware execution."],
                checked_at,
            )
        clear_lease(manifest)
        return manifest

    if state == "IN_PROGRESS":
        if reconciliation["status"] == "blocked":
            manifest["last_validator_result"] = make_validator_result(
                "reconciliation",
                False,
                "block",
                reconciliation["reason_codes"] or ["MISSING_REQUIRED_SOURCE_FIELD"],
                reconciliation["details"],
                reconciliation["reconciled_at"] or checked_at,
            )
        if manifest.get("run_binding", {}).get("binding_context") == "AS_RUN_BINDING":
            set_state(manifest, "READY_FOR_AS_RUN_BINDING", "binding_context_switched", [], checked_at)
            manifest["last_validator_result"] = make_validator_result(
                "binding_context_monitor",
                True,
                "pass",
                [],
                ["binding_context is now AS_RUN_BINDING."],
                checked_at,
            )
        else:
            manifest["last_validator_result"] = make_validator_result(
                "binding_context_monitor",
                False,
                "block",
                ["AS_RUN_BINDING_NOT_ACTIVE"],
                ["Waiting for run_binding.binding_context to switch to AS_RUN_BINDING."],
                checked_at,
            )
        clear_lease(manifest)
        return manifest

    if state in {"READY_FOR_AS_RUN_BINDING", "BLOCKED_VALIDATION"}:
        result = validate_as_run_binding(manifest_path, manifest)
        manifest["last_validator_result"] = result
        if result["passed"]:
            set_state(manifest, "COMPLETE", "as_run_validated", [], result["checked_at"])
            clear_lease(manifest)
            return manifest
        if result["severity"] == "escalate":
            manifest["escalation_reason"] = result["reason_codes"][0]
            set_state(manifest, "ESCALATED", "as_run_escalated", result["reason_codes"], result["checked_at"])
            clear_lease(manifest)
            return manifest
        if result["severity"] == "fail":
            manifest["escalation_reason"] = result["reason_codes"][0]
            set_state(manifest, "FAILED", "terminal_validation_failure", result["reason_codes"], result["checked_at"])
            clear_lease(manifest)
            return manifest

        manifest["retry_count"] = int(manifest.get("retry_count", 0)) + 1
        if int(manifest["retry_count"]) >= int(manifest.get("max_retry_count", 3)) and any(
            code not in TRANSIENT_REASON_CODES for code in result["reason_codes"]
        ):
            manifest["escalation_reason"] = "VALIDATION_RETRY_EXHAUSTED"
            set_state(manifest, "FAILED", "validation_retry_exhausted", result["reason_codes"], result["checked_at"])
        else:
            set_state(manifest, "BLOCKED_VALIDATION", "as_run_blocked", result["reason_codes"], result["checked_at"])
        clear_lease(manifest)
        return manifest

    clear_lease(manifest)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage the E01 autonomous execution queue.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a queue manifest from a run-binding file.")
    create_parser.add_argument("--queue-item-id", required=True)
    create_parser.add_argument("--branch-slug", default="e01_mm_flux_history_hysteresis")
    create_parser.add_argument("--run-binding-path", required=True)
    create_parser.add_argument("--execution-sheet-path", required=True)
    create_parser.add_argument("--output-path", required=True)

    tick_parser = subparsers.add_parser("tick", help="Advance a queue manifest by one worker tick.")
    tick_parser.add_argument("--manifest-path", required=True)
    tick_parser.add_argument("--worker-id", required=True)
    tick_parser.add_argument("--lease-duration-seconds", type=int, default=300)

    directory_parser = subparsers.add_parser("tick-directory", help="Advance every queue manifest in a directory once.")
    directory_parser.add_argument("--queue-dir", required=True)
    directory_parser.add_argument("--worker-id", required=True)
    directory_parser.add_argument("--lease-duration-seconds", type=int, default=300)

    run_once_parser = subparsers.add_parser("run-once", help="Discover queue manifests, process each once, and emit a scheduler-friendly summary.")
    run_once_parser.add_argument("--queue-dir", required=True)
    run_once_parser.add_argument("--worker-id", required=True)
    run_once_parser.add_argument("--lease-duration-seconds", type=int, default=300)
    run_once_parser.add_argument("--audit-dir")

    dry_run_parser = subparsers.add_parser("reconcile-dry-run", help="Show proposed run-binding updates without writing files.")
    dry_run_parser.add_argument("--manifest-path", required=True)

    return parser.parse_args(argv)


def command_create(args: argparse.Namespace) -> int:
    run_binding_path = Path(args.run_binding_path).resolve()
    manifest_path = Path(args.output_path).resolve()
    run_binding = read_json(run_binding_path)
    manifest = create_queue_manifest(
        queue_item_id=args.queue_item_id,
        branch_slug=args.branch_slug,
        run_binding_path=str(run_binding_path),
        execution_sheet_path=str(Path(args.execution_sheet_path).resolve()),
        run_binding=run_binding,
    )
    write_queue_manifest(manifest_path, manifest)
    return 0


def command_tick(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest_path).resolve()
    process_queue_manifest(
        manifest_path,
        worker_id=args.worker_id,
        lease_duration_seconds=args.lease_duration_seconds,
    )
    return 0


def command_tick_directory(args: argparse.Namespace) -> int:
    queue_dir = Path(args.queue_dir).resolve()
    process_queue_directory(
        queue_dir,
        worker_id=args.worker_id,
        lease_duration_seconds=args.lease_duration_seconds,
    )
    return 0


def command_run_once(args: argparse.Namespace) -> int:
    queue_dir = Path(args.queue_dir).resolve()
    audit_dir = Path(args.audit_dir).resolve() if is_non_empty_string(args.audit_dir) else (queue_dir / "audit")
    summary = process_queue_directory(
        queue_dir,
        worker_id=args.worker_id,
        lease_duration_seconds=args.lease_duration_seconds,
        audit_dir=audit_dir,
    )
    print(json.dumps(summary, indent=2))
    return 0


def command_reconcile_dry_run(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest_path).resolve()
    manifest = load_queue_manifest(manifest_path)
    reconciled = reconcile_queue_manifest(manifest_path, manifest)
    print(
        json.dumps(
            {
                "queue_item_id": reconciled.get("queue_item_id"),
                "queue_state": reconciled.get("queue_state"),
                "reconciliation": reconciled.get("reconciliation"),
                "sheet_sync_preview": preview_execution_sheet_sync(manifest_path, reconciled),
                "proposed_run_binding": reconciled.get("run_binding"),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "create":
        return command_create(args)
    if args.command == "tick":
        return command_tick(args)
    if args.command == "tick-directory":
        return command_tick_directory(args)
    if args.command == "run-once":
        return command_run_once(args)
    if args.command == "reconcile-dry-run":
        return command_reconcile_dry_run(args)
    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
