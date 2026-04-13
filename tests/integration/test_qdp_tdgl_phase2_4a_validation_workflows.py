from __future__ import annotations

from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_META_MATERIALS_SRC = ROOT / "packages" / "qdp_meta_materials" / "src"
QDP_TDGL_SRC = ROOT / "packages" / "qdp_tdgl" / "src"

for path in (QDP_IO_SRC, QDP_META_MATERIALS_SRC, QDP_TDGL_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_tdgl.testing.case_configs import read_json
from qdp_tdgl.workflows import phase2_4a_validation as phase2_4a_validation_module
from qdp_tdgl.workflows.phase2_4a_validation import run_phase2_4a_validation


PHASE2_4A_VALIDATION_MANIFEST = (
    ROOT / "configs" / "validation" / "tdgl" / "seeded_vortex_phase2_4a_validation_manifest.yaml"
).resolve()
PHASE2_4A_EXPERIMENT_PACK = (
    ROOT / "configs" / "validation" / "tdgl" / "seeded_vortex_phase2_4a_experiment_pack.yaml"
).resolve()


def test_run_phase2_4a_validation_on_committed_manifest_succeeds(tmp_path: Path) -> None:
    summary = run_phase2_4a_validation(
        PHASE2_4A_VALIDATION_MANIFEST,
        output_dir=tmp_path / "phase2_4a_validation_out",
    )

    payload = read_json(tmp_path / "phase2_4a_validation_out" / "phase2_4a_validation.json")
    markdown = (tmp_path / "phase2_4a_validation_out" / "phase2_4a_validation.md").read_text(encoding="utf-8")

    assert summary.status == "success"
    assert payload["overall_status"] == "success"
    assert payload["mismatch_count"] == 0
    assert payload["case_count"] == 9
    assert "same-stack runtime/control-plane surface only" in markdown


def test_run_phase2_4a_validation_reports_failed_artifacts_on_aggregate_mismatch(tmp_path: Path) -> None:
    source_manifest = yaml.safe_load(PHASE2_4A_VALIDATION_MANIFEST.read_text(encoding="utf-8"))
    source_manifest["experiment_pack"] = str(PHASE2_4A_EXPERIMENT_PACK)
    source_manifest["expected_results"]["parameter_points"][0]["aggregates"]["early_window.mean_abs2_final"]["mean"] = 0.0
    mismatch_manifest = tmp_path / "mismatch_validation_manifest.yaml"
    mismatch_manifest.write_text(yaml.safe_dump(source_manifest, sort_keys=False), encoding="utf-8")

    summary = run_phase2_4a_validation(
        mismatch_manifest,
        output_dir=tmp_path / "mismatch_out",
    )

    payload = read_json(tmp_path / "mismatch_out" / "phase2_4a_validation.json")

    assert summary.status == "failed"
    assert payload["overall_status"] == "failed"
    assert payload["mismatch_count"] >= 1
    assert any(
        record["surface"] == "parameter_point"
        and record["path"] == "aggregates.early_window.mean_abs2_final.mean"
        for record in payload["mismatch_records"]
    )


def test_phase2_4a_missing_provenance_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_run = phase2_4a_validation_module.run_seeded_vortex_experiment_pack

    def _run_then_remove_provenance(manifest_path_arg, *, output_dir=None):
        summary = real_run(manifest_path_arg, output_dir=output_dir)
        payload = read_json(Path(summary.results_json_path))
        first_run_dir = Path(payload["run_records"][0]["run_dir"])
        (first_run_dir / "provenance.json").unlink()
        return summary

    monkeypatch.setattr(phase2_4a_validation_module, "run_seeded_vortex_experiment_pack", _run_then_remove_provenance)

    with pytest.raises(Exception, match="missing JSON payload"):
        run_phase2_4a_validation(
            PHASE2_4A_VALIDATION_MANIFEST,
            output_dir=tmp_path / "missing_provenance_out",
        )
