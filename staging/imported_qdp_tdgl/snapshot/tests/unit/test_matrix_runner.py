from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import yaml

from tdgl_rf.exceptions import ConfigError
from tdgl_rf.workflows.run_matrix import build_execution_config, filter_matrix_rows, load_experiment_matrix, run_experiment_matrix


def _minimal_base_config() -> dict:
    return {
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
        "time": {"dt": 0.01, "n_steps": 2, "obs_stride": 1, "field_stride": 1, "checkpoint_stride": 1},
        "solver": {"backend": "scipy", "scheme": "imex_linearized", "psi_linear_solver": "gmres", "phi_linear_solver": "cg", "rtol": 1e-8, "atol": 1e-12, "max_it": 100},
        "observables": {"track_vortices": True, "compute_frequency_shift_proxy": True, "compute_qinv_proxy": True, "weight_profile_f": "uniform", "weight_profile_q": "uniform", "c_f": 1.0, "c_q": 1.0, "qinv_bg": 0.0},
        "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
        "output": {"root_dir": "runs", "write_fields": False, "write_observables": True, "compression": "none"},
        "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
    }


def _write_matrix(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_base_config(path: Path) -> None:
    path.write_text(yaml.safe_dump(_minimal_base_config(), sort_keys=False), encoding="utf-8")


def _two_row_matrix(base_config_ref: str) -> list[dict[str, object]]:
    return [
        {
            "case_id": "D01",
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
            "notes": "tiny deterministic row",
        },
        {
            "case_id": "S01",
            "phase": "S",
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
            "a_rf": 0.0,
            "omega": 0.0,
            "gamma_noise": 0.001,
            "dt": 0.01,
            "n_steps": 1,
            "ensemble_size": 2,
            "obs_stride": 1,
            "field_stride": 1,
            "goal": "stochastic smoke",
            "success_metric": "records unsupported noise row",
            "promotion_rule": "gate:G2",
            "notes": "expected semantic failure in current phase",
        },
    ]


def test_load_matrix_and_filter_selectors(tmp_path: Path) -> None:
    base_path = tmp_path / "base.yaml"
    matrix_path = tmp_path / "matrix.csv"
    _write_base_config(base_path)
    _write_matrix(matrix_path, _two_row_matrix("base.yaml"))

    rows = load_experiment_matrix(matrix_path)
    selected = filter_matrix_rows(rows, ["phase=D"])

    assert len(rows) == 2
    assert [row.case_id for row in selected] == ["D01"]
    assert rows[0].values["nx"] == 16


def test_run_matrix_dry_run_reports_validation_failures(tmp_path: Path) -> None:
    base_path = tmp_path / "base.yaml"
    matrix_path = tmp_path / "matrix.csv"
    _write_base_config(base_path)
    _write_matrix(matrix_path, _two_row_matrix("base.yaml"))

    summary = run_experiment_matrix(matrix_path, dry_run=True)

    assert summary.status == "dry_run_with_issues"
    assert summary.validated_count == 1
    assert summary.failed_count == 1

    state = json.loads(Path(summary.state_path).read_text(encoding="utf-8"))
    statuses = {row["case_id"]: row["status"] for row in state["rows"]}
    assert statuses["D01"] == "validated"
    assert statuses["S01"] == "failed"


def test_run_matrix_resume_skips_success_and_retries_failures(tmp_path: Path) -> None:
    base_path = tmp_path / "base.yaml"
    matrix_path = tmp_path / "matrix.csv"
    _write_base_config(base_path)
    _write_matrix(matrix_path, _two_row_matrix("base.yaml"))

    first = run_experiment_matrix(matrix_path)
    assert first.status == "partial_failure"
    assert first.success_count == 1
    assert first.failed_count == 1

    second = run_experiment_matrix(matrix_path, resume_dir=first.campaign_dir)
    assert second.status == "partial_failure"
    assert second.skipped_success_count >= 1
    assert second.attempted_row_count == 3

    state = json.loads(Path(second.state_path).read_text(encoding="utf-8"))
    rows = {row["case_id"]: row for row in state["rows"]}
    assert rows["D01"]["status"] == "success"
    assert rows["D01"]["attempts"] == 1
    assert rows["S01"]["status"] == "failed"
    assert rows["S01"]["attempts"] == 2


def test_gaussian_defect_rows_receive_deterministic_defaults(tmp_path: Path) -> None:
    base_path = tmp_path / "base.yaml"
    matrix_path = tmp_path / "matrix.csv"
    _write_base_config(base_path)
    rows = _two_row_matrix("base.yaml")
    rows[0]["case_id"] = "D04"
    rows[0]["pinning_model"] = "gaussian_defects"
    rows[0]["defect_count"] = 3
    rows[0]["goal"] = "defect defaults"
    rows[0]["success_metric"] = "expands"
    rows = [rows[0]]
    _write_matrix(matrix_path, rows)

    row = load_experiment_matrix(matrix_path)[0]
    campaign_dir = tmp_path / "campaign"
    campaign_dir.mkdir()
    snapshot, _, _ = build_execution_config(row, matrix_path, campaign_dir)

    defects = snapshot["physics"]["pinning"]["defects"]
    assert len(defects) == 3
    assert all(defect["amplitude"] == 1.0 for defect in defects)
    assert all(defect["width"] > 0.0 for defect in defects)


def test_strip_with_moat_rows_receive_default_exclusion(tmp_path: Path) -> None:
    base_path = tmp_path / "base.yaml"
    matrix_path = tmp_path / "matrix.csv"
    _write_base_config(base_path)
    rows = _two_row_matrix("base.yaml")
    rows[0]["case_id"] = "D05"
    rows[0]["geometry_family"] = "strip_with_moat"
    rows[0]["goal"] = "moat defaults"
    rows[0]["success_metric"] = "expands"
    rows = [rows[0]]
    _write_matrix(matrix_path, rows)

    row = load_experiment_matrix(matrix_path)[0]
    campaign_dir = tmp_path / "campaign"
    campaign_dir.mkdir()
    snapshot, _, _ = build_execution_config(row, matrix_path, campaign_dir)

    moats = snapshot["geometry"]["moats"]
    assert len(moats) == 1
    assert moats[0]["x0"] == 4.0
    assert moats[0]["y0"] == 2.0
    assert moats[0]["radius"] > 0.0


def test_resume_refuses_rows_marked_running(tmp_path: Path) -> None:
    base_path = tmp_path / "base.yaml"
    matrix_path = tmp_path / "matrix.csv"
    _write_base_config(base_path)
    _write_matrix(matrix_path, [_two_row_matrix("base.yaml")[0]])

    summary = run_experiment_matrix(matrix_path, dry_run=True)
    state_path = Path(summary.state_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["dry_run"] = False
    state["summary"]["status"] = "partial_failure"
    state["summary"]["attempted_row_count"] = 1
    state["rows"][0]["status"] = "running"
    state["rows"][0]["attempts"] = 1
    state["rows"][0]["start_timestamp"] = "2026-04-02T00:00:00"
    state["rows"][0]["stop_timestamp"] = None
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ConfigError, match="still marked running"):
        run_experiment_matrix(matrix_path, resume_dir=summary.campaign_dir)
