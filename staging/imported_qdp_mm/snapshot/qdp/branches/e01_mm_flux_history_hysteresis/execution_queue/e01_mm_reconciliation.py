from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MARKDOWN_EXTENSIONS = {".md", ".markdown"}
STRUCTURED_EVIDENCE_KEYS = (
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
RECONCILIATION_REASON_CODES = {
    "SOURCE_PARSE_FAILED",
    "SOURCE_CONFLICT",
    "MISSING_REQUIRED_SOURCE_FIELD",
    "UNSUPPORTED_SOURCE_FORMAT",
    "RUN_BINDING_WRITE_SKIPPED",
}
TERMINAL_RECONCILIATION_CODES = {
    "SOURCE_PARSE_FAILED",
    "UNSUPPORTED_SOURCE_FORMAT",
}
CRITICAL_CONFLICT_FIELDS = {
    "cooldown_id",
    "hardware_binding.target_device_ids",
    "hardware_binding.witness_channel_id",
    "fixed_settings.P_read",
}
FIELD_SPECS = (
    {
        "target": "cooldown_id",
        "sources": [("as_run_logbook_path", "cooldown_id"), ("fridge_log_path", "cooldown_id")],
        "kind": "str",
    },
    {
        "target": "run_metadata.operator",
        "sources": [("as_run_logbook_path", "operator"), ("fridge_log_path", "operator")],
        "kind": "str",
    },
    {
        "target": "run_metadata.run_date",
        "sources": [("as_run_logbook_path", "run_date"), ("fridge_log_path", "run_date")],
        "kind": "str",
    },
    {
        "target": "run_metadata.lab_location",
        "sources": [("as_run_logbook_path", "lab_location"), ("fridge_log_path", "lab_location")],
        "kind": "str",
    },
    {
        "target": "hardware_binding.target_device_ids",
        "sources": [("fridge_log_path", "target_device_ids"), ("sample_map_path", "target_device_ids")],
        "kind": "list_str",
    },
    {
        "target": "hardware_binding.witness_channel_id",
        "sources": [("fridge_log_path", "witness_channel_id"), ("channel_map_path", "witness_channel_id")],
        "kind": "str",
    },
    {
        "target": "hardware_binding.matched_geometry_device_ids",
        "sources": [("fridge_log_path", "matched_geometry_device_ids"), ("sample_map_path", "matched_geometry_device_ids")],
        "kind": "list_str",
    },
    {
        "target": "fixed_settings.T_base",
        "sources": [("daq_record_path", "T_base")],
        "kind": "float",
    },
    {
        "target": "fixed_settings.P_read",
        "sources": [("daq_record_path", "P_read"), ("calibration_record_path", "P_read")],
        "kind": "float",
    },
    {
        "target": "fixed_settings.readout_tone_id",
        "sources": [("daq_record_path", "readout_tone_id")],
        "kind": "str",
    },
    {
        "target": "fixed_settings.attenuation_state",
        "sources": [("daq_record_path", "attenuation_state")],
        "kind": "str",
    },
    {
        "target": "fixed_settings.readout_chain_config",
        "sources": [("daq_record_path", "readout_chain_config")],
        "kind": "str",
    },
    {
        "target": "field_program.field_unit",
        "sources": [("as_run_logbook_path", "field_unit"), ("daq_record_path", "field_unit")],
        "kind": "str",
    },
    {
        "target": "field_program.B_max",
        "sources": [("as_run_logbook_path", "B_max"), ("daq_record_path", "B_max")],
        "kind": "float",
    },
    {
        "target": "field_program.fc_field",
        "sources": [("as_run_logbook_path", "fc_field"), ("daq_record_path", "fc_field")],
        "kind": "float",
    },
    {
        "target": "field_program.field_steps",
        "sources": [("as_run_logbook_path", "field_steps"), ("daq_record_path", "field_steps")],
        "kind": "list_float",
    },
    {
        "target": "field_program.selected_fields",
        "sources": [("as_run_logbook_path", "selected_fields"), ("daq_record_path", "selected_fields")],
        "kind": "list_float",
    },
    {
        "target": "field_program.dwell_probe_schedule.probe_fields",
        "sources": [("as_run_logbook_path", "probe_fields"), ("daq_record_path", "probe_fields")],
        "kind": "list_float",
    },
    {
        "target": "field_program.dwell_probe_schedule.dwell_times",
        "sources": [("as_run_logbook_path", "dwell_times"), ("daq_record_path", "dwell_times")],
        "kind": "list_float",
    },
    {
        "target": "field_program.dwell_probe_schedule.dwell_time_unit",
        "sources": [("as_run_logbook_path", "dwell_time_unit"), ("daq_record_path", "dwell_time_unit")],
        "kind": "str",
    },
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def to_iso8601(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def resolve_manifest_path(manifest_path: Path, linked_path: str) -> Path:
    path = Path(linked_path)
    if path.is_absolute():
        return path
    return (manifest_path.parent / path).resolve()


def get_nested(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def set_nested(payload: dict[str, Any], path: str, value: Any) -> None:
    current = payload
    parts = path.split(".")
    for segment in parts[:-1]:
        if segment not in current or not isinstance(current[segment], dict):
            current[segment] = {}
        current = current[segment]
    current[parts[-1]] = value


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def parse_frontmatter_value(raw_value: str) -> Any:
    value = raw_value.strip()
    if value == "":
        return ""
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if value.startswith(("[", "{", "\"")):
        return json.loads(value)
    try:
        if "." in value or "e" in lowered:
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_markdown_frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise ValueError("Markdown evidence must start with YAML-style frontmatter delimited by ---")

    frontmatter: dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return frontmatter
        if ":" not in line:
            raise ValueError(f"Invalid frontmatter line: {line}")
        key, raw_value = line.split(":", 1)
        frontmatter[key.strip()] = parse_frontmatter_value(raw_value)
    raise ValueError("Markdown evidence frontmatter is missing a closing ---")


def load_structured_payload(source_path: Path) -> tuple[Any, str]:
    suffix = source_path.suffix.lower()
    raw_text = source_path.read_text(encoding="ascii")
    if suffix == ".json":
        return json.loads(raw_text), "json"
    if suffix in MARKDOWN_EXTENSIONS:
        return parse_markdown_frontmatter(raw_text), "markdown_frontmatter"
    raise ValueError(f"Unsupported evidence format: {suffix}")


def normalise_value(value: Any, kind: str) -> Any:
    if value is None:
        return None
    if kind == "str":
        stripped = str(value).strip()
        return stripped if stripped != "" else None
    if kind == "float":
        return float(value)
    if kind == "list_str":
        if not isinstance(value, list):
            raise ValueError("Expected a list of strings.")
        return [str(item).strip() for item in value]
    if kind == "list_float":
        if not isinstance(value, list):
            raise ValueError("Expected a list of numbers.")
        return [float(item) for item in value]
    return value


def canonicalise(value: Any, kind: str) -> Any:
    normalised = normalise_value(value, kind)
    if kind == "list_str":
        return sorted(normalised)
    return normalised


def ensure_reconciliation_block(manifest: dict[str, Any]) -> dict[str, Any]:
    reconciliation = manifest.setdefault("reconciliation", {})
    reconciliation.setdefault("status", "not_run")
    reconciliation.setdefault("reconciled_at", None)
    reconciliation.setdefault("populated_fields", [])
    reconciliation.setdefault("missing_fields", [])
    reconciliation.setdefault("source_conflicts", [])
    reconciliation.setdefault("evidence_summary", {})
    reconciliation.setdefault("reason_codes", [])
    reconciliation.setdefault("details", [])
    return reconciliation


def load_evidence_source(manifest_path: Path, source_key: str, declared_path: str | None) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "declared": is_non_empty_string(declared_path),
        "exists": False,
        "parse_ok": False,
        "format": None,
        "path": declared_path,
        "errors": [],
        "normalized_fields": {},
    }
    if not is_non_empty_string(declared_path):
        return summary

    resolved = resolve_manifest_path(manifest_path, str(declared_path))
    summary["path"] = str(resolved)
    if not resolved.exists():
        summary["errors"].append("PROVENANCE_PATH_NOT_FOUND")
        return summary

    summary["exists"] = True
    try:
        payload, source_format = load_structured_payload(resolved)
    except ValueError as error:
        message = str(error)
        summary["format"] = resolved.suffix.lower()
        if "Unsupported evidence format" in message:
            summary["errors"].append("UNSUPPORTED_SOURCE_FORMAT")
        else:
            summary["errors"].append("SOURCE_PARSE_FAILED")
        return summary
    except json.JSONDecodeError:
        summary["format"] = resolved.suffix.lower()
        summary["errors"].append("SOURCE_PARSE_FAILED")
        return summary

    if not isinstance(payload, dict):
        summary["format"] = source_format
        summary["errors"].append("SOURCE_PARSE_FAILED")
        return summary

    summary["parse_ok"] = True
    summary["format"] = source_format
    summary["normalized_fields"] = payload
    return summary


def reconcile_field(
    updated_binding: dict[str, Any],
    source_summaries: dict[str, Any],
    field_spec: dict[str, Any],
    populated_fields: list[str],
    missing_fields: list[str],
    source_conflicts: list[dict[str, Any]],
    reason_codes: list[str],
    details: list[str],
) -> None:
    target = field_spec["target"]
    kind = field_spec["kind"]
    candidates: list[tuple[str, Any]] = []
    for source_key, source_field in field_spec["sources"]:
        summary = source_summaries[source_key]
        if not summary["parse_ok"]:
            continue
        payload = summary["normalized_fields"]
        if source_field not in payload or payload[source_field] is None:
            continue
        try:
            candidates.append((source_key, normalise_value(payload[source_field], kind)))
        except (TypeError, ValueError):
            reason_codes.append("SOURCE_PARSE_FAILED")
            details.append(f"{source_key} provided an invalid value for {target}.")
            return

    existing_value = get_nested(updated_binding, target)
    if not candidates:
        if existing_value in (None, [], ""):
            missing_fields.append(target)
            reason_codes.append("MISSING_REQUIRED_SOURCE_FIELD")
            details.append(f"No declared source provided a value for {target}.")
        return

    canonical_values = [canonicalise(value, kind) for _, value in candidates]
    first_value = canonical_values[0]
    if any(value != first_value for value in canonical_values[1:]):
        source_conflicts.append(
            {
                "field": target,
                "sources": [source_key for source_key, _ in candidates],
                "values": [value for _, value in candidates],
            }
        )
        reason_codes.append("SOURCE_CONFLICT")
        details.append(f"Conflicting source values detected for {target}.")
        return

    if canonicalise(existing_value, kind) != first_value:
        set_nested(updated_binding, target, candidates[0][1])
    populated_fields.append(target)


def apply_output_paths(manifest_path: Path, manifest: dict[str, Any], updated_binding: dict[str, Any], populated_fields: list[str]) -> None:
    evidence_paths = manifest.get("required_evidence_paths", {})
    data_capture = updated_binding.setdefault("data_capture", {})
    for output_key in OUTPUT_EVIDENCE_KEYS:
        declared_path = evidence_paths.get(output_key)
        if not is_non_empty_string(declared_path):
            continue
        resolved = resolve_manifest_path(manifest_path, str(declared_path))
        if resolved.exists() and data_capture.get(output_key) != str(resolved):
            data_capture[output_key] = str(resolved)
            populated_fields.append(f"data_capture.{output_key}")


def detect_as_run_evidence(manifest_path: Path, manifest: dict[str, Any], run_binding: dict[str, Any]) -> bool:
    evidence_paths = manifest.get("required_evidence_paths", {})
    candidate_paths: list[str] = []
    for output_key in OUTPUT_EVIDENCE_KEYS:
        declared_path = evidence_paths.get(output_key)
        if is_non_empty_string(declared_path):
            candidate_paths.append(str(declared_path))
        bound_path = run_binding.get("data_capture", {}).get(output_key)
        if is_non_empty_string(bound_path):
            candidate_paths.append(str(bound_path))

    for candidate in candidate_paths:
        if resolve_manifest_path(manifest_path, candidate).exists():
            return True
    return False


def maybe_switch_binding_context(manifest_path: Path, manifest: dict[str, Any], updated_binding: dict[str, Any], source_summaries: dict[str, Any]) -> None:
    if updated_binding.get("binding_context") == "AS_RUN_BINDING":
        return
    if detect_as_run_evidence(manifest_path, manifest, updated_binding):
        updated_binding["binding_context"] = "AS_RUN_BINDING"
        return
    for source_key in ("as_run_logbook_path", "fridge_log_path", "daq_record_path", "calibration_record_path"):
        if source_summaries[source_key]["parse_ok"]:
            updated_binding["binding_context"] = "AS_RUN_BINDING"
            return


def derive_binding_checks(manifest_path: Path, updated_binding: dict[str, Any], source_summaries: dict[str, Any]) -> None:
    field_program = updated_binding.get("field_program", {})
    field_steps = [float(value) for value in ensure_list(field_program.get("field_steps"))]
    selected_fields = [float(value) for value in ensure_list(field_program.get("selected_fields"))]
    probe_schedule = field_program.get("dwell_probe_schedule", {})
    probe_fields = [float(value) for value in ensure_list(probe_schedule.get("probe_fields"))]
    dwell_times = ensure_list(probe_schedule.get("dwell_times"))

    field_step_set = {float(value) for value in field_steps}
    binding_checks = updated_binding.setdefault("binding_checks", {})
    binding_checks["selected_fields_subset_of_field_steps"] = bool(
        selected_fields and field_steps and all(float(value) in field_step_set for value in selected_fields)
    )
    binding_checks["probe_schedule_lengths_match"] = bool(probe_fields) and len(probe_fields) == len(dwell_times)
    binding_checks["field_unit_consistent"] = is_non_empty_string(field_program.get("field_unit"))

    calibration_summary = source_summaries.get("calibration_record_path", {})
    calibration_fields = calibration_summary.get("normalized_fields", {})
    explicit_flag = calibration_fields.get("p_read_device_calibrated")
    binding_checks["p_read_device_calibrated"] = bool(
        updated_binding.get("fixed_settings", {}).get("P_read") is not None
        and (
            explicit_flag is True
            or (calibration_summary.get("parse_ok") and calibration_fields.get("P_read") is not None)
        )
    )

    output_paths_exist = True
    for output_key in OUTPUT_EVIDENCE_KEYS:
        output_path = updated_binding.get("data_capture", {}).get(output_key)
        if not is_non_empty_string(output_path):
            output_paths_exist = False
            continue
        if not resolve_manifest_path(manifest_path, str(output_path)).exists():
            output_paths_exist = False
    binding_checks["output_paths_exist"] = output_paths_exist


def derive_binding_status(updated_binding: dict[str, Any]) -> None:
    binding_context = updated_binding.get("binding_context")
    binding_checks = updated_binding.get("binding_checks", {})
    hardware_binding = updated_binding.get("hardware_binding", {})
    field_program = updated_binding.get("field_program", {})
    probe_schedule = field_program.get("dwell_probe_schedule", {})

    if binding_context == "PRE_RUN_MINIMUM_ACQUISITION":
        ready = (
            bool(ensure_list(hardware_binding.get("target_device_ids")))
            and is_non_empty_string(hardware_binding.get("witness_channel_id"))
            and isinstance(hardware_binding.get("matched_geometry_device_ids"), list)
            and bool(ensure_list(field_program.get("field_steps")))
            and bool(ensure_list(field_program.get("selected_fields")))
            and bool(ensure_list(probe_schedule.get("probe_fields")))
            and binding_checks.get("selected_fields_subset_of_field_steps") is True
            and binding_checks.get("probe_schedule_lengths_match") is True
            and binding_checks.get("field_unit_consistent") is True
        )
        updated_binding["binding_status"] = "PRE_RUN_MINIMUM_READY" if ready else "TEMPLATE_UNBOUND"
        return

    if binding_context == "AS_RUN_BINDING":
        run_identity_complete = (
            is_non_empty_string(updated_binding.get("cooldown_id"))
            and is_non_empty_string(updated_binding.get("run_metadata", {}).get("operator"))
            and is_non_empty_string(updated_binding.get("run_metadata", {}).get("run_date"))
            and is_non_empty_string(updated_binding.get("run_metadata", {}).get("lab_location"))
        )
        fixed_settings = updated_binding.get("fixed_settings", {})
        fixed_settings_complete = (
            fixed_settings.get("T_base") is not None
            and fixed_settings.get("P_read") is not None
            and is_non_empty_string(fixed_settings.get("readout_tone_id"))
            and is_non_empty_string(fixed_settings.get("attenuation_state"))
            and is_non_empty_string(fixed_settings.get("readout_chain_config"))
        )
        field_program_complete = (
            is_non_empty_string(field_program.get("field_unit"))
            and field_program.get("B_max") is not None
            and field_program.get("fc_field") is not None
            and bool(ensure_list(field_program.get("field_steps")))
            and bool(ensure_list(field_program.get("selected_fields")))
            and bool(ensure_list(probe_schedule.get("probe_fields")))
        )
        complete = (
            run_identity_complete
            and bool(ensure_list(hardware_binding.get("target_device_ids")))
            and is_non_empty_string(hardware_binding.get("witness_channel_id"))
            and isinstance(hardware_binding.get("matched_geometry_device_ids"), list)
            and fixed_settings_complete
            and field_program_complete
            and all(bool(binding_checks.get(name)) for name in binding_checks)
        )
        partial = run_identity_complete or fixed_settings_complete or field_program_complete
        updated_binding["binding_status"] = "AS_RUN_BOUND" if complete else ("AS_RUN_PARTIAL" if partial else "TEMPLATE_UNBOUND")


def reconcile_queue_manifest(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    checked_at = to_iso8601(utc_now())
    reconciliation = ensure_reconciliation_block(manifest)
    run_binding = manifest.get("run_binding")
    if not isinstance(run_binding, dict):
        reconciliation.update(
            {
                "status": "failed",
                "reconciled_at": checked_at,
                "populated_fields": [],
                "missing_fields": [],
                "source_conflicts": [],
                "evidence_summary": {},
                "reason_codes": ["MALFORMED_RUN_BINDING"],
                "details": ["Queue manifest is missing a valid run_binding payload."],
            }
        )
        return manifest

    updated_binding = deepcopy(run_binding)
    source_summaries: dict[str, Any] = {}
    populated_fields: list[str] = []
    missing_fields: list[str] = []
    source_conflicts: list[dict[str, Any]] = []
    reason_codes: list[str] = []
    details: list[str] = []

    evidence_paths = manifest.get("required_evidence_paths", {})
    for source_key in STRUCTURED_EVIDENCE_KEYS:
        source_summaries[source_key] = load_evidence_source(manifest_path, source_key, evidence_paths.get(source_key))
        reason_codes.extend(source_summaries[source_key]["errors"])
        if not source_summaries[source_key]["declared"]:
            reason_codes.append("MISSING_PROVENANCE_PATH")
            details.append(f"{source_key} is not declared in required_evidence_paths.")

    for field_spec in FIELD_SPECS:
        reconcile_field(
            updated_binding,
            source_summaries,
            field_spec,
            populated_fields,
            missing_fields,
            source_conflicts,
            reason_codes,
            details,
        )

    apply_output_paths(manifest_path, manifest, updated_binding, populated_fields)
    maybe_switch_binding_context(manifest_path, manifest, updated_binding, source_summaries)
    derive_binding_checks(manifest_path, updated_binding, source_summaries)
    derive_binding_status(updated_binding)

    manifest["run_binding"] = updated_binding
    manifest["cooldown_id"] = updated_binding.get("cooldown_id")

    status = "clean"
    if any(code in TERMINAL_RECONCILIATION_CODES for code in reason_codes) or any(
        conflict["field"] in CRITICAL_CONFLICT_FIELDS for conflict in source_conflicts
    ):
        status = "failed"
    elif reason_codes or source_conflicts or missing_fields:
        status = "blocked"

    evidence_summary: dict[str, Any] = {}
    for source_key, summary in source_summaries.items():
        evidence_summary[source_key] = {
            "declared": summary["declared"],
            "exists": summary["exists"],
            "parse_ok": summary["parse_ok"],
            "format": summary["format"],
            "errors": summary["errors"],
            "populated_field_count": len(summary["normalized_fields"]),
        }

    reconciliation.update(
        {
            "status": status,
            "reconciled_at": checked_at,
            "populated_fields": sorted(set(populated_fields)),
            "missing_fields": sorted(set(missing_fields)),
            "source_conflicts": source_conflicts,
            "evidence_summary": evidence_summary,
            "reason_codes": dedupe(reason_codes),
            "details": dedupe(details),
        }
    )
    return manifest
