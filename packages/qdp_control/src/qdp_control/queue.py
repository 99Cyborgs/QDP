from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from qdp_io.artifacts import artifact_report_header, dump_json, stable_hash, utc_now
from qdp_io.serialization import load_json
from .control_plane import (
    get_queue_item,
    insert_queue_item,
    list_queue_items,
    update_queue_item,
)
from tools.workflow.qdp_runtime.qdp_paths import QUEUE_LOGS_DIR, QUEUE_MANIFESTS_DIR, QUEUE_REPORT, ROOT


SUPPORTED_JOB_TYPES = {
    "check",
    "campaign_prepare",
    "campaign_plan",
    "lab_pack",
    "lab_ingest",
}
RETRYABLE_REASON_CODES = {
    "PROCESS_CRASH",
    "STALE_LEASE_RECOVERED",
    "TEMPORARY_FILE_LOCK",
    "MISSING_EXPECTED_REPORT",
}
BLOCKED_REASON_CODES = {
    "VALIDATION_FAILED",
    "AUTHORITATIVE_BLOCKERS",
    "SCHEMA_INVALID",
    "GOVERNANCE_BLOCKED",
    "MISSING_REQUIRED_INPUT",
    "INVALID_CAMPAIGN_STATE",
    "AMBIGUOUS_DEPENDENCY_ARTIFACT",
}
FAILURE_HISTORY_LIMIT = 5

# Missing paths may be accepted only when they are explicitly declared as
# artifacts produced by the immediate dependency and that transition is allowed.
DEPENDENCY_ARTIFACT_SPECS: Dict[str, Dict[str, Dict[str, str]]] = {
    "lab_pack": {
        "lab_ingest": {"request_pack_path": "request_pack_path"},
    }
}
def make_queue_id(*, manifest_id: str, job_id: str, job_type: str, payload: Dict[str, Any]) -> str:
    digest = stable_hash(
        {
            "manifest_id": manifest_id,
            "job_id": job_id,
            "job_type": job_type,
            "payload": payload,
        }
    )
    return f"QDPQUE-{digest[:16].upper()}"


def resolve_manifest_path(path: Path | str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def _normalize_path(value: str, *, base_dir: Path) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    else:
        path = path.resolve()
    return str(path)


def _normalize_path_list(values: Iterable[Any], *, base_dir: Path) -> List[str]:
    return [_normalize_path(str(item), base_dir=base_dir) for item in values]


def _require_fields(payload: Dict[str, Any], fields: Iterable[str], errors: List[str]) -> None:
    for field in fields:
        if field not in payload or payload[field] in {None, ""}:
            errors.append(f"payload.{field} is required")


def _validate_existing_path(path_str: str, *, expect_dir: bool, errors: List[str], label: str) -> None:
    path = Path(path_str)
    if not path.exists():
        errors.append(f"{label} does not exist: {path}")
        return
    if expect_dir and not path.is_dir():
        errors.append(f"{label} must be a directory: {path}")
    if not expect_dir and not path.is_file():
        errors.append(f"{label} must be a file: {path}")


def expected_dependency_artifact_fields(dependency_job_type: str, job_type: str) -> Dict[str, str]:
    return DEPENDENCY_ARTIFACT_SPECS.get(dependency_job_type, {}).get(job_type, {})


def dependency_job_type(depends_on: str | None, jobs: List[Dict[str, Any]]) -> str | None:
    if not depends_on:
        return None
    for job in jobs:
        if job["job_id"] == depends_on:
            return str(job["job_type"])
    return None


def normalize_dependency_artifacts(job: Dict[str, Any], jobs: List[Dict[str, Any]], *, errors: List[str]) -> List[str]:
    raw = job.get("dependency_artifacts", [])
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        errors.append(f"jobs[{job['manifest_index']}].dependency_artifacts must be a list when provided")
        return []
    dep_type = dependency_job_type(job.get("depends_on"), jobs)
    if not dep_type:
        errors.append(f"jobs[{job['manifest_index']}].dependency_artifacts requires depends_on")
        return []
    allowed = expected_dependency_artifact_fields(dep_type, str(job["job_type"]))
    normalized: List[str] = []
    for field in raw:
        value = str(field)
        if value not in allowed:
            errors.append(
                f"jobs[{job['manifest_index']}].dependency_artifacts contains unsupported field '{value}' for dependency {dep_type}->{job['job_type']}"
            )
            continue
        normalized.append(value)
    return normalized


def _normalize_payload(job_type: str, payload: Dict[str, Any], *, manifest_dir: Path) -> tuple[Dict[str, Any], List[str]]:
    normalized = dict(payload)
    errors: List[str] = []

    if job_type == "check":
        normalized["lane"] = str(normalized.get("lane", "recovery"))
        if normalized["lane"] not in {"recovery", "authoritative"}:
            errors.append("payload.lane must be 'recovery' or 'authoritative'")
        normalized["skip_bootstrap"] = bool(normalized.get("skip_bootstrap", False))
        normalized["repeat"] = int(normalized.get("repeat", 1))
        if normalized["repeat"] < 1:
            errors.append("payload.repeat must be >= 1")
        if "outputs_root" in normalized and normalized["outputs_root"] not in {None, ""}:
            normalized["outputs_root"] = _normalize_path(str(normalized["outputs_root"]), base_dir=manifest_dir)

    elif job_type == "campaign_prepare":
        candidate_paths = normalized.pop("candidate_paths", None)
        if candidate_paths is not None:
            if not isinstance(candidate_paths, list) or not candidate_paths:
                errors.append("payload.candidate_paths must be a non-empty list when provided")
            else:
                normalized["candidate_paths"] = _normalize_path_list(candidate_paths, base_dir=manifest_dir)
        elif "candidate_path" in normalized and normalized["candidate_path"] not in {None, ""}:
            normalized["candidate_paths"] = [_normalize_path(str(normalized.pop("candidate_path")), base_dir=manifest_dir)]
        else:
            normalized["candidate_paths"] = []
        if "input_root" in normalized and normalized["input_root"] not in {None, ""}:
            normalized["input_root"] = _normalize_path(str(normalized["input_root"]), base_dir=manifest_dir)

    elif job_type == "campaign_plan":
        candidate_paths = normalized.pop("candidate_paths", None)
        if candidate_paths is not None:
            if not isinstance(candidate_paths, list) or not candidate_paths:
                errors.append("payload.candidate_paths must be a non-empty list when provided")
            else:
                normalized["candidate_paths"] = _normalize_path_list(candidate_paths, base_dir=manifest_dir)
        elif "candidate_path" in normalized and normalized["candidate_path"] not in {None, ""}:
            normalized["candidate_paths"] = [_normalize_path(str(normalized.pop("candidate_path")), base_dir=manifest_dir)]
        else:
            normalized["candidate_paths"] = []
        if "input_root" in normalized and normalized["input_root"] not in {None, ""}:
            normalized["input_root"] = _normalize_path(str(normalized["input_root"]), base_dir=manifest_dir)
        normalized["budget"] = int(normalized.get("budget", 5))
        if normalized["budget"] < 0:
            errors.append("payload.budget must be >= 0")

    elif job_type == "lab_pack":
        _require_fields(normalized, ["candidate_path"], errors)
        if "candidate_path" in normalized and normalized["candidate_path"] not in {None, ""}:
            normalized["candidate_path"] = _normalize_path(str(normalized["candidate_path"]), base_dir=manifest_dir)
        normalized["lane"] = str(normalized.get("lane", "recovery"))
        if normalized["lane"] not in {"recovery", "authoritative"}:
            errors.append("payload.lane must be 'recovery' or 'authoritative'")
        if "instrument_profile" in normalized and normalized["instrument_profile"] not in {None, ""}:
            normalized["instrument_profile"] = _normalize_path(str(normalized["instrument_profile"]), base_dir=manifest_dir)
        if "output_dir" in normalized and normalized["output_dir"] not in {None, ""}:
            normalized["output_dir"] = _normalize_path(str(normalized["output_dir"]), base_dir=manifest_dir)

    elif job_type == "lab_ingest":
        _require_fields(
            normalized,
            [
                "candidate_path",
                "request_pack_path",
                "result_packet_path",
                "calibration_snapshot_path",
                "lineage_record_path",
            ],
            errors,
        )
        for field in [
            "candidate_path",
            "request_pack_path",
            "result_packet_path",
            "calibration_snapshot_path",
            "lineage_record_path",
        ]:
            if normalized.get(field) not in {None, ""}:
                normalized[field] = _normalize_path(str(normalized[field]), base_dir=manifest_dir)
        if "output" in normalized and normalized["output"] not in {None, ""}:
            normalized["output"] = _normalize_path(str(normalized["output"]), base_dir=manifest_dir)
    else:
        errors.append(f"Unsupported job_type: {job_type}")

    return normalized, errors


def validate_payload_paths_for_job(job: Dict[str, Any], jobs: List[Dict[str, Any]], *, errors: List[str]) -> None:
    payload = dict(job["payload"])
    dependency_fields = set(job.get("dependency_artifacts", []))
    dep_type = dependency_job_type(job.get("depends_on"), jobs)
    allowed_dependency_fields = set(expected_dependency_artifact_fields(dep_type or "", str(job["job_type"])))
    label_prefix = f"jobs[{job['manifest_index']}].payload"

    def validate_field(field: str, *, expect_dir: bool) -> None:
        value = payload.get(field)
        if value in {None, ""}:
            return
        path = Path(str(value))
        if path.exists():
            _validate_existing_path(str(path), expect_dir=expect_dir, errors=errors, label=f"{label_prefix}.{field}")
            return
        if field in dependency_fields:
            return
        if field in allowed_dependency_fields:
            errors.append(
                f"{label_prefix}.{field} is missing and could be dependency-produced; declare it in dependency_artifacts to disambiguate"
            )
            return
        errors.append(f"{label_prefix}.{field} does not exist: {path}")

    if job["job_type"] == "check":
        validate_field("outputs_root", expect_dir=True)
    elif job["job_type"] in {"campaign_prepare", "campaign_plan"}:
        validate_field("input_root", expect_dir=True)
        for candidate_path in payload.get("candidate_paths", []):
            if not Path(str(candidate_path)).exists():
                errors.append(f"{label_prefix}.candidate_paths contains missing file: {candidate_path}")
    elif job["job_type"] == "lab_pack":
        validate_field("candidate_path", expect_dir=False)
        validate_field("instrument_profile", expect_dir=False)
    elif job["job_type"] == "lab_ingest":
        for field in ["candidate_path", "request_pack_path", "result_packet_path", "calibration_snapshot_path", "lineage_record_path"]:
            validate_field(field, expect_dir=False)


def validate_manifest_payload(manifest: Dict[str, Any], *, manifest_path: Path) -> Dict[str, Any]:
    errors: List[str] = []
    manifest_id = str(manifest.get("manifest_id", "") or "").strip()
    if not manifest_id:
        errors.append("manifest_id is required")
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        errors.append("jobs must be a non-empty list")
        return {"valid": False, "errors": errors, "manifest_id": manifest_id, "jobs": []}

    seen_job_ids: set[str] = set()
    normalized_jobs: List[Dict[str, Any]] = []
    dependency_graph: Dict[str, str] = {}
    manifest_dir = manifest_path.parent
    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"jobs[{index}] must be an object")
            continue
        job_id = str(job.get("job_id", "") or "").strip()
        job_type = str(job.get("job_type", "") or "").strip()
        payload = job.get("payload", {})
        if not job_id:
            errors.append(f"jobs[{index}].job_id is required")
            continue
        if job_id in seen_job_ids:
            errors.append(f"duplicate job_id: {job_id}")
            continue
        seen_job_ids.add(job_id)
        if job_type not in SUPPORTED_JOB_TYPES:
            errors.append(f"jobs[{index}].job_type is not supported: {job_type}")
        if not isinstance(payload, dict):
            errors.append(f"jobs[{index}].payload must be an object")
            continue
        normalized_payload, payload_errors = _normalize_payload(job_type, payload, manifest_dir=manifest_dir)
        errors.extend(f"jobs[{index}].{message}" for message in payload_errors)
        depends_on = job.get("depends_on")
        if depends_on is not None and not isinstance(depends_on, str):
            errors.append(f"jobs[{index}].depends_on must be a string when provided")
        normalized_jobs.append(
            {
                "job_id": job_id,
                "job_type": job_type,
                "payload": normalized_payload,
                "priority": int(job.get("priority", 100)),
                "max_attempts": int(job.get("max_attempts", 3)),
                "depends_on": depends_on,
                "manifest_index": index,
                "dependency_artifacts": job.get("dependency_artifacts", []),
            }
        )

    local_ids = {job["job_id"] for job in normalized_jobs}
    for job in normalized_jobs:
        depends_on = job.get("depends_on")
        if depends_on and depends_on in local_ids:
            dependency_graph[job["job_id"]] = depends_on
        elif depends_on and not get_queue_item(depends_on):
            errors.append(f"jobs[{job['job_id']}].depends_on does not reference a local job_id or existing queue_id: {depends_on}")

    visited: set[str] = set()
    stack: set[str] = set()

    def visit(job_id: str) -> None:
        if job_id in visited:
            return
        if job_id in stack:
            errors.append(f"dependency cycle detected at job_id: {job_id}")
            return
        stack.add(job_id)
        parent = dependency_graph.get(job_id)
        if parent:
            visit(parent)
        stack.remove(job_id)
        visited.add(job_id)

    for job_id in dependency_graph:
        visit(job_id)

    for job in normalized_jobs:
        job["dependency_artifacts"] = normalize_dependency_artifacts(job, normalized_jobs, errors=errors)
        validate_payload_paths_for_job(job, normalized_jobs, errors=errors)

    return {
        "valid": not errors,
        "errors": errors,
        "manifest_id": manifest_id,
        "jobs": normalized_jobs,
    }


def load_queue_manifest(path: Path | str) -> Dict[str, Any]:
    manifest_path = resolve_manifest_path(path)
    payload = load_json(manifest_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Queue manifest root must be an object: {manifest_path}")
    result = validate_manifest_payload(payload, manifest_path=manifest_path)
    result["manifest_path"] = str(manifest_path)
    return result


def refresh_queue_report(path: Path | None = None) -> Dict[str, Any]:
    path = path or QUEUE_REPORT
    items = list_queue_items()
    state_counts: Dict[str, int] = {}
    latest_reason_code_counts: Dict[str, int] = {}
    retryable_failure_count = 0
    blocked_count = 0
    terminal_failure_count = 0
    active_items: List[Dict[str, Any]] = []
    blocked_items: List[Dict[str, Any]] = []
    retryable_items: List[Dict[str, Any]] = []
    recent_recoveries: List[Dict[str, Any]] = []
    latest_activity: List[Dict[str, Any]] = []
    for item in items:
        state = str(item["state"])
        state_counts[state] = state_counts.get(state, 0) + 1
        if state in {"LEASED", "RUNNING", "QUEUED"}:
            active_items.append(queue_item_overview(item))
        if state == "BLOCKED":
            blocked_count += 1
            blocked_items.append(queue_item_overview(item))
        if state == "FAILED_TERMINAL":
            terminal_failure_count += 1
        if state == "FAILED_RETRYABLE":
            retryable_items.append(queue_item_overview(item))
        retryable_failure_count += len(
            [entry for entry in item.get("failure_history", []) if isinstance(entry, dict) and entry.get("classification") == "RETRYABLE"]
        )
        if item.get("last_error") and isinstance(item["last_error"], dict):
            reason_code = str(item["last_error"].get("reason_code", "") or "")
            if reason_code:
                latest_reason_code_counts[reason_code] = latest_reason_code_counts.get(reason_code, 0) + 1
    lease_recoveries = 0
    if QUEUE_LOGS_DIR.exists():
        for log_path in QUEUE_LOGS_DIR.glob("*.jsonl"):
            try:
                for line in log_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    latest_activity.append(entry)
                    if entry.get("event") == "LEASE_RECOVERED":
                        lease_recoveries += 1
                        recent_recoveries.append(entry)
            except Exception:
                continue
    latest_activity = sorted(latest_activity, key=lambda entry: entry.get("timestamp_utc", ""))[-10:]
    recent_recoveries = sorted(recent_recoveries, key=lambda entry: entry.get("timestamp_utc", ""))[-10:]
    payload = {
        **artifact_report_header("QDP_V10_6_EXECUTION_QUEUE"),
        "queue_item_count": len(items),
        "state_counts": state_counts,
        "lease_recoveries": lease_recoveries,
        "retryable_failure_count": retryable_failure_count,
        "blocked_count": blocked_count,
        "terminal_failure_count": terminal_failure_count,
        "reason_code_summary": latest_reason_code_counts,
        "latest_reason_code_counts": latest_reason_code_counts,
        "active_items": active_items,
        "blocked_items": blocked_items,
        "retryable_items": retryable_items,
        "recent_recoveries": recent_recoveries,
        "latest_activity": latest_activity,
        "items": items,
    }
    dump_json(path, payload)
    return payload


def queue_log_path(queue_id: str) -> Path:
    return QUEUE_LOGS_DIR / f"{queue_id}.jsonl"


def queue_item_overview(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("job_payload", {})
    last_error = item.get("last_error") if isinstance(item.get("last_error"), dict) else {}
    result_summary = item.get("result_summary") if isinstance(item.get("result_summary"), dict) else {}
    return {
        "queue_id": item.get("queue_id"),
        "job_type": item.get("job_type"),
        "state": item.get("state"),
        "depends_on_queue_id": item.get("depends_on_queue_id"),
        "attempt_count": item.get("attempt_count"),
        "max_attempts": item.get("max_attempts"),
        "reason_code": last_error.get("reason_code") or result_summary.get("reason_code", ""),
        "operator_hint": last_error.get("operator_hint") or result_summary.get("operator_hint", ""),
        "job_id": payload.get("job_id", ""),
        "manifest_id": payload.get("manifest_id", ""),
    }


def append_queue_log(
    queue_id: str,
    event: str,
    payload: Dict[str, Any],
    *,
    state_before: str | None = None,
    state_after: str | None = None,
    reason_code: str | None = None,
    operator_hint: str | None = None,
) -> None:
    path = queue_log_path(queue_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    item = get_queue_item(queue_id)
    payload = dict(payload)
    entry = {
        "timestamp_utc": utc_now(),
        "event": event,
        "queue_id": queue_id,
        "job_type": item.get("job_type", payload.get("job_type", "")),
        "state_before": state_before if state_before is not None else payload.pop("state_before", None),
        "state_after": state_after if state_after is not None else item.get("state", payload.pop("state_after", None)),
        "reason_code": reason_code if reason_code is not None else payload.get("reason_code"),
        "operator_hint": operator_hint if operator_hint is not None else payload.get("operator_hint"),
        "payload": payload,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def load_queue_log(queue_id: str) -> List[Dict[str, Any]]:
    path = queue_log_path(queue_id)
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entries.append(json.loads(line))
    return sorted(entries, key=lambda entry: entry.get("timestamp_utc", ""))


def filtered_queue_items(
    *,
    limit: int = 200,
    state: str | None = None,
    job_type: str | None = None,
    reason_code: str | None = None,
) -> List[Dict[str, Any]]:
    items = list_queue_items(limit=limit)
    filtered: List[Dict[str, Any]] = []
    for item in items:
        last_error = item.get("last_error") if isinstance(item.get("last_error"), dict) else {}
        summary = item.get("result_summary") if isinstance(item.get("result_summary"), dict) else {}
        effective_reason = str(last_error.get("reason_code") or summary.get("reason_code", ""))
        if state and item.get("state") != state:
            continue
        if job_type and item.get("job_type") != job_type:
            continue
        if reason_code and effective_reason != reason_code:
            continue
        filtered.append(item)
    return filtered


def queue_show_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    result_summary = item.get("result_summary") if isinstance(item.get("result_summary"), dict) else {}
    return {
        "queue_id": item.get("queue_id"),
        "job_type": item.get("job_type"),
        "state": item.get("state"),
        "payload": item.get("job_payload", {}),
        "depends_on_queue_id": item.get("depends_on_queue_id"),
        "attempt_count": item.get("attempt_count"),
        "max_attempts": item.get("max_attempts"),
        "lease": {
            "lease_owner": item.get("lease_owner"),
            "lease_expires_utc": item.get("lease_expires_utc"),
        },
        "latest_error": item.get("last_error"),
        "failure_history": item.get("failure_history", []),
        "result_summary": result_summary,
        "artifacts_verified": bool(result_summary.get("artifacts_verified", False)),
        "last_manual_action": result_summary.get("last_manual_action"),
    }


def bounded_failure_history(existing: List[Dict[str, Any]] | None, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    history = list(existing or [])
    history.append(entry)
    return history[-FAILURE_HISTORY_LIMIT:]


def build_error_record(
    *,
    reason_code: str,
    operator_hint: str,
    message: str,
    details: Dict[str, Any] | None = None,
    classification: str,
) -> Dict[str, Any]:
    return {
        "reason_code": reason_code,
        "operator_hint": operator_hint,
        "message": message,
        "details": details or {},
        "classification": classification,
        "timestamp_utc": utc_now(),
    }


def enqueue_manifest(path: Path | str) -> Dict[str, Any]:
    manifest_result = load_queue_manifest(path)
    if not manifest_result["valid"]:
        return manifest_result

    manifest_id = manifest_result["manifest_id"]
    inserted: List[Dict[str, Any]] = []
    local_to_queue: Dict[str, str] = {}
    for job in manifest_result["jobs"]:
        queue_id = make_queue_id(
            manifest_id=manifest_id,
            job_id=job["job_id"],
            job_type=job["job_type"],
            payload=job["payload"],
        )
        local_to_queue[job["job_id"]] = queue_id
    for job in manifest_result["jobs"]:
        depends_on = job.get("depends_on")
        resolved_dependency = local_to_queue.get(depends_on, depends_on) if depends_on else None
        existing = get_queue_item(local_to_queue[job["job_id"]])
        if existing:
            return {
                "valid": False,
                "errors": [f"Queue item already exists for manifest job_id {job['job_id']}: {existing['queue_id']}"],
                "manifest_id": manifest_id,
            }
        record = {
            "queue_id": local_to_queue[job["job_id"]],
            "job_type": job["job_type"],
            "job_payload": {
                **job["payload"],
                "manifest_id": manifest_id,
                "job_id": job["job_id"],
                "manifest_path": manifest_result["manifest_path"],
                **({"dependency_artifacts": job["dependency_artifacts"]} if job.get("dependency_artifacts") else {}),
            },
            "state": "QUEUED",
            "priority": job.get("priority", 100),
            "attempt_count": 0,
            "max_attempts": job.get("max_attempts", 3),
            "depends_on_queue_id": resolved_dependency,
            "last_error": None,
            "result_summary": None,
            "failure_history": [],
        }
        insert_queue_item(record)
        append_queue_log(record["queue_id"], "ENQUEUED", {"job_type": record["job_type"], "depends_on_queue_id": resolved_dependency})
        inserted.append(get_queue_item(record["queue_id"]))

    QUEUE_MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_copy = QUEUE_MANIFESTS_DIR / f"{manifest_id}.json"
    dump_json(
        manifest_copy,
        {
            "manifest_id": manifest_id,
            "source_manifest_path": manifest_result["manifest_path"],
            "queue_ids_by_job_id": local_to_queue,
            "jobs": manifest_result["jobs"],
        },
    )
    refresh_queue_report()
    return {
        "valid": True,
        "manifest_id": manifest_id,
        "manifest_path": manifest_result["manifest_path"],
        "stored_manifest_path": str(manifest_copy),
        "inserted": inserted,
    }


def lease_expiration(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def mark_running(queue_id: str, *, worker_id: str, attempt_count: int) -> None:
    item = get_queue_item(queue_id)
    update_queue_item(
        queue_id,
        state="RUNNING",
        lease_owner=worker_id,
        attempt_count=attempt_count,
        clear_result_summary=True,
    )
    append_queue_log(
        queue_id,
        "RUNNING",
        {"worker_id": worker_id, "attempt_count": attempt_count},
        state_before=str(item.get("state", "")),
        state_after="RUNNING",
    )
    refresh_queue_report()


def mark_succeeded(queue_id: str, *, summary: Dict[str, Any]) -> None:
    item = get_queue_item(queue_id)
    update_queue_item(queue_id, state="SUCCEEDED", result_summary=summary, clear_lease=True, clear_last_error=True)
    append_queue_log(
        queue_id,
        "SUCCEEDED",
        summary,
        state_before=str(item.get("state", "")),
        state_after="SUCCEEDED",
        reason_code=str(summary.get("reason_code", "")),
        operator_hint=str(summary.get("operator_hint", "")),
    )
    refresh_queue_report()


def mark_failed_retryable(queue_id: str, *, error: Dict[str, Any]) -> None:
    item = get_queue_item(queue_id)
    history = bounded_failure_history(item.get("failure_history", []), error)
    update_queue_item(queue_id, state="FAILED_RETRYABLE", last_error=error, failure_history=history, clear_lease=True)
    append_queue_log(
        queue_id,
        "FAILED_RETRYABLE",
        error,
        state_before=str(item.get("state", "")),
        state_after="FAILED_RETRYABLE",
        reason_code=str(error.get("reason_code", "")),
        operator_hint=str(error.get("operator_hint", "")),
    )
    refresh_queue_report()


def requeue(queue_id: str, *, error: Dict[str, Any] | None = None) -> None:
    item = get_queue_item(queue_id)
    update_queue_item(queue_id, state="QUEUED", last_error=error, clear_lease=True)
    append_queue_log(
        queue_id,
        "QUEUED",
        error or {},
        state_before=str(item.get("state", "")),
        state_after="QUEUED",
        reason_code=str((error or {}).get("reason_code", "")),
        operator_hint=str((error or {}).get("operator_hint", "")),
    )
    refresh_queue_report()


def mark_blocked(queue_id: str, *, error: Dict[str, Any]) -> None:
    item = get_queue_item(queue_id)
    history = bounded_failure_history(item.get("failure_history", []), error)
    update_queue_item(queue_id, state="BLOCKED", last_error=error, failure_history=history, clear_lease=True)
    append_queue_log(
        queue_id,
        "BLOCKED",
        error,
        state_before=str(item.get("state", "")),
        state_after="BLOCKED",
        reason_code=str(error.get("reason_code", "")),
        operator_hint=str(error.get("operator_hint", "")),
    )
    refresh_queue_report()


def mark_failed_terminal(queue_id: str, *, error: Dict[str, Any]) -> None:
    item = get_queue_item(queue_id)
    history = bounded_failure_history(item.get("failure_history", []), error)
    update_queue_item(queue_id, state="FAILED_TERMINAL", last_error=error, failure_history=history, clear_lease=True)
    append_queue_log(
        queue_id,
        "FAILED_TERMINAL",
        error,
        state_before=str(item.get("state", "")),
        state_after="FAILED_TERMINAL",
        reason_code=str(error.get("reason_code", "")),
        operator_hint=str(error.get("operator_hint", "")),
    )
    refresh_queue_report()


def record_lease_recovery(record: Dict[str, Any]) -> None:
    queue_id = str(record["queue_id"])
    error = build_error_record(
        reason_code="STALE_LEASE_RECOVERED",
        operator_hint="Previous worker lease expired; queue item was returned to QUEUED.",
        message="Recovered expired queue lease.",
        details={
            "previous_state": record.get("previous_state"),
            "previous_lease_owner": record.get("previous_lease_owner"),
            "previous_lease_expires_utc": record.get("previous_lease_expires_utc"),
        },
        classification="RETRYABLE",
    )
    item = get_queue_item(queue_id)
    history = bounded_failure_history(item.get("failure_history", []), error)
    update_queue_item(queue_id, last_error=error, failure_history=history)
    append_queue_log(
        queue_id,
        "LEASE_RECOVERED",
        error,
        state_before=str(record.get("previous_state", "")),
        state_after=str(item.get("state", "")),
        reason_code=str(error.get("reason_code", "")),
        operator_hint=str(error.get("operator_hint", "")),
    )
    refresh_queue_report()
