"""Aggregation utilities for deterministic and stochastic seeded-vortex experiment packs."""

from __future__ import annotations

from collections import OrderedDict
import math
from pathlib import Path
from statistics import pstdev
from typing import Any, Sequence

from tdgl_rf.exceptions import AggregationError, ManifestValidationError
from tdgl_rf.io.reports import write_csv, write_json
from tdgl_rf.analysis.experiment_robustness import compute_robustness_summary

ALLOWED_EXPERIMENT_AGGREGATION_METRICS = ("mean", "std", "min", "max")
EXPERIMENT_HARNESS_CLAIM_SCOPE = (
    "Deterministic same-stack repetition and aggregation of committed seeded "
    "initialization / short-horizon Tier-2 observables only."
)
EXPERIMENT_HARNESS_NON_CLAIMS = {
    "equilibrium_preparation": "not established by this experiment harness",
    "long_time_dynamics": "not established by this experiment harness",
    "stochastic_behavior": "not established by this experiment harness",
    "cross_stack_portability": "not established by this experiment harness",
}
ENSEMBLE_HARNESS_CLAIM_SCOPE = (
    "Stochastic same-stack ensemble aggregation of committed seeded initialization / "
    "short-horizon Tier-2 observables only."
)
ENSEMBLE_HARNESS_NON_CLAIMS = {
    "equilibrium_preparation": "not established by this ensemble harness",
    "long_time_dynamics": "not established by this ensemble harness",
    "cross_stack_portability": "not established by this ensemble harness",
}


def classify_experiment_observable(observable_name: str) -> str:
    """Classify one extracted seeded-vortex observable by interpretive surface."""

    if observable_name.startswith("initialization."):
        return "initialization_observable"
    if observable_name.startswith("early_window."):
        return "early_window_observable"
    raise ManifestValidationError(f"unsupported experiment observable '{observable_name}'")


def _coerce_numeric_observable(value: Any, *, observable_name: str) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    raise AggregationError(
        f"experiment observable '{observable_name}' must resolve to a finite scalar; observed {value!r}"
    )


def _aggregate_series(values: Sequence[float], metrics: Sequence[str]) -> dict[str, float]:
    """Aggregate one observable series using the manifest-approved metrics only."""

    if not values:
        raise AggregationError("cannot aggregate an empty observable series")
    aggregated: dict[str, float] = {}
    if "mean" in metrics:
        aggregated["mean"] = float(sum(values) / len(values))
    if "std" in metrics:
        aggregated["std"] = float(pstdev(values)) if len(values) > 1 else 0.0
    if "min" in metrics:
        aggregated["min"] = float(min(values))
    if "max" in metrics:
        aggregated["max"] = float(max(values))
    return aggregated


def _record_sort_key(record: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(record["param_set_hash"]),
        int(record.get("repetition_index", -1) if record.get("repetition_index") is not None else -1),
        int(record.get("member_index", -1) if record.get("member_index") is not None else -1),
        str(record["run_id"]),
    )


def _validate_group_consistency(
    grouped_records: Sequence[dict[str, Any]],
    *,
    param_set_hash: str,
    repetitions: int,
) -> tuple[dict[str, Any], str]:
    """Fail closed unless one parameter point resolves to one deterministic result family."""

    if len(grouped_records) != int(repetitions):
        raise AggregationError(
            f"parameter point '{param_set_hash}' expected {repetitions} repetitions but observed {len(grouped_records)}"
        )
    if any(str(record.get("status")) != "success" for record in grouped_records):
        raise AggregationError(
            f"parameter point '{param_set_hash}' contains non-successful run records; deterministic aggregation is fail-closed"
        )

    first_parameters = dict(grouped_records[0]["parameters"])
    case_class = grouped_records[0].get("case_class")
    for record in grouped_records[1:]:
        if dict(record["parameters"]) != first_parameters:
            raise AggregationError(
                f"parameter point '{param_set_hash}' contains inconsistent swept-parameter payloads"
            )
        if record.get("case_class") != case_class:
            raise AggregationError(
                f"parameter point '{param_set_hash}' contains inconsistent case_class values"
            )
    return first_parameters, str(case_class) if case_class is not None else None


def _validate_ensemble_group_consistency(
    grouped_records: Sequence[dict[str, Any]],
    *,
    param_set_hash: str,
    expected_member_count: int,
) -> tuple[dict[str, Any], str | None, str]:
    if len(grouped_records) != int(expected_member_count):
        raise AggregationError(
            f"parameter point '{param_set_hash}' expected {expected_member_count} ensemble members but observed {len(grouped_records)}"
        )
    if any(str(record.get("status")) != "success" for record in grouped_records):
        raise AggregationError(
            f"parameter point '{param_set_hash}' contains non-successful ensemble members; aggregation is fail-closed"
        )

    member_indices = sorted(int(record.get("member_index", -1)) for record in grouped_records)
    expected_indices = list(range(int(expected_member_count)))
    if member_indices != expected_indices:
        raise AggregationError(
            f"parameter point '{param_set_hash}' is missing ensemble members; expected indices {expected_indices} observed {member_indices}"
        )

    first_parameters = dict(grouped_records[0]["parameters"])
    case_class = grouped_records[0].get("case_class")
    ensemble_id = str(grouped_records[0].get("ensemble_id"))
    for record in grouped_records[1:]:
        if dict(record["parameters"]) != first_parameters:
            raise AggregationError(
                f"parameter point '{param_set_hash}' contains inconsistent swept-parameter payloads"
            )
        if record.get("case_class") != case_class:
            raise AggregationError(
                f"parameter point '{param_set_hash}' contains inconsistent case_class values"
            )
        if str(record.get("ensemble_id")) != ensemble_id:
            raise AggregationError(
                f"parameter point '{param_set_hash}' contains inconsistent ensemble_id values"
            )
    return first_parameters, str(case_class) if case_class is not None else None, ensemble_id


def aggregate_experiment_results(
    *,
    schema_version: str,
    pack_name: str,
    manifest_path: str,
    base_case_path: str,
    repetitions: int,
    sweep_parameters: Sequence[str],
    observables: Sequence[str],
    aggregation_metrics: Sequence[str],
    run_records: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate Tier-2 observables across deterministic experiment repetitions.

    The aggregation contract is intentionally strict: every repetition for one parameter point
    must succeed and expose the same observable surface before any summary statistic is emitted.
    """

    if not run_records:
        raise AggregationError("deterministic experiment aggregation requires at least one successful run record")

    ordered_run_records = [dict(record) for record in sorted(run_records, key=_record_sort_key)]
    parameter_points: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for record in ordered_run_records:
        parameter_points.setdefault(str(record["param_set_hash"]), []).append(record)

    observable_classification = OrderedDict(
        (
            observable_name,
            classify_experiment_observable(observable_name),
        )
        for observable_name in observables
    )

    parameter_summaries: list[dict[str, Any]] = []
    for param_set_hash, grouped_records in parameter_points.items():
        sorted_group = list(sorted(grouped_records, key=_record_sort_key))
        parameters, case_class = _validate_group_consistency(
            sorted_group,
            param_set_hash=param_set_hash,
            repetitions=repetitions,
        )
        aggregates: dict[str, dict[str, float]] = OrderedDict()
        for observable_name in observables:
            series: list[float] = []
            for record in sorted_group:
                observables_payload = record.get("observables")
                if not isinstance(observables_payload, dict):
                    raise AggregationError(
                        f"run '{record.get('run_id')}' is missing extracted observables for aggregation"
                    )
                if observable_name not in observables_payload:
                    raise AggregationError(
                        f"run '{record.get('run_id')}' is missing observable '{observable_name}'"
                    )
                series.append(
                    _coerce_numeric_observable(
                        observables_payload[observable_name],
                        observable_name=observable_name,
                    )
                )
            aggregates[observable_name] = _aggregate_series(series, aggregation_metrics)

        parameter_summaries.append(
            OrderedDict(
                [
                    ("param_set_hash", param_set_hash),
                    ("parameters", parameters),
                    ("case_class", case_class),
                    ("run_count", len(sorted_group)),
                    ("successful_run_count", len(sorted_group)),
                    ("run_ids", [str(record["run_id"]) for record in sorted_group]),
                    ("run_dirs", [str(record["run_dir"]) for record in sorted_group]),
                    ("observable_classification", dict(observable_classification)),
                    ("status", "success"),
                    ("aggregates", aggregates),
                    ("notes", "aggregated deterministic same-stack Tier-2 observables"),
                ]
            )
        )

    return OrderedDict(
        [
            ("schema_version", schema_version),
            ("pack_name", pack_name),
            ("manifest_path", manifest_path),
            ("claim_scope", EXPERIMENT_HARNESS_CLAIM_SCOPE),
            ("non_claims", dict(EXPERIMENT_HARNESS_NON_CLAIMS)),
            ("base_case_path", base_case_path),
            ("repetitions", int(repetitions)),
            ("sweep_parameters", list(sweep_parameters)),
            ("observables", list(observables)),
            ("aggregation_metrics", list(aggregation_metrics)),
            ("observable_classification", dict(observable_classification)),
            ("parameter_point_count", len(parameter_summaries)),
            ("run_count", len(ordered_run_records)),
            ("parameter_points", parameter_summaries),
            ("run_records", ordered_run_records),
            ("overall_status", "success"),
        ]
    )


def aggregate_ensemble_results(
    *,
    schema_version: str,
    pack_name: str,
    manifest_path: str,
    base_case_path: str,
    parent_manifest_hash: str,
    expected_member_count: int,
    sweep_parameters: Sequence[str],
    observables: Sequence[str],
    aggregation_metrics: Sequence[str],
    run_records: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate Tier-2 observables across a stochastic ensemble.

    Aggregation is fail-closed: every expected member for one parameter point must succeed and
    expose the full observable set before any artifact can be emitted.
    """

    if not run_records:
        raise AggregationError("stochastic ensemble aggregation requires at least one successful run record")

    ordered_run_records = [dict(record) for record in sorted(run_records, key=_record_sort_key)]
    parameter_points: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for record in ordered_run_records:
        parameter_points.setdefault(str(record["param_set_hash"]), []).append(record)

    observable_classification = OrderedDict(
        (
            observable_name,
            classify_experiment_observable(observable_name),
        )
        for observable_name in observables
    )

    parameter_summaries: list[dict[str, Any]] = []
    for param_set_hash, grouped_records in parameter_points.items():
        sorted_group = list(sorted(grouped_records, key=_record_sort_key))
        parameters, case_class, ensemble_id = _validate_ensemble_group_consistency(
            sorted_group,
            param_set_hash=param_set_hash,
            expected_member_count=expected_member_count,
        )
        aggregates: dict[str, dict[str, float]] = OrderedDict()
        for observable_name in observables:
            series: list[float] = []
            for record in sorted_group:
                observables_payload = record.get("observables")
                if not isinstance(observables_payload, dict):
                    raise AggregationError(
                        f"ensemble member '{record.get('run_id')}' is missing extracted observables for aggregation"
                    )
                if observable_name not in observables_payload:
                    raise AggregationError(
                        f"ensemble member '{record.get('run_id')}' is missing observable '{observable_name}'"
                    )
                series.append(
                    _coerce_numeric_observable(
                        observables_payload[observable_name],
                        observable_name=observable_name,
                    )
                )
            aggregates[observable_name] = _aggregate_series(series, aggregation_metrics)
        robustness_summary = compute_robustness_summary(
            run_records=sorted_group,
            observables=observables,
        )

        parameter_summaries.append(
            OrderedDict(
                [
                    ("param_set_hash", param_set_hash),
                    ("ensemble_id", ensemble_id),
                    ("parameters", parameters),
                    ("case_class", case_class),
                    ("run_count", len(sorted_group)),
                    ("successful_run_count", len(sorted_group)),
                    ("run_ids", [str(record["run_id"]) for record in sorted_group]),
                    ("run_dirs", [str(record["run_dir"]) for record in sorted_group]),
                    ("member_indices", [int(record["member_index"]) for record in sorted_group]),
                    ("noise_seeds", [int(record["noise_seed"]) for record in sorted_group]),
                    ("observable_classification", dict(observable_classification)),
                    ("robustness_summary", robustness_summary),
                    ("status", "success"),
                    ("aggregates", aggregates),
                    ("notes", "aggregated stochastic same-stack Tier-2 observables"),
                ]
            )
        )

    return OrderedDict(
        [
            ("schema_version", schema_version),
            ("mode", "stochastic_ensemble"),
            ("pack_name", pack_name),
            ("manifest_path", manifest_path),
            ("claim_scope", ENSEMBLE_HARNESS_CLAIM_SCOPE),
            ("non_claims", dict(ENSEMBLE_HARNESS_NON_CLAIMS)),
            ("base_case_path", base_case_path),
            ("parent_manifest_hash", parent_manifest_hash),
            ("expected_member_count", int(expected_member_count)),
            ("sweep_parameters", list(sweep_parameters)),
            ("observables", list(observables)),
            ("aggregation_metrics", list(aggregation_metrics)),
            ("observable_classification", dict(observable_classification)),
            ("parameter_point_count", len(parameter_summaries)),
            ("run_count", len(ordered_run_records)),
            ("parameter_points", parameter_summaries),
            ("run_records", ordered_run_records),
            ("overall_status", "success"),
        ]
    )


def experiment_results_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten aggregated experiment results into one CSV row per parameter point.

    Column names retain the observable namespace so downstream tooling can join CSV exports back
    to the JSON payload without an external schema registry.
    """

    rows: list[dict[str, Any]] = []
    sweep_parameters = list(payload["sweep_parameters"])
    observables = list(payload["observables"])
    metrics = list(payload["aggregation_metrics"])
    for point in payload["parameter_points"]:
        row: dict[str, Any] = OrderedDict(
            [
                ("pack_name", payload["pack_name"]),
                ("mode", payload.get("mode", "deterministic_sweep")),
                ("claim_scope", payload["claim_scope"]),
                ("param_set_hash", point["param_set_hash"]),
                ("case_class", point.get("case_class")),
                ("status", point["status"]),
                ("run_count", point["run_count"]),
                ("successful_run_count", point["successful_run_count"]),
                ("notes", point["notes"]),
            ]
        )
        if "ensemble_id" in point:
            row["ensemble_id"] = point["ensemble_id"]
        for parameter_name in sweep_parameters:
            row[f"parameter.{parameter_name}"] = point["parameters"].get(parameter_name)
        robustness_summary = point.get("robustness_summary")
        if isinstance(robustness_summary, dict):
            row["robustness.member_count"] = robustness_summary.get("member_count")
            row["robustness.successful_member_count"] = robustness_summary.get("successful_member_count")
            row["robustness.failed_member_count"] = robustness_summary.get("failed_member_count")
            row["robustness.failure_rate"] = robustness_summary.get("failure_rate")
        aggregates = point["aggregates"]
        for observable_name in observables:
            row[f"classification.{observable_name}"] = payload["observable_classification"][observable_name]
            for metric_name in metrics:
                row[f"{observable_name}.{metric_name}"] = aggregates[observable_name][metric_name]
            if isinstance(robustness_summary, dict):
                observable_robustness = robustness_summary.get("observables", {}).get(observable_name, {})
                row[f"robustness.{observable_name}.successful_member_count"] = observable_robustness.get(
                    "successful_member_count"
                )
                row[f"robustness.{observable_name}.coefficient_of_variation"] = observable_robustness.get(
                    "coefficient_of_variation"
                )
                row[f"robustness.{observable_name}.coefficient_of_variation_defined"] = observable_robustness.get(
                    "coefficient_of_variation_defined"
                )
                row[f"robustness.{observable_name}.sign_consistency"] = observable_robustness.get(
                    "sign_consistency"
                )
        rows.append(row)
    return rows


def experiment_results_markdown(payload: dict[str, Any]) -> str:
    """Render a reviewer-facing Markdown summary for one experiment harness run."""

    lines = [
        "# Seeded-Vortex Experiment Harness",
        "",
        f"- Pack name: `{payload['pack_name']}`",
        f"- Mode: `{payload.get('mode', 'deterministic_sweep')}`",
        f"- Manifest: `{payload['manifest_path']}`",
        f"- Base case: `{payload['base_case_path']}`",
        f"- Overall status: `{payload['overall_status']}`",
        (
            f"- Repetitions per parameter point: `{payload['repetitions']}`"
            if "repetitions" in payload
            else f"- Ensemble members per parameter point: `{payload['expected_member_count']}`"
        ),
        f"- Parameter points: `{payload['parameter_point_count']}`",
        "",
        "## Interpretation Boundary",
        "",
        payload["claim_scope"],
        "",
        "- `equilibrium_preparation`: " + payload["non_claims"]["equilibrium_preparation"],
        "- `long_time_dynamics`: " + payload["non_claims"]["long_time_dynamics"],
        "- `cross_stack_portability`: " + payload["non_claims"]["cross_stack_portability"],
        "",
        "## Parameter Points",
        "",
        "| param_set_hash | case_class | status | successful runs | parameters | notes |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for point in payload["parameter_points"]:
        parameter_text = ", ".join(
            f"{key}={value!r}" for key, value in sorted(point["parameters"].items())
        )
        lines.append(
            "| {param_set_hash} | {case_class} | {status} | {successful_run_count}/{run_count} | {parameters} | {notes} |".format(
                param_set_hash=point["param_set_hash"],
                case_class=point.get("case_class") or "n/a",
                status=point["status"],
                successful_run_count=point["successful_run_count"],
                run_count=point["run_count"],
                parameters=parameter_text,
                notes=point["notes"],
            )
        )
    lines.extend(
        [
            "",
            "## Aggregated Observables",
            "",
            "| param_set_hash | observable | classification | aggregates |",
            "| --- | --- | --- | --- |",
        ]
    )
    for point in payload["parameter_points"]:
        for observable_name in payload["observables"]:
            aggregate_text = ", ".join(
                f"{metric}={point['aggregates'][observable_name][metric]!r}"
                for metric in payload["aggregation_metrics"]
            )
            lines.append(
                "| {param_set_hash} | {observable} | {classification} | {aggregates} |".format(
                    param_set_hash=point["param_set_hash"],
                    observable=observable_name,
                    classification=payload["observable_classification"][observable_name],
                    aggregates=aggregate_text,
                )
            )
    if any("robustness_summary" in point for point in payload["parameter_points"]):
        lines.extend(
            [
                "",
                "## Ensemble Robustness Summary",
                "",
                "| param_set_hash | failure_rate | observable | coefficient_of_variation | cv_defined | sign_consistency |",
                "| --- | ---: | --- | ---: | --- | ---: |",
            ]
        )
        for point in payload["parameter_points"]:
            robustness_summary = point.get("robustness_summary")
            if not isinstance(robustness_summary, dict):
                continue
            for observable_name in payload["observables"]:
                observable_robustness = robustness_summary["observables"][observable_name]
                coefficient_of_variation = observable_robustness["coefficient_of_variation"]
                lines.append(
                    "| {param_set_hash} | {failure_rate!r} | {observable} | {coefficient_of_variation!r} | {cv_defined} | {sign_consistency!r} |".format(
                        param_set_hash=point["param_set_hash"],
                        failure_rate=robustness_summary["failure_rate"],
                        observable=observable_name,
                        coefficient_of_variation=coefficient_of_variation,
                        cv_defined=observable_robustness["coefficient_of_variation_defined"],
                        sign_consistency=observable_robustness["sign_consistency"],
                    )
                )
    lines.append("")
    return "\n".join(lines)


def write_experiment_result_artifacts(output_dir: str | Path, payload: dict[str, Any]) -> dict[str, str]:
    """Write the deterministic experiment result bundle with stable file names."""

    destination = Path(output_dir)
    results_json_path = destination / "experiment_results.json"
    results_csv_path = destination / "experiment_results.csv"
    results_markdown_path = destination / "experiment_results.md"
    write_json(results_json_path, payload)
    write_csv(results_csv_path, experiment_results_rows(payload))
    results_markdown_path.write_text(experiment_results_markdown(payload), encoding="utf-8")
    return {
        "results_json_path": str(results_json_path),
        "results_csv_path": str(results_csv_path),
        "results_markdown_path": str(results_markdown_path),
    }
