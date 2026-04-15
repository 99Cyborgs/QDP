from __future__ import annotations

import pytest

from tdgl_rf.analysis.experiment_aggregation import aggregate_ensemble_results, aggregate_experiment_results
from tdgl_rf.exceptions import AggregationError


def _successful_run_record(
    *,
    run_id: str,
    param_set_hash: str = "param_a",
    repetition_index: int = 0,
    mean_abs2: float = 0.8,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "param_set_hash": param_set_hash,
        "parameters": {"forcing.a_rf": 0.0},
        "repetition_index": repetition_index,
        "run_dir": run_id,
        "case_class": "short_horizon",
        "status": "success",
        "observables": {
            "initialization.local_winding.initial_total_signed_winding": 1,
            "early_window.mean_abs2_final": mean_abs2,
        },
        "notes": "ok",
    }


def test_aggregate_experiment_results_computes_mean_std_min_max() -> None:
    payload = aggregate_experiment_results(
        schema_version="3.0",
        pack_name="unit_pack",
        manifest_path="unit_pack.yaml",
        base_case_path="base_case.yaml",
        repetitions=2,
        sweep_parameters=["forcing.a_rf"],
        observables=[
            "initialization.local_winding.initial_total_signed_winding",
            "early_window.mean_abs2_final",
        ],
        aggregation_metrics=["mean", "std", "min", "max"],
        run_records=[
            _successful_run_record(run_id="run_a", repetition_index=0, mean_abs2=0.8),
            _successful_run_record(run_id="run_b", repetition_index=1, mean_abs2=1.0),
        ],
    )

    point = payload["parameter_points"][0]
    signed_winding = point["aggregates"]["initialization.local_winding.initial_total_signed_winding"]
    mean_abs2 = point["aggregates"]["early_window.mean_abs2_final"]

    assert payload["overall_status"] == "success"
    assert payload["observable_classification"]["initialization.local_winding.initial_total_signed_winding"] == "initialization_observable"
    assert payload["observable_classification"]["early_window.mean_abs2_final"] == "early_window_observable"
    assert signed_winding == {"mean": 1.0, "std": 0.0, "min": 1.0, "max": 1.0}
    assert mean_abs2["mean"] == pytest.approx(0.9)
    assert mean_abs2["std"] == pytest.approx(0.1)
    assert mean_abs2["min"] == pytest.approx(0.8)
    assert mean_abs2["max"] == pytest.approx(1.0)


def test_aggregate_experiment_results_raises_on_failed_record() -> None:
    failed_record = _successful_run_record(run_id="run_b", repetition_index=1)
    failed_record["status"] = "failed"
    failed_record["observables"] = {}

    with pytest.raises(AggregationError, match="fail-closed"):
        aggregate_experiment_results(
            schema_version="3.0",
            pack_name="unit_pack",
            manifest_path="unit_pack.yaml",
            base_case_path="base_case.yaml",
            repetitions=2,
            sweep_parameters=["forcing.a_rf"],
            observables=["early_window.mean_abs2_final"],
            aggregation_metrics=["mean"],
            run_records=[
                _successful_run_record(run_id="run_a", repetition_index=0),
                failed_record,
            ],
        )


def test_aggregate_experiment_results_raises_on_missing_observable() -> None:
    incomplete_record = _successful_run_record(run_id="run_b", repetition_index=1)
    incomplete_record["observables"] = {
        "initialization.local_winding.initial_total_signed_winding": 1
    }

    with pytest.raises(AggregationError, match="missing observable 'early_window.mean_abs2_final'"):
        aggregate_experiment_results(
            schema_version="3.0",
            pack_name="unit_pack",
            manifest_path="unit_pack.yaml",
            base_case_path="base_case.yaml",
            repetitions=2,
            sweep_parameters=["forcing.a_rf"],
            observables=["early_window.mean_abs2_final"],
            aggregation_metrics=["mean"],
            run_records=[
                _successful_run_record(run_id="run_a", repetition_index=0),
                incomplete_record,
            ],
        )


def test_aggregate_ensemble_results_raises_when_member_set_is_incomplete() -> None:
    with pytest.raises(AggregationError, match="expected 3 ensemble members but observed 2"):
        aggregate_ensemble_results(
            schema_version="4.0",
            pack_name="unit_pack_v4",
            manifest_path="unit_pack_v4.yaml",
            base_case_path="base_case.yaml",
            parent_manifest_hash="abc123",
            expected_member_count=3,
            sweep_parameters=["forcing.a_rf"],
            observables=["early_window.mean_abs2_final"],
            aggregation_metrics=["mean"],
            run_records=[
                {
                    "run_id": "member_a",
                    "ensemble_id": "ensemble_a",
                    "param_set_hash": "param_a",
                    "parameters": {"forcing.a_rf": 0.0},
                    "member_index": 0,
                    "noise_seed": 11,
                    "run_dir": "member_a",
                    "case_class": "short_horizon",
                    "status": "success",
                    "observables": {"early_window.mean_abs2_final": 0.8},
                    "notes": "ok",
                },
                {
                    "run_id": "member_b",
                    "ensemble_id": "ensemble_a",
                    "param_set_hash": "param_a",
                    "parameters": {"forcing.a_rf": 0.0},
                    "member_index": 1,
                    "noise_seed": 12,
                    "run_dir": "member_b",
                    "case_class": "short_horizon",
                    "status": "success",
                    "observables": {"early_window.mean_abs2_final": 1.0},
                    "notes": "ok",
                },
            ],
        )
