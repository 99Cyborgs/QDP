from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_runner_module():
    runner_path = ROOT / "scripts" / "run_repo_validation.py"
    spec = importlib.util.spec_from_file_location("qdp_run_repo_validation_test", runner_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_interface_artifact_or_exit_accepts_current_contract() -> None:
    runner = load_runner_module()

    interface = runner.validate_interface_artifact_or_exit(runner.INTERFACE_PATH)

    assert interface["artifact_id"] == "QDP_ALL_MIND_INTERFACE"


def test_validate_interface_artifact_or_exit_fails_on_schema_drift(tmp_path: Path) -> None:
    runner = load_runner_module()
    invalid_path = tmp_path / "all_mind_interface.json"
    invalid_path.write_text(json.dumps({"artifact_id": "QDP_ALL_MIND_INTERFACE"}), encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        runner.validate_interface_artifact_or_exit(invalid_path)

    assert excinfo.value.code == 1
