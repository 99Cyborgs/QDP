from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tdgl_rf.config.loaders import load_case_config
from tdgl_rf.exceptions import ConfigError
from tdgl_rf.fields.linkvars import build_link_variables
from tdgl_rf.fields.vortices import compute_vortex_map
from tdgl_rf.geometry.masks import build_geometry, grid_from_config
from tdgl_rf.solvers.state import initialize_state
from tdgl_rf.testing.case_configs import read_csv_rows, write_case_config
from tdgl_rf.workflows.run_case import run_simulation


def _initial_vortex_map(config_path: Path) -> np.ndarray:
    config = load_case_config(config_path)
    grid = grid_from_config(config.mesh)
    geometry = build_geometry(grid, config.geometry, config_path.parent)
    state = initialize_state(grid, geometry, config, config_path.parent)
    return compute_vortex_map(state.psi, build_link_variables(grid, state.A), geometry)


def test_single_positive_seeded_vortex_acceptance_case(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_positive",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 0},
            "output": {"write_fields": False},
        },
    )

    summary = run_simulation(config_path)
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))
    vortex_map = _initial_vortex_map(config_path)

    assert summary.status == "success"
    assert float(rows[0]["vortex_count"]) == 1.0
    assert int(np.sum(vortex_map)) == 1
    assert int(np.sum(np.abs(vortex_map))) == 1


def test_single_negative_seeded_vortex_acceptance_case(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_negative",
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
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))
    vortex_map = _initial_vortex_map(config_path)

    assert summary.status == "success"
    assert float(rows[0]["vortex_count"]) == 1.0
    assert int(np.sum(vortex_map)) == -1
    assert int(np.sum(np.abs(vortex_map))) == 1


def test_two_vortex_seeded_acceptance_case(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_pair",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [
                    {"x0": 2.0, "y0": 2.0, "winding": 1},
                    {"x0": 6.0, "y0": 2.0, "winding": -1},
                ],
            },
            "time": {"n_steps": 0},
            "output": {"write_fields": False},
        },
    )

    summary = run_simulation(config_path)
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))
    vortex_map = _initial_vortex_map(config_path)

    assert summary.status == "success"
    assert float(rows[0]["vortex_count"]) == 2.0
    assert int(np.sum(np.abs(vortex_map))) == 2
    assert int(np.sum(vortex_map)) == 0
    assert int(np.sum(vortex_map > 0)) == 1
    assert int(np.sum(vortex_map < 0)) == 1


def test_seeded_vortex_rejects_masked_placement(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_masked_reject",
        overrides={
            "geometry": {
                "family": "strip_with_moat",
                "moats": [{"x0": 4.0, "y0": 2.0, "radius": 0.7}],
            },
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
        },
    )

    with pytest.raises(ConfigError, match="fully active plaquette"):
        run_simulation(config_path)


def test_seeded_vortex_rejects_ambiguous_config_combination(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_invalid_combo",
        overrides={
            "physics": {
                "initial_condition": "meissner",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            }
        },
    )

    with pytest.raises(ConfigError, match="only valid when physics.initial_condition == 'seeded_vortices'"):
        run_simulation(config_path)
