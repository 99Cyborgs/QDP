from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"

path_str = str(QDP_IO_SRC)
if path_str not in sys.path:
    sys.path.insert(0, path_str)

from qdp_io.module_registry import (
    build_module_registry_json as build_module_registry_payload,
    build_module_registry_md as build_module_registry_markdown,
    closure_limitations_for,
    derived_status_for,
    write_module_registry as write_module_registry_payload,
)
from tools.workflow.qdp_runtime.qdp_paths import MODULE_REGISTRY_BLUEPRINTS, RESUME_POLICY


def build_module_registry_json(
    closure_by_module: Dict[str, Dict[str, Any]],
    readiness: Dict[str, Any],
) -> Dict[str, Any]:
    return build_module_registry_payload(
        MODULE_REGISTRY_BLUEPRINTS,
        resume_policy=RESUME_POLICY,
        closure_by_module=closure_by_module,
        readiness=readiness,
    )


def build_module_registry_md(
    closure_by_module: Dict[str, Dict[str, Any]],
    readiness: Dict[str, Any],
) -> str:
    return build_module_registry_markdown(
        MODULE_REGISTRY_BLUEPRINTS,
        closure_by_module=closure_by_module,
        readiness=readiness,
    )


def write_module_registry(
    registry_json_path: Path,
    registry_md_path: Path,
    closure_by_module: Dict[str, Dict[str, Any]],
    readiness: Dict[str, Any],
) -> Dict[str, Any]:
    return write_module_registry_payload(
        registry_json_path,
        registry_md_path,
        MODULE_REGISTRY_BLUEPRINTS,
        resume_policy=RESUME_POLICY,
        closure_by_module=closure_by_module,
        readiness=readiness,
    )

