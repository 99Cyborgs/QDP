#!/usr/bin/env python3
"""
Validate a QDP v10.6 M04 fork-intake JSON object.

Usage:
  python tools/validators/fork_intake_validator.py intake.json
  python tools/validators/fork_intake_validator.py intake.json --mode final
  python tools/validators/fork_intake_validator.py intake.json --schema /mnt/data/QDP_v10_6_FORK_INTAKE_SCHEMA_M04.schema.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    print(f"FATAL: jsonschema import failed: {exc}", file=sys.stderr)
    raise SystemExit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qdp_paths import FORK_INTAKE_SCHEMA


DEFAULT_SCHEMA = FORK_INTAKE_SCHEMA

REQUIRED_NONEMPTY_FINAL = [
    ("$.branch_or_model_tag", "branch_or_model_tag"),
    ("$.model_classification", "model_classification"),
    ("$.declared_likely_bath_class_raw", "declared_likely_bath_class_raw"),
    ("$.primary_observable", "primary_observable"),
    ("$.secondary_observable", "secondary_observable"),
    ("$.accessible_platform_or_device_class", "accessible_platform_or_device_class"),
    ("$.minimal_discriminant_measurement", "minimal_discriminant_measurement"),
    ("$.invariant_preserved", "invariant_preserved"),
    ("$.reduction_limit", "reduction_limit"),
    ("$.exact_falsifier", "exact_falsifier"),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def path_str(err: jsonschema.ValidationError) -> str:
    if not err.path:
        return "$"
    return "$." + ".".join(str(x) for x in err.path)


def schema_validate(instance: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    validator = jsonschema.Draft202012Validator(schema)
    errors: List[str] = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        errors.append(f"{path_str(err)}: {err.message}")
    return errors


def semantic_validate(instance: Dict[str, Any], mode: str) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if mode == "final":
        for label, key in REQUIRED_NONEMPTY_FINAL:
            if not isinstance(instance.get(key, ""), str) or instance.get(key, "") == "":
                errors.append(f"{label} must be non-empty in final mode")
        if not instance.get("change_types"):
            errors.append("$.change_types must contain at least one trigger in final mode")

    if instance.get("declared_likely_bath_class_raw") == "OTHER" and instance.get("declared_likely_bath_class_other_text", "") == "":
        errors.append("$.declared_likely_bath_class_other_text must be non-empty when declared_likely_bath_class_raw=OTHER")

    if instance.get("cross_scale_claim_present") and not instance.get("effective_mapping_attached"):
        errors.append("cross_scale_claim_present=true requires effective_mapping_attached=true")

    new_params = instance.get("new_free_parameters", [])
    count = instance.get("count_new_free_parameters", 0)
    if count != len(new_params):
        errors.append("$.count_new_free_parameters must equal len($.new_free_parameters)")

    if len(new_params) != len(set(new_params)):
        errors.append("$.new_free_parameters contains duplicates")

    source_map = instance.get("independent_constraint_source_per_parameter", {})
    unconstrained = [p for p in new_params if str(source_map.get(p, "")).strip() == ""]
    if unconstrained:
        warnings.append(
            "independent constraint source missing for: " + ", ".join(unconstrained)
        )
    if len(unconstrained) > 2:
        warnings.append(">2 unconstrained new parameters will force SANDBOX_ONLY under M04")

    if not instance.get("bath_classification_consistent_with_glossary_asserted", False):
        warnings.append("bath_classification_consistent_with_glossary_asserted=false")

    if not instance.get("relevant_nuisance_controls_list"):
        warnings.append("relevant_nuisance_controls_list is empty")

    if not instance.get("does_increase_falsifiable_surface_area", False):
        warnings.append("does_increase_falsifiable_surface_area=false")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a QDP v10.6 M04 fork intake JSON object.")
    parser.add_argument("intake", type=Path, help="Path to intake JSON file")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="Path to intake schema")
    parser.add_argument("--mode", choices=["template", "final"], default="template", help="Validation mode")
    args = parser.parse_args()

    if not args.intake.exists():
        print(f"FATAL: intake file not found: {args.intake}", file=sys.stderr)
        return 2
    if not args.schema.exists():
        print(f"FATAL: schema file not found: {args.schema}", file=sys.stderr)
        return 2

    try:
        instance = load_json(args.intake)
        schema = load_json(args.schema)
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2

    if not isinstance(instance, dict):
        print("INVALID: intake root must be exactly one JSON object", file=sys.stderr)
        return 1

    errors = schema_validate(instance, schema)
    sem_errors, warnings = semantic_validate(instance, args.mode)
    errors.extend(sem_errors)

    if errors:
        print("INVALID")
        for msg in errors:
            print(f"- {msg}")
        for msg in warnings:
            print(f"! WARNING: {msg}")
        return 1

    print("VALID")
    print(f"- mode: {args.mode}")
    print(f"- intake: {args.intake}")
    print(f"- schema: {args.schema}")
    for msg in warnings:
        print(f"! WARNING: {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
