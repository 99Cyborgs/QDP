from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tdgl_rf.fields.currents import compute_normal_current, compute_supercurrent
from tdgl_rf.fields.forcing import VectorPotential
from tdgl_rf.fields.linkvars import apply_gauge_transform, build_link_variables
from tdgl_rf.fields.observables import build_weight_profile, compute_basic_observables
from tdgl_rf.geometry.masks import GeometryMask, StructuredGrid2D
from tdgl_rf.solvers.state import SimulationState
from tdgl_rf.testing.case_configs import read_csv_rows, write_case_config
from tdgl_rf.workflows.run_case import run_simulation


def test_gauge_observable_invariance_sanity() -> None:
    grid = StructuredGrid2D(nx=10, ny=8, lx=5.0, ly=4.0)
    mask = GeometryMask(cell_active=np.ones((grid.nx, grid.ny), dtype=bool))
    rng = np.random.default_rng(42)

    amplitude = 0.75 + 0.05 * rng.standard_normal((grid.nx, grid.ny))
    phase = 0.3 * rng.standard_normal((grid.nx, grid.ny))
    psi = amplitude * np.exp(1j * phase)
    potential = VectorPotential(
        ax=0.05 * rng.standard_normal((grid.nx + 1, grid.ny)),
        ay=0.05 * rng.standard_normal((grid.nx, grid.ny + 1)),
    )
    chi = np.zeros((grid.nx, grid.ny), dtype=float)
    chi[1:-1, 1:-1] = 0.2 * rng.standard_normal((grid.nx - 2, grid.ny - 2))

    psi_t, potential_t = apply_gauge_transform(grid, psi, potential, chi)
    state = SimulationState(
        grid=grid,
        t=0.0,
        step=0,
        psi=psi,
        phi=np.zeros((grid.nx, grid.ny), dtype=float),
        A=potential,
        A_dot=VectorPotential.zeros(grid),
    )
    state_t = SimulationState(
        grid=grid,
        t=0.0,
        step=0,
        psi=psi_t,
        phi=np.zeros((grid.nx, grid.ny), dtype=float),
        A=potential_t,
        A_dot=VectorPotential.zeros(grid),
    )
    weights = build_weight_profile(grid, "uniform", mask=mask)

    obs = compute_basic_observables(
        state,
        mask,
        build_link_variables(grid, potential),
        compute_supercurrent(grid, mask, psi, build_link_variables(grid, potential)),
        compute_normal_current(grid, mask, state.phi, state.A_dot, sigma_n=1.0),
        weights,
        weights,
        track_vortices=True,
        compute_freq=True,
        compute_qinv=True,
        c_f=1.0,
        c_q=1.0,
        qinv_bg=0.0,
    )
    obs_t = compute_basic_observables(
        state_t,
        mask,
        build_link_variables(grid, potential_t),
        compute_supercurrent(grid, mask, psi_t, build_link_variables(grid, potential_t)),
        compute_normal_current(grid, mask, state_t.phi, state_t.A_dot, sigma_n=1.0),
        weights,
        weights,
        track_vortices=True,
        compute_freq=True,
        compute_qinv=True,
        c_f=1.0,
        c_q=1.0,
        qinv_bg=0.0,
    )

    assert obs_t["mean_abs2"] == pytest.approx(obs["mean_abs2"], rel=0.0, abs=1.0e-12)
    assert obs_t["supercurrent_l2"] == pytest.approx(obs["supercurrent_l2"], rel=0.0, abs=1.0e-12)
    assert obs_t["charge_residual_inf"] == pytest.approx(obs["charge_residual_inf"], rel=0.0, abs=1.0e-12)
    assert obs_t["vortex_count"] == obs["vortex_count"]
    assert obs_t["delta_f_over_f0"] == pytest.approx(obs["delta_f_over_f0"], rel=0.0, abs=1.0e-12)
    assert obs_t["qinv"] == pytest.approx(obs["qinv"], rel=0.0, abs=1.0e-12)


def test_short_driven_run_keeps_charge_residual_bounded(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "charge_residual_sanity",
        overrides={"forcing": {"a_rf": 0.15, "omega": 4.0, "phase": 0.2}},
    )

    summary = run_simulation(config_path)
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))
    residuals = [float(row["charge_residual_inf"]) for row in rows]

    assert summary.status == "success"
    assert max(residuals) < 0.4
    assert all(lhs >= rhs - 1.0e-12 for lhs, rhs in zip(residuals, residuals[1:]))
    assert residuals[-1] < 0.2


def test_meissner_relaxation_sanity_in_no_drive_case(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "meissner_relaxation",
        overrides={"time": {"n_steps": 6}},
    )

    summary = run_simulation(config_path)
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))

    assert summary.status == "success"
    assert all(float(row["vortex_count"]) == 0 for row in rows)
    assert all(float(row["supercurrent_l2"]) == 0.0 for row in rows)
    assert all(float(row["normalcurrent_l2"]) == 0.0 for row in rows)
    assert max(abs(float(row["mean_abs2"]) - 1.0) for row in rows) < 1.0e-12
