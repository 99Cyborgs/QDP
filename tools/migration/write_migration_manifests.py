from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
path_str = str(QDP_IO_SRC)
if path_str not in sys.path:
    sys.path.insert(0, path_str)

from qdp_io.artifacts import artifact_report_header, dump_json, utc_now

SYSTEM_REPORTS_DIR = ROOT / "artifacts" / "reports" / "system"


MOVE_RECORDS: List[Dict[str, str]] = [
    {
        "from": "qdp.py",
        "to": "tools/workflow/qdp_runtime/qdp_cli.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_artifact_contracts.py",
        "to": "tools/workflow/qdp_runtime/qdp_artifact_contracts.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_campaign_planner.py",
        "to": "tools/workflow/qdp_runtime/qdp_campaign_planner.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_control_plane.py",
        "to": "tools/workflow/qdp_runtime/qdp_control_plane.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_governance.py",
        "to": "tools/workflow/qdp_runtime/qdp_governance.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_lab_workflows.py",
        "to": "tools/workflow/qdp_runtime/qdp_lab_workflows.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_module_sdk.py",
        "to": "tools/workflow/qdp_runtime/qdp_module_sdk.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_module_workflows.py",
        "to": "tools/workflow/qdp_runtime/qdp_module_workflows.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_paths.py",
        "to": "tools/workflow/qdp_runtime/qdp_paths.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_registry.py",
        "to": "tools/workflow/qdp_runtime/qdp_registry.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_run_ledger.py",
        "to": "tools/workflow/qdp_runtime/qdp_run_ledger.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_subsystem.py",
        "to": "tools/workflow/qdp_runtime/qdp_subsystem.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "qdp_validation.py",
        "to": "tools/workflow/qdp_runtime/qdp_validation.py",
        "action": "relocated_with_root_wrapper",
    },
    {
        "from": "docs/implementation/m05_implementation_pack.md",
        "to": "docs/architecture/m05_stage_machine_implementation_pack.md",
        "action": "moved",
    },
    {
        "from": "docs/reports/drift_control_artifact_pack.md",
        "to": "docs/decisions/drift_control_artifact_pack.md",
        "action": "moved",
    },
    {
        "from": "docs/schema/schema_patch_notes_m02.md",
        "to": "docs/decisions/schema_patch_notes_m02.md",
        "action": "moved",
    },
    {
        "from": "RL framework/",
        "to": "legacy/imported_artifacts/rl_framework/",
        "action": "moved_directory",
    },
]

ADDED_FILES = [
    "tools/__init__.py",
    "tools/workflow/__init__.py",
    "tools/workflow/qdp_runtime/__init__.py",
    "tools/workflow/qdp_runtime/qdp_cli.py",
    "tools/workflow/qdp_runtime/qdp_artifact_contracts.py",
    "tools/workflow/qdp_runtime/qdp_campaign_planner.py",
    "tools/workflow/qdp_runtime/qdp_control_plane.py",
    "tools/workflow/qdp_runtime/qdp_governance.py",
    "tools/workflow/qdp_runtime/qdp_lab_workflows.py",
    "tools/workflow/qdp_runtime/qdp_module_sdk.py",
    "tools/workflow/qdp_runtime/qdp_module_workflows.py",
    "tools/workflow/qdp_runtime/qdp_paths.py",
    "tools/workflow/qdp_runtime/qdp_registry.py",
    "tools/workflow/qdp_runtime/qdp_run_ledger.py",
    "tools/workflow/qdp_runtime/qdp_subsystem.py",
    "tools/workflow/qdp_runtime/qdp_validation.py",
    "tools/migration/repo_audit.py",
    "tools/migration/write_migration_manifests.py",
    "docs/repo/qdp_repo_refactor_plan.md",
    "legacy/docs/README.md",
    "legacy/docs/forwarding_manifest.json",
    ".gitignore",
]

UPDATED_FILES = [
    "qdp.py",
    "qdp_artifact_contracts.py",
    "qdp_campaign_planner.py",
    "qdp_control_plane.py",
    "qdp_governance.py",
    "qdp_lab_workflows.py",
    "qdp_module_sdk.py",
    "qdp_module_workflows.py",
    "qdp_paths.py",
    "qdp_registry.py",
    "qdp_run_ledger.py",
    "qdp_subsystem.py",
    "qdp_validation.py",
    "REPO_MAP.md",
    "STATUS.md",
    "VALIDATION.md",
    "PROMOTION_NOTES.md",
    "modules/m06_bootstrap_harness/patch_notes.md",
    "modules/m06_bootstrap_harness/integration_run_report.md",
    "docs/decisions/drift_control_artifact_pack.md",
    "config/manifests/reference_manifest.json",
    "config/registries/governance_registry.json",
    "config/registries/module_registry.json",
    "docs/repo/module_registry.md",
]

DELETED_PATHS = [
    "MISSING/",
    "legacy/QDP_REPO_REFACTOR_PLAN.md",
    "legacy/docs/architecture/solver_architecture.md",
    "legacy/docs/implementation/m05_implementation_pack.md",
    "legacy/docs/repo/module_registry.md",
    "legacy/docs/reports/drift_control_artifact_pack.md",
    "legacy/docs/schema/schema_patch_notes_m02.md",
    "legacy/docs/architecture/",
    "legacy/docs/implementation/",
    "legacy/docs/repo/",
    "legacy/docs/reports/",
    "legacy/docs/schema/",
    "RL framework/",
    "__pycache__/",
    "modules/**/__pycache__/",
    "tools/**/__pycache__/",
]


def build_write_log() -> Dict[str, Any]:
    warnings: List[str] = []

    for record in MOVE_RECORDS:
        if record["to"].endswith("/"):
            if not (ROOT / record["to"].rstrip("/")).exists():
                warnings.append(f"Missing expected moved directory: {record['to']}")
        elif not (ROOT / record["to"]).exists():
            warnings.append(f"Missing expected moved target: {record['to']}")

    for path in ADDED_FILES + UPDATED_FILES:
        if not (ROOT / path).exists():
            warnings.append(f"Missing expected changed path: {path}")

    return {
        **artifact_report_header("QDP_MIGRATION_WRITE_LOG"),
        "moves": MOVE_RECORDS,
        "added": [{"path": path} for path in ADDED_FILES],
        "updated": [{"path": path} for path in UPDATED_FILES],
        "deleted": [{"path": path} for path in DELETED_PATHS],
        "warnings": warnings,
    }


def build_changed_manifest(write_log: Dict[str, Any]) -> Dict[str, Any]:
    changed_paths = set()
    for record in write_log.get("moves", []):
        changed_paths.add(record["from"])
        changed_paths.add(record["to"])
    for section in ("added", "updated", "deleted"):
        for record in write_log.get(section, []):
            changed_paths.add(record["path"])

    return {
        **artifact_report_header("QDP_CHANGED_FILE_MANIFEST"),
        "source": "artifacts/reports/system/migration_write_log.json",
        "counts": {
            "moves": len(write_log.get("moves", [])),
            "added": len(write_log.get("added", [])),
            "updated": len(write_log.get("updated", [])),
            "deleted": len(write_log.get("deleted", [])),
            "changed_paths_total": len(changed_paths),
        },
        "changed_paths": sorted(changed_paths),
    }


def main() -> int:
    write_log = build_write_log()
    changed_manifest = build_changed_manifest(write_log)
    dump_json(SYSTEM_REPORTS_DIR / "migration_write_log.json", write_log)
    dump_json(SYSTEM_REPORTS_DIR / "changed_file_manifest.json", changed_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
