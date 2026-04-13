from __future__ import annotations

import argparse
import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
for path in (ROOT, QDP_IO_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_io.artifacts import artifact_report_header, dump_json, utc_now
from tools.workflow.qdp_runtime.qdp_module_verification import (
    build_module_selftest_alias,
    module_verification_from_bootstrap,
)
from tools.workflow.qdp_runtime.qdp_paths import (
    ALL_MIND_AUTHORITATIVE_READINESS_FIELDS,
    ALL_MIND_INTERFACE_CALLABLE_SURFACES,
    ALL_MIND_INTERFACE_PROMOTION_NOTE,
)


SYSTEM_REPORTS_DIR = ROOT / "artifacts" / "reports" / "system"

GUIDANCE_FILES = {
    "README.md",
    "AGENTS.md",
    "SYSTEM_BOUNDARY.md",
    "STATUS.md",
    "REPO_MAP.md",
    "VALIDATION.md",
    "ARCHITECTURE_SUMMARY.md",
    "PROMOTION_NOTES.md",
    "DEPENDENCY_NOTES.md",
    "INTEGRATION_RISKS.md",
    "INTEGRATION_PLAN.md",
    "QDP_REPO_REFACTOR_PLAN.md",
}
ENTRYPOINT_FILES = {"qdp.py", "qdp_validation.py"}
ROOT_SUPPORT_MODULES = {
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
}
CANONICAL_ROOT_DIRS = {
    "artifacts",
    "config",
    "docs",
    "legacy",
    "modules",
    "runtime",
    "specs",
    "tools",
}
OUTLIER_ROOT_DIRS = {"RL framework", "MISSING", "__pycache__"}
MODULE_IDS = [f"M{i:02d}" for i in range(1, 16)] + ["S16", "S17", "S18", "S19"]
ACTIVE_NARRATIVE_DOC_GLOBS = (
    "modules/*/patch_notes.md",
    "modules/*/integration_run_report.md",
    "docs/architecture/*.md",
    "docs/decisions/*.md",
)
def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def file_contains(path: Path, needle: str) -> bool:
    if not path.exists():
        return False
    return needle in path.read_text(encoding="utf-8")


def is_thin_wrapper(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8").strip()
    if "tools.workflow.qdp_runtime" not in text:
        return False
    return "def " not in text and "class " not in text and len(text.splitlines()) <= 8


def python_has_function(path: Path, function_name: str) -> bool:
    if not path.exists():
        return False
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(isinstance(node, ast.FunctionDef) and node.name == function_name for node in ast.walk(tree))


def python_has_main_block(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return 'if __name__ == "__main__"' in text


def load_active_narrative_docs() -> Dict[str, str]:
    docs: Dict[str, str] = {}
    for pattern in ACTIVE_NARRATIVE_DOC_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                docs[rel(path)] = path.read_text(encoding="utf-8")
    return docs


def module_status_map(module_closure_evaluation: Dict[str, Any], module_registry: Dict[str, Any]) -> Dict[str, str]:
    statuses: Dict[str, str] = {}
    for item in module_closure_evaluation.get("modules", []):
        if isinstance(item, dict) and item.get("module_id") and item.get("derived_status"):
            statuses[str(item["module_id"])] = str(item["derived_status"])
    for item in module_registry.get("modules", []):
        if isinstance(item, dict) and item.get("module_id"):
            statuses.setdefault(str(item["module_id"]), str(item.get("derived_closure_status", item.get("status", ""))))
    return statuses


def doc_claims_module_status(text: str, module_id: str, status: str) -> bool:
    normalized = text.lower()
    module_token = module_id.lower()
    status_token = status.lower()
    patterns = (
        f"{module_token} = `{status_token}`",
        f"{module_token} is `{status_token}`",
        f"{module_token} therefore qualifies as `{status_token}`",
        f"{module_token} now qualifies as `{status_token}`",
        f"resulting {module_token} status: `{status_token}`",
    )
    return any(pattern in normalized for pattern in patterns)


def active_truth_conflict_paths(
    active_docs: Dict[str, str],
    module_statuses: Dict[str, str],
    readiness: Dict[str, bool],
) -> List[str]:
    conflicts: List[str] = []
    authoritative_ready = bool(readiness.get("ordinary_authoritative_ready")) and bool(
        readiness.get("subsystem_authoritative_ready")
    )

    for path, text in active_docs.items():
        normalized = text.lower()

        if authoritative_ready and (
            "authoritative readiness remains false" in normalized
            or "recovery readiness is true while authoritative readiness remains false" in normalized
            or "ordinary testing remains blocked by the authoritative requirements" in normalized
            or "subsystem testing remains blocked by the authoritative requirements" in normalized
        ):
            conflicts.append(path)
            continue

        for module_id, actual_status in module_statuses.items():
            for stale_status in ("BLOCKED", "WORKING_PATCH", "RECOVERY_INTERIM"):
                if actual_status != stale_status and doc_claims_module_status(text, module_id, stale_status):
                    conflicts.append(path)
                    break
            else:
                continue
            break
        if path in conflicts:
            continue

        if module_statuses.get("M05") == "AUTHORITATIVE_CLOSURE" and (
            "status: working_patch" in normalized
            or "do not mark m05 as `authoritative_closure`" in normalized
        ):
            conflicts.append(path)
            continue

        if module_statuses.get("M06") == "AUTHORITATIVE_CLOSURE" and (
            "status: recovery-interim" in normalized
            or "m06 remains below authoritative closure" in normalized
        ):
            conflicts.append(path)

    return sorted(set(conflicts))


def all_mind_doc_drift_paths(status_text: str, promotion_text: str, integration_text: str) -> List[str]:
    drift: List[str] = []

    if "compact status and interface artifacts" not in status_text or "whole-repo ingestion" not in status_text:
        drift.append("STATUS.md")

    if (
        "artifacts/reports/system/all_mind_interface.json" not in promotion_text
        or "whole-repo ALL-MIND runtime dependency" not in promotion_text
    ):
        drift.append("PROMOTION_NOTES.md")

    required_integration_snippets = [
        "- `artifacts/reports/system/all_mind_interface.json`",
        "- compact status language in `STATUS.md`",
        "- promotion posture in `PROMOTION_NOTES.md`",
        "`structural_consistency_passed` is not equivalent to authoritative readiness.",
        "callable_surfaces` provide the only allowed control-plane affordances",
    ]
    required_integration_snippets.extend(f"- `{field}`" for field in ALL_MIND_AUTHORITATIVE_READINESS_FIELDS)
    if any(snippet not in integration_text for snippet in required_integration_snippets):
        drift.append("INTEGRATION_PLAN.md")

    return sorted(set(drift))


def module_verification_statuses() -> Dict[str, Any]:
    bootstrap = load_json(ROOT / "artifacts" / "reports" / "m06" / "bootstrap_report.json", {}) or {}
    statuses = module_verification_from_bootstrap(bootstrap)
    return statuses if isinstance(statuses, dict) else {}


def build_inventory() -> Dict[str, Any]:
    root_files = sorted(path.name for path in ROOT.iterdir() if path.is_file())
    root_dirs = sorted(path.name for path in ROOT.iterdir() if path.is_dir())
    docs_children = sorted(rel(path) for path in (ROOT / "docs").rglob("*") if path.is_file())
    legacy_children = sorted(rel(path) for path in (ROOT / "legacy").rglob("*") if path.is_file())
    runtime_files = sorted(rel(path) for path in (ROOT / "runtime").rglob("*") if path.is_file())
    artifact_files = sorted(rel(path) for path in (ROOT / "artifacts").rglob("*") if path.is_file())
    config_files = sorted(rel(path) for path in (ROOT / "config").rglob("*") if path.is_file())
    spec_files = sorted(rel(path) for path in (ROOT / "specs").rglob("*") if path.is_file())
    module_files = sorted(rel(path) for path in (ROOT / "modules").rglob("*") if path.is_file())
    tool_files = sorted(rel(path) for path in (ROOT / "tools").rglob("*") if path.is_file())
    return {
        **artifact_report_header("QDP_REPO_SOURCE_GENERATED_INVENTORY"),
        "root": {
            "guidance_files": [name for name in root_files if name in GUIDANCE_FILES],
            "entrypoint_files": [name for name in root_files if name in ENTRYPOINT_FILES],
            "support_modules": [name for name in root_files if name in ROOT_SUPPORT_MODULES],
            "other_root_files": [name for name in root_files if name not in GUIDANCE_FILES.union(ENTRYPOINT_FILES).union(ROOT_SUPPORT_MODULES)],
            "canonical_dirs": [name for name in root_dirs if name in CANONICAL_ROOT_DIRS],
            "outlier_dirs": [name for name in root_dirs if name in OUTLIER_ROOT_DIRS],
            "other_root_dirs": [name for name in root_dirs if name not in CANONICAL_ROOT_DIRS.union(OUTLIER_ROOT_DIRS).union({".git"})],
        },
        "source_space": {
            "specs": spec_files,
            "config": config_files,
            "modules": module_files,
            "tools": tool_files,
            "docs": docs_children,
        },
        "runtime_space": runtime_files,
        "generated_space": artifact_files,
        "legacy_space": legacy_children,
    }


def build_blockers(phase: str) -> Dict[str, Any]:
    status_md = (ROOT / "STATUS.md").read_text(encoding="utf-8")
    promotion_md = (ROOT / "PROMOTION_NOTES.md").read_text(encoding="utf-8")
    integration_md = (ROOT / "INTEGRATION_PLAN.md").read_text(encoding="utf-8")
    module_registry = load_json(ROOT / "config" / "registries" / "module_registry.json", {}) or {}
    governance_registry = load_json(ROOT / "config" / "registries" / "governance_registry.json", {}) or {}
    reference_manifest = load_json(ROOT / "config" / "manifests" / "reference_manifest.json", {}) or {}
    subsystem_report = load_json(ROOT / "artifacts" / "reports" / "m03" / "reference_resolution_subsystem.json", {}) or {}
    bootstrap_report = load_json(ROOT / "artifacts" / "reports" / "m06" / "bootstrap_report.json", {}) or {}
    closure_report = load_json(ROOT / "artifacts" / "reports" / "m06" / "closure_report.json", {}) or {}
    module_closure_evaluation = (
        load_json(ROOT / "artifacts" / "reports" / "system" / "module_closure_evaluation.json", {}) or {}
    )

    blockers: List[Dict[str, Any]] = []

    root_support = [name for name in ROOT_SUPPORT_MODULES if (ROOT / name).exists()]
    heavy_root_support = [name for name in root_support if not is_thin_wrapper(ROOT / name)]
    if heavy_root_support:
        blockers.append(
            {
                "blocker_id": "ROOT_SUPPORT_MODULES_PRESENT",
                "class": "STRUCTURE",
                "severity": "high",
                "detail": "Root still contains shared implementation-heavy support modules instead of a canonical internal package.",
                "paths": heavy_root_support,
            }
        )

    outliers = [name for name in OUTLIER_ROOT_DIRS if (ROOT / name).exists()]
    if outliers:
        blockers.append(
            {
                "blocker_id": "ROOT_OUTLIER_DIRS_PRESENT",
                "class": "STRUCTURE",
                "severity": "medium",
                "detail": "Root contains outlier or generated directories that should be quarantined or removed.",
                "paths": outliers,
            }
        )

    qdp_validation_path = ROOT / "qdp_validation.py"
    is_validation_wrapper = file_contains(qdp_validation_path, "tools.workflow.qdp_runtime.qdp_validation") and python_has_main_block(qdp_validation_path)
    is_validation_cli = python_has_function(qdp_validation_path, "main") and python_has_main_block(qdp_validation_path) and file_contains(qdp_validation_path, "argparse")
    if not (is_validation_wrapper or is_validation_cli):
        blockers.append(
            {
                "blocker_id": "QDP_VALIDATION_NOT_CLI",
                "class": "ENTRYPOINT",
                "severity": "high",
                "detail": "qdp_validation.py is documented as a repo-level validation entrypoint but does not expose a real CLI.",
                "paths": ["qdp_validation.py", "VALIDATION.md", "REPO_MAP.md"],
            }
        )

    wrong_subsystem_path = "specs/subsystem/specs/subsystem/gksl_subsystem_case_matrix.json"
    manifest_has_wrong_path = any(
        entry.get("relative_path") == wrong_subsystem_path
        for entry in reference_manifest.get("reference_entries", [])
        if isinstance(entry, dict)
    )
    registry_has_wrong_path = any(
        entry.get("relative_path") == wrong_subsystem_path
        for entry in governance_registry.get("canonical_references", [])
        if isinstance(entry, dict)
    )
    report_has_wrong_path = any(
        entry.get("relative_path") == wrong_subsystem_path
        for entry in subsystem_report.get("unresolved_references", [])
        if isinstance(entry, dict)
    )
    if manifest_has_wrong_path or registry_has_wrong_path or report_has_wrong_path:
        blockers.append(
            {
                "blocker_id": "SUBSYSTEM_MATRIX_PATH_DRIFT",
                "class": "PATH_DRIFT",
                "severity": "high",
                "detail": "The subsystem case matrix path is inconsistent with the canonical specs/subsystem location.",
                "paths": [
                    "config/manifests/reference_manifest.json",
                    "config/registries/governance_registry.json",
                    "artifacts/reports/m03/reference_resolution_subsystem.json",
                ],
            }
        )

    stale_truth_paths = active_truth_conflict_paths(
        load_active_narrative_docs(),
        module_status_map(module_closure_evaluation, module_registry),
        {
            "ordinary_authoritative_ready": bool(bootstrap_report.get("ordinary_authoritative_ready", False)),
            "subsystem_authoritative_ready": bool(bootstrap_report.get("subsystem_authoritative_ready", False)),
        },
    )
    if stale_truth_paths:
        blockers.append(
            {
                "blocker_id": "STALE_NARRATIVE_TRUTH",
                "class": "TRUTHFULNESS",
                "severity": "high",
                "detail": "Narrative docs disagree with current executable closure artifacts and readiness reports.",
                "paths": stale_truth_paths,
            }
        )

    interface_doc_drift_paths = all_mind_doc_drift_paths(status_md, promotion_md, integration_md)
    if interface_doc_drift_paths:
        blockers.append(
            {
                "blocker_id": "ALL_MIND_INTERFACE_DOC_DRIFT",
                "class": "TRUTHFULNESS",
                "severity": "high",
                "detail": "The active control-plane docs do not fully match the frozen ALL-MIND interface contract.",
                "paths": interface_doc_drift_paths,
            }
        )

    if (ROOT / "docs" / "implementation").exists() or (ROOT / "docs" / "reports").exists() or (ROOT / "docs" / "schema").exists():
        blockers.append(
            {
                "blocker_id": "NON_CANONICAL_DOCS_LAYOUT",
                "class": "STRUCTURE",
                "severity": "medium",
                "detail": "docs/ still uses non-canonical implementation/reports/schema subdirectories.",
                "paths": ["docs/implementation", "docs/reports", "docs/schema"],
            }
        )

    legacy_docs = ROOT / "legacy" / "docs"
    legacy_duplicate_files = []
    if legacy_docs.exists():
        legacy_duplicate_files = [
            rel(path)
            for path in legacy_docs.rglob("*")
            if path.is_file()
            and not rel(path).startswith("legacy/docs/archive/")
            and path.name not in {"README.md", "forwarding_manifest.json"}
        ]
    if legacy_duplicate_files:
        blockers.append(
            {
                "blocker_id": "LEGACY_DOC_DUPLICATION",
                "class": "STRUCTURE",
                "severity": "medium",
                "detail": "legacy/docs duplicates canonical docs instead of acting as a compact forwarding surface.",
                "paths": legacy_duplicate_files,
            }
        )

    if not (
        bootstrap_report.get("ordinary_authoritative_ready", False)
        and bootstrap_report.get("subsystem_authoritative_ready", False)
    ):
        blockers.append(
            {
                "blocker_id": "AUTHORITATIVE_READY_FALSE",
                "class": "READINESS",
                "severity": "informational",
                "detail": "Authoritative readiness remains false and must not be upgraded unless regenerated predicates truly change.",
                "paths": ["config/registries/module_registry.json", "artifacts/reports/m06/bootstrap_report.json"],
            }
        )

    module_verification = module_verification_statuses()

    return {
        **artifact_report_header(f"QDP_{phase.upper()}_OVERHAUL_BLOCKER_LEDGER"),
        "phase": phase,
        "summary": {
            "class": "incubate" if "class: `incubate`" in status_md else "",
            "activity": "active" if "activity: `active`" in status_md else "",
            "promotion_mode": "incubation link" if "incubation link" in promotion_md else "",
            "ordinary_recovery_ready": bool(bootstrap_report.get("ordinary_recovery_ready", False)),
            "ordinary_authoritative_ready": bool(bootstrap_report.get("ordinary_authoritative_ready", False)),
            "subsystem_recovery_ready": bool(bootstrap_report.get("subsystem_recovery_ready", False)),
            "subsystem_authoritative_ready": bool(bootstrap_report.get("subsystem_authoritative_ready", False)),
            "m06_derived_status": closure_report.get("derived_status", ""),
            "module_verification": module_verification,
            "module_selftests": build_module_selftest_alias(module_verification),
            "module_selftests_note": "Deprecated compatibility alias of summary.module_verification.",
            "blocker_count": len(blockers),
        },
        "blockers": blockers,
    }


def build_path_migration_report(phase: str) -> Dict[str, Any]:
    wrong_subsystem_path = "specs/subsystem/specs/subsystem/gksl_subsystem_case_matrix.json"
    canonical_subsystem_path = "specs/subsystem/gksl_subsystem_case_matrix.json"
    reference_manifest = load_json(ROOT / "config" / "manifests" / "reference_manifest.json", {}) or {}
    governance_registry = load_json(ROOT / "config" / "registries" / "governance_registry.json", {}) or {}
    subsystem_report = load_json(ROOT / "artifacts" / "reports" / "m03" / "reference_resolution_subsystem.json", {}) or {}
    manifest_paths = {
        entry.get("relative_path")
        for entry in reference_manifest.get("reference_entries", [])
        if isinstance(entry, dict)
    }
    registry_paths = {
        entry.get("relative_path")
        for entry in governance_registry.get("canonical_references", [])
        if isinstance(entry, dict)
    }
    unresolved_paths = {
        entry.get("relative_path")
        for entry in subsystem_report.get("unresolved_references", [])
        if isinstance(entry, dict)
    }
    drift_resolved = (
        wrong_subsystem_path not in manifest_paths
        and wrong_subsystem_path not in registry_paths
        and wrong_subsystem_path not in unresolved_paths
        and canonical_subsystem_path in manifest_paths
        and canonical_subsystem_path in registry_paths
    )
    moves = [
        {
            "from": "root qdp_*.py shared support modules",
            "to": "tools/workflow/qdp_runtime/",
            "reason": "Move shared implementation out of the root while keeping root compatibility shims.",
            "status": "planned" if phase == "pre" else "applied",
        },
        {
            "from": "docs/implementation/*",
            "to": "docs/architecture/*",
            "reason": "Normalize non-canonical source docs.",
            "status": "planned" if phase == "pre" else "applied",
        },
        {
            "from": "docs/reports/*",
            "to": "docs/decisions/*",
            "reason": "Keep source docs distinct from generated reports under artifacts/.",
            "status": "planned" if phase == "pre" else "applied",
        },
        {
            "from": "docs/schema/*",
            "to": "docs/decisions/*",
            "reason": "Treat schema patch notes as decisions/source docs, not generated reports.",
            "status": "planned" if phase == "pre" else "applied",
        },
        {
            "from": "RL framework/*",
            "to": "legacy/imported_artifacts/rl_framework/*",
            "reason": "Quarantine non-governing reference material from the active root surface.",
            "status": "planned" if phase == "pre" else "applied",
        },
        {
            "from": "superseded readiness narrative under modules/ and docs/",
            "to": "legacy/docs/archive/",
            "reason": "Archive historical readiness notes outside the active truth surface while preserving chronology.",
            "status": "planned" if phase == "pre" else "applied",
        },
    ]
    return {
        **artifact_report_header("QDP_PATH_MIGRATION_REPORT"),
        "phase": phase,
        "known_drift": [
            {
                "issue_id": "GKSL_SUBSYSTEM_CASE_MATRIX_PATH",
                "status": "resolved" if drift_resolved else "open",
                "current_value": canonical_subsystem_path if drift_resolved else wrong_subsystem_path,
                "canonical_value": canonical_subsystem_path,
                "affected_paths": [
                    "config/manifests/reference_manifest.json",
                    "config/registries/governance_registry.json",
                    "artifacts/reports/m03/reference_resolution_subsystem.json",
                ],
            }
        ],
        "planned_moves": moves,
        "retained_legacy_surfaces": [
            "qdp.py",
            "qdp_validation.py",
            "root qdp_*.py compatibility shims",
            "existing module runner paths under modules/*/runner.py",
            "root read-first guidance files",
        ],
        "explicit_write_log_path": "artifacts/reports/system/migration_write_log.json",
    }


def build_all_mind_interface() -> Dict[str, Any]:
    status_text = (ROOT / "STATUS.md").read_text(encoding="utf-8")
    promotion_text = (ROOT / "PROMOTION_NOTES.md").read_text(encoding="utf-8")
    bootstrap_report = load_json(ROOT / "artifacts" / "reports" / "m06" / "bootstrap_report.json", {}) or {}
    module_registry = load_json(ROOT / "config" / "registries" / "module_registry.json", {}) or {}
    return {
        **artifact_report_header("QDP_ALL_MIND_INTERFACE"),
        "repo_class": "incubate" if "class: `incubate`" in status_text else "",
        "activity": "active" if "activity: `active`" in status_text else "",
        "promotion_mode": "incubation link" if "incubation link" in promotion_text else "",
        "readiness": {
            "ordinary_recovery_ready": bool(bootstrap_report.get("ordinary_recovery_ready", False)),
            "ordinary_authoritative_ready": bool(bootstrap_report.get("ordinary_authoritative_ready", False)),
            "subsystem_recovery_ready": bool(bootstrap_report.get("subsystem_recovery_ready", False)),
            "subsystem_authoritative_ready": bool(bootstrap_report.get("subsystem_authoritative_ready", False)),
        },
        "blockers": {
            "ordinary_recovery_blockers": bootstrap_report.get("ordinary_recovery_blockers", []),
            "ordinary_authoritative_blockers": bootstrap_report.get("ordinary_authoritative_blockers", []),
            "subsystem_recovery_blockers": bootstrap_report.get("subsystem_recovery_blockers", []),
            "subsystem_authoritative_blockers": bootstrap_report.get("subsystem_authoritative_blockers", []),
        },
        "module_readiness_summary": {
            item.get("module_id", ""): item.get("derived_closure_status", item.get("status", ""))
            for item in module_registry.get("modules", [])
            if isinstance(item, dict)
        },
        "module_closure_limitations": {
            item.get("module_id", ""): item.get("closure_limitations", [])
            for item in module_registry.get("modules", [])
            if isinstance(item, dict) and item.get("closure_limitations")
        },
        "promotion_posture": {
            "suggested_mode": "incubation link",
            "note": ALL_MIND_INTERFACE_PROMOTION_NOTE,
        },
        "callable_surfaces": ALL_MIND_INTERFACE_CALLABLE_SURFACES,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit QDP overhaul audit artifacts.")
    parser.add_argument("--phase", choices=["pre", "post"], required=True)
    parser.add_argument(
        "--emit-all-mind-interface",
        action="store_true",
        help="Emit the narrow ALL-MIND interface artifact.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dump_json(SYSTEM_REPORTS_DIR / f"{args.phase}_overhaul_blocker_ledger.json", build_blockers(args.phase))
    dump_json(SYSTEM_REPORTS_DIR / "source_generated_inventory.json", build_inventory())
    dump_json(SYSTEM_REPORTS_DIR / "path_migration_report.json", build_path_migration_report(args.phase))
    if args.emit_all_mind_interface:
        dump_json(SYSTEM_REPORTS_DIR / "all_mind_interface.json", build_all_mind_interface())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
