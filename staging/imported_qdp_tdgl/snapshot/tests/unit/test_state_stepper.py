from __future__ import annotations

from pathlib import Path

import numpy as np

from tdgl_rf.config.models import TDGLRFCaseConfig
from tdgl_rf.fields.forcing import evaluate_forcing
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.solvers.state import initialize_state
from tdgl_rf.solvers.tdgl_stepper import TDGLStepper


def _build_config(dt: float = 0.05) -> TDGLRFCaseConfig:
    return TDGLRFCaseConfig.model_validate(
        {
            "base_config": None,
            "metadata": {"case_id": "forcing_alignment", "phase": "D", "version": "0.1.0", "description": "", "tags": []},
            "mesh": {"nx": 8, "ny": 8, "lx": 4.0, "ly": 4.0, "periodic_x": False, "periodic_y": False},
            "geometry": {"family": "strip", "moats": [], "holes": [], "mask_file": None},
            "physics": {
                "u": 5.79,
                "sigma_n": 1.0,
                "alpha_background": 1.0,
                "initial_condition": "meissner",
                "restart_file": None,
                "pinning": {"model": "none", "seed": None, "mu": 0.0, "sigma": 0.0, "lcorr": 0.0, "defect_count": 0, "defects": []},
            },
            "forcing": {"b_dc": 0.0, "a_rf": 0.4, "omega": 20.0, "phase": 0.3, "rf_profile": "uniform_y", "rf_profile_file": None},
            "noise": {"enabled": False, "gamma_psi": 0.0, "master_seed": 1234},
            "time": {"dt": dt, "n_steps": 1, "obs_stride": 1, "field_stride": 1, "checkpoint_stride": 1},
            "solver": {"backend": "scipy", "scheme": "imex_linearized", "psi_linear_solver": "spsolve", "phi_linear_solver": "spsolve", "rtol": 1e-10, "atol": 1e-12, "max_it": 100},
            "observables": {"track_vortices": True, "compute_frequency_shift_proxy": True, "compute_qinv_proxy": True, "weight_profile_f": "uniform", "weight_profile_q": "uniform", "c_f": 1.0, "c_q": 1.0, "qinv_bg": 0.0},
            "inference": {"enabled": False, "mode": "none", "infer_parameters": [], "dataset_path": None, "summary_statistics": []},
            "output": {"root_dir": "runs", "write_fields": False, "write_observables": True, "compression": "none"},
            "campaign": {"ensemble_size": 1, "matrix_row_id": None, "promotion_rule": None},
        }
    )


def test_initialize_state_evaluates_forcing_at_t0() -> None:
    grid = StructuredGrid2D(nx=8, ny=8, lx=4.0, ly=4.0)
    mask = GeometryMask(cell_active=np.ones((grid.nx, grid.ny), dtype=bool))
    config = _build_config()

    state = initialize_state(grid, mask, config, Path("."))
    expected_a, expected_a_dot = evaluate_forcing(grid, config.forcing, 0.0, config_dir=Path("."))

    np.testing.assert_allclose(state.A.ax, expected_a.ax)
    np.testing.assert_allclose(state.A.ay, expected_a.ay)
    np.testing.assert_allclose(state.A_dot.ax, expected_a_dot.ax)
    np.testing.assert_allclose(state.A_dot.ay, expected_a_dot.ay)
    assert not np.allclose(state.A.ay, 0.0)


def test_stepper_advance_returns_forcing_aligned_with_state_time() -> None:
    grid = StructuredGrid2D(nx=8, ny=8, lx=4.0, ly=4.0)
    mask = GeometryMask(cell_active=np.ones((grid.nx, grid.ny), dtype=bool))
    config = _build_config()
    alpha = np.ones((grid.nx, grid.ny), dtype=float)
    stepper = TDGLStepper(grid, mask, alpha, config, Path("."))
    state0 = initialize_state(grid, mask, config, Path("."))

    state1 = stepper.advance(state0)
    expected_a, expected_a_dot = evaluate_forcing(grid, config.forcing, state1.t, config_dir=Path("."))
    old_a, old_a_dot = evaluate_forcing(grid, config.forcing, state0.t, config_dir=Path("."))

    assert np.isclose(state1.t, config.time.dt)
    assert state1.step == 1
    np.testing.assert_allclose(state1.A.ax, expected_a.ax)
    np.testing.assert_allclose(state1.A.ay, expected_a.ay)
    np.testing.assert_allclose(state1.A_dot.ax, expected_a_dot.ax)
    np.testing.assert_allclose(state1.A_dot.ay, expected_a_dot.ay)
    assert not np.allclose(state1.A.ay, old_a.ay)
    assert not np.allclose(state1.A_dot.ay, old_a_dot.ay)
