from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tdgl_rf.exceptions import SolverDivergenceError
from tdgl_rf.testing.case_configs import latest_run_dir, read_csv_rows, read_json, write_case_config, write_mask
from tdgl_rf.workflows.run_case import run_simulation


def test_clean_strip_acceptance_case(tmp_path: Path) -> None:
    config_path = write_case_config(tmp_path, "clean_strip")

    summary = run_simulation(config_path)
    run_dir = latest_run_dir(tmp_path / "runs", "clean_strip")
    summary_payload = read_json(Path(summary.observable_file_paths["summary"]))
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))
    status_payload = read_json(run_dir / "status.json")

    assert summary.status == "success"
    assert summary_payload["n_samples"] == 5
    assert summary_payload["max_vortex_count"] == 0
    assert summary_payload["final_time"] == pytest.approx(0.04)
    assert summary_payload["final_mean_abs2"] == pytest.approx(1.0, abs=1.0e-12)
    assert summary_payload["final_charge_residual_inf"] < 1.0e-12
    assert all(float(row["normalcurrent_l2"]) == 0.0 for row in rows)
    assert status_payload["status"] == "success"


def test_rf_driven_strip_acceptance_case(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "rf_driven_strip",
        overrides={"forcing": {"a_rf": 0.15, "omega": 4.0, "phase": 0.2}},
    )

    summary = run_simulation(config_path)
    summary_payload = read_json(Path(summary.observable_file_paths["summary"]))
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))

    assert summary.status == "success"
    assert summary_payload["n_samples"] == 5
    assert summary_payload["max_vortex_count"] == 0
    assert 0.99 < summary_payload["final_mean_abs2"] <= 1.0
    assert summary_payload["final_charge_residual_inf"] < 0.3
    assert max(float(row["normalcurrent_l2"]) for row in rows) > 0.0
    assert max(float(row["supercurrent_l2"]) for row in rows) > 0.0
    assert float(rows[-1]["delta_f_over_f0"]) < 0.0
    assert float(rows[-1]["qinv"]) > 0.0


def test_masked_moat_acceptance_case(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "masked_moat",
        overrides={
            "geometry": {
                "family": "strip_with_moat",
                "moats": [{"x0": 4.0, "y0": 2.0, "radius": 0.7}],
            },
            "forcing": {"a_rf": 0.1, "omega": 3.0, "phase": 0.1},
        },
    )

    summary = run_simulation(config_path)
    summary_payload = read_json(Path(summary.observable_file_paths["summary"]))
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))

    assert summary.status == "success"
    assert summary_payload["n_samples"] == 5
    assert summary_payload["max_vortex_count"] == 0
    assert 0.99 < summary_payload["final_mean_abs2"] <= 1.0
    assert summary_payload["final_charge_residual_inf"] < 0.4
    assert float(rows[-1]["delta_f_over_f0"]) < 0.0
    assert float(rows[-1]["qinv"]) > 0.0


def test_disconnected_custom_mask_is_rejected(tmp_path: Path) -> None:
    mask = np.zeros((16, 8), dtype=bool)
    mask[1:3, 1:3] = True
    mask[12:14, 5:7] = True
    write_mask(tmp_path / "disconnected_mask.npy", mask)
    config_path = write_case_config(
        tmp_path,
        "disconnected_custom_mask",
        overrides={
            "geometry": {
                "family": "custom_mask",
                "mask_file": "disconnected_mask.npy",
            }
        },
    )

    with pytest.raises(SolverDivergenceError, match="connected active mask"):
        run_simulation(config_path)
