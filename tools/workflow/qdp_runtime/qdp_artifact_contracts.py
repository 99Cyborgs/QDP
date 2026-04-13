from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_VALIDATION_SRC = ROOT / "packages" / "qdp_validation" / "src"

for path in (QDP_IO_SRC, QDP_VALIDATION_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_validation import (  # noqa: E402
    SemanticValidator,
    emit_artifact_validation_result as emit_validation_result,
    require_no_errors,
    validate_artifact_file as validate_file,
    validate_artifact_instance as validate_instance,
)
from qdp_io.artifacts import dump_json, sha256_file, stable_hash  # noqa: E402
from qdp_io.serialization import load_json  # noqa: E402
