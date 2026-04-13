from __future__ import annotations

import pytest

from tdgl_rf.analysis.experiment_robustness import (
    coefficient_of_variation,
    compute_robustness_summary,
    failure_rate,
    sign_consistency,
)


def test_coefficient_of_variation_uses_population_std() -> None:
    assert coefficient_of_variation([1.0, 2.0, 3.0]) == pytest.approx(0.408248290463863)


def test_failure_rate_returns_failed_fraction() -> None:
    assert failure_rate(failed_count=1, total_count=4) == pytest.approx(0.25)


def test_sign_consistency_returns_dominant_sign_fraction() -> None:
    assert sign_consistency([1.0, 2.0, -3.0]) == pytest.approx(2.0 / 3.0)


def test_compute_robustness_summary_reports_counts_and_observables() -> None:
    summary = compute_robustness_summary(
        run_records=[
            {
                "run_id": "member_a",
                "status": "success",
                "observables": {"early_window.mean_abs2_final": 0.8},
            },
            {
                "run_id": "member_b",
                "status": "success",
                "observables": {"early_window.mean_abs2_final": 1.0},
            },
            {
                "run_id": "member_c",
                "status": "failed",
                "observables": {},
            },
        ],
        observables=["early_window.mean_abs2_final"],
    )

    assert summary["member_count"] == 3
    assert summary["successful_member_count"] == 2
    assert summary["failed_member_count"] == 1
    assert summary["failure_rate"] == pytest.approx(1.0 / 3.0)
    assert summary["observables"]["early_window.mean_abs2_final"]["coefficient_of_variation"] == pytest.approx(0.1 / 0.9)
    assert summary["observables"]["early_window.mean_abs2_final"]["coefficient_of_variation_defined"] is True
    assert summary["observables"]["early_window.mean_abs2_final"]["sign_consistency"] == pytest.approx(1.0)


def test_compute_robustness_summary_marks_zero_mean_cv_as_undefined() -> None:
    summary = compute_robustness_summary(
        run_records=[
            {
                "run_id": "member_a",
                "status": "success",
                "observables": {"initialization.local_winding.initial_total_signed_winding": 1.0},
            },
            {
                "run_id": "member_b",
                "status": "success",
                "observables": {"initialization.local_winding.initial_total_signed_winding": -1.0},
            },
        ],
        observables=["initialization.local_winding.initial_total_signed_winding"],
    )

    observable_summary = summary["observables"]["initialization.local_winding.initial_total_signed_winding"]
    assert observable_summary["coefficient_of_variation"] is None
    assert observable_summary["coefficient_of_variation_defined"] is False
    assert observable_summary["sign_consistency"] == pytest.approx(0.5)
