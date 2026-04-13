from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from qdp_io.artifacts import utc_now
from tools.workflow.qdp_runtime.qdp_paths import CONTROL_PLANE_DB


def parse_utc(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None
    return datetime.fromisoformat(timestamp)


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = db_path or CONTROL_PLANE_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize(db_path: Path | None = None) -> None:
    db_path = db_path or CONTROL_PLANE_DB
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS run_ledger (
                run_id TEXT PRIMARY KEY,
                operation TEXT NOT NULL,
                lane TEXT NOT NULL,
                provenance_mode TEXT NOT NULL,
                status TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                first_seen_utc TEXT NOT NULL,
                last_seen_utc TEXT NOT NULL,
                occurrences INTEGER NOT NULL,
                summary_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lab_requests (
                request_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                scheduler_state TEXT NOT NULL,
                request_pack_path TEXT NOT NULL,
                result_packet_path TEXT,
                calibration_snapshot_path TEXT,
                lineage_record_path TEXT,
                updated_utc TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS campaign_runs (
                campaign_id TEXT PRIMARY KEY,
                created_utc TEXT NOT NULL,
                status TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                report_path TEXT NOT NULL,
                summary_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS execution_queue (
                queue_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                job_payload_json TEXT NOT NULL,
                state TEXT NOT NULL,
                priority INTEGER NOT NULL,
                attempt_count INTEGER NOT NULL,
                max_attempts INTEGER NOT NULL,
                depends_on_queue_id TEXT,
                lease_owner TEXT,
                lease_expires_utc TEXT,
                created_utc TEXT NOT NULL,
                updated_utc TEXT NOT NULL,
                last_error_json TEXT,
                result_summary_json TEXT,
                failure_history_json TEXT
            );
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(execution_queue)").fetchall()}
        if "failure_history_json" not in columns:
            conn.execute("ALTER TABLE execution_queue ADD COLUMN failure_history_json TEXT")


def upsert_run(record: Dict[str, Any], db_path: Path | None = None) -> None:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    with connect(db_path) as conn:
        existing = conn.execute("SELECT run_id, occurrences, first_seen_utc FROM run_ledger WHERE run_id = ?", (record["run_id"],)).fetchone()
        now = utc_now()
        if existing:
            conn.execute(
                """
                UPDATE run_ledger
                SET last_seen_utc = ?, occurrences = ?, summary_json = ?, status = ?, content_hash = ?, operation = ?, lane = ?, provenance_mode = ?
                WHERE run_id = ?
                """,
                (
                    now,
                    int(existing["occurrences"]) + 1,
                    json.dumps(record["summary"], sort_keys=True),
                    record["status"],
                    record["content_hash"],
                    record["operation"],
                    record["lane"],
                    record["provenance_mode"],
                    record["run_id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO run_ledger (
                    run_id, operation, lane, provenance_mode, status, content_hash, first_seen_utc, last_seen_utc, occurrences, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["run_id"],
                    record["operation"],
                    record["lane"],
                    record["provenance_mode"],
                    record["status"],
                    record["content_hash"],
                    now,
                    now,
                    1,
                    json.dumps(record["summary"], sort_keys=True),
                ),
            )


def list_runs(db_path: Path | None = None, *, limit: int = 200) -> List[Dict[str, Any]]:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT run_id, operation, lane, provenance_mode, status, content_hash, first_seen_utc, last_seen_utc, occurrences, summary_json
            FROM run_ledger
            ORDER BY last_seen_utc DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "run_id": row["run_id"],
            "operation": row["operation"],
            "lane": row["lane"],
            "provenance_mode": row["provenance_mode"],
            "status": row["status"],
            "content_hash": row["content_hash"],
            "first_seen_utc": row["first_seen_utc"],
            "last_seen_utc": row["last_seen_utc"],
            "occurrences": row["occurrences"],
            "summary": json.loads(row["summary_json"]),
        }
        for row in rows
    ]


def upsert_lab_request(record: Dict[str, Any], db_path: Path | None = None) -> None:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lab_requests (
                request_id, candidate_id, scheduler_state, request_pack_path, result_packet_path, calibration_snapshot_path, lineage_record_path, updated_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(request_id) DO UPDATE SET
                candidate_id = excluded.candidate_id,
                scheduler_state = excluded.scheduler_state,
                request_pack_path = excluded.request_pack_path,
                result_packet_path = excluded.result_packet_path,
                calibration_snapshot_path = excluded.calibration_snapshot_path,
                lineage_record_path = excluded.lineage_record_path,
                updated_utc = excluded.updated_utc
            """,
            (
                record["request_id"],
                record["candidate_id"],
                record["scheduler_state"],
                record["request_pack_path"],
                record.get("result_packet_path"),
                record.get("calibration_snapshot_path"),
                record.get("lineage_record_path"),
                utc_now(),
            ),
        )


def upsert_campaign(record: Dict[str, Any], db_path: Path | None = None) -> None:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO campaign_runs (campaign_id, created_utc, status, input_hash, report_path, summary_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(campaign_id) DO UPDATE SET
                status = excluded.status,
                input_hash = excluded.input_hash,
                report_path = excluded.report_path,
                summary_json = excluded.summary_json
            """,
            (
                record["campaign_id"],
                utc_now(),
                record["status"],
                record["input_hash"],
                record["report_path"],
                json.dumps(record["summary"], sort_keys=True),
            ),
        )


def load_latest_campaign(db_path: Path | None = None) -> Dict[str, Any]:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT campaign_id, created_utc, status, input_hash, report_path, summary_json
            FROM campaign_runs
            ORDER BY created_utc DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return {}
    return {
        "campaign_id": row["campaign_id"],
        "created_utc": row["created_utc"],
        "status": row["status"],
        "input_hash": row["input_hash"],
        "report_path": row["report_path"],
        "summary": json.loads(row["summary_json"]),
    }


def _queue_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "queue_id": row["queue_id"],
        "job_type": row["job_type"],
        "job_payload": json.loads(row["job_payload_json"]),
        "state": row["state"],
        "priority": row["priority"],
        "attempt_count": row["attempt_count"],
        "max_attempts": row["max_attempts"],
        "depends_on_queue_id": row["depends_on_queue_id"],
        "lease_owner": row["lease_owner"],
        "lease_expires_utc": row["lease_expires_utc"],
        "created_utc": row["created_utc"],
        "updated_utc": row["updated_utc"],
        "last_error": json.loads(row["last_error_json"]) if row["last_error_json"] else None,
        "result_summary": json.loads(row["result_summary_json"]) if row["result_summary_json"] else None,
        "failure_history": json.loads(row["failure_history_json"]) if row["failure_history_json"] else [],
    }


def insert_queue_item(record: Dict[str, Any], db_path: Path | None = None) -> None:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO execution_queue (
                queue_id, job_type, job_payload_json, state, priority, attempt_count, max_attempts,
                depends_on_queue_id, lease_owner, lease_expires_utc, created_utc, updated_utc,
                last_error_json, result_summary_json, failure_history_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["queue_id"],
                record["job_type"],
                json.dumps(record["job_payload"], sort_keys=True),
                record["state"],
                int(record.get("priority", 100)),
                int(record.get("attempt_count", 0)),
                int(record.get("max_attempts", 3)),
                record.get("depends_on_queue_id"),
                record.get("lease_owner"),
                record.get("lease_expires_utc"),
                now,
                now,
                json.dumps(record["last_error"], sort_keys=True) if record.get("last_error") is not None else None,
                json.dumps(record["result_summary"], sort_keys=True) if record.get("result_summary") is not None else None,
                json.dumps(record.get("failure_history", []), sort_keys=True),
            ),
        )


def get_queue_item(queue_id: str, db_path: Path | None = None) -> Dict[str, Any]:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT queue_id, job_type, job_payload_json, state, priority, attempt_count, max_attempts,
                   depends_on_queue_id, lease_owner, lease_expires_utc, created_utc, updated_utc,
                   last_error_json, result_summary_json, failure_history_json
            FROM execution_queue
            WHERE queue_id = ?
            """,
            (queue_id,),
        ).fetchone()
    return _queue_row_to_dict(row) if row is not None else {}


def list_queue_items(db_path: Path | None = None, *, limit: int = 200) -> List[Dict[str, Any]]:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT queue_id, job_type, job_payload_json, state, priority, attempt_count, max_attempts,
                   depends_on_queue_id, lease_owner, lease_expires_utc, created_utc, updated_utc,
                   last_error_json, result_summary_json, failure_history_json
            FROM execution_queue
            ORDER BY
                CASE state
                    WHEN 'RUNNING' THEN 0
                    WHEN 'LEASED' THEN 1
                    WHEN 'QUEUED' THEN 2
                    WHEN 'BLOCKED' THEN 3
                    WHEN 'FAILED_TERMINAL' THEN 4
                    WHEN 'SUCCEEDED' THEN 5
                    WHEN 'CANCELLED' THEN 6
                    ELSE 7
                END,
                priority DESC,
                created_utc ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_queue_row_to_dict(row) for row in rows]


def update_queue_item(
    queue_id: str,
    *,
    state: str | None = None,
    lease_owner: str | None = None,
    lease_expires_utc: str | None = None,
    last_error: Dict[str, Any] | None = None,
    result_summary: Dict[str, Any] | None = None,
    failure_history: List[Dict[str, Any]] | None = None,
    attempt_count: int | None = None,
    depends_on_queue_id: str | None = None,
    clear_lease: bool = False,
    clear_last_error: bool = False,
    clear_result_summary: bool = False,
    clear_failure_history: bool = False,
    db_path: Path | None = None,
) -> None:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    assignments: List[str] = ["updated_utc = ?"]
    params: List[Any] = [utc_now()]
    if state is not None:
        assignments.append("state = ?")
        params.append(state)
    if attempt_count is not None:
        assignments.append("attempt_count = ?")
        params.append(int(attempt_count))
    if depends_on_queue_id is not None:
        assignments.append("depends_on_queue_id = ?")
        params.append(depends_on_queue_id)
    if clear_lease:
        assignments.append("lease_owner = NULL")
        assignments.append("lease_expires_utc = NULL")
    else:
        if lease_owner is not None:
            assignments.append("lease_owner = ?")
            params.append(lease_owner)
        if lease_expires_utc is not None:
            assignments.append("lease_expires_utc = ?")
            params.append(lease_expires_utc)
    if clear_last_error:
        assignments.append("last_error_json = NULL")
    elif last_error is not None:
        assignments.append("last_error_json = ?")
        params.append(json.dumps(last_error, sort_keys=True))
    if clear_result_summary:
        assignments.append("result_summary_json = NULL")
    elif result_summary is not None:
        assignments.append("result_summary_json = ?")
        params.append(json.dumps(result_summary, sort_keys=True))
    if clear_failure_history:
        assignments.append("failure_history_json = '[]'")
    elif failure_history is not None:
        assignments.append("failure_history_json = ?")
        params.append(json.dumps(failure_history, sort_keys=True))
    params.append(queue_id)
    with connect(db_path) as conn:
        conn.execute(f"UPDATE execution_queue SET {', '.join(assignments)} WHERE queue_id = ?", params)


def recover_expired_queue_leases(db_path: Path | None = None) -> List[Dict[str, Any]]:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    expired_records: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT queue_id, state, lease_owner, lease_expires_utc
            FROM execution_queue
            WHERE state IN ('LEASED', 'RUNNING') AND lease_expires_utc IS NOT NULL
            """
        ).fetchall()
        for row in rows:
            expires = parse_utc(row["lease_expires_utc"])
            if expires is None or expires >= now:
                continue
            expired_records.append(
                {
                    "queue_id": row["queue_id"],
                    "previous_state": row["state"],
                    "previous_lease_owner": row["lease_owner"],
                    "previous_lease_expires_utc": row["lease_expires_utc"],
                }
            )
        for record in expired_records:
            conn.execute(
                """
                UPDATE execution_queue
                SET state = 'QUEUED',
                    lease_owner = NULL,
                    lease_expires_utc = NULL,
                    updated_utc = ?
                WHERE queue_id = ?
                """,
                (utc_now(), record["queue_id"]),
            )
    return expired_records


def claim_next_queue_item(
    *,
    lease_owner: str,
    lease_expires_utc: str,
    db_path: Path | None = None,
) -> Dict[str, Any]:
    db_path = db_path or CONTROL_PLANE_DB
    initialize(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT q.queue_id, q.job_type, q.job_payload_json, q.state, q.priority, q.attempt_count, q.max_attempts,
                   q.depends_on_queue_id, q.lease_owner, q.lease_expires_utc, q.created_utc, q.updated_utc,
                   q.last_error_json, q.result_summary_json, q.failure_history_json
            FROM execution_queue q
            LEFT JOIN execution_queue dep ON dep.queue_id = q.depends_on_queue_id
            WHERE q.state = 'QUEUED'
              AND (q.depends_on_queue_id IS NULL OR dep.state = 'SUCCEEDED')
            ORDER BY q.priority DESC, q.created_utc ASC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return {}
        conn.execute(
            """
            UPDATE execution_queue
            SET state = 'LEASED',
                lease_owner = ?,
                lease_expires_utc = ?,
                updated_utc = ?
            WHERE queue_id = ?
            """,
            (lease_owner, lease_expires_utc, utc_now(), row["queue_id"]),
        )
    return get_queue_item(row["queue_id"], db_path)

