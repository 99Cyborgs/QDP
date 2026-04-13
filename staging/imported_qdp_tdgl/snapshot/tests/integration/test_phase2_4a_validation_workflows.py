from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner
import yaml

from tdgl_rf.cli import app
from tdgl_rf.testing.case_configs import read_json
from tdgl_rf.workflows import phase2_4a_validation as phase2_4a_validation_module
from tdgl_rf.workflows.phase2_4a_validation import run_phase2_4a_validation


def test_validate_phase2_4a_cli_committed_manifest_succeeds(tmp_path: Path) -> None:
    manifest_path = Path("validation/seeded_vortex_phase2_4a_validation_manifest.yaml").resolve()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["validate-phase2-4a", str(manifest_path), "--output-dir", str(tmp_path / "phase2_4a_validation_out")],
    )

    assert result.exit_code == 0
    assert '"status": "success"' in result.stdout
    payload = read_json(tmp_path / "phase2_4a_validation_out" / "phase2_4a_validation.json")
    markdown = (tmp_path / "phase2_4a_validation_out" / "phase2_4a_validation.md").read_text(encoding="utf-8")
    assert payload["overall_status"] == "success"
    assert payload["mismatch_count"] == 0
    assert payload["case_count"] == 9
    assert "same-stack runtime/control-plane surface only" in markdown


def test_validate_phase2_4a_cli_rejects_malformed_manifest(tmp_path: Path) -> None:
    malformed_manifest = tmp_path / "bad_validation_manifest.yaml"
    malformed_manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "tdgl_rf.seeded_vortex_phase2_4a_validation.v1",
                "validation_id": "bad",
                "claim_scope": "bad",
                "experiment_pack": "seeded_vortex_phase2_4a_experiment_pack.yaml",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["validate-phase2-4a", str(malformed_manifest)])

    assert result.exit_code == 1
    assert "Phase-2.4A validation manifest schema validation failed" in result.output


def test_validate_phase2_4a_cli_reports_failed_validation_artifacts_on_aggregate_mismatch(tmp_path: Path) -> None:
    source_manifest = yaml.safe_load(
        Path("validation/seeded_vortex_phase2_4a_validation_manifest.yaml").read_text(encoding="utf-8")
    )
    source_manifest["experiment_pack"] = str(Path("validation/seeded_vortex_phase2_4a_experiment_pack.yaml").resolve())
    source_manifest["expected_results"]["parameter_points"][0]["aggregates"]["early_window.mean_abs2_final"]["mean"] = 0.0
    mismatch_manifest = tmp_path / "mismatch_validation_manifest.yaml"
    mismatch_manifest.write_text(yaml.safe_dump(source_manifest, sort_keys=False), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["validate-phase2-4a", str(mismatch_manifest), "--output-dir", str(tmp_path / "mismatch_out")],
    )

    assert result.exit_code == 1
    payload = read_json(tmp_path / "mismatch_out" / "phase2_4a_validation.json")
    assert payload["overall_status"] == "failed"
    assert payload["mismatch_count"] >= 1
    assert any(
        record["surface"] == "parameter_point"
        and record["path"] == "aggregates.early_window.mean_abs2_final.mean"
        for record in payload["mismatch_records"]
    )


def test_validate_phase2_4a_missing_provenance_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = Path("validation/seeded_vortex_phase2_4a_validation_manifest.yaml").resolve()
    real_run = phase2_4a_validation_module.run_seeded_vortex_experiment_pack

    def _run_then_remove_provenance(manifest_path_arg, *, output_dir=None):
        summary = real_run(manifest_path_arg, output_dir=output_dir)
        payload = read_json(Path(summary.results_json_path))
        first_run_dir = Path(payload["run_records"][0]["run_dir"])
        (first_run_dir / "provenance.json").unlink()
        return summary

    monkeypatch.setattr(phase2_4a_validation_module, "run_seeded_vortex_experiment_pack", _run_then_remove_provenance)

    with pytest.raises(Exception, match="missing JSON payload"):
        run_phase2_4a_validation(manifest_path, output_dir=tmp_path / "missing_provenance_out")
