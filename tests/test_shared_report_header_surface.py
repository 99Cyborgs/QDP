from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_PATHS = {
    "packages/qdp_control/src/qdp_control/queue.py": "artifact_report_header",
    "packages/qdp_control/src/qdp_control/run_ledger.py": "artifact_report_header",
    "tools/workflow/qdp_runtime/qdp_subsystem.py": "module_report_header",
    "tools/migration/repo_audit.py": "artifact_report_header",
    "tools/migration/write_migration_manifests.py": "artifact_report_header",
}


def test_active_control_and_audit_surfaces_use_shared_report_header_helpers() -> None:
    for rel_path, helper_name in TARGET_PATHS.items():
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "from qdp_io.artifacts import" in text, rel_path
        assert helper_name in text, rel_path
