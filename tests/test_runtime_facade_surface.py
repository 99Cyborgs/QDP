from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_runtime_artifact_contracts_is_only_a_compatibility_facade() -> None:
    text = _read("tools/workflow/qdp_runtime/qdp_artifact_contracts.py")

    assert "from qdp_validation import" in text
    assert "from qdp_io.artifacts import" in text
    assert "from qdp_io.serialization import load_json" in text
    assert "def dump_json(" not in text
    assert "def stable_hash(" not in text
    assert "def sha256_file(" not in text
    assert "def validate_file(" not in text


def test_runtime_registry_is_a_qdp_io_backed_adapter() -> None:
    text = _read("tools/workflow/qdp_runtime/qdp_registry.py")

    assert "from qdp_io.module_registry import" in text
    assert "build_module_registry_payload" in text
    assert "write_module_registry_payload" in text
    assert "datetime.now(timezone.utc)" not in text


def test_runtime_shell_helpers_use_shared_object_root_loader() -> None:
    for rel_path in [
        "tools/workflow/qdp_runtime/qdp_module_sdk.py",
        "tools/workflow/qdp_runtime/qdp_subsystem.py",
        "tools/workflow/qdp_runtime/qdp_cli.py",
    ]:
        text = _read(rel_path)
        assert "load_json_object" in text, rel_path


def test_runtime_validation_helper_modules_are_qdp_validation_facades() -> None:
    workflows = _read("tools/workflow/qdp_runtime/qdp_module_workflows.py")
    verification = _read("tools/workflow/qdp_runtime/qdp_module_verification.py")

    assert "from qdp_validation.module_workflows import *" in workflows
    assert "from qdp_validation.module_verification import *" in verification
    assert "ThreadPoolExecutor" not in workflows
    assert "_m03_verification(" not in verification
