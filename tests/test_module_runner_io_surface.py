from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATHS = [
    "modules/m01_runtime_assembly/runner.py",
    "modules/m02_schema_validator/runner.py",
    "modules/m03_reference_resolution/runner.py",
    "modules/m04_branch_registration/runner.py",
    "modules/m05_stage_machine/runner.py",
    "modules/m06_bootstrap_harness/runner.py",
    "modules/m07_family_triage/runner.py",
    "modules/m08_baseline_fit/runner.py",
    "modules/m09_mechanism_competition/runner.py",
    "modules/m10_artifact_audit/runner.py",
    "modules/m11_lindblad_equivalence/runner.py",
    "modules/m12_experiment_design/runner.py",
    "modules/m13_cross_device_gate/runner.py",
    "modules/m14_promotion_caps/runner.py",
    "modules/m15_governance_guardrails/runner.py",
]


def test_active_module_runners_use_qdp_io_dump_json() -> None:
    for rel_path in RUNNER_PATHS:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "from qdp_io.artifacts import" in text, rel_path
        assert "dump_json" in text, rel_path
        assert "def dump_json(" not in text, rel_path


def test_active_module_runners_use_qdp_io_utc_now() -> None:
    for rel_path in RUNNER_PATHS:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "from qdp_io.artifacts import" in text, rel_path
        assert "utc_now" in text, rel_path
        assert "datetime.now(timezone.utc).isoformat()" not in text, rel_path


def test_active_module_runners_use_qdp_io_module_report_header() -> None:
    for rel_path in RUNNER_PATHS:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "from qdp_io.artifacts import" in text, rel_path
        assert (
            "module_report_header" in text
            or "candidate_result_summary_report" in text
            or "visible_source_result_summary_report" in text
        ), rel_path


SELFTEST_RUNNER_PATHS = [
    "modules/m01_runtime_assembly/runner.py",
    "modules/m02_schema_validator/runner.py",
    "modules/m04_branch_registration/runner.py",
    "modules/m05_stage_machine/runner.py",
    "modules/m07_family_triage/runner.py",
    "modules/m08_baseline_fit/runner.py",
    "modules/m09_mechanism_competition/runner.py",
    "modules/m10_artifact_audit/runner.py",
    "modules/m11_lindblad_equivalence/runner.py",
    "modules/m12_experiment_design/runner.py",
    "modules/m13_cross_device_gate/runner.py",
    "modules/m14_promotion_caps/runner.py",
    "modules/m15_governance_guardrails/runner.py",
]


def test_active_module_selftest_surfaces_use_qdp_io_selftest_report_payload() -> None:
    for rel_path in SELFTEST_RUNNER_PATHS:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "module_selftest_report_payload" in text, rel_path


RESULT_SUMMARY_RUNNER_PATHS = [
    "modules/m11_lindblad_equivalence/runner.py",
    "modules/m12_experiment_design/runner.py",
    "modules/m13_cross_device_gate/runner.py",
    "modules/m14_promotion_caps/runner.py",
    "modules/m15_governance_guardrails/runner.py",
]


def test_active_candidate_result_summary_surfaces_use_qdp_io_helper() -> None:
    for rel_path in RESULT_SUMMARY_RUNNER_PATHS:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "candidate_result_summary_report" in text, rel_path


VISIBLE_SOURCE_RESULT_RUNNER_PATHS = [
    "modules/m07_family_triage/runner.py",
    "modules/m08_baseline_fit/runner.py",
    "modules/m09_mechanism_competition/runner.py",
    "modules/m10_artifact_audit/runner.py",
]


def test_active_visible_source_result_summary_surfaces_use_qdp_io_helper() -> None:
    for rel_path in VISIBLE_SOURCE_RESULT_RUNNER_PATHS:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "visible_source_result_summary_report" in text, rel_path
