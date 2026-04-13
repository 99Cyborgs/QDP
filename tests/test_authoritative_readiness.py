from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_runner_module():
    runner_path = ROOT / "modules" / "m06_bootstrap_harness" / "runner.py"
    spec = importlib.util.spec_from_file_location("qdp_m06_runner_authoritative_test", runner_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_visible_source_module_requires_explicit_authoritative_binding() -> None:
    runner = load_runner_module()
    predicate_results = [{"passed": True}, {"passed": True}]
    context = {
        "reference_manifest": {"reference_entries": []},
        "governance_registry": {},
        "rule_binding_registry": {"authoritative_module_bindings": {}},
    }

    assert runner.derive_contract_status("M07", predicate_results, context) == "WORKING_PATCH"


def test_visible_source_module_closes_authoritatively_with_binding() -> None:
    runner = load_runner_module()
    predicate_results = [{"passed": True}, {"passed": True}]
    context = {
        "reference_manifest": {"reference_entries": []},
        "governance_registry": {},
        "rule_binding_registry": {
            "authoritative_module_bindings": {
                "M07": {
                    "status": "BOUND",
                    "evidence_paths": [
                        "modules/m07_family_triage/runner.py",
                        "artifacts/reports/m07/selftest_report.json",
                    ],
                }
            }
        },
    }

    assert runner.derive_contract_status("M07", predicate_results, context) == "AUTHORITATIVE_CLOSURE"


def test_surrogate_retained_reference_requires_authoritative_binding() -> None:
    runner = load_runner_module()
    context = {
        "reference_manifest": {
            "reference_entries": [
                {
                    "ref_id": "RETAINED_V10_1_OPERATIVE_BODY",
                    "provenance": "reconstructed_surrogate",
                }
            ]
        },
        "governance_registry": {},
        "rule_binding_registry": {},
    }

    limitations = runner.surrogate_limitations_for_module("M01", context)
    assert limitations


def test_surrogate_retained_reference_can_be_superseded_by_explicit_binding() -> None:
    runner = load_runner_module()
    context = {
        "reference_manifest": {
            "reference_entries": [
                {
                    "ref_id": "RETAINED_V10_1_OPERATIVE_BODY",
                    "provenance": "reconstructed_surrogate",
                    "authoritative_binding_status": "BOUND",
                }
            ]
        },
        "governance_registry": {
            "authoritative_reference_bindings": {
                "RETAINED_V10_1_OPERATIVE_BODY": {
                    "status": "BOUND",
                }
            }
        },
        "rule_binding_registry": {},
    }

    assert runner.surrogate_limitations_for_module("M01", context) == []
