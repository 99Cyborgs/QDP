from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


def _load_qdp_validation_module():
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    module_path = repo_root / "qdp_validation.py"
    spec = importlib.util.spec_from_file_location("qdp_validation", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qdp_validation = _load_qdp_validation_module()


def _write_schema(path: Path) -> Path:
    path.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    return path


def _write_validator(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "def schema_validate(instance, schema):",
                "    return []",
                "",
                "def semantic_validate(instance, mode):",
                "    return [] if instance.get('ok') else [f'{mode}: missing ok flag']",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _write_candidate(path: Path, *, ok: bool) -> Path:
    path.write_text(json.dumps({"ok": ok}), encoding="utf-8")
    return path


def test_run_candidate_sweep_reports_success(tmp_path: Path) -> None:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()
    schema_path = _write_schema(tmp_path / "candidate_schema.json")
    validator_path = _write_validator(tmp_path / "candidate_validator.py")
    _write_candidate(outputs_root / "alpha_candidate.json", ok=True)
    _write_candidate(outputs_root / "beta_candidate.json", ok=True)

    summary = qdp_validation.run_candidate_sweep(
        outputs_root,
        validator_path,
        schema_path,
        max_workers=4,
    )

    assert summary["returncode"] == 0
    assert summary["status"] == "success"
    assert summary["candidates_total"] == 2
    assert summary["candidates_failed"] == 0
    assert summary["failed_results"] == []
    assert summary["error"] is None


def test_run_candidate_sweep_reports_failure_details(tmp_path: Path) -> None:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()
    schema_path = _write_schema(tmp_path / "candidate_schema.json")
    validator_path = _write_validator(tmp_path / "candidate_validator.py")
    _write_candidate(outputs_root / "alpha_candidate.json", ok=True)
    failing_path = _write_candidate(outputs_root / "beta_candidate.json", ok=False)

    summary = qdp_validation.run_candidate_sweep(
        outputs_root,
        validator_path,
        schema_path,
        max_workers=2,
    )

    assert summary["returncode"] == 1
    assert summary["status"] == "failure"
    assert summary["candidates_total"] == 2
    assert summary["candidates_failed"] == 1
    assert summary["failed_results"][0]["candidate_path"] == str(failing_path)
    assert summary["failed_results"][0]["errors"] == ["final: missing ok flag"]


def test_main_validates_single_candidate_target(tmp_path: Path, capsys) -> None:
    schema_path = _write_schema(tmp_path / "candidate_schema.json")
    validator_path = _write_validator(tmp_path / "candidate_validator.py")
    candidate_path = _write_candidate(tmp_path / "single_candidate.json", ok=True)

    returncode = qdp_validation.main(
        [
            str(candidate_path),
            "--validator",
            str(validator_path),
            "--schema",
            str(schema_path),
        ]
    )
    captured = capsys.readouterr()

    assert returncode == 0
    assert "VALID" in captured.out
    assert str(candidate_path) in captured.out


def test_main_without_target_runs_candidate_sweep(tmp_path: Path, capsys) -> None:
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()
    schema_path = _write_schema(tmp_path / "candidate_schema.json")
    validator_path = _write_validator(tmp_path / "candidate_validator.py")
    _write_candidate(outputs_root / "alpha_candidate.json", ok=True)

    returncode = qdp_validation.main(
        [
            "--outputs-root",
            str(outputs_root),
            "--validator",
            str(validator_path),
            "--schema",
            str(schema_path),
        ]
    )
    captured = capsys.readouterr()

    assert returncode == 0
    assert "CHECK PASSED" in captured.out
    assert "- candidates_total: 1" in captured.out
