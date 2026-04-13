from __future__ import annotations

import copy
from typing import Any, Dict, List


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
TERMINATING_SYSTEM_STATUSES = {"GOVERNANCE_LOGIC_FAILURE", "REFERENCE_RESOLUTION_FAILURE"}
RAW_PROCEED_DECISION_INPUTS = {
    "",
    "NOT_EVALUATED",
    "PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST",
}


def upper_text(value: Any) -> str:
    return str(value or "").strip().upper()


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().upper() in {"TRUE", "YES", "1", "PASSED", "PASS", "READY"}
    return False


def list_of_strings(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def unique_preserve(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def derive_system_status(gsc: Dict[str, Any], fallback: str = "") -> str:
    schema = str(gsc.get("schema_validation_status", "") or "")
    ref = str(gsc.get("reference_resolution_status", "") or "")
    harness = str(gsc.get("validation_harness_status", "") or "")
    determinism = str(gsc.get("determinism_status", "") or "")
    if schema == "FAILED":
        return "SCHEMA_VALIDATION_FAILURE"
    if ref == "FAILED":
        return "REFERENCE_RESOLUTION_FAILURE"
    if harness == "FAILED" or determinism == "FAILED":
        return "GOVERNANCE_LOGIC_FAILURE"
    if harness == "UNKNOWN":
        return "HARNESS_REQUIRED"
    if harness == "PASSED" and determinism == "PASSED" and ref == "PASSED" and schema == "PASSED":
        return "READY"
    return fallback or str(gsc.get("system_status", "") or "")


def strongest_governance_cap(a: str, b: str) -> str:
    order = {"": 0, "PROCEED": 1, "SANDBOX_ONLY": 2, "DEFER": 3, "REJECT": 4}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def strongest_scientific_cap(a: str, b: str) -> str:
    order = {"": 0, "SANDBOX_ONLY": 1}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def sync_governance_system_status(candidate: Dict[str, Any]) -> str:
    gsc = candidate.setdefault("governance_self_check", {})
    gsc.setdefault("validation_harness_status", "UNKNOWN")
    gsc.setdefault("schema_validation_status", "UNKNOWN")
    gsc.setdefault("reference_resolution_status", "UNKNOWN")
    gsc.setdefault("determinism_status", "UNKNOWN")
    derived = derive_system_status(gsc, fallback=str(candidate.get("system_status", "") or gsc.get("system_status", "")))
    gsc["system_status"] = derived
    candidate["system_status"] = derived
    return derived


def set_cross_device_status(candidate: Dict[str, Any], status: str, notes: str = "") -> None:
    candidate["cross_device_status"] = status
    nested = candidate.setdefault("cross_device_validation", {})
    nested["status"] = status
    nested.setdefault("devices_tested", [])
    nested.setdefault("fabrication_matched", bool(candidate.get("fabrication_matched_for_geometry_claim", False)))
    if notes:
        nested["notes"] = notes
    else:
        nested.setdefault("notes", "")


def apply_terminal_outcome(
    candidate: Dict[str, Any],
    *,
    scientific_decision: str,
    governance_outcome: str,
    cross_device_status: str,
    terminated_at: str,
) -> None:
    candidate["scientific_decision"] = scientific_decision
    candidate["governance_outcome"] = governance_outcome
    candidate["terminated_at"] = terminated_at
    set_cross_device_status(candidate, cross_device_status)


def append_gate_trace(
    candidate: Dict[str, Any],
    *,
    stage_id: str,
    stage_name: str,
    inputs_checked: List[str],
    decision_or_cap_change: str,
    key_evidence_ids: List[str],
    status: str,
    notes: str,
) -> None:
    candidate.setdefault("gate_trace", []).append(
        {
            "stage_id": stage_id,
            "stage_name": stage_name,
            "inputs_checked": inputs_checked,
            "decision_or_cap_change": decision_or_cap_change,
            "key_evidence_ids": key_evidence_ids,
            "status": status,
            "notes": notes,
        }
    )


def ensure_governance_structures(candidate: Dict[str, Any]) -> None:
    candidate.setdefault("cross_device_validation", {"status": "", "devices_tested": [], "fabrication_matched": False, "notes": ""})
    candidate.setdefault(
        "calibration_status",
        {
            "status": "PENDING_REVIEW",
            "validity_score": None,
            "threshold": 70.0,
            "below_threshold": False,
            "notes": "",
        },
    )
    candidate.setdefault(
        "identifiability_status",
        {
            "status": "PENDING_REVIEW",
            "orthogonal_axes_satisfied": False,
            "independent_constraints_satisfied": False,
            "notes": "",
        },
    )
    candidate.setdefault(
        "drift_ledger",
        {
            "status": "PENDING_REVIEW",
            "hierarchical_model_required": False,
            "hierarchical_model_applied": False,
            "notes": "",
        },
    )
    candidate.setdefault(
        "dataset_governance",
        {
            "status": "PENDING_REVIEW",
            "device_lineage_recorded": False,
            "calibration_context_recorded": False,
            "protocol_metadata_recorded": False,
            "independent_evidence_eligible": False,
            "notes": "",
        },
    )
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("failure_mode_library_hits", [])
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("gate_trace", [])
    if not str(candidate.get("scientific_decision", "") or "").strip():
        candidate["scientific_decision"] = "NOT_EVALUATED"
    if not str(candidate.get("governance_outcome", "") or "").strip():
        candidate["governance_outcome"] = "SANDBOX_ONLY"
    candidate.setdefault("promotion_cap_governance", "")
    candidate.setdefault("promotion_cap_scientific", "")
    candidate.setdefault("terminated_at", "")
    if not str(candidate.get("cross_device_status", "") or "").strip():
        if candidate.get("governance_outcome", "") in {"REJECT", "DEFER"}:
            candidate["cross_device_status"] = "NOT_REQUIRED"
        elif bool(candidate.get("multi_device_data_available", False)):
            candidate["cross_device_status"] = "DEVICE_SPECIFIC"
        else:
            candidate["cross_device_status"] = "SCHEDULED"
    nested = candidate["cross_device_validation"]
    if not str(nested.get("status", "") or "").strip():
        nested["status"] = candidate["cross_device_status"]
    nested.setdefault("devices_tested", [])
    nested.setdefault("fabrication_matched", bool(candidate.get("fabrication_matched_for_geometry_claim", False)))
    nested.setdefault("notes", "")
    sync_governance_system_status(candidate)


def clip_candidate_with_caps(candidate: Dict[str, Any]) -> List[str]:
    decisions: List[str] = []
    if candidate.get("governance_outcome", "") == "PROCEED" and candidate.get("promotion_cap_governance", "") == "SANDBOX_ONLY":
        candidate["governance_outcome"] = "SANDBOX_ONLY"
        decisions.append("CLIP governance_outcome PROCEED->SANDBOX_ONLY due promotion_cap_governance=SANDBOX_ONLY")
    if candidate.get("governance_outcome", "") == "PROCEED" and candidate.get("promotion_cap_governance", "") == "DEFER":
        candidate["governance_outcome"] = "DEFER"
        decisions.append("CLIP governance_outcome PROCEED->DEFER due promotion_cap_governance=DEFER")
    if candidate.get("governance_outcome", "") == "PROCEED" and candidate.get("promotion_cap_governance", "") == "REJECT":
        candidate["governance_outcome"] = "REJECT"
        decisions.append("CLIP governance_outcome PROCEED->REJECT due promotion_cap_governance=REJECT")
    if candidate.get("scientific_decision", "") == "CROSS_DEVICE_CONFIRMED_IDENTIFIABLE" and candidate.get("promotion_cap_scientific", "") == "SANDBOX_ONLY":
        candidate["scientific_decision"] = "SANDBOX_ONLY"
        candidate["governance_outcome"] = "SANDBOX_ONLY"
        decisions.append("CLIP scientific_decision CROSS_DEVICE_CONFIRMED_IDENTIFIABLE->SANDBOX_ONLY due promotion_cap_scientific=SANDBOX_ONLY")
    return decisions


def complete_governance_fallback(candidate: Dict[str, Any]) -> str:
    if candidate.get("governance_outcome", ""):
        return "NO_CHANGE"
    scientific_decision = candidate.get("scientific_decision", "")
    if scientific_decision in {"PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST", "SANDBOX_ONLY"}:
        candidate["governance_outcome"] = "SANDBOX_ONLY"
    elif scientific_decision == "NOT_EVALUATED":
        candidate["governance_outcome"] = "DEFER"
    else:
        candidate["governance_outcome"] = "REJECT"
    return f"SET governance_outcome={candidate['governance_outcome']}"


def clone_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(candidate)
    ensure_governance_structures(out)
    return out
