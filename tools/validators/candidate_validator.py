#!/usr/bin/env python3
"""
QDP v10.6 M02 candidate validator.

Usage:
  python tools/validators/candidate_validator.py candidate.json
  python tools/validators/candidate_validator.py candidate.json --mode final
  python tools/validators/candidate_validator.py candidate.json --schema config/schema/candidate_schema.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    print(f"FATAL: jsonschema import failed: {exc}", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.workflow.qdp_runtime.qdp_paths import SCHEMA


DEFAULT_SCHEMA = SCHEMA

SELF_CHECK_VALUES = {"PASSED", "FAILED", "UNKNOWN"}
SYSTEM_STATUS_VALUES = {
    "READY",
    "HARNESS_REQUIRED",
    "GOVERNANCE_LOGIC_FAILURE",
    "SCHEMA_VALIDATION_FAILURE",
    "REFERENCE_RESOLUTION_FAILURE",
}
CROSS_DEVICE_STATUS_VALUES = {
    "NOT_REQUIRED",
    "SCHEDULED",
    "CONFUNDED",
    "DEVICE_SPECIFIC",
    "INCONSISTENT",
    "CONFIRMED",
}
GOVERNANCE_OUTCOME_VALUES = {"PROCEED", "SANDBOX_ONLY", "DEFER", "REJECT"}
CALIBRATION_STATUS_VALUES = {"PENDING_REVIEW", "UNKNOWN", "VALID", "INVALID"}
IDENTIFIABILITY_STATUS_VALUES = {"PENDING_REVIEW", "INSUFFICIENT", "PROVISIONAL", "SUFFICIENT"}
DRIFT_STATUS_VALUES = {"PENDING_REVIEW", "NOT_REQUIRED", "ASSESSED", "MISSING_MODEL"}
DATASET_GOVERNANCE_STATUS_VALUES = {"PENDING_REVIEW", "INCOMPLETE", "COMPLETE"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def path_str(err: jsonschema.ValidationError) -> str:
    if not err.path:
        return "$"
    return "$." + ".".join(str(x) for x in err.path)


def schema_validate(instance: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        errors.append(f"{path_str(err)}: {err.message}")
    return errors


def semantic_validate(instance: Dict[str, Any], mode: str) -> List[str]:
    errors: List[str] = []

    def require_nonempty(path: str, value: Any) -> None:
        if not isinstance(value, str) or value == "":
            errors.append(f"{path} must be non-empty in final mode")

    gsc = instance.get("governance_self_check", {})
    top_system = instance.get("system_status", "")
    nested_system = gsc.get("system_status", "")
    cross_top = instance.get("cross_device_status", "")
    cross_nested = instance.get("cross_device_validation", {}).get("status", "")
    gov_outcome = instance.get("governance_outcome", "")
    sci = instance.get("scientific_decision", "")
    calibration_status = instance.get("calibration_status", {})
    identifiability_status = instance.get("identifiability_status", {})
    drift_ledger = instance.get("drift_ledger", {})
    dataset_governance = instance.get("dataset_governance", {})

    if mode == "final":
        require_nonempty("$.system_status", top_system)
        require_nonempty("$.governance_self_check.validation_harness_status", gsc.get("validation_harness_status", ""))
        require_nonempty("$.governance_self_check.schema_validation_status", gsc.get("schema_validation_status", ""))
        require_nonempty("$.governance_self_check.reference_resolution_status", gsc.get("reference_resolution_status", ""))
        require_nonempty("$.governance_self_check.determinism_status", gsc.get("determinism_status", ""))
        require_nonempty("$.governance_self_check.system_status", nested_system)
        require_nonempty("$.cross_device_status", cross_top)
        require_nonempty("$.cross_device_validation.status", cross_nested)
        require_nonempty("$.governance_outcome", gov_outcome)
        require_nonempty("$.calibration_status.status", calibration_status.get("status", ""))
        require_nonempty("$.identifiability_status.status", identifiability_status.get("status", ""))
        require_nonempty("$.drift_ledger.status", drift_ledger.get("status", ""))
        require_nonempty("$.dataset_governance.status", dataset_governance.get("status", ""))
        if instance.get("validation_ladder", {}).get("L4_instrument_facing_comparison_path_defined") and not instance.get("exact_falsifier"):
            errors.append("$.exact_falsifier must be non-empty when L4 instrument-facing comparison path is defined")
        if instance.get("validation_ladder", {}).get("L1_reduction_limit_verified") and not instance.get("reduction_limit"):
            errors.append("$.reduction_limit must be non-empty when L1 reduction limit is verified")

    # Exact mirror requirements
    if top_system and nested_system and top_system != nested_system:
        errors.append("$.system_status must match $.governance_self_check.system_status")
    if cross_top and cross_nested and cross_top != cross_nested:
        errors.append("$.cross_device_status must match $.cross_device_validation.status")

    # Known enum values for critical fields when non-empty
    vh = gsc.get("validation_harness_status", "")
    sv = gsc.get("schema_validation_status", "")
    rr = gsc.get("reference_resolution_status", "")
    det = gsc.get("determinism_status", "")

    if vh and vh not in SELF_CHECK_VALUES:
        errors.append("$.governance_self_check.validation_harness_status has invalid value")
    if sv and sv not in SELF_CHECK_VALUES:
        errors.append("$.governance_self_check.schema_validation_status has invalid value")
    if rr and rr not in SELF_CHECK_VALUES:
        errors.append("$.governance_self_check.reference_resolution_status has invalid value")
    if det and det not in SELF_CHECK_VALUES:
        errors.append("$.governance_self_check.determinism_status has invalid value")
    if top_system and top_system not in SYSTEM_STATUS_VALUES:
        errors.append("$.system_status has invalid value")
    if cross_top and cross_top not in CROSS_DEVICE_STATUS_VALUES:
        errors.append("$.cross_device_status has invalid value")
    if gov_outcome and gov_outcome not in GOVERNANCE_OUTCOME_VALUES:
        errors.append("$.governance_outcome has invalid value")
    if calibration_status.get("status") and calibration_status.get("status") not in CALIBRATION_STATUS_VALUES:
        errors.append("$.calibration_status.status has invalid value")
    if identifiability_status.get("status") and identifiability_status.get("status") not in IDENTIFIABILITY_STATUS_VALUES:
        errors.append("$.identifiability_status.status has invalid value")
    if drift_ledger.get("status") and drift_ledger.get("status") not in DRIFT_STATUS_VALUES:
        errors.append("$.drift_ledger.status has invalid value")
    if dataset_governance.get("status") and dataset_governance.get("status") not in DATASET_GOVERNANCE_STATUS_VALUES:
        errors.append("$.dataset_governance.status has invalid value")

    # Build-spec consistency checks
    if sv == "FAILED" and top_system != "SCHEMA_VALIDATION_FAILURE":
        errors.append("schema_validation_status=FAILED requires system_status=SCHEMA_VALIDATION_FAILURE")
    if top_system == "SCHEMA_VALIDATION_FAILURE" and gov_outcome and gov_outcome != "DEFER":
        errors.append("system_status=SCHEMA_VALIDATION_FAILURE requires governance_outcome=DEFER")

    if rr == "FAILED" and top_system != "REFERENCE_RESOLUTION_FAILURE":
        errors.append("reference_resolution_status=FAILED requires system_status=REFERENCE_RESOLUTION_FAILURE")

    if (vh == "FAILED" or det == "FAILED") and top_system != "GOVERNANCE_LOGIC_FAILURE":
        errors.append("validation_harness_status=FAILED or determinism_status=FAILED requires system_status=GOVERNANCE_LOGIC_FAILURE")

    if vh == "UNKNOWN" and top_system != "HARNESS_REQUIRED":
        errors.append("validation_harness_status=UNKNOWN requires system_status=HARNESS_REQUIRED")

    if vh == "UNKNOWN":
        cap = instance.get("promotion_cap_governance", "")
        if mode == "final" and cap != "SANDBOX_ONLY":
            errors.append("validation_harness_status=UNKNOWN requires promotion_cap_governance=SANDBOX_ONLY")

    if gov_outcome == "PROCEED" and cross_top != "CONFIRMED":
        errors.append("governance_outcome=PROCEED is invalid unless cross_device_status=CONFIRMED")

    if sci == "CROSS_DEVICE_CONFIRMED_IDENTIFIABLE" and cross_top != "CONFIRMED":
        errors.append("scientific_decision=CROSS_DEVICE_CONFIRMED_IDENTIFIABLE requires cross_device_status=CONFIRMED")

    if not instance.get("multi_device_data_available", False) and cross_top == "CONFIRMED":
        errors.append("cross_device_status=CONFIRMED is inconsistent with multi_device_data_available=false")

    if instance.get("fabrication_matched_for_geometry_claim") is False and cross_top == "CONFIRMED":
        # only a soft check if geometry was not actually claimed; still useful to flag
        if instance.get("scaling_analysis", {}).get("geometry_claim_fabrication_matched") is False:
            errors.append("cross_device_status=CONFIRMED is suspect when fabrication_matched_for_geometry_claim=false and geometry_claim_fabrication_matched=false")

    top_score = instance.get("calibration_validity_score")
    nested_score = calibration_status.get("validity_score")
    if top_score is not None and nested_score is not None and top_score != nested_score:
        errors.append("$.calibration_validity_score must match $.calibration_status.validity_score when both are present")

    threshold = calibration_status.get("threshold", 70)
    below_threshold = calibration_status.get("below_threshold", False)
    if nested_score is not None and isinstance(nested_score, (int, float)):
        if nested_score < threshold and not below_threshold:
            errors.append("$.calibration_status.below_threshold must be true when validity_score is below threshold")
        if nested_score >= threshold and below_threshold:
            errors.append("$.calibration_status.below_threshold must be false when validity_score meets threshold")
        if nested_score < threshold and calibration_status.get("status") == "VALID":
            errors.append("$.calibration_status.status=VALID is inconsistent with below-threshold calibration score")
        if nested_score >= threshold and calibration_status.get("status") == "INVALID":
            errors.append("$.calibration_status.status=INVALID is inconsistent with above-threshold calibration score")

    if below_threshold and gov_outcome == "PROCEED":
        errors.append("calibration below threshold is incompatible with governance_outcome=PROCEED")
    if calibration_status.get("status") == "INVALID" and gov_outcome == "PROCEED":
        errors.append("calibration_status=INVALID is incompatible with governance_outcome=PROCEED")
    if dataset_governance.get("status") == "INCOMPLETE" and gov_outcome == "PROCEED":
        errors.append("dataset_governance.status=INCOMPLETE is incompatible with governance_outcome=PROCEED")
    if identifiability_status.get("status") == "INSUFFICIENT" and gov_outcome == "PROCEED":
        errors.append("identifiability_status.status=INSUFFICIENT is incompatible with governance_outcome=PROCEED")
    if drift_ledger.get("status") == "MISSING_MODEL" and gov_outcome == "PROCEED":
        errors.append("drift_ledger.status=MISSING_MODEL is incompatible with governance_outcome=PROCEED")

    if sci == "CROSS_DEVICE_CONFIRMED_IDENTIFIABLE":
        if calibration_status.get("status") in {"PENDING_REVIEW", "UNKNOWN", "INVALID"}:
            errors.append("scientific_decision=CROSS_DEVICE_CONFIRMED_IDENTIFIABLE requires calibration_status=VALID")
        if dataset_governance.get("status") != "COMPLETE":
            errors.append("scientific_decision=CROSS_DEVICE_CONFIRMED_IDENTIFIABLE requires dataset_governance.status=COMPLETE")
        if identifiability_status.get("status") not in {"PROVISIONAL", "SUFFICIENT"}:
            errors.append("scientific_decision=CROSS_DEVICE_CONFIRMED_IDENTIFIABLE requires identifiability_status to be provisional or sufficient")
        if drift_ledger.get("status") not in {"ASSESSED", "NOT_REQUIRED"}:
            errors.append("scientific_decision=CROSS_DEVICE_CONFIRMED_IDENTIFIABLE requires drift_ledger.status to be assessed or not required")

    # failure_mode_library_hits consistency
    hits = instance.get("failure_mode_library_hits", [])
    if "SCHEMA_VALIDATION_FAILURE" in hits and top_system != "SCHEMA_VALIDATION_FAILURE":
        errors.append("failure_mode_library_hits contains SCHEMA_VALIDATION_FAILURE but system_status does not match")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a QDP v10.6 M02 candidate JSON object.")
    parser.add_argument("candidate", type=Path, help="Path to candidate JSON file")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="Path to JSON Schema file")
    parser.add_argument("--mode", choices=["template", "final"], default="template", help="Validation mode")
    args = parser.parse_args()

    if not args.candidate.exists():
        print(f"FATAL: candidate file not found: {args.candidate}", file=sys.stderr)
        return 2
    if not args.schema.exists():
        print(f"FATAL: schema file not found: {args.schema}", file=sys.stderr)
        return 2

    try:
        instance = load_json(args.candidate)
    except Exception as exc:
        print(f"FATAL: could not parse candidate JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(instance, dict):
        print("INVALID: candidate root must be exactly one JSON object", file=sys.stderr)
        return 1

    try:
        schema = load_json(args.schema)
    except Exception as exc:
        print(f"FATAL: could not parse schema JSON: {exc}", file=sys.stderr)
        return 2

    errors = schema_validate(instance, schema)
    errors.extend(semantic_validate(instance, args.mode))

    if errors:
        print("INVALID")
        for msg in errors:
            print(f"- {msg}")
        return 1

    print("VALID")
    print(f"- mode: {args.mode}")
    print(f"- candidate: {args.candidate}")
    print(f"- schema: {args.schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

