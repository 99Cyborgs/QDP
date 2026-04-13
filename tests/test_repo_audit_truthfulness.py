from __future__ import annotations

from tools.migration.repo_audit import active_truth_conflict_paths


def test_active_truth_conflict_paths_flags_stale_live_narrative() -> None:
    active_docs = {
        "modules/m06_bootstrap_harness/patch_notes.md": (
            "Status: Recovery-interim module closure for M06; "
            "recovery readiness is true while authoritative readiness remains false"
        ),
        "docs/decisions/drift_control_artifact_pack.md": "- M05 is `RECOVERY_INTERIM` because stage semantics still depend on surrogate provenance.",
    }
    module_statuses = {
        "M05": "AUTHORITATIVE_CLOSURE",
        "M06": "AUTHORITATIVE_CLOSURE",
    }
    readiness = {
        "ordinary_authoritative_ready": True,
        "subsystem_authoritative_ready": True,
    }

    conflicts = active_truth_conflict_paths(active_docs, module_statuses, readiness)

    assert conflicts == sorted(active_docs)


def test_active_truth_conflict_paths_ignores_forwarding_stubs() -> None:
    active_docs = {
        "modules/m06_bootstrap_harness/patch_notes.md": (
            "This path is retained only as a forwarding stub.\n"
            "Use these current sources instead:\n"
            "- artifacts/reports/m06/bootstrap_report.json"
        )
    }
    module_statuses = {"M06": "AUTHORITATIVE_CLOSURE"}
    readiness = {
        "ordinary_authoritative_ready": True,
        "subsystem_authoritative_ready": True,
    }

    conflicts = active_truth_conflict_paths(active_docs, module_statuses, readiness)

    assert conflicts == []
