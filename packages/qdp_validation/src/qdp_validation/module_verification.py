from __future__ import annotations

from typing import Any, Dict

from .module_workflows import report_all_passed, report_all_validator_valid
from tools.workflow.qdp_runtime.qdp_paths import (
    M01_CLOSURE_REPORT,
    M03_ORDINARY_REPORT,
    M03_SUBSYSTEM_REPORT,
    MODE_DIVERGENCE_REPORT,
    MODULES,
    MODULE_REGISTRY_BLUEPRINTS,
)


MODULE_IDS = list(MODULE_REGISTRY_BLUEPRINTS.keys())


def _selftest_verification(module_key: str, result: Dict[str, Any]) -> Dict[str, Any]:
    meta = MODULES[module_key]
    report = result.get("report", {})
    execution = result.get("execution", {})
    all_passed = report_all_passed(report)
    validator_valid_all = report_all_validator_valid(report)
    return {
        "module_key": module_key,
        "verification_kind": "selftest_report",
        "evidence_paths": {
            "report": str(meta["selftest_report"]),
        },
        "execution": execution,
        "cases_total": int(report.get("cases_total", 0) or 0),
        "cases_passed": int(report.get("cases_passed", 0) or 0),
        "all_passed": all_passed,
        "validator_valid_all": validator_valid_all,
        "verification_passed": bool(execution.get("ok", False)) and all_passed and validator_valid_all,
    }


def _m01_verification(result: Dict[str, Any]) -> Dict[str, Any]:
    verification = _selftest_verification("m01", result)
    verification["verification_kind"] = "assembly_report"
    verification["evidence_paths"] = {
        "assembly_report": str(MODULES["m01"]["selftest_report"]),
        "closure_report": str(M01_CLOSURE_REPORT),
    }
    verification["closure_report_exists"] = M01_CLOSURE_REPORT.exists()
    verification["verification_passed"] = bool(verification["verification_passed"]) and verification["closure_report_exists"]
    return verification


def _m03_verification(
    ordinary_report: Dict[str, Any],
    subsystem_report: Dict[str, Any],
    divergence_report: Dict[str, Any],
) -> Dict[str, Any]:
    ordinary_status = str(ordinary_report.get("reference_resolution_status", "") or "")
    subsystem_status = str(subsystem_report.get("reference_resolution_status", "") or "")
    ordinary_critical_unresolved = int(ordinary_report.get("critical_unresolved_count", 0) or 0)
    subsystem_critical_unresolved = int(subsystem_report.get("critical_unresolved_count", 0) or 0)
    mode_divergence_status = str(divergence_report.get("status", "") or "")
    return {
        "module_key": "m03",
        "verification_kind": "reference_resolution",
        "evidence_paths": {
            "ordinary_report": str(M03_ORDINARY_REPORT),
            "subsystem_report": str(M03_SUBSYSTEM_REPORT),
            "mode_divergence_report": str(MODE_DIVERGENCE_REPORT),
        },
        "ordinary_status": ordinary_status,
        "subsystem_status": subsystem_status,
        "ordinary_critical_unresolved_count": ordinary_critical_unresolved,
        "subsystem_critical_unresolved_count": subsystem_critical_unresolved,
        "mode_divergence_status": mode_divergence_status,
        "verification_passed": (
            ordinary_status == "PASSED"
            and subsystem_status == "PASSED"
            and ordinary_critical_unresolved == 0
            and subsystem_critical_unresolved == 0
            and mode_divergence_status == "PASSED"
        ),
    }


def _m06_verification(
    bootstrap_report: Dict[str, Any],
    divergence_report: Dict[str, Any],
) -> Dict[str, Any]:
    validation_harness_status = str(bootstrap_report.get("validation_harness_status", "") or "")
    schema_validation_status = str(bootstrap_report.get("schema_validation_status", "") or "")
    reference_resolution_status = str(bootstrap_report.get("reference_resolution_status", "") or "")
    determinism_status = str(bootstrap_report.get("determinism_status", "") or "")
    mode_divergence_status = str(divergence_report.get("status", "") or "")
    return {
        "module_key": "m06",
        "verification_kind": "bootstrap_harness",
        "evidence_paths": {
            "bootstrap_report": str(MODULES["m06"]["bootstrap_report"]),
            "closure_report": str(MODULES["m06"]["closure_report"]),
            "mode_divergence_report": str(MODE_DIVERGENCE_REPORT),
        },
        "validation_harness_status": validation_harness_status,
        "schema_validation_status": schema_validation_status,
        "reference_resolution_status": reference_resolution_status,
        "determinism_status": determinism_status,
        "mode_divergence_status": mode_divergence_status,
        "verification_passed": (
            validation_harness_status == "PASSED"
            and schema_validation_status == "PASSED"
            and reference_resolution_status == "PASSED"
            and determinism_status == "PASSED"
            and mode_divergence_status == "PASSED"
        ),
    }


def build_module_verification_checks(
    module_selftest_results: Dict[str, Dict[str, Any]],
    ordinary_report: Dict[str, Any],
    subsystem_report: Dict[str, Any],
    bootstrap_report: Dict[str, Any],
    divergence_report: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    checks: Dict[str, Dict[str, Any]] = {}
    for module_key, result in module_selftest_results.items():
        module_id = MODULES[module_key]["module_id"]
        if module_id == "M01":
            checks[module_id] = _m01_verification(result)
            continue
        checks[module_id] = _selftest_verification(module_key, result)

    checks["M03"] = _m03_verification(ordinary_report, subsystem_report, divergence_report)
    checks["M06"] = _m06_verification(bootstrap_report, divergence_report)
    return {
        module_id: checks[module_id]
        for module_id in MODULE_IDS
        if module_id in checks
    }


def build_module_selftest_alias(module_verification: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    alias: Dict[str, Dict[str, Any]] = {}
    for module_id in MODULE_IDS:
        entry = module_verification.get(module_id)
        if not isinstance(entry, dict):
            continue
        evidence_paths = entry.get("evidence_paths", {})
        report_path = ""
        for key in ("report", "assembly_report", "bootstrap_report", "ordinary_report"):
            candidate = evidence_paths.get(key)
            if isinstance(candidate, str) and candidate:
                report_path = candidate
                break
        all_passed = bool(entry.get("all_passed", entry.get("verification_passed", False)))
        cases_total = int(entry.get("cases_total", 0) or 0)
        alias[module_id] = {
            "module_key": str(entry.get("module_key", module_id.lower())),
            "verification_kind": str(entry.get("verification_kind", "") or ""),
            "evidence_paths": evidence_paths,
            "execution": entry.get(
                "execution",
                {
                    "ok": bool(entry.get("verification_passed", False)),
                    "mode": "compatibility_alias",
                },
            ),
            "report_path": report_path,
            "cases_total": cases_total,
            "cases_passed": int(entry.get("cases_passed", cases_total if all_passed else 0) or 0),
            "all_passed": all_passed,
            "validator_valid_all": bool(entry.get("validator_valid_all", entry.get("verification_passed", False))),
            "verification_passed": bool(entry.get("verification_passed", False)),
        }
    return alias


def module_verification_from_bootstrap(bootstrap_report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    checks = bootstrap_report.get("checks", {}) if isinstance(bootstrap_report, dict) else {}
    module_verification = checks.get("module_verification", {})
    if isinstance(module_verification, dict):
        return module_verification
    module_selftests = checks.get("module_selftests", {})
    return module_selftests if isinstance(module_selftests, dict) else {}


__all__ = [
    "build_module_verification_checks",
    "build_module_selftest_alias",
    "module_verification_from_bootstrap",
]
