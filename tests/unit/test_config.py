from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tdgl_rf.config.validators import validate_case_config
from tdgl_rf.config.loaders import load_case_config
from tdgl_rf.exceptions import ConfigError, SeedRejectionCode, SeedRejectionError


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


def test_config_allows_zero_step_runs(tmp_path: Path) -> None:
    config_path = tmp_path / "zero_step.yaml"
    payload = {
        "base_config": None,
        "metadata": {"case_id": "zero_step", "phase": "D", "version": "0.1.0"},
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
        "time": {"dt": 0.01, "n_steps": 0, "obs_stride": 1, "field_stride": 1, "checkpoint_stride": 1},
        "solver": {"backend": "scipy", "scheme": "imex_linearized", "psi_linear_solver": "gmres", "phi_linear_solver": "cg", "rtol": 1e-8, "atol": 1e-12, "max_it": 500},
        "observables": {"track_vortices": True, "compute_frequency_shift_proxy": True, "compute_qinv_proxy": True, "weight_profile_f": "uniform", "weight_profile_q": "uniform", "c_f": 1.0, "c_q": 1.0, "qinv_bg": 0.0},
        "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
        "output": {"root_dir": "runs", "write_fields": False, "write_observables": True, "compression": "none"},
        "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
    }
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    config = load_case_config(config_path)

    assert config.time.n_steps == 0


def test_config_accepts_legacy_noise_aliases_when_noise_is_disabled(tmp_path: Path) -> None:
    payload = {
        "base_config": None,
        "metadata": {"case_id": "legacy_noise_aliases", "phase": "D", "version": "0.1.0"},
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
    }

    config = validate_case_config(payload, Path("configs/tdgl_case.schema.json").resolve(), tmp_path)

    assert config.noise.enabled is False
    assert config.noise.strength == 0.0
    assert config.noise.seed == 1234


def test_config_rejects_negative_n_steps(tmp_path: Path) -> None:
    payload = {
        "base_config": None,
        "metadata": {"case_id": "negative_steps", "phase": "D", "version": "0.1.0"},
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
        "time": {"dt": 0.01, "n_steps": -1, "obs_stride": 1, "field_stride": 1, "checkpoint_stride": 1},
        "solver": {"backend": "scipy", "scheme": "imex_linearized", "psi_linear_solver": "gmres", "phi_linear_solver": "cg", "rtol": 1e-8, "atol": 1e-12, "max_it": 500},
        "observables": {"track_vortices": True, "compute_frequency_shift_proxy": True, "compute_qinv_proxy": True, "weight_profile_f": "uniform", "weight_profile_q": "uniform", "c_f": 1.0, "c_q": 1.0, "qinv_bg": 0.0},
        "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
        "output": {"root_dir": "runs", "write_fields": False, "write_observables": True, "compression": "none"},
        "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
    }

    with pytest.raises(ConfigError, match="n_steps"):
        validate_case_config(payload, Path("configs/tdgl_case.schema.json").resolve(), tmp_path)


def test_seeded_vortex_mode_conflict_has_explicit_taxonomy(tmp_path: Path) -> None:
    payload = {
        "base_config": None,
        "metadata": {"case_id": "seed_mode_conflict", "phase": "D", "version": "0.1.0"},
        "mesh": {"nx": 16, "ny": 8, "lx": 8.0, "ly": 4.0, "periodic_x": False, "periodic_y": False},
        "geometry": {"family": "strip", "moats": [], "holes": [], "mask_file": None},
        "physics": {
            "u": 5.79,
            "sigma_n": 1.0,
            "alpha_background": 1.0,
            "initial_condition": "meissner",
            "restart_file": None,
            "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
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
    }

    with pytest.raises(SeedRejectionError) as excinfo:
        validate_case_config(payload, Path("configs/tdgl_case.schema.json").resolve(), tmp_path)

    assert excinfo.value.code == SeedRejectionCode.UNEXPECTED_SEEDS
    assert excinfo.value.field_path == "physics.vortex_seeds"


def test_seeded_vortex_schema_error_has_explicit_taxonomy(tmp_path: Path) -> None:
    payload = {
        "base_config": None,
        "metadata": {"case_id": "seed_schema_invalid", "phase": "D", "version": "0.1.0"},
        "mesh": {"nx": 16, "ny": 8, "lx": 8.0, "ly": 4.0, "periodic_x": False, "periodic_y": False},
        "geometry": {"family": "strip", "moats": [], "holes": [], "mask_file": None},
        "physics": {
            "u": 5.79,
            "sigma_n": 1.0,
            "alpha_background": 1.0,
            "initial_condition": "seeded_vortices",
            "restart_file": None,
            "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 0}],
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
    }

    with pytest.raises(SeedRejectionError) as excinfo:
        validate_case_config(payload, Path("configs/tdgl_case.schema.json").resolve(), tmp_path)

    assert excinfo.value.code == SeedRejectionCode.SCHEMA_INVALID
    assert excinfo.value.seed_index == 0
    assert "winding" in str(excinfo.value)


def test_seeded_vortex_mask_rejection_has_explicit_taxonomy(tmp_path: Path) -> None:
    config_path = tmp_path / "masked_seed.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "base_config": None,
                "metadata": {"case_id": "seed_mask_invalid", "phase": "D", "version": "0.1.0"},
                "mesh": {"nx": 16, "ny": 8, "lx": 8.0, "ly": 4.0, "periodic_x": False, "periodic_y": False},
                "geometry": {"family": "strip_with_moat", "moats": [{"x0": 4.0, "y0": 2.0, "radius": 0.7}], "holes": [], "mask_file": None},
                "physics": {
                    "u": 5.79,
                    "sigma_n": 1.0,
                    "alpha_background": 1.0,
                    "initial_condition": "seeded_vortices",
                    "restart_file": None,
                    "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
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

    with pytest.raises(SeedRejectionError) as excinfo:
        load_case_config(config_path)

    assert excinfo.value.code == SeedRejectionCode.INACTIVE_PLAQUETTE
    assert excinfo.value.seed_index == 0


def test_config_requires_explicit_noise_seed_when_stochastic(tmp_path: Path) -> None:
    payload = {
        "base_config": None,
        "metadata": {"case_id": "stochastic_seed_required", "phase": "S", "version": "0.1.0"},
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
        "noise": {"enabled": True, "strength": 0.1, "master_seed": 1234},
        "time": {"dt": 0.01, "n_steps": 1, "obs_stride": 1, "field_stride": 1, "checkpoint_stride": 1},
        "solver": {"backend": "scipy", "scheme": "imex_linearized", "psi_linear_solver": "gmres", "phi_linear_solver": "cg", "rtol": 1e-8, "atol": 1e-12, "max_it": 100},
        "observables": {"track_vortices": True, "compute_frequency_shift_proxy": True, "compute_qinv_proxy": True, "weight_profile_f": "uniform", "weight_profile_q": "uniform", "c_f": 1.0, "c_q": 1.0, "qinv_bg": 0.0},
        "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
        "output": {"root_dir": "runs", "write_fields": False, "write_observables": True, "compression": "none"},
        "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
    }

    with pytest.raises(ConfigError, match="noise.seed is required") as excinfo:
        validate_case_config(payload, Path("configs/tdgl_case.schema.json").resolve(), tmp_path)

    assert "implicit RNG is rejected" in str(excinfo.value)


def test_config_requires_positive_noise_strength_when_stochastic(tmp_path: Path) -> None:
    payload = {
        "base_config": None,
        "metadata": {"case_id": "stochastic_strength_required", "phase": "S", "version": "0.1.0"},
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
        "noise": {"enabled": True, "strength": 0.0, "seed": 1234},
        "time": {"dt": 0.01, "n_steps": 1, "obs_stride": 1, "field_stride": 1, "checkpoint_stride": 1},
        "solver": {"backend": "scipy", "scheme": "imex_linearized", "psi_linear_solver": "gmres", "phi_linear_solver": "cg", "rtol": 1e-8, "atol": 1e-12, "max_it": 100},
        "observables": {"track_vortices": True, "compute_frequency_shift_proxy": True, "compute_qinv_proxy": True, "weight_profile_f": "uniform", "weight_profile_q": "uniform", "c_f": 1.0, "c_q": 1.0, "qinv_bg": 0.0},
        "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
        "output": {"root_dir": "runs", "write_fields": False, "write_observables": True, "compression": "none"},
        "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
    }

    with pytest.raises(ConfigError, match="noise.strength must be > 0"):
        validate_case_config(payload, Path("configs/tdgl_case.schema.json").resolve(), tmp_path)

