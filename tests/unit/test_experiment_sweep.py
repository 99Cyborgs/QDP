from __future__ import annotations

import pytest
import yaml

from tdgl_rf.testing.case_configs import write_case_config
from tdgl_rf.workflows.experiment_sweep import (
    ExperimentSweepParameter,
    build_run_id,
    canonicalize_parameter_point,
    compute_param_set_hash,
    expand_parameter_grid,
    load_seeded_vortex_experiment_pack,
)


def test_expand_parameter_grid_returns_cartesian_product() -> None:
    parameters = [
        ExperimentSweepParameter(name="forcing.a_rf", values=[0.0, 0.1]),
        ExperimentSweepParameter(name="physics.vortex_seeds.0.winding", values=[1, -1]),
    ]

    grid = expand_parameter_grid(parameters)

    assert grid == [
        {"forcing.a_rf": 0.0, "physics.vortex_seeds.0.winding": 1},
        {"forcing.a_rf": 0.0, "physics.vortex_seeds.0.winding": -1},
        {"forcing.a_rf": 0.1, "physics.vortex_seeds.0.winding": 1},
        {"forcing.a_rf": 0.1, "physics.vortex_seeds.0.winding": -1},
    ]


def test_canonical_parameter_hash_is_stable_under_key_reordering() -> None:
    point_a = {
        "forcing.profile": {
            "beta": 2.0,
            "alpha": 1.0,
        },
        "physics.seed": {
            "core": {"width": 3, "height": 2},
            "winding": 1,
        },
    }
    point_b = {
        "physics.seed": {
            "winding": 1,
            "core": {"height": 2, "width": 3},
        },
        "forcing.profile": {
            "alpha": 1.0,
            "beta": 2.0,
        },
    }

    assert canonicalize_parameter_point(point_a) == canonicalize_parameter_point(point_b)
    assert compute_param_set_hash(point_a) == compute_param_set_hash(point_b)


def test_build_run_id_is_deterministic_and_indexed() -> None:
    run_id = build_run_id("phase2_3", "abc123def4567890", repetition_index=3)

    assert run_id == "phase2_3__abc123def4567890__r3"
    assert build_run_id("phase2_3", "abc123def4567890", repetition_index=3) == run_id


def test_load_seeded_vortex_experiment_pack_rejects_unknown_keys(tmp_path) -> None:
    base_case = write_case_config(
        tmp_path,
        "sweep_unknown_key_base",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "output": {"write_fields": False},
        },
    )
    manifest_path = tmp_path / "bad_experiment_pack.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "3.0",
                "experiment_pack": {
                    "mode": "deterministic_sweep",
                    "base_case": str(base_case),
                    "sweep": {
                        "parameters": [
                            {"name": "forcing.a_rf", "values": [0.0, 0.1], "unexpected": True}
                        ]
                    },
                    "repetitions": 2,
                    "observables": ["early_window.mean_abs2_final"],
                    "aggregation": {"metrics": ["mean", "std", "min", "max"]},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="schema validation failed"):
        load_seeded_vortex_experiment_pack(manifest_path)
