from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_VALIDATION_SRC = ROOT / "packages" / "qdp_validation" / "src"

# Compatibility wrapper for tools.workflow.qdp_runtime.qdp_validation.
for path in (QDP_IO_SRC, QDP_VALIDATION_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

PACKAGE_INIT = QDP_VALIDATION_SRC / "qdp_validation" / "__init__.py"
SPEC = importlib.util.spec_from_file_location(
    "_qdp_validation_pkg",
    PACKAGE_INIT,
    submodule_search_locations=[str(PACKAGE_INIT.parent)],
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not import qdp_validation package from {PACKAGE_INIT}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

__all__ = list(getattr(MODULE, "__all__", []))
for name in __all__:
    globals()[name] = getattr(MODULE, name)

main = MODULE.main


if __name__ == "__main__":
    raise SystemExit(main())
