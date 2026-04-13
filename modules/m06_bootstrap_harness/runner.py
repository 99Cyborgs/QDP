#!/usr/bin/env python3
"""
QDP v10.6 M06 bootstrap harness runner.

This harness does four things in one deterministic pass:
1. Re-runs strict ordinary and subsystem reference resolution.
2. Re-runs M05 stage-machine self-tests.
3. Executes the five canonical M06 bootstrap cases and checks exact outcomes.
4. Computes mode-divergence and module-closure reports from the current artifact set.

The harness is allowed to report that the environment is NOT ready.
That is different from the harness module itself being implemented correctly.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import subprocess
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

from qdp_io.artifacts import artifact_report_header, dump_json, module_report_header, sha256_file, stable_hash, utc_now
from qdp_io.reference_manifest import (
    RETAINED_GOVERNANCE_REGISTRY_REF_ID,
    RETAINED_RUNTIME_REF_ID,
    find_reference_entry,
    reference_has_authoritative_binding as shared_reference_has_authoritative_binding,
    reference_is_reconstructed_surrogate,
)
from tools.workflow.qdp_runtime.qdp_module_verification import (
    build_module_selftest_alias,
    build_module_verification_checks,
)
from tools.workflow.qdp_runtime.qdp_module_workflows import module_selftest_keys, report_all_passed, report_all_validator_valid, run_module_selftests
from tools.workflow.qdp_runtime.qdp_paths import (
    AUTHORITATIVE_DEPENDENT_MODULES,
    BASE_TEMPLATE,
    BATH_GLOSSARY,
    BUILD_SPEC,
    CANDIDATE_VALIDATOR,
    DEEP_RESEARCH_REPORT,
    GOVERNANCE_REGISTRY,
    MASTER_SPEC,
    M01_CLOSURE_REPORT,
    M03_ORDINARY_REPORT,
    M03_SUBSYSTEM_REPORT,
    MODE_DIVERGENCE_POLICY,
    MODE_DIVERGENCE_REPORT,
    MODEL_SPEC,
    MODULES,
    MODULE_CLOSURE_CONTRACTS,
    MODULE_CLOSURE_EVALUATION_REPORT,
    MODULE_REGISTRY_JSON,
    MODULE_REGISTRY_MD,
    REFERENCE_MANIFEST,
    RESUME_POLICY,
    RETAINED_OPERATIVE_BODY,
    ROOT,
    RULE_BINDING_REGISTRY,
    RUNTIME_PROMPT,
    SCHEMA,
    SIGNATURE_TO_BATH_CHART,
    VISIBLE_SOURCE_WORKING_PATCH_MODULES,
    VALIDATION_GATE,
    repo_rel,
)
from tools.workflow.qdp_runtime.qdp_registry import write_module_registry
from tools.workflow.qdp_runtime.qdp_run_ledger import record_run


DEFAULT_ROOT = ROOT
SELFTEST_MODULE_KEYS = module_selftest_keys()
PATCH_NOTE_TERMS = {
    "M07": ["visible-source", "working", "patch"],
    "M08": ["visible-source", "working", "patch"],
    "M09": ["visible-source", "partial"],
    "M10": ["visible-source", "working", "patch"],
    "M11": ["visible-source", "working", "patch", "lindblad"],
    "M12": ["visible-source", "working", "patch", "falsifier"],
    "M13": ["visible-source", "working", "patch", "cross-device"],
    "M14": ["visible-source", "working", "patch", "promotion-cap"],
    "M15": ["visible-source", "working", "patch", "typed"],
    "S16": ["visible-source", "working", "patch", "subsystem"],
    "S17": ["visible-source", "working", "patch", "alias"],
    "S18": ["visible-source", "working", "patch", "closure"],
    "S19": ["visible-source", "working", "patch", "supported"],
}
M02_TYPED_FIELDS = [
    "calibration_status",
    "identifiability_status",
    "drift_ledger",
    "dataset_governance",
]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def run_cmd(cmd: List[str]) -> Dict[str, Any]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode == 0,
    }


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def derive_system_status(gsc: Dict[str, Any], fallback: str = "") -> str:
    schema = gsc.get("schema_validation_status", "")
    ref = gsc.get("reference_resolution_status", "")
    vh = gsc.get("validation_harness_status", "")
    det = gsc.get("determinism_status", "")
    if schema == "FAILED":
        return "SCHEMA_VALIDATION_FAILURE"
    if ref == "FAILED":
        return "REFERENCE_RESOLUTION_FAILURE"
    if vh == "FAILED" or det == "FAILED":
        return "GOVERNANCE_LOGIC_FAILURE"
    if vh == "UNKNOWN":
        return "HARNESS_REQUIRED"
    if fallback:
        return fallback
    if vh == "PASSED" and det == "PASSED" and ref == "PASSED" and schema == "PASSED":
        return "READY"
    return ""


def normalize_case_result(case_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "case_id": case_result["case_id"],
        "passed": case_result["passed"],
        "comparison_ok": case_result["comparison_ok"],
        "comparison_failures": case_result["comparison_failures"],
        "validator_valid": case_result["validator_result"]["valid"],
        "governance_self_check_ok": case_result["governance_self_check_ok"],
        "result_summary": case_result["result_summary"],
    }


def extract_mandatory_retained_sections(build_spec_text: str) -> List[str]:
    lines = build_spec_text.splitlines()
    in_block = False
    sections: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "## MANDATORY RETAINED BODY":
            in_block = True
            continue
        if in_block and stripped.startswith("## "):
            break
        if in_block and stripped.startswith("- "):
            sections.append(stripped[2:].strip())
    return sections


def detect_forbidden_shorthand(runtime_text: str, forbidden_phrases: List[str]) -> List[str]:
    detected = set()
    in_no_loss_block = False
    for line in runtime_text.splitlines():
        stripped = line.strip()
        if stripped == "## NO LOSS PRESERVATION RULE":
            in_no_loss_block = True
            continue
        if in_no_loss_block and stripped.startswith("## "):
            in_no_loss_block = False
        lowered = stripped.lower()
        for phrase in forbidden_phrases:
            if phrase in lowered:
                # Allow the explicit forbidden-example bullets inside the no-loss rule itself.
                if in_no_loss_block and stripped.startswith("- "):
                    continue
                detected.add(phrase)
    return sorted(detected)


def mandatory_section_present(section_name: str, runtime_text_lower: str) -> bool:
    if section_name == "full enum block":
        required_markers = [
            "### scientific_decision",
            "### governance_outcome",
            "### cross_device_status",
            "### self_check_status",
            "### system_status",
        ]
        return all(marker in runtime_text_lower for marker in required_markers)
    if section_name == "full execution order":
        return "## execution order" in runtime_text_lower
    if section_name == "full stage definitions":
        required_markers = [
            "### stage 0",
            "### stage 1",
            "### stage 10",
            "### stage 17",
            "### stage 19",
        ]
        return all(marker in runtime_text_lower for marker in required_markers)
    return section_name.lower() in runtime_text_lower


def runtime_integrity_check(root: Path, build_spec_path: Path) -> Dict[str, Any]:
    runtime_path = RUNTIME_PROMPT
    retained_path = RETAINED_OPERATIVE_BODY
    forbidden_phrases = [
        "operational meaning identical to prior version",
        "same as v10.1",
        "same as v10.2",
        "same as earlier rules",
    ]

    result: Dict[str, Any] = {
        "build_spec_path": str(build_spec_path),
        "build_spec_exists": build_spec_path.exists(),
        "runtime_prompt_path": str(runtime_path),
        "retained_runtime_source_path": str(retained_path),
        "runtime_prompt_exists": runtime_path.exists(),
        "retained_runtime_source_exists": retained_path.exists(),
        "forbidden_shorthand_phrases": forbidden_phrases,
        "mandatory_retained_sections": [],
        "forbidden_shorthand_detected": [],
        "missing_mandatory_sections": [],
        "passed": False,
        "status": "BLOCKED",
        "blocking_reason": "",
    }

    if not build_spec_path.exists():
        result["blocking_reason"] = f"Build spec is absent: {build_spec_path.name}"
        return result

    build_spec_text = build_spec_path.read_text(encoding="utf-8")
    mandatory_sections = extract_mandatory_retained_sections(build_spec_text)
    result["mandatory_retained_sections"] = mandatory_sections

    if not runtime_path.exists():
        result["blocking_reason"] = "runtime/current/runtime_prompt.md is absent."
        return result

    text = runtime_path.read_text(encoding="utf-8")
    lowered = text.lower()
    result["forbidden_shorthand_detected"] = detect_forbidden_shorthand(text, forbidden_phrases)
    result["missing_mandatory_sections"] = [s for s in mandatory_sections if not mandatory_section_present(s, lowered)]
    result["passed"] = not result["forbidden_shorthand_detected"] and not result["missing_mandatory_sections"] and retained_path.exists()
    result["status"] = "PASSED" if result["passed"] else "FAILED"
    if not retained_path.exists():
        result["blocking_reason"] = "runtime/retained/operative_body_v10_1.md is absent."
    elif result["forbidden_shorthand_detected"]:
        result["blocking_reason"] = "Forbidden shorthand detected in runtime prompt."
    elif result["missing_mandatory_sections"]:
        result["blocking_reason"] = "Mandatory retained sections missing from runtime prompt."
    return result


def emit_m01_closure_report(
    root: Path,
    manifest: Dict[str, Any],
    runtime_integrity: Dict[str, Any],
    output_path: Path,
) -> Dict[str, Any]:
    runtime_prompt = RUNTIME_PROMPT
    retained_runtime = RETAINED_OPERATIVE_BODY
    retained_entry = find_reference_entry(manifest, RETAINED_RUNTIME_REF_ID)
    retained_provenance = retained_entry.get("provenance", "")
    report = {
        **module_report_header("QDP_V10_6_M01_CLOSURE_REPORT", "M01"),
        "runtime_prompt_path": str(runtime_prompt),
        "runtime_prompt_sha256": sha256_file(runtime_prompt) if runtime_prompt.exists() else "",
        "retained_runtime_source_path": str(retained_runtime),
        "retained_runtime_source_sha256": sha256_file(retained_runtime) if retained_runtime.exists() else "",
        "retained_runtime_source_provenance": retained_provenance,
        "retained_runtime_source_authoritative": retained_provenance != "reconstructed_surrogate",
        "runtime_integrity_snapshot": {
            "status": runtime_integrity.get("status", ""),
            "runtime_prompt_exists": runtime_integrity.get("runtime_prompt_exists", False),
            "retained_runtime_source_exists": runtime_integrity.get("retained_runtime_source_exists", False),
            "forbidden_shorthand_detected": runtime_integrity.get("forbidden_shorthand_detected", []),
            "missing_mandatory_sections": runtime_integrity.get("missing_mandatory_sections", []),
        },
        "notes": [
            "This report records the current runtime prompt hash used by the M01 closure predicate.",
            "If retained_runtime_source_provenance is reconstructed_surrogate, this artifact does not certify independently recovered retained-source fidelity.",
        ],
    }
    dump_json(output_path, report)
    return report


def evaluate_governance_self_check(candidate: Dict[str, Any]) -> Tuple[bool, List[str]]:
    failures: List[str] = []
    gsc = candidate.get("governance_self_check")
    if not isinstance(gsc, dict):
        return False, ["governance_self_check missing or not an object"]
    required = [
        "validation_harness_status",
        "schema_validation_status",
        "reference_resolution_status",
        "determinism_status",
        "system_status",
    ]
    for key in required:
        if key not in gsc:
            failures.append(f"governance_self_check.{key} missing")
    if candidate.get("system_status", "") != gsc.get("system_status", ""):
        failures.append("system_status does not mirror governance_self_check.system_status")
    return (not failures), failures


def make_base_candidate(m05_module, base_template: Dict[str, Any], gsc_status: str = "READY") -> Dict[str, Any]:
    c = m05_module.make_minimal_final_candidate(base_template)
    if gsc_status == "READY":
        c["governance_self_check"] = {
            "validation_harness_status": "PASSED",
            "schema_validation_status": "PASSED",
            "reference_resolution_status": "PASSED",
            "determinism_status": "PASSED",
            "system_status": "READY",
        }
        c["system_status"] = "READY"
    return c


def run_bootstrap_cases(
    m05_module,
    base_template: Dict[str, Any],
    cases_obj: Dict[str, Any],
    validator: Path,
    schema: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    runs: List[Dict[str, Any]] = []
    cases = cases_obj.get("cases", []) if isinstance(cases_obj.get("cases", []), list) else []
    repeats = int(cases_obj.get("repeat_runs_for_determinism", 2))

    for run_index in range(1, repeats + 1):
        run_dir = output_dir / f"run_{run_index}"
        run_dir.mkdir(parents=True, exist_ok=True)
        run_results: List[Dict[str, Any]] = []
        for case in cases:
            case_id = str(case.get("case_id", ""))
            base_candidate = make_base_candidate(m05_module, base_template)
            candidate = m05_module.deep_merge(base_candidate, case.get("candidate_overrides", {}))
            stage_inputs = case.get("stage_inputs", {}) if isinstance(case.get("stage_inputs", {}), dict) else {}
            out_candidate, report = m05_module.run_state_machine(candidate, stage_inputs)

            case_dir = run_dir / case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            candidate_path = case_dir / f"{case_id}_candidate.json"
            report_path = case_dir / f"{case_id}_report.json"
            candidate_path.write_text(json.dumps(out_candidate, indent=2), encoding="utf-8")
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

            validator_result = m05_module.validate_candidate_with_existing_validator(
                out_candidate,
                validator,
                schema,
                case_dir,
                case_id,
            )
            comparison_ok, comparison_failures = m05_module.compare_expected(out_candidate, report, case.get("expected", {}))
            gsc_ok, gsc_failures = evaluate_governance_self_check(out_candidate)
            case_passed = comparison_ok and validator_result["valid"] and gsc_ok
            run_results.append(
                {
                    "case_id": case_id,
                    "class": case.get("class", ""),
                    "description": case.get("description", ""),
                    "passed": case_passed,
                    "comparison_ok": comparison_ok,
                    "comparison_failures": comparison_failures,
                    "validator_result": validator_result,
                    "governance_self_check_ok": gsc_ok,
                    "governance_self_check_failures": gsc_failures,
                    "result_summary": {
                        "scientific_decision": out_candidate.get("scientific_decision", ""),
                        "governance_outcome": out_candidate.get("governance_outcome", ""),
                        "cross_device_status": out_candidate.get("cross_device_status", ""),
                        "promotion_cap_governance": out_candidate.get("promotion_cap_governance", ""),
                        "promotion_cap_scientific": out_candidate.get("promotion_cap_scientific", ""),
                        "system_status": out_candidate.get("system_status", ""),
                        "terminated_at": report.get("terminated_at", ""),
                        "validation_ladder": out_candidate.get("validation_ladder", {}),
                    },
                    "output_paths": {
                        "candidate": str(candidate_path),
                        "report": str(report_path),
                    },
                }
            )
        runs.append(
            {
                "run_index": run_index,
                "cases_total": len(run_results),
                "cases_passed": sum(1 for r in run_results if r["passed"]),
                "all_passed": all(r["passed"] for r in run_results),
                "results": run_results,
                "normalized_hash": stable_hash([normalize_case_result(r) for r in run_results]),
            }
        )

    deterministic = len({r["normalized_hash"] for r in runs}) == 1
    all_passed_all_runs = all(r["all_passed"] for r in runs)
    return {
        "cases_total": len(cases),
        "repeat_runs": repeats,
        "runs": runs,
        "all_cases_exact_match_all_runs": all_passed_all_runs,
        "deterministic_across_repeated_runs": deterministic,
    }


def update_governance_registry_with_reports(
    registry_path: Path,
    ordinary_report: Dict[str, Any],
    subsystem_report: Dict[str, Any],
) -> Dict[str, Any]:
    registry = load_json(registry_path)
    resolution_index: Dict[str, Dict[str, Any]] = {}
    for report in (ordinary_report, subsystem_report):
        for item in report.get("resolved_references", []):
            ref_id = str(item.get("ref_id", "")).strip()
            if not ref_id:
                continue
            resolution_index[ref_id] = {
                "ref_id": ref_id,
                "relative_path": item.get("relative_path", ""),
                "sha256": item.get("sha256", ""),
                "resolved": True,
            }
        for item in report.get("unresolved_references", []):
            ref_id = str(item.get("ref_id", "")).strip()
            if not ref_id or ref_id in resolution_index:
                continue
            resolution_index[ref_id] = {
                "ref_id": ref_id,
                "relative_path": item.get("relative_path", ""),
                "sha256": "",
                "resolved": False,
            }

    registry["reference_resolution_summary_current_environment"] = {
        "resolved_count": ordinary_report.get("resolved_count", 0),
        "unresolved_count": ordinary_report.get("unresolved_count", 0),
        "critical_unresolved_ref_ids": [u["ref_id"] for u in ordinary_report.get("unresolved_references", []) if str(u.get("criticality", "")).startswith("CRITICAL")],
        "reference_resolution_status": ordinary_report.get("reference_resolution_status", ""),
    }
    registry["reference_resolution_summary_by_mode"] = {
        "ordinary": {
            "report_id": ordinary_report.get("report_id", ""),
            "resolved_count": ordinary_report.get("resolved_count", 0),
            "unresolved_count": ordinary_report.get("unresolved_count", 0),
            "critical_unresolved_count": ordinary_report.get("critical_unresolved_count", 0),
            "reference_resolution_status": ordinary_report.get("reference_resolution_status", ""),
        },
        "subsystem": {
            "report_id": subsystem_report.get("report_id", ""),
            "resolved_count": subsystem_report.get("resolved_count", 0),
            "unresolved_count": subsystem_report.get("unresolved_count", 0),
            "critical_unresolved_count": subsystem_report.get("critical_unresolved_count", 0),
            "reference_resolution_status": subsystem_report.get("reference_resolution_status", ""),
        },
    }
    registry["current_resolution_reports"] = {
        "ordinary": ordinary_report.get("report_id", ""),
        "subsystem": subsystem_report.get("report_id", ""),
    }
    canonical_references: List[Dict[str, Any]] = []
    seen_ref_ids = set()
    for item in registry.get("canonical_references", []):
        ref_id = str(item.get("ref_id", "")).strip()
        if not ref_id:
            continue
        merged = copy.deepcopy(item)
        current = resolution_index.get(ref_id)
        if current is not None:
            merged["relative_path"] = current.get("relative_path", merged.get("relative_path", ""))
            merged["sha256"] = current.get("sha256", "") if current.get("resolved", False) else ""
            merged["resolved"] = current.get("resolved", False)
        canonical_references.append(merged)
        seen_ref_ids.add(ref_id)
    for ref_id in sorted(resolution_index):
        if ref_id not in seen_ref_ids:
            canonical_references.append(copy.deepcopy(resolution_index[ref_id]))
    registry["canonical_references"] = canonical_references
    dump_json(registry_path, registry)
    return registry


def build_mode_divergence_report(
    root: Path,
    policy_path: Path,
    manifest_path: Path,
    ordinary_report_path: Path,
    subsystem_report_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    policy = load_json(policy_path)
    manifest = load_json(manifest_path)
    ordinary = load_json(ordinary_report_path)
    subsystem = load_json(subsystem_report_path)

    hash_inputs: List[Dict[str, Any]] = []
    for rel in policy.get("shared_core", {}).get("hash_inputs", []):
        path = root / rel
        hash_inputs.append(
            {
                "path": rel,
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.exists() else "",
            }
        )
    shared_core_hash = stable_hash(hash_inputs)

    shared_ref_ids = {
        e["ref_id"]
        for e in manifest.get("reference_entries", [])
        if set(e.get("modes", [])) >= {"ordinary", "subsystem"}
    }

    def ref_state_map(report: Dict[str, Any]) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for item in report.get("resolved_references", []):
            out[item["ref_id"]] = "resolved"
        for item in report.get("unresolved_references", []):
            out[item["ref_id"]] = "unresolved"
        return out

    ordinary_ref_map = ref_state_map(ordinary)
    subsystem_ref_map = ref_state_map(subsystem)
    shared_overrides: List[Dict[str, Any]] = []
    for ref_id in sorted(shared_ref_ids):
        if ordinary_ref_map.get(ref_id, "absent") != subsystem_ref_map.get(ref_id, "absent"):
            shared_overrides.append(
                {
                    "field": f"reference:{ref_id}",
                    "ordinary": ordinary_ref_map.get(ref_id, "absent"),
                    "subsystem": subsystem_ref_map.get(ref_id, "absent"),
                }
            )

    shared_fields = [
        "reference_resolution_status",
        "system_status",
        "promotion_cap_governance",
        "critical_unresolved_count",
    ]
    for field in shared_fields:
        if ordinary.get(field) != subsystem.get(field):
            shared_overrides.append(
                {
                    "field": field,
                    "ordinary": ordinary.get(field),
                    "subsystem": subsystem.get(field),
                }
            )

    if sorted(ordinary.get("automatic_flags_triggered", [])) != sorted(subsystem.get("automatic_flags_triggered", [])):
        shared_overrides.append(
            {
                "field": "automatic_flags_triggered",
                "ordinary": sorted(ordinary.get("automatic_flags_triggered", [])),
                "subsystem": sorted(subsystem.get("automatic_flags_triggered", [])),
            }
        )

    ordinary_delta = {
        "mode": ordinary.get("mode", ""),
        "resolved_mode_specific_refs": sorted(
            item["ref_id"]
            for item in ordinary.get("resolved_references", [])
            if item["ref_id"] not in shared_ref_ids
        ),
        "unresolved_mode_specific_refs": sorted(
            item["ref_id"]
            for item in ordinary.get("unresolved_references", [])
            if item["ref_id"] not in shared_ref_ids
        ),
    }
    subsystem_delta = {
        "mode": subsystem.get("mode", ""),
        "resolved_mode_specific_refs": sorted(
            item["ref_id"]
            for item in subsystem.get("resolved_references", [])
            if item["ref_id"] not in shared_ref_ids
        ),
        "unresolved_mode_specific_refs": sorted(
            item["ref_id"]
            for item in subsystem.get("unresolved_references", [])
            if item["ref_id"] not in shared_ref_ids
        ),
    }

    report = {
        **artifact_report_header("QDP_V10_6_MODE_DIVERGENCE_REPORT"),
        "policy_id": policy.get("artifact_id", ""),
        "shared_core_hash": shared_core_hash,
        "shared_core_hash_inputs": hash_inputs,
        "ordinary_delta_hash": stable_hash(ordinary_delta),
        "subsystem_delta_hash": stable_hash(subsystem_delta),
        "shared_field_override_detected": bool(shared_overrides),
        "override_details": shared_overrides,
        "override_exception_ids": [],
        "ordinary_report_id": ordinary.get("report_id", ""),
        "subsystem_report_id": subsystem.get("report_id", ""),
        "status": "FAILED" if shared_overrides else "PASSED",
    }
    dump_json(output_path, report)
    return report


def module_selftest_report(context: Dict[str, Any], module_id: str) -> Dict[str, Any]:
    return context.get("module_selftests", {}).get(module_id, {}).get("report", {})


def patch_notes_terms_present(module_id: str) -> Tuple[bool, str]:
    module = MODULES[module_id.lower()]
    patch_notes = module.get("patch_notes")
    if not isinstance(patch_notes, Path) or not patch_notes.exists():
        return False, "patch notes missing"
    text = patch_notes.read_text(encoding="utf-8").lower()
    terms = PATCH_NOTE_TERMS.get(module_id, [])
    missing = [term for term in terms if term not in text]
    return not missing, f"missing_terms={missing}"


def m02_contract_complete() -> Tuple[bool, str]:
    if not BASE_TEMPLATE.exists() or not SCHEMA.exists() or not CANDIDATE_VALIDATOR.exists():
        return False, "template, schema, or validator missing"
    template = load_json(BASE_TEMPLATE)
    schema = load_json(SCHEMA)
    validator_text = CANDIDATE_VALIDATOR.read_text(encoding="utf-8")
    template_missing = [field for field in M02_TYPED_FIELDS if field not in template]
    schema_missing = [field for field in M02_TYPED_FIELDS if field not in schema.get("properties", {})]
    validator_missing = [field for field in M02_TYPED_FIELDS if field not in validator_text]
    passed = not template_missing and not schema_missing and not validator_missing
    return passed, (
        f"template_missing={template_missing}; "
        f"schema_missing={schema_missing}; "
        f"validator_missing={validator_missing}"
    )


def m04_intake_mapping_complete(context: Dict[str, Any]) -> Tuple[bool, str]:
    report = module_selftest_report(context, "M04")
    valid_case = next((case for case in report.get("cases", []) if case.get("case_id") == "CASE_M04_VALID_BRANCH"), None)
    if not isinstance(valid_case, dict):
        return False, "CASE_M04_VALID_BRANCH missing"
    actual = valid_case.get("actual_summary", {})
    required = {
        "branch_or_model_tag": bool(str(actual.get("branch_or_model_tag", "")).strip()),
        "primary_observable": bool(str(actual.get("primary_observable", "")).strip()),
        "secondary_observable": bool(str(actual.get("secondary_observable", "")).strip()),
        "preliminary_intake_outcome": bool(str(actual.get("preliminary_intake_outcome", "")).strip()),
        "intake_ready_for_compute": bool(actual.get("intake_ready_for_compute", False)),
    }
    passed = all(required.values()) and bool(str(actual.get("governance_outcome", "")).strip())
    return passed, f"required_fields={required}"


def evaluate_contract_predicate(
    module_id: str,
    predicate_id: str,
    target: str,
    root: Path,
    context: Dict[str, Any],
) -> Tuple[bool, str]:
    path = root / target

    if predicate_id == "M06_P2":
        if not path.exists():
            return False, f"bootstrap_cases_missing path={path.name}"
        cases_obj = load_json(path)
        case_count = len(cases_obj.get("cases", [])) if isinstance(cases_obj.get("cases", []), list) else 0
        passed = case_count >= 5
        return passed, f"bootstrap_case_count={case_count}"

    if predicate_id.endswith(("_P1", "_P2", "_P3")) and predicate_id not in {"M01_P3", "M06_P2"}:
        exists = path.exists()
        return exists, f"artifact_exists={exists} path={path.name}"

    if predicate_id == "M01_P3":
        runtime = context["runtime_integrity"]
        passed = runtime.get("runtime_prompt_exists", False) and not runtime.get("missing_mandatory_sections", [])
        return passed, f"missing_mandatory_sections={runtime.get('missing_mandatory_sections', [])}"

    if predicate_id == "M01_P4":
        runtime = context["runtime_integrity"]
        passed = runtime.get("runtime_prompt_exists", False) and not runtime.get("forbidden_shorthand_detected", [])
        return passed, f"forbidden_shorthand_detected={runtime.get('forbidden_shorthand_detected', [])}"

    if predicate_id == "M01_P5":
        closure_report = M01_CLOSURE_REPORT
        runtime_prompt = RUNTIME_PROMPT
        if not closure_report.exists() or not runtime_prompt.exists():
            return False, "M01 closure report or runtime prompt missing"
        try:
            report = load_json(closure_report)
        except Exception:
            return False, "M01 closure report unreadable"
        expected = report.get("runtime_prompt_sha256", "")
        actual = sha256_file(runtime_prompt)
        return expected == actual and bool(expected), f"expected={expected} actual={actual}"

    if predicate_id == "M03_P4":
        report = context["ordinary_reference_report"]
        passed = report.get("critical_unresolved_count", 0) == 0
        return passed, f"critical_unresolved_count={report.get('critical_unresolved_count', 0)}"

    if predicate_id == "M03_P5":
        report = context["subsystem_reference_report"]
        passed = report.get("critical_unresolved_count", 0) == 0
        return passed, f"critical_unresolved_count={report.get('critical_unresolved_count', 0)}"

    if predicate_id == "M03_P6":
        registry = context["governance_registry"]
        ordinary = context["ordinary_reference_report"]
        subsystem = context["subsystem_reference_report"]
        by_mode = registry.get("reference_resolution_summary_by_mode", {})
        passed = (
            by_mode.get("ordinary", {}).get("report_id") == ordinary.get("report_id")
            and by_mode.get("subsystem", {}).get("report_id") == subsystem.get("report_id")
            and by_mode.get("ordinary", {}).get("reference_resolution_status") == ordinary.get("reference_resolution_status")
            and by_mode.get("subsystem", {}).get("reference_resolution_status") == subsystem.get("reference_resolution_status")
        )
        return passed, f"ordinary_report_id={by_mode.get('ordinary', {}).get('report_id', '')}; subsystem_report_id={by_mode.get('subsystem', {}).get('report_id', '')}"

    if predicate_id == "M05_P6":
        retained = RETAINED_OPERATIVE_BODY
        passed = retained.exists()
        return passed, f"retained_v10_1_operative_body_exists={passed}"

    if predicate_id == "M06_P4":
        report = context["m06_bootstrap_report"]
        checks = report.get("checks", {})
        passed = all(
            key in checks
            for key in [
                "reference_resolution",
                "schema_validation",
                "module_verification",
                "stage_machine_selftests",
                "governance_self_diagnostic",
                "runtime_integrity",
            ]
        )
        return passed, f"check_keys={sorted(checks.keys())}"

    if predicate_id == "M06_P5":
        report = context["m06_bootstrap_report"]
        passed = report.get("determinism_status") == "PASSED"
        return passed, f"determinism_status={report.get('determinism_status', '')}"

    if predicate_id in {"M03_P7", "M06_P6"}:
        divergence = context["mode_divergence_report"]
        passed = divergence.get("status") == "PASSED"
        return passed, f"mode_divergence_status={divergence.get('status', '')}"

    if predicate_id.endswith("_P4") and module_id in {
        "M01",
        "M02",
        "M04",
        "M05",
        "M07",
        "M08",
        "M09",
        "M10",
        "M11",
        "M12",
        "M13",
        "M14",
        "M15",
        "S16",
        "S17",
        "S18",
        "S19",
    }:
        report = module_selftest_report(context, module_id)
        passed = report_all_passed(report)
        return passed, f"cases_passed={report.get('cases_passed', 0)}/{report.get('cases_total', 0)}"

    if predicate_id.endswith("_P5") and module_id in {
        "M02",
        "M04",
        "M05",
        "M07",
        "M08",
        "M09",
        "M10",
        "M11",
        "M12",
        "M13",
        "M14",
        "M15",
        "S16",
        "S17",
        "S18",
        "S19",
    }:
        report = module_selftest_report(context, module_id)
        passed = report_all_passed(report) and report_all_validator_valid(report)
        return passed, f"all_validator_results_valid={passed}"

    if predicate_id == "M02_P6":
        return m02_contract_complete()

    if predicate_id == "M04_P6":
        return m04_intake_mapping_complete(context)

    if predicate_id.endswith("_P6") and module_id in {"M07", "M08", "M09", "M10", "M11", "M12", "M13", "M14", "M15", "S16", "S17", "S18", "S19"}:
        return patch_notes_terms_present(module_id)

    return False, f"Unhandled predicate {module_id}:{predicate_id}"


def surrogate_limitations_for_module(module_id: str, context: Dict[str, Any]) -> List[str]:
    manifest = context.get("reference_manifest", {})
    limitations: List[str] = []
    if module_id in {"M01", "M05", "M06"}:
        retained_runtime = find_reference_entry(manifest, RETAINED_RUNTIME_REF_ID)
        if (
            reference_is_reconstructed_surrogate(retained_runtime)
            and not reference_has_authoritative_binding(RETAINED_RUNTIME_REF_ID, context)
        ):
            limitations.append(
                "retained_v10_1_operative_body is a reconstructed_surrogate artifact without an authoritative binding"
            )
    if module_id in {"M03", "M06"}:
        retained_registry = find_reference_entry(manifest, RETAINED_GOVERNANCE_REGISTRY_REF_ID)
        if (
            reference_is_reconstructed_surrogate(retained_registry)
            and not reference_has_authoritative_binding(
                RETAINED_GOVERNANCE_REGISTRY_REF_ID,
                context,
            )
        ):
            limitations.append(
                "retained_federated_governance_registry_object is a reconstructed_surrogate artifact without an authoritative binding"
            )
    return limitations


def reference_has_authoritative_binding(ref_id: str, context: Dict[str, Any]) -> bool:
    return shared_reference_has_authoritative_binding(
        ref_id,
        context.get("reference_manifest", {}),
        context.get("governance_registry", {}),
    )


def module_has_authoritative_binding(module_id: str, context: Dict[str, Any]) -> bool:
    binding_registry = context.get("rule_binding_registry", {})
    module_bindings = binding_registry.get("authoritative_module_bindings", {})
    binding = module_bindings.get(module_id, {})
    if not isinstance(binding, dict) or binding.get("status") != "BOUND":
        return False
    evidence_paths = binding.get("evidence_paths", [])
    return isinstance(evidence_paths, list) and bool(evidence_paths)


def derive_contract_status(module_id: str, predicate_results: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
    all_pass = all(r["passed"] for r in predicate_results)
    any_pass = any(r["passed"] for r in predicate_results)
    surrogate_limitations = surrogate_limitations_for_module(module_id, context)
    if all_pass:
        if surrogate_limitations:
            return "RECOVERY_INTERIM"
        if module_id in VISIBLE_SOURCE_WORKING_PATCH_MODULES and not module_has_authoritative_binding(
            module_id,
            context,
        ):
            return "WORKING_PATCH"
        return "AUTHORITATIVE_CLOSURE"
    if module_id in AUTHORITATIVE_DEPENDENT_MODULES.union(VISIBLE_SOURCE_WORKING_PATCH_MODULES) and any_pass:
        return "WORKING_PATCH"
    return "BLOCKED"


def evaluate_module_closure_contracts(
    root: Path,
    contracts_path: Path,
    context: Dict[str, Any],
    output_path: Path,
) -> Dict[str, Any]:
    contracts = load_json(contracts_path)
    modules_out: List[Dict[str, Any]] = []
    for contract in contracts.get("contracts", []):
        module_id = contract.get("module_id", "")
        if not module_id.startswith(("M", "S")):
            continue
        predicate_results: List[Dict[str, Any]] = []
        for pred in contract.get("required_predicates", []):
            passed, detail = evaluate_contract_predicate(
                module_id,
                pred.get("predicate_id", ""),
                pred.get("target", ""),
                root,
                context,
            )
            predicate_results.append(
                {
                    "predicate_id": pred.get("predicate_id", ""),
                    "description": pred.get("description", ""),
                    "passed": passed,
                    "detail": detail,
                }
            )
        derived_status = derive_contract_status(module_id, predicate_results, context)
        module_record = {
            "module_id": module_id,
            "derived_status": derived_status,
            "passing_predicates": [r["predicate_id"] for r in predicate_results if r["passed"]],
            "failing_predicates": [r["predicate_id"] for r in predicate_results if not r["passed"]],
            "predicate_results": predicate_results,
        }
        surrogate_limitations = surrogate_limitations_for_module(module_id, context)
        if surrogate_limitations:
            module_record["closure_limitations"] = surrogate_limitations
        modules_out.append(module_record)

    report = {
        **artifact_report_header("QDP_V10_6_MODULE_CLOSURE_EVALUATION_REPORT"),
        "contract_source": str(contracts_path),
        "modules": modules_out,
    }
    dump_json(output_path, report)
    return report


def update_contracts_current_assessment(contracts_path: Path, evaluation_report: Dict[str, Any]) -> Dict[str, Any]:
    contracts = load_json(contracts_path)
    by_module = {m["module_id"]: m for m in evaluation_report.get("modules", [])}
    for contract in contracts.get("contracts", []):
        module_id = contract.get("module_id", "")
        if module_id not in by_module:
            continue
        ev = by_module[module_id]
        contract["current_assessment"] = {
            "derived_status": ev["derived_status"],
            "passing_predicates": ev.get("passing_predicates", []),
            "failing_predicates": ev.get("failing_predicates", []),
            "reason": "Derived from QDP_V10_6_MODULE_CLOSURE_EVALUATION_REPORT.",
        }
    dump_json(contracts_path, contracts)
    return contracts


def update_rule_binding_registry(
    registry_path: Path,
    harness_path: Path,
    divergence_report_path: Path,
) -> Dict[str, Any]:
    registry = load_json(registry_path)
    source_artifacts = registry.setdefault("source_artifacts", {})
    canonical_sources = {
        "build_spec": BUILD_SPEC,
        "master_spec": MASTER_SPEC,
        "validation_gate": VALIDATION_GATE,
        "reference_manifest": REFERENCE_MANIFEST,
        "schema": SCHEMA,
        "stage_machine": MODULES["m05"]["runner"],
        "reference_resolver": MODULES["m03"]["runner"],
        "schema_validator": CANDIDATE_VALIDATOR,
        "missing_retained_runtime": RETAINED_OPERATIVE_BODY,
        "bootstrap_harness": harness_path,
        "mode_divergence_report": divergence_report_path,
    }
    for key, path in canonical_sources.items():
        record = {"path": repo_rel(path)}
        if path.exists():
            record["sha256"] = sha256_file(path)
        source_artifacts[key] = record

    for rule in registry.get("rules", []):
        rid = rule.get("rule_id", "")
        bindings = rule.get("enforcement_bindings", [])
        if rid == "REFERENCE_STRICT_003":
            for b in bindings:
                if b.get("class") == "HARNESS_ENFORCED":
                    b["implementation"] = "modules/m06_bootstrap_harness/runner.py executes strict ordinary/subsystem reference-resolution and records failure in governance self check"
                    b["status"] = "BOUND"
            rule["coverage_status"] = "BOUND"
        elif rid == "GOVERNANCE_SELFCHECK_009":
            for b in bindings:
                if b.get("class") == "HARNESS_ENFORCED":
                    b["implementation"] = "modules/m06_bootstrap_harness/runner.py verifies governance_self_check field presence and mirror consistency across bootstrap outputs"
                    b["status"] = "BOUND"
            rule["coverage_status"] = "BOUND"
        elif rid == "MODE_CORE_IMMUTABILITY_010":
            for b in bindings:
                if b.get("class") == "HARNESS_ENFORCED":
                    b["implementation"] = "modules/m06_bootstrap_harness/runner.py emits artifacts/reports/system/mode_divergence_report.json and fails if shared core fields diverge without exception"
                    b["status"] = "BOUND"
            rule["coverage_status"] = "BOUND"
        elif rid == "RUNTIME_NO_LOSS_001":
            for b in bindings:
                if b.get("class") == "HARNESS_ENFORCED":
                    b["implementation"] = "modules/m06_bootstrap_harness/runner.py checks runtime prompt presence, forbidden shorthand, and mandatory retained section presence when the runtime artifact exists"
                    b["status"] = "BOUND"
            # Overall coverage still blocked by missing retained runtime source.
            rule["coverage_status"] = "BLOCKED_BY_MISSING_SOURCE"

    counts = {"BOUND": 0, "PARTIALLY_BOUND": 0, "UNBOUND": 0, "BLOCKED_BY_MISSING_SOURCE": 0}
    for rule in registry.get("rules", []):
        status = rule.get("coverage_status", "")
        if status in counts:
            counts[status] += 1
    registry["coverage_summary"] = {
        **counts,
        "note": "Coverage summary counts terminal coverage_status values after M06 harness integration.",
    }
    dump_json(registry_path, registry)
    return registry


def update_mode_divergence_policy(policy_path: Path, divergence_report: Dict[str, Any]) -> Dict[str, Any]:
    policy = load_json(policy_path)
    policy["current_assessment"] = {
        "status": "POLICY_ENFORCED" if divergence_report.get("status") == "PASSED" else "POLICY_ENFORCED_WITH_FAILURE",
        "observed_risk": "Ordinary/subsystem shared-core divergence is now checked by artifacts/reports/system/mode_divergence_report.json rather than inferred narratively.",
        "last_report_path": repo_rel(MODE_DIVERGENCE_REPORT),
        "last_report_status": divergence_report.get("status", ""),
        "next_enforcement_target": "Wire divergence failure into broader ordinary-testing resume automation once M07-M15 exist.",
    }
    dump_json(policy_path, policy)
    return policy


def update_module_registry(
    registry_json_path: Path,
    registry_md_path: Path,
    closure_by_module: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    registry = load_json(registry_json_path)
    for module in registry.get("modules", []):
        module_id = module.get("module_id")
        if module_id in closure_by_module:
            module["derived_closure_status"] = closure_by_module[module_id].get("derived_status", "BLOCKED")
        if module_id in {"M06", "M07", "M08", "M09", "M10"}:
            module["status"] = closure_by_module.get(module_id, {}).get("derived_status", module.get("status", "BLOCKED"))
    dump_json(registry_json_path, registry)

    text = registry_md_path.read_text(encoding="utf-8")
    old = "| M06 | Bootstrap harness runner and fixture loader | ordinary + subsystem | Execute five canonical harness cases and set deterministic readiness state | `specs/core/build_spec.md` | `validation_harness_status`; `determinism_status`; `system_status`; fixture manifests; expected-outcome matcher | harness spec present in build spec; fixtures and runner missing |"
    m06_status = closure_by_module.get("M06", {}).get("derived_status", "BLOCKED")
    if m06_status == "AUTHORITATIVE_CLOSURE":
        new = "| M06 | Bootstrap harness runner and fixture loader | ordinary + subsystem | Execute five canonical harness cases and set deterministic readiness state | `specs/core/build_spec.md` | `validation_harness_status`; `determinism_status`; `system_status`; fixture manifests; expected-outcome matcher | harness runner, canonical fixtures, deterministic bootstrap report, and divergence report now exist; module closed, but environment still blocked by remaining resume-policy modules |"
    else:
        new = "| M06 | Bootstrap harness runner and fixture loader | ordinary + subsystem | Execute five canonical harness cases and set deterministic readiness state | `specs/core/build_spec.md` | `validation_harness_status`; `determinism_status`; `system_status`; fixture manifests; expected-outcome matcher | harness runner, canonical fixtures, deterministic bootstrap report, and divergence report now exist; closure is recovery-interim because retained dependencies currently resolve through regenerated surrogate artifacts |"
    if old in text:
        text = text.replace(old, new)
    else:
        if "fixtures and runner missing" in text:
            text = text.replace("fixtures and runner missing", new.split("|")[-2].strip())

    old_m07 = "| M07 | Family-class triage and signature-to-bath scorer | ordinary + subsystem | Rank likely mechanism classes and choose minimal discriminant measurement before parameter expansion | `specs/core/bath_glossary.md`; `specs/core/signature_to_bath_decision_chart.md`; `config/schema/candidate_template.json` | `declared_family_class`; `assigned_family_class`; `family_class_mismatch`; `inferred_bath_rank_order`; `signature_matches`; `minimal_discriminant_measurement` | source docs present; scorer missing |"
    m07_status = closure_by_module.get("M07", {}).get("derived_status", "BLOCKED")
    if m07_status == "AUTHORITATIVE_CLOSURE":
        new_m07 = "| M07 | Family-class triage and signature-to-bath scorer | ordinary + subsystem | Rank likely mechanism classes and choose minimal discriminant measurement before parameter expansion | `specs/core/bath_glossary.md`; `specs/core/signature_to_bath_decision_chart.md`; `config/schema/candidate_template.json` | `declared_family_class`; `assigned_family_class`; `family_class_mismatch`; `inferred_bath_rank_order`; `signature_matches`; `minimal_discriminant_measurement` | surfaced scorer, self-test pack, and schema-valid outputs now exist; module closed from visible source set |"
    elif m07_status == "WORKING_PATCH":
        new_m07 = "| M07 | Family-class triage and signature-to-bath scorer | ordinary + subsystem | Rank likely mechanism classes and choose minimal discriminant measurement before parameter expansion | `specs/core/bath_glossary.md`; `specs/core/signature_to_bath_decision_chart.md`; `config/schema/candidate_template.json` | `declared_family_class`; `assigned_family_class`; `family_class_mismatch`; `inferred_bath_rank_order`; `signature_matches`; `minimal_discriminant_measurement` | visible-source scorer, self-test pack, and schema-valid outputs now exist; working patch only and not resume-authoritative |"
    else:
        new_m07 = old_m07
    if old_m07 in text:
        text = text.replace(old_m07, new_m07)

    old_m08 = "| M08 | Baseline GKSL fit and drift-aware residual diagnostics | ordinary + subsystem | Fit baseline Lindblad/GKSL null model jointly and test residual structure on time-series observables | `specs/core/model_spec.md`; `specs/research/deep_research_report.md`; `config/schema/candidate_template.json` | `baseline_model.*`; `residual_analysis.*`; drift-aware fit outputs; whiteness/stationarity diagnostics | baseline spec present; implementation missing |"
    m08_status = closure_by_module.get("M08", {}).get("derived_status", "BLOCKED")
    if m08_status == "AUTHORITATIVE_CLOSURE":
        new_m08 = "| M08 | Baseline GKSL fit and drift-aware residual diagnostics | ordinary + subsystem | Fit baseline Lindblad/GKSL null model jointly and test residual structure on time-series observables | `specs/core/model_spec.md`; `specs/research/deep_research_report.md`; `config/schema/candidate_template.json` | `baseline_model.*`; `residual_analysis.*`; drift-aware fit outputs; whiteness/stationarity diagnostics | surfaced baseline-fit runner, self-test pack, and schema-valid outputs now exist; module closed from visible source set |"
    elif m08_status == "WORKING_PATCH":
        new_m08 = "| M08 | Baseline GKSL fit and drift-aware residual diagnostics | ordinary + subsystem | Fit baseline Lindblad/GKSL null model jointly and test residual structure on time-series observables | `specs/core/model_spec.md`; `specs/research/deep_research_report.md`; `config/schema/candidate_template.json` | `baseline_model.*`; `residual_analysis.*`; drift-aware fit outputs; whiteness/stationarity diagnostics | visible-source baseline-fit runner, self-test pack, and schema-valid outputs now exist; working patch only and not resume-authoritative |"
    else:
        new_m08 = old_m08
    if old_m08 in text:
        text = text.replace(old_m08, new_m08)

    old_m09 = "| M09 | Known-mechanism competition suite | ordinary + subsystem | Evaluate parsimonious physical mechanisms before Hamiltonian escalation | `specs/core/signature_to_bath_decision_chart.md`; `QDP_Vortex_Pinning_Microwave_Loss_Module.md`; `vortex_entry_barrier.md`; `vortex_entry_calculator.md`; `vortex_microwave_dissipation.md`; `residual_field_estimation_dilution_fridge.md`; `config/schema/candidate_template.json` | `mechanism_tests.*`; `strongest_competing_mechanism`; mechanism score updates; rejection mapping if explained | mechanism docs partially present; unified executable suite missing |"
    m09_status = closure_by_module.get("M09", {}).get("derived_status", "BLOCKED")
    if m09_status == "AUTHORITATIVE_CLOSURE":
        new_m09 = "| M09 | Known-mechanism competition suite | ordinary + subsystem | Evaluate parsimonious physical mechanisms before Hamiltonian escalation | `specs/core/signature_to_bath_decision_chart.md`; `QDP_Vortex_Pinning_Microwave_Loss_Module.md`; `vortex_entry_barrier.md`; `vortex_entry_calculator.md`; `vortex_microwave_dissipation.md`; `residual_field_estimation_dilution_fridge.md`; `config/schema/candidate_template.json` | `mechanism_tests.*`; `strongest_competing_mechanism`; mechanism score updates; rejection mapping if explained | surfaced mechanism suite, self-test pack, and schema-valid outputs now exist; module closed from visible source set |"
    elif m09_status == "WORKING_PATCH":
        new_m09 = "| M09 | Known-mechanism competition suite | ordinary + subsystem | Evaluate parsimonious physical mechanisms before Hamiltonian escalation | `specs/core/signature_to_bath_decision_chart.md`; `QDP_Vortex_Pinning_Microwave_Loss_Module.md`; `vortex_entry_barrier.md`; `vortex_entry_calculator.md`; `vortex_microwave_dissipation.md`; `residual_field_estimation_dilution_fridge.md`; `config/schema/candidate_template.json` | `mechanism_tests.*`; `strongest_competing_mechanism`; mechanism score updates; rejection mapping if explained | visible-source partial mechanism suite, self-test pack, and schema-valid outputs now exist; working patch only and not resume-authoritative |"
    else:
        new_m09 = old_m09
    if old_m09 in text:
        text = text.replace(old_m09, new_m09)

    old_m10 = "| M10 | Artifact-equivalence audit | ordinary + subsystem | Eliminate classical/systematic explanations distinct from physical mechanisms | `specs/research/deep_research_report.md`; `specs/intake/fork_intake_form_one_page.pdf`; `config/schema/candidate_template.json` | `artifact_tests`; artifact alias summary; rejection mapping if artifact route explains data | design logic present; implementation missing |"
    m10_status = closure_by_module.get("M10", {}).get("derived_status", "BLOCKED")
    if m10_status == "AUTHORITATIVE_CLOSURE":
        new_m10 = "| M10 | Artifact-equivalence audit | ordinary + subsystem | Eliminate classical/systematic explanations distinct from physical mechanisms | `specs/research/deep_research_report.md`; `specs/intake/fork_intake_form_one_page.pdf`; `config/schema/candidate_template.json` | `artifact_tests`; artifact alias summary; rejection mapping if artifact route explains data | surfaced artifact-audit runner, self-test pack, and schema-valid outputs now exist; module closed from visible source set |"
    elif m10_status == "WORKING_PATCH":
        new_m10 = "| M10 | Artifact-equivalence audit | ordinary + subsystem | Eliminate classical/systematic explanations distinct from physical mechanisms | `specs/research/deep_research_report.md`; `specs/intake/fork_intake_form_one_page.pdf`; `config/schema/candidate_template.json` | `artifact_tests`; artifact alias summary; rejection mapping if artifact route explains data | visible-source artifact-audit runner, self-test pack, and schema-valid outputs now exist; working patch only and not resume-authoritative |"
    else:
        new_m10 = old_m10
    if old_m10 in text:
        text = text.replace(old_m10, new_m10)
    registry_md_path.write_text(text, encoding="utf-8")
    return registry


def effective_module_resume_status(
    module_id: str,
    closure_by_module: Dict[str, Dict[str, Any]],
) -> str:
    return closure_by_module.get(module_id, {}).get("derived_status", "BLOCKED")


def compute_testing_readiness(
    closure_by_module: Dict[str, Dict[str, Any]],
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    ordinary_required = policy.get("ordinary_candidate_testing_requires", [])
    subsystem_required = policy.get("subsystem_testing_requires", [])
    recovery_allowed = {"WORKING_PATCH", "RECOVERY_INTERIM", "AUTHORITATIVE_CLOSURE"}
    ordinary_authoritative_blockers = [
        module_id
        for module_id in ordinary_required
        if effective_module_resume_status(module_id, closure_by_module) != "AUTHORITATIVE_CLOSURE"
    ]
    ordinary_recovery_blockers = [
        module_id
        for module_id in ordinary_required
        if effective_module_resume_status(module_id, closure_by_module) not in recovery_allowed
    ]
    subsystem_authoritative_blockers = [
        module_id
        for module_id in subsystem_required
        if effective_module_resume_status(module_id, closure_by_module) != "AUTHORITATIVE_CLOSURE"
    ]
    subsystem_recovery_blockers = [
        module_id
        for module_id in subsystem_required
        if effective_module_resume_status(module_id, closure_by_module) not in recovery_allowed
    ]
    return {
        "ordinary_recovery_ready": not ordinary_recovery_blockers,
        "ordinary_authoritative_ready": not ordinary_authoritative_blockers,
        "ordinary_testing_ready": not ordinary_authoritative_blockers,
        "subsystem_recovery_ready": not subsystem_recovery_blockers,
        "subsystem_authoritative_ready": not subsystem_authoritative_blockers,
        "subsystem_testing_ready": not subsystem_authoritative_blockers,
        "ordinary_recovery_blockers": ordinary_recovery_blockers,
        "ordinary_authoritative_blockers": ordinary_authoritative_blockers,
        "ordinary_testing_blockers": ordinary_authoritative_blockers,
        "subsystem_recovery_blockers": subsystem_recovery_blockers,
        "subsystem_authoritative_blockers": subsystem_authoritative_blockers,
        "subsystem_testing_blockers": subsystem_authoritative_blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QDP v10.6 M06 bootstrap harness.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--build-spec", type=Path, default=BUILD_SPEC)
    parser.add_argument("--reference-manifest", type=Path, default=REFERENCE_MANIFEST)
    parser.add_argument("--governance-registry", type=Path, default=GOVERNANCE_REGISTRY)
    parser.add_argument("--resolver", type=Path, default=MODULES["m03"]["runner"])
    parser.add_argument("--ordinary-report", type=Path, default=M03_ORDINARY_REPORT)
    parser.add_argument("--subsystem-report", type=Path, default=M03_SUBSYSTEM_REPORT)
    parser.add_argument("--base-template", type=Path, default=BASE_TEMPLATE)
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    parser.add_argument("--validator", type=Path, default=CANDIDATE_VALIDATOR)
    parser.add_argument("--stage-machine", type=Path, default=MODULES["m05"]["runner"])
    parser.add_argument("--m05-selftest-cases", type=Path, default=MODULES["m05"]["selftest_cases"])
    parser.add_argument("--m05-selftest-report", type=Path, default=MODULES["m05"]["selftest_report"])
    parser.add_argument("--m05-selftest-output-dir", type=Path, default=MODULES["m05"]["selftest_output_dir"])
    parser.add_argument("--family-triage", type=Path, default=MODULES["m07"]["runner"])
    parser.add_argument("--m07-selftest-cases", type=Path, default=MODULES["m07"]["selftest_cases"])
    parser.add_argument("--m07-selftest-report", type=Path, default=MODULES["m07"]["selftest_report"])
    parser.add_argument("--m07-selftest-output-dir", type=Path, default=MODULES["m07"]["selftest_output_dir"])
    parser.add_argument("--baseline-fit", type=Path, default=MODULES["m08"]["runner"])
    parser.add_argument("--m08-selftest-cases", type=Path, default=MODULES["m08"]["selftest_cases"])
    parser.add_argument("--m08-selftest-report", type=Path, default=MODULES["m08"]["selftest_report"])
    parser.add_argument("--m08-selftest-output-dir", type=Path, default=MODULES["m08"]["selftest_output_dir"])
    parser.add_argument("--mechanism-suite", type=Path, default=MODULES["m09"]["runner"])
    parser.add_argument("--m09-selftest-cases", type=Path, default=MODULES["m09"]["selftest_cases"])
    parser.add_argument("--m09-selftest-report", type=Path, default=MODULES["m09"]["selftest_report"])
    parser.add_argument("--m09-selftest-output-dir", type=Path, default=MODULES["m09"]["selftest_output_dir"])
    parser.add_argument("--artifact-audit-suite", type=Path, default=MODULES["m10"]["runner"])
    parser.add_argument("--m10-selftest-cases", type=Path, default=MODULES["m10"]["selftest_cases"])
    parser.add_argument("--m10-selftest-report", type=Path, default=MODULES["m10"]["selftest_report"])
    parser.add_argument("--m10-selftest-output-dir", type=Path, default=MODULES["m10"]["selftest_output_dir"])
    parser.add_argument("--m06-cases", type=Path, default=MODULES["m06"]["bootstrap_cases"])
    parser.add_argument("--m06-output-dir", type=Path, default=MODULES["m06"]["output_dir"])
    parser.add_argument("--rule-binding-registry", type=Path, default=RULE_BINDING_REGISTRY)
    parser.add_argument("--closure-contracts", type=Path, default=MODULE_CLOSURE_CONTRACTS)
    parser.add_argument("--mode-divergence-policy", type=Path, default=MODE_DIVERGENCE_POLICY)
    parser.add_argument("--mode-divergence-report", type=Path, default=MODE_DIVERGENCE_REPORT)
    parser.add_argument("--closure-evaluation-report", type=Path, default=MODULE_CLOSURE_EVALUATION_REPORT)
    parser.add_argument("--write-report", type=Path, default=MODULES["m06"]["bootstrap_report"])
    parser.add_argument("--write-closure-report", type=Path, default=MODULES["m06"]["closure_report"])
    parser.add_argument("--module-registry-json", type=Path, default=MODULE_REGISTRY_JSON)
    parser.add_argument("--module-registry-md", type=Path, default=MODULE_REGISTRY_MD)
    args = parser.parse_args()

    root = args.root
    root.mkdir(parents=True, exist_ok=True)
    args.m06_output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Strict reference-resolution refresh.
    ordinary_cmd = [
        sys.executable,
        str(args.resolver),
        "--manifest",
        str(args.reference_manifest),
        "--registry",
        str(args.governance_registry),
        "--root",
        str(root),
        "--mode",
        "ordinary",
        "--write-report",
        str(args.ordinary_report),
    ]
    subsystem_cmd = [
        sys.executable,
        str(args.resolver),
        "--manifest",
        str(args.reference_manifest),
        "--registry",
        str(args.governance_registry),
        "--root",
        str(root),
        "--mode",
        "subsystem",
        "--write-report",
        str(args.subsystem_report),
    ]
    ordinary_exec = run_cmd(ordinary_cmd)
    subsystem_exec = run_cmd(subsystem_cmd)
    if not ordinary_exec["ok"] or not subsystem_exec["ok"]:
        print(json.dumps({"ordinary_exec": ordinary_exec, "subsystem_exec": subsystem_exec}, indent=2))
        return 1

    ordinary_report = load_json(args.ordinary_report)
    subsystem_report = load_json(args.subsystem_report)
    reference_manifest = load_json(args.reference_manifest)
    governance_registry = update_governance_registry_with_reports(args.governance_registry, ordinary_report, subsystem_report)

    # 2. Schema template validation.
    template_validation = run_cmd([
        sys.executable,
        str(args.validator),
        str(args.base_template),
        "--mode",
        "template",
        "--schema",
        str(args.schema),
    ])

    # 3. Core-module self-test refresh.
    module_selftest_results = run_module_selftests(SELFTEST_MODULE_KEYS)

    m01_selftest_report = module_selftest_results["m01"]["report"]
    m02_selftest_report = module_selftest_results["m02"]["report"]
    m04_selftest_report = module_selftest_results["m04"]["report"]
    m05_selftest_exec = module_selftest_results["m05"]["execution"]
    m05_selftest_report = module_selftest_results["m05"]["report"]
    m07_selftest_exec = module_selftest_results["m07"]["execution"]
    m07_selftest_report = module_selftest_results["m07"]["report"]
    m08_selftest_exec = module_selftest_results["m08"]["execution"]
    m08_selftest_report = module_selftest_results["m08"]["report"]
    m09_selftest_exec = module_selftest_results["m09"]["execution"]
    m09_selftest_report = module_selftest_results["m09"]["report"]
    m10_selftest_exec = module_selftest_results["m10"]["execution"]
    m10_selftest_report = module_selftest_results["m10"]["report"]
    m11_selftest_report = module_selftest_results["m11"]["report"]
    m12_selftest_report = module_selftest_results["m12"]["report"]
    m13_selftest_report = module_selftest_results["m13"]["report"]
    m14_selftest_report = module_selftest_results["m14"]["report"]
    m15_selftest_report = module_selftest_results["m15"]["report"]

    # 4. M06 canonical bootstrap cases.
    m05_module = load_module(args.stage_machine, "qdp_m05_stage_machine")
    base_template = load_json(args.base_template)
    m06_cases = load_json(args.m06_cases)
    bootstrap_case_report = run_bootstrap_cases(
        m05_module,
        base_template,
        m06_cases,
        args.validator,
        args.schema,
        args.m06_output_dir,
    )

    # 5. Runtime integrity and mode divergence.
    runtime_integrity = runtime_integrity_check(root, args.build_spec)
    emit_m01_closure_report(root, reference_manifest, runtime_integrity, M01_CLOSURE_REPORT)
    divergence_report = build_mode_divergence_report(
        root,
        args.mode_divergence_policy,
        args.reference_manifest,
        args.ordinary_report,
        args.subsystem_report,
        args.mode_divergence_report,
    )

    # 6. Typed statuses for current environment.
    reference_resolution_status = "PASSED" if (
        ordinary_report.get("critical_unresolved_count", 0) == 0 and subsystem_report.get("critical_unresolved_count", 0) == 0
    ) else "FAILED"

    all_module_selftests_valid = all(
        result.get("execution", {}).get("ok", False)
        and report_all_passed(result.get("report", {}))
        and report_all_validator_valid(result.get("report", {}))
        for result in module_selftest_results.values()
    )

    schema_validation_status = "PASSED" if (
        template_validation["ok"]
        and bootstrap_case_report.get("all_cases_exact_match_all_runs", False)
        and all(
            case.get("validator_result", {}).get("valid", False)
            for run in bootstrap_case_report.get("runs", [])
            for case in run.get("results", [])
        )
        and all_module_selftests_valid
    ) else "FAILED"

    validation_harness_status = "PASSED" if bootstrap_case_report.get("all_cases_exact_match_all_runs", False) else "FAILED"
    determinism_status = "PASSED" if bootstrap_case_report.get("deterministic_across_repeated_runs", False) else "FAILED"

    governance_self_diagnostic = {
        "validation_harness_status": validation_harness_status,
        "schema_validation_status": schema_validation_status,
        "reference_resolution_status": reference_resolution_status,
        "determinism_status": determinism_status,
        "system_status": "",
    }
    governance_self_diagnostic["system_status"] = derive_system_status(governance_self_diagnostic)

    governance_self_diagnostic_check = {
        "fields_present_in_all_bootstrap_outputs": all(
            case.get("governance_self_check_ok", False)
            for run in bootstrap_case_report.get("runs", [])
            for case in run.get("results", [])
        ),
        "mirror_consistency_in_all_bootstrap_outputs": all(
            case.get("governance_self_check_ok", False)
            for run in bootstrap_case_report.get("runs", [])
            for case in run.get("results", [])
        ),
        "enum_validity_enforced_via_schema": schema_validation_status == "PASSED",
    }
    governance_self_diagnostic_check["passed"] = all(governance_self_diagnostic_check.values())

    # 7. Closure evaluation and dynamic artifact updates.
    bootstrap_verification_state = {
        "validation_harness_status": validation_harness_status,
        "determinism_status": determinism_status,
        "reference_resolution_status": reference_resolution_status,
        "schema_validation_status": schema_validation_status,
    }
    module_verification_checks = build_module_verification_checks(
        module_selftest_results,
        ordinary_report,
        subsystem_report,
        bootstrap_verification_state,
        divergence_report,
    )
    module_selftest_alias = build_module_selftest_alias(module_verification_checks)
    preliminary_report = {
        **module_report_header("QDP_V10_6_M06_BOOTSTRAP_REPORT", "M06"),
        "checks": {
            "reference_resolution": {
                "ordinary_report_path": str(args.ordinary_report),
                "subsystem_report_path": str(args.subsystem_report),
                "ordinary_status": ordinary_report.get("reference_resolution_status", ""),
                "subsystem_status": subsystem_report.get("reference_resolution_status", ""),
                "ordinary_critical_unresolved_count": ordinary_report.get("critical_unresolved_count", 0),
                "subsystem_critical_unresolved_count": subsystem_report.get("critical_unresolved_count", 0),
                "passed": reference_resolution_status == "PASSED",
            },
            "schema_validation": {
                "template_validation": template_validation,
                "bootstrap_case_outputs_valid": all(
                    case.get("validator_result", {}).get("valid", False)
                    for run in bootstrap_case_report.get("runs", [])
                    for case in run.get("results", [])
                ),
                "module_selftests_all_valid": all_module_selftests_valid,
                "m01_selftests_all_valid": report_all_passed(m01_selftest_report),
                "m02_selftests_all_valid": report_all_passed(m02_selftest_report),
                "m04_selftests_all_valid": report_all_passed(m04_selftest_report),
                "m05_selftests_all_valid": report_all_passed(m05_selftest_report),
                "m07_selftests_all_valid": report_all_passed(m07_selftest_report),
                "m08_selftests_all_valid": report_all_passed(m08_selftest_report),
                "m09_selftests_all_valid": report_all_passed(m09_selftest_report),
                "m10_selftests_all_valid": report_all_passed(m10_selftest_report),
                "m11_selftests_all_valid": report_all_passed(m11_selftest_report),
                "m12_selftests_all_valid": report_all_passed(m12_selftest_report),
                "m13_selftests_all_valid": report_all_passed(m13_selftest_report),
                "m14_selftests_all_valid": report_all_passed(m14_selftest_report),
                "m15_selftests_all_valid": report_all_passed(m15_selftest_report),
                "passed": schema_validation_status == "PASSED",
            },
            "module_verification": module_verification_checks,
            "module_selftests": module_selftest_alias,
            "module_selftests_note": "Deprecated compatibility alias of checks.module_verification.",
            "stage_machine_selftests": module_selftest_alias.get("M05", {}),
            "family_triage_selftests": module_selftest_alias.get("M07", {}),
            "baseline_fit_selftests": module_selftest_alias.get("M08", {}),
            "mechanism_competition_selftests": module_selftest_alias.get("M09", {}),
            "artifact_equivalence_selftests": module_selftest_alias.get("M10", {}),
            "governance_self_diagnostic": governance_self_diagnostic_check,
            "runtime_integrity": runtime_integrity,
            "mode_divergence": {
                "report_path": str(args.mode_divergence_report),
                "status": divergence_report.get("status", ""),
                "shared_field_override_detected": divergence_report.get("shared_field_override_detected", False),
                "passed": divergence_report.get("status") == "PASSED",
            },
            "rule_binding_summary": load_json(args.rule_binding_registry).get("coverage_summary", {}),
        },
        "bootstrap_cases": bootstrap_case_report,
        "validation_harness_status": validation_harness_status,
        "determinism_status": determinism_status,
        "reference_resolution_status": reference_resolution_status,
        "schema_validation_status": schema_validation_status,
        "system_status": governance_self_diagnostic["system_status"],
        "promotion_cap_governance": "SANDBOX_ONLY" if reference_resolution_status == "FAILED" else "",
        "ordinary_recovery_ready": False,
        "ordinary_authoritative_ready": False,
        "ordinary_testing_ready": False,
        "subsystem_recovery_ready": False,
        "subsystem_authoritative_ready": False,
        "subsystem_testing_ready": False,
    }

    # Write once so closure predicates can inspect the file.
    dump_json(args.write_report, preliminary_report)

    context = {
        "runtime_integrity": runtime_integrity,
        "ordinary_reference_report": ordinary_report,
        "subsystem_reference_report": subsystem_report,
        "governance_registry": governance_registry,
        "rule_binding_registry": load_json(args.rule_binding_registry),
        "module_selftests": {
            MODULES[module_key]["module_id"]: result
            for module_key, result in module_selftest_results.items()
        },
        "m01_selftest_report": m01_selftest_report,
        "m02_selftest_report": m02_selftest_report,
        "m04_selftest_report": m04_selftest_report,
        "m05_selftest_report": m05_selftest_report,
        "m07_selftest_report": m07_selftest_report,
        "m08_selftest_report": m08_selftest_report,
        "m09_selftest_report": m09_selftest_report,
        "m10_selftest_report": m10_selftest_report,
        "m11_selftest_report": m11_selftest_report,
        "m12_selftest_report": m12_selftest_report,
        "m13_selftest_report": m13_selftest_report,
        "m14_selftest_report": m14_selftest_report,
        "m15_selftest_report": m15_selftest_report,
        "m06_bootstrap_report": preliminary_report,
        "mode_divergence_report": divergence_report,
        "reference_manifest": reference_manifest,
    }
    closure_evaluation = evaluate_module_closure_contracts(
        root,
        args.closure_contracts,
        context,
        args.closure_evaluation_report,
    )
    update_contracts_current_assessment(args.closure_contracts, closure_evaluation)
    updated_rule_binding = update_rule_binding_registry(args.rule_binding_registry, Path(__file__), args.mode_divergence_report)
    updated_policy = update_mode_divergence_policy(args.mode_divergence_policy, divergence_report)

    # Refresh embedded rule-binding summary after registry update.
    closure_by_module = {m["module_id"]: m for m in closure_evaluation.get("modules", [])}
    testing_readiness = compute_testing_readiness(closure_by_module, policy=RESUME_POLICY)
    write_module_registry(
        args.module_registry_json,
        args.module_registry_md,
        closure_by_module,
        testing_readiness,
    )
    final_report = load_json(args.write_report)
    final_report["checks"]["rule_binding_summary"] = updated_rule_binding.get("coverage_summary", {})
    final_report["module_closure_evaluation_report_path"] = str(args.closure_evaluation_report)
    final_report["governance_self_check"] = governance_self_diagnostic
    final_report["ordinary_recovery_ready"] = testing_readiness["ordinary_recovery_ready"]
    final_report["ordinary_authoritative_ready"] = testing_readiness["ordinary_authoritative_ready"]
    final_report["ordinary_testing_ready"] = testing_readiness["ordinary_testing_ready"]
    final_report["subsystem_recovery_ready"] = testing_readiness["subsystem_recovery_ready"]
    final_report["subsystem_authoritative_ready"] = testing_readiness["subsystem_authoritative_ready"]
    final_report["subsystem_testing_ready"] = testing_readiness["subsystem_testing_ready"]
    final_report["ordinary_recovery_blockers"] = testing_readiness["ordinary_recovery_blockers"]
    final_report["ordinary_authoritative_blockers"] = testing_readiness["ordinary_authoritative_blockers"]
    final_report["ordinary_testing_blockers"] = testing_readiness["ordinary_testing_blockers"]
    final_report["subsystem_recovery_blockers"] = testing_readiness["subsystem_recovery_blockers"]
    final_report["subsystem_authoritative_blockers"] = testing_readiness["subsystem_authoritative_blockers"]
    final_report["subsystem_testing_blockers"] = testing_readiness["subsystem_testing_blockers"]
    dump_json(args.write_report, final_report)

    m06_closure = closure_by_module.get("M06", {})
    m06_notes = [
        "M06 closure is computed from config/contracts/module_closure_contracts.json.",
    ]
    if m06_closure.get("derived_status") == "RECOVERY_INTERIM":
        m06_notes.append("Closure is downgraded to RECOVERY_INTERIM because retained dependencies currently resolve through regenerated local surrogate artifacts.")
    if final_report.get("system_status") != "READY":
        m06_notes.append("Module closure does not imply runtime readiness; consult system_status in the bootstrap report.")
    if not testing_readiness["ordinary_testing_ready"] or not testing_readiness["subsystem_testing_ready"]:
        m06_notes.append("Resume-testing readiness still follows the module-registry policy and remains false until the required module sets close authoritatively.")
    m06_closure_report = {
        **module_report_header("QDP_V10_6_M06_CLOSURE_REPORT", "M06"),
        "derived_status": m06_closure.get("derived_status", "BLOCKED"),
        "predicate_results": m06_closure.get("predicate_results", []),
        "bootstrap_report_path": str(args.write_report),
        "mode_divergence_report_path": str(args.mode_divergence_report),
        "notes": m06_notes,
    }
    dump_json(args.write_closure_report, m06_closure_report)

    record_run(
        operation="bootstrap",
        lane="recovery",
        status=final_report.get("system_status", "FAILED"),
        summary={
            "ordinary_recovery_ready": final_report.get("ordinary_recovery_ready", False),
            "ordinary_authoritative_ready": final_report.get("ordinary_authoritative_ready", False),
            "subsystem_recovery_ready": final_report.get("subsystem_recovery_ready", False),
            "subsystem_authoritative_ready": final_report.get("subsystem_authoritative_ready", False),
            "validation_harness_status": final_report.get("validation_harness_status", ""),
            "schema_validation_status": final_report.get("schema_validation_status", ""),
        },
        artifacts=[args.write_report, args.write_closure_report, args.closure_evaluation_report, args.module_registry_json],
    )

    print(json.dumps(final_report, indent=2))
    # Module-level success means harness exists and ran deterministically.
    return 0 if m06_closure_report.get("derived_status") in {"AUTHORITATIVE_CLOSURE", "RECOVERY_INTERIM"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

