from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from tdgl_rf.testing.case_configs import base_case_payload, read_csv_rows, write_case_config
from tdgl_rf.workflows.run_case import run_simulation
from tdgl_rf.workflows.validation import _canonical_sha256, run_phase1_validation, run_reference_check, run_reproducibility_check


def _write_base_config(path: Path) -> None:
    payload = base_case_payload("validation_base", path.parent / "runs")
    payload["output"]["root_dir"] = str(path.parent / "runs")
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_matrix(path: Path, base_config_ref: str) -> None:
    rows = [
        {
            "case_id": "VAL_A",
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
            "goal": "small validation strip",
            "success_metric": "bounded residual",
            "promotion_rule": "gate:G1",
            "notes": "small strip row",
        },
        {
            "case_id": "VAL_B",
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
            "a_rf": 0.10,
            "omega": 3.0,
            "gamma_noise": 0.0,
            "dt": 0.01,
            "n_steps": 2,
            "ensemble_size": 1,
            "obs_stride": 1,
            "field_stride": 1,
            "goal": "small validation moat",
            "success_metric": "bounded residual",
            "promotion_rule": "gate:G1",
            "notes": "small moat row",
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _reference_manifest_entry(config_path: Path) -> dict[str, object]:
    summary = run_simulation(config_path)
    final_row = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))[-1]
    expected_final_observables = {
        "charge_residual_inf": float(final_row["charge_residual_inf"]),
        "mean_abs2": float(final_row["mean_abs2"]),
        "delta_f_over_f0": float(final_row["delta_f_over_f0"]),
        "qinv": float(final_row["qinv"]),
        "vortex_count": int(final_row["vortex_count"]),
    }
    hashed_final_observables = {
        "step": int(final_row["step"]),
        "t": float(final_row["t"]),
        "mean_abs2": float(final_row["mean_abs2"]),
        "charge_residual_inf": float(final_row["charge_residual_inf"]),
        "delta_f_over_f0": float(final_row["delta_f_over_f0"]),
        "qinv": float(final_row["qinv"]),
        "vortex_count": int(final_row["vortex_count"]),
        "supercurrent_l2": float(final_row["supercurrent_l2"]),
        "normalcurrent_l2": float(final_row["normalcurrent_l2"]),
        "max_abs2": float(final_row["max_abs2"]),
        "min_abs2": float(final_row["min_abs2"]),
    }
    payload_sha256 = _canonical_sha256({"summary_metrics": summary.summary_metrics, "final_observables": hashed_final_observables})
    return {
        "reference_id": "rf_reference",
        "kind": "config",
        "config_path": str(config_path),
        "command": f"tdgl-rf run-case {config_path}",
        "expected_files": [
            "observables/summary.json",
            "observables/timeseries.csv",
            "diagnostics/run_summary.json",
        ],
        "expected_summary": summary.summary_metrics,
        "expected_final_observables": expected_final_observables,
        "expected_payload_sha256": payload_sha256,
    }


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


def _write_thresholds(path: Path, reproducibility_config_path: Path, *, surface: dict[str, object] | None = None) -> None:
    payload = {
        "campaign": {
            "required_campaign_status": "success",
            "required_case_status": "success",
            "max_charge_residual_inf": 0.4,
            "max_vortex_count": 0,
        },
        "refinement": {
            "delta_mean_abs2_max": 1.0e-3,
            "delta_charge_residual_inf_max": 0.5,
            "delta_delta_f_over_f0_max": 1.0e-3,
            "delta_qinv_max": 1.0e-2,
        },
        "reproducibility": {
            "config_path": str(reproducibility_config_path),
            "summary_metric_tolerances": {
                "final_charge_residual_inf": 0.0,
                "final_mean_abs2": 0.0,
                "final_time": 0.0,
                "max_vortex_count": 0.0,
            },
            "final_observable_tolerances": {
                "charge_residual_inf": 0.0,
                "delta_f_over_f0": 0.0,
                "mean_abs2": 0.0,
                "qinv": 0.0,
                "vortex_count": 0.0,
            },
            "require_payload_hash_match": True,
        },
    }
    if surface is not None:
        payload["surface"] = surface
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def test_run_reference_check_on_config_manifest(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "reference_config",
        overrides={"forcing": {"a_rf": 0.15, "omega": 4.0, "phase": 0.2}},
    )
    manifest_path = tmp_path / "reference_manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump({"reference_runs": [_reference_manifest_entry(config_path)]}, sort_keys=False),
        encoding="utf-8",
    )

    summary = run_reference_check(manifest_path, output_dir=tmp_path / "reference_check")

    payload = json.loads(Path(summary.results_json_path).read_text(encoding="utf-8"))
    assert summary.status == "success"
    assert summary.reference_case_count == 1
    assert summary.passed_case_count == 1
    assert payload["records"][0]["status"] == "success"


def test_run_reproducibility_check_writes_pass_report(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "repro_case",
        overrides={"forcing": {"a_rf": 0.15, "omega": 4.0, "phase": 0.2}},
    )
    thresholds_path = tmp_path / "thresholds.yaml"
    _write_thresholds(thresholds_path, config_path)

    summary = run_reproducibility_check(config_path, tolerances_path=thresholds_path, output_dir=tmp_path / "repro")
    payload = json.loads(Path(summary.comparison_json_path).read_text(encoding="utf-8"))

    assert summary.status == "success"
    assert summary.exact_match is True
    assert payload["payload_hash_match"] is True
    assert all(row["pass"] for row in payload["comparison_rows"])


def test_run_phase1_validation_writes_summary_and_markdown(tmp_path: Path) -> None:
    base_config_path = tmp_path / "base.yaml"
    matrix_path = tmp_path / "matrix.csv"
    reference_manifest_path = tmp_path / "reference_manifest.yaml"
    thresholds_path = tmp_path / "thresholds.yaml"
    refinement_config_path = write_case_config(
        tmp_path,
        "refinement_case",
        overrides={
            "forcing": {"a_rf": 0.15, "omega": 4.0, "phase": 0.2},
            "time": {"n_steps": 2},
            "output": {"write_fields": False},
        },
    )
    reference_config_path = write_case_config(
        tmp_path,
        "reference_case",
        overrides={"forcing": {"a_rf": 0.15, "omega": 4.0, "phase": 0.2}},
    )

    _write_base_config(base_config_path)
    _write_matrix(matrix_path, "base.yaml")
    reference_manifest_path.write_text(
        yaml.safe_dump({"reference_runs": [_reference_manifest_entry(reference_config_path)]}, sort_keys=False),
        encoding="utf-8",
    )
    surface = _surface_metadata()
    _write_thresholds(thresholds_path, reference_config_path, surface=surface)

    summary = run_phase1_validation(
        matrix_path,
        thresholds_path=thresholds_path,
        reference_manifest_path=reference_manifest_path,
        refinement_config_path=refinement_config_path,
        output_dir=tmp_path / "validation_outputs",
    )

    validation_payload = json.loads(Path(summary.validation_summary_json_path).read_text(encoding="utf-8"))
    markdown = Path(summary.validation_report_path).read_text(encoding="utf-8")

    assert summary.status == "success"
    assert summary.campaign_case_count == 2
    assert summary.campaign_pass_count == 2
    assert summary.reference_case_count == 1
    assert summary.reference_pass_count == 1
    assert summary.reproducibility_passed is True
    assert validation_payload["overall_status"] == "success"
    assert validation_payload["surface"]["surface_id"] == surface["surface_id"]
    assert "## Campaign Cases" in markdown
    assert "Deterministic Phase-1 Short-Horizon" in markdown
    assert "Short-horizon deterministic strip and simple masked-strip baseline" in markdown
    assert "VAL_A" in markdown
    assert "rf_reference" in markdown
