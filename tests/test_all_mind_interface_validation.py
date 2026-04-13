from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.workflow.qdp_runtime.qdp_paths import ALL_MIND_INTERFACE_REPORT, ROOT
from tools.workflow.qdp_runtime.qdp_validation import validate_all_mind_interface_file


def test_current_all_mind_interface_validates() -> None:
    result = validate_all_mind_interface_file(ALL_MIND_INTERFACE_REPORT)

    assert result["valid"] is True
    assert result["errors"] == []


def test_cli_rejects_invalid_all_mind_interface_contract(tmp_path: Path) -> None:
    payload = json.loads(ALL_MIND_INTERFACE_REPORT.read_text(encoding="utf-8"))
    payload["callable_surfaces"] = payload["callable_surfaces"][:1]
    invalid_path = tmp_path / "invalid_all_mind_interface.json"
    invalid_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(ROOT / "qdp.py"), "validate", str(invalid_path), "--kind", "all-mind-interface"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "callable_surfaces must match the frozen ALL-MIND contract." in completed.stdout
