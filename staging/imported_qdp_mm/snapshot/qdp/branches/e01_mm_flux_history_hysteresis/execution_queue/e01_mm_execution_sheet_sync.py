from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHEET_SYNC_REASON_CODES = {
    "SHEET_SYNC_SKIPPED",
    "SHEET_SYNC_CONFLICT",
    "SHEET_SYNC_PARSE_FAILED",
    "SHEET_SYNC_WRITE_SKIPPED",
}

SYNCABLE_QUEUE_STATES = {
    "READY_FOR_PRECHECK",
    "READY_FOR_HARDWARE",
    "IN_PROGRESS",
    "READY_FOR_AS_RUN_BINDING",
    "COMPLETE",
}

FIELD_MAPPINGS = (
    {"label": "`binding_context`", "path": "binding_context", "style": "code"},
    {"label": "`binding_status`", "path": "binding_status", "style": "code"},
    {"label": "`cooldown_id`", "path": "cooldown_id", "style": "code"},
    {"label": "`operator`", "path": "run_metadata.operator", "style": "code"},
    {"label": "`run_date`", "path": "run_metadata.run_date", "style": "code"},
    {"label": "`lab_location`", "path": "run_metadata.lab_location", "style": "code"},
    {"label": "`run_readiness`", "derived": "run_readiness", "style": "code"},
    {"label": "`target_device_ids`", "path": "hardware_binding.target_device_ids", "style": "code"},
    {"label": "`witness_channel_id`", "path": "hardware_binding.witness_channel_id", "style": "code"},
    {"label": "`matched_geometry_device_ids`", "path": "hardware_binding.matched_geometry_device_ids", "style": "code"},
    {"label": "`H2 run eligibility`", "derived": "h2_run_eligibility", "style": "text"},
    {"label": "`T_base`", "path": "fixed_settings.T_base", "style": "code"},
    {"label": "`P_read`", "path": "fixed_settings.P_read", "style": "code"},
    {"label": "`readout_tone_id`", "path": "fixed_settings.readout_tone_id", "style": "code"},
    {"label": "`attenuation_state`", "path": "fixed_settings.attenuation_state", "style": "code"},
    {"label": "`readout_chain_config`", "path": "fixed_settings.readout_chain_config", "style": "code"},
    {"label": "`field_unit`", "path": "field_program.field_unit", "style": "code"},
    {"label": "`B_max`", "path": "field_program.B_max", "style": "code"},
    {"label": "`fc_field`", "path": "field_program.fc_field", "style": "code"},
    {"label": "`field_steps`", "path": "field_program.field_steps", "style": "code"},
    {"label": "`selected_fields`", "path": "field_program.selected_fields", "style": "code"},
    {"label": "`probe_fields`", "path": "field_program.dwell_probe_schedule.probe_fields", "style": "code"},
    {"label": "`dwell_times`", "path": "field_program.dwell_probe_schedule.dwell_times", "style": "code"},
    {"label": "`dwell_time_unit`", "path": "field_program.dwell_probe_schedule.dwell_time_unit", "style": "code"},
    {"label": "production dwell `t_conv`", "path": "field_program.production_dwell_t_conv", "style": "code"},
    {"label": "raw data output path", "path": "data_capture.raw_data_output_path", "style": "code"},
    {"label": "metadata output path", "path": "data_capture.metadata_output_path", "style": "code"},
    {"label": "witness trace path", "path": "data_capture.witness_trace_output_path", "style": "code"},
    {"label": "witness channel bound", "derived": "witness_channel_bound", "style": "code"},
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def to_iso8601(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def get_nested(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def ensure_sheet_sync_block(manifest: dict[str, Any]) -> dict[str, Any]:
    sheet_sync = manifest.setdefault("sheet_sync", {})
    sheet_sync.setdefault("status", "not_run")
    sheet_sync.setdefault("synced_at", None)
    sheet_sync.setdefault("updated_fields", [])
    sheet_sync.setdefault("skipped_fields", [])
    sheet_sync.setdefault("reason_codes", [])
    return sheet_sync


def resolve_manifest_path(manifest_path: Path, linked_path: str) -> Path:
    path = Path(linked_path)
    if path.is_absolute():
        return path
    return (manifest_path.parent / path).resolve()


def render_value(value: Any, style: str) -> str:
    if isinstance(value, list):
        rendered = json.dumps(value)
    elif isinstance(value, float):
        rendered = format(value, "g")
    else:
        rendered = str(value)
    return f"`{rendered}`" if style == "code" else rendered


def derive_run_readiness(run_binding: dict[str, Any]) -> str:
    binding_status = run_binding.get("binding_status")
    if binding_status == "PRE_RUN_MINIMUM_READY":
        return "PRE_RUN_READY"
    if binding_status == "AS_RUN_BOUND":
        return "AS_RUN_READY"
    return "NOT_READY"


def derive_h2_run_eligibility(run_binding: dict[str, Any]) -> str:
    matched_geometry_ids = ensure_list(run_binding.get("hardware_binding", {}).get("matched_geometry_device_ids"))
    if matched_geometry_ids:
        return "MATCHED GEOMETRY BOUND; H2 STILL GATED BY COMPETITION ORDER"
    return "INELIGIBLE UNTIL SAME-CHIP MATCHED GEOMETRY IS BOUND"


def derive_witness_channel_bound(run_binding: dict[str, Any]) -> str:
    return "BOUND" if is_non_empty_string(run_binding.get("hardware_binding", {}).get("witness_channel_id")) else "UNBOUND"


def get_mapping_value(run_binding: dict[str, Any], mapping: dict[str, str]) -> Any:
    if "path" in mapping:
        return get_nested(run_binding, mapping["path"])
    derived_key = mapping["derived"]
    if derived_key == "run_readiness":
        return derive_run_readiness(run_binding)
    if derived_key == "h2_run_eligibility":
        return derive_h2_run_eligibility(run_binding)
    if derived_key == "witness_channel_bound":
        return derive_witness_channel_bound(run_binding)
    return None


def get_mapping_key(mapping: dict[str, str]) -> str:
    return mapping["path"] if "path" in mapping else mapping["derived"]


def should_sync_sheet(manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    reason_codes: list[str] = []
    reconciliation = manifest.get("reconciliation", {})
    if manifest.get("queue_state") not in SYNCABLE_QUEUE_STATES:
        reason_codes.append("SHEET_SYNC_SKIPPED")
    if manifest.get("stop_condition_reasons"):
        reason_codes.append("SHEET_SYNC_CONFLICT")
    if reconciliation.get("status") != "clean":
        if reconciliation.get("source_conflicts"):
            reason_codes.append("SHEET_SYNC_CONFLICT")
        else:
            reason_codes.append("SHEET_SYNC_SKIPPED")
    last_validator = manifest.get("last_validator_result")
    if isinstance(last_validator, dict) and last_validator.get("severity") in {"block", "fail", "escalate"}:
        reason_codes.append("SHEET_SYNC_SKIPPED")
    return (not reason_codes, sorted(set(reason_codes)))


def update_table_rows(sheet_text: str, run_binding: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    lines = sheet_text.splitlines()
    updated_fields: list[str] = []
    skipped_fields: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        if len(cells) != 2:
            continue
        label = cells[0]
        current_value = cells[1]
        for mapping in FIELD_MAPPINGS:
            if label != mapping["label"]:
                continue
            value = get_mapping_value(run_binding, mapping)
            if value in (None, "", []):
                skipped_fields.append(get_mapping_key(mapping))
                break
            rendered_value = render_value(value, mapping["style"])
            if current_value != rendered_value:
                lines[index] = f"| {label} | {rendered_value} |"
                updated_fields.append(get_mapping_key(mapping))
            break
    return ("\n".join(lines) + "\n", sorted(set(updated_fields)), sorted(set(skipped_fields)))


def preview_execution_sheet_sync(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    checked_at = to_iso8601(utc_now())
    sheet_sync = ensure_sheet_sync_block(manifest)
    execution_sheet_path = manifest.get("execution_sheet_path")
    if not is_non_empty_string(execution_sheet_path):
        result = {
            "status": "skipped",
            "synced_at": checked_at,
            "updated_fields": [],
            "skipped_fields": [],
            "reason_codes": ["SHEET_SYNC_PARSE_FAILED"],
            "proposed_text": None,
        }
        sheet_sync.update({key: value for key, value in result.items() if key != "proposed_text"})
        return result

    resolved_path = resolve_manifest_path(manifest_path, str(execution_sheet_path))
    if not resolved_path.exists():
        result = {
            "status": "skipped",
            "synced_at": checked_at,
            "updated_fields": [],
            "skipped_fields": [],
            "reason_codes": ["SHEET_SYNC_PARSE_FAILED"],
            "proposed_text": None,
        }
        sheet_sync.update({key: value for key, value in result.items() if key != "proposed_text"})
        return result

    should_sync, gating_reason_codes = should_sync_sheet(manifest)
    source_text = resolved_path.read_text(encoding="ascii")
    proposed_text, updated_fields, skipped_fields = update_table_rows(source_text, manifest.get("run_binding", {}))
    status = "ready" if should_sync else "skipped"
    result = {
        "status": status,
        "synced_at": checked_at,
        "updated_fields": updated_fields,
        "skipped_fields": skipped_fields,
        "reason_codes": gating_reason_codes,
        "proposed_text": proposed_text,
    }
    sheet_sync.update({key: value for key, value in result.items() if key != "proposed_text"})
    return result


def sync_execution_sheet(manifest_path: Path, manifest: dict[str, Any], *, write_changes: bool) -> dict[str, Any]:
    preview = preview_execution_sheet_sync(manifest_path, manifest)
    sheet_sync = ensure_sheet_sync_block(manifest)
    execution_sheet_path = manifest.get("execution_sheet_path")
    if preview["status"] != "ready":
        return manifest
    if not is_non_empty_string(execution_sheet_path):
        sheet_sync["status"] = "skipped"
        sheet_sync["reason_codes"] = ["SHEET_SYNC_PARSE_FAILED"]
        return manifest

    resolved_path = resolve_manifest_path(manifest_path, str(execution_sheet_path))
    if not write_changes:
        sheet_sync["status"] = "preview"
        sheet_sync["reason_codes"] = ["SHEET_SYNC_WRITE_SKIPPED"] if preview["updated_fields"] else []
        return manifest

    current_text = resolved_path.read_text(encoding="ascii")
    if current_text != preview["proposed_text"]:
        resolved_path.write_text(preview["proposed_text"], encoding="ascii")
        sheet_sync["status"] = "synced"
    else:
        sheet_sync["status"] = "unchanged"
    return manifest
