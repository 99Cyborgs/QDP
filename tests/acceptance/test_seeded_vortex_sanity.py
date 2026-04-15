from __future__ import annotations

from pathlib import Path

import numpy as np

from tdgl_rf.config.loaders import load_case_config
from tdgl_rf.fields.linkvars import build_link_variables
from tdgl_rf.fields.vortices import compute_vortex_map
from tdgl_rf.geometry.masks import build_geometry, grid_from_config
from tdgl_rf.solvers.state import initialize_state
from tdgl_rf.testing.case_configs import read_csv_rows, write_case_config
from tdgl_rf.workflows.run_case import run_simulation


def _seeded_state(config_path: Path):
    config = load_case_config(config_path)
    grid = grid_from_config(config.mesh)
    geometry = build_geometry(grid, config.geometry, config_path.parent)
    state = initialize_state(grid, geometry, config, config_path.parent)
    return grid, geometry, state


def test_seeded_winding_appears_in_initial_vortex_map(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_initial_map",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 0},
            "output": {"write_fields": False},
        },
    )

    grid, geometry, state = _seeded_state(config_path)
    vortex_map = compute_vortex_map(state.psi, build_link_variables(grid, state.A), geometry)

    assert int(np.sum(vortex_map)) == 1
    assert int(np.sum(np.abs(vortex_map))) == 1


def test_seeded_vortex_initialization_is_deterministic(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_reproducible",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [
                    {"x0": 2.0, "y0": 2.0, "winding": 1},
                    {"x0": 6.0, "y0": 2.0, "winding": -1, "core_radius": 0.2},
                ],
            },
            "output": {"write_fields": False},
        },
    )

    _, _, state_a = _seeded_state(config_path)
    _, _, state_b = _seeded_state(config_path)

    np.testing.assert_allclose(state_a.psi, state_b.psi)
    np.testing.assert_allclose(state_a.A.ax, state_b.A.ax)
    np.testing.assert_allclose(state_a.A.ay, state_b.A.ay)


def test_seeded_vortex_short_no_drive_run_remains_finite(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_short_run",
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
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))

    assert summary.status == "success"
    assert all(np.isfinite(float(row["mean_abs2"])) for row in rows)
    assert all(np.isfinite(float(row["charge_residual_inf"])) for row in rows)
    assert all(np.isfinite(float(row["supercurrent_l2"])) for row in rows)
    assert float(rows[0]["vortex_count"]) == 1.0


def test_seeded_vortex_masked_cells_do_not_create_spurious_structure(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_masked_sanity",
        overrides={
            "geometry": {
                "family": "strip_with_moat",
                "moats": [{"x0": 6.0, "y0": 2.0, "radius": 0.6}],
            },
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 2.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 0},
            "output": {"write_fields": False},
        },
    )

    grid, geometry, state = _seeded_state(config_path)
    vortex_map = compute_vortex_map(state.psi, build_link_variables(grid, state.A), geometry)

    assert int(np.sum(vortex_map)) == 1
    assert int(np.sum(np.abs(vortex_map))) == 1
