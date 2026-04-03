from __future__ import annotations

import csv
from pathlib import Path

import yaml
from typer.testing import CliRunner

from tdgl_rf.cli import app
from tdgl_rf.testing.case_configs import write_case_config


def test_validate_config_cli() -> None:
    runner = CliRunner()
    config_path = Path("configs/d01_smoke.yaml").resolve()
    result = runner.invoke(app, ["validate-config", str(config_path)])
    assert result.exit_code == 0
    assert '"case_id": "D01_smoke"' in result.stdout


def test_run_matrix_dry_run_cli(tmp_path: Path) -> None:
    base_path = tmp_path / "base.yaml"
    matrix_path = tmp_path / "matrix.csv"
    base_path.write_text(
        yaml.safe_dump(
            {
                "base_config": None,
                "metadata": {"case_id": "base", "phase": "D", "version": "0.1.0", "description": "", "tags": []},
                "mesh": {"nx": 16, "ny": 8, "lx": 8.0, "ly": 4.0, "periodic_x": False, "periodic_y": False},
                "geometry": {"family": "strip", "moats": [], "holes": [], "mask_file": None},
                "physics": {
                    "u": 5.79,
                    "sigma_n": 1.0,
                    "alpha_background": 1.0,
                    "initial_condition": "meissner",
                    "restart_file": None,
                    "pinning": {"model": "none", "seed": None, "mu": 0.0, "sigma": 0.0, "lcorr": 0.0, "defect_count": 0, "defects": []},
                },
                "forcing": {"b_dc": 0.0, "a_rf": 0.0, "omega": 0.0, "phase": 0.0, "rf_profile": "uniform_y", "rf_profile_file": None},
                "noise": {"enabled": False, "gamma_psi": 0.0, "master_seed": 1234},
                "time": {"dt": 0.01, "n_steps": 1, "obs_stride": 1, "field_stride": 1, "checkpoint_stride": 1},
                "solver": {"backend": "scipy", "scheme": "imex_linearized", "psi_linear_solver": "gmres", "phi_linear_solver": "cg", "rtol": 1e-8, "atol": 1e-12, "max_it": 100},
                "observables": {"track_vortices": True, "compute_frequency_shift_proxy": True, "compute_qinv_proxy": True, "weight_profile_f": "uniform", "weight_profile_q": "uniform", "c_f": 1.0, "c_q": 1.0, "qinv_bg": 0.0},
                "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
                "output": {"root_dir": "runs", "write_fields": False, "write_observables": True, "compression": "none"},
                "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    with matrix_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "phase",
                "base_config",
                "geometry_family",
                "nx",
                "ny",
                "pinning_model",
                "pinning_mu",
                "pinning_sigma",
                "pinning_lcorr",
                "defect_count",
                "b_dc",
                "a_rf",
                "omega",
                "gamma_noise",
                "dt",
                "n_steps",
                "ensemble_size",
                "obs_stride",
                "field_stride",
                "goal",
                "success_metric",
                "promotion_rule",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "D01",
                "phase": "D",
                "base_config": "base.yaml",
                "geometry_family": "strip",
                "nx": 16,
                "ny": 8,
                "pinning_model": "none",
                "pinning_mu": 0.0,
                "pinning_sigma": 0.0,
                "pinning_lcorr": 0.0,
                "defect_count": 0,
                "b_dc": 0.0,
                "a_rf": 0.0,
                "omega": 0.0,
                "gamma_noise": 0.0,
                "dt": 0.01,
                "n_steps": 1,
                "ensemble_size": 1,
                "obs_stride": 1,
                "field_stride": 1,
                "goal": "deterministic smoke",
                "success_metric": "completes",
                "promotion_rule": "gate:G1",
                "notes": "cli dry-run",
            }
        )

    runner = CliRunner()
    result = runner.invoke(app, ["run-matrix", str(matrix_path), "--dry-run", "--selector", "case_id=D01"])
    assert result.exit_code == 0
    assert '"status": "dry_run"' in result.stdout
    assert '"selected_row_count": 1' in result.stdout


def test_refinement_sanity_cli(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "cli_refinement",
        overrides={
            "forcing": {"a_rf": 0.15, "omega": 4.0, "phase": 0.2},
            "time": {"n_steps": 4},
            "output": {"write_fields": False},
        },
    )

    runner = CliRunner()
    result = runner.invoke(app, ["refinement-sanity", str(config_path), "--output-dir", str(tmp_path / "refinement_outputs")])

    assert result.exit_code == 0
    assert '"status": "success"' in result.stdout
    assert '"case_count": 4' in result.stdout
