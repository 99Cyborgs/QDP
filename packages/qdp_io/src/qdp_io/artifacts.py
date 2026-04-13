from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def utc_now() -> str:
    """Return one timezone-aware UTC timestamp string."""

    return datetime.now(timezone.utc).isoformat()


def artifact_report_header(artifact_id: str) -> dict[str, str]:
    """Build the shared header for non-module report artifacts."""

    return {
        "artifact_id": artifact_id,
        "timestamp_utc": utc_now(),
    }


def module_report_header(artifact_id: str, module_id: str) -> dict[str, str]:
    """Build the shared header for module-scoped report artifacts."""

    return {
        "artifact_id": artifact_id,
        "module_id": module_id,
        "timestamp_utc": utc_now(),
    }


def module_selftest_report_payload(
    artifact_id: str,
    module_id: str,
    cases: list[dict[str, Any]],
    *,
    visible_source_only: bool | None = None,
    metadata: Mapping[str, Any] | None = None,
    all_passed: bool | None = None,
    schema_valid_all: bool | None = None,
) -> dict[str, Any]:
    """Build the shared module selftest report payload shape."""

    cases_total = len(cases)
    cases_passed = sum(1 for case in cases if case.get("passed", False))
    payload: dict[str, Any] = module_report_header(artifact_id, module_id)
    if visible_source_only is not None:
        payload["visible_source_only"] = visible_source_only
    if metadata:
        payload.update(dict(metadata))
    payload["cases_total"] = cases_total
    payload["cases_passed"] = cases_passed
    payload["all_passed"] = all_passed if all_passed is not None else (cases_total > 0 and cases_passed == cases_total)
    if schema_valid_all is not None:
        payload["schema_valid_all"] = schema_valid_all
    payload["cases"] = cases
    return payload


def candidate_result_summary_report(
    artifact_id: str,
    module_id: str,
    candidate_id: str,
    result_summary: Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the shared candidate-scoped result-summary report payload shape."""

    payload: dict[str, Any] = module_report_header(artifact_id, module_id)
    payload["candidate_id"] = candidate_id
    if metadata:
        payload.update(dict(metadata))
    payload["result_summary"] = dict(result_summary)
    return payload


def visible_source_result_summary_report(
    artifact_id: str,
    module_id: str,
    result_summary: Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the shared visible-source result-summary report payload shape."""

    payload: dict[str, Any] = module_report_header(artifact_id, module_id)
    payload["visible_source_only"] = True
    if metadata:
        payload.update(dict(metadata))
    payload["result_summary"] = dict(result_summary)
    if diagnostics is not None:
        payload["diagnostics"] = dict(diagnostics)
    return payload


def dump_json(path: str | Path, payload: Any) -> Path:
    """Write a JSON artifact with the legacy QDP formatting contract."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def stable_hash(payload: Any) -> str:
    """Hash a JSON-serializable payload using stable key ordering."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Compute the SHA-256 digest of one file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
