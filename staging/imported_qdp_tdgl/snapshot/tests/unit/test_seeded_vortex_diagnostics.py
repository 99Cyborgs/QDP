from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tdgl_rf.config.loaders import load_case_config
from tdgl_rf.diagnostics.seeded_vortex import (
    SEEDED_CASE_CLASS_INITIALIZATION_ONLY,
    SEEDED_CASE_CLASS_SHORT_HORIZON,
    SEEDED_SAMPLING_POLICY_ALL_OBSERVABLE_SAMPLES,
    SEEDED_SAMPLING_POLICY_INITIALIZATION_SURFACE,
    compute_seeded_vortex_tier2_diagnostics,
    extract_observables,
)
from tdgl_rf.exceptions import Tier2ContractError
from tdgl_rf.fields.linkvars import build_link_variables
from tdgl_rf.fields.vortices import compute_vortex_map
from tdgl_rf.geometry.masks import build_geometry, grid_from_config
from tdgl_rf.solvers.seeded_vortices import resolve_vortex_seeds
from tdgl_rf.solvers.state import initialize_state
from tdgl_rf.testing.case_configs import read_csv_rows, read_json, write_case_config
from tdgl_rf.workflows.run_case import run_simulation


def test_compute_seeded_vortex_tier2_diagnostics_reports_expected_short_horizon_contract(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "tier2_diag_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 4},
            "output": {"write_fields": False},
        },
    )

    summary = run_simulation(config_path)
    timeseries = [
        {key: (int(value) if key in {"step", "vortex_count"} else float(value)) for key, value in row.items()}
        for row in read_csv_rows(Path(summary.observable_file_paths["timeseries"]))
    ]
    config = load_case_config(config_path)
    grid = grid_from_config(config.mesh)
    geometry = build_geometry(grid, config.geometry, config_path.parent)
    state = initialize_state(grid, geometry, config, config_path.parent)
    resolved = resolve_vortex_seeds(grid, geometry, config.physics.vortex_seeds)
    vortex_map = compute_vortex_map(state.psi, build_link_variables(grid, state.A), geometry)

    payload = compute_seeded_vortex_tier2_diagnostics(
        psi=state.psi,
        vortex_map=vortex_map,
        resolved_seeds=resolved,
        timeseries=timeseries,
        n_steps=4,
        sampling_policy=SEEDED_SAMPLING_POLICY_ALL_OBSERVABLE_SAMPLES,
    )

    assert payload["schema_version"] == "tdgl_rf.seeded_vortex_tier2.v2"
    assert payload["case_class"] == SEEDED_CASE_CLASS_SHORT_HORIZON
    assert payload["horizon_contract"]["n_steps"] == 4
    assert payload["horizon_contract"]["sampling_policy"] == SEEDED_SAMPLING_POLICY_ALL_OBSERVABLE_SAMPLES
    assert payload["horizon_contract"]["observed_step_series"] == [0, 1, 2, 3, 4]
    assert payload["initialization_observables"]["local_winding_verification"]["host_winding_series"] == [1]
    assert payload["initialization_observables"]["core_contrast_observables"]["all_core_observable"] is True
    assert payload["early_window_observables"]["vortex_count_series"] == [1, 1, 1, 1, 1]
    assert payload["early_window_observables"]["vortex_count_matches_expected_pass"] is True
    assert payload["early_window_observables"]["overall_pass"] is True
    assert payload["tier2_overall_pass"] is True


def test_compute_seeded_vortex_tier2_diagnostics_emits_initialization_only_surface_without_early_window(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "tier2_init_only_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": -1}],
            },
            "time": {"n_steps": 0},
            "output": {"write_fields": False},
        },
    )

    summary = run_simulation(config_path)
    timeseries = [
        {key: (int(value) if key in {"step", "vortex_count"} else float(value)) for key, value in row.items()}
        for row in read_csv_rows(Path(summary.observable_file_paths["timeseries"]))
    ]
    config = load_case_config(config_path)
    grid = grid_from_config(config.mesh)
    geometry = build_geometry(grid, config.geometry, config_path.parent)
    state = initialize_state(grid, geometry, config, config_path.parent)
    resolved = resolve_vortex_seeds(grid, geometry, config.physics.vortex_seeds)
    vortex_map = compute_vortex_map(state.psi, build_link_variables(grid, state.A), geometry)

    payload = compute_seeded_vortex_tier2_diagnostics(
        psi=state.psi,
        vortex_map=vortex_map,
        resolved_seeds=resolved,
        timeseries=timeseries,
        n_steps=0,
        sampling_policy=SEEDED_SAMPLING_POLICY_INITIALIZATION_SURFACE,
    )

    assert payload["case_class"] == SEEDED_CASE_CLASS_INITIALIZATION_ONLY
    assert payload["early_window_observables"] is None
    assert payload["horizon_contract"]["observed_sample_count"] == 1
    assert payload["horizon_contract"]["observed_step_series"] == [0]
    assert payload["initialization_observables"]["local_winding_verification"]["host_winding_series"] == [-1]
    assert payload["tier2_overall_pass"] is True


def test_compute_seeded_vortex_tier2_diagnostics_flags_failed_short_horizon_checks(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "tier2_diag_negative_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 1},
            "output": {"write_fields": False},
        },
    )

    config = load_case_config(config_path)
    grid = grid_from_config(config.mesh)
    geometry = build_geometry(grid, config.geometry, config_path.parent)
    resolved = resolve_vortex_seeds(grid, geometry, config.physics.vortex_seeds)
    state = initialize_state(grid, geometry, config, config_path.parent)
    failed_timeseries = [
        {"step": 0, "t": 0.0, "mean_abs2": 1.0, "charge_residual_inf": 0.0, "vortex_count": 0},
        {"step": 1, "t": 0.01, "mean_abs2": 0.0, "charge_residual_inf": 0.1, "vortex_count": 0},
    ]

    payload = compute_seeded_vortex_tier2_diagnostics(
        psi=np.ones_like(state.psi),
        vortex_map=np.zeros((grid.nx, grid.ny), dtype=np.int64),
        resolved_seeds=resolved,
        timeseries=failed_timeseries,
        n_steps=1,
        sampling_policy=SEEDED_SAMPLING_POLICY_ALL_OBSERVABLE_SAMPLES,
    )

    assert payload["initialization_observables"]["local_winding_verification"]["all_host_winding_match"] is False
    assert payload["initialization_observables"]["local_winding_verification"]["all_local_winding_match"] is False
    assert payload["initialization_observables"]["core_contrast_observables"]["all_core_observable"] is False
    assert payload["early_window_observables"]["positive_amplitude_pass"] is False
    assert payload["early_window_observables"]["vortex_count_matches_expected_pass"] is False
    assert payload["early_window_observables"]["overall_pass"] is False
    assert payload["tier2_overall_pass"] is False


def test_extract_observables_required_surface_is_available_for_short_horizon(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "tier2_extract_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 4},
            "output": {"write_fields": False},
        },
    )

    summary = run_simulation(config_path)
    tier2_payload = read_json(Path(summary.diagnostic_file_paths["seeded_vortex_tier2"]))

    observables = extract_observables(
        tier2_payload,
        required=[
            "initialization.overall_pass",
            "early_window.mean_abs2_final",
        ],
    )

    assert observables["initialization.overall_pass"] is True
    assert observables["early_window.mean_abs2_final"] > 0.0


def test_extract_observables_required_surface_raises_when_early_window_is_absent(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "tier2_extract_init_only",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": -1}],
            },
            "time": {"n_steps": 0},
            "output": {"write_fields": False},
        },
    )

    summary = run_simulation(config_path)
    tier2_payload = read_json(Path(summary.diagnostic_file_paths["seeded_vortex_tier2"]))

    with pytest.raises(Tier2ContractError, match="required early_window observables"):
        extract_observables(
            tier2_payload,
            required=["early_window.mean_abs2_final"],
        )
