from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def base_case_payload(case_id: str, output_root: Path) -> dict[str, Any]:
    return {
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
            "vortex_seeds": [],
            "pinning": {
                "model": "none",
                "seed": None,
                "mu": 0.0,
                "sigma": 0.0,
                "lcorr": 0.0,
                "defect_count": 0,
                "defects": [],
            },
        },
        "forcing": {"b_dc": 0.0, "a_rf": 0.0, "omega": 0.0, "phase": 0.0, "rf_profile": "uniform_y", "rf_profile_file": None},
        "noise": {"enabled": False, "strength": 0.0, "seed": 1234},
        "time": {"dt": 0.01, "n_steps": 4, "obs_stride": 1, "field_stride": 2, "checkpoint_stride": 2},
        "solver": {
            "backend": "scipy",
            "scheme": "imex_linearized",
            "psi_linear_solver": "gmres",
            "phi_linear_solver": "cg",
            "rtol": 1e-8,
            "atol": 1e-12,
            "max_it": 500,
        },
        "observables": {
            "track_vortices": True,
            "compute_frequency_shift_proxy": True,
            "compute_qinv_proxy": True,
            "weight_profile_f": "uniform",
            "weight_profile_q": "uniform",
            "c_f": 1.0,
            "c_q": 1.0,
            "qinv_bg": 0.0,
        },
        "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
        "output": {"root_dir": str(output_root), "write_fields": False, "write_observables": True, "compression": "none"},
        "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
    }


def deep_update(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_update(merged[key], value)
        else:
            merged[key] = value
    return merged


def write_case_config(tmp_path: Path, case_id: str, *, overrides: dict[str, Any] | None = None) -> Path:
    output_root = tmp_path / "runs"
    payload = base_case_payload(case_id, output_root)
    if overrides:
        payload = deep_update(payload, overrides)
    config_path = tmp_path / f"{case_id}.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def latest_run_dir(output_root: Path, case_id: str) -> Path:
    run_dirs = sorted((output_root / case_id).iterdir())
    assert len(run_dirs) == 1
    return run_dirs[0]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_mask(mask_path: Path, mask: np.ndarray) -> Path:
    np.save(mask_path, np.asarray(mask, dtype=bool))
    return mask_path
