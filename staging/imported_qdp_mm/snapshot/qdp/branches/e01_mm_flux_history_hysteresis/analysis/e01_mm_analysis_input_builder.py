from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from .e01_mm_analysis_runner import DEFAULT_ANALYSIS_SCHEMA_VERSION
except ImportError:
    from e01_mm_analysis_runner import DEFAULT_ANALYSIS_SCHEMA_VERSION

try:
    from execution_queue.e01_mm_reconciliation import load_structured_payload
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from execution_queue.e01_mm_reconciliation import load_structured_payload

MEASUREMENT_EVIDENCE_SCHEMA_VERSION = "1.0.0"
REQUIRED_MEASUREMENT_FIELDS = (
    "device_id",
    "geometry_id",
    "history_label",
    "branch",
    "commanded_field",
    "calibrated_field",
    "elapsed_time",
    "dwell_duration",
    "inv_qi",
    "fr",
    "delta_fr_over_fr",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="ascii"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def ensure_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def resolve_linked_path(base_path: Path, linked_path: str) -> Path:
    path = Path(linked_path)
    if path.is_absolute():
        return path
    return (base_path.parent / path).resolve()


def load_run_binding_from_manifest(manifest_path: Path) -> tuple[dict[str, Any], Path]:
    manifest = read_json(manifest_path)
    run_binding_path_value = manifest.get("run_binding_path")
    if not is_non_empty_string(run_binding_path_value):
        raise ValueError("Queue manifest is missing run_binding_path.")
    run_binding_path = resolve_linked_path(manifest_path, str(run_binding_path_value))
    if run_binding_path.exists():
        payload = read_json(run_binding_path)
        if not isinstance(payload, dict):
            raise ValueError("Resolved run-binding payload must be a JSON object.")
        return payload, run_binding_path
    embedded = manifest.get("run_binding")
    if not isinstance(embedded, dict):
        raise ValueError("Queue manifest does not contain a usable run_binding payload.")
    return deepcopy(embedded), run_binding_path


def load_run_binding(run_binding_path: Path | None, queue_manifest_path: Path | None) -> tuple[dict[str, Any], Path]:
    if queue_manifest_path is not None:
        return load_run_binding_from_manifest(queue_manifest_path)
    if run_binding_path is None:
        raise ValueError("Either --run-binding or --queue-manifest is required.")
    payload = read_json(run_binding_path)
    if not isinstance(payload, dict):
        raise ValueError("Run-binding payload must be a JSON object.")
    return payload, run_binding_path


def choose_measurement_evidence_path(run_binding: dict[str, Any], run_binding_path: Path) -> Path:
    data_capture = run_binding.get("data_capture", {})
    candidate_paths = [
        data_capture.get("metadata_output_path"),
        data_capture.get("raw_data_output_path"),
    ]
    for candidate in candidate_paths:
        if not is_non_empty_string(candidate):
            continue
        resolved = resolve_linked_path(run_binding_path, str(candidate))
        if resolved.exists():
            return resolved
    raise ValueError("No existing measurement evidence path was found in run_binding.data_capture.")


def load_measurement_evidence(path: Path) -> dict[str, Any]:
    try:
        payload, _source_format = load_structured_payload(path)
    except ValueError as error:
        raise ValueError(f"Unsupported or invalid measurement evidence format: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Measurement evidence is not valid JSON: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError("Measurement evidence payload must be a JSON object or markdown frontmatter object.")
    schema_version = payload.get("measurement_evidence_schema_version")
    if schema_version is not None and schema_version != MEASUREMENT_EVIDENCE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported measurement_evidence_schema_version: {schema_version}. Expected {MEASUREMENT_EVIDENCE_SCHEMA_VERSION}."
        )
    if not isinstance(payload.get("records"), list):
        raise ValueError("Measurement evidence must contain a top-level records array.")
    return payload


def derive_primary_device_id(run_binding: dict[str, Any]) -> str | None:
    target_device_ids = ensure_list(run_binding.get("hardware_binding", {}).get("target_device_ids"))
    if not target_device_ids:
        return None
    return str(target_device_ids[0])


def fill_record_defaults(record: dict[str, Any], run_binding: dict[str, Any]) -> dict[str, Any]:
    output = deepcopy(record)
    if output.get("cooldown_id") is None and is_non_empty_string(run_binding.get("cooldown_id")):
        output["cooldown_id"] = run_binding["cooldown_id"]
    if output.get("bath_temperature") is None and run_binding.get("fixed_settings", {}).get("T_base") is not None:
        output["bath_temperature"] = run_binding["fixed_settings"]["T_base"]
    if output.get("readout_power") is None and run_binding.get("fixed_settings", {}).get("P_read") is not None:
        output["readout_power"] = run_binding["fixed_settings"]["P_read"]
    return output


def normalise_record(record: dict[str, Any], run_binding: dict[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError(f"Measurement record {index} must be a JSON object.")
    record = fill_record_defaults(record, run_binding)
    missing_fields = []
    if not is_non_empty_string(record.get("cooldown_id")):
        missing_fields.append("cooldown_id")
    for field_name in REQUIRED_MEASUREMENT_FIELDS:
        if field_name not in record or record[field_name] is None:
            missing_fields.append(field_name)
    if missing_fields:
        raise ValueError(f"Measurement record {index} is missing required fields: {', '.join(missing_fields)}")
    return {
        "cooldown_id": str(record["cooldown_id"]),
        "device_id": str(record["device_id"]),
        "geometry_id": str(record["geometry_id"]),
        "history_label": str(record["history_label"]),
        "branch": str(record["branch"]),
        "commanded_field": float(record["commanded_field"]),
        "calibrated_field": float(record["calibrated_field"]),
        "elapsed_time": float(record["elapsed_time"]),
        "dwell_duration": float(record["dwell_duration"]),
        "inv_qi": float(record["inv_qi"]),
        "fr": float(record["fr"]),
        "delta_fr_over_fr": float(record["delta_fr_over_fr"]),
        "T1": None if record.get("T1") is None else float(record["T1"]),
        "witness_response": None if record.get("witness_response") is None else float(record["witness_response"]),
        "bath_temperature": float(record["bath_temperature"]),
        "readout_power": float(record["readout_power"]),
    }


def derive_dwell_metadata(run_binding: dict[str, Any], measurement_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    existing = measurement_evidence.get("dwell_metadata")
    if isinstance(existing, list):
        return deepcopy(existing)
    production_dwell = run_binding.get("field_program", {}).get("production_dwell_t_conv")
    cooldown_id = run_binding.get("cooldown_id")
    if production_dwell is None or not is_non_empty_string(cooldown_id):
        return []
    return [
        {
            "cooldown_id": str(cooldown_id),
            "production_dwell_t_conv": float(production_dwell),
        }
    ]


def build_analysis_input(run_binding: dict[str, Any], measurement_evidence: dict[str, Any]) -> dict[str, Any]:
    records = [
        normalise_record(record, run_binding, index)
        for index, record in enumerate(ensure_list(measurement_evidence.get("records")))
    ]
    branch_slug = run_binding.get("branch_slug") or "e01_mm_flux_history_hysteresis"
    return {
        "analysis_schema_version": DEFAULT_ANALYSIS_SCHEMA_VERSION,
        "branch_slug": str(branch_slug),
        "primary_device_id": derive_primary_device_id(run_binding),
        "matched_geometry_device_ids": [
            str(value) for value in ensure_list(run_binding.get("hardware_binding", {}).get("matched_geometry_device_ids"))
        ],
        "records": records,
        "dwell_metadata": derive_dwell_metadata(run_binding, measurement_evidence),
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build normalized E01 analysis input from authoritative run evidence.")
    parser.add_argument("--run-binding", help="Path to the authoritative run-binding JSON.")
    parser.add_argument("--queue-manifest", help="Optional queue manifest path used to discover run_binding_path.")
    parser.add_argument("--output-path", required=True, help="Path that will receive analysis_input.json.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    run_binding_arg = Path(args.run_binding).resolve() if is_non_empty_string(args.run_binding) else None
    queue_manifest_arg = Path(args.queue_manifest).resolve() if is_non_empty_string(args.queue_manifest) else None
    run_binding, run_binding_path = load_run_binding(run_binding_arg, queue_manifest_arg)
    measurement_evidence_path = choose_measurement_evidence_path(run_binding, run_binding_path)
    measurement_evidence = load_measurement_evidence(measurement_evidence_path)
    analysis_input = build_analysis_input(run_binding, measurement_evidence)
    output_path = Path(args.output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_path, analysis_input)
    print(f"Wrote analysis input to {output_path}")
    print(json.dumps({"record_count": len(analysis_input["records"]), "measurement_evidence_path": str(measurement_evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
