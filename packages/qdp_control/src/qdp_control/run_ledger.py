from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from qdp_io.artifacts import artifact_report_header, dump_json, sha256_file, stable_hash, utc_now
from qdp_io.reference_manifest import retained_reference_provenance_mode
from qdp_io.serialization import load_json
from .control_plane import list_runs, upsert_run
from tools.workflow.qdp_runtime.qdp_paths import REFERENCE_MANIFEST, RUN_LEDGER_REPORT


def infer_provenance_mode(reference_manifest: Dict[str, Any] | None = None) -> str:
    manifest = reference_manifest
    if manifest is None:
        manifest = load_json(REFERENCE_MANIFEST) if REFERENCE_MANIFEST.exists() else {}
    return retained_reference_provenance_mode(manifest)


def artifact_hashes(paths: Iterable[Path]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for path in paths:
        path = Path(path)
        if path.exists() and path.is_file():
            result[str(path)] = sha256_file(path)
    return result


def build_record(
    *,
    operation: str,
    lane: str,
    provenance_mode: str,
    status: str,
    summary: Dict[str, Any],
    artifacts: Iterable[Path],
) -> Dict[str, Any]:
    hashes = artifact_hashes(artifacts)
    content_hash = stable_hash(
        {
            "operation": operation,
            "lane": lane,
            "provenance_mode": provenance_mode,
            "status": status,
            "summary": summary,
            "artifacts": hashes,
        }
    )
    run_id = f"QDPRUN-{content_hash[:16].upper()}"
    return {
        "run_id": run_id,
        "operation": operation,
        "lane": lane,
        "provenance_mode": provenance_mode,
        "status": status,
        "content_hash": content_hash,
        "summary": summary,
        "artifact_hashes": hashes,
        "timestamp_utc": utc_now(),
    }


def refresh_ledger_json(path: Path = RUN_LEDGER_REPORT) -> Dict[str, Any]:
    runs = list_runs()
    payload = {
        **artifact_report_header("QDP_V10_6_RUN_LEDGER"),
        "runs": runs,
    }
    dump_json(path, payload)
    return payload


def record_run(
    *,
    operation: str,
    lane: str,
    status: str,
    summary: Dict[str, Any],
    artifacts: Iterable[Path],
    provenance_mode: str | None = None,
) -> Dict[str, Any]:
    mode = provenance_mode or infer_provenance_mode()
    record = build_record(
        operation=operation,
        lane=lane,
        provenance_mode=mode,
        status=status,
        summary=summary,
        artifacts=artifacts,
    )
    upsert_run(record)
    refresh_ledger_json()
    return record

