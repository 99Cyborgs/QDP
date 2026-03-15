#!/usr/bin/env python3
"""
QDP v10.6 M09 known-mechanism competition suite.

This is a visible-source working-patch implementation derived from surfaced
mechanism documents only. It fills mechanism_tests and strongest competing
mechanism fields conservatively without claiming parity with unsurfaced
retained-runtime behavior.
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

from qdp_paths import BASE_TEMPLATE, CANDIDATE_VALIDATOR, DEEP_RESEARCH_REPORT, MODULES, ROOT, SCHEMA, SIGNATURE_TO_BATH_CHART, VORTEX_PINNING_METHODS, repo_rel
from qdp_validation import validate_candidate_file


MODULE_PATHS = MODULES["m09"]
DEFAULT_BASE_TEMPLATE = BASE_TEMPLATE
DEFAULT_SCHEMA = SCHEMA
DEFAULT_VALIDATOR = CANDIDATE_VALIDATOR
DEFAULT_SELFTEST_CASES = MODULE_PATHS["selftest_cases"]
DEFAULT_SELFTEST_REPORT = MODULE_PATHS["selftest_report"]
DEFAULT_SELFTEST_OUTPUT_DIR = MODULE_PATHS["selftest_output_dir"]

READY_SELF_CHECK = {
    "validation_harness_status": "PASSED",
    "schema_validation_status": "PASSED",
    "reference_resolution_status": "PASSED",
    "determinism_status": "PASSED",
    "system_status": "READY",
}

M09_OWNER_ARTIFACTS = {
    repo_rel(SIGNATURE_TO_BATH_CHART): SIGNATURE_TO_BATH_CHART,
    repo_rel(VORTEX_PINNING_METHODS): VORTEX_PINNING_METHODS,
    "QDP_Vortex_Pinning_Microwave_Loss_Module.md": ROOT / "QDP_Vortex_Pinning_Microwave_Loss_Module.md",
    "vortex_entry_barrier.md": ROOT / "vortex_entry_barrier.md",
    "vortex_entry_calculator.md": ROOT / "vortex_entry_calculator.md",
    "vortex_microwave_dissipation.md": ROOT / "vortex_microwave_dissipation.md",
    "residual_field_estimation_dilution_fridge.md": ROOT / "residual_field_estimation_dilution_fridge.md",
}

PRIOR_KEY_TO_MECHANISM = {
    "P_TLS": "TLS",
    "P_VORTEX": "VORTEX",
    "P_QUASIPARTICLE": "QUASIPARTICLE",
    "P_PHONON": "PHONON",
    "P_CONTROL_NOISE": "CONTROL_NOISE",
    "P_EM_PURCELL": "EM_PURCELL",
}

MECHANISM_RULES: List[Dict[str, Any]] = [
    {
        "name": "VORTEX",
        "field": "vortex",
        "prior_key": "P_VORTEX",
        "primary_signatures": ["HYSTERESIS", "DRIVE_DEPINNING_OR_FLUX_FLOW", "CONSISTENT_IMPEDANCE_RATIO"],
        "supporting_signatures": ["BIMODAL_DISTRIBUTION", "TELEGRAPH_SWITCHING"],
        "primary_terms": ["bcool", "zfc", "fc", "cooldown field", "field history", "hysteresis index", "depinning", "flux-flow"],
        "supporting_terms": ["vortex", "pinning", "trapped flux", "pearl length", "edge barrier", "field loop"],
        "family_terms": ["VORTEX", "PINNED", "METASTABLE"],
        "minimum_discriminator": "Repeat ZFC vs FC and cooldown-field sweeps, then test width/thickness dependence and delta fr over delta 1/Qi ratio consistency.",
    },
    {
        "name": "QUASIPARTICLE",
        "field": "quasiparticle",
        "prior_key": "P_QUASIPARTICLE",
        "primary_signatures": ["SUDDEN_T1_COLLAPSES"],
        "supporting_signatures": ["CORRELATED_EVENTS_ACROSS_DEVICES"],
        "primary_terms": ["parity switching", "quasiparticle", "qp burst", "pair-breaking", "drive-induced qp", "controlled qp injection"],
        "supporting_terms": ["quasiparticle sink", "vortex-assisted trapping", "above-gap", "nonequilibrium qp"],
        "family_terms": ["QUASIPARTICLE", "GLOBAL_BATH_EVENT"],
        "minimum_discriminator": "Measure parity-switch correlations or controlled QP injection/suppression, and compare with drive-induced pair-breaking signatures.",
    },
    {
        "name": "TLS",
        "field": "tls",
        "prior_key": "P_TLS",
        "primary_signatures": ["POWER_DEPENDENT_SATURATION"],
        "supporting_signatures": ["TEMPERATURE_SCALING_WITHOUT_HYSTERESIS", "NOT_VORTEX_DOMINATED"],
        "primary_terms": ["tls saturation", "participation", "dielectric", "interface loss", "power dependence"],
        "supporting_terms": ["spectral diffusion", "t1 fluctuations", "surface loss", "participation scaling"],
        "family_terms": ["TLS", "DIELECTRIC"],
        "minimum_discriminator": "Run a calibrated power sweep plus geometry/participation scaling and verify the TLS saturation trend across temperatures.",
    },
    {
        "name": "PHONON",
        "field": "phonon",
        "prior_key": "P_PHONON",
        "primary_signatures": ["REVIVALS_BACKFLOW"],
        "supporting_signatures": ["NON_EXPONENTIAL_DECAY", "CORRELATED_EVENTS_ACROSS_DEVICES"],
        "primary_terms": ["pulse tube", "mechanical vibration", "phononic", "bandgap", "vibrational environment"],
        "supporting_terms": ["phonon", "substrate", "downconversion", "phonon trap", "synchronized"],
        "family_terms": ["PHONON", "FINITE_SIZE", "STRUCTURED_BATH"],
        "minimum_discriminator": "Synchronize to the mechanical environment or vary phononic structures to test whether the residual signature tracks substrate-phonon control knobs.",
    },
    {
        "name": "CONTROL_NOISE",
        "field": "control_noise",
        "prior_key": "P_CONTROL_NOISE",
        "primary_signatures": ["NARROWBAND_NOISE_PSD"],
        "supporting_signatures": [],
        "primary_terms": ["filter-function", "control-line", "pulse distortion", "line attenuation", "noise spectroscopy", "1/f"],
        "supporting_terms": ["flux noise", "wiring", "attenuation", "am/pm noise"],
        "family_terms": ["CONTROL", "NOISE"],
        "minimum_discriminator": "Run filter-function noise spectroscopy and line-attenuation or pulse-shape perturbations to see whether the inferred noise peak follows the control chain.",
    },
    {
        "name": "EM_PURCELL",
        "field": "em_purcell",
        "prior_key": "P_EM_PURCELL",
        "primary_signatures": ["AVOIDED_CROSSING"],
        "supporting_signatures": ["NARROWBAND_NOISE_PSD"],
        "primary_terms": ["purcell", "spurious resonator", "coherent parasitic mode", "avoided crossing", "anticrossing", "gap 2g"],
        "supporting_terms": ["mode tracking", "package mode", "em bath"],
        "family_terms": ["PARASITIC", "EM", "MODE"],
        "minimum_discriminator": "Run high-resolution spectroscopy versus bias and verify anticrossing behavior or package-mode dependence.",
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


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().upper() in {"TRUE", "YES", "1", "PASS", "PASSED", "READY"}
    return False


def list_of_strings(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def unique_preserve(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def append_unique(items: List[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


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
    candidate["candidate_id"] = candidate.get("candidate_id", "") or "M09_WORKING_PATCH_CANDIDATE"
    candidate["branch_or_model_tag"] = candidate.get("branch_or_model_tag", "") or "M09_WORKING_PATCH_BRANCH"
    candidate["governance_self_check"] = copy.deepcopy(READY_SELF_CHECK)
    candidate["system_status"] = "READY"
    candidate["scientific_decision"] = "NOT_EVALUATED"
    candidate["governance_outcome"] = "DEFER"
    candidate["cross_device_status"] = "NOT_REQUIRED"
    candidate.setdefault("cross_device_validation", {})
    candidate["cross_device_validation"]["status"] = "NOT_REQUIRED"
    candidate["promotion_cap_governance"] = ""
    candidate["promotion_cap_scientific"] = ""
    candidate["strongest_competing_mechanism_initial"] = ""
    candidate["strongest_competing_mechanism"] = ""
    candidate["mechanism_tests"] = {
        "vortex": {},
        "quasiparticle": {},
        "tls": {},
        "phonon": {},
        "control_noise": {},
        "em_purcell": {},
    }
    candidate.setdefault("mechanism_scores_after_signature", {})
    candidate.setdefault("signature_matches", [])
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("gate_trace", [])
    return candidate


def ensure_candidate_defaults(candidate: Dict[str, Any]) -> None:
    candidate.setdefault("governance_self_check", {})
    for key, value in READY_SELF_CHECK.items():
        candidate["governance_self_check"].setdefault(key, value)
    candidate["governance_self_check"]["system_status"] = derive_system_status(candidate["governance_self_check"]) or "READY"
    candidate["system_status"] = candidate.get("system_status", "") or candidate["governance_self_check"]["system_status"]
    candidate["governance_self_check"]["system_status"] = candidate["system_status"]
    candidate["scientific_decision"] = candidate.get("scientific_decision", "") or "NOT_EVALUATED"
    candidate["governance_outcome"] = candidate.get("governance_outcome", "") or "DEFER"
    candidate["cross_device_status"] = candidate.get("cross_device_status", "") or "NOT_REQUIRED"
    candidate.setdefault("cross_device_validation", {})
    candidate["cross_device_validation"]["status"] = candidate["cross_device_status"]
    candidate.setdefault("mechanism_tests", {})
    for key in ["vortex", "quasiparticle", "tls", "phonon", "control_noise", "em_purcell"]:
        candidate["mechanism_tests"].setdefault(key, {})
    candidate["mechanism_tests"].setdefault("parsimonious_combination_explains", False)
    candidate["mechanism_tests"].setdefault("parsimonious_combination_label", "")
    candidate["mechanism_tests"].setdefault("explains_data", False)
    candidate["mechanism_tests"].setdefault("visible_source_partial_suite", True)
    candidate.setdefault("mechanism_scores_after_signature", {})
    candidate.setdefault("signature_matches", [])
    candidate.setdefault("evaluation_notes", [])
    candidate.setdefault("automatic_flags_triggered", [])
    candidate.setdefault("linked_artifacts", [])
    candidate.setdefault("gate_trace", [])


def evidence_text(candidate: Dict[str, Any]) -> str:
    parts: List[str] = []
    parts.extend(list_of_strings(candidate.get("evaluation_notes", [])))
    for key in [
        "primary_observable",
        "secondary_observable",
        "assigned_family_class",
        "declared_family_class",
        "declared_likely_bath_class",
    ]:
        value = str(candidate.get(key, "") or "").strip()
        if value:
            parts.append(value)
    parts.extend(list_of_strings(candidate.get("signature_matches", [])))
    residuals = candidate.get("residual_analysis", {})
    if isinstance(residuals, dict):
        parts.extend(list_of_strings(residuals.get("features", [])))
    return " ".join(parts).lower()


def match_terms(text: str, terms: List[str]) -> List[str]:
    return [term for term in terms if term in text]


def family_match(candidate: Dict[str, Any], family_terms: List[str]) -> bool:
    haystack = " ".join(
        [
            str(candidate.get("assigned_family_class", "") or ""),
            str(candidate.get("declared_family_class", "") or ""),
            str(candidate.get("declared_likely_bath_class", "") or ""),
        ]
    ).upper()
    return any(term in haystack for term in family_terms)


def strongest_initial_from_priors(candidate: Dict[str, Any]) -> str:
    priors = candidate.get("mechanism_scores_after_signature", {})
    best_name = ""
    best_value = 0.0
    if not isinstance(priors, dict):
        return ""
    for prior_key, mech_name in PRIOR_KEY_TO_MECHANISM.items():
        value = float(priors.get(prior_key, 0.0) or 0.0)
        if value > best_value:
            best_value = value
            best_name = mech_name
    return best_name if best_value > 0.0 else ""


def evaluate_mechanism(rule: Dict[str, Any], candidate: Dict[str, Any], text: str, signatures: List[str]) -> Dict[str, Any]:
    signature_set = set(signatures)
    primary_signature_hits = [sig for sig in rule["primary_signatures"] if sig in signature_set]
    supporting_signature_hits = [sig for sig in rule["supporting_signatures"] if sig in signature_set]
    primary_term_hits = match_terms(text, rule["primary_terms"])
    supporting_term_hits = match_terms(text, rule["supporting_terms"])
    has_family_match = family_match(candidate, rule["family_terms"])
    prior_value = float(candidate.get("mechanism_scores_after_signature", {}).get(rule["prior_key"], 0.0) or 0.0)

    support_score = (
        3 * len(primary_signature_hits)
        + 2 * len(primary_term_hits)
        + len(supporting_signature_hits)
        + len(supporting_term_hits)
        + (1 if has_family_match else 0)
        + prior_value
    )

    explains_data = False
    if rule["name"] == "VORTEX":
        explains_data = bool(primary_signature_hits) or ("field history" in text and "hysteresis" in text)
    elif rule["name"] == "TLS":
        explains_data = "POWER_DEPENDENT_SATURATION" in signature_set or "tls saturation" in text or ("participation" in text and "power dependence" in text)
    elif rule["name"] == "QUASIPARTICLE":
        explains_data = "parity switching" in text or "drive-induced qp" in text or ("SUDDEN_T1_COLLAPSES" in signature_set and "quasiparticle" in text)
    elif rule["name"] == "PHONON":
        phonon_positive = "pulse tube" in text or "mechanical vibration" in text or ("phononic" in text and bool(primary_signature_hits))
        phonon_negative = any(
            phrase in text
            for phrase in [
                "no pulse tube",
                "without pulse tube",
                "remain untested",
                "not been run",
                "no dedicated mechanical-environment discriminator",
                "no engineered phononic control",
            ]
        )
        explains_data = phonon_positive and not phonon_negative
    elif rule["name"] == "CONTROL_NOISE":
        explains_data = ("NARROWBAND_NOISE_PSD" in signature_set or "filter-function" in text) and (
            "line attenuation" in text or "pulse distortion" in text or "control-line" in text or "noise spectroscopy" in text
        )
    elif rule["name"] == "EM_PURCELL":
        explains_data = "AVOIDED_CROSSING" in signature_set or "purcell" in text or "spurious resonator" in text or "coherent parasitic mode" in text

    if explains_data:
        status = "EXPLAINS_DATA"
    elif primary_signature_hits or primary_term_hits:
        status = "PRIMARY_DISCRIMINANT"
    elif support_score > 0:
        status = "SUPPORTING"
    else:
        status = "NOT_SUPPORTED"

    return {
        "status": status,
        "support_score": round(float(support_score), 6),
        "explains_data": explains_data,
        "primary_signature_hits": unique_preserve(primary_signature_hits),
        "supporting_signature_hits": unique_preserve(supporting_signature_hits),
        "primary_term_hits": unique_preserve(primary_term_hits),
        "supporting_term_hits": unique_preserve(supporting_term_hits),
        "family_match": has_family_match,
        "prior_score": round(prior_value, 6),
        "minimal_discriminant_measurement": rule["minimum_discriminator"],
    }


def summarize_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    tests = candidate.get("mechanism_tests", {})
    return {
        "strongest_competing_mechanism_initial": candidate.get("strongest_competing_mechanism_initial", ""),
        "strongest_competing_mechanism": candidate.get("strongest_competing_mechanism", ""),
        "mechanism_tests": {
            "explains_data": tests.get("explains_data", False),
            "parsimonious_combination_explains": tests.get("parsimonious_combination_explains", False),
            "parsimonious_combination_label": tests.get("parsimonious_combination_label", ""),
            "tls": {
                "status": tests.get("tls", {}).get("status", ""),
                "explains_data": tests.get("tls", {}).get("explains_data", False),
            },
            "vortex": {
                "status": tests.get("vortex", {}).get("status", ""),
                "explains_data": tests.get("vortex", {}).get("explains_data", False),
            },
            "quasiparticle": {
                "status": tests.get("quasiparticle", {}).get("status", ""),
                "explains_data": tests.get("quasiparticle", {}).get("explains_data", False),
            },
            "phonon": {
                "status": tests.get("phonon", {}).get("status", ""),
                "explains_data": tests.get("phonon", {}).get("explains_data", False),
            },
            "control_noise": {
                "status": tests.get("control_noise", {}).get("status", ""),
                "explains_data": tests.get("control_noise", {}).get("explains_data", False),
            },
            "em_purcell": {
                "status": tests.get("em_purcell", {}).get("status", ""),
                "explains_data": tests.get("em_purcell", {}).get("explains_data", False),
            },
        },
    }


def run_mechanism_competition(candidate: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    out = copy.deepcopy(candidate)
    ensure_candidate_defaults(out)
    text = evidence_text(out)
    signatures = unique_preserve(list_of_strings(out.get("signature_matches", [])))

    tests = out["mechanism_tests"]
    tests["visible_source_partial_suite"] = True
    tests["surfaced_source_artifacts"] = [
        repo_rel(SIGNATURE_TO_BATH_CHART),
        repo_rel(VORTEX_PINNING_METHODS),
        repo_rel(DEEP_RESEARCH_REPORT),
    ]
    tests["missing_owner_artifacts"] = [name for name, path in M09_OWNER_ARTIFACTS.items() if not path.exists()]

    results_by_name: Dict[str, Dict[str, Any]] = {}
    explainers: List[Tuple[str, float]] = []
    supporters: List[Tuple[str, float]] = []
    for rule in MECHANISM_RULES:
        result = evaluate_mechanism(rule, out, text, signatures)
        tests[rule["field"]] = result
        results_by_name[rule["name"]] = result
        supporters.append((rule["name"], result["support_score"]))
        if result["explains_data"]:
            explainers.append((rule["name"], result["support_score"]))

    initial = strongest_initial_from_priors(out)
    if not initial:
        initial = max(supporters, key=lambda item: item[1])[0] if supporters and supporters[0][1] > 0 else ""
    out["strongest_competing_mechanism_initial"] = initial

    parsimonious_combination_explains = False
    parsimonious_combination_label = ""
    interplay_terms = ["quasiparticle sink", "qp sink", "vortex-assisted trapping", "controlled vortex trapping", "interplay"]
    if results_by_name["VORTEX"]["explains_data"] and results_by_name["QUASIPARTICLE"]["explains_data"] and any(term in text for term in interplay_terms):
        parsimonious_combination_explains = True
        parsimonious_combination_label = "VORTEX_QUASIPARTICLE_INTERPLAY"

    tests["parsimonious_combination_explains"] = parsimonious_combination_explains
    tests["parsimonious_combination_label"] = parsimonious_combination_label
    tests["explains_data"] = bool(explainers) or parsimonious_combination_explains

    if parsimonious_combination_explains:
        strongest = parsimonious_combination_label
    elif explainers:
        strongest = max(explainers, key=lambda item: item[1])[0]
    else:
        strongest = ""
    out["strongest_competing_mechanism"] = strongest

    append_unique(out["automatic_flags_triggered"], "M09_VISIBLE_SOURCE_PARTIAL_DOC_SET")
    if tests["explains_data"]:
        append_unique(out["automatic_flags_triggered"], "M09_KNOWN_MECHANISM_SURFACED")
    append_unique(out["linked_artifacts"], repo_rel(SIGNATURE_TO_BATH_CHART))
    if VORTEX_PINNING_METHODS.exists():
        append_unique(out["linked_artifacts"], repo_rel(VORTEX_PINNING_METHODS))
    append_unique(out["linked_artifacts"], repo_rel(DEEP_RESEARCH_REPORT))

    note = "M09 mechanism competition used only the surfaced subset of mechanism references available in this workspace."
    if note not in out["evaluation_notes"]:
        out["evaluation_notes"].append(note)

    diagnostics = {
        "artifact_id": "QDP_V10_6_M09_MECHANISM_REPORT",
        "module_id": "M09",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "visible_source_only": True,
        "result_summary": summarize_candidate(out),
        "diagnostics": {
            "evidence_text_sample": text[:700],
            "signature_matches": signatures,
            "missing_owner_artifacts": tests["missing_owner_artifacts"],
        },
    }
    return out, diagnostics


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
        candidate, mechanism_report = run_mechanism_competition(candidate)

        candidate_path = case_dir / f"{case_id}_candidate.json"
        report_path = case_dir / f"{case_id}_report.json"
        dump_json(candidate_path, candidate)
        dump_json(report_path, mechanism_report)

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
        "artifact_id": "QDP_V10_6_M09_SELFTEST_REPORT",
        "module_id": "M09",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "visible_source_only": True,
        "cases_total": cases_total,
        "cases_passed": cases_passed,
        "all_passed": cases_total > 0 and cases_passed == cases_total,
        "schema_valid_all": all(case["validator_result"]["valid"] for case in results),
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M09 known-mechanism competition subset.")
    parser.add_argument("--candidate", type=Path, help="Input candidate JSON object")
    parser.add_argument("--output", type=Path, help="Output candidate JSON path")
    parser.add_argument("--write-mechanism-report", type=Path, help="Optional mechanism report path")
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
    candidate, mechanism_report = run_mechanism_competition(candidate)

    if args.output:
        dump_json(args.output, candidate)
    else:
        print(json.dumps(candidate, indent=2))
    if args.write_mechanism_report:
        dump_json(args.write_mechanism_report, mechanism_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
