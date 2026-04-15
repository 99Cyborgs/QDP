"""Robustness metrics for Phase-2.4A ensemble post-processing."""

from __future__ import annotations

from collections import OrderedDict
import math
from statistics import pstdev
from typing import Any, Sequence

from tdgl_rf.exceptions import AggregationError


def _coerce_numeric_series(values: Sequence[Any], *, label: str) -> list[float]:
    """Validate that a candidate robustness series is numeric, finite, and non-empty."""

    if not values:
        raise AggregationError(f"{label} requires at least one numeric value")
    series: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise AggregationError(f"{label} requires finite numeric values; observed {value!r}")
        series.append(float(value))
    return series


def coefficient_of_variation(values: Sequence[Any]) -> float:
    """Return the population standard deviation divided by the absolute mean.

    The denominator uses `abs(mean)` so the metric remains sign-agnostic for observables that can
    flip orientation while still becoming undefined at a true zero mean.
    """

    series = _coerce_numeric_series(values, label="coefficient_of_variation")
    mean_value = float(sum(series) / len(series))
    if mean_value == 0.0:
        raise AggregationError("coefficient_of_variation is undefined for a zero-mean series")
    return float(pstdev(series) / abs(mean_value)) if len(series) > 1 else 0.0


def failure_rate(*, failed_count: int, total_count: int) -> float:
    """Return the failed-member fraction."""

    if int(total_count) <= 0:
        raise AggregationError("failure_rate requires total_count >= 1")
    if int(failed_count) < 0 or int(failed_count) > int(total_count):
        raise AggregationError("failure_rate requires 0 <= failed_count <= total_count")
    return float(int(failed_count) / int(total_count))


def sign_consistency(values: Sequence[Any]) -> float:
    """Return the dominant-sign fraction across non-zero numeric values."""

    series = _coerce_numeric_series(values, label="sign_consistency")
    non_zero_signs = [1 if value > 0.0 else -1 for value in series if value != 0.0]
    if not non_zero_signs:
        return 1.0
    positive_count = sum(sign > 0 for sign in non_zero_signs)
    negative_count = len(non_zero_signs) - positive_count
    return float(max(positive_count, negative_count) / len(non_zero_signs))


def compute_robustness_summary(
    *,
    run_records: Sequence[dict[str, Any]],
    observables: Sequence[str],
) -> dict[str, Any]:
    """Aggregate count and robustness metrics over ensemble member run records.

    Failed ensemble members are counted in the headline rate but excluded from per-observable
    statistics because they do not provide a numerically meaningful value surface.
    """

    if not run_records:
        raise AggregationError("robustness summary requires at least one ensemble member record")

    successful_records = [record for record in run_records if str(record.get("status")) == "success"]
    failed_count = len(run_records) - len(successful_records)
    if not successful_records:
        raise AggregationError("robustness summary requires at least one successful ensemble member")

    observable_summary: dict[str, Any] = OrderedDict()
    for observable_name in observables:
        values: list[float] = []
        for record in successful_records:
            observables_payload = record.get("observables")
            if not isinstance(observables_payload, dict) or observable_name not in observables_payload:
                raise AggregationError(
                    f"ensemble member '{record.get('run_id')}' is missing observable '{observable_name}'"
                )
            values.append(float(_coerce_numeric_series([observables_payload[observable_name]], label=observable_name)[0]))
        observable_summary[observable_name] = OrderedDict(
            [
                ("successful_member_count", len(values)),
                ("coefficient_of_variation", coefficient_of_variation(values)),
                ("sign_consistency", sign_consistency(values)),
            ]
        )

    return OrderedDict(
        [
            ("member_count", len(run_records)),
            ("successful_member_count", len(successful_records)),
            ("failed_member_count", failed_count),
            ("failure_rate", failure_rate(failed_count=failed_count, total_count=len(run_records))),
            ("observables", observable_summary),
        ]
    )
