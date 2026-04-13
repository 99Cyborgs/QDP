from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_PATHS = [
    "packages/qdp_control/src/qdp_control/control_plane.py",
    "packages/qdp_control/src/qdp_control/queue.py",
    "packages/qdp_control/src/qdp_control/run_ledger.py",
    "tools/workflow/qdp_runtime/qdp_subsystem.py",
    "tools/migration/repo_audit.py",
    "tools/migration/write_migration_manifests.py",
]


def test_active_control_and_audit_surfaces_use_qdp_io_utc_now() -> None:
    for rel_path in TARGET_PATHS:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        assert "from qdp_io.artifacts import" in text, rel_path
        assert "utc_now" in text, rel_path
        assert "def utc_now(" not in text, rel_path
