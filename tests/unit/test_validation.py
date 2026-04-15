from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import yaml

from tdgl_rf.exceptions import ConfigError
from tdgl_rf.workflows.validation import (
    evaluate_campaign_results,
    evaluate_refinement_results,
    load_reference_manifest,
    load_threshold_spec,
)


def _write_matrix(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _matrix_rows(base_config_ref: str) -> list[dict[str, object]]:
    return [
        {
            "case_id": "VAL01",
            "phase": "D",
            "base_config": base_config_ref,
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
            "n_steps": 2,
            "ensemble_size": 1,
            "obs_stride": 1,
            "field_stride": 1,
            "goal": "validation",
            "success_metric": "bounded residual",
            "promotion_rule": "gate:G1",
            "notes": "synthetic row 1",
        },
        {
            "case_id": "VAL02",
            "phase": "D",
            "base_config": base_config_ref,
            "geometry_family": "strip_with_moat",
            "nx": 16,
            "ny": 8,
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
            "n_steps": 2,
            "ensemble_size": 1,
            "obs_stride": 1,
            "field_stride": 1,
            "goal": "validation",
            "success_metric": "bounded residual",
            "promotion_rule": "gate:G1",
            "notes": "synthetic row 2",
        },
        {
            "case_id": "VAL03",
            "phase": "D",
            "base_config": base_config_ref,
            "geometry_family": "strip",
            "nx": 24,
            "ny": 12,
            "pinning_model": "none",
            "pinning_mu": 0.0,
            "pinning_sigma": 0.0,
            "pinning_lcorr": 0.0,
            "defect_count": 0,
            "b_dc": 0.0,
            "a_rf": 0.15,
            "omega": 2.0,
            "gamma_noise": 0.0,
            "dt": 0.01,
            "n_steps": 2,
            "ensemble_size": 1,
            "obs_stride": 1,
            "field_stride": 1,
            "goal": "validation",
            "success_metric": "bounded residual",
            "promotion_rule": "gate:G1",
            "notes": "synthetic row 3",
        },
    ]


def _write_thresholds(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "campaign": {
                    "required_campaign_status": "success",
                    "required_case_status": "success",
                    "max_charge_residual_inf": 0.4,
                    "max_vortex_count": 0,
                },
                "refinement": {
                    "delta_mean_abs2_max": 5.0e-4,
                    "delta_charge_residual_inf_max": 0.25,
                    "delta_delta_f_over_f0_max": 2.0e-4,
                    "delta_qinv_max": 5.0e-3,
                },
                "reproducibility": {
                    "config_path": "repro_case.yaml",
                    "summary_metric_tolerances": {"final_mean_abs2": 0.0},
                    "final_observable_tolerances": {"mean_abs2": 0.0},
                    "require_payload_hash_match": True,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _surface_metadata() -> dict[str, object]:
    return {
        "surface_id": "phase1_short_horizon",
        "display_name": "Deterministic Phase-1 Short-Horizon",
        "claim_scope": "Short-horizon deterministic strip and simple masked-strip baseline on the committed n_steps=4 matrix surface only.",
        "reproduction_command": "tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml",
        "accepted_use": "Cite the current runtime as a short-horizon deterministic baseline inside the committed matrix surface.",
        "not_established": [
            "Asymptotic convergence certification.",
            "PETSc parity.",
            "Stochastic robustness or ensemble behavior.",
        ],
    }


def _write_run_outputs(run_dir: Path, *, charge_residual: float, mean_abs2: float, include_timeseries: bool = True) -> None:
    (run_dir / "observables").mkdir(parents=True, exist_ok=True)
    (run_dir / "diagnostics").mkdir(parents=True, exist_ok=True)
    (run_dir / "observables" / "summary.json").write_text(
        json.dumps(
            {
                "final_charge_residual_inf": charge_residual,
                "final_mean_abs2": mean_abs2,
                "final_time": 0.02,
                "max_vortex_count": 0,
                "n_events": 0,
                "n_samples": 3,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "diagnostics" / "run_summary.json").write_text(
        json.dumps({"status": "success", "summary_metrics": {"final_charge_residual_inf": charge_residual}}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    if include_timeseries:
        with (run_dir / "observables" / "timeseries.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "step",
                    "t",
                    "mean_abs2",
                    "charge_residual_inf",
                    "delta_f_over_f0",
                    "qinv",
                    "vortex_count",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "step": 2,
                    "t": 0.02,
                    "mean_abs2": mean_abs2,
                    "charge_residual_inf": charge_residual,
                    "delta_f_over_f0": -0.0001,
                    "qinv": 0.001,
                    "vortex_count": 0,
                }
            )


def test_load_reference_manifest_rejects_duplicate_ids(tmp_path: Path) -> None:
    config_path = tmp_path / "case.yaml"
    config_path.write_text("base_config: null\nmetadata:\n  case_id: demo\n", encoding="utf-8")
    manifest_path = tmp_path / "reference_manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "reference_runs": [
                    {
                        "reference_id": "dup",
                        "kind": "config",
                        "config_path": "case.yaml",
                        "command": "tdgl-rf run-case case.yaml",
                        "expected_files": ["observables/summary.json"],
                        "expected_summary": {},
                        "expected_final_observables": {},
                        "expected_payload_sha256": "abc",
                    },
                    {
                        "reference_id": "dup",
                        "kind": "config",
                        "config_path": "case.yaml",
                        "command": "tdgl-rf run-case case.yaml",
                        "expected_files": ["observables/summary.json"],
                        "expected_summary": {},
                        "expected_final_observables": {},
                        "expected_payload_sha256": "def",
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="duplicate reference_id"):
        load_reference_manifest(manifest_path)


def test_load_threshold_spec_accepts_optional_surface_metadata(tmp_path: Path) -> None:
    thresholds_path = tmp_path / "thresholds.yaml"
    thresholds_path.write_text(
        yaml.safe_dump(
            {
                "surface": _surface_metadata(),
                "campaign": {"required_campaign_status": "success"},
                "refinement": {"delta_mean_abs2_max": 5.0e-4},
                "reproducibility": {"config_path": "repro_case.yaml"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    thresholds = load_threshold_spec(thresholds_path)

    assert thresholds["surface"]["surface_id"] == "phase1_short_horizon"
    assert thresholds["surface"]["display_name"] == "Deterministic Phase-1 Short-Horizon"
    assert thresholds["surface"]["not_established"][2] == "Stochastic robustness or ensemble behavior."


def test_load_threshold_spec_still_requires_numeric_sections(tmp_path: Path) -> None:
    thresholds_path = tmp_path / "thresholds.yaml"
    thresholds_path.write_text(
        yaml.safe_dump(
            {
                "surface": _surface_metadata(),
                "campaign": {"required_campaign_status": "success"},
                "reproducibility": {"config_path": "repro_case.yaml"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="missing 'refinement' section"):
        load_threshold_spec(thresholds_path)


def test_evaluate_campaign_results_handles_missing_rows_failed_cases_and_partial_outputs(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    thresholds_path = tmp_path / "thresholds.yaml"
    _write_matrix(matrix_path, _matrix_rows("base.yaml"))
    _write_thresholds(thresholds_path)

    valid_run = tmp_path / "case_runs" / "valid"
    partial_run = tmp_path / "case_runs" / "partial"
    _write_run_outputs(valid_run, charge_residual=0.1, mean_abs2=0.999)
    _write_run_outputs(partial_run, charge_residual=0.1, mean_abs2=0.999, include_timeseries=False)

    campaign_dir = tmp_path / "campaign"
    campaign_dir.mkdir()
    (campaign_dir / "campaign_state.json").write_text(
        json.dumps(
            {
                "summary": {"status": "success"},
                "rows": [
                    {"row_index": 1, "case_id": "VAL01", "status": "success", "run_dir": str(valid_run)},
                    {"row_index": 2, "case_id": "VAL02", "status": "failed", "run_dir": None},
                    {"row_index": 3, "case_id": "VAL03", "status": "success", "run_dir": str(partial_run)},
                    {"row_index": 99, "case_id": "MISSING", "status": "success", "run_dir": str(valid_run)},
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    evaluation = evaluate_campaign_results(campaign_dir, matrix_path=matrix_path, thresholds_path=thresholds_path)

    records = {record["case_id"]: record for record in evaluation["records"]}
    assert evaluation["case_count"] == 4
    assert evaluation["pass_count"] == 1
    assert not evaluation["overall_pass"]
    assert records["VAL01"]["overall_pass"] is True
    assert records["VAL02"]["notes"] == "campaign row status was 'failed'"
    assert "partial outputs:" in records["VAL03"]["notes"]
    assert records["MISSING"]["notes"] == "row index missing from source matrix"


def test_evaluate_campaign_results_flags_zero_rows(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    thresholds_path = tmp_path / "thresholds.yaml"
    _write_matrix(matrix_path, _matrix_rows("base.yaml"))
    _write_thresholds(thresholds_path)

    campaign_dir = tmp_path / "campaign"
    campaign_dir.mkdir()
    (campaign_dir / "campaign_state.json").write_text(
        json.dumps({"summary": {"status": "success"}, "rows": []}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    evaluation = evaluate_campaign_results(campaign_dir, matrix_path=matrix_path, thresholds_path=thresholds_path)

    assert evaluation["case_count"] == 0
    assert evaluation["pass_count"] == 0
    assert evaluation["overall_pass"] is False


def test_evaluate_refinement_results_applies_thresholds(tmp_path: Path) -> None:
    thresholds_path = tmp_path / "thresholds.yaml"
    _write_thresholds(thresholds_path)

    refinement_dir = tmp_path / "refinement"
    refinement_dir.mkdir()
    (refinement_dir / "comparison_table.json").write_text(
        json.dumps(
            {
                "reference_case_id": "REF",
                "results": [
                    {
                        "case_id": "REF",
                        "mesh_level": "16x8",
                        "dt": 0.01,
                        "delta_mean_abs2_vs_reference": 0.0,
                        "delta_charge_residual_inf_vs_reference": 0.0,
                        "delta_delta_f_over_f0_vs_reference": 0.0,
                        "delta_qinv_vs_reference": 0.0,
                    },
                    {
                        "case_id": "FLAGGED",
                        "mesh_level": "24x12",
                        "dt": 0.005,
                        "delta_mean_abs2_vs_reference": 1.0e-3,
                        "delta_charge_residual_inf_vs_reference": 0.3,
                        "delta_delta_f_over_f0_vs_reference": 3.0e-4,
                        "delta_qinv_vs_reference": 6.0e-3,
                    },
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    evaluation = evaluate_refinement_results(refinement_dir, thresholds_path=thresholds_path)

    assert evaluation["case_count"] == 2
    assert evaluation["pass_count"] == 1
    assert evaluation["overall_pass"] is False
    flagged = next(record for record in evaluation["records"] if record["case_id"] == "FLAGGED")
    assert flagged["overall_pass"] is False
