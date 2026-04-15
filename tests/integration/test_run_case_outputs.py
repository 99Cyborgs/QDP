from __future__ import annotations

from pathlib import Path

import json
import pytest
from jsonschema import Draft202012Validator

from tdgl_rf.exceptions import OutputWriteError
from tdgl_rf.solvers.tdgl_stepper import TDGLStepper
from tdgl_rf.testing.case_configs import latest_run_dir, read_csv_rows, read_json, write_case_config
from tdgl_rf.workflows.run_case import run_simulation


def test_run_simulation_appends_terminal_observable_sample(tmp_path: Path) -> None:
    config_path = write_case_config(tmp_path, "terminal_sample", overrides={"time": {"n_steps": 3, "obs_stride": 2}})

    summary = run_simulation(config_path)
    summary_path = Path(summary.observable_file_paths["summary"])
    timeseries_path = Path(summary.observable_file_paths["timeseries"])

    summary_payload = read_json(summary_path)
    rows = read_csv_rows(timeseries_path)

    assert len(rows) == 3
    assert float(rows[-1]["t"]) == 0.03
    assert summary.summary_metrics == summary_payload
    assert summary_payload["final_time"] == 0.03
    assert summary_payload["final_time"] == float(rows[-1]["t"])
    assert summary_payload["final_mean_abs2"] == float(rows[-1]["mean_abs2"])


def test_run_simulation_compute_only_observables_mode_keeps_summary_metadata(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = write_case_config(
        tmp_path,
        "compute_only_observables",
        overrides={"time": {"n_steps": 2}, "output": {"write_observables": False}},
    )

    summary = run_simulation(config_path)
    run_dir = latest_run_dir(output_root, "compute_only_observables")
    observables_dir = run_dir / "observables"
    status_payload = read_json(run_dir / "status.json")
    run_summary_payload = read_json(run_dir / "diagnostics" / "run_summary.json")
    convergence_payload = read_json(run_dir / "diagnostics" / "convergence_report.json")

    assert summary.observable_mode == "computed_only"
    assert summary.observable_file_paths == {}
    assert summary.summary_metrics["n_samples"] == 3
    assert list(observables_dir.iterdir()) == []
    assert status_payload == run_summary_payload
    assert status_payload["summary_metrics"] == summary.summary_metrics
    assert status_payload["diagnostic_file_paths"] == summary.diagnostic_file_paths
    assert convergence_payload["observable_mode"] == "computed_only"
    assert convergence_payload["key_observables"] == summary.summary_metrics


def test_zero_step_run_writes_compact_summary_and_zero_step_diagnostics(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = write_case_config(
        tmp_path,
        "zero_step",
        overrides={"time": {"n_steps": 0}, "output": {"write_fields": False}},
    )

    summary = run_simulation(config_path)
    run_dir = latest_run_dir(output_root, "zero_step")
    rows = read_csv_rows(Path(summary.observable_file_paths["timeseries"]))
    status_payload = read_json(run_dir / "status.json")
    profiling_payload = read_json(run_dir / "diagnostics" / "profiling.json")

    assert summary.status == "success"
    assert summary.summary_metrics["n_samples"] == 1
    assert summary.summary_metrics["final_time"] == 0.0
    assert summary.solver_iteration_stats["completed_step_count"] == 0
    assert summary.solver_iteration_stats["requested_n_steps"] == 0
    assert summary.checkpoint_file_paths == []
    assert len(rows) == 1
    assert float(rows[0]["t"]) == 0.0
    assert profiling_payload["step_count"] == 0
    assert profiling_payload["requested_n_steps"] == 0
    assert status_payload["summary_metrics"] == summary.summary_metrics


def test_run_simulation_respects_write_fields_flag(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = write_case_config(
        tmp_path,
        "no_fields",
        overrides={"time": {"n_steps": 2}, "output": {"write_fields": False}},
    )

    summary = run_simulation(config_path)
    run_dir = latest_run_dir(output_root, "no_fields")
    fields_dir = run_dir / "fields"
    status_payload = read_json(run_dir / "status.json")

    assert summary.checkpoint_file_paths == []
    assert list(fields_dir.iterdir()) == []
    assert status_payload["checkpoint_file_paths"] == []
    assert Path(summary.diagnostic_file_paths["profiling"]).exists()


def test_run_simulation_persists_failed_status_and_diagnostics(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = write_case_config(tmp_path, "forced_failure", overrides={"time": {"n_steps": 2}})

    def _raise_failure(self, state):  # pragma: no cover - executed through monkeypatch
        raise OutputWriteError("forced early failure")

    monkeypatch.setattr(TDGLStepper, "advance", _raise_failure)

    with pytest.raises(OutputWriteError, match="forced early failure"):
        run_simulation(config_path)

    run_dir = latest_run_dir(output_root, "forced_failure")
    status_payload = read_json(run_dir / "status.json")
    run_summary_payload = read_json(run_dir / "diagnostics" / "run_summary.json")
    profiling_payload = read_json(run_dir / "diagnostics" / "profiling.json")
    convergence_payload = read_json(run_dir / "diagnostics" / "convergence_report.json")

    assert status_payload == run_summary_payload
    assert status_payload["status"] == "failed"
    assert status_payload["failure_reason"] == "forced early failure"
    assert status_payload["summary_metrics"]["n_samples"] == 1
    assert status_payload["observable_file_paths"] == {}
    assert profiling_payload["step_count"] == 0
    assert convergence_payload["status"] == "failed"
    assert convergence_payload["failure_reason"] == "forced early failure"


def test_seeded_run_writes_replayable_provenance_and_tier2_diagnostics(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = write_case_config(
        tmp_path,
        "seeded_metadata",
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
    run_dir = latest_run_dir(output_root, "seeded_metadata")
    provenance_payload = read_json(run_dir / "provenance.json")
    tier2_payload = read_json(run_dir / "diagnostics" / "seeded_vortex_tier2.json")
    schema = json.loads(Path("configs/tdgl_run_provenance.schema.json").read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(provenance_payload)

    assert provenance_payload["schema_version"] == "tdgl_rf.run_provenance.v3"
    assert provenance_payload["noise"]["contract_kind"] == "additive_complex_gaussian"
    assert provenance_payload["noise"]["sampling"] == "run_local_complex_standard_normal"
    assert provenance_payload["noise"]["enabled"] is False
    assert provenance_payload["config"]["source_config_path"] == str(config_path.resolve())
    assert provenance_payload["config"]["expanded_config_path"] == str((run_dir / "expanded_config.yaml").resolve())
    assert provenance_payload["config"]["output_root_dir"] == str(output_root.resolve())
    assert provenance_payload["numeric_environment"]["real_dtype"] == "float64"
    assert provenance_payload["numeric_environment"]["complex_dtype"] == "complex128"
    assert provenance_payload["initialization"]["mode"] == "seeded_vortices"
    assert provenance_payload["initialization"]["seed_resolution_policy"] == "strict_interior_fully_active_plaquette"
    assert provenance_payload["initialization"]["seed_rejection_taxonomy_version"] == "seeded_vortex_phase2_1"
    assert provenance_payload["initialization"]["resolved_vortex_seeds"][0]["plaquette_x"] == 7
    assert summary.seed_information["resolved_vortex_seeds"][0]["plaquette_x"] == 7
    assert Path(summary.diagnostic_file_paths["seeded_vortex_tier2"]).exists()
    assert tier2_payload["schema_version"] == "tdgl_rf.seeded_vortex_tier2.v2"
    assert tier2_payload["case_class"] == "short_horizon"
    assert tier2_payload["horizon_contract"]["n_steps"] == 4
    assert tier2_payload["tier2_overall_pass"] is True


def test_run_simulation_experiment_provenance_uses_hardened_experiment_block(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = write_case_config(
        tmp_path,
        "experiment_provenance",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 1},
            "output": {"write_fields": False},
        },
    )
    experiment_metadata = {
        "experiment_name": "phase2_3_demo",
        "mode": "deterministic_sweep",
        "manifest_path": str((tmp_path / "phase2_3_demo.yaml").resolve()),
        "base_case_path": str(config_path.resolve()),
        "parent_manifest_hash": "manifest123",
        "base_case_hash": "basecase123",
        "param_set_hash": "abcd1234efef5678",
        "repetition_index": 1,
        "run_id": "phase2_3_demo__abcd1234efef5678__r1",
        "swept_parameters": {"forcing.a_rf": 0.05},
    }

    run_simulation(config_path, experiment_metadata=experiment_metadata)
    run_dir = latest_run_dir(output_root, "experiment_provenance")
    provenance_payload = read_json(run_dir / "provenance.json")
    schema = json.loads(Path("configs/tdgl_run_provenance.schema.json").read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(provenance_payload)

    assert provenance_payload["schema_version"] == "tdgl_rf.run_provenance.v3.3"
    assert provenance_payload["experiment"] == experiment_metadata
    assert "ensemble" not in provenance_payload


def test_run_simulation_experiment_provenance_can_include_ensemble_block(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = write_case_config(
        tmp_path,
        "ensemble_provenance",
        overrides={
            "metadata": {"phase": "S"},
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "noise": {"enabled": True, "strength": 0.1, "seed": 4242},
            "time": {"n_steps": 1},
            "output": {"write_fields": False},
        },
    )
    experiment_metadata = {
        "experiment_name": "phase2_4a_demo",
        "mode": "stochastic_ensemble",
        "manifest_path": str((tmp_path / "phase2_4a_demo.yaml").resolve()),
        "base_case_path": str(config_path.resolve()),
        "parent_manifest_hash": "abc123",
        "base_case_hash": "basecase123",
        "param_set_hash": "fedcba9876543210",
        "repetition_index": None,
        "run_id": "phase2_4a_demo__fedcba9876543210__m2",
        "swept_parameters": {"forcing.a_rf": 0.05},
    }
    ensemble_metadata = {
        "mode": "stochastic_ensemble",
        "ensemble_id": "ensemble_demo",
        "member_index": 2,
        "noise_seed": 4242,
        "member_count": 3,
        "master_seed": 1234,
        "parent_manifest_hash": "abc123",
    }

    run_simulation(
        config_path,
        experiment_metadata=experiment_metadata,
        ensemble_metadata=ensemble_metadata,
    )
    run_dir = latest_run_dir(output_root, "ensemble_provenance")
    provenance_payload = read_json(run_dir / "provenance.json")
    schema = json.loads(Path("configs/tdgl_run_provenance.schema.json").read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(provenance_payload)

    assert provenance_payload["schema_version"] == "tdgl_rf.run_provenance.v3.3"
    assert provenance_payload["experiment"] == experiment_metadata
    assert provenance_payload["ensemble"] == ensemble_metadata
    assert provenance_payload["noise"]["enabled"] is True
    assert provenance_payload["noise"]["seed"] == 4242
    assert provenance_payload["seeds"]["master_seed"] == 1234
    assert provenance_payload["seeds"]["noise_seed"] == 4242
    assert provenance_payload["determinism"]["master_seed"] == 1234
    assert provenance_payload["determinism"]["noise_seed"] == 4242


def test_run_simulation_is_reproducible_for_same_noise_seed(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "stochastic_reproducible",
        overrides={
            "metadata": {"phase": "S"},
            "noise": {"enabled": True, "strength": 0.1, "seed": 2027},
            "time": {"n_steps": 2},
            "output": {"write_fields": False},
        },
    )

    summary_a = run_simulation(config_path)
    summary_b = run_simulation(config_path)

    rows_a = read_csv_rows(Path(summary_a.observable_file_paths["timeseries"]))
    rows_b = read_csv_rows(Path(summary_b.observable_file_paths["timeseries"]))

    assert summary_a.summary_metrics == summary_b.summary_metrics
    assert rows_a == rows_b


def test_run_simulation_differs_for_different_noise_seed(tmp_path: Path) -> None:
    config_a = write_case_config(
        tmp_path,
        "stochastic_seed_a",
        overrides={
            "metadata": {"phase": "S"},
            "noise": {"enabled": True, "strength": 0.1, "seed": 2027},
            "time": {"n_steps": 2},
            "output": {"write_fields": False},
        },
    )
    config_b = write_case_config(
        tmp_path,
        "stochastic_seed_b",
        overrides={
            "metadata": {"phase": "S"},
            "noise": {"enabled": True, "strength": 0.1, "seed": 2028},
            "time": {"n_steps": 2},
            "output": {"write_fields": False},
        },
    )

    summary_a = run_simulation(config_a)
    summary_b = run_simulation(config_b)

    rows_a = read_csv_rows(Path(summary_a.observable_file_paths["timeseries"]))
    rows_b = read_csv_rows(Path(summary_b.observable_file_paths["timeseries"]))

    assert rows_a != rows_b


def test_noise_disabled_preserves_deterministic_behavior_independent_of_seed(tmp_path: Path) -> None:
    config_a = write_case_config(
        tmp_path,
        "deterministic_noise_disabled_a",
        overrides={
            "noise": {"enabled": False, "strength": 0.1, "seed": 1111},
            "time": {"n_steps": 2},
            "output": {"write_fields": False},
        },
    )
    config_b = write_case_config(
        tmp_path,
        "deterministic_noise_disabled_b",
        overrides={
            "noise": {"enabled": False, "strength": 0.1, "seed": 9999},
            "time": {"n_steps": 2},
            "output": {"write_fields": False},
        },
    )

    summary_a = run_simulation(config_a)
    summary_b = run_simulation(config_b)

    rows_a = read_csv_rows(Path(summary_a.observable_file_paths["timeseries"]))
    rows_b = read_csv_rows(Path(summary_b.observable_file_paths["timeseries"]))

    assert summary_a.summary_metrics == summary_b.summary_metrics
    assert rows_a == rows_b
