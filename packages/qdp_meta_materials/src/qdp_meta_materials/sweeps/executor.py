from __future__ import annotations

import heapq
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qdp_io.serialization import write_json

from ..errors import SweepExecutionError
from ..registry import load_dataset
from ..models import MMMDataset, RunSliceProvenance, ScalarValue, ScoreResult
from ..runs import execute_scoring_run
from .aggregator import build_sweep_summary
from .artifacts import write_sweep_outputs
from .contracts import get_equivalence_edges
from .cross_tranche import generate_cross_tranche_tranche
from .models import (
    ExecutionPriorityEntry,
    GovernanceRecommendation,
    ResolvedSlicePlan,
    ResolvedTranchePlan,
    SliceExecutionRecord,
    SliceNullModelComparison,
    SliceRunStatus,
    SweepManifest,
    SweepRunStatus,
    SweepSpec,
    SweepSummary,
    TrancheExecutionRecord,
    TrancheType,
)
from .planner import (
    _candidate_id_hash,
    _rank_slice_candidates,
    _slice_null_model_comparison,
    build_tranche_execution_record,
    generate_discriminator_tranches_from_summary,
    generate_refinement_slices,
    load_sweep_spec,
    plan_sweep,
    prune_pending_slices,
    update_slice_utilities,
)


def execute_sweep(
    spec: SweepSpec,
    *,
    dataset_root: str | Path | None = None,
    output_dir: str | Path | None = None,
    command: str = "qdp-meta-materials sweep-run",
    spec_source: str | Path | None = None,
) -> tuple[SweepManifest, SweepSummary]:
    """Plan and execute a sweep spec end to end."""

    manifest = plan_sweep(
        spec,
        dataset_root=dataset_root,
        output_dir=output_dir,
        command=command,
        spec_source=spec_source,
    )
    output_root = Path(manifest.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    manifest.status = SweepRunStatus.RUNNING
    manifest.started_at = datetime.now(UTC)
    _persist_manifest(manifest)

    dataset = load_dataset(manifest.dataset_root)
    slice_results: dict[tuple[str, str], list[ScoreResult]] = {}

    for tranche_plan, tranche_record in _ordered_tranche_pairs(manifest):
        _execute_tranche(
            manifest=manifest,
            dataset=dataset,
            tranche_plan=tranche_plan,
            tranche_record=tranche_record,
            slice_results=slice_results,
            command=command,
            include_refinement=manifest.adaptive.enabled,
            initial_phase=1,
        )

    if manifest.adaptive.enabled:
        interaction_tranche = generate_cross_tranche_tranche(manifest, dataset=dataset)
        if interaction_tranche is not None:
            manifest.plan.tranches.append(interaction_tranche)
            interaction_record = build_tranche_execution_record(interaction_tranche)
            manifest.tranches.append(interaction_record)
            _persist_manifest(manifest)
            prune_pending_slices(
                manifest,
                slice_results=slice_results,
                tranche_id=interaction_tranche.tranche_id,
            )
            _persist_manifest(manifest)
            _execute_tranche(
                manifest=manifest,
                dataset=dataset,
                tranche_plan=interaction_tranche,
                tranche_record=interaction_record,
                slice_results=slice_results,
                command=command,
                include_refinement=False,
                initial_phase=3,
            )

    summary = build_sweep_summary(manifest, slice_results)
    if manifest.adaptive.enabled and manifest.measurement.discriminator_generation_limit > 0:
        generation = 2
        while generation <= manifest.measurement.discriminator_generation_limit:
            if not any(edge.equivalence_margin < 1.0 for edge in get_equivalence_edges(summary)):
                break
            discriminator_tranches = generate_discriminator_tranches_from_summary(
                manifest,
                summary=summary,
                dataset=dataset,
                generation=generation,
            )
            if not discriminator_tranches:
                break
            for discriminator_tranche in discriminator_tranches:
                manifest.plan.tranches.append(discriminator_tranche)
                discriminator_record = build_tranche_execution_record(discriminator_tranche)
                manifest.tranches.append(discriminator_record)
                _persist_manifest(manifest)
                _execute_tranche(
                    manifest=manifest,
                    dataset=dataset,
                    tranche_plan=discriminator_tranche,
                    tranche_record=discriminator_record,
                    slice_results=slice_results,
                    command=command,
                    include_refinement=False,
                    initial_phase=2,
                )
            summary = build_sweep_summary(manifest, slice_results)
            if not any(edge.equivalence_margin < 1.0 for edge in get_equivalence_edges(summary)):
                break
            generation += 1
    manifest.completed_at = datetime.now(UTC)
    manifest.metrics_summary = _build_sweep_metrics(summary)
    manifest.status = _derive_sweep_status(summary)
    _apply_tranche_summaries(manifest, summary)
    manifest.artifact_paths.update(
        {
            "cross_slice_score_plot": str(
                output_root / "plots" / "cross_slice_score_comparison.png"
            ),
            "robustness_plot": str(output_root / "plots" / "robustness_overview.png"),
        }
    )
    write_sweep_outputs(manifest, summary, slice_results)
    _persist_manifest(manifest)
    return manifest, summary


def execute_sweep_from_path(
    spec_path: str | Path,
    *,
    dataset_root: str | Path | None = None,
    output_dir: str | Path | None = None,
    command: str = "qdp-meta-materials sweep-run",
) -> tuple[SweepManifest, SweepSummary]:
    """Load a sweep spec from disk and execute it."""

    spec = load_sweep_spec(spec_path)
    return execute_sweep(
        spec,
        dataset_root=dataset_root,
        output_dir=output_dir,
        command=command,
        spec_source=spec_path,
    )


def _execute_tranche(
    *,
    manifest: SweepManifest,
    dataset: MMMDataset,
    tranche_plan: ResolvedTranchePlan,
    tranche_record: TrancheExecutionRecord,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
    command: str,
    include_refinement: bool,
    initial_phase: int,
) -> None:
    Path(tranche_record.output_dir).mkdir(parents=True, exist_ok=True)
    tranche_record.status = SweepRunStatus.RUNNING
    _persist_manifest(manifest)

    phases = sorted(
        {
            slice_plan.phase
            for slice_plan in tranche_plan.slices
            if slice_plan.phase >= initial_phase
        }
    )
    for phase in phases:
        _execute_priority_queue(
            manifest=manifest,
            dataset=dataset,
            tranche_plan=tranche_plan,
            tranche_record=tranche_record,
            slice_results=slice_results,
            command=command,
            phase=phase,
        )

    if include_refinement and tranche_plan.tranche_type not in {
        TrancheType.NULL_MODEL,
        TrancheType.NULL_DOMINANCE_TRANCHE,
    }:
        update_slice_utilities(
            manifest,
            dataset=dataset,
            slice_results=slice_results,
            tranche_id=tranche_plan.tranche_id,
        )
        generated = generate_refinement_slices(
            manifest,
            dataset=dataset,
            tranche_id=tranche_plan.tranche_id,
        )
        if generated:
            _append_generated_slices(tranche_plan, tranche_record, generated)
            _persist_manifest(manifest)
            prune_pending_slices(
                manifest,
                slice_results=slice_results,
                tranche_id=tranche_plan.tranche_id,
            )
            _persist_manifest(manifest)
            _execute_priority_queue(
                manifest=manifest,
                dataset=dataset,
                tranche_plan=tranche_plan,
                tranche_record=tranche_record,
                slice_results=slice_results,
                command=command,
                phase=2,
            )
            update_slice_utilities(
                manifest,
                dataset=dataset,
                slice_results=slice_results,
                tranche_id=tranche_plan.tranche_id,
            )

    tranche_record.status = _derive_tranche_status(tranche_record.slice_statuses)
    tranche_record.metrics_summary = _build_tranche_metrics(tranche_record.slice_statuses)
    _persist_manifest(manifest)


def _execute_priority_queue(
    *,
    manifest: SweepManifest,
    dataset: MMMDataset,
    tranche_plan: ResolvedTranchePlan,
    tranche_record: TrancheExecutionRecord,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
    command: str,
    phase: int,
) -> None:
    queue: list[tuple[float, float, float, int, int, str]] = []
    indexed_slices = list(zip(tranche_plan.slices, tranche_record.slice_statuses, strict=True))
    slice_index = {
        slice_plan.slice_id: (slice_plan, slice_record)
        for slice_plan, slice_record in indexed_slices
    }
    for serial, (slice_plan, slice_record) in enumerate(indexed_slices):
        if slice_plan.phase != phase or slice_record.status != SliceRunStatus.PENDING:
            continue
        heapq.heappush(
            queue,
            (
                0.0 if _null_pair_ready(slice_plan, slice_index) else 1.0,
                float(_execution_type_priority(slice_plan.tranche_type)),
                -slice_plan.utility.utility_score,
                slice_plan.lineage_depth,
                serial,
                slice_plan.slice_id,
            ),
        )

    while queue:
        _, _, _, _, queue_serial, slice_id = heapq.heappop(queue)
        slice_plan, slice_record = slice_index[slice_id]
        if slice_record.status != SliceRunStatus.PENDING:
            continue

        priority_order = len(manifest.execution_order) + 1
        slice_record.priority_order = priority_order
        slice_record.execution_order = priority_order
        slice_record.utility = slice_plan.utility.model_copy(deep=True)
        slice_record.score_breakdown = slice_plan.utility.utility_components.model_copy(deep=True)
        manifest.execution_order.append(
            ExecutionPriorityEntry(
                tranche_id=tranche_plan.tranche_id,
                slice_id=slice_plan.slice_id,
                phase=slice_plan.phase,
                tranche_type=slice_plan.tranche_type,
                hypothesis_class=slice_plan.hypothesis_class,
                utility_score=slice_plan.utility.utility_score,
                priority_order=priority_order,
                queue_serial=queue_serial,
                null_pair_id=slice_plan.null_pair_id,
                parent_slice_id=slice_plan.parent_slice_id,
                lineage_depth=slice_plan.lineage_depth,
                source=slice_plan.planning_source.value,
            )
        )
        _persist_manifest(manifest)

        try:
            _validate_null_lineage_lock(manifest, slice_plan, slice_record)
            results, null_comparison = _execute_slice(
                dataset_root=dataset.root,
                dataset=dataset,
                sweep_id=manifest.sweep_id,
                slice_plan=slice_plan,
                slice_record=slice_record,
                command=command,
                null_model_enabled=manifest.adaptive.null_model.enabled,
                baseline_mode=manifest.adaptive.null_model.mode.value
                if manifest.adaptive.null_model.enabled
                else None,
                baseline_profile=manifest.adaptive.null_model.baseline_profile,
                residual_weights=manifest.residual_weights,
                null_model_tolerance=manifest.null_model_tolerance,
            )
            slice_record.null_model_comparison = null_comparison
            slice_results[(slice_plan.tranche_id, slice_plan.slice_id)] = results
        except Exception as exc:  # noqa: BLE001
            slice_record.status = SliceRunStatus.FAILED
            slice_record.completed_at = datetime.now(UTC)
            slice_record.error_message = str(exc)
            _write_slice_failure_artifacts(slice_plan, slice_record)
        finally:
            _persist_manifest(manifest)


def _execute_slice(
    *,
    dataset_root: Path,
    dataset: MMMDataset,
    sweep_id: str,
    slice_plan: ResolvedSlicePlan,
    slice_record: SliceExecutionRecord,
    command: str,
    null_model_enabled: bool,
    baseline_mode: str | None,
    baseline_profile: str | None,
    residual_weights: Any,
    null_model_tolerance: float,
) -> tuple[list[ScoreResult], SliceNullModelComparison]:
    Path(slice_plan.output_dir).mkdir(parents=True, exist_ok=True)
    slice_record.status = SliceRunStatus.RUNNING
    slice_record.started_at = datetime.now(UTC)
    slice_record.candidate_count = slice_plan.candidate_count
    slice_record.tranche_type = slice_plan.tranche_type
    slice_record.tranche_objective = slice_plan.tranche_objective
    slice_record.null_pair_id = slice_plan.null_pair_id
    slice_record.parent_slice_id = slice_plan.parent_slice_id
    slice_record.lineage_depth = slice_plan.lineage_depth
    slice_record.parameter_hash = slice_plan.parameter_hash

    results = _rank_slice_candidates(
        dataset=dataset,
        profile=slice_plan.resolved_profile,
        candidate_ids=slice_plan.candidate_ids,
        tranche_type=slice_plan.tranche_type,
        null_model_enabled=null_model_enabled,
        baseline_mode=baseline_mode if null_model_enabled else None,
        baseline_profile=baseline_profile if null_model_enabled else None,
    )
    if not results:
        raise SweepExecutionError(
            f"Slice '{slice_plan.slice_id}' resolved candidates but produced no score results."
        )

    run_manifest = execute_scoring_run(
        dataset=dataset,
        results=results,
        profile=slice_plan.resolved_profile,
        top_n=slice_plan.resolved_parameters.top_n,
        output_dir=slice_plan.output_dir,
        command=command,
        run_id=f"{sweep_id}.{slice_plan.tranche_id}.{slice_plan.slice_id}",
        params={
            "sweep_id": sweep_id,
            "tranche_id": slice_plan.tranche_id,
            "tranche_type": slice_plan.tranche_type.value,
            "hypothesis_class": slice_plan.hypothesis_class.value,
            "slice_id": slice_plan.slice_id,
            "candidate_count": slice_plan.candidate_count,
            "candidate_ids": ",".join(slice_plan.candidate_ids),
            "tags": ",".join(slice_plan.tags),
            "dataset_root": str(dataset_root),
            "slice_phase": slice_plan.phase,
            "null_pair_id": slice_plan.null_pair_id,
            "parent_slice_id": slice_plan.parent_slice_id,
            "lineage_depth": slice_plan.lineage_depth,
            "parameter_hash": slice_plan.parameter_hash,
            "baseline_mode": baseline_mode if null_model_enabled else None,
            "baseline_profile": baseline_profile if null_model_enabled else None,
        },
        slice_provenance=RunSliceProvenance(
            sweep_id=sweep_id,
            tranche_id=slice_plan.tranche_id,
            tranche_origin=slice_plan.tranche_type.value,
            tranche_type=slice_plan.tranche_type.value,
            tranche_objective=slice_plan.tranche_objective.value,
            hypothesis_class=slice_plan.hypothesis_class.value,
            null_pair_id=slice_plan.null_pair_id,
            parent_slice_id=slice_plan.parent_slice_id,
            lineage_depth=slice_plan.lineage_depth,
            execution_order=slice_record.execution_order,
            parameter_hash=slice_plan.parameter_hash,
            null_lineage_source_tranche_id=(
                slice_plan.lineage.null_lineage_lock.source_tranche_id
                if slice_plan.lineage.null_lineage_lock is not None
                else None
            ),
            null_lineage_source_slice_id=(
                slice_plan.lineage.null_lineage_lock.source_slice_id
                if slice_plan.lineage.null_lineage_lock is not None
                else None
            ),
            null_lineage_source_parameter_hash=(
                slice_plan.lineage.null_lineage_lock.source_parameter_hash
                if slice_plan.lineage.null_lineage_lock is not None
                else None
            ),
            originating_equivalence_cluster_id=slice_plan.originating_equivalence_cluster_id,
            discriminator_rationale=slice_plan.discriminator_rationale,
            discriminator_axis=slice_plan.discriminator_axis,
            target_hypothesis_pair=list(slice_plan.target_hypothesis_pair),
            required_resolution=slice_plan.required_resolution,
            predicted_separation=slice_plan.predicted_separation,
            observed_separation=slice_plan.observed_separation,
            discriminator_gain=slice_plan.discriminator_gain,
            axis_cost=slice_plan.axis_cost,
            redundancy_penalty=slice_plan.redundancy_penalty,
            equivalence_margin=slice_plan.utility.equivalence_margin,
        ),
        score_breakdown=slice_plan.utility.utility_components.model_copy(deep=True),
        results_filename="scores.json",
        write_leaderboard_csv_artifact=slice_plan.output_requirements.write_leaderboard_csv,
        include_plots=slice_plan.output_requirements.write_plots,
        include_candidate_report=slice_plan.output_requirements.write_candidate_report,
        include_simulation_artifacts=False,
    )
    slice_record.status = SliceRunStatus.COMPLETED
    slice_record.completed_at = datetime.now(UTC)
    slice_record.top_candidate_id = run_manifest.top_candidate_id
    top_score = run_manifest.metrics.get("top_score")
    slice_record.top_score = float(top_score) if top_score is not None else None
    slice_record.artifact_paths = run_manifest.artifact_paths
    slice_record.score_breakdown = slice_plan.utility.utility_components.model_copy(deep=True)
    return (
        results,
        _build_null_model_comparison(
            results,
            requested=null_model_enabled,
            baseline_mode=baseline_mode,
            baseline_profile=baseline_profile,
            residual_weights=residual_weights,
            tolerance=null_model_tolerance,
        ),
    )


def _build_null_model_comparison(
    results: list[ScoreResult],
    *,
    requested: bool,
    baseline_mode: str | None,
    baseline_profile: str | None,
    residual_weights: Any,
    tolerance: float,
) -> SliceNullModelComparison:
    baseline_candidates = [result for result in results if result.baseline_score is not None]
    if not requested:
        return SliceNullModelComparison(
            enabled=False,
            requested=False,
            available=False,
            mode=baseline_mode,
            baseline_profile=baseline_profile,
            candidate_count=len(results),
            baseline_candidate_count=len(baseline_candidates),
        )
    if not baseline_candidates:
        return SliceNullModelComparison(
            enabled=False,
            requested=True,
            available=False,
            mode=baseline_mode,
            baseline_profile=baseline_profile,
            candidate_count=len(results),
            baseline_candidate_count=0,
            missing_reason=(
                "Null-model baseline was requested but no baseline scores were produced."
            ),
        )
    comparison = _slice_null_model_comparison(
        results=results,
        axis_values=[float(index) for index in range(len(results))],
        residual_weights=residual_weights,
        tolerance=tolerance,
        existing=SliceNullModelComparison(
            enabled=True,
            requested=True,
            available=True,
            mode=baseline_mode,
            baseline_profile=baseline_profile,
        ),
    )
    return comparison.model_copy(
        update={
            "enabled": True,
            "requested": True,
            "available": True,
        }
    )


def _append_generated_slices(
    tranche_plan: ResolvedTranchePlan,
    tranche_record: TrancheExecutionRecord,
    generated: list[ResolvedSlicePlan],
) -> None:
    tranche_plan.slices.extend(generated)
    tranche_record.slice_statuses.extend(
        [
            SliceExecutionRecord(
                tranche_id=slice_plan.tranche_id,
                slice_id=slice_plan.slice_id,
                phase=slice_plan.phase,
                tranche_type=slice_plan.tranche_type,
                tranche_objective=slice_plan.tranche_objective,
                hypothesis_class=slice_plan.hypothesis_class,
                status=SliceRunStatus.PENDING,
                candidate_count=slice_plan.candidate_count,
                null_pair_id=slice_plan.null_pair_id,
                parent_slice_id=slice_plan.parent_slice_id,
                lineage_depth=slice_plan.lineage_depth,
                output_dir=slice_plan.output_dir,
                parameter_hash=slice_plan.parameter_hash,
                utility=slice_plan.utility.model_copy(deep=True),
                score_breakdown=slice_plan.utility.utility_components.model_copy(deep=True),
            )
            for slice_plan in generated
        ]
    )


def _ordered_tranche_pairs(
    manifest: SweepManifest,
) -> list[tuple[ResolvedTranchePlan, TrancheExecutionRecord]]:
    pairs = list(zip(manifest.plan.tranches, manifest.tranches, strict=True))
    return sorted(
        pairs,
        key=lambda item: (
            _execution_type_priority(item[0].tranche_type),
            min((slice_plan.phase for slice_plan in item[0].slices), default=1),
            item[0].tranche_id,
        ),
    )


def _execution_type_priority(tranche_type: TrancheType) -> int:
    order = {
        TrancheType.NULL_MODEL: 0,
        TrancheType.BASELINE: 1,
        TrancheType.PRIMARY: 2,
        TrancheType.DISCRIMINATION_TRANCHE: 2,
        TrancheType.SCALING_LAW_TRANCHE: 3,
        TrancheType.IDENTIFIABILITY_TRANCHE: 3,
        TrancheType.CROSS_DEVICE_TRANCHE: 4,
        TrancheType.LOCAL_PERTURBATION: 5,
        TrancheType.SCALING: 6,
        TrancheType.FAILURE_MODE_TRANCHE: 7,
        TrancheType.BOUNDARY_STRESS_TRANCHE: 8,
        TrancheType.NULL_DOMINANCE_TRANCHE: 9,
        TrancheType.INTERACTION: 10,
        TrancheType.STRESS_TEST: 11,
    }
    return order.get(tranche_type, 99)


def _null_pair_ready(
    slice_plan: ResolvedSlicePlan,
    slice_index: dict[str, tuple[ResolvedSlicePlan, SliceExecutionRecord]],
) -> bool:
    if slice_plan.tranche_type == TrancheType.NULL_MODEL:
        return True
    if slice_plan.tranche_type != TrancheType.NULL_DOMINANCE_TRANCHE:
        return True
    lock = slice_plan.lineage.null_lineage_lock
    if lock is None:
        return False
    paired = slice_index.get(lock.source_slice_id)
    if paired is None:
        return True
    _, paired_record = paired
    return paired_record.status == SliceRunStatus.COMPLETED


def _validate_null_lineage_lock(
    manifest: SweepManifest,
    slice_plan: ResolvedSlicePlan,
    slice_record: SliceExecutionRecord,
) -> None:
    if slice_plan.tranche_type != TrancheType.NULL_DOMINANCE_TRANCHE:
        return
    lock = slice_plan.lineage.null_lineage_lock
    if lock is None:
        raise SweepExecutionError(
            f"Null-dominance slice '{slice_plan.slice_id}' is missing a locked source lineage."
        )
    source_tranche = next(
        (tranche for tranche in manifest.plan.tranches if tranche.tranche_id == lock.source_tranche_id),
        None,
    )
    if source_tranche is None:
        raise SweepExecutionError(
            f"Null-dominance slice '{slice_plan.slice_id}' references unknown source tranche "
            f"'{lock.source_tranche_id}'."
        )
    source_slice = next(
        (candidate for candidate in source_tranche.slices if candidate.slice_id == lock.source_slice_id),
        None,
    )
    if source_slice is None:
        raise SweepExecutionError(
            f"Null-dominance slice '{slice_plan.slice_id}' references unknown source slice "
            f"'{lock.source_slice_id}'."
        )
    if source_slice.parameter_hash != lock.source_parameter_hash:
        raise SweepExecutionError(
            f"Null-dominance lineage lock mismatch for '{slice_plan.slice_id}': source parameter hash drifted."
        )
    if _candidate_id_hash(source_slice.candidate_ids) != lock.source_candidate_ids_sha256:
        raise SweepExecutionError(
            f"Null-dominance lineage lock mismatch for '{slice_plan.slice_id}': source candidate basis drifted."
        )
    slice_record.null_lineage_lock_verified = True
    slice_record.null_lineage_source = f"{lock.source_tranche_id}:{lock.source_slice_id}"


def _write_slice_failure_artifacts(
    slice_plan: ResolvedSlicePlan,
    slice_record: SliceExecutionRecord,
) -> None:
    failure_metrics = {
        "status": slice_record.status.value,
        "candidate_count": slice_record.candidate_count,
        "error_message": slice_record.error_message,
    }
    write_json(Path(slice_plan.output_dir) / "metrics.json", failure_metrics)
    write_json(
        Path(slice_plan.output_dir) / "error.json",
        {
            "tranche_id": slice_plan.tranche_id,
            "slice_id": slice_plan.slice_id,
            "error_message": slice_record.error_message,
        },
    )
    slice_record.artifact_paths = {
        "metrics": str(Path(slice_plan.output_dir) / "metrics.json"),
        "error": str(Path(slice_plan.output_dir) / "error.json"),
    }


def _derive_tranche_status(slice_records: list[SliceExecutionRecord]) -> SweepRunStatus:
    completed = [record for record in slice_records if record.status == SliceRunStatus.COMPLETED]
    failed = [record for record in slice_records if record.status == SliceRunStatus.FAILED]
    pruned = [record for record in slice_records if record.status == SliceRunStatus.PRUNED]
    if failed and completed:
        return SweepRunStatus.COMPLETED_WITH_FAILURES
    if failed and pruned:
        return SweepRunStatus.COMPLETED_WITH_FAILURES
    if completed or pruned:
        return SweepRunStatus.COMPLETED
    if failed:
        return SweepRunStatus.FAILED
    return SweepRunStatus.PLANNED


def _derive_sweep_status(summary: SweepSummary) -> SweepRunStatus:
    successful = summary.successful_slices
    failed = summary.failed_slices
    if successful and failed:
        return SweepRunStatus.COMPLETED_WITH_FAILURES
    if successful or summary.pruned_slices:
        return SweepRunStatus.COMPLETED
    return SweepRunStatus.FAILED


def _build_tranche_metrics(slice_records: list[SliceExecutionRecord]) -> dict[str, ScalarValue]:
    successful = len(
        [record for record in slice_records if record.status == SliceRunStatus.COMPLETED]
    )
    failed = len([record for record in slice_records if record.status == SliceRunStatus.FAILED])
    pruned = len([record for record in slice_records if record.status == SliceRunStatus.PRUNED])
    return {
        "successful_slices": successful,
        "failed_slices": failed,
        "pruned_slices": pruned,
    }


def _build_sweep_metrics(summary: SweepSummary) -> dict[str, ScalarValue]:
    top_candidate = summary.aggregate_rankings[0] if summary.aggregate_rankings else None
    return {
        "successful_slices": summary.successful_slices,
        "failed_slices": summary.failed_slices,
        "pruned_slices": summary.pruned_slices,
        "top_robust_candidate": top_candidate.genome_id if top_candidate else None,
        "top_robustness_score": top_candidate.robustness_score if top_candidate else None,
        "governance_recommendation": summary.adjudication.recommendation.value,
        "governance_sufficiency_passes": summary.sufficiency.passes,
        "weakest_unresolved_edge_count": len(summary.adjudication.weakest_unresolved_edges),
        "discriminator_history_count": len(summary.adjudication.discriminator_history),
        "promotion_blocked": summary.adjudication.promotion_blocked,
        "promotion_block_reason": summary.adjudication.promotion_block_reason,
        "discriminator_stop_reason": (
            summary.adjudication.discriminator_stop_reason.value
            if summary.adjudication.discriminator_stop_reason is not None
            else None
        ),
    }


def _apply_tranche_summaries(manifest: SweepManifest, summary: SweepSummary) -> None:
    summary_by_tranche = {tranche.tranche_id: tranche for tranche in summary.tranches}
    for tranche_record in manifest.tranches:
        tranche_summary = summary_by_tranche[tranche_record.tranche_id]
        tranche_record.metrics_summary.update(
            {
                "winner_consistency_ratio": (
                    tranche_summary.winner_consistency.winner_consistency_ratio
                ),
                "dominant_candidate_id": tranche_summary.winner_consistency.dominant_candidate_id,
                "successful_slices": tranche_summary.successful_slices,
                "failed_slices": tranche_summary.failed_slices,
                "pruned_slices": tranche_summary.pruned_slices,
                "governance_recommendation": (
                    tranche_summary.adjudication.recommendation.value
                    if tranche_summary.adjudication is not None
                    else None
                ),
                "weakest_unresolved_edge_count": (
                    len(tranche_summary.adjudication.weakest_unresolved_edges)
                    if tranche_summary.adjudication is not None
                    else None
                ),
                "discriminator_history_count": (
                    len(tranche_summary.adjudication.discriminator_history)
                    if tranche_summary.adjudication is not None
                    else None
                ),
                "promotion_blocked": (
                    tranche_summary.adjudication.promotion_blocked
                    if tranche_summary.adjudication is not None
                    else None
                ),
                "promotion_block_reason": (
                    tranche_summary.adjudication.promotion_block_reason
                    if tranche_summary.adjudication is not None
                    else None
                ),
                "discriminator_stop_reason": (
                    tranche_summary.adjudication.discriminator_stop_reason.value
                    if tranche_summary.adjudication is not None
                    and tranche_summary.adjudication.discriminator_stop_reason is not None
                    else None
                ),
            }
        )


def _persist_manifest(manifest: SweepManifest) -> None:
    write_json(Path(manifest.output_root) / "sweep_manifest.json", manifest.model_dump(mode="json"))
