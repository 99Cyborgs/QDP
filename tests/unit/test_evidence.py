from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner
import yaml

from tdgl_rf.cli import app
from tdgl_rf.config.loaders import repo_root
from tdgl_rf.testing.case_configs import base_case_payload
from tdgl_rf.workflows.evidence import (
    build_evidence_bundle,
    generate_limitations_markdown,
    generate_operating_conditions_markdown,
    generate_technical_summary_markdown,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_matrix(path: Path) -> None:
    rows = [
        {
            "case_id": "EVID_A",
            "phase": "D",
            "base_config": "phase1_matrix_base.yaml",
            "geometry_family": "strip",
            "nx": 16,
            "ny": 8,
            "pinning_model": "none",
            "pinning_mu": 0.0,
            "pinning_sigma": 0.0,
            "pinning_lcorr": 0.0,
            "defect_count": 0,
            "b_dc": 0.0,
            "a_rf": 0.05,
            "omega": 2.0,
            "gamma_noise": 0.0,
            "dt": 0.01,
            "n_steps": 4,
            "ensemble_size": 1,
            "obs_stride": 1,
            "field_stride": 2,
            "goal": "evidence fixture row a",
            "success_metric": "bounded residual",
            "promotion_rule": "gate:G1",
            "notes": "fixture row a",
        },
        {
            "case_id": "EVID_B",
            "phase": "D",
            "base_config": "phase1_matrix_base.yaml",
            "geometry_family": "strip_with_moat",
            "nx": 24,
            "ny": 12,
            "pinning_model": "none",
            "pinning_mu": 0.0,
            "pinning_sigma": 0.0,
            "pinning_lcorr": 0.0,
            "defect_count": 0,
            "b_dc": 0.0,
            "a_rf": 0.15,
            "omega": 4.0,
            "gamma_noise": 0.0,
            "dt": 0.01,
            "n_steps": 4,
            "ensemble_size": 1,
            "obs_stride": 1,
            "field_stride": 2,
            "goal": "evidence fixture row b",
            "success_metric": "bounded residual",
            "promotion_rule": "gate:G1",
            "notes": "fixture row b",
        },
    ]
    _write_csv(path, rows)


def _surface_metadata() -> dict[str, object]:
    return {
        "surface_id": "phase1_short_horizon",
        "display_name": "Deterministic Phase-1 Short-Horizon",
        "claim_scope": "Short-horizon deterministic strip and simple masked-strip baseline with conservative numerical gates on the committed n_steps=4 matrix surface only.",
        "reproduction_command": "tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml",
        "accepted_use": "Cite the current runtime as a short-horizon deterministic baseline for strip and simple masked-strip runs inside the committed matrix surface.",
        "not_established": [
            "Asymptotic convergence certification.",
            "PETSc parity or broader cross-stack reproducibility.",
            "Stochastic robustness or ensemble behavior.",
            "Seeded-vortex support or broader geometry support beyond the committed phase-1 surface.",
            "Longer-horizon or very-long-time stability beyond the committed n_steps=4 matrix.",
            "Broader physics-validation or external-benchmark claims.",
        ],
    }


def _write_thresholds(path: Path, *, surface: dict[str, object] | None = None) -> None:
    payload = {
        "campaign": {
            "required_campaign_status": "success",
            "required_case_status": "success",
            "max_charge_residual_inf": 0.45,
            "max_vortex_count": 0,
        },
        "refinement": {
            "delta_mean_abs2_max": 5.0e-4,
            "delta_charge_residual_inf_max": 0.25,
            "delta_delta_f_over_f0_max": 2.0e-4,
            "delta_qinv_max": 5.0e-3,
        },
        "reproducibility": {
            "config_path": "reference_rf_strip.yaml",
            "summary_metric_tolerances": {"final_mean_abs2": 0.0},
            "final_observable_tolerances": {"mean_abs2": 0.0},
            "require_payload_hash_match": True,
        },
    }
    if surface is not None:
        payload["surface"] = surface
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _write_manifest(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "reference_runs": [
                    {
                        "reference_id": "clean_strip",
                        "kind": "config",
                        "config_path": "reference_clean_strip.yaml",
                        "command": "tdgl-rf run-case reference_clean_strip.yaml",
                        "expected_files": ["observables/summary.json"],
                        "expected_summary": {},
                        "expected_final_observables": {},
                        "expected_payload_sha256": "abc123",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_refinement_config(path: Path) -> None:
    payload = base_case_payload("evidence_refinement", path.parent / "runs")
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_validation_fixture(tmp_path: Path, *, surface: dict[str, object] | None = None) -> tuple[Path, dict[str, object], Path, Path]:
    validation_dir = tmp_path / "validation"
    matrix_path = tmp_path / "phase1_validation_matrix_v1.csv"
    thresholds_path = tmp_path / "thresholds.yaml"
    manifest_path = tmp_path / "reference_manifest.yaml"
    refinement_config_path = tmp_path / "phase1_refinement_sanity.yaml"

    _write_matrix(matrix_path)
    _write_thresholds(thresholds_path, surface=surface)
    _write_manifest(manifest_path)
    _write_refinement_config(refinement_config_path)

    campaign_records = [
        {
            "case_id": "EVID_A",
            "geometry_family": "strip",
            "nx": 16,
            "ny": 8,
            "a_rf": 0.05,
            "omega": 2.0,
            "dt": 0.01,
            "campaign_row_status": "success",
            "overall_pass": True,
            "final_mean_abs2": 0.99997,
            "final_charge_residual_inf": 0.094878,
            "final_delta_f_over_f0": -2.6e-05,
            "final_qinv": 0.000401,
            "max_vortex_count": 0,
        },
        {
            "case_id": "EVID_B",
            "geometry_family": "strip_with_moat",
            "nx": 24,
            "ny": 12,
            "a_rf": 0.15,
            "omega": 4.0,
            "dt": 0.01,
            "campaign_row_status": "success",
            "overall_pass": True,
            "final_mean_abs2": 0.99975,
            "final_charge_residual_inf": 0.145564,
            "final_delta_f_over_f0": -0.000245,
            "final_qinv": 0.003803,
            "max_vortex_count": 0,
        },
    ]
    refinement_records = [
        {
            "case_id": "ref_16x8",
            "mesh_level": "16x8",
            "dt": 0.01,
            "delta_mean_abs2_vs_reference": 1.1e-4,
            "delta_charge_residual_inf_vs_reference": 0.21,
            "delta_delta_f_over_f0_vs_reference": 1.1e-4,
            "delta_qinv_vs_reference": 0.0032,
            "overall_pass": True,
        },
        {
            "case_id": "ref_24x12",
            "mesh_level": "24x12",
            "dt": 0.005,
            "delta_mean_abs2_vs_reference": 0.0,
            "delta_charge_residual_inf_vs_reference": 0.0,
            "delta_delta_f_over_f0_vs_reference": 0.0,
            "delta_qinv_vs_reference": 0.0,
            "overall_pass": True,
        },
    ]
    validation_payload: dict[str, object] = {
        "matrix_path": str(matrix_path.resolve()),
        "thresholds_path": str(thresholds_path.resolve()),
        "reference_manifest_path": str(manifest_path.resolve()),
        "refinement_config_path": str(refinement_config_path.resolve()),
        "overall_status": "success",
        "campaign": {
            "campaign_dir": str((tmp_path / "runs" / "campaign").resolve()),
            "case_count": 2,
            "pass_count": 2,
            "records": campaign_records,
        },
        "refinement": {
            "case_count": 2,
            "pass_count": 2,
            "reference_case_id": "ref_24x12",
            "records": refinement_records,
        },
        "reference": {
            "case_count": 2,
            "pass_count": 2,
            "records": [
                {"reference_id": "clean_strip", "payload_sha256_match": True, "status": "success", "notes": "matched manifest"},
                {"reference_id": "rf_driven_strip", "payload_sha256_match": True, "status": "success", "notes": "matched manifest"},
            ],
        },
        "reproducibility": {
            "overall_pass": True,
            "payload_hash_match": True,
            "notes": "Same-stack exact reproducibility matched.",
            "records": [{"label": "summary", "metric": "final_mean_abs2", "pass": True}],
        },
    }
    if surface is not None:
        validation_payload["surface"] = surface

    validation_dir.mkdir(parents=True, exist_ok=True)
    (validation_dir / "validation_summary.json").write_text(
        json.dumps(validation_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(validation_dir / "validation_summary.csv", campaign_records)
    (validation_dir / "validation_report.md").write_text(
        "# Phase-1 Validation Report\n\nFixture validation report.\n",
        encoding="utf-8",
    )
    (validation_dir / "campaign_summary").mkdir(parents=True, exist_ok=True)
    (validation_dir / "campaign_summary" / "proposal_summary.json").write_text(
        json.dumps({"rows": campaign_records}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(validation_dir / "campaign_summary" / "proposal_summary.csv", campaign_records)
    (validation_dir / "campaign_summary" / "proposal_summary.md").write_text(
        "# Campaign Summary\n\nFixture campaign summary.\n",
        encoding="utf-8",
    )
    (validation_dir / "reference_checks").mkdir(parents=True, exist_ok=True)
    (validation_dir / "reference_checks" / "reference_check.json").write_text(
        json.dumps({"records": validation_payload["reference"]["records"]}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (validation_dir / "reference_checks" / "reference_check.md").write_text(
        "# Frozen Reference Check\n\nFixture reference check.\n",
        encoding="utf-8",
    )
    (validation_dir / "refinement_sanity").mkdir(parents=True, exist_ok=True)
    refinement_payload = {"reference_case_id": "ref_24x12", "results": refinement_records}
    (validation_dir / "refinement_sanity" / "comparison_table.json").write_text(
        json.dumps(refinement_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(validation_dir / "refinement_sanity" / "comparison_table.csv", refinement_records)

    return validation_dir, validation_payload, matrix_path, thresholds_path


def test_build_evidence_bundle_writes_compact_bundle(tmp_path: Path) -> None:
    validation_dir, _, _, _ = _write_validation_fixture(tmp_path, surface=_surface_metadata())

    summary = build_evidence_bundle(validation_dir, output_dir=tmp_path / "bundle")

    manifest = json.loads(Path(summary.manifest_path).read_text(encoding="utf-8"))
    overview = Path(summary.overview_path).read_text(encoding="utf-8")
    technical_summary = Path(summary.technical_summary_path).read_text(encoding="utf-8")
    operating_conditions = Path(summary.operating_conditions_path).read_text(encoding="utf-8")
    limitations = Path(summary.limitations_path).read_text(encoding="utf-8")

    assert summary.status == "success"
    assert summary.copied_artifact_count == 17
    assert summary.generated_artifact_count == 5
    assert manifest["overall_status"] == "success"
    assert "Deterministic Phase-1 Short-Horizon Evidence Bundle" in overview
    assert "tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv" in overview
    assert "Deterministic Phase-1 Short-Horizon Technical Summary" in technical_summary
    assert "Claim scope: Short-horizon deterministic strip and simple masked-strip baseline" in technical_summary
    assert "Recorded Operating Conditions" in operating_conditions
    assert "Known Limitations And Unsupported Regimes" in limitations
    assert Path(summary.output_dir, "source_artifacts", "validation_report.md").exists()
    assert Path(summary.output_dir, "source_docs", "PHASE1_VALIDATION_MEMO.md").exists()


def test_build_evidence_bundle_requires_validation_report(tmp_path: Path) -> None:
    validation_dir, _, _, _ = _write_validation_fixture(tmp_path, surface=_surface_metadata())
    (validation_dir / "validation_report.md").unlink()

    with pytest.raises(FileNotFoundError, match="validation report markdown"):
        build_evidence_bundle(validation_dir, output_dir=tmp_path / "bundle")


def test_generate_operating_conditions_markdown_includes_thresholds_and_surface(tmp_path: Path) -> None:
    _, validation_payload, matrix_path, thresholds_path = _write_validation_fixture(tmp_path, surface=_surface_metadata())

    markdown = generate_operating_conditions_markdown(
        validation_payload,
        matrix_path=matrix_path,
        thresholds_path=thresholds_path,
    )

    assert "Deterministic Phase-1 Short-Horizon" in markdown
    assert "deterministic phase `D` only" in markdown
    assert "`final_charge_residual_inf <= 0.45`" in markdown
    assert "strip_with_moat" in markdown
    assert "0.0050" in markdown


def test_generate_limitations_markdown_groups_phase1_constraints() -> None:
    docs_root = repo_root() / "docs"

    markdown = generate_limitations_markdown(
        acceptance_path=docs_root / "PHASE1_ACCEPTANCE.md",
        memo_path=docs_root / "PHASE1_VALIDATION_MEMO.md",
    )

    assert "Stochastic noise / ensembles" in markdown
    assert "PETSc parity / larger-scale runs" in markdown
    assert "Long-horizon deterministic behavior" in markdown


def test_generate_technical_summary_markdown_falls_back_without_surface(tmp_path: Path) -> None:
    _, validation_payload, _, thresholds_path = _write_validation_fixture(tmp_path, surface=None)

    markdown = generate_technical_summary_markdown(validation_payload, thresholds_path=thresholds_path)

    assert "Deterministic Phase-1 Technical Summary" in markdown
    assert "## Surface Use" in markdown
    assert "Cite the current runtime as a short-horizon deterministic baseline" in markdown


def test_generate_technical_summary_markdown_keeps_long_horizon_use_informative(tmp_path: Path) -> None:
    surface = _surface_metadata()
    surface["surface_id"] = "phase1_longer_horizon"
    surface["display_name"] = "Deterministic Phase-1 Longer-Horizon"
    surface["claim_scope"] = "Committed longer-horizon deterministic follow-on tranche on the n_steps=8 matrix only."
    surface["accepted_use"] = (
        "Use this tranche only as an informative longer-horizon follow-on run through n_steps=8 for debugging and future gate decisions; do not cite it as accepted deterministic baseline evidence."
    )
    _, validation_payload, _, thresholds_path = _write_validation_fixture(tmp_path, surface=surface)

    markdown = generate_technical_summary_markdown(validation_payload, thresholds_path=thresholds_path)

    assert "## Surface Use" in markdown
    assert "informative longer-horizon follow-on run through n_steps=8" in markdown
    assert "accepted deterministic baseline evidence" in markdown


def test_evidence_bundle_cli_writes_bundle(tmp_path: Path) -> None:
    validation_dir, _, _, _ = _write_validation_fixture(tmp_path, surface=_surface_metadata())
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["evidence-bundle", str(validation_dir), "--output-dir", str(tmp_path / "bundle_cli")],
    )

    assert result.exit_code == 0
    assert '"status": "success"' in result.stdout
    assert (tmp_path / "bundle_cli" / "README.md").exists()
