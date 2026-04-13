from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_VALIDATION_SRC = ROOT / "packages" / "qdp_validation" / "src"

for path in (QDP_IO_SRC, QDP_VALIDATION_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_validation import (
    build_module_selftest_alias,
    module_verification_from_bootstrap,
    report_all_passed,
    report_all_validator_valid,
    structural_consistency_from_blockers,
    validate_all_mind_interface_file,
)
from tools.workflow.qdp_runtime.qdp_paths import ALL_MIND_INTERFACE_REPORT


def test_current_all_mind_interface_contract_is_valid() -> None:
    result = validate_all_mind_interface_file(ALL_MIND_INTERFACE_REPORT)

    assert result["valid"] is True
    assert result["errors"] == []


def test_structural_consistency_from_blockers_ignores_informational_entries() -> None:
    blocker_ledger = {
        "blockers": [
            {"severity": "informational"},
            {"severity": "info"},
        ]
    }

    assert structural_consistency_from_blockers(blocker_ledger) is True


def test_structural_consistency_from_blockers_rejects_non_informational_entries() -> None:
    blocker_ledger = {
        "blockers": [
            {"severity": "informational"},
            {"severity": "critical"},
        ]
    }

    assert structural_consistency_from_blockers(blocker_ledger) is False


def test_validation_module_workflow_helpers_cover_report_flags() -> None:
    assert report_all_passed({"all_passed": True}) is True
    assert report_all_validator_valid({"schema_valid_all": True}) is True
    assert report_all_validator_valid({"cases": [{"validator_result": {"valid": True}}]}) is True


def test_module_verification_helpers_read_bootstrap_shapes() -> None:
    module_verification = {
        "M01": {
            "module_key": "m01",
            "verification_kind": "assembly_report",
            "evidence_paths": {"assembly_report": "a.json"},
            "verification_passed": True,
            "all_passed": True,
            "validator_valid_all": True,
            "cases_total": 2,
            "cases_passed": 2,
        }
    }
    bootstrap_report = {"checks": {"module_verification": module_verification}}

    assert module_verification_from_bootstrap(bootstrap_report) == module_verification
    alias = build_module_selftest_alias(module_verification)
    assert alias["M01"]["report_path"] == "a.json"
    assert alias["M01"]["all_passed"] is True
