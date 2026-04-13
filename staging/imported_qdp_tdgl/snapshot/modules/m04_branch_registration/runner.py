#!/usr/bin/env python3
"""
Register a QDP v10.6 branch intake (M04) and map it onto the working M02 candidate template.

Usage:
  python modules/m04_branch_registration/runner.py \
    --intake /mnt/data/QDP_v10_6_FORK_INTAKE_TEMPLATE_M04.json \
    --candidate-template /mnt/data/config/schema/candidate_template.json \
    --registry /mnt/data/config/registries/governance_registry.json \
    --write-candidate /mnt/data/QDP_candidate_from_intake_M04.json \
    --write-registration /mnt/data/QDP_branch_registration_M04.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import jsonschema
except ImportError:
    jsonschema = None  # pragma: no cover

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qdp_paths import FORK_INTAKE_SCHEMA


DEFAULT_INTAKE_SCHEMA = FORK_INTAKE_SCHEMA


CHANGE_TYPE_MAP = {
    "HAMILTONIAN_TERM": "HAMILTONIAN_TERM",
    "HAMILTONIAN TERM": "HAMILTONIAN_TERM",
    "FREE_PARAMETER": "FREE_PARAMETER",
    "FREE PARAMETER": "FREE_PARAMETER",
    "OBSERVABLE": "OBSERVABLE",
    "INTEGRATOR": "INTEGRATOR",
    "PLATFORM": "PLATFORM",
    "SCALE_BRIDGE": "SCALE_BRIDGE",
    "SCALE-BRIDGE": "SCALE_BRIDGE",
    "SCALE BRIDGE": "SCALE_BRIDGE",
}

CLASS_MAP = {
    "FORMAL_CORE": "FORMAL_CORE",
    "FORMAL CORE": "FORMAL_CORE",
    "EXAMPLE": "EXAMPLE",
    "INTERPRETATION": "INTERPRETATION",
}

BATH_MAP = {
    "MARKOVIAN_RESERVOIR": "MARKOVIAN_RESERVOIR",
    "MARKOVIAN RESERVOIR": "MARKOVIAN_RESERVOIR",
    "KERNEL_MEMORY": "KERNEL_MEMORY",
    "KERNEL MEMORY": "KERNEL_MEMORY",
    "METASTABLE_C_STATE": "METASTABLE_C_STATE",
    "METASTABLE C-STATE": "METASTABLE_C_STATE",
    "METASTABLE C STATE": "METASTABLE_C_STATE",
    "TLS": "TLS",
    "QP": "QP",
    "QUASIPARTICLE": "QP",
    "PHONON": "PHONON",
    "VORTEX": "VORTEX",
    "EM_PURCELL": "EM_PURCELL",
    "EM/PURCELL": "EM_PURCELL",
    "OTHER": "OTHER",
}

ALLOWED_BATHS = set(BATH_MAP.values())


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def normalize_change_types(values: List[str]) -> List[str]:
    out: List[str] = []
    for raw in values or []:
        key = normalize_text(raw).replace("/", "_")
        norm = CHANGE_TYPE_MAP.get(key)
        if norm and norm not in out:
            out.append(norm)
    return out


def normalize_class(value: str) -> str:
    key = normalize_text(value)
    return CLASS_MAP.get(key, "")


def normalize_bath(value: str) -> str:
    key = normalize_text(value)
    return BATH_MAP.get(key, "")


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return text or "untagged"


def strongest_cap(a: str, b: str) -> str:
    order = {"": 0, "SANDBOX_ONLY": 1, "DEFER": 2, "REJECT": 3}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def validate_against_schema(intake: Dict[str, Any], schema_path: Path) -> None:
    if jsonschema is None or not schema_path.exists():
        return
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(intake), key=lambda e: list(e.path))
    if errors:
        joined = "; ".join(e.message for e in errors)
        raise ValueError(f"intake schema validation failed: {joined}")


def duplicate_scan(tag: str, symbolic_h: str, registry: Dict[str, Any]) -> Tuple[str, str]:
    if not tag and not symbolic_h:
        return "UNASSESSED", ""

    known_tags = set()
    known_symbolic = {}
    for item in registry.get("model_registry", []):
        mt = str(item.get("model_tag", "")).strip()
        if mt:
            known_tags.add(mt)
    for item in registry.get("active_branch_registry", []):
        bt = str(item.get("branch_or_model_tag", "")).strip()
        if bt:
            known_tags.add(bt)
        sym = str(item.get("candidate_H_mod_symbolic", "")).strip()
        if sym:
            known_symbolic[sym] = bt or sym

    if tag and tag in known_tags:
        return "DUPLICATE", tag
    if symbolic_h and symbolic_h in known_symbolic:
        return "DUPLICATE_SYMBOLIC_H", known_symbolic[symbolic_h]
    return "CLEAR", ""


def outcome_from_flags(flags: List[str]) -> str:
    hard_reject = {
        "MISSING_REDUCTION_LIMIT",
        "SCALE_CLAIM_WITHOUT_EFFECTIVE_MAPPING",
        "MISSING_PRIMARY_OBSERVABLE_AND_SECONDARY_OBSERVABLE",
    }
    defer = {
        "MISSING_PRIMARY_OBSERVABLE",
        "MISSING_SECONDARY_OBSERVABLE",
        "MISSING_EXACT_FALSIFIER",
        "BATH_CLASSIFICATION_INCONSISTENT",
        "DUPLICATE_BRANCH_TAG",
        "DUPLICATE_SYMBOLIC_H",
        "MISSING_CHANGE_TYPE",
        "MISSING_MODEL_CLASSIFICATION",
        "MISSING_BRANCH_TAG",
    }
    sandbox = {
        "MORE_THAN_TWO_UNCONSTRAINED_NEW_PARAMETERS",
    }
    if any(flag in hard_reject for flag in flags):
        return "REJECT"
    if any(flag in defer for flag in flags):
        return "DEFER"
    if any(flag in sandbox for flag in flags):
        return "SANDBOX_ONLY"
    return "PROCEED"


def build_registration(intake: Dict[str, Any], registry: Dict[str, Any], candidate_template: Dict[str, Any], intake_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    out = copy.deepcopy(candidate_template)

    change_types = normalize_change_types(intake.get("change_types", []))
    model_classification = normalize_class(intake.get("model_classification", ""))
    declared_bath = normalize_bath(intake.get("declared_likely_bath_class_raw", ""))
    declared_family = normalize_bath(intake.get("declared_family_class", "")) or declared_bath

    bath_asserted = bool(intake.get("bath_classification_consistent_with_glossary_asserted", False))
    bath_consistent = bool(declared_bath and declared_bath in ALLOWED_BATHS and bath_asserted)

    new_params = list(intake.get("new_free_parameters", []))
    source_map = intake.get("independent_constraint_source_per_parameter", {}) or {}
    unconstrained = [p for p in new_params if str(source_map.get(p, "")).strip() == ""]

    flags: List[str] = []
    notes: List[str] = []

    if not intake.get("branch_or_model_tag", "").strip():
        flags.append("MISSING_BRANCH_TAG")
    if not change_types:
        flags.append("MISSING_CHANGE_TYPE")
    if not model_classification:
        flags.append("MISSING_MODEL_CLASSIFICATION")

    primary = str(intake.get("primary_observable", "")).strip()
    secondary = str(intake.get("secondary_observable", "")).strip()
    if not primary and not secondary:
        flags.append("MISSING_PRIMARY_OBSERVABLE_AND_SECONDARY_OBSERVABLE")
    else:
        if not primary:
            flags.append("MISSING_PRIMARY_OBSERVABLE")
        if not secondary:
            flags.append("MISSING_SECONDARY_OBSERVABLE")

    if not str(intake.get("exact_falsifier", "")).strip():
        flags.append("MISSING_EXACT_FALSIFIER")
    if not str(intake.get("reduction_limit", "")).strip():
        flags.append("MISSING_REDUCTION_LIMIT")
    if intake.get("cross_scale_claim_present", False) and not intake.get("effective_mapping_attached", False):
        flags.append("SCALE_CLAIM_WITHOUT_EFFECTIVE_MAPPING")
    if not bath_consistent:
        flags.append("BATH_CLASSIFICATION_INCONSISTENT")
    if len(unconstrained) > 2:
        flags.append("MORE_THAN_TWO_UNCONSTRAINED_NEW_PARAMETERS")
    if not intake.get("relevant_nuisance_controls_list", []):
        flags.append("NUISANCE_CONTROLS_UNDERDECLARED")
    if not intake.get("does_increase_falsifiable_surface_area", False):
        flags.append("FALSIFIABLE_SURFACE_AREA_NOT_INCREASED")

    dup_status, dup_ref = duplicate_scan(
        str(intake.get("branch_or_model_tag", "")).strip(),
        str(intake.get("candidate_H_mod_symbolic", "")).strip(),
        registry,
    )
    if dup_status == "DUPLICATE":
        flags.append("DUPLICATE_BRANCH_TAG")
    elif dup_status == "DUPLICATE_SYMBOLIC_H":
        flags.append("DUPLICATE_SYMBOLIC_H")

    preliminary_outcome = outcome_from_flags(flags)
    intake_cap = preliminary_outcome if preliminary_outcome in {"SANDBOX_ONLY", "DEFER", "REJECT"} else ""

    date_str = str(intake.get("date", "")).strip() or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = slugify(str(intake.get("branch_or_model_tag", "")).strip())
    out["candidate_id"] = out.get("candidate_id") or f"m04-{slug}-{date_str}"
    out["branch_or_model_tag"] = str(intake.get("branch_or_model_tag", "")).strip()
    out["change_type"] = "+".join(change_types)
    out["model_classification"] = model_classification
    out["candidate_H_mod_symbolic"] = str(intake.get("candidate_H_mod_symbolic", "")).strip()
    out["candidate_H_mod_physical_interpretation"] = str(intake.get("candidate_H_mod_physical_interpretation", "")).strip()
    out["claimed_effect"] = str(intake.get("claimed_effect", "")).strip()
    out["declared_family_class"] = declared_family
    out["assigned_family_class"] = out.get("assigned_family_class", "")
    out["family_class_mismatch"] = False
    out["family_status"] = "DECLARED_PENDING_TRIAGE"
    out["declared_likely_bath_class"] = declared_bath
    out["bath_classification_consistent_with_glossary"] = bath_consistent
    out["primary_observable"] = primary
    out["secondary_observable"] = secondary
    out["accessible_platform_or_device_class"] = str(intake.get("accessible_platform_or_device_class", "")).strip()
    out["minimal_discriminant_measurement"] = str(intake.get("minimal_discriminant_measurement", "")).strip()
    out["cross_scale_claim_present"] = bool(intake.get("cross_scale_claim_present", False))
    out["effective_mapping_attached"] = bool(intake.get("effective_mapping_attached", False))
    out["invariant_preserved"] = str(intake.get("invariant_preserved", "")).strip()
    out["reduction_limit"] = str(intake.get("reduction_limit", "")).strip()
    out["count_new_free_parameters"] = int(intake.get("count_new_free_parameters", 0))
    out["new_free_parameters"] = new_params
    out["parameter_constraints"] = intake.get("parameter_constraints", {}) or {}
    out["independent_constraint_source_per_parameter"] = source_map
    out["relevant_nuisance_controls_list"] = intake.get("relevant_nuisance_controls_list", []) or []
    out["exact_falsifier"] = str(intake.get("exact_falsifier", "")).strip()
    out["falsifiable_surface_area_delta"] = (
        "INCREASED" if intake.get("does_increase_falsifiable_surface_area", False) else "NOT_INCREASED"
    )
    out["validation_ladder"]["L0_baseline_pipeline_reproduced"] = bool(
        intake.get("validation_ladder_plan", {}).get("L0_baseline_pipeline_reproduced", False)
    )
    out["validation_ladder"]["L1_reduction_limit_verified"] = bool(
        intake.get("validation_ladder_plan", {}).get("L1_reduction_limit_verified", False)
    )
    out["validation_ladder"]["L2_convergence_plan_defined"] = bool(
        intake.get("validation_ladder_plan", {}).get("L2_convergence_plan_defined", False)
    )
    # Deliberately do not mark L3_numerical_stability_passed from "criterion defined".
    out["validation_ladder"]["L3_numerical_stability_passed"] = False
    out["validation_ladder"]["L4_instrument_facing_comparison_path_defined"] = bool(
        intake.get("validation_ladder_plan", {}).get("L4_instrument_facing_comparison_path_defined", False)
    )
    out["registry_duplicate_status"] = dup_status
    out["duplicate_reference"] = dup_ref

    auto_flags = out.setdefault("automatic_flags_triggered", [])
    for flag in flags:
        if flag not in auto_flags:
            auto_flags.append(flag)

    existing_cap = str(out.get("promotion_cap_governance", "") or "")
    out["promotion_cap_governance"] = strongest_cap(existing_cap, intake_cap)
    out["scientific_decision"] = out.get("scientific_decision") or "NOT_EVALUATED"

    out.setdefault("evaluation_notes", [])
    notes.append(f"M04 preliminary_intake_outcome={preliminary_outcome}")
    notes.append(f"M04 unconstrained_new_parameter_count={len(unconstrained)}")
    notes.append(
        "M04 L3 mapping preserved conservatively: intake L3_stability_criterion_defined does not set validation_ladder.L3_numerical_stability_passed"
    )
    for n in notes:
        if n not in out["evaluation_notes"]:
            out["evaluation_notes"].append(n)

    out.setdefault("linked_artifacts", [])
    for art in [str(intake_path)]:
        if art not in out["linked_artifacts"]:
            out["linked_artifacts"].append(art)

    out.setdefault("gate_trace", [])
    gate_entry = {
        "stage_id": "M04",
        "stage_name": "FORK_INTAKE_AND_BRANCH_REGISTRATION",
        "inputs_checked": [
            "QDP_Fork_Intake_Form_One_Page",
            "FORK_QUESTIONS",
            "MASTER_SPEC",
            "VALIDATION_GATE",
            "governance_registry_duplicate_scan",
        ],
        "decision_or_cap_change": f"PRELIMINARY_INTAKE_OUTCOME:{preliminary_outcome};PROMOTION_CAP_GOVERNANCE:{out['promotion_cap_governance']}",
        "key_evidence_ids": [intake_path.name],
        "status": "FAIL" if preliminary_outcome == "REJECT" else ("WARN" if preliminary_outcome in {"DEFER", "SANDBOX_ONLY"} else "PASS"),
        "notes": "; ".join([
            f"bath_consistent={bath_consistent}",
            f"unconstrained_new_parameter_count={len(unconstrained)}",
            f"L3_stability_criterion_defined={bool(intake.get('validation_ladder_plan', {}).get('L3_stability_criterion_defined', False))}",
            f"duplicate_status={dup_status}",
        ]),
    }
    out["gate_trace"].append(gate_entry)

    registration = {
        "artifact_id": "QDP_V10_6_BRANCH_REGISTRATION_M04",
        "module_id": "M04",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "intake_artifact": str(intake_path),
        "branch_or_model_tag": str(intake.get("branch_or_model_tag", "")).strip(),
        "candidate_id": out["candidate_id"],
        "normalized_fields": {
            "change_types": change_types,
            "model_classification": model_classification,
            "declared_family_class": declared_family,
            "declared_likely_bath_class": declared_bath,
        },
        "bath_classification_consistent_with_glossary": bath_consistent,
        "duplicate_detection": {
            "registry_duplicate_status": dup_status,
            "duplicate_reference": dup_ref,
        },
        "unconstrained_new_parameter_count": len(unconstrained),
        "automatic_flags_triggered": list(auto_flags),
        "preliminary_intake_outcome": preliminary_outcome,
        "preliminary_promotion_cap_governance": intake_cap,
        "intake_ready_for_compute": preliminary_outcome in {"PROCEED", "SANDBOX_ONLY"},
        "notes": notes,
    }
    return out, registration


def main() -> int:
    parser = argparse.ArgumentParser(description="Register a QDP branch intake and map it to the M02 candidate template.")
    parser.add_argument("--intake", required=True, type=Path)
    parser.add_argument("--candidate-template", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--intake-schema", type=Path, default=DEFAULT_INTAKE_SCHEMA)
    parser.add_argument("--write-candidate", type=Path)
    parser.add_argument("--write-registration", type=Path)
    args = parser.parse_args()

    intake = load_json(args.intake)
    candidate_template = load_json(args.candidate_template)
    registry = load_json(args.registry)

    if args.intake_schema:
        validate_against_schema(intake, args.intake_schema)

    candidate, registration = build_registration(intake, registry, candidate_template, args.intake)

    if args.write_candidate:
        args.write_candidate.write_text(json.dumps(candidate, indent=2), encoding="utf-8")
    else:
        print(json.dumps(candidate, indent=2))

    if args.write_registration:
        args.write_registration.write_text(json.dumps(registration, indent=2), encoding="utf-8")
    elif args.write_candidate:
        # If candidate is written to file, also print registration to stdout for visibility.
        print(json.dumps(registration, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
