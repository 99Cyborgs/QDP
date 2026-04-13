#!/usr/bin/env python3
"""
QDP v10.6 M12 executable falsifier and experiment-design module.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = REPO_ROOT / "packages" / "qdp_io" / "src"
for path in (REPO_ROOT, QDP_IO_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_io.artifacts import candidate_result_summary_report, dump_json, module_selftest_report_payload, stable_hash, utc_now
from tools.workflow.qdp_runtime.qdp_governance import ensure_governance_structures, list_of_strings
from tools.workflow.qdp_runtime.qdp_paths import BASE_TEMPLATE, CANDIDATE_VALIDATOR, MODULES, SCHEMA
from tools.workflow.qdp_runtime.qdp_validation import validate_candidate_file


MODULE_PATHS = MODULES["m12"]
DEFAULT_BASE_TEMPLATE = BASE_TEMPLATE
DEFAULT_SCHEMA = SCHEMA
DEFAULT_VALIDATOR = CANDIDATE_VALIDATOR
DEFAULT_SELFTEST_CASES = MODULE_PATHS["selftest_cases"]
DEFAULT_SELFTEST_REPORT = MODULE_PATHS["selftest_report"]
DEFAULT_SELFTEST_OUTPUT_DIR = MODULE_PATHS["selftest_output_dir"]
GENERIC_PRIORITY_PREFIXES = (
    "Matched discriminant sweep on ",
    "Control comparison versus ",
)
GENERIC_PRIORITY_LABELS = {
    "Matched control pair",
    "Single-device follow-up",
}
PRUNE_FLAGS = {
    "DUPLICATE_BRANCH_TAG",
    "DUPLICATE_MODEL_TAG",
    "DUPLICATE_SYMBOLIC_H",
    "MISSING_EXACT_FALSIFIER",
    "MISSING_PRIMARY_OBSERVABLE",
    "MISSING_CHANGE_TYPE",
    "MISSING_MODEL_CLASSIFICATION",
    "MORE_THAN_TWO_UNCONSTRAINED_NEW_PARAMETERS",
}
PRUNE_DECISIONS = {
    "REJECTED_BY_BASELINE_SUFFICIENCY",
    "REJECTED_BY_CLASSICAL_MECHANISM_EQUIVALENCE",
    "REJECTED_BY_ARTIFACT_EQUIVALENCE",
}
SIMULATION_ONLY_FEATURES = {
    "CORRELATED_RESIDUALS",
    "NON_GAUSSIAN_RESIDUALS",
    "DRIVE_CONDITIONAL_SHIFTS",
    "RAMSEY_ENVELOPE_MISMATCH",
    "CROSS_OBSERVABLE_CORRELATIONS",
    "NONSTATIONARY_RESIDUALS",
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


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


def upper_text(value: Any) -> str:
    return str(value or "").strip().upper()


def unique_preserve(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def make_minimal_final_candidate(base_template: Dict[str, Any]) -> Dict[str, Any]:
    candidate = copy.deepcopy(base_template)
    candidate["candidate_id"] = candidate.get("candidate_id", "") or "M12_WORKING_PATCH_CANDIDATE"
    candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or "M12_WORKING_PATCH_BRANCH"
    ensure_governance_structures(candidate)
    return candidate


def is_generic_priority(label: str) -> bool:
    text = str(label or "").strip()
    if not text:
        return True
    if text in GENERIC_PRIORITY_LABELS:
        return True
    return any(text.startswith(prefix) for prefix in GENERIC_PRIORITY_PREFIXES)


def has_explicit_priority(priority: List[str]) -> bool:
    return bool(priority) and any(not is_generic_priority(item) for item in priority)


def default_experiments(candidate: Dict[str, Any]) -> List[str]:
    observable = str(candidate.get("primary_observable", "") or candidate.get("secondary_observable", "") or "").strip()
    competitor = str(candidate.get("strongest_competing_mechanism", "") or candidate.get("assigned_family_class", "") or "").strip()
    if not observable:
        return []
    competitor_label = competitor or "the strongest competing explanation"
    return [
        f"Matched discriminant sweep on {observable}",
        f"Control comparison versus {competitor_label}",
    ]


def default_falsifier(candidate: Dict[str, Any]) -> str:
    observable = str(candidate.get("primary_observable", "") or candidate.get("secondary_observable", "") or "").strip()
    competitor = str(candidate.get("strongest_competing_mechanism", "") or candidate.get("assigned_family_class", "") or "").strip()
    if not observable:
        return ""
    competitor_label = competitor or "the strongest competing explanation"
    return f"If the branch is real, the instrument-facing sweep on {observable} must separate it from {competitor_label} under matched controls."


def candidate_devices(candidate: Dict[str, Any]) -> List[str]:
    devices = list_of_strings(candidate.get("candidate_target_devices", []))
    if devices:
        return unique_preserve(devices)
    nested = candidate.get("cross_device_validation", {})
    if isinstance(nested, dict):
        return unique_preserve(list_of_strings(nested.get("devices_tested", [])))
    return []


def prune_reason(candidate: Dict[str, Any]) -> str:
    flags = {upper_text(item) for item in list_of_strings(candidate.get("automatic_flags_triggered", []))}
    registry_status = upper_text(candidate.get("registry_duplicate_status", ""))
    if registry_status in {"DUPLICATE", "DUPLICATE_SYMBOLIC_H"}:
        return "registration_repair_required"
    if flags & PRUNE_FLAGS:
        return "registration_repair_required"
    scientific = upper_text(candidate.get("scientific_decision", ""))
    if scientific in PRUNE_DECISIONS:
        return "baseline_or_equivalence_pruned"
    return ""


def artifact_route(candidate: Dict[str, Any]) -> str:
    tests = candidate.get("artifact_tests", {})
    if not isinstance(tests, dict):
        return ""
    if bool(tests.get("parsimonious_combination_explains", False)):
        label = upper_text(tests.get("parsimonious_combination_label", ""))
        if label:
            return label
    for key in ("strongest_artifact_route", "strongest_artifact_route_initial"):
        label = upper_text(tests.get(key, ""))
        if label:
            return label
    return ""


def mechanism_route(candidate: Dict[str, Any]) -> str:
    tests = candidate.get("mechanism_tests", {})
    if isinstance(tests, dict) and bool(tests.get("parsimonious_combination_explains", False)):
        label = upper_text(tests.get("parsimonious_combination_label", ""))
        if label:
            return label
    for key in ("strongest_competing_mechanism", "strongest_competing_mechanism_initial", "assigned_family_class"):
        label = upper_text(candidate.get(key, ""))
        if label and label not in {"UNASSESSED", "DECLARED_ONLY_PENDING_SIGNATURE_TRIAGE"}:
            return label
    signatures = " ".join(list_of_strings(candidate.get("signature_matches", [])))
    return upper_text(signatures)


def classify_route_group(candidate: Dict[str, Any]) -> str:
    artifact = artifact_route(candidate)
    if artifact:
        if "READOUT" in artifact:
            return "READOUT_ALIAS"
        if "CALIBRATION" in artifact:
            return "CALIBRATION_DRIFT"
        if "POWER" in artifact and "CONTROL_CHAIN" in artifact:
            return "CONTROL_CHAIN_POWER_ALIAS"
        if "POWER" in artifact:
            return "POWER_CALIBRATION_ALIAS"
        if "REFRIGERATOR" in artifact or "FRIDGE" in artifact:
            return "REFRIGERATOR_CYCLE_ALIAS"
        if "CONTROL_CHAIN" in artifact:
            return "CONTROL_CHAIN_DISTORTION"

    minimal = upper_text(candidate.get("minimal_discriminant_measurement", ""))
    combined = " ".join(
        [
            artifact,
            mechanism_route(candidate),
            minimal,
            upper_text(candidate.get("branch_or_model_tag", "")),
            upper_text(candidate.get("candidate_id", "")),
            upper_text(" ".join(list_of_strings(candidate.get("evaluation_notes", [])))),
        ]
    )
    if "VORTEX_QUASIPARTICLE" in combined:
        return "VORTEX_QUASIPARTICLE"
    if any(token in combined for token in ["HYSTERESIS", "VORTEX", "BCOOL", "PINNED", "METASTABLE", "IMPEDANCE_RATIO", "FIELD LOOP"]):
        return "VORTEX"
    if any(token in combined for token in ["TLS", "SATURATION", "DIELECTRIC", "PARTICIPATION", "NOT_VORTEX_DOMINATED"]):
        return "TLS"
    if any(token in combined for token in ["QUASIPARTICLE", "GLOBAL_BATH", "PARITY SWITCHING", "SUDDEN_T1_COLLAPSES"]):
        return "QUASIPARTICLE"
    if any(token in combined for token in ["PHONON", "FINITE_SIZE", "KERNEL_MEMORY", "REVIVALS", "BACKFLOW", "NON_EXPONENTIAL"]):
        return "PHONON"
    if any(token in combined for token in ["EM_PURCELL", "PARASITIC", "AVOIDED_CROSSING", "COHERENT_PARASITIC_MODE"]):
        return "EM_PURCELL"
    if any(token in combined for token in ["CONTROL_NOISE", "NARROWBAND_NOISE_PSD", "FILTER-FUNCTION", "LINE ATTENUATION"]):
        return "CONTROL_NOISE"
    return ""


def is_equivalence_candidate(candidate: Dict[str, Any]) -> bool:
    labels = " ".join(
        [
            upper_text(candidate.get("candidate_id", "")),
            upper_text(candidate.get("branch_or_model_tag", "")),
            upper_text(candidate.get("best_equivalent_model", "")),
            upper_text(" ".join(list_of_strings(candidate.get("evaluation_notes", [])))),
        ]
    )
    return "M11" in labels or "EQUIVALENT" in labels or "LINDBLAD" in labels


def residual_features(candidate: Dict[str, Any]) -> List[str]:
    residuals = candidate.get("residual_analysis", {})
    if not isinstance(residuals, dict):
        return []
    return [upper_text(item) for item in list_of_strings(residuals.get("features", []))]


def needs_residual_simulation(candidate: Dict[str, Any]) -> bool:
    residuals = candidate.get("residual_analysis", {})
    if not isinstance(residuals, dict):
        return False
    if bool(residuals.get("structured_residuals", False)):
        return True
    return bool(set(residual_features(candidate)) & SIMULATION_ONLY_FEATURES)


def is_cross_device_candidate(candidate: Dict[str, Any]) -> bool:
    cross = upper_text(candidate.get("cross_device_status", ""))
    if cross in {"DEVICE_SPECIFIC", "INCONSISTENT", "CONFIRMED", "CONFUNDED"}:
        return True
    if cross == "SCHEDULED":
        if candidate_devices(candidate):
            return True
        science = upper_text(candidate.get("scientific_decision", ""))
        if science == "PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST":
            return True
    exact_falsifier = upper_text(candidate.get("exact_falsifier", ""))
    return "CROSS-DEVICE" in exact_falsifier or "MATCHED-FABRICATION" in exact_falsifier


def branch_partition(candidate: Dict[str, Any]) -> str:
    if prune_reason(candidate):
        return "baseline_prune"
    if artifact_route(candidate):
        return "artifact_elimination"
    if is_cross_device_candidate(candidate):
        return "cross_device_confirmation"
    if is_equivalence_candidate(candidate) or needs_residual_simulation(candidate):
        return "mechanism_discrimination"
    if mechanism_route(candidate):
        return "mechanism_discrimination"
    if str(candidate.get("minimal_discriminant_measurement", "") or "").strip():
        return "mechanism_discrimination"
    return "baseline_prune"


def route_priority(route_group: str) -> List[str]:
    if route_group == "VORTEX":
        return [
            "Vortex discriminant sweep: ZFC vs FC, field loops, cooldown field, matched width or thickness, delta fr over delta 1/Qi"
        ]
    if route_group == "TLS":
        return [
            "TLS saturation sweep: readout power x temperature x geometry or participation"
        ]
    if route_group == "QUASIPARTICLE":
        return [
            "Quasiparticle burst sweep: parity switching, synchronized multi-device T1, shielding or injection controls"
        ]
    if route_group == "PHONON":
        return [
            "Structured-bath sweep: high-SNR decay, filter-function spacing, packaging or phononic perturbation"
        ]
    if route_group == "EM_PURCELL":
        return [
            "Parasitic-mode sweep: high-resolution bias spectroscopy and package-mode perturbation"
        ]
    if route_group == "CONTROL_NOISE":
        return [
            "Control-chain noise sweep: line attenuation, filter swap, pulse-shape perturbation, filter-function spectroscopy"
        ]
    if route_group == "READOUT_ALIAS":
        return [
            "Readout alias sweep: readout power or gain, digitizer linearity, relinearized fit"
        ]
    if route_group == "CALIBRATION_DRIFT":
        return [
            "Calibration drift sweep: interleaved recalibration and drift-ledger replay"
        ]
    if route_group == "POWER_CALIBRATION_ALIAS":
        return [
            "Power calibration sweep: in-situ device power and checked attenuation map"
        ]
    if route_group == "REFRIGERATOR_CYCLE_ALIAS":
        return [
            "Refrigerator-cycle sweep: phase-binned hold-time and cryocooler synchronization"
        ]
    if route_group == "CONTROL_CHAIN_DISTORTION":
        return [
            "Control-chain distortion sweep: attenuation or filter swap plus pulse-shape perturbation"
        ]
    if route_group == "CONTROL_CHAIN_POWER_ALIAS":
        return [
            "Artifact combination sweep: control-chain perturbation plus in-situ power recalibration"
        ]
    if route_group == "VORTEX_QUASIPARTICLE":
        return [
            "Vortex or quasiparticle interplay sweep: cooldown-field history, parity switching, synchronized multi-device T1"
        ]
    return []


def route_falsifier(route_group: str, candidate: Dict[str, Any]) -> str:
    if route_group == "VORTEX":
        return "If the vortex branch is real, ZFC vs FC, field-loop history, and matched width or thickness sweeps must preserve the delta fr over delta 1/Qi ordering across cooldowns."
    if route_group == "TLS":
        return "If the TLS branch is real, readout-power and temperature sweeps must reproduce the saturation trend across matched geometry or participation changes."
    if route_group == "QUASIPARTICLE":
        return "If the quasiparticle branch is real, parity-switch and synchronized multi-device burst measurements must track shielding or injection controls."
    if route_group == "PHONON":
        return "If the structured-bath branch is real, high-SNR decay and filter-function sweeps must preserve the revival or backflow structure across packaging or phononic perturbations."
    if route_group == "EM_PURCELL":
        return "If the parasitic-mode branch is real, high-resolution bias spectroscopy must preserve the anticrossing or mode-tracking signature under package perturbation."
    if route_group == "CONTROL_NOISE":
        return "If the control-noise branch is real, line-attenuation, filter, and pulse-shape sweeps must move the inferred noise peak with the control chain."
    if route_group == "READOUT_ALIAS":
        return "If the readout-alias branch is real, readout-power and gain sweeps plus a relinearized fit must remove the anomaly."
    if route_group == "CALIBRATION_DRIFT":
        return "If the calibration-drift branch is real, interleaved recalibration and drift-ledger replay must remove the apparent anomaly."
    if route_group == "POWER_CALIBRATION_ALIAS":
        return "If the power-calibration alias branch is real, in-situ device-power calibration must remove the amplitude dependence across the checked attenuation map."
    if route_group == "REFRIGERATOR_CYCLE_ALIAS":
        return "If the refrigerator-cycle alias branch is real, phase-binned hold-time sweeps must move the anomaly with the cryocooler cycle."
    if route_group == "CONTROL_CHAIN_DISTORTION":
        return "If the control-chain distortion branch is real, attenuation, filter, and pulse-shape sweeps must move the anomaly with the microwave chain."
    if route_group == "CONTROL_CHAIN_POWER_ALIAS":
        return "If the combined control-chain and power-calibration artifact branch is real, control-chain perturbations plus in-situ power recalibration must remove the anomaly."
    if route_group == "VORTEX_QUASIPARTICLE":
        return "If the vortex-quasiparticle interplay branch is real, cooldown-field history and parity-switch measurements must preserve the suppression ordering across matched devices."
    return default_falsifier(candidate)


def route_simulation_conditions(route_group: str, partition: str) -> Dict[str, Any]:
    if route_group in {
        "VORTEX",
        "TLS",
        "QUASIPARTICLE",
        "PHONON",
        "EM_PURCELL",
        "CONTROL_NOISE",
        "READOUT_ALIAS",
        "CALIBRATION_DRIFT",
        "POWER_CALIBRATION_ALIAS",
        "REFRIGERATOR_CYCLE_ALIAS",
        "CONTROL_CHAIN_DISTORTION",
        "CONTROL_CHAIN_POWER_ALIAS",
        "VORTEX_QUASIPARTICLE",
    }:
        return {
            "branch_partition": partition,
            "owner_route": route_group,
            "status": "PROPOSED",
            "simulation_sweep_required": True,
            "lab_sweep_required": True,
        }
    return {}


def route_parameter_ranges(route_group: str) -> Dict[str, Any]:
    if route_group == "VORTEX":
        return {
            "field_history_tag": ["ZFC", "FC", "UP_LOOP", "DOWN_LOOP"],
            "field_magnitude": ["LOW", "MID", "HIGH"],
            "geometry": ["MATCHED_WIDTH_A", "MATCHED_WIDTH_B"],
            "drive_amplitude": ["LOW", "MID", "HIGH"],
            "temperature": ["BASE", "MID", "HIGH"],
        }
    if route_group == "TLS":
        return {
            "readout_power": ["LOW", "MID", "HIGH"],
            "temperature": ["BASE", "MID", "HIGH"],
            "geometry_or_participation": ["LOW", "MID", "HIGH"],
            "saturation_parameters": ["LOW", "MID", "HIGH"],
        }
    if route_group == "QUASIPARTICLE":
        return {
            "burst_rate": ["LOW", "MID", "HIGH"],
            "correlation_window": ["SHORT", "MEDIUM", "LONG"],
            "cross_device_coupling": ["WEAK", "MEDIUM", "STRONG"],
            "shielding_or_injection": ["BASELINE", "PERTURBED"],
        }
    if route_group == "PHONON":
        return {
            "memory_timescale": ["SHORT", "MEDIUM", "LONG"],
            "spectral_peak": ["LOW", "MID", "HIGH"],
            "linewidth": ["NARROW", "MEDIUM", "BROAD"],
            "packaging_or_phononic_toggle": ["OFF", "ON"],
        }
    if route_group == "EM_PURCELL":
        return {
            "mode_frequency": ["LOW", "MID", "HIGH"],
            "mode_coupling": ["WEAK", "MEDIUM", "STRONG"],
            "bias_or_flux": ["LOW", "MID", "HIGH"],
        }
    if route_group == "CONTROL_NOISE":
        return {
            "noise_peak_frequency": ["LOW", "MID", "HIGH"],
            "attenuation_profile": ["LIGHT", "NOMINAL", "HEAVY"],
            "pulse_shape": ["BASELINE", "PERTURBED"],
        }
    if route_group == "READOUT_ALIAS":
        return {
            "readout_power": ["LOW", "MID", "HIGH"],
            "readout_gain": ["LOW", "MID", "HIGH"],
            "digitizer_linearity_model": ["BASELINE", "RELINEARIZED"],
        }
    if route_group == "CALIBRATION_DRIFT":
        return {
            "recalibration_interval": ["SHORT", "MEDIUM", "LONG"],
            "drift_model_toggle": ["OFF", "ON"],
        }
    if route_group == "POWER_CALIBRATION_ALIAS":
        return {
            "device_power_model": ["GENERATOR_SETTING", "IN_SITU_CALIBRATED"],
            "attenuation_map": ["BASELINE", "CHECKED"],
        }
    if route_group == "REFRIGERATOR_CYCLE_ALIAS":
        return {
            "hold_time": ["SHORT", "MEDIUM", "LONG"],
            "cryocooler_phase_bin": ["0", "90", "180", "270"],
        }
    if route_group == "CONTROL_CHAIN_DISTORTION":
        return {
            "attenuation_profile": ["LIGHT", "NOMINAL", "HEAVY"],
            "filter_profile": ["BASELINE", "ALT_FILTER"],
            "pulse_shape": ["BASELINE", "PERTURBED"],
        }
    if route_group == "CONTROL_CHAIN_POWER_ALIAS":
        return {
            "attenuation_profile": ["LIGHT", "NOMINAL", "HEAVY"],
            "pulse_shape": ["BASELINE", "PERTURBED"],
            "device_power_model": ["GENERATOR_SETTING", "IN_SITU_CALIBRATED"],
        }
    if route_group == "VORTEX_QUASIPARTICLE":
        return {
            "field_history_tag": ["ZFC", "FC"],
            "burst_rate": ["LOW", "MID", "HIGH"],
            "cross_device_coupling": ["WEAK", "MEDIUM", "STRONG"],
            "shielding_or_injection": ["BASELINE", "PERTURBED"],
        }
    return {}


def residual_simulation_plan(candidate: Dict[str, Any], partition: str) -> Dict[str, Any]:
    return {
        "partition": partition,
        "route_group": "RESIDUAL_SIMULATION",
        "priority_experiments": [],
        "exact_falsifier": "If the residual branch is real, the structured residual features must persist across drift-aware baseline and numerical perturbation sweeps.",
        "simulation_conditions": {
            "branch_partition": partition,
            "owner_route": "RESIDUAL_SIMULATION",
            "status": "PROPOSED",
            "simulation_sweep_required": True,
            "lab_sweep_required": False,
            "residual_features": unique_preserve(residual_features(candidate)),
        },
        "tested_parameter_ranges": {
            "drift_model_toggle": ["OFF", "ON"],
            "nonstationarity_window": ["SHORT", "MEDIUM", "LONG"],
            "drive_condition": ["BASELINE", "PERTURBED"],
            "equivalence_resolution": ["COARSE", "MEDIUM", "FINE"],
        },
    }


def equivalence_plan(partition: str) -> Dict[str, Any]:
    return {
        "partition": partition,
        "route_group": "COMPUTATIONAL_EQUIVALENCE",
        "priority_experiments": [],
        "exact_falsifier": "If the non-equivalent branch is real, the separation from the best equivalent model must persist across timestep, truncation, solver, and resolution sweeps.",
        "simulation_conditions": {
            "branch_partition": partition,
            "owner_route": "COMPUTATIONAL_EQUIVALENCE",
            "status": "PROPOSED",
            "simulation_sweep_required": True,
            "lab_sweep_required": False,
        },
        "tested_parameter_ranges": {
            "timestep": ["COARSE", "MEDIUM", "FINE"],
            "truncation": ["LOW", "MID", "HIGH"],
            "solver": ["BASELINE", "ALT_SOLVER"],
            "resolution": ["COARSE", "MEDIUM", "FINE"],
        },
    }


def cross_device_plan(candidate: Dict[str, Any], partition: str) -> Dict[str, Any]:
    exact_falsifier = str(candidate.get("exact_falsifier", "") or "").strip()
    matched = bool(candidate.get("fabrication_matched_for_geometry_claim", False))
    nested = candidate.get("cross_device_validation", {})
    if isinstance(nested, dict):
        matched = matched or bool(nested.get("fabrication_matched", False))
    label = "Cross-device matched-fabrication sweep" if matched or "MATCHED-FABRICATION" in upper_text(exact_falsifier) else "Cross-device discriminant sweep"
    if not exact_falsifier:
        if "matched-fabrication" in label.lower():
            exact_falsifier = "If the branch is real, the matched-fabrication cross-device sweep must preserve the discriminant ordering."
        else:
            exact_falsifier = "If the branch is real, the cross-device discriminant sweep must preserve the observed ordering under matched controls."
    return {
        "partition": partition,
        "route_group": "CROSS_DEVICE_CONFIRMATION",
        "priority_experiments": [label],
        "exact_falsifier": exact_falsifier,
        "simulation_conditions": {},
        "tested_parameter_ranges": {},
    }


def generic_family_plan(candidate: Dict[str, Any], partition: str) -> Dict[str, Any]:
    minimal = str(candidate.get("minimal_discriminant_measurement", "") or "").strip()
    return {
        "partition": partition,
        "route_group": "GENERIC_FAMILY",
        "priority_experiments": [minimal] if minimal else [],
        "exact_falsifier": default_falsifier(candidate),
        "simulation_conditions": {},
        "tested_parameter_ranges": {},
    }


def route_plan(candidate: Dict[str, Any]) -> Dict[str, Any]:
    partition = branch_partition(candidate)
    reason = prune_reason(candidate)
    if reason:
        return {
            "partition": partition,
            "route_group": "NO_NEW_SWEEP",
            "priority_experiments": [],
            "exact_falsifier": str(candidate.get("exact_falsifier", "") or ""),
            "simulation_conditions": {},
            "tested_parameter_ranges": {},
            "suppression_reason": reason,
        }
    if is_equivalence_candidate(candidate):
        return equivalence_plan(partition)
    if needs_residual_simulation(candidate) and not artifact_route(candidate) and not mechanism_route(candidate):
        return residual_simulation_plan(candidate, partition)
    route_group = classify_route_group(candidate)
    if route_group:
        return {
            "partition": partition,
            "route_group": route_group,
            "priority_experiments": route_priority(route_group),
            "exact_falsifier": route_falsifier(route_group, candidate),
            "simulation_conditions": route_simulation_conditions(route_group, partition),
            "tested_parameter_ranges": route_parameter_ranges(route_group),
        }
    if is_cross_device_candidate(candidate):
        return cross_device_plan(candidate, partition)
    return generic_family_plan(candidate, partition)


def run_experiment_design(candidate: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    out = copy.deepcopy(candidate)
    ensure_governance_structures(out)
    schedule = out.setdefault("experiment_schedule", {})
    tests = out.setdefault("hamiltonian_test", {})
    instrument = out.setdefault("instrument_capabilities", {})
    plan = route_plan(out)

    out["candidate_target_devices"] = candidate_devices(out)
    schedule["branch_partition"] = plan.get("partition", "")
    schedule["sweep_route_group"] = plan.get("route_group", "")

    if not str(out.get("exact_falsifier", "") or "").strip():
        out["exact_falsifier"] = str(plan.get("exact_falsifier", "") or "").strip()
        if not out["exact_falsifier"]:
            out["exact_falsifier"] = default_falsifier(out)

    priority = list_of_strings(schedule.get("priority_experiments", []))
    if not has_explicit_priority(priority):
        proposed_priority = list_of_strings(plan.get("priority_experiments", []))
        if not proposed_priority and not priority:
            proposed_priority = default_experiments(out)
        priority = proposed_priority or priority
    schedule["priority_experiments"] = priority

    proposed_simulation_conditions = plan.get("simulation_conditions", {})
    if isinstance(proposed_simulation_conditions, dict) and proposed_simulation_conditions:
        existing_conditions = out.get("simulation_conditions", {})
        if not isinstance(existing_conditions, dict):
            existing_conditions = {}
        out["simulation_conditions"] = deep_merge(proposed_simulation_conditions, existing_conditions)

    proposed_parameter_ranges = plan.get("tested_parameter_ranges", {})
    if isinstance(proposed_parameter_ranges, dict) and proposed_parameter_ranges:
        existing_ranges = out.get("tested_parameter_ranges", {})
        if not isinstance(existing_ranges, dict):
            existing_ranges = {}
        out["tested_parameter_ranges"] = deep_merge(proposed_parameter_ranges, existing_ranges)

    templates = list_of_strings(schedule.get("default_templates_triggered", []))
    if priority and "ORTHOGONAL_DISCRIMINANT_SWEEP" not in templates:
        templates.append("ORTHOGONAL_DISCRIMINANT_SWEEP")
    schedule["default_templates_triggered"] = templates

    capability_ok = bool(instrument.get("instrument_facing_requirement_satisfied", False))
    if not capability_ok and (priority or str(out.get("accessible_platform_or_device_class", "")).strip()):
        capability_ok = True
        instrument["instrument_facing_requirement_satisfied"] = True

    package_emitted = bool(out.get("exact_falsifier", "")) and bool(priority) and capability_ok
    schedule["executable_falsifier_package_emitted"] = package_emitted
    tests["experiment_design_law_satisfied"] = package_emitted
    tests["instrument_facing_requirement_satisfied"] = capability_ok

    outputs = list_of_strings(out.get("requested_output_artifacts", []))
    if package_emitted and "EXECUTABLE_FALSIFIER_PACKAGE" not in outputs:
        outputs.append("EXECUTABLE_FALSIFIER_PACKAGE")
    out["requested_output_artifacts"] = outputs

    diagnostics = candidate_result_summary_report(
        "QDP_V10_6_M12_REPORT",
        "M12",
        out.get("candidate_id", ""),
        {
            "exact_falsifier": out.get("exact_falsifier", ""),
            "priority_experiments": schedule.get("priority_experiments", []),
            "default_templates_triggered": schedule.get("default_templates_triggered", []),
            "executable_falsifier_package_emitted": schedule.get("executable_falsifier_package_emitted", False),
            "instrument_facing_requirement_satisfied": instrument.get("instrument_facing_requirement_satisfied", False),
            "branch_partition": schedule.get("branch_partition", ""),
            "sweep_route_group": schedule.get("sweep_route_group", ""),
            "candidate_target_devices": out.get("candidate_target_devices", []),
            "simulation_conditions": out.get("simulation_conditions", {}),
            "tested_parameter_ranges": out.get("tested_parameter_ranges", {}),
            "suppression_reason": plan.get("suppression_reason", ""),
        },
    )
    return out, diagnostics


def attach_materialization_provenance(
    report: Dict[str, Any],
    *,
    source_candidate_path: Path,
    source_candidate: Dict[str, Any],
    output_candidate_path: Path,
    output_candidate: Dict[str, Any],
) -> Dict[str, Any]:
    out = copy.deepcopy(report)
    out["source_candidate_path"] = str(source_candidate_path.resolve())
    out["source_candidate_hash"] = stable_hash(source_candidate)
    out["output_candidate_path"] = str(output_candidate_path.resolve())
    out["output_candidate_hash"] = stable_hash(output_candidate)
    return out


def summarize_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    schedule = candidate.get("experiment_schedule", {})
    return {
        "exact_falsifier": candidate.get("exact_falsifier", ""),
        "experiment_schedule": {
            "priority_experiments": schedule.get("priority_experiments", []),
            "default_templates_triggered": schedule.get("default_templates_triggered", []),
            "executable_falsifier_package_emitted": schedule.get("executable_falsifier_package_emitted", False),
            "branch_partition": schedule.get("branch_partition", ""),
            "sweep_route_group": schedule.get("sweep_route_group", ""),
        },
        "instrument_capabilities": {
            "instrument_facing_requirement_satisfied": candidate.get("instrument_capabilities", {}).get(
                "instrument_facing_requirement_satisfied",
                False,
            )
        },
        "requested_output_artifacts": candidate.get("requested_output_artifacts", []),
        "candidate_target_devices": candidate.get("candidate_target_devices", []),
        "simulation_conditions": candidate.get("simulation_conditions", {}),
        "tested_parameter_ranges": candidate.get("tested_parameter_ranges", {}),
    }


def compare_expected(actual: Any, expected: Any, path: str = "$") -> List[str]:
    failures: List[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, found {type(actual).__name__}"]
        for key, value in expected.items():
            next_path = f"{path}.{key}"
            if key not in actual:
                failures.append(f"{next_path}: missing")
                continue
            failures.extend(compare_expected(actual[key], value, next_path))
        return failures
    if isinstance(expected, list):
        if actual != expected:
            failures.append(f"{path}: expected {expected!r}, found {actual!r}")
        return failures
    if actual != expected:
        failures.append(f"{path}: expected {expected!r}, found {actual!r}")
    return failures


def run_selftests(
    cases_path: Path,
    base_template_path: Path,
    validator_path: Path,
    schema_path: Path,
    output_dir: Path,
    write_report_path: Path,
) -> Dict[str, Any]:
    cases_obj = load_json(cases_path)
    base_template = load_json(base_template_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []

    for case in cases_obj.get("cases", []):
        case_id = str(case.get("case_id", ""))
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        candidate = deep_merge(make_minimal_final_candidate(base_template), case.get("candidate_overrides", {}))
        candidate, report = run_experiment_design(candidate)
        candidate_path = case_dir / f"{case_id}_candidate.json"
        report_path = case_dir / f"{case_id}_report.json"
        dump_json(candidate_path, candidate)
        dump_json(report_path, report)
        validator_result = validate_candidate_file(candidate_path, validator_path, schema_path, mode="final")
        actual_summary = summarize_candidate(candidate)
        expected_summary = case.get("expected", {})
        comparison_failures = compare_expected(actual_summary, expected_summary)
        comparison_ok = not comparison_failures
        passed = comparison_ok and validator_result["valid"]
        results.append(
            {
                "case_id": case_id,
                "description": case.get("description", ""),
                "passed": passed,
                "comparison_ok": comparison_ok,
                "comparison_failures": comparison_failures,
                "validator_result": validator_result,
                "expected_summary": expected_summary,
                "actual_summary": actual_summary,
                "report_path": str(report_path),
                "output_candidate_path": str(candidate_path),
            }
        )

    cases_total = len(results)
    cases_passed = sum(1 for result in results if result["passed"])
    report = module_selftest_report_payload(
        "QDP_V10_6_M12_SELFTEST_REPORT",
        "M12",
        results,
        visible_source_only=True,
        all_passed=cases_total > 0 and cases_passed == cases_total,
        schema_valid_all=all(result["validator_result"]["valid"] for result in results),
    )
    dump_json(write_report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M12 executable falsifier and experiment-design module.")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--write-report", type=Path, default=DEFAULT_SELFTEST_REPORT)
    parser.add_argument("--base-template", type=Path, default=DEFAULT_BASE_TEMPLATE)
    parser.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--selftest-cases", type=Path, default=DEFAULT_SELFTEST_CASES)
    parser.add_argument("--selftest-output-dir", type=Path, default=DEFAULT_SELFTEST_OUTPUT_DIR)
    args = parser.parse_args()

    if args.selftest:
        report = run_selftests(args.selftest_cases, args.base_template, args.validator, args.schema, args.selftest_output_dir, args.write_report)
        print(json.dumps(report, indent=2))
        return 0

    if not args.candidate:
        raise SystemExit("M12 run requires --candidate unless --selftest is set.")

    candidate_path = args.candidate.resolve()
    candidate = load_json(candidate_path)
    output_path = args.output.resolve() if args.output else candidate_path
    out_candidate, report = run_experiment_design(candidate)
    report = attach_materialization_provenance(
        report,
        source_candidate_path=candidate_path,
        source_candidate=candidate,
        output_candidate_path=output_path,
        output_candidate=out_candidate,
    )
    if args.output:
        dump_json(output_path, out_candidate)
    else:
        print(json.dumps(out_candidate, indent=2))
    if args.write_report:
        dump_json(args.write_report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
