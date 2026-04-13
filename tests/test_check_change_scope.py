from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_scope_checker():
    script_path = ROOT / "scripts" / "check_change_scope.py"
    spec = importlib.util.spec_from_file_location("qdp_check_change_scope_test", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runtime_only_diff_passes() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(
        [
            "modules/m06_bootstrap_harness/runner.py",
            "tests/test_execution_queue.py",
        ]
    )

    assert summary["status"] == "ok"
    assert summary["primary_bucket"] == "active_runtime"
    assert summary["bucket_files"]["active_runtime"] == [
        "modules/m06_bootstrap_harness/runner.py",
        "tests/test_execution_queue.py",
    ]


def test_staging_only_diff_passes() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(
        [
            "staging/imported_qdp_tdgl/snapshot/tests/test_runtime.py",
            "legacy/imported_artifacts/example.json",
        ]
    )

    assert summary["status"] == "ok"
    assert summary["primary_bucket"] == "staged_donor"


def test_generated_only_diff_passes() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(
        [
            "artifacts/reports/system/repo_validation_report.json",
            "runs/phase2_4a_validation/output.json",
        ]
    )

    assert summary["status"] == "ok"
    assert summary["primary_bucket"] == "generated_artifacts"


def test_runtime_and_staging_diff_fails() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(
        [
            "packages/qdp_tdgl/src/qdp_tdgl/cli.py",
            "staging/imported_qdp_tdgl/README.md",
        ]
    )

    assert summary["status"] == "scope_violation"
    assert summary["mixed_scope_violations"] == ["active_runtime+staged_donor"]


def test_runtime_and_generated_diff_fails() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(
        [
            "packages/qdp_validation/src/qdp_validation/repo_validation.py",
            "artifacts/reports/system/repo_validation_report.json",
        ]
    )

    assert summary["status"] == "scope_violation"
    assert summary["mixed_scope_violations"] == ["active_runtime+generated_artifacts"]


def test_docs_and_runtime_diff_passes() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(
        [
            "VALIDATION.md",
            "scripts/check_change_scope.py",
        ]
    )

    assert summary["status"] == "ok"
    assert summary["primary_bucket"] == "active_runtime"
    assert summary["bucket_files"]["docs_metadata"] == ["VALIDATION.md"]


def test_docs_and_staging_diff_passes() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(
        [
            "docs/migration/MONOREPO_CONSOLIDATION_STATUS.md",
            "staging/imported_qdp_mm/README.md",
        ]
    )

    assert summary["status"] == "ok"
    assert summary["primary_bucket"] == "staged_donor"


def test_github_workflow_counts_as_docs_metadata() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(
        [
            ".github/workflows/change-scope-hygiene.yml",
            "scripts/check_change_scope.py",
        ]
    )

    assert summary["status"] == "ok"
    assert summary["primary_bucket"] == "active_runtime"
    assert summary["bucket_files"]["docs_metadata"] == [".github/workflows/change-scope-hygiene.yml"]


def test_tests_without_runtime_source_fail() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(["tests/test_execution_queue.py"])

    assert summary["status"] == "scope_violation"
    assert summary["policy_violations"] == ["tests_without_runtime_source"]


def test_allow_mixed_scope_records_override() -> None:
    checker = load_scope_checker()

    summary = checker.summarize_scope(
        [
            "packages/qdp_control/src/qdp_control/queue.py",
            "artifacts/reports/system/queue_report.json",
        ],
        allow_mixed_scope=True,
    )

    assert summary["status"] == "allowed_mixed_scope"
    assert summary["accepted_mixed_scope"] == ["active_runtime+generated_artifacts"]
    assert summary["mixed_scope_violations"] == []
