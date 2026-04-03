from __future__ import annotations

from pathlib import Path

import pytest

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
