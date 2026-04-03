from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from tdgl_rf.workflows.run_case import run_simulation


def _write_case_config(
    tmp_path: Path,
    case_id: str,
    *,
    n_steps: int,
    obs_stride: int,
    write_observables: bool,
) -> Path:
    config_path = tmp_path / f"{case_id}.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "base_config": None,
                "metadata": {"case_id": case_id, "phase": "D", "version": "0.1.0", "description": "", "tags": []},
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
                "forcing": {"b_dc": 0.0, "a_rf": 0.15, "omega": 4.0, "phase": 0.2, "rf_profile": "uniform_y", "rf_profile_file": None},
                "noise": {"enabled": False, "gamma_psi": 0.0, "master_seed": 1234},
                "time": {"dt": 0.01, "n_steps": n_steps, "obs_stride": obs_stride, "field_stride": 1, "checkpoint_stride": 1},
                "solver": {"backend": "scipy", "scheme": "imex_linearized", "psi_linear_solver": "gmres", "phi_linear_solver": "cg", "rtol": 1e-8, "atol": 1e-12, "max_it": 500},
                "observables": {"track_vortices": True, "compute_frequency_shift_proxy": True, "compute_qinv_proxy": True, "weight_profile_f": "uniform", "weight_profile_q": "uniform", "c_f": 1.0, "c_q": 1.0, "qinv_bg": 0.0},
                "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
                "output": {"root_dir": str(tmp_path / "runs"), "write_fields": False, "write_observables": write_observables, "compression": "none"},
                "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return config_path


def _run_dir(output_root: Path, case_id: str) -> Path:
    run_dirs = sorted((output_root / case_id).iterdir())
    assert len(run_dirs) == 1
    return run_dirs[0]


def test_run_simulation_appends_terminal_observable_sample(tmp_path: Path) -> None:
    config_path = _write_case_config(tmp_path, "terminal_sample", n_steps=3, obs_stride=2, write_observables=True)

    summary = run_simulation(config_path)
    summary_path = Path(summary.observable_file_paths["summary"])
    timeseries_path = Path(summary.observable_file_paths["timeseries"])

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    with timeseries_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 3
    assert float(rows[-1]["t"]) == 0.03
    assert summary_payload["final_time"] == 0.03
    assert summary_payload["final_time"] == float(rows[-1]["t"])
    assert summary_payload["final_mean_abs2"] == float(rows[-1]["mean_abs2"])


def test_run_simulation_respects_write_observables_flag(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = _write_case_config(tmp_path, "no_observables", n_steps=2, obs_stride=1, write_observables=False)

    summary = run_simulation(config_path)
    run_dir = _run_dir(output_root, "no_observables")
    observables_dir = run_dir / "observables"
    status_payload = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))

    assert summary.observable_file_paths == {}
    assert status_payload["observable_file_paths"] == {}
    assert list(observables_dir.iterdir()) == []
