from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List

from tools.workflow.qdp_runtime.qdp_module_sdk import module_keys_with_selftests, selftest_module


def module_selftest_keys() -> List[str]:
    return module_keys_with_selftests()


def run_module_selftest(module_key: str) -> Dict[str, Any]:
    return selftest_module(module_key)


def run_module_selftests(module_keys: Iterable[str], *, max_workers: int = 8) -> Dict[str, Dict[str, Any]]:
    ordered = list(module_keys)
    if not ordered:
        return {}
    workers = max(1, min(max_workers, len(ordered)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(run_module_selftest, ordered))
    return {result["module_key"]: result for result in results}


def report_all_passed(report: Dict[str, Any]) -> bool:
    if not isinstance(report, dict):
        return False
    return bool(report.get("all_passed", False))


def report_all_validator_valid(report: Dict[str, Any]) -> bool:
    if not isinstance(report, dict):
        return False
    if "schema_valid_all" in report:
        return bool(report.get("schema_valid_all", False))
    cases = report.get("cases", [])
    if not isinstance(cases, list):
        return False
    valid_cases = []
    for case in cases:
        if not isinstance(case, dict):
            return False
        validator_result = case.get("validator_result")
        if validator_result is None:
            continue
        valid_cases.append(bool(validator_result.get("valid", False)))
    return all(valid_cases) if valid_cases else bool(report.get("all_passed", False))


__all__ = [
    "module_selftest_keys",
    "run_module_selftest",
    "run_module_selftests",
    "report_all_passed",
    "report_all_validator_valid",
]
