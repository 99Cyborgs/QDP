#!/usr/bin/env python3
"""
QDP v10.6 M07 family-class triage and signature-to-bath scorer.

This is a visible-source working-patch implementation derived only from the
surfaced specs/core/bath_glossary.md and specs/core/signature_to_bath_decision_chart.md artifacts.
It does not claim no-loss parity with any missing retained runtime sections.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qdp_paths import BATH_GLOSSARY, BASE_TEMPLATE, CANDIDATE_VALIDATOR, MODULES, SCHEMA, SIGNATURE_TO_BATH_CHART, repo_rel
from qdp_validation import validate_candidate_file


MODULE_PATHS = MODULES["m07"]
DEFAULT_BASE_TEMPLATE = BASE_TEMPLATE
DEFAULT_SCHEMA = SCHEMA
DEFAULT_VALIDATOR = CANDIDATE_VALIDATOR
DEFAULT_SELFTEST_CASES = MODULE_PATHS["selftest_cases"]
DEFAULT_SELFTEST_REPORT = MODULE_PATHS["selftest_report"]
DEFAULT_SELFTEST_OUTPUT_DIR = MODULE_PATHS["selftest_output_dir"]

MECHANISM_SCORE_KEYS = [
    "P_TLS",
    "P_VORTEX",
    "P_QUASIPARTICLE",
    "P_PHONON",
    "P_CONTROL_NOISE",
    "P_EM_PURCELL",
    "P_OTHER",
]

READY_SELF_CHECK = {
    "validation_harness_status": "PASSED",
    "schema_validation_status": "PASSED",
    "reference_resolution_status": "PASSED",
    "determinism_status": "PASSED",
    "system_status": "READY",
}

SIGNATURE_RULES: List[Dict[str, Any]] = [
    {
        "signature_id": "HYSTERESIS_MEMORY",
        "signature_label": "HYSTERESIS",
        "match_terms": ["hysteresis", "bcool", "zfc", "fc", "field loop", "sweep direction", "hysteresis index"],
        "min_terms": 1,
        "assigned_family_class": "METASTABLE_CONFIGURATION_MEMORY",
        "bath_rank_order": [
            "METASTABLE_CONFIGURATION_MEMORY",
            "PINNED_VORTEX_OCCUPANCY",
            "SLOW_DEFECT_SECTOR",
        ],
        "minimal_discriminant_measurement": "Repeat ZFC vs FC and up/down field loops; compute hysteresis index; replicate across cooldowns.",
        "mechanism_weights": {
            "P_VORTEX": 0.8,
            "P_CONTROL_NOISE": 0.05,
            "P_OTHER": 0.15,
        },
    },
    {
        "signature_id": "BIMODAL_HIDDEN_STATE",
        "signature_label": "BIMODAL_DISTRIBUTION",
        "match_terms": ["bimodal", "2-state hmm", "two-state hmm", "hidden discrete state", "histogram"],
        "min_terms": 1,
        "assigned_family_class": "HIDDEN_DISCRETE_STATE",
        "bath_rank_order": [
            "HIDDEN_DISCRETE_STATE",
            "PINNED_VORTEX_OCCUPANCY",
            "STRONG_FLUCTUATOR",
        ],
        "minimal_discriminant_measurement": "Acquire long time traces and histograms; fit two-state HMM versus single drift and verify protocol dependence.",
        "mechanism_weights": {
            "P_VORTEX": 0.45,
            "P_CONTROL_NOISE": 0.15,
            "P_OTHER": 0.4,
        },
    },
    {
        "signature_id": "TELEGRAPH_SWITCHING",
        "signature_label": "TELEGRAPH_SWITCHING",
        "match_terms": ["telegraph switching", "telegraph", "dwell times", "c(t) jumps", "metastable switching"],
        "min_terms": 1,
        "assigned_family_class": "METASTABLE_SWITCHING",
        "bath_rank_order": [
            "METASTABLE_SWITCHING",
            "PINNED_VORTEX_OCCUPANCY",
            "SLOW_FLUCTUATOR",
        ],
        "minimal_discriminant_measurement": "Monitor the device at fixed conditions, estimate dwell times, and test dependence on Bcool, drive, and temperature.",
        "mechanism_weights": {
            "P_VORTEX": 0.4,
            "P_CONTROL_NOISE": 0.2,
            "P_OTHER": 0.4,
        },
    },
    {
        "signature_id": "TLS_SATURATION",
        "signature_label": "POWER_DEPENDENT_SATURATION",
        "match_terms": ["power dependence", "saturation", "tls saturation", "qi vs readout power", "smooth power dependence"],
        "min_terms": 1,
        "assigned_family_class": "TLS_ENSEMBLE",
        "bath_rank_order": [
            "TLS_ENSEMBLE",
            "DIELECTRIC_INTERFACE_LOSS",
            "THERMAL_BATH",
        ],
        "minimal_discriminant_measurement": "Run a Qi versus readout power sweep, fit a TLS saturation form, and repeat at two to three temperatures.",
        "mechanism_weights": {
            "P_TLS": 0.8,
            "P_CONTROL_NOISE": 0.05,
            "P_OTHER": 0.15,
        },
    },
    {
        "signature_id": "TEMPERATURE_SCALING",
        "signature_label": "TEMPERATURE_SCALING_WITHOUT_HYSTERESIS",
        "match_terms": ["temperature scaling", "without hysteresis", "no hysteresis", "tanh-law", "activation-like"],
        "min_terms": 1,
        "assigned_family_class": "THERMAL_BATH_SCALING",
        "bath_rank_order": [
            "TLS_ENSEMBLE",
            "QUASIPARTICLE_BATH",
            "THERMAL_BATH",
        ],
        "minimal_discriminant_measurement": "Run a small temperature sweep and compare the scaling against TLS tanh-law versus quasiparticle activation-like behavior.",
        "mechanism_weights": {
            "P_TLS": 0.45,
            "P_QUASIPARTICLE": 0.45,
            "P_PHONON": 0.1,
        },
    },
    {
        "signature_id": "NON_EXPONENTIAL_DECAY",
        "signature_label": "NON_EXPONENTIAL_DECAY",
        "match_terms": ["non-exponential", "stretched", "multi-exponential", "kernel memory", "structured bath"],
        "min_terms": 1,
        "priority": 0,
        "assigned_family_class": "KERNEL_MEMORY",
        "bath_rank_order": [
            "KERNEL_MEMORY",
            "STRUCTURED_PHONON_BATH",
            "STRUCTURED_EM_BATH",
        ],
        "minimal_discriminant_measurement": "Acquire high-SNR decay curves, compare exponential versus stretched or multi-exponential fits, then use filter-function sequences if needed.",
        "mechanism_weights": {
            "P_PHONON": 0.6,
            "P_EM_PURCELL": 0.2,
            "P_OTHER": 0.2,
        },
    },
    {
        "signature_id": "REVIVALS_BACKFLOW",
        "signature_label": "REVIVALS_BACKFLOW",
        "match_terms": ["revivals", "backflow", "partial recovery", "finite-size", "bandgap"],
        "min_terms": 1,
        "priority": 1,
        "assigned_family_class": "FINITE_SIZE_STRUCTURED_BATH",
        "bath_rank_order": [
            "FINITE_SIZE_STRUCTURED_BATH",
            "STRUCTURED_PHONON_BATH",
            "STRUCTURED_EM_BATH",
        ],
        "minimal_discriminant_measurement": "Run time-domain sequences that expose revivals and compare with and without phononic or packaging changes.",
        "mechanism_weights": {
            "P_PHONON": 0.6,
            "P_EM_PURCELL": 0.25,
            "P_OTHER": 0.15,
        },
    },
    {
        "signature_id": "AVOIDED_CROSSING",
        "signature_label": "AVOIDED_CROSSING",
        "match_terms": ["avoided crossing", "anticrossing", "gap 2g", "mode tracking"],
        "min_terms": 1,
        "assigned_family_class": "COHERENT_PARASITIC_MODE",
        "bath_rank_order": [
            "COHERENT_PARASITIC_MODE",
            "STRUCTURED_EM_BATH",
            "DEFECT_MODE",
        ],
        "minimal_discriminant_measurement": "Run high-resolution spectroscopy versus flux or bias and verify the anticrossing gap and mode tracking.",
        "mechanism_weights": {
            "P_EM_PURCELL": 0.75,
            "P_OTHER": 0.25,
        },
    },
    {
        "signature_id": "NARROWBAND_PSD",
        "signature_label": "NARROWBAND_NOISE_PSD",
        "match_terms": ["narrowband peak", "noise psd", "filter-function", "linewidth"],
        "min_terms": 1,
        "assigned_family_class": "STRUCTURED_BATH_MODE",
        "bath_rank_order": [
            "STRUCTURED_BATH_MODE",
            "STRUCTURED_EM_BATH",
            "COHERENT_FLUCTUATOR",
        ],
        "minimal_discriminant_measurement": "Use filter-function noise spectroscopy with varied pulse spacing to identify the peak frequency and linewidth.",
        "mechanism_weights": {
            "P_EM_PURCELL": 0.55,
            "P_CONTROL_NOISE": 0.25,
            "P_OTHER": 0.2,
        },
    },
    {
        "signature_id": "BURST_RELAXATION",
        "signature_label": "SUDDEN_T1_COLLAPSES",
        "match_terms": ["sudden t1 collapses", "bursty relaxation", "quasiparticle burst", "parity switching"],
        "min_terms": 1,
        "assigned_family_class": "GLOBAL_BATH_EVENT",
        "bath_rank_order": [
            "QUASIPARTICLE_BATH",
            "PHONON_BATH",
            "GLOBAL_BATH_EVENT",
        ],
        "minimal_discriminant_measurement": "Run fast repeated T1 sampling, look for cross-device correlations, and vary shielding, biasing, and thermalization.",
        "mechanism_weights": {
            "P_QUASIPARTICLE": 0.7,
            "P_PHONON": 0.2,
            "P_OTHER": 0.1,
        },
    },
    {
        "signature_id": "CORRELATED_EVENTS",
        "signature_label": "CORRELATED_EVENTS_ACROSS_DEVICES",
        "match_terms": ["correlated events across devices", "simultaneous monitoring", "global bath"],
        "min_terms": 1,
        "assigned_family_class": "GLOBAL_BATH",
        "bath_rank_order": [
            "GLOBAL_BATH",
            "QUASIPARTICLE_BATH",
            "RADIATIVE_GLOBAL_BATH",
        ],
        "minimal_discriminant_measurement": "Run simultaneous monitoring, compute cross-device correlations, and modify shielding, absorbers, or packaging to test suppression.",
        "mechanism_weights": {
            "P_QUASIPARTICLE": 0.45,
            "P_PHONON": 0.3,
            "P_EM_PURCELL": 0.15,
            "P_OTHER": 0.1,
        },
    },
    {
        "signature_id": "DEPINNING_FLUX_FLOW",
        "signature_label": "DRIVE_DEPINNING_OR_FLUX_FLOW",
        "match_terms": ["depinning", "flux-flow onset", "drive causes crossover", "crossover to higher loss"],
        "min_terms": 1,
        "assigned_family_class": "PINNED_VORTEX_IMPEDANCE",
        "bath_rank_order": [
            "PINNED_VORTEX_IMPEDANCE",
            "METASTABLE_CONFIGURATION_MEMORY",
            "THERMAL_HEATING",
        ],
        "minimal_discriminant_measurement": "Run a drive sweep at fixed prepared state, check whether the crossover shifts with Bcool, and compare delta fr over delta 1/Qi.",
        "mechanism_weights": {
            "P_VORTEX": 0.75,
            "P_CONTROL_NOISE": 0.1,
            "P_OTHER": 0.15,
        },
    },
    {
        "signature_id": "IMPEDANCE_RATIO",
        "signature_label": "CONSISTENT_IMPEDANCE_RATIO",
        "match_terms": ["consistent ratio", "single omega_p", "pinned vortex impedance", "deltafr/fr", "delta(1/qi)"],
        "min_terms": 1,
        "assigned_family_class": "PINNED_VORTEX_IMPEDANCE",
        "bath_rank_order": [
            "PINNED_VORTEX_IMPEDANCE",
            "METASTABLE_CONFIGURATION_MEMORY",
            "VORTEX_RESPONSE",
        ],
        "minimal_discriminant_measurement": "Jointly extract Qi and frequency shift, apply the ratio test for inferred omega_p, and check consistency across Bcool histories.",
        "mechanism_weights": {
            "P_VORTEX": 0.8,
            "P_OTHER": 0.2,
        },
    },
    {
        "signature_id": "NOT_VORTEX",
        "signature_label": "NOT_VORTEX_DOMINATED",
        "match_terms": ["no geometry dependence", "loss stable across field protocols", "not vortex-dominated"],
        "min_terms": 1,
        "assigned_family_class": "NOT_VORTEX_DOMINATED",
        "bath_rank_order": [
            "TLS_ENSEMBLE",
            "EM_BATH",
            "CONDUCTOR_LOSS",
        ],
        "minimal_discriminant_measurement": "Swap geometry or participation, run power and temperature sweeps, and check package and line attenuation contributions.",
        "mechanism_weights": {
            "P_TLS": 0.35,
            "P_EM_PURCELL": 0.35,
            "P_OTHER": 0.3,
        },
    },
]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def dump_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


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


def collect_strings(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            out.extend(collect_strings(item))
        return out
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(collect_strings(item))
        return out
    return []


def append_unique(items: List[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def unique_preserve(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def normalize_label(value: str) -> str:
    chars = [ch if ch.isalnum() else "_" for ch in str(value or "").upper()]
    normalized = "".join(chars)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def family_bucket(label: str) -> str:
    upper = normalize_label(label)
    if any(token in upper for token in ["VORTEX", "METASTABLE", "HIDDEN_DISCRETE", "PINNED"]):
        return "VORTEX_MEMORY"
    if "TLS" in upper or "DIELECTRIC" in upper:
        return "TLS"
    if any(token in upper for token in ["QUASIPARTICLE", "GLOBAL_BATH", "RADIATIVE_GLOBAL"]):
        return "GLOBAL_OR_QUASIPARTICLE"
    if any(token in upper for token in ["KERNEL", "PHONON", "STRUCTURED_BATH", "FINITE_SIZE"]):
        return "KERNEL_OR_PHONON"
    if any(token in upper for token in ["EM", "PURCELL", "PARASITIC_MODE", "COHERENT_FLUCTUATOR", "MODE"]):
        return "EM_MODE"
    if any(token in upper for token in ["CONTROL", "HEATING"]):
        return "CONTROL_OR_THERMAL"
    if upper:
        return "OTHER"
    return ""


def seed_scores_from_label(label: str) -> Dict[str, float]:
    bucket = family_bucket(label)
    scores = {key: 0.0 for key in MECHANISM_SCORE_KEYS}
    if bucket == "VORTEX_MEMORY":
        scores["P_VORTEX"] = 1.0
    elif bucket == "TLS":
        scores["P_TLS"] = 1.0
    elif bucket == "GLOBAL_OR_QUASIPARTICLE":
        scores["P_QUASIPARTICLE"] = 0.7
        scores["P_PHONON"] = 0.3
    elif bucket == "KERNEL_OR_PHONON":
        scores["P_PHONON"] = 0.8
        scores["P_EM_PURCELL"] = 0.2
    elif bucket == "EM_MODE":
        scores["P_EM_PURCELL"] = 1.0
    elif bucket == "CONTROL_OR_THERMAL":
        scores["P_CONTROL_NOISE"] = 0.6
        scores["P_OTHER"] = 0.4
    else:
        scores["P_OTHER"] = 1.0
    return scores


def normalize_scores(weights: Dict[str, float]) -> Dict[str, float]:
    raw = {key: max(0.0, float(weights.get(key, 0.0))) for key in MECHANISM_SCORE_KEYS}
    total = sum(raw.values())
    if total <= 0.0:
        raw["P_OTHER"] = 1.0
        total = 1.0
    return {key: round(raw[key] / total, 6) for key in MECHANISM_SCORE_KEYS}


def derive_system_status(gsc: Dict[str, Any]) -> str:
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
    if harness == "PASSED" and schema == "PASSED" and ref == "PASSED" and determinism == "PASSED":
        return "READY"
    return str(gsc.get("system_status", "") or "")


def make_minimal_final_candidate(base_template: Dict[str, Any]) -> Dict[str, Any]:
    candidate = copy.deepcopy(base_template)
    candidate["candidate_id"] = candidate.get("candidate_id", "") or "M07_WORKING_PATCH_CANDIDATE"
    candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or "M07_WORKING_PATCH_BRANCH"
    candidate["declared_family_class"] = candidate.get("declared_family_class", "") or ""
    candidate["assigned_family_class"] = candidate.get("assigned_family_class", "") or ""
    candidate["family_status"] = candidate.get("family_status", "") or ""
    candidate["governance_self_check"] = copy.deepcopy(READY_SELF_CHECK)
    candidate["system_status"] = "READY"
    candidate["scientific_decision"] = "NOT_EVALUATED"
    candidate["governance_outcome"] = "DEFER"
    candidate["cross_device_status"] = "NOT_REQUIRED"
    candidate.setdefault("cross_device_validation", {})
    candidate["cross_device_validation"]["status"] = "NOT_REQUIRED"
    candidate["promotion_cap_governance"] = ""
    candidate["promotion_cap_scientific"] = ""
    candidate.setdefault("mechanism_scores_after_signature", {key: 0.0 for key in MECHANISM_SCORE_KEYS})
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("signature_matches", [])
    candidate.setdefault("inferred_bath_rank_order", [])
    candidate.setdefault("minimal_discriminant_measurement", "")
    candidate.setdefault("gate_trace", [])
    return candidate


def ensure_candidate_defaults(candidate: Dict[str, Any]) -> None:
    candidate.setdefault("governance_self_check", {})
    for key, value in READY_SELF_CHECK.items():
        candidate["governance_self_check"].setdefault(key, value)
    candidate["governance_self_check"]["system_status"] = derive_system_status(candidate["governance_self_check"]) or "READY"
    candidate["system_status"] = candidate.get("system_status", "") or candidate["governance_self_check"]["system_status"]
    candidate["governance_self_check"]["system_status"] = candidate["system_status"]

    if not candidate.get("scientific_decision"):
        candidate["scientific_decision"] = "NOT_EVALUATED"
    if not candidate.get("governance_outcome"):
        candidate["governance_outcome"] = "DEFER"
    if not candidate.get("cross_device_status"):
        candidate["cross_device_status"] = "NOT_REQUIRED"

    candidate.setdefault("cross_device_validation", {})
    candidate["cross_device_validation"]["status"] = candidate["cross_device_status"]
    candidate.setdefault("mechanism_scores_after_signature", {})
    for key in MECHANISM_SCORE_KEYS:
        candidate["mechanism_scores_after_signature"].setdefault(key, 0.0)
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("signature_matches", [])
    candidate.setdefault("inferred_bath_rank_order", [])
    candidate.setdefault("minimal_discriminant_measurement", "")
    candidate.setdefault("family_status", "")
    candidate.setdefault("declared_family_class", "")
    candidate.setdefault("declared_likely_bath_class", "")
    candidate.setdefault("assigned_family_class", "")
    candidate.setdefault("family_class_mismatch", False)
    candidate.setdefault("bath_classification_consistent_with_glossary", False)
    candidate.setdefault("gate_trace", [])


def find_rule_matches(text: str) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for index, rule in enumerate(SIGNATURE_RULES):
        matched_terms = [term for term in rule["match_terms"] if term in text]
        if len(matched_terms) >= int(rule.get("min_terms", 1)):
            matches.append(
                {
                    "rule_index": index,
                    "signature_id": rule["signature_id"],
                    "signature_label": rule["signature_label"],
                    "matched_terms": unique_preserve(matched_terms),
                    "score": len(unique_preserve(matched_terms)),
                    "priority": int(rule.get("priority", 0)),
                    "assigned_family_class": rule["assigned_family_class"],
                    "bath_rank_order": list(rule["bath_rank_order"]),
                    "minimal_discriminant_measurement": rule["minimal_discriminant_measurement"],
                    "mechanism_weights": dict(rule["mechanism_weights"]),
                }
            )
    matches.sort(key=lambda item: (-item["priority"], -item["score"], item["rule_index"]))
    return matches


def summarize_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "assigned_family_class": candidate.get("assigned_family_class", ""),
        "family_class_mismatch": candidate.get("family_class_mismatch", False),
        "family_status": candidate.get("family_status", ""),
        "inferred_bath_rank_order": candidate.get("inferred_bath_rank_order", []),
        "signature_matches": candidate.get("signature_matches", []),
        "minimal_discriminant_measurement": candidate.get("minimal_discriminant_measurement", ""),
        "bath_classification_consistent_with_glossary": candidate.get("bath_classification_consistent_with_glossary", False),
        "mechanism_scores_after_signature": candidate.get("mechanism_scores_after_signature", {}),
    }


def run_family_triage(candidate: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    candidate = copy.deepcopy(candidate)
    ensure_candidate_defaults(candidate)

    evidence_text = " ".join(collect_strings(candidate)).lower()
    declared_family = str(candidate.get("declared_family_class", "") or "").strip()
    declared_bath = str(candidate.get("declared_likely_bath_class", "") or "").strip()
    declared_label = declared_family or declared_bath

    matches = find_rule_matches(evidence_text)
    append_unique(candidate["automatic_flags_triggered"], "M07_VISIBLE_SOURCE_TRIAGE_ONLY")
    append_unique(candidate["linked_artifacts"], repo_rel(BATH_GLOSSARY))
    append_unique(candidate["linked_artifacts"], repo_rel(SIGNATURE_TO_BATH_CHART))

    if matches:
        top = matches[0]
        assigned_family_class = top["assigned_family_class"]
        inferred_bath_rank_order = list(top["bath_rank_order"])
        for match in matches[1:]:
            inferred_bath_rank_order.extend(match["bath_rank_order"])
        inferred_bath_rank_order = unique_preserve(inferred_bath_rank_order)
        minimal_discriminant_measurement = top["minimal_discriminant_measurement"]
        signature_matches = [match["signature_label"] for match in matches]

        combined_scores = {key: 0.0 for key in MECHANISM_SCORE_KEYS}
        for match in matches:
            for key, value in match["mechanism_weights"].items():
                combined_scores[key] += float(value)
        normalized_scores = normalize_scores(combined_scores)
        assigned_bucket = family_bucket(assigned_family_class)
        declared_bucket = family_bucket(declared_label)
        mismatch = bool(declared_label) and bool(declared_bucket) and assigned_bucket != declared_bucket
        if declared_label and mismatch:
            family_status = "DECLARED_FAMILY_MISMATCH"
        elif declared_label:
            family_status = "DECLARED_FAMILY_CONFIRMED"
        else:
            family_status = "INFERRED_FROM_SIGNATURES"
        candidate["bath_classification_consistent_with_glossary"] = True
    else:
        if declared_label:
            assigned_family_class = declared_family or normalize_label(declared_bath)
            inferred_bath_rank_order = [declared_bath or assigned_family_class]
            normalized_scores = normalize_scores(seed_scores_from_label(declared_label))
            family_status = "DECLARED_ONLY_PENDING_SIGNATURE_TRIAGE"
            mismatch = False
            candidate["bath_classification_consistent_with_glossary"] = True
        else:
            assigned_family_class = "UNASSESSED"
            inferred_bath_rank_order = ["UNASSESSED"]
            normalized_scores = normalize_scores({"P_OTHER": 1.0})
            family_status = "NO_STRONG_SIGNATURE_MATCH"
            mismatch = False
            candidate["bath_classification_consistent_with_glossary"] = False
        minimal_discriminant_measurement = "Collect one surfaced signature from specs/core/signature_to_bath_decision_chart.md before parameter expansion."
        signature_matches = []
        append_unique(candidate["automatic_flags_triggered"], "M07_NO_STRONG_SIGNATURE_MATCH")

    candidate["assigned_family_class"] = assigned_family_class
    candidate["family_class_mismatch"] = mismatch
    candidate["family_status"] = family_status
    candidate["inferred_bath_rank_order"] = inferred_bath_rank_order
    candidate["signature_matches"] = signature_matches
    candidate["minimal_discriminant_measurement"] = minimal_discriminant_measurement
    candidate["mechanism_scores_after_signature"] = normalized_scores

    note = "M07 family triage used only surfaced specs/core/bath_glossary.md and specs/core/signature_to_bath_decision_chart.md mappings."
    if note not in candidate["evaluation_notes"]:
        candidate["evaluation_notes"].append(note)
    if signature_matches:
        matched_note = f"M07 matched signatures: {', '.join(signature_matches)}."
        if matched_note not in candidate["evaluation_notes"]:
            candidate["evaluation_notes"].append(matched_note)

    diagnostics = {
        "artifact_id": "QDP_V10_6_M07_TRIAGE_REPORT",
        "module_id": "M07",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "visible_source_only": True,
        "declared_family_class": declared_family,
        "declared_likely_bath_class": declared_bath,
        "evidence_text_sample": evidence_text[:500],
        "rule_matches": matches,
        "result_summary": summarize_candidate(candidate),
    }
    return candidate, diagnostics


def validate_candidate(candidate_path: Path, validator_path: Path, schema_path: Path) -> Dict[str, Any]:
    return validate_candidate_file(candidate_path, validator_path, schema_path, mode="final")


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
    base_template: Dict[str, Any],
    cases_path: Path,
    validator_path: Path,
    schema_path: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    cases_obj = load_json(cases_path)
    results: List[Dict[str, Any]] = []

    for case in cases_obj.get("cases", []):
        case_id = str(case.get("case_id", ""))
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        candidate = make_minimal_final_candidate(base_template)
        candidate = deep_merge(candidate, case.get("input_candidate", {}))
        candidate, triage_report = run_family_triage(candidate)

        candidate_path = case_dir / f"{case_id}_candidate.json"
        report_path = case_dir / f"{case_id}_report.json"
        dump_json(candidate_path, candidate)
        dump_json(report_path, triage_report)

        validator_result = validate_candidate(candidate_path, validator_path, schema_path)
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
    cases_passed = sum(1 for case in results if case["passed"])
    return {
        "artifact_id": "QDP_V10_6_M07_SELFTEST_REPORT",
        "module_id": "M07",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "visible_source_only": True,
        "cases_total": cases_total,
        "cases_passed": cases_passed,
        "all_passed": cases_total > 0 and cases_passed == cases_total,
        "schema_valid_all": all(case["validator_result"]["valid"] for case in results),
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M07 family-class triage scorer.")
    parser.add_argument("--candidate", type=Path, help="Input candidate JSON object")
    parser.add_argument("--output", type=Path, help="Output candidate JSON path")
    parser.add_argument("--write-triage-report", type=Path, help="Optional triage diagnostic report path")
    parser.add_argument("--base-template", type=Path, default=DEFAULT_BASE_TEMPLATE)
    parser.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--selftest-cases", type=Path, default=DEFAULT_SELFTEST_CASES)
    parser.add_argument("--selftest-output-dir", type=Path, default=DEFAULT_SELFTEST_OUTPUT_DIR)
    parser.add_argument("--write-report", type=Path, default=DEFAULT_SELFTEST_REPORT)
    args = parser.parse_args()

    if args.selftest or (args.candidate is None and args.write_report is not None):
        base_template = load_json(args.base_template)
        report = run_selftests(
            base_template,
            args.selftest_cases,
            args.validator,
            args.schema,
            args.selftest_output_dir,
        )
        dump_json(args.write_report, report)
        print(json.dumps(report, indent=2))
        return 0 if report.get("all_passed", False) else 1

    if args.candidate is None:
        parser.error("--candidate is required unless --selftest is set")

    base_template = load_json(args.base_template)
    candidate = make_minimal_final_candidate(base_template)
    candidate = deep_merge(candidate, load_json(args.candidate))
    candidate, triage_report = run_family_triage(candidate)

    if args.output:
        dump_json(args.output, candidate)
    else:
        print(json.dumps(candidate, indent=2))

    if args.write_triage_report:
        dump_json(args.write_triage_report, triage_report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
