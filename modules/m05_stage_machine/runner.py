#!/usr/bin/env python3
"""
QDP v10.6 M05 gate-trace and validation-ladder stage machine.

This is a conservative working-patch implementation of the visible v10.6 rules.
It does not claim no-loss parity with the retained v10.1 operative body.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = REPO_ROOT / "packages" / "qdp_io" / "src"
for path in (REPO_ROOT, QDP_IO_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_io.artifacts import dump_json, module_report_header, module_selftest_report_payload, utc_now
from modules.m07_family_triage.runner import run_family_triage
from modules.m08_baseline_fit.runner import run_baseline_fit
from modules.m09_mechanism_competition.runner import run_mechanism_competition
from modules.m10_artifact_audit.runner import run_artifact_audit
from modules.m11_lindblad_equivalence.runner import run_lindblad_equivalence
from modules.m12_experiment_design.runner import run_experiment_design
from modules.m13_cross_device_gate.runner import run_cross_device_gate
from modules.m14_promotion_caps.runner import run_promotion_caps
from modules.m15_governance_guardrails.runner import run_governance_guardrails
from tools.workflow.qdp_runtime.qdp_paths import BASE_TEMPLATE, CANDIDATE_VALIDATOR, MODULES, SCHEMA
from tools.workflow.qdp_runtime.qdp_validation import validate_candidate_file


MODULE_PATHS = MODULES["m05"]
DEFAULT_BASE_TEMPLATE = BASE_TEMPLATE
DEFAULT_SCHEMA = SCHEMA
DEFAULT_VALIDATOR = CANDIDATE_VALIDATOR
DEFAULT_SELFTEST_CASES = MODULE_PATHS["selftest_cases"]
DEFAULT_SELFTEST_REPORT = MODULE_PATHS["selftest_report"]
DEFAULT_SELFTEST_OUTPUT_DIR = MODULE_PATHS["selftest_output_dir"]

MISSING = object()
TERMINATING_SYSTEM_STATUSES = {"GOVERNANCE_LOGIC_FAILURE", "REFERENCE_RESOLUTION_FAILURE"}
RAW_PROCEED_DECISION_INPUTS = {
    "",
    "NOT_EVALUATED",
    "PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST",
}
CONFIRMABLE_CROSS_DEVICE_STATUSES = {"DEVICE_SPECIFIC", "INCONSISTENT", "CONFIRMED"}
SELFTEST_BASE_PROFILE = {
    "validation_harness_status": "PASSED",
    "schema_validation_status": "UNKNOWN",
    "reference_resolution_status": "PASSED",
    "determinism_status": "PASSED",
    "system_status": "READY",
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = copy.deepcopy(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    return copy.deepcopy(override)


def make_minimal_final_candidate(base_template: Dict[str, Any]) -> Dict[str, Any]:
    candidate = copy.deepcopy(base_template)
    candidate["candidate_id"] = candidate.get("candidate_id", "") or "M05_WORKING_PATCH_CANDIDATE"
    candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or "M05_WORKING_PATCH_BRANCH"
    candidate["change_type"] = candidate.get("change_type", "") or "HAMILTONIAN_TERM"
    candidate["model_classification"] = candidate.get("model_classification", "") or "FORMAL_CORE"
    candidate["declared_family_class"] = candidate.get("declared_family_class", "") or "UNASSESSED"
    candidate["assigned_family_class"] = candidate.get("assigned_family_class", "") or "UNASSESSED"
    candidate["family_status"] = candidate.get("family_status", "") or "PENDING_M05"
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("failure_mode_library_hits", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("gate_trace", [])
    candidate.setdefault("validation_ladder", {})
    candidate["governance_self_check"] = {
        "validation_harness_status": "UNKNOWN",
        "schema_validation_status": "UNKNOWN",
        "reference_resolution_status": "UNKNOWN",
        "determinism_status": "UNKNOWN",
        "system_status": "HARNESS_REQUIRED",
    }
    candidate["system_status"] = "HARNESS_REQUIRED"
    candidate["scientific_decision"] = ""
    candidate["governance_outcome"] = ""
    candidate["cross_device_status"] = ""
    candidate["promotion_cap_governance"] = ""
    candidate["promotion_cap_scientific"] = ""
    candidate.setdefault("cross_device_validation", {})
    candidate["cross_device_validation"]["status"] = ""
    return candidate


def derive_system_status(gsc: Dict[str, Any], fallback: str = "") -> str:
    schema = gsc.get("schema_validation_status", "")
    ref = gsc.get("reference_resolution_status", "")
    harness = gsc.get("validation_harness_status", "")
    determinism = gsc.get("determinism_status", "")
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
    return fallback or gsc.get("system_status", "") or ""


def strongest_governance_cap(a: str, b: str) -> str:
    order = {"": 0, "PROCEED": 1, "SANDBOX_ONLY": 2, "DEFER": 3, "REJECT": 4}
    return a if order.get(a, 0) >= order.get(b, 0) else b


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
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def stage_data(stage_inputs: Dict[str, Any], stage_key: str) -> Dict[str, Any]:
    value = stage_inputs.get(stage_key, {})
    return value if isinstance(value, dict) else {}


def stage_override(stage_inputs: Dict[str, Any], stage_key: str, field: str) -> Any:
    return stage_data(stage_inputs, stage_key).get(field, MISSING)


def stage_evidence_ids(stage_inputs: Dict[str, Any], stage_key: str) -> List[str]:
    return list_of_strings(stage_data(stage_inputs, stage_key).get("evidence_ids", []))


def clear_placeholder_governance(candidate: Dict[str, Any]) -> bool:
    scientific_decision = str(candidate.get("scientific_decision", "") or "")
    governance_outcome = str(candidate.get("governance_outcome", "") or "")
    if scientific_decision == "NOT_EVALUATED" and governance_outcome == "DEFER" and not str(candidate.get("terminated_at", "") or ""):
        candidate["governance_outcome"] = ""
        return True
    return False


def ensure_structures(candidate: Dict[str, Any]) -> None:
    candidate.setdefault("baseline_model", {})
    candidate.setdefault("residual_analysis", {})
    candidate.setdefault("mechanism_tests", {})
    candidate.setdefault("artifact_tests", {})
    candidate.setdefault("hamiltonian_test", {})
    candidate.setdefault("lindblad_equivalence", {})
    candidate.setdefault("scaling_analysis", {})
    candidate.setdefault("numerical_stability", {})
    candidate.setdefault("experiment_schedule", {})
    candidate.setdefault("cross_device_validation", {})
    candidate.setdefault("instrument_capabilities", {})
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("failure_mode_library_hits", [])
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("gate_trace", [])
    candidate.setdefault("validation_ladder", {})
    ladder = candidate["validation_ladder"]
    ladder["L0_baseline_pipeline_reproduced"] = False
    ladder["L1_reduction_limit_verified"] = False
    ladder["L2_convergence_plan_defined"] = False
    ladder["L3_numerical_stability_passed"] = False
    ladder["L4_instrument_facing_comparison_path_defined"] = False
    candidate["scientific_decision"] = ""
    candidate["governance_outcome"] = ""
    candidate["cross_device_status"] = ""
    candidate["cross_device_validation"]["status"] = ""
    candidate["terminated_at"] = ""


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
    candidate.setdefault("cross_device_validation", {})
    candidate["cross_device_validation"]["status"] = status
    candidate["cross_device_validation"].setdefault("devices_tested", [])
    candidate["cross_device_validation"].setdefault(
        "fabrication_matched",
        bool(candidate.get("fabrication_matched_for_geometry_claim", False)),
    )
    if notes:
        candidate["cross_device_validation"]["notes"] = notes
    else:
        candidate["cross_device_validation"].setdefault("notes", "")


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


def baseline_pipeline_executed(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    override = stage_override(stage_inputs, "stage5", "baseline_pipeline_executed")
    if override is not MISSING:
        return bool_value(override)
    baseline = candidate.get("baseline_model", {})
    status = upper_text(baseline.get("status", ""))
    return status in {"EXECUTED_SUCCESSFULLY", "BASELINE_PIPELINE_EXECUTED", "PASSED", "REPRODUCED"} or bool_value(
        baseline.get("pipeline_executed", False)
    )


def baseline_suffices(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    override = stage_override(stage_inputs, "stage6", "baseline_suffices")
    if override is not MISSING:
        return bool_value(override)
    residuals = candidate.get("residual_analysis", {})
    return (
        candidate.get("validation_ladder", {}).get("L0_baseline_pipeline_reproduced", False)
        and bool_value(residuals.get("white_residuals", False))
        and bool_value(residuals.get("stationary_residuals", False))
        and not bool_value(residuals.get("structured_residuals", False))
        and bool_value(residuals.get("cross_observable_correlations_vanish", False))
        and bool_value(residuals.get("drift_aware_fit_applied", False))
    )


def known_mechanism_explains(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    override = stage_override(stage_inputs, "stage8", "known_mechanism_explains")
    if override is not MISSING:
        return bool_value(override)
    tests = candidate.get("mechanism_tests", {})
    if bool_value(tests.get("explains_data", False)) or bool_value(tests.get("parsimonious_combination_explains", False)):
        return True
    for value in tests.values():
        if isinstance(value, dict) and bool_value(value.get("explains_data", False)):
            return True
    return False


def artifact_route_explains(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    override = stage_override(stage_inputs, "stage9", "artifact_route_explains")
    if override is not MISSING:
        return bool_value(override)
    tests = candidate.get("artifact_tests", {})
    return bool_value(tests.get("route_explains_data", False)) or bool_value(tests.get("explains_data", False))


def convergence_plan_declared(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    override = stage_override(stage_inputs, "stage10", "convergence_plan_declared")
    if override is not MISSING:
        return bool_value(override)
    hamiltonian = candidate.get("hamiltonian_test", {})
    return bool_value(hamiltonian.get("convergence_plan_declared", False)) or bool_value(
        hamiltonian.get("plan_declared_before_nonlinear_sweeps", False)
    )


def reduction_limit_verified(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    override = stage_override(stage_inputs, "stage10", "reduction_limit_verified")
    if override is not MISSING:
        return bool_value(override)
    baseline = candidate.get("baseline_model", {})
    return str(candidate.get("reduction_limit", "")).strip() != "" and (
        bool_value(baseline.get("reduction_limit_verified", False))
        or bool_value(baseline.get("reduction_limit_test_passed", False))
    )


def equivalent_within_resolution(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    override = stage_override(stage_inputs, "stage11", "equivalent_within_resolution")
    if override is not MISSING:
        return bool_value(override)
    return bool_value(candidate.get("lindblad_equivalence", {}).get("equivalent_within_resolution", False))


def numerical_stability_passed(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    override = stage_override(stage_inputs, "stage13", "numerical_stability_passed")
    if override is not MISSING:
        return bool_value(override)
    stability = candidate.get("numerical_stability", {})
    return bool_value(stability.get("stable", False)) and not list_of_strings(stability.get("failed_checks", []))


def instrument_facing_path_defined(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    emitted = stage_override(stage_inputs, "stage15", "executable_falsifier_package_emitted")
    requirement = stage_override(stage_inputs, "stage15", "experiment_design_law_satisfied")
    if emitted is not MISSING or requirement is not MISSING:
        package_emitted = bool_value(False if emitted is MISSING else emitted)
        requirement_met = bool_value(False if requirement is MISSING else requirement)
    else:
        schedule = candidate.get("experiment_schedule", {})
        package_emitted = bool_value(schedule.get("executable_falsifier_package_emitted", False)) or (
            "EXECUTABLE_FALSIFIER_PACKAGE" in list_of_strings(candidate.get("requested_output_artifacts", []))
        )
        requirement_met = bool_value(candidate.get("instrument_capabilities", {}).get("instrument_facing_requirement_satisfied", False)) and bool(
            list_of_strings(schedule.get("priority_experiments", []))
        )
    return str(candidate.get("exact_falsifier", "")).strip() != "" and package_emitted and requirement_met


def geometry_claimed_discriminator(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> bool:
    override = stage_override(stage_inputs, "stage16", "geometry_claimed_discriminator")
    if override is not MISSING:
        return bool_value(override)
    scaling = candidate.get("scaling_analysis", {})
    axes = {upper_text(item) for item in list_of_strings(scaling.get("axes_used", []))}
    return bool_value(scaling.get("geometry_claimed_discriminator", False)) or bool(axes & {"GEOMETRY", "DEVICE_GEOMETRY"})


def mapped_cross_device_status(candidate: Dict[str, Any], stage_inputs: Dict[str, Any]) -> str:
    override = upper_text(stage_override(stage_inputs, "stage16", "signal_consistency"))
    if override in CONFIRMABLE_CROSS_DEVICE_STATUSES:
        return override
    nested = candidate.get("cross_device_validation", {})
    direct = upper_text(nested.get("status", ""))
    if direct in CONFIRMABLE_CROSS_DEVICE_STATUSES:
        return direct
    consistency_class = upper_text(nested.get("consistency_class", ""))
    if consistency_class in CONFIRMABLE_CROSS_DEVICE_STATUSES:
        return consistency_class
    devices = list_of_strings(nested.get("devices_tested", []))
    if len(devices) <= 1:
        return "DEVICE_SPECIFIC"
    return "INCONSISTENT"


def internal_schema_validate(
    candidate: Dict[str, Any],
    validator_path: Path,
    schema_path: Path,
    mode: str = "final",
) -> Dict[str, Any]:
    validator_module = load_module(validator_path, "qdp_m02_validator_internal")
    schema = load_json(schema_path)
    errors = validator_module.schema_validate(candidate, schema)
    errors.extend(validator_module.semantic_validate(candidate, mode))
    return {
        "valid": not errors,
        "errors": errors,
        "schema_path": str(schema_path),
        "validator_path": str(validator_path),
        "mode": mode,
    }


def validate_candidate_with_existing_validator(
    candidate: Dict[str, Any],
    validator_path: Path,
    schema_path: Path,
    output_dir: Path,
    case_id: str,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = output_dir / f"{case_id}_candidate.json"
    candidate_path.write_text(json.dumps(candidate, indent=2), encoding="utf-8")
    return validate_candidate_file(candidate_path, validator_path, schema_path, mode="final")


def compare_expected(candidate: Dict[str, Any], report: Dict[str, Any], expected: Dict[str, Any]) -> Tuple[bool, List[str]]:
    failures: List[str] = []
    for key, expected_value in expected.items():
        if key == "validation_ladder":
            actual_ladder = candidate.get("validation_ladder", {})
            if not isinstance(expected_value, dict):
                failures.append("expected.validation_ladder must be an object")
                continue
            for ladder_key, ladder_expected in expected_value.items():
                actual = actual_ladder.get(ladder_key)
                if actual != ladder_expected:
                    failures.append(
                        f"validation_ladder.{ladder_key}: expected {ladder_expected!r} got {actual!r}"
                    )
        elif key == "terminated_at":
            actual = report.get("terminated_at", "")
            if actual != expected_value:
                failures.append(f"terminated_at: expected {expected_value!r} got {actual!r}")
        else:
            actual = candidate.get(key)
            if actual != expected_value:
                failures.append(f"{key}: expected {expected_value!r} got {actual!r}")
    return not failures, failures


def run_state_machine(
    candidate: Dict[str, Any],
    stage_inputs: Dict[str, Any] | None = None,
    *,
    schema_path: Path = DEFAULT_SCHEMA,
    validator_path: Path = DEFAULT_VALIDATOR,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    stage_inputs = stage_inputs if isinstance(stage_inputs, dict) else {}
    out = copy.deepcopy(candidate)
    ensure_structures(out)

    terminated = False
    termination_reason = ""

    current_system_status = sync_governance_system_status(out)
    precheck_decisions: List[str] = []
    if out.get("governance_self_check", {}).get("validation_harness_status") == "UNKNOWN":
        out["promotion_cap_governance"] = strongest_governance_cap(str(out.get("promotion_cap_governance", "") or ""), "SANDBOX_ONLY")
        precheck_decisions.append("FORCE promotion_cap_governance=SANDBOX_ONLY due validation_harness_status=UNKNOWN")
    if out.get("governance_self_check", {}).get("reference_resolution_status") == "FAILED":
        out["promotion_cap_governance"] = strongest_governance_cap(str(out.get("promotion_cap_governance", "") or ""), "SANDBOX_ONLY")
        precheck_decisions.append("FORCE promotion_cap_governance=SANDBOX_ONLY due reference_resolution_status=FAILED")
    if current_system_status in TERMINATING_SYSTEM_STATUSES:
        apply_terminal_outcome(
            out,
            scientific_decision="NOT_EVALUATED",
            governance_outcome="DEFER",
            cross_device_status="NOT_REQUIRED",
            terminated_at="PRECHECK",
        )
        terminated = True
        termination_reason = f"terminated before visible stages because system_status={current_system_status}"
        status = "TERMINATED"
        precheck_decisions.append("TERMINATE scientific_decision=NOT_EVALUATED governance_outcome=DEFER cross_device_status=NOT_REQUIRED")
    else:
        status = "WARN" if precheck_decisions else "PASS"
    append_gate_trace(
        out,
        stage_id="PRECHECK",
        stage_name="GOVERNANCE_PRECHECK",
        inputs_checked=[
            "system_status",
            "governance_self_check.validation_harness_status",
            "governance_self_check.reference_resolution_status",
            "governance_self_check.system_status",
        ],
        decision_or_cap_change="; ".join(precheck_decisions) if precheck_decisions else "NO_CHANGE",
        key_evidence_ids=[],
        status=status,
        notes=termination_reason or "Mirror consistency enforced between top-level and governance self-check system_status.",
    )

    if not terminated:
        if upper_text(out.get("assigned_family_class", "")) in {"", "UNASSESSED"}:
            out, _ = run_family_triage(out)
        baseline_status = upper_text(out.get("baseline_model", {}).get("status", ""))
        if baseline_status == "" and not out.get("residual_analysis", {}):
            out, _ = run_baseline_fit(out)
        if not out.get("mechanism_tests", {}):
            out, _ = run_mechanism_competition(out)
        if not out.get("artifact_tests", {}):
            out, _ = run_artifact_audit(out)

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_5",
            stage_name="BASELINE_PIPELINE_REPRODUCTION",
            inputs_checked=["baseline_model.status", "baseline_model.pipeline_executed"],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage5"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        l0 = baseline_pipeline_executed(out, stage_inputs)
        if l0:
            out["validation_ladder"]["L0_baseline_pipeline_reproduced"] = True
            decision = "SET validation_ladder.L0_baseline_pipeline_reproduced=true"
            stage_status = "PASS"
            notes = "Baseline pipeline trigger satisfied by baseline_model.status or baseline_model.pipeline_executed."
        else:
            decision = "NO_CHANGE"
            stage_status = "NO_CHANGE"
            notes = "No surfaced baseline execution trigger was present."
        append_gate_trace(
            out,
            stage_id="STAGE_5",
            stage_name="BASELINE_PIPELINE_REPRODUCTION",
            inputs_checked=["baseline_model.status", "baseline_model.pipeline_executed"],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage5"),
            status=stage_status,
            notes=notes,
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_6",
            stage_name="BASELINE_SUFFICIENCY_GATE",
            inputs_checked=[
                "validation_ladder.L0_baseline_pipeline_reproduced",
                "residual_analysis.white_residuals",
                "residual_analysis.stationary_residuals",
                "residual_analysis.structured_residuals",
                "residual_analysis.cross_observable_correlations_vanish",
                "residual_analysis.drift_aware_fit_applied",
            ],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage6"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        if baseline_suffices(out, stage_inputs):
            apply_terminal_outcome(
                out,
                scientific_decision="REJECTED_BY_BASELINE_SUFFICIENCY",
                governance_outcome="REJECT",
                cross_device_status="NOT_REQUIRED",
                terminated_at="STAGE_6",
            )
            terminated = True
            termination_reason = "baseline sufficiency trigger satisfied"
            decision = "TERMINATE scientific_decision=REJECTED_BY_BASELINE_SUFFICIENCY governance_outcome=REJECT cross_device_status=NOT_REQUIRED"
            stage_status = "TERMINATED"
            notes = "Residuals were treated as white, stationary, structurally absent, and decorrelated after drift-aware fitting."
        else:
            decision = "NO_CHANGE"
            stage_status = "PASS"
            notes = "Baseline sufficiency trigger not satisfied."
        append_gate_trace(
            out,
            stage_id="STAGE_6",
            stage_name="BASELINE_SUFFICIENCY_GATE",
            inputs_checked=[
                "validation_ladder.L0_baseline_pipeline_reproduced",
                "residual_analysis.white_residuals",
                "residual_analysis.stationary_residuals",
                "residual_analysis.structured_residuals",
                "residual_analysis.cross_observable_correlations_vanish",
                "residual_analysis.drift_aware_fit_applied",
            ],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage6"),
            status=stage_status,
            notes=notes,
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_8",
            stage_name="KNOWN_MECHANISM_COMPETITION",
            inputs_checked=["mechanism_tests.*.explains_data", "mechanism_tests.parsimonious_combination_explains"],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage8"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        if known_mechanism_explains(out, stage_inputs):
            apply_terminal_outcome(
                out,
                scientific_decision="REJECTED_BY_CLASSICAL_MECHANISM_EQUIVALENCE",
                governance_outcome="REJECT",
                cross_device_status="NOT_REQUIRED",
                terminated_at="STAGE_8",
            )
            terminated = True
            termination_reason = "known mechanism trigger satisfied"
            decision = "TERMINATE scientific_decision=REJECTED_BY_CLASSICAL_MECHANISM_EQUIVALENCE governance_outcome=REJECT cross_device_status=NOT_REQUIRED"
            stage_status = "TERMINATED"
            notes = "At least one known mechanism or parsimonious combination was surfaced as explanatory."
        else:
            decision = "NO_CHANGE"
            stage_status = "PASS"
            notes = "No surfaced known-mechanism equivalence trigger was present."
        append_gate_trace(
            out,
            stage_id="STAGE_8",
            stage_name="KNOWN_MECHANISM_COMPETITION",
            inputs_checked=["mechanism_tests.*.explains_data", "mechanism_tests.parsimonious_combination_explains"],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage8"),
            status=stage_status,
            notes=notes,
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_9",
            stage_name="ARTIFACT_EQUIVALENCE_AUDIT",
            inputs_checked=["artifact_tests.route_explains_data", "artifact_tests.explains_data"],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage9"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        if artifact_route_explains(out, stage_inputs):
            apply_terminal_outcome(
                out,
                scientific_decision="REJECTED_BY_ARTIFACT_EQUIVALENCE",
                governance_outcome="REJECT",
                cross_device_status="NOT_REQUIRED",
                terminated_at="STAGE_9",
            )
            terminated = True
            termination_reason = "artifact equivalence trigger satisfied"
            decision = "TERMINATE scientific_decision=REJECTED_BY_ARTIFACT_EQUIVALENCE governance_outcome=REJECT cross_device_status=NOT_REQUIRED"
            stage_status = "TERMINATED"
            notes = "A surfaced artifact route explained the candidate behavior."
        else:
            decision = "NO_CHANGE"
            stage_status = "PASS"
            notes = "No surfaced artifact-equivalence trigger was present."
        append_gate_trace(
            out,
            stage_id="STAGE_9",
            stage_name="ARTIFACT_EQUIVALENCE_AUDIT",
            inputs_checked=["artifact_tests.route_explains_data", "artifact_tests.explains_data"],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage9"),
            status=stage_status,
            notes=notes,
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_10",
            stage_name="CONVERGENCE_AND_REDUCTION_LIMIT_GATE",
            inputs_checked=[
                "hamiltonian_test.convergence_plan_declared",
                "hamiltonian_test.plan_declared_before_nonlinear_sweeps",
                "reduction_limit",
                "baseline_model.reduction_limit_verified",
                "baseline_model.reduction_limit_test_passed",
            ],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage10"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        stage_decisions: List[str] = []
        if convergence_plan_declared(out, stage_inputs):
            out["validation_ladder"]["L2_convergence_plan_defined"] = True
            stage_decisions.append("SET validation_ladder.L2_convergence_plan_defined=true")
        else:
            apply_terminal_outcome(
                out,
                scientific_decision="NOT_EVALUATED",
                governance_outcome="DEFER",
                cross_device_status="NOT_REQUIRED",
                terminated_at="STAGE_10",
            )
            terminated = True
            termination_reason = "convergence plan missing"
            stage_decisions.append("TERMINATE scientific_decision=NOT_EVALUATED governance_outcome=DEFER cross_device_status=NOT_REQUIRED")

        if not terminated:
            if reduction_limit_verified(out, stage_inputs):
                out["validation_ladder"]["L1_reduction_limit_verified"] = True
                stage_decisions.append("SET validation_ladder.L1_reduction_limit_verified=true")
            else:
                apply_terminal_outcome(
                    out,
                    scientific_decision="NOT_EVALUATED",
                    governance_outcome="REJECT",
                    cross_device_status="NOT_REQUIRED",
                    terminated_at="STAGE_10",
                )
                terminated = True
                termination_reason = "reduction limit verification failed"
                stage_decisions.append("TERMINATE scientific_decision=NOT_EVALUATED governance_outcome=REJECT cross_device_status=NOT_REQUIRED")

        append_gate_trace(
            out,
            stage_id="STAGE_10",
            stage_name="CONVERGENCE_AND_REDUCTION_LIMIT_GATE",
            inputs_checked=[
                "hamiltonian_test.convergence_plan_declared",
                "hamiltonian_test.plan_declared_before_nonlinear_sweeps",
                "reduction_limit",
                "baseline_model.reduction_limit_verified",
                "baseline_model.reduction_limit_test_passed",
            ],
            decision_or_cap_change="; ".join(stage_decisions) if stage_decisions else "NO_CHANGE",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage10"),
            status="TERMINATED" if terminated else "PASS",
            notes="Convergence planning is allowed to set L2, but reduction-limit verification is required before continuing.",
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_11",
            stage_name="LINDBLAD_EQUIVALENCE_GATE",
            inputs_checked=["lindblad_equivalence.equivalent_within_resolution", "lindblad_equivalence.best_equivalent_model"],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage11"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        equivalent_override = stage_override(stage_inputs, "stage11", "equivalent_within_resolution")
        if equivalent_override is not MISSING:
            out.setdefault("lindblad_equivalence", {})["equivalent_within_resolution"] = bool_value(equivalent_override)
        best_model_override = stage_override(stage_inputs, "stage11", "best_equivalent_model")
        if best_model_override is not MISSING:
            out.setdefault("lindblad_equivalence", {})["best_equivalent_model"] = str(best_model_override or "")
        out, lindblad_report = run_lindblad_equivalence(out)
        if equivalent_within_resolution(out, stage_inputs):
            apply_terminal_outcome(
                out,
                scientific_decision="REJECTED_BY_LINDBLAD_EQUIVALENCE",
                governance_outcome="REJECT",
                cross_device_status="NOT_REQUIRED",
                terminated_at="STAGE_11",
            )
            terminated = True
            termination_reason = "Lindblad equivalence trigger satisfied"
            decision = "TERMINATE scientific_decision=REJECTED_BY_LINDBLAD_EQUIVALENCE governance_outcome=REJECT cross_device_status=NOT_REQUIRED"
            stage_status = "TERMINATED"
            notes = "The branch was surfaced as equivalent within measurement resolution."
        else:
            decision = "NO_CHANGE"
            stage_status = "PASS"
            notes = "No surfaced Lindblad-equivalence trigger was present."
        append_gate_trace(
            out,
            stage_id="STAGE_11",
            stage_name="LINDBLAD_EQUIVALENCE_GATE",
            inputs_checked=["lindblad_equivalence.equivalent_within_resolution", "lindblad_equivalence.best_equivalent_model"],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage11"),
            status=stage_status,
            notes=f"{notes} M11 module report: {json.dumps(lindblad_report.get('lindblad_equivalence', {}), sort_keys=True)}",
        )

    placeholder_cleared = False
    if not terminated:
        placeholder_cleared = clear_placeholder_governance(out)

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_12",
            stage_name="GOVERNANCE_GUARDRAILS",
            inputs_checked=[
                "calibration_status",
                "identifiability_status",
                "drift_ledger",
                "dataset_governance",
                "promotion_cap_governance",
            ],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage12"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        out, guardrail_report = run_governance_guardrails(out)
        guardrail_notes = list_of_strings(guardrail_report.get("result_summary", {}).get("notes", []))
        hard_guardrail_flags = {
            "CALIBRATION_INVALID_OR_BELOW_THRESHOLD",
            "DATASET_GOVERNANCE_INCOMPLETE",
        }
        if out.get("promotion_cap_governance", "") == "REJECT" or (
            out.get("governance_outcome", "") == "DEFER"
            and hard_guardrail_flags.intersection(set(list_of_strings(out.get("automatic_flags_triggered", []))))
        ):
            apply_terminal_outcome(
                out,
                scientific_decision="NOT_EVALUATED",
                governance_outcome=out.get("governance_outcome", "") or "DEFER",
                cross_device_status="NOT_REQUIRED",
                terminated_at="STAGE_12",
            )
            terminated = True
            termination_reason = "governance guardrail block triggered"
            decision = f"TERMINATE governance_outcome={out.get('governance_outcome', '') or 'DEFER'} via M15 guardrails"
            stage_status = "TERMINATED"
        else:
            decision = "SET typed governance guardrails from M15 module"
            stage_status = "PASS"
            if placeholder_cleared:
                decision = f"{decision}; CLEAR placeholder governance_outcome=DEFER"
        append_gate_trace(
            out,
            stage_id="STAGE_12",
            stage_name="GOVERNANCE_GUARDRAILS",
            inputs_checked=[
                "calibration_status",
                "identifiability_status",
                "drift_ledger",
                "dataset_governance",
                "promotion_cap_governance",
            ],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage12"),
            status=stage_status,
            notes="; ".join(guardrail_notes) if guardrail_notes else "Typed governance guardrails were refreshed from the shared M15 module.",
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_13",
            stage_name="NUMERICAL_STABILITY_GATE",
            inputs_checked=["numerical_stability.stable", "numerical_stability.failed_checks"],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage13"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        if numerical_stability_passed(out, stage_inputs):
            out["validation_ladder"]["L3_numerical_stability_passed"] = True
            decision = "SET validation_ladder.L3_numerical_stability_passed=true"
            stage_status = "PASS"
            notes = "Numerical stability required a surfaced passed state, not planning text."
        else:
            apply_terminal_outcome(
                out,
                scientific_decision="NUMERICALLY_UNSTABLE",
                governance_outcome="DEFER",
                cross_device_status="NOT_REQUIRED",
                terminated_at="STAGE_13",
            )
            terminated = True
            termination_reason = "numerical stability did not pass"
            decision = "TERMINATE scientific_decision=NUMERICALLY_UNSTABLE governance_outcome=DEFER cross_device_status=NOT_REQUIRED"
            stage_status = "TERMINATED"
            notes = "Planning fields alone do not satisfy Stage 13."
        append_gate_trace(
            out,
            stage_id="STAGE_13",
            stage_name="NUMERICAL_STABILITY_GATE",
            inputs_checked=["numerical_stability.stable", "numerical_stability.failed_checks"],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage13"),
            status=stage_status,
            notes=notes,
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_14",
            stage_name="PROVISIONAL_IDENTIFIABILITY_ASSIGNMENT",
            inputs_checked=["scientific_decision", "validation_ladder.L0-L3"],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=[],
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        if out.get("scientific_decision", "") in {"", "NOT_EVALUATED"}:
            out["scientific_decision"] = "PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST"
            decision = "SET scientific_decision=PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST"
            stage_status = "PASS"
            notes = "Visible Stage 14 survival assignment applied after Stages 5-13."
        else:
            decision = "NO_CHANGE"
            stage_status = "NO_CHANGE"
            notes = "Scientific decision was already set before Stage 14."
        append_gate_trace(
            out,
            stage_id="STAGE_14",
            stage_name="PROVISIONAL_IDENTIFIABILITY_ASSIGNMENT",
            inputs_checked=["scientific_decision", "validation_ladder.L0-L3"],
            decision_or_cap_change=decision,
            key_evidence_ids=[],
            status=stage_status,
            notes=notes,
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_15",
            stage_name="INSTRUMENT_FACING_L4_RULE",
            inputs_checked=[
                "exact_falsifier",
                "experiment_schedule.executable_falsifier_package_emitted",
                "experiment_schedule.priority_experiments",
                "instrument_capabilities.instrument_facing_requirement_satisfied",
            ],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage15"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        out, experiment_report = run_experiment_design(out)
        if instrument_facing_path_defined(out, stage_inputs):
            out["validation_ladder"]["L4_instrument_facing_comparison_path_defined"] = True
            decision = "SET validation_ladder.L4_instrument_facing_comparison_path_defined=true"
            stage_status = "PASS"
            notes = "L4 required both an executable falsifier package and at least one surfaced instrument-facing experiment."
        else:
            decision = "NO_CHANGE"
            stage_status = "NO_CHANGE"
            notes = "Planning text alone did not satisfy L4."
        append_gate_trace(
            out,
            stage_id="STAGE_15",
            stage_name="INSTRUMENT_FACING_L4_RULE",
            inputs_checked=[
                "exact_falsifier",
                "experiment_schedule.executable_falsifier_package_emitted",
                "experiment_schedule.priority_experiments",
                "instrument_capabilities.instrument_facing_requirement_satisfied",
            ],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage15"),
            status=stage_status,
            notes=f"{notes} M12 module report: {json.dumps(experiment_report.get('result_summary', {}), sort_keys=True)}",
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_16",
            stage_name="CROSS_DEVICE_GATE",
            inputs_checked=[
                "multi_device_data_available",
                "fabrication_matched_for_geometry_claim",
                "scaling_analysis.geometry_claimed_discriminator",
                "cross_device_validation.status",
                "cross_device_validation.devices_tested",
            ],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage16"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        geometry_override = stage_override(stage_inputs, "stage16", "geometry_claimed_discriminator")
        if geometry_override is not MISSING:
            out.setdefault("scaling_analysis", {})["geometry_claimed_discriminator"] = bool_value(geometry_override)
        signal_override = stage_override(stage_inputs, "stage16", "signal_consistency")
        if signal_override is not MISSING:
            out.setdefault("cross_device_validation", {})["status"] = upper_text(signal_override)
        devices_override = stage_override(stage_inputs, "stage16", "devices_tested")
        if devices_override is not MISSING:
            out.setdefault("cross_device_validation", {})["devices_tested"] = list_of_strings(devices_override)
        prior_cross_device_status = out.get("cross_device_status", "")
        prior_governance_cap = out.get("promotion_cap_governance", "")
        out, cross_device_report = run_cross_device_gate(out)
        if out.get("cross_device_status", "") != prior_cross_device_status and out.get("promotion_cap_governance", "") != prior_governance_cap:
            decision = (
                f"SET cross_device_status={out.get('cross_device_status', '')}; "
                f"FORCE promotion_cap_governance={out.get('promotion_cap_governance', '')}"
            )
        elif out.get("cross_device_status", "") != prior_cross_device_status:
            decision = f"SET cross_device_status={out.get('cross_device_status', '')}"
        else:
            decision = "NO_CHANGE"
        stage_status = "PASS" if out.get("cross_device_status", "") == "CONFIRMED" else "WARN"
        notes = str(cross_device_report.get("result_summary", {}).get("notes", "") or "Cross-device status refreshed from the shared M13 module.")
        append_gate_trace(
            out,
            stage_id="STAGE_16",
            stage_name="CROSS_DEVICE_GATE",
            inputs_checked=[
                "multi_device_data_available",
                "fabrication_matched_for_geometry_claim",
                "scaling_analysis.geometry_claimed_discriminator",
                "cross_device_validation.status",
                "cross_device_validation.devices_tested",
            ],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage16"),
            status=stage_status,
            notes=notes,
        )

    if terminated:
        append_gate_trace(
            out,
            stage_id="STAGE_17",
            stage_name="PROCEED_GATE",
            inputs_checked=[
                "cross_device_status",
                "validation_ladder.L0_baseline_pipeline_reproduced",
                "validation_ladder.L1_reduction_limit_verified",
                "validation_ladder.L2_convergence_plan_defined",
                "validation_ladder.L3_numerical_stability_passed",
                "validation_ladder.L4_instrument_facing_comparison_path_defined",
            ],
            decision_or_cap_change="SKIPPED",
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage17"),
            status="SKIPPED",
            notes=f"Skipped because {termination_reason}.",
        )
    else:
        ladder = out.get("validation_ladder", {})
        raw_proceed = (
            out.get("cross_device_status", "") == "CONFIRMED"
            and all(
                [
                    bool(ladder.get("L0_baseline_pipeline_reproduced", False)),
                    bool(ladder.get("L1_reduction_limit_verified", False)),
                    bool(ladder.get("L2_convergence_plan_defined", False)),
                    bool(ladder.get("L3_numerical_stability_passed", False)),
                    bool(ladder.get("L4_instrument_facing_comparison_path_defined", False)),
                ]
            )
            and out.get("scientific_decision", "") in RAW_PROCEED_DECISION_INPUTS
            and out.get("system_status", "") not in TERMINATING_SYSTEM_STATUSES
        )
        if raw_proceed:
            out["scientific_decision"] = "CROSS_DEVICE_CONFIRMED_IDENTIFIABLE"
            out["governance_outcome"] = "PROCEED"
            decision = "SET scientific_decision=CROSS_DEVICE_CONFIRMED_IDENTIFIABLE; SET governance_outcome=PROCEED"
            stage_status = "PASS"
            notes = "Visible raw proceed conditions passed before clipping."
        else:
            decision = "NO_CHANGE"
            stage_status = "NO_CHANGE"
            notes = "Proceed remained impossible without confirmed cross-device evidence and a complete visible ladder."
        append_gate_trace(
            out,
            stage_id="STAGE_17",
            stage_name="PROCEED_GATE",
            inputs_checked=[
                "cross_device_status",
                "validation_ladder.L0_baseline_pipeline_reproduced",
                "validation_ladder.L1_reduction_limit_verified",
                "validation_ladder.L2_convergence_plan_defined",
                "validation_ladder.L3_numerical_stability_passed",
                "validation_ladder.L4_instrument_facing_comparison_path_defined",
            ],
            decision_or_cap_change=decision,
            key_evidence_ids=stage_evidence_ids(stage_inputs, "stage17"),
            status=stage_status,
            notes=notes,
        )

    out, promotion_report = run_promotion_caps(out)
    clip_decisions = list_of_strings(promotion_report.get("result_summary", {}).get("clip_decisions", []))
    append_gate_trace(
        out,
        stage_id="FINAL_CLIP",
        stage_name="FINAL_CLIPPING_RULE",
        inputs_checked=["governance_outcome", "promotion_cap_governance", "scientific_decision", "promotion_cap_scientific"],
        decision_or_cap_change="; ".join(clip_decisions) if clip_decisions else "NO_CHANGE",
        key_evidence_ids=[],
        status="PASS" if clip_decisions else "NO_CHANGE",
        notes="Visible clipping rules were applied exactly as surfaced in the M05 implementation pack.",
    )

    fallback_decision = str(promotion_report.get("result_summary", {}).get("fallback_decision", "") or "NO_CHANGE")
    append_gate_trace(
        out,
        stage_id="FALLBACK",
        stage_name="FALLBACK_COMPLETION_RULE",
        inputs_checked=["governance_outcome", "scientific_decision"],
        decision_or_cap_change=fallback_decision,
        key_evidence_ids=[],
        status="PASS" if fallback_decision != "NO_CHANGE" else "NO_CHANGE",
        notes="Fallback completion was only applied when governance_outcome remained unset.",
    )

    gsc = out.setdefault("governance_self_check", {})
    gsc["schema_validation_status"] = "PASSED"
    sync_governance_system_status(out)
    validation_result = internal_schema_validate(out, validator_path=validator_path, schema_path=schema_path, mode="final")
    if not validation_result["valid"]:
        gsc["schema_validation_status"] = "FAILED"
        if "SCHEMA_VALIDATION_FAILURE" not in out.get("failure_mode_library_hits", []):
            out.setdefault("failure_mode_library_hits", []).append("SCHEMA_VALIDATION_FAILURE")
        out["governance_outcome"] = "DEFER"
        out["system_status"] = "SCHEMA_VALIDATION_FAILURE"
        gsc["system_status"] = "SCHEMA_VALIDATION_FAILURE"
        append_gate_trace(
            out,
            stage_id="SCHEMA",
            stage_name="POST_RUN_SCHEMA_VALIDATION",
            inputs_checked=["config/schema/candidate_schema.json", "tools/validators/candidate_validator.py final semantics"],
            decision_or_cap_change="SET governance_self_check.schema_validation_status=FAILED; SET system_status=SCHEMA_VALIDATION_FAILURE; SET governance_outcome=DEFER",
            key_evidence_ids=[],
            status="FAIL",
            notes="; ".join(validation_result["errors"]),
        )
    else:
        append_gate_trace(
            out,
            stage_id="SCHEMA",
            stage_name="POST_RUN_SCHEMA_VALIDATION",
            inputs_checked=["config/schema/candidate_schema.json", "tools/validators/candidate_validator.py final semantics"],
            decision_or_cap_change="SET governance_self_check.schema_validation_status=PASSED",
            key_evidence_ids=[],
            status="PASS",
            notes="Post-run final-mode schema validation passed.",
        )

    report = {
        **module_report_header("QDP_V10_6_M05_STAGE_REPORT", "M05"),
        "candidate_id": out.get("candidate_id", ""),
        "branch_or_model_tag": out.get("branch_or_model_tag", ""),
        "terminated_at": out.get("terminated_at", ""),
        "final_state": {
            "scientific_decision": out.get("scientific_decision", ""),
            "governance_outcome": out.get("governance_outcome", ""),
            "cross_device_status": out.get("cross_device_status", ""),
            "promotion_cap_governance": out.get("promotion_cap_governance", ""),
            "promotion_cap_scientific": out.get("promotion_cap_scientific", ""),
            "system_status": out.get("system_status", ""),
            "validation_ladder": out.get("validation_ladder", {}),
        },
        "schema_validation": validation_result,
        "gate_trace_count": len(out.get("gate_trace", [])),
        "stage_inputs_used": stage_inputs,
    }
    return out, report


def selftest_base_candidate(base_template: Dict[str, Any]) -> Dict[str, Any]:
    candidate = make_minimal_final_candidate(base_template)
    candidate["governance_self_check"] = copy.deepcopy(SELFTEST_BASE_PROFILE)
    candidate["system_status"] = "READY"
    candidate["promotion_cap_governance"] = ""
    candidate["promotion_cap_scientific"] = ""
    return candidate


def build_case_candidate(case: Dict[str, Any], base_template: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(case.get("input_candidate_path"), str) and case["input_candidate_path"].strip():
        source = load_json(Path(case["input_candidate_path"]))
        return deep_merge(make_minimal_final_candidate(base_template), source)
    if isinstance(case.get("input_candidate"), dict):
        return deep_merge(selftest_base_candidate(base_template), case["input_candidate"])
    if isinstance(case.get("candidate_overrides"), dict):
        return deep_merge(selftest_base_candidate(base_template), case["candidate_overrides"])
    return selftest_base_candidate(base_template)


def run_selftests(
    cases_path: Path,
    base_template_path: Path,
    validator_path: Path,
    schema_path: Path,
    output_dir: Path,
    write_report_path: Path | None = None,
) -> Dict[str, Any]:
    cases_obj = load_json(cases_path)
    base_template = load_json(base_template_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for case in cases_obj.get("cases", []):
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip() or "UNNAMED_CASE"
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        candidate = build_case_candidate(case, base_template)
        candidate["candidate_id"] = candidate.get("candidate_id", "") or case_id.lower()
        candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or case_id
        stage_inputs = case.get("stage_inputs", {}) if isinstance(case.get("stage_inputs", {}), dict) else {}

        out_candidate, stage_report = run_state_machine(
            candidate,
            stage_inputs,
            schema_path=schema_path,
            validator_path=validator_path,
        )

        candidate_path = case_dir / f"{case_id}_candidate.json"
        report_path = case_dir / f"{case_id}_report.json"
        dump_json(candidate_path, out_candidate)
        dump_json(report_path, stage_report)

        validator_result = validate_candidate_with_existing_validator(
            out_candidate,
            validator_path,
            schema_path,
            case_dir,
            case_id,
        )
        comparison_ok, comparison_failures = compare_expected(out_candidate, stage_report, case.get("expected", {}))
        passed = comparison_ok and validator_result["valid"]
        results.append(
            {
                "case_id": case_id,
                "description": str(case.get("description", "")),
                "passed": passed,
                "comparison_ok": comparison_ok,
                "comparison_failures": comparison_failures,
                "validator_result": validator_result,
                "expected_summary": case.get("expected", {}),
                "actual_summary": {
                    "scientific_decision": out_candidate.get("scientific_decision", ""),
                    "governance_outcome": out_candidate.get("governance_outcome", ""),
                    "cross_device_status": out_candidate.get("cross_device_status", ""),
                    "promotion_cap_governance": out_candidate.get("promotion_cap_governance", ""),
                    "promotion_cap_scientific": out_candidate.get("promotion_cap_scientific", ""),
                    "terminated_at": stage_report.get("terminated_at", ""),
                    "validation_ladder": out_candidate.get("validation_ladder", {}),
                    "system_status": out_candidate.get("system_status", ""),
                },
                "result_summary": {
                    "scientific_decision": out_candidate.get("scientific_decision", ""),
                    "governance_outcome": out_candidate.get("governance_outcome", ""),
                    "cross_device_status": out_candidate.get("cross_device_status", ""),
                    "terminated_at": stage_report.get("terminated_at", ""),
                    "validation_ladder": out_candidate.get("validation_ladder", {}),
                },
                "report_path": str(report_path),
                "output_candidate_path": str(candidate_path),
            }
        )

    report = module_selftest_report_payload(
        "QDP_V10_6_M05_SELFTEST_REPORT",
        "M05",
        results,
        all_passed=all(item.get("passed") for item in results),
        schema_valid_all=all(item.get("validator_result", {}).get("valid", False) for item in results),
    )
    if write_report_path is not None:
        dump_json(write_report_path, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M05 stage machine or its self-tests.")
    parser.add_argument("candidate", nargs="?", type=Path, help="Optional candidate JSON path for a single stage-machine run")
    parser.add_argument("--stage-inputs", type=Path, help="Optional JSON file containing explicit surfaced stage inputs")
    parser.add_argument("--base-template", type=Path, default=DEFAULT_BASE_TEMPLATE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    parser.add_argument("--write-candidate", type=Path)
    parser.add_argument("--write-stage-report", type=Path)
    parser.add_argument("--selftest", action="store_true", help="Run the M05 self-test suite")
    parser.add_argument("--selftest-cases", type=Path, default=DEFAULT_SELFTEST_CASES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SELFTEST_OUTPUT_DIR)
    parser.add_argument("--write-selftest-report", type=Path)
    parser.add_argument("--write-report", type=Path, help="Alias for --write-selftest-report in self-test mode, otherwise writes the single-run stage report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    inferred_selftest = args.candidate is None and args.write_selftest_report is not None
    if args.selftest or inferred_selftest:
        report_path = args.write_selftest_report or args.write_report or DEFAULT_SELFTEST_REPORT
        report = run_selftests(
            cases_path=args.selftest_cases,
            base_template_path=args.base_template,
            validator_path=args.validator,
            schema_path=args.schema,
            output_dir=args.output_dir,
            write_report_path=report_path,
        )
        print(json.dumps(report, indent=2))
        return 0 if report.get("all_passed", False) and report.get("schema_valid_all", False) else 1

    if args.candidate is None:
        print("FATAL: candidate path is required unless --selftest is used.", file=sys.stderr)
        return 2

    base_template = load_json(args.base_template)
    candidate_input = load_json(args.candidate)
    candidate = deep_merge(make_minimal_final_candidate(base_template), candidate_input)
    stage_inputs = load_json(args.stage_inputs) if args.stage_inputs else {}

    out_candidate, report = run_state_machine(
        candidate,
        stage_inputs,
        schema_path=args.schema,
        validator_path=args.validator,
    )

    if args.write_candidate:
        dump_json(args.write_candidate, out_candidate)
    report_output_path = args.write_stage_report or args.write_report
    if report_output_path:
        dump_json(report_output_path, report)

    print(json.dumps(report, indent=2))
    return 0 if report.get("schema_validation", {}).get("valid", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())

