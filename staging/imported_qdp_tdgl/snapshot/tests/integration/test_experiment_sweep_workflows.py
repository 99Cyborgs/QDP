from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest
from typer.testing import CliRunner
import yaml

from tdgl_rf.cli import app, classify_experiment_manifest
from tdgl_rf.testing.case_configs import read_json, write_case_config
from tdgl_rf.workflows import experiment_sweep as experiment_sweep_module
from tdgl_rf.workflows.experiment_sweep import (
    derive_noise_seed_from_provenance,
    rebuild_member_config_from_provenance,
    run_seeded_vortex_experiment_pack,
)


def _write_phase2_3_manifest(path: Path, *, base_case: Path) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "3.0",
                "experiment_pack": {
                    "mode": "deterministic_sweep",
                    "base_case": str(base_case),
                    "sweep": {
                        "parameters": [
                            {"name": "forcing.a_rf", "values": [0.0, 0.05]},
                            {"name": "physics.vortex_seeds.0.winding", "values": [1, -1]},
                        ]
                    },
                    "repetitions": 2,
                    "observables": [
                        "initialization.local_winding.initial_total_signed_winding",
                        "initialization.core_contrast.mean_core_to_ring_ratio",
                        "early_window.mean_abs2_final",
                    ],
                    "aggregation": {"metrics": ["mean", "std", "min", "max"]},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_phase2_4a_manifest(path: Path, *, base_case: Path) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "4.0",
                "experiment_pack": {
                    "mode": "stochastic_ensemble",
                    "base_case": str(base_case),
                    "sweep": {
                        "parameters": [
                            {"name": "forcing.a_rf", "values": [0.0, 0.05]},
                        ]
                    },
                    "ensemble": {
                        "member_count": 3,
                        "master_seed": 1234,
                    },
                    "observables": [
                        "early_window.mean_abs2_final",
                    ],
                    "aggregation": {"metrics": ["mean", "std", "min", "max"]},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_phase2_2_manifest(path: Path, *, reject_config: Path) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "tdgl_rf.seeded_vortex_experiment_pack.v1",
                "suite_id": "phase2_2_route_suite",
                "claim_scope": "Deterministic same-stack seeded initialization / bounded short-horizon expectation matching and seeded input rejection taxonomy only.",
                "defaults": {
                    "horizon_contracts": {
                        "initialization_only": {"n_steps": 0, "sampling_policy": "initialization_surface"},
                        "short_horizon": {"n_steps": 4, "sampling_policy": "all_observable_samples_through_n_steps"},
                    }
                },
                "canonical_cases": [],
                "exercise_cases": [],
                "rejection_cases": [
                    {
                        "case_id": "reject_missing",
                        "config_path": str(reject_config),
                        "expected_stage": "config_validation",
                        "expected_rejection": {
                            "code": "missing_seeds",
                            "field_path": "physics.vortex_seeds",
                            "seed_index": None,
                        },
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_malformed_phase2_3_manifest(path: Path, *, base_case: Path) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "3.0",
                "experiment_pack": {
                    "mode": "deterministic_sweep",
                    "base_case": str(base_case),
                    "sweep": {
                        "parameters": [
                            {"name": "forcing.a_rf", "values": [0.0]},
                        ]
                    },
                    "observables": ["early_window.mean_abs2_final"],
                    "aggregation": {"metrics": ["mean"]},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_malformed_phase2_4a_manifest(path: Path, *, base_case: Path) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "4.0",
                "experiment_pack": {
                    "mode": "stochastic_ensemble",
                    "base_case": str(base_case),
                    "sweep": {
                        "parameters": [
                            {"name": "forcing.a_rf", "values": [0.0]},
                        ]
                    },
                    "observables": ["early_window.mean_abs2_final"],
                    "aggregation": {"metrics": ["mean"]},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _minimal_tier2_payload() -> dict[str, object]:
    return {
        "initialization_observables": {
            "local_winding_verification": {
                "seed_count": 1,
                "initial_total_signed_winding": 1,
                "initial_total_abs_winding": 1,
                "all_host_winding_match": True,
                "all_local_winding_match": True,
            },
            "core_contrast_observables": {
                "all_core_observable": True,
                "core_to_ring_ratio_series": [0.75],
            },
            "overall_pass": True,
        },
        "early_window_observables": {
            "checked_sample_count": 2,
            "expected_vortex_count": 1,
            "vortex_count_series": [1, 1],
            "mean_abs2_series": [1.0, 0.9],
            "charge_residual_inf_series": [0.1, 0.05],
            "finite_observables_pass": True,
            "positive_amplitude_pass": True,
            "vortex_count_matches_expected_pass": True,
            "overall_pass": True,
        },
        "case_class": "short_horizon",
    }


def _stochastic_seeded_overrides() -> dict[str, object]:
    return {
        "metadata": {"phase": "S"},
        "physics": {
            "initial_condition": "seeded_vortices",
            "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
        },
        "noise": {"enabled": True, "strength": 0.05, "seed": 777},
        "output": {"write_fields": False},
    }


def test_classify_experiment_manifest_is_explicit_and_disjoint(tmp_path: Path) -> None:
    base_case = write_case_config(
        tmp_path,
        "dispatch_base_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "output": {"write_fields": False},
        },
    )
    reject_config = write_case_config(
        tmp_path,
        "dispatch_reject_case",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )

    assert classify_experiment_manifest(_write_phase2_2_manifest(tmp_path / "phase2_2.yaml", reject_config=reject_config)) == "phase2_2_suite"
    assert classify_experiment_manifest(_write_phase2_3_manifest(tmp_path / "phase2_3.yaml", base_case=base_case)) == "phase2_3_deterministic"
    assert classify_experiment_manifest(_write_phase2_4a_manifest(tmp_path / "phase2_4a.yaml", base_case=base_case)) == "phase2_4a_ensemble"


def test_run_seeded_vortex_experiment_pack_small_sweep_is_deterministic(tmp_path: Path) -> None:
    base_case = write_case_config(
        tmp_path,
        "sweep_base_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 2},
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_phase2_3_manifest(tmp_path / "seeded_experiment_pack.yaml", base_case=base_case)

    summary_a = run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "experiment_a")
    summary_b = run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "experiment_b")

    payload_a = read_json(Path(summary_a.results_json_path))
    payload_b = read_json(Path(summary_b.results_json_path))
    provenance_schema = json.loads(Path("configs/tdgl_run_provenance.schema.json").read_text(encoding="utf-8"))
    first_run_dir = Path(payload_a["run_records"][0]["run_dir"])
    provenance_payload = read_json(first_run_dir / "provenance.json")

    Draft202012Validator(provenance_schema).validate(provenance_payload)

    assert summary_a.status == "success"
    assert summary_a.parameter_point_count == 4
    assert summary_a.run_count == 8
    assert payload_a["overall_status"] == "success"
    assert Path(summary_a.results_csv_path).exists()
    assert Path(summary_a.results_markdown_path).exists()
    assert provenance_payload["schema_version"] == "tdgl_rf.run_provenance.v3.3"
    assert provenance_payload["experiment"]["experiment_name"] == "seeded_experiment_pack"
    assert provenance_payload["experiment"]["mode"] == "deterministic_sweep"
    assert provenance_payload["experiment"]["manifest_path"] == str(manifest_path.resolve())
    assert provenance_payload["experiment"]["base_case_path"] == str(base_case.resolve())
    assert provenance_payload["experiment"]["run_id"] == payload_a["run_records"][0]["run_id"]
    assert provenance_payload["experiment"]["param_set_hash"] == payload_a["run_records"][0]["param_set_hash"]
    assert provenance_payload["experiment"]["repetition_index"] == 0
    assert provenance_payload["experiment"]["swept_parameters"] == payload_a["run_records"][0]["parameters"]
    assert "ensemble" not in provenance_payload
    reconstructed_payload = rebuild_member_config_from_provenance(provenance_payload)
    assert reconstructed_payload["metadata"]["case_id"] == provenance_payload["experiment"]["run_id"]
    assert reconstructed_payload["output"]["root_dir"] == provenance_payload["config"]["output_root_dir"]
    assert all(record["status"] == "success" for record in payload_a["run_records"])
    assert all(point["successful_run_count"] == 2 for point in payload_a["parameter_points"])
    for point in payload_a["parameter_points"]:
        for observable_name, aggregates in point["aggregates"].items():
            assert aggregates["std"] == 0.0, observable_name

    projected_runs_a = sorted(
        (
            record["run_id"],
            record["param_set_hash"],
            record["repetition_index"],
            record["parameters"],
            record["observables"],
        )
        for record in payload_a["run_records"]
    )
    projected_runs_b = sorted(
        (
            record["run_id"],
            record["param_set_hash"],
            record["repetition_index"],
            record["parameters"],
            record["observables"],
        )
        for record in payload_b["run_records"]
    )

    assert projected_runs_a == projected_runs_b


def test_deterministic_sweep_failure_aborts_whole_experiment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_case = write_case_config(
        tmp_path,
        "abort_base_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_phase2_3_manifest(tmp_path / "abort_manifest.yaml", base_case=base_case)
    call_count = {"value": 0}

    def _fake_run_simulation(_config_path, *, run_dir_override, experiment_metadata, ensemble_metadata=None):
        call_count["value"] += 1
        if call_count["value"] == 2:
            raise RuntimeError("forced failure")
        run_dir = Path(run_dir_override)
        (run_dir / "diagnostics").mkdir(parents=True, exist_ok=True)
        (run_dir / "provenance.json").write_text(
            json.dumps(
                {
                    "schema_version": "tdgl_rf.run_provenance.v3.3",
                    "experiment": experiment_metadata,
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "diagnostics" / "seeded_vortex_tier2.json").write_text(
            json.dumps(_minimal_tier2_payload()),
            encoding="utf-8",
        )
        return SimpleNamespace(run_dir=str(run_dir))

    monkeypatch.setattr(experiment_sweep_module, "run_simulation", _fake_run_simulation)
    monkeypatch.setattr(experiment_sweep_module, "_validate_payload_against_schema", lambda *args, **kwargs: None)
    monkeypatch.setattr(experiment_sweep_module, "_validate_success_metadata", lambda *args, **kwargs: None)
    monkeypatch.setattr(experiment_sweep_module, "_validate_replayable_provenance", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="forced failure"):
        run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "abort_out")

    assert call_count["value"] == 2
    assert not (tmp_path / "abort_out" / "experiment_results.json").exists()


def test_run_seeded_vortex_experiment_pack_phase2_4a_executes_successfully(tmp_path: Path) -> None:
    base_case = write_case_config(
        tmp_path,
        "ensemble_base_case",
        overrides=_stochastic_seeded_overrides(),
    )
    manifest_path = _write_phase2_4a_manifest(tmp_path / "phase2_4a.yaml", base_case=base_case)
    summary = run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "phase2_4a_out")
    payload = read_json(Path(summary.results_json_path))
    first_run_dir = Path(payload["run_records"][0]["run_dir"])
    provenance_payload = read_json(first_run_dir / "provenance.json")

    assert summary.status == "success"
    assert payload["mode"] == "stochastic_ensemble"
    assert payload["overall_status"] == "success"
    assert payload["expected_member_count"] == 3
    assert payload["parameter_point_count"] == 2
    assert payload["run_count"] == 6
    assert all(record["parent_manifest_hash"] == payload["parent_manifest_hash"] for record in payload["run_records"])
    assert payload["parameter_points"][0]["robustness_summary"]["member_count"] == 3
    assert payload["parameter_points"][0]["robustness_summary"]["failed_member_count"] == 0
    assert payload["parameter_points"][0]["robustness_summary"]["failure_rate"] == pytest.approx(0.0)
    assert payload["parameter_points"][0]["robustness_summary"]["observables"]["early_window.mean_abs2_final"]["coefficient_of_variation_defined"] is True
    assert provenance_payload["schema_version"] == "tdgl_rf.run_provenance.v3.3"
    assert provenance_payload["experiment"]["mode"] == "stochastic_ensemble"
    assert provenance_payload["experiment"]["manifest_path"] == str(manifest_path.resolve())
    assert provenance_payload["experiment"]["base_case_path"] == str(base_case.resolve())
    assert provenance_payload["ensemble"]["member_index"] == 0
    assert provenance_payload["ensemble"]["noise_seed"] == payload["run_records"][0]["noise_seed"]
    assert provenance_payload["ensemble"]["parent_manifest_hash"] == payload["parent_manifest_hash"]
    assert provenance_payload["noise"]["seed"] == payload["run_records"][0]["noise_seed"]
    assert derive_noise_seed_from_provenance(provenance_payload) == payload["run_records"][0]["noise_seed"]
    reconstructed_payload = rebuild_member_config_from_provenance(provenance_payload)
    assert reconstructed_payload["metadata"]["case_id"] == payload["run_records"][0]["run_id"]
    assert reconstructed_payload["noise"]["seed"] == payload["run_records"][0]["noise_seed"]
    assert reconstructed_payload["output"]["root_dir"] == provenance_payload["config"]["output_root_dir"]


def test_phase2_4a_member_failure_emits_zero_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base_case = write_case_config(
        tmp_path,
        "ensemble_gate_artifacts_base",
        overrides=_stochastic_seeded_overrides(),
    )
    manifest_path = _write_phase2_4a_manifest(tmp_path / "phase2_4a_gate.yaml", base_case=base_case)

    real_execute = experiment_sweep_module.execute_ensemble_plan

    def _fail_on_second_member(members):
        members = list(members)
        real_execute(members[:1])
        raise RuntimeError("forced member failure")

    monkeypatch.setattr(experiment_sweep_module, "execute_ensemble_plan", _fail_on_second_member)

    with pytest.raises(RuntimeError, match="forced member failure"):
        run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "phase2_4a_gate_out")

    assert not (tmp_path / "phase2_4a_gate_out").exists()
    assert not list(tmp_path.glob("**/provenance.json"))
    assert not list(tmp_path.glob("**/experiment_results.json"))
    assert not list(tmp_path.glob("**/status.json"))


def test_phase2_4a_missing_staged_outputs_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base_case = write_case_config(
        tmp_path,
        "ensemble_missing_stage_base",
        overrides=_stochastic_seeded_overrides(),
    )
    manifest_path = _write_phase2_4a_manifest(tmp_path / "phase2_4a_missing_stage.yaml", base_case=base_case)

    real_execute = experiment_sweep_module.execute_ensemble_plan

    def _execute_then_remove_first_tier2(members):
        members = list(members)
        summaries = real_execute(members)
        first_run_dir = Path(members[0]["run_dir"])
        (first_run_dir / "diagnostics" / "seeded_vortex_tier2.json").unlink()
        return summaries

    monkeypatch.setattr(experiment_sweep_module, "execute_ensemble_plan", _execute_then_remove_first_tier2)

    with pytest.raises(Exception, match="missing JSON payload"):
        run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "phase2_4a_missing_stage_out")

    assert not (tmp_path / "phase2_4a_missing_stage_out").exists()
    assert not list(tmp_path.glob("**/experiment_results.json"))


def test_phase2_4a_incomplete_member_set_emits_no_aggregate_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base_case = write_case_config(
        tmp_path,
        "ensemble_incomplete_base",
        overrides=_stochastic_seeded_overrides(),
    )
    manifest_path = _write_phase2_4a_manifest(tmp_path / "phase2_4a_incomplete.yaml", base_case=base_case)
    real_aggregate = experiment_sweep_module.aggregate_ensemble_results

    def _truncate_last_member(**kwargs):
        truncated = list(kwargs["run_records"])[:-1]
        return real_aggregate(**{**kwargs, "run_records": truncated})

    monkeypatch.setattr(experiment_sweep_module, "aggregate_ensemble_results", _truncate_last_member)

    with pytest.raises(Exception, match="expected 3 ensemble members but observed 2"):
        run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "phase2_4a_incomplete_out")

    assert not (tmp_path / "phase2_4a_incomplete_out").exists()
    assert not list(tmp_path.glob("**/experiment_results.json"))


def test_phase2_4a_duplicate_noise_seed_is_rejected_before_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base_case = write_case_config(
        tmp_path,
        "ensemble_duplicate_seed_base",
        overrides=_stochastic_seeded_overrides(),
    )
    manifest_path = _write_phase2_4a_manifest(tmp_path / "phase2_4a_duplicate_seed.yaml", base_case=base_case)

    monkeypatch.setattr(experiment_sweep_module, "derive_seed", lambda *args: 42)

    with pytest.raises(Exception, match="duplicate noise_seed"):
        run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "phase2_4a_duplicate_seed_out")

    assert not (tmp_path / "phase2_4a_duplicate_seed_out").exists()


def test_phase2_4a_failed_promotion_cleans_partial_destination(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base_case = write_case_config(
        tmp_path,
        "ensemble_promotion_base",
        overrides=_stochastic_seeded_overrides(),
    )
    manifest_path = _write_phase2_4a_manifest(tmp_path / "phase2_4a_promotion.yaml", base_case=base_case)

    def _partial_promotion(staging_dir: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "experiment_results.json").write_text("partial", encoding="utf-8")
        raise RuntimeError("forced promotion failure")

    monkeypatch.setattr(experiment_sweep_module, "_promote_staging_directory", _partial_promotion)

    with pytest.raises(RuntimeError, match="forced promotion failure"):
        run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "phase2_4a_promotion_out")

    assert not (tmp_path / "phase2_4a_promotion_out").exists()


def test_phase2_4a_successful_pack_is_replay_stable(tmp_path: Path) -> None:
    base_case = write_case_config(
        tmp_path,
        "ensemble_replay_base",
        overrides=_stochastic_seeded_overrides(),
    )
    manifest_path = _write_phase2_4a_manifest(tmp_path / "phase2_4a_replay.yaml", base_case=base_case)

    summary_a = run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "phase2_4a_replay_a")
    summary_b = run_seeded_vortex_experiment_pack(manifest_path, output_dir=tmp_path / "phase2_4a_replay_b")
    payload_a = read_json(Path(summary_a.results_json_path))
    payload_b = read_json(Path(summary_b.results_json_path))

    assert payload_a["overall_status"] == "success"
    assert payload_b["overall_status"] == "success"
    assert payload_a["parent_manifest_hash"] == payload_b["parent_manifest_hash"]
    assert payload_a["expected_member_count"] == payload_b["expected_member_count"] == 3
    assert sorted(
        (
            record["run_id"],
            record["ensemble_id"],
            record["member_index"],
            record["noise_seed"],
            record["observables"],
        )
        for record in payload_a["run_records"]
    ) == sorted(
        (
            record["run_id"],
            record["ensemble_id"],
            record["member_index"],
            record["noise_seed"],
            record["observables"],
        )
        for record in payload_b["run_records"]
    )
    assert [
        (point["param_set_hash"], point["ensemble_id"], point["aggregates"], point["robustness_summary"])
        for point in payload_a["parameter_points"]
    ] == [
        (point["param_set_hash"], point["ensemble_id"], point["aggregates"], point["robustness_summary"])
        for point in payload_b["parameter_points"]
    ]


def test_run_experiment_cli_routes_phase2_2_manifest_unchanged(tmp_path: Path) -> None:
    reject_config = write_case_config(
        tmp_path,
        "cli_route_reject_case",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_phase2_2_manifest(tmp_path / "phase2_2_route.yaml", reject_config=reject_config)
    runner = CliRunner()
    help_result = runner.invoke(app, ["run-experiment", "--help"])

    result = runner.invoke(
        app,
        ["run-experiment", str(manifest_path), "--output-dir", str(tmp_path / "phase2_2_route_out")],
    )

    assert help_result.exit_code == 0
    assert "Phase-2.4A" in help_result.stdout
    assert result.exit_code == 0
    assert '"case_count": 1' in result.stdout
    assert '"status": "success"' in result.stdout


def test_run_experiment_cli_rejects_malformed_phase2_3_without_phase2_2_fallback(tmp_path: Path) -> None:
    base_case = write_case_config(
        tmp_path,
        "malformed_v3_base_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_malformed_phase2_3_manifest(tmp_path / "malformed_phase2_3.yaml", base_case=base_case)
    runner = CliRunner()

    result = runner.invoke(app, ["run-experiment", str(manifest_path)])

    assert result.exit_code == 1
    assert "Phase-2.3 deterministic experiment-pack validation failed" in result.output
    assert '"case_count"' not in result.output


def test_run_experiment_cli_rejects_malformed_phase2_4a_without_phase2_2_fallback(tmp_path: Path) -> None:
    base_case = write_case_config(
        tmp_path,
        "malformed_v4_base_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_malformed_phase2_4a_manifest(tmp_path / "malformed_phase2_4a.yaml", base_case=base_case)
    runner = CliRunner()

    result = runner.invoke(app, ["run-experiment", str(manifest_path)])

    assert result.exit_code == 1
    assert "Phase-2.4A ensemble experiment-pack validation failed" in result.output
    assert '"case_count"' not in result.output


def test_run_experiment_cli_phase2_4a_executes_successfully(tmp_path: Path) -> None:
    base_case = write_case_config(
        tmp_path,
        "cli_phase2_4a_base_case",
        overrides=_stochastic_seeded_overrides(),
    )
    manifest_path = _write_phase2_4a_manifest(tmp_path / "cli_phase2_4a.yaml", base_case=base_case)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["run-experiment", str(manifest_path), "--output-dir", str(tmp_path / "cli_phase2_4a_out")],
    )

    assert result.exit_code == 0
    assert '"status": "success"' in result.output
    assert '"run_count": 6' in result.output


def test_run_experiment_cli_committed_phase2_4a_manifest_executes_successfully(tmp_path: Path) -> None:
    manifest_path = Path("validation/seeded_vortex_phase2_4a_experiment_pack.yaml").resolve()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["run-experiment", str(manifest_path), "--output-dir", str(tmp_path / "committed_phase2_4a_out")],
    )

    assert result.exit_code == 0
    assert '"status": "success"' in result.output
    assert '"run_count": 6' in result.output
    payload = read_json(tmp_path / "committed_phase2_4a_out" / "experiment_results.json")
    markdown = (tmp_path / "committed_phase2_4a_out" / "experiment_results.md").read_text(encoding="utf-8")
    assert payload["parameter_points"][0]["robustness_summary"]["member_count"] == 3
    assert "## Ensemble Robustness Summary" in markdown
