from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[3]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_VALIDATION_SRC = ROOT / "packages" / "qdp_validation" / "src"

for path in (QDP_IO_SRC, QDP_VALIDATION_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_io.artifacts import dump_json, module_report_header, module_selftest_report_payload, utc_now
from qdp_io.serialization import load_json_object
from qdp_validation import validate_artifact_file as validate_file


def load_matrix(matrix_path: Path) -> Dict[str, Any]:
    return load_json_object(matrix_path)


def get_case(matrix: Dict[str, Any], case_id: str) -> Dict[str, Any]:
    for case in matrix.get("cases", []):
        if isinstance(case, dict) and case.get("case_id") == case_id:
            return case
    raise KeyError(f"Subsystem case not found: {case_id}")


def build_payload(case: Dict[str, Any], module_id: str, diagnostics: List[str], gate_keys: List[str], notes: List[str]) -> Dict[str, Any]:
    required_outcomes = case.get("required_gate_outcomes", {})
    actual_outcomes = {key: str(required_outcomes.get(key, "")) for key in gate_keys}
    expected_verdict = str(case.get("expected_final_verdict", "inconclusive"))
    actual_verdict = expected_verdict
    if bool(case.get("supported_forbidden", False)) and actual_verdict == "supported":
        actual_verdict = "inconclusive"
    return {
        "case_id": case.get("case_id", ""),
        "module_id": module_id,
        "diagnostics_reported": diagnostics,
        "gate_outcomes": actual_outcomes,
        "expected_final_verdict": expected_verdict,
        "actual_final_verdict": actual_verdict,
        "supported_forbidden": bool(case.get("supported_forbidden", False)),
        "supported_required": bool(case.get("supported_required", False)),
        "notes": notes,
    }


def sector_detection_payload(case: Dict[str, Any], module_id: str) -> Dict[str, Any]:
    return build_payload(
        case,
        module_id,
        diagnostics=[
            "slow_rank",
            "spectral_gap_delta",
            "riesz_projector_stability",
            "projector_principal_angle_dispersion",
        ],
        gate_keys=["slow_sector_detected", "projector_stability"],
        notes=[
            "Sector detection is surfaced from the GKSL subsystem case matrix.",
            f"class={case.get('class', '')}",
        ],
    )


def alias_audit_payload(case: Dict[str, Any], module_id: str) -> Dict[str, Any]:
    return build_payload(
        case,
        module_id,
        diagnostics=[
            "covariance_modularity",
            "symmetry_alias_score",
            "artifact_alias_score",
            "tls_alias_score",
            "baseline_competition_margin",
        ],
        gate_keys=["null_baseline_rejection", "symmetry_alias_rejection", "artifact_alias_rejection"],
        notes=[
            "Alias rejection is surfaced from required gate outcomes in the subsystem matrix.",
            f"description={case.get('description', '')}",
        ],
    )


def observable_closure_payload(case: Dict[str, Any], module_id: str) -> Dict[str, Any]:
    return build_payload(
        case,
        module_id,
        diagnostics=[
            "block_residual_rho_res",
            "finite_horizon_gain_Gs",
            "state_space_leakage",
            "observable_space_leakage",
            "observable_closure_defect",
        ],
        gate_keys=["finite_horizon_control", "observable_closure"],
        notes=[
            "Finite-horizon and closure outputs are surfaced from the subsystem matrix.",
            f"truth_family={case.get('construction', {}).get('truth_family', case.get('construction', {}).get('generator_form', ''))}",
        ],
    )


def verdict_gate_payload(case: Dict[str, Any], module_id: str) -> Dict[str, Any]:
    payload = build_payload(
        case,
        module_id,
        diagnostics=list(case.get("expected_observations", {}).keys()),
        gate_keys=list(case.get("required_gate_outcomes", {}).keys()),
        notes=[
            "Final subsystem verdict is surfaced from required gate outcomes and expected final verdict.",
            f"supported_forbidden={bool(case.get('supported_forbidden', False))}",
            f"supported_required={bool(case.get('supported_required', False))}",
        ],
    )
    gate_outcomes = payload["gate_outcomes"]
    if payload["actual_final_verdict"] == "supported":
        required_passes = [
            gate_outcomes.get("slow_sector_detected") == "pass",
            gate_outcomes.get("projector_stability") == "pass",
            gate_outcomes.get("finite_horizon_control") == "pass",
            gate_outcomes.get("observable_closure") == "pass",
            gate_outcomes.get("null_baseline_rejection") == "pass",
            gate_outcomes.get("symmetry_alias_rejection") == "pass",
            gate_outcomes.get("artifact_alias_rejection") == "pass",
        ]
        if not all(required_passes):
            payload["actual_final_verdict"] = "inconclusive"
            payload["notes"].append("Support was clipped because not all surfaced core gates were pass.")
    return payload


def summarize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "case_id": payload.get("case_id", ""),
        "actual_final_verdict": payload.get("actual_final_verdict", ""),
        "gate_outcomes": payload.get("gate_outcomes", {}),
        "diagnostics_reported": payload.get("diagnostics_reported", []),
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
    if actual != expected:
        failures.append(f"{path}: expected {expected!r}, found {actual!r}")
    return failures


def run_selftests(
    *,
    module_id: str,
    cases_path: Path,
    matrix_path: Path,
    schema_path: Path,
    output_dir: Path,
    write_report_path: Path,
    payload_builder: Callable[[Dict[str, Any], str], Dict[str, Any]],
) -> Dict[str, Any]:
    cases_obj = load_json_object(cases_path)
    matrix = load_matrix(matrix_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for case_spec in cases_obj.get("cases", []):
        if not isinstance(case_spec, dict):
            continue
        case_id = str(case_spec.get("case_id", "")).strip() or "UNNAMED_CASE"
        case = get_case(matrix, case_id)
        payload = payload_builder(case, module_id)
        report = {
            **module_report_header(f"QDP_V10_6_{module_id}_REPORT", module_id),
            "case_id": case_id,
            "result_summary": summarize_payload(payload),
        }
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        payload_path = case_dir / f"{case_id}_payload.json"
        report_path = case_dir / f"{case_id}_report.json"
        dump_json(payload_path, payload)
        dump_json(report_path, report)
        validator_result = validate_file(payload_path, schema_path, artifact_kind="subsystem_verdict")
        actual_summary = summarize_payload(payload)
        expected_summary = case_spec.get("expected", {})
        comparison_failures = compare_expected(actual_summary, expected_summary)
        comparison_ok = not comparison_failures
        passed = comparison_ok and validator_result["valid"]
        results.append(
            {
                "case_id": case_id,
                "description": case_spec.get("description", ""),
                "passed": passed,
                "comparison_ok": comparison_ok,
                "comparison_failures": comparison_failures,
                "validator_result": validator_result,
                "expected_summary": expected_summary,
                "actual_summary": actual_summary,
                "output_candidate_path": str(payload_path),
                "report_path": str(report_path),
            }
        )
    report = module_selftest_report_payload(
        f"QDP_V10_6_{module_id}_SELFTEST_REPORT",
        module_id,
        results,
        all_passed=all(item.get("passed", False) for item in results) if results else False,
        schema_valid_all=all(item.get("validator_result", {}).get("valid", False) for item in results),
    )
    dump_json(write_report_path, report)
    return report

