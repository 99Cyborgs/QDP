from __future__ import annotations

from pathlib import Path

import yaml

from tdgl_rf.config.loaders import load_case_config


def test_config_base_inheritance(tmp_path: Path) -> None:
    base = {
        "base_config": None,
        "metadata": {"case_id": "base", "phase": "D", "version": "0.1.0"},
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
        "solver": {"backend": "scipy", "scheme": "imex_linearized", "psi_linear_solver": "gmres", "phi_linear_solver": "cg", "rtol": 1e-8, "atol": 1e-12, "max_it": 500},
        "observables": {"track_vortices": True, "compute_frequency_shift_proxy": True, "compute_qinv_proxy": True, "weight_profile_f": "uniform", "weight_profile_q": "uniform", "c_f": 1.0, "c_q": 1.0, "qinv_bg": 0.0},
        "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
        "output": {"root_dir": "runs", "write_fields": False, "write_observables": True, "compression": "none"},
        "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
    }
    base_path = tmp_path / "base.yaml"
    child_path = tmp_path / "child.yaml"
    base_path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    child_path.write_text(
        yaml.safe_dump(
            {
                "base_config": "base.yaml",
                "metadata": {"case_id": "child", "phase": "D", "version": "0.1.0"},
                "mesh": {"nx": 24},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    config = load_case_config(child_path)
    assert config.metadata.case_id == "child"
    assert config.mesh.nx == 24
    assert config.mesh.ny == 8
    assert config.output.write_fields is False

