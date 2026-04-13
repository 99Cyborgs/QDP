from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations
from statistics import mean, pstdev

from ..models import HypothesisClass, NullDominanceClassification, ScoreResult
from ..scoring import clamp, equivalence_margin as compute_equivalence_margin
from .models import (
    AdjudicationEvidence,
    AdjudicationGuardrail,
    AdjudicationGuardrailCode,
    AdaptiveAuditSummary,
    AdaptiveDecisionType,
    CandidateAggregate,
    DegeneracyCluster,
    DiscriminatorHistoryEntry,
    EquivalenceEdge,
    EquivalenceGraph,
    EquivalenceCluster,
    EquivalenceFingerprint,
    GovernanceRecommendation,
    HypothesisAdjudication,
    IdentifiabilitySummary,
    MechanismSeparationEntry,
    NullModelSummary,
    NullModelWinLossSummary,
    NullModelWinRateEntry,
    ResidualStructureSummary,
    ScalingConsistencyEntry,
    ScalingSummary,
    SweepAdjudication,
    SliceComparison,
    SliceExecutionRecord,
    SliceRunStatus,
    SliceWinner,
    SweepManifest,
    SweepSummary,
    TopSliceSummary,
    TrancheAdjudication,
    TrancheOutcome,
    TrancheSummary,
    TrancheType,
    TrancheWinnerConsistency,
    UnstableRegionSummary,
    UtilityDistributionSummary,
)


@dataclass(slots=True)
class CandidateObservation:
    tranche_id: str
    slice_id: str
    rank: int
    score: float
    parent_structure_id: str
    candidate_count: int


def build_sweep_summary(
    manifest: SweepManifest,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
) -> SweepSummary:
    """Aggregate completed slice runs into tranche-level and sweep-level summaries."""

    tranche_summaries = [
        build_tranche_summary(manifest, tranche_record.tranche_id, slice_results)
        for tranche_record in manifest.tranches
    ]
    overall_successful_slices = sum(summary.successful_slices for summary in tranche_summaries)
    overall_failed_slices = sum(summary.failed_slices for summary in tranche_summaries)
    overall_pruned_slices = sum(summary.pruned_slices for summary in tranche_summaries)
    all_slice_records = [
        record for tranche in manifest.tranches for record in tranche.slice_statuses
    ]

    aggregate_rankings = _aggregate_candidates(
        slice_results=slice_results,
        successful_slice_count=overall_successful_slices,
        top_k=_overall_top_k(manifest),
    )
    per_slice_winners = [
        winner for summary in tranche_summaries for winner in summary.slice_winners
    ]
    cross_slice_comparisons = _build_slice_comparisons(
        slice_results=slice_results,
        top_k=_overall_top_k(manifest),
        tranche_id=None,
    )

    consistent_top_performers = [
        aggregate.genome_id
        for aggregate in aggregate_rankings[:5]
        if aggregate.robustness_score >= 0.6
    ]
    profile_sensitive_candidates = [
        aggregate.genome_id
        for aggregate in sorted(
            aggregate_rankings,
            key=lambda item: (-item.profile_sensitivity_score, item.mean_rank),
        )[:5]
        if aggregate.profile_sensitivity_score >= 0.35
    ]
    adjudication = _build_sweep_adjudication(manifest, tranche_summaries, slice_results)
    weakest_edges = sorted(
        adjudication.equivalence_graph.edges,
        key=lambda edge: (edge.equivalence_margin, edge.edge_id),
    )[:10]
    discriminator_history = _discriminator_history(manifest, tranche_summaries)

    return SweepSummary(
        sweep_id=manifest.sweep_id,
        sweep_name=manifest.sweep_name,
        generated_at=datetime.now(UTC),
        successful_slices=overall_successful_slices,
        failed_slices=overall_failed_slices,
        pruned_slices=overall_pruned_slices,
        aggregate_rankings=aggregate_rankings,
        per_slice_winners=per_slice_winners,
        cross_slice_comparisons=cross_slice_comparisons,
        tranches=tranche_summaries,
        adaptive_audit=_adaptive_audit_summary(
            manifest,
            slice_records=all_slice_records,
            tranche_id=None,
        ),
        residual_structure_summary=_residual_structure_summary(all_slice_records),
        null_model_summary=_null_model_summary(all_slice_records),
        identifiability_summary=_identifiability_summary(all_slice_records),
        scaling_summary=_scaling_summary(all_slice_records),
        top_slices=_top_slices(all_slice_records),
        utility_distribution=_utility_distribution(all_slice_records),
        null_model_win_loss=_null_model_win_loss(all_slice_records),
        unstable_regions=_unstable_regions(all_slice_records),
        mechanism_separation_matrix=_mechanism_separation_matrix(
            manifest=manifest,
            slice_results=slice_results,
        ),
        scaling_consistency_map=_scaling_consistency_map(manifest, all_slice_records),
        null_model_win_rate_by_tranche_class=_null_model_win_rate_by_tranche_class(
            all_slice_records
        ),
        degeneracy_clusters=_degeneracy_clusters(all_slice_records),
        consistent_top_performers=consistent_top_performers,
        profile_sensitive_candidates=profile_sensitive_candidates,
        sufficiency=manifest.plan.sufficiency.model_copy(deep=True),
        adjudication=adjudication,
        equivalence_clusters=adjudication.equivalence_clusters,
        weakest_edges=weakest_edges,
        discriminator_history=discriminator_history,
        summary_highlights=_build_summary_highlights(
            aggregate_rankings=aggregate_rankings,
            successful_slices=overall_successful_slices,
            failed_slices=overall_failed_slices,
            pruned_slices=overall_pruned_slices,
        ),
    )


def build_tranche_summary(
    manifest: SweepManifest,
    tranche_id: str,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
) -> TrancheSummary:
    tranche_plan = next(
        tranche for tranche in manifest.plan.tranches if tranche.tranche_id == tranche_id
    )
    tranche_record = next(
        tranche for tranche in manifest.tranches if tranche.tranche_id == tranche_id
    )
    successful_slice_records = [
        record
        for record in tranche_record.slice_statuses
        if record.status == SliceRunStatus.COMPLETED
    ]
    successful_slice_count = len(successful_slice_records)
    failed_slice_count = len(
        [
            record
            for record in tranche_record.slice_statuses
            if record.status == SliceRunStatus.FAILED
        ]
    )
    pruned_slice_count = len(
        [
            record
            for record in tranche_record.slice_statuses
            if record.status == SliceRunStatus.PRUNED
        ]
    )

    slice_winners = [
        _slice_winner(
            tranche_plan.tranche_id,
            slice_plan.slice_id,
            slice_plan.resolved_profile,
            record,
            slice_results,
        )
        for slice_plan, record in zip(
            tranche_plan.slices, tranche_record.slice_statuses, strict=True
        )
    ]
    candidate_leaderboard = _aggregate_candidates(
        slice_results={key: value for key, value in slice_results.items() if key[0] == tranche_id},
        successful_slice_count=successful_slice_count,
        top_k=tranche_plan.comparison_strategy.top_k,
    )
    overlap_matrix = _build_slice_comparisons(
        slice_results=slice_results,
        top_k=tranche_plan.comparison_strategy.top_k,
        tranche_id=tranche_id,
    )
    consistent_top_performers = [
        aggregate.genome_id
        for aggregate in candidate_leaderboard[:5]
        if aggregate.robustness_score >= 0.6
    ]
    profile_sensitive_candidates = [
        aggregate.genome_id
        for aggregate in sorted(
            candidate_leaderboard,
            key=lambda item: (-item.profile_sensitivity_score, item.mean_rank),
        )[:5]
        if aggregate.profile_sensitivity_score >= 0.35
    ]

    dominant_candidate_id, dominant_win_count = _dominant_winner(slice_winners)
    winner_consistency_ratio = (
        dominant_win_count / successful_slice_count if successful_slice_count else 0.0
    )
    adjudication = _build_tranche_adjudication(
        manifest=manifest,
        tranche_plan=tranche_plan,
        tranche_record=tranche_record,
        slice_winners=slice_winners,
        successful_slice_records=successful_slice_records,
        winner_consistency_ratio=winner_consistency_ratio,
    )

    return TrancheSummary(
        sweep_id=manifest.sweep_id,
        tranche_id=tranche_id,
        objective=tranche_plan.objective,
        status=tranche_record.status,
        successful_slices=successful_slice_count,
        failed_slices=failed_slice_count,
        pruned_slices=pruned_slice_count,
        slice_records=tranche_record.slice_statuses,
        slice_winners=slice_winners,
        candidate_leaderboard=candidate_leaderboard,
        overlap_matrix=overlap_matrix,
        winner_consistency=TrancheWinnerConsistency(
            dominant_candidate_id=dominant_candidate_id,
            dominant_win_count=dominant_win_count,
            successful_slice_count=successful_slice_count,
            winner_consistency_ratio=winner_consistency_ratio,
        ),
        adaptive_audit=_adaptive_audit_summary(
            manifest,
            slice_records=tranche_record.slice_statuses,
            tranche_id=tranche_id,
        ),
        residual_structure_summary=_residual_structure_summary(tranche_record.slice_statuses),
        null_model_summary=_null_model_summary(tranche_record.slice_statuses),
        identifiability_summary=_identifiability_summary(tranche_record.slice_statuses),
        scaling_summary=_scaling_summary(tranche_record.slice_statuses),
        top_slices=_top_slices(tranche_record.slice_statuses),
        utility_distribution=_utility_distribution(tranche_record.slice_statuses),
        null_model_win_loss=_null_model_win_loss(tranche_record.slice_statuses),
        unstable_regions=_unstable_regions(tranche_record.slice_statuses),
        mechanism_separation_matrix=_mechanism_separation_matrix(
            manifest=manifest,
            slice_results={key: value for key, value in slice_results.items() if key[0] == tranche_id},
        ),
        scaling_consistency_map=_scaling_consistency_map(manifest, tranche_record.slice_statuses),
        null_model_win_rate_by_tranche_class=_null_model_win_rate_by_tranche_class(
            tranche_record.slice_statuses
        ),
        degeneracy_clusters=_degeneracy_clusters(tranche_record.slice_statuses),
        consistent_top_performers=consistent_top_performers,
        profile_sensitive_candidates=profile_sensitive_candidates,
        adjudication=adjudication,
        artifact_paths=tranche_record.artifact_paths,
    )


def _build_tranche_adjudication(
    *,
    manifest: SweepManifest,
    tranche_plan,
    tranche_record,
    slice_winners: list[SliceWinner],
    successful_slice_records: list[SliceExecutionRecord],
    winner_consistency_ratio: float,
) -> TrancheAdjudication:
    outcomes: set[TrancheOutcome] = set()
    evidence: list[AdjudicationEvidence] = []
    guardrails: list[AdjudicationGuardrail] = []
    dominant_candidate_id, _ = _dominant_winner(slice_winners)

    mean_null_equivalence = _mean_component(
        successful_slice_records,
        lambda record: record.utility.utility_components.null_equivalence_score,
    )
    mean_failure_match = _mean_component(
        successful_slice_records,
        lambda record: record.utility.utility_components.failure_mode_match_score,
    )
    mean_scaling_separation = _mean_component(
        successful_slice_records,
        lambda record: record.utility.utility_components.scaling_separation_score,
    )
    mean_identifiability = _mean_component(
        successful_slice_records,
        lambda record: record.utility.identifiability_score,
    )
    mean_measurement_equivalence = _mean_component(
        successful_slice_records,
        lambda record: record.utility.utility_components.measurement_equivalence_score,
    )
    mean_equivalence_margin = _mean_component(
        successful_slice_records,
        lambda record: record.utility.equivalence_margin,
    )
    mean_utility = _mean_component(
        successful_slice_records,
        lambda record: record.utility.utility_score,
    )
    mean_measurement_gap = _mean_component(
        successful_slice_records,
        lambda record: record.utility.trace.measurement_signal_gap,
    )
    if manifest is None:
        measurement_floor = 0.01
        equivalence_threshold = 0.80
        discriminator_coverage = 0
    else:
        measurement_floor = _effective_measurement_resolution(manifest.measurement, "__default__")
        equivalence_threshold = manifest.measurement.equivalence_threshold
        discriminator_coverage = sum(
            1
            for tranche in manifest.plan.tranches
            if tranche.discriminator_tranche is not None
            and tranche_plan.tranche_id in tranche.discriminator_tranche.target_hypothesis_pair
        )
    null_losses = sum(
        record.null_model_comparison.dominance_classification
        == NullDominanceClassification.DOMINATED_BY_NULL
        for record in successful_slice_records
    )
    identifiability_failures = sum(
        not record.utility.identifiability.is_identifiable for record in successful_slice_records
    )
    scaling_mismatches = sum(
        record.utility.scaling_validation.expected_scaling_type != record.utility.scaling_validation.observed_scaling_type
        and record.utility.scaling_validation.expected_scaling_type.value != "unknown"
        for record in successful_slice_records
    )

    evidence.extend(
        [
            AdjudicationEvidence(
                metric="winner_consistency_ratio",
                source=f"tranche:{tranche_plan.tranche_id}",
                value=winner_consistency_ratio,
            ),
            AdjudicationEvidence(
                metric="mean_null_equivalence_score",
                source=f"tranche:{tranche_plan.tranche_id}",
                value=mean_null_equivalence,
            ),
            AdjudicationEvidence(
                metric="mean_failure_mode_match_score",
                source=f"tranche:{tranche_plan.tranche_id}",
                value=mean_failure_match,
            ),
            AdjudicationEvidence(
                metric="mean_scaling_separation_score",
                source=f"tranche:{tranche_plan.tranche_id}",
                value=mean_scaling_separation,
            ),
            AdjudicationEvidence(
                metric="mean_identifiability_score",
                source=f"tranche:{tranche_plan.tranche_id}",
                value=mean_identifiability,
            ),
            AdjudicationEvidence(
                metric="mean_measurement_equivalence_score",
                source=f"tranche:{tranche_plan.tranche_id}",
                value=mean_measurement_equivalence,
            ),
            AdjudicationEvidence(
                metric="mean_equivalence_margin",
                source=f"tranche:{tranche_plan.tranche_id}",
                value=mean_equivalence_margin,
            ),
            AdjudicationEvidence(
                metric="mean_measurement_signal_gap",
                source=f"tranche:{tranche_plan.tranche_id}",
                value=mean_measurement_gap,
            ),
            AdjudicationEvidence(
                metric="successful_slice_count",
                source=f"tranche:{tranche_plan.tranche_id}",
                value=len(successful_slice_records),
            ),
        ]
    )

    if not successful_slice_records:
        outcomes.add(TrancheOutcome.INSUFFICIENT_EVIDENCE)
    if null_losses > 0:
        outcomes.add(TrancheOutcome.NULL_DOMINANT)
    if mean_null_equivalence >= 0.80:
        outcomes.add(TrancheOutcome.NULL_EQUIVALENT)
    if mean_equivalence_margin < 1.0:
        outcomes.add(TrancheOutcome.INDETERMINATE_EQUIVALENCE)
        outcomes.add(TrancheOutcome.EQUIVALENCE_UNBROKEN)
    if mean_equivalence_margin < 1.0 and mean_measurement_gap < measurement_floor:
        outcomes.add(TrancheOutcome.INSTRUMENT_LIMITED)
    if scaling_mismatches > 0 and mean_scaling_separation < 0.55:
        outcomes.add(TrancheOutcome.SCALING_INCONSISTENT)
    if tranche_plan.tranche_type == TrancheType.FAILURE_MODE_TRANCHE and mean_failure_match >= 0.70:
        outcomes.add(TrancheOutcome.FAILURE_MODE_MATCHED)
    if tranche_plan.tranche_type == TrancheType.CROSS_DEVICE_TRANCHE and winner_consistency_ratio < 0.60:
        outcomes.add(TrancheOutcome.CROSS_DEVICE_UNSTABLE)
    if tranche_plan.tranche_type == TrancheType.BOUNDARY_STRESS_TRANCHE and any(
        record.utility.utility_score < 0.50 for record in successful_slice_records
    ):
        outcomes.add(TrancheOutcome.BOUNDARY_FRAGILE)
    if (
        tranche_plan.tranche_type == TrancheType.DISCRIMINATION_TRANCHE
        and winner_consistency_ratio >= 0.60
        and null_losses == 0
        and identifiability_failures == 0
    ):
        outcomes.add(TrancheOutcome.DISCRIMINATED)

    if mean_scaling_separation >= 0.70 and all(
        record.utility.scaling_validation.scaling_axis is None for record in successful_slice_records
    ):
        guardrails.append(
            AdjudicationGuardrail(
                code=AdjudicationGuardrailCode.SCALING_LAYOUT_INFLATION,
                message="Scaling separation was high without any resolved scaling axis evidence.",
                source=f"tranche:{tranche_plan.tranche_id}",
                blocked_recommendation=GovernanceRecommendation.PROCEED_TO_REFINEMENT,
            )
        )
        outcomes.add(TrancheOutcome.INSUFFICIENT_EVIDENCE)
    if mean_utility >= 0.70 and discriminator_coverage == 0:
        guardrails.append(
            AdjudicationGuardrail(
                code=AdjudicationGuardrailCode.DISCRIMINATOR_COVERAGE_GAP,
                message="High utility was observed without any adversarial discriminator coverage.",
                source=f"tranche:{tranche_plan.tranche_id}",
                blocked_recommendation=GovernanceRecommendation.PROCEED_TO_REFINEMENT,
            )
        )
        outcomes.add(TrancheOutcome.INSUFFICIENT_EVIDENCE)
    if mean_equivalence_margin < 1.0 and mean_measurement_gap < measurement_floor:
        guardrails.append(
            AdjudicationGuardrail(
                code=AdjudicationGuardrailCode.BELOW_MEASUREMENT_RESOLUTION,
                message="Predicted separation remained below the configured measurement floor.",
                source=f"tranche:{tranche_plan.tranche_id}",
                blocked_recommendation=GovernanceRecommendation.PROCEED_TO_REFINEMENT,
            )
        )
        outcomes.add(TrancheOutcome.INDETERMINATE_EQUIVALENCE)
    if tranche_plan.failure_modes and mean_failure_match >= 0.70 and (
        len(tranche_plan.failure_modes) < 2 or len(successful_slice_records) < 2
    ):
        guardrails.append(
            AdjudicationGuardrail(
                code=AdjudicationGuardrailCode.FAILURE_MODE_CONGENIAL_OPPOSITION,
                message="Failure-mode match was high under weak opposition coverage.",
                source=f"tranche:{tranche_plan.tranche_id}",
                blocked_recommendation=GovernanceRecommendation.REJECT_BY_FAILURE_MODE_MATCH,
            )
        )
        outcomes.add(TrancheOutcome.INSUFFICIENT_EVIDENCE)
    if mean_null_equivalence >= 0.75 and (
        sum(record.null_model_comparison.available for record in successful_slice_records)
        < max(1, len(successful_slice_records))
    ):
        guardrails.append(
            AdjudicationGuardrail(
                code=AdjudicationGuardrailCode.NULL_EQUIVALENCE_UNDERCOVERED,
                message="Null equivalence was high under insufficient null-model coverage.",
                source=f"tranche:{tranche_plan.tranche_id}",
                blocked_recommendation=GovernanceRecommendation.SANDBOX_ONLY,
            )
        )
        outcomes.add(TrancheOutcome.INSUFFICIENT_EVIDENCE)
    if (
        tranche_plan.tranche_type == TrancheType.DISCRIMINATOR_TRANCHE
        and mean_equivalence_margin < 1.0
    ):
        guardrails.append(
            AdjudicationGuardrail(
                code=AdjudicationGuardrailCode.EQUIVALENCE_PERSISTS,
                message="Equivalence persisted across discriminator tranches.",
                source=f"tranche:{tranche_plan.tranche_id}",
                blocked_recommendation=GovernanceRecommendation.PROCEED_TO_REFINEMENT,
            )
        )
        outcomes.add(TrancheOutcome.INDETERMINATE_EQUIVALENCE)
        outcomes.add(TrancheOutcome.DISCRIMINATOR_EXHAUSTED)

    fingerprint = EquivalenceFingerprint(
        fingerprint_id=_fingerprint_id(
            tranche_plan.tranche_id,
            dominant_candidate_id,
            winner_consistency_ratio,
            mean_null_equivalence,
            mean_failure_match,
            mean_scaling_separation,
            mean_identifiability,
            mean_measurement_equivalence,
            mean_equivalence_margin,
            mean_utility,
            null_losses,
            scaling_mismatches,
            identifiability_failures,
        ),
        dominant_candidate_id=dominant_candidate_id,
        winner_consistency_ratio=round(winner_consistency_ratio, 3),
        mean_null_equivalence_score=round(mean_null_equivalence, 3),
        mean_failure_mode_match_score=round(mean_failure_match, 3),
        mean_scaling_separation_score=round(mean_scaling_separation, 3),
        mean_identifiability_score=round(mean_identifiability, 3),
        mean_measurement_equivalence_score=round(mean_measurement_equivalence, 3),
        mean_equivalence_margin=round(mean_equivalence_margin, 3),
        mean_utility_score=round(mean_utility, 3),
        null_dominance_losses=null_losses,
        scaling_mismatches=scaling_mismatches,
        identifiability_failures=identifiability_failures,
    )
    recommendation = _recommendation_for_outcomes(outcomes, guardrails)
    return TrancheAdjudication(
        tranche_id=tranche_plan.tranche_id,
        hypothesis_class=tranche_plan.hypothesis_class,
        outcomes=sorted(outcomes, key=lambda value: value.value),
        recommendation=recommendation,
        evidence=evidence,
        guardrails=guardrails,
        fingerprint=fingerprint,
        measurement_config=manifest.measurement.model_copy(deep=True) if manifest is not None else None,
        measurement_config_provenance="manifest.measurement" if manifest is not None else None,
        discriminator_stop_reason=_discriminator_stop_reason(outcomes),
        promotion_blocked=_promotion_blocked(recommendation),
        promotion_block_reason=_promotion_block_reason(recommendation, outcomes, guardrails),
    )


def _build_sweep_adjudication(
    manifest: SweepManifest,
    tranche_summaries: list[TrancheSummary],
    slice_results: dict[tuple[str, str], list[ScoreResult]],
) -> SweepAdjudication:
    discriminator_history = _discriminator_history(manifest, tranche_summaries)
    tranche_adjudications = [
        summary.adjudication
        for summary in tranche_summaries
        if summary.adjudication is not None
    ]
    equivalence_graph = _build_equivalence_graph(manifest, discriminator_history)
    equivalence_clusters = _equivalence_clusters_from_graph(
        manifest,
        equivalence_graph,
        tranche_adjudications,
    )
    equivalent_by_tranche = {
        tranche_id: set()
        for tranche_id in [adjudication.tranche_id for adjudication in tranche_adjudications]
    }
    for cluster in equivalence_clusters:
        for tranche_id in cluster.tranche_ids:
            equivalent_by_tranche.setdefault(tranche_id, set()).update(
                candidate for candidate in cluster.tranche_ids if candidate != tranche_id
            )
    for adjudication in tranche_adjudications:
        adjudication.equivalent_to_tranche_ids = sorted(
            equivalent_by_tranche.get(adjudication.tranche_id, set())
        )
        if adjudication.equivalent_to_tranche_ids and len(
            {
                cluster_class
                for cluster in equivalence_clusters
                if adjudication.tranche_id in cluster.tranche_ids
                for cluster_class in cluster.hypothesis_classes
            }
        ) > 1:
            if TrancheOutcome.INDETERMINATE_EQUIVALENCE not in adjudication.outcomes:
                adjudication.outcomes.append(TrancheOutcome.INDETERMINATE_EQUIVALENCE)
            adjudication.recommendation = GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY
        adjudication.weakest_unresolved_edges = _weakest_edges_for_tranche(
            equivalence_graph,
            adjudication.tranche_id,
        )
        adjudication.discriminator_history = [
            entry
            for entry in discriminator_history
            if adjudication.tranche_id in entry.target_hypothesis_pair
            or adjudication.tranche_id == entry.tranche_id
        ]
        adjudication.measurement_config = manifest.measurement.model_copy(deep=True)
        adjudication.measurement_config_provenance = "manifest.measurement"
        adjudication.discriminator_stop_reason = _discriminator_stop_reason(
            set(adjudication.outcomes)
        )
        adjudication.promotion_blocked = _promotion_blocked(adjudication.recommendation)
        adjudication.promotion_block_reason = _promotion_block_reason(
            adjudication.recommendation,
            set(adjudication.outcomes),
            adjudication.guardrails,
        )

    hypothesis_adjudications = _hypothesis_adjudications(tranche_adjudications, equivalence_clusters)
    recommendation = _sweep_recommendation(hypothesis_adjudications)
    return SweepAdjudication(
        recommendation=recommendation,
        tranche_adjudications=tranche_adjudications,
        hypothesis_adjudications=hypothesis_adjudications,
        equivalence_clusters=equivalence_clusters,
        equivalence_graph=equivalence_graph,
        weakest_unresolved_edges=sorted(
            equivalence_graph.edges,
            key=lambda edge: (edge.equivalence_margin, edge.edge_id),
        )[:10],
        discriminator_history=discriminator_history,
        measurement_config=manifest.measurement.model_copy(deep=True),
        measurement_config_provenance="manifest.measurement",
        discriminator_stop_reason=_discriminator_stop_reason(
            {outcome for adjudication in tranche_adjudications for outcome in adjudication.outcomes}
        ),
        promotion_blocked=_promotion_blocked(recommendation),
        promotion_block_reason=_promotion_block_reason(
            recommendation,
            {
                outcome
                for adjudication in tranche_adjudications
                for outcome in adjudication.outcomes
            },
            [guardrail for adjudication in tranche_adjudications for guardrail in adjudication.guardrails],
        ),
    )


def _build_equivalence_graph(
    manifest: SweepManifest,
    discriminator_history: list[DiscriminatorHistoryEntry] | None = None,
) -> EquivalenceGraph:
    discriminator_history = discriminator_history or []
    tranche_lookup = {tranche.tranche_id: tranche for tranche in manifest.plan.tranches}
    completed_records = [
        record
        for tranche in manifest.tranches
        for record in tranche.slice_statuses
        if record.status == SliceRunStatus.COMPLETED
        and record.hypothesis_class not in {HypothesisClass.LEGACY, HypothesisClass.NULL_DOMINANCE}
    ]
    nodes = [f"{record.tranche_id}:{record.slice_id}" for record in completed_records]
    edges: list[EquivalenceEdge] = []
    for left_record, right_record in combinations(
        sorted(completed_records, key=lambda record: (record.tranche_id, record.slice_id)),
        2,
    ):
        if left_record.tranche_id == right_record.tranche_id:
            continue
        metric_differences = {
            "null_equivalence_score": abs(
                left_record.utility.utility_components.null_equivalence_score
                - right_record.utility.utility_components.null_equivalence_score
            ),
            "scaling_separation_score": abs(
                left_record.utility.utility_components.scaling_separation_score
                - right_record.utility.utility_components.scaling_separation_score
            ),
            "identifiability_score": abs(
                left_record.utility.identifiability_score - right_record.utility.identifiability_score
            ),
            "utility_score": abs(left_record.utility.utility_score - right_record.utility.utility_score),
            "equivalence_margin": abs(
                left_record.utility.equivalence_margin - right_record.utility.equivalence_margin
            ),
        }
        margin = max(
            difference / _effective_measurement_resolution(manifest.measurement, metric_name)
            for metric_name, difference in metric_differences.items()
        )
        if margin >= 1.0:
            continue
        left_tranche = tranche_lookup[left_record.tranche_id]
        right_tranche = tranche_lookup[right_record.tranche_id]
        edges.append(
            EquivalenceEdge(
                edge_id=(
                    f"{left_record.tranche_id}:{left_record.slice_id}__"
                    f"{right_record.tranche_id}:{right_record.slice_id}"
                ),
                left_tranche_id=left_record.tranche_id,
                left_slice_id=left_record.slice_id,
                right_tranche_id=right_record.tranche_id,
                right_slice_id=right_record.slice_id,
                left_hypothesis_class=left_tranche.hypothesis_class,
                right_hypothesis_class=right_tranche.hypothesis_class,
                equivalence_margin=margin,
                measurement_equivalence_score=_legacy_measurement_equivalence_score(margin),
                tested_axes=_tested_axes_for_edge(
                    left_tranche_id=left_record.tranche_id,
                    right_tranche_id=right_record.tranche_id,
                    discriminator_history=discriminator_history,
                ),
            )
        )
    return EquivalenceGraph(
        nodes=sorted(nodes),
        edges=sorted(edges, key=lambda edge: (edge.equivalence_margin, edge.edge_id)),
    )


def _equivalence_clusters_from_graph(
    manifest: SweepManifest,
    equivalence_graph: EquivalenceGraph,
    tranche_adjudications: list[TrancheAdjudication],
) -> list[EquivalenceCluster]:
    tranche_lookup = {tranche.tranche_id: tranche for tranche in manifest.plan.tranches}
    adjacency: dict[str, set[str]] = {node: set() for node in equivalence_graph.nodes}
    edge_by_pair: dict[frozenset[str], EquivalenceEdge] = {}
    for edge in equivalence_graph.edges:
        left_node = f"{edge.left_tranche_id}:{edge.left_slice_id}"
        right_node = f"{edge.right_tranche_id}:{edge.right_slice_id}"
        adjacency.setdefault(left_node, set()).add(right_node)
        adjacency.setdefault(right_node, set()).add(left_node)
        edge_by_pair[frozenset({left_node, right_node})] = edge
    clusters: list[EquivalenceCluster] = []
    visited: set[str] = set()
    for node in sorted(adjacency):
        if node in visited or not adjacency[node]:
            continue
        stack = [node]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(sorted(adjacency.get(current, set()) - visited))
        if len(component) < 2:
            continue
        component_edges = [
            edge_by_pair[frozenset({left_node, right_node})]
            for left_node, right_node in combinations(sorted(component), 2)
            if frozenset({left_node, right_node}) in edge_by_pair
        ]
        if not component_edges:
            continue
        tranche_ids = sorted({node_id.split(":", 1)[0] for node_id in component})
        hypothesis_classes = sorted(
            {tranche_lookup[tranche_id].hypothesis_class for tranche_id in tranche_ids},
            key=lambda value: value.value,
        )
        clusters.append(
            EquivalenceCluster(
                cluster_id=f"equivalence_{len(clusters) + 1}",
                tranche_ids=tranche_ids,
                slice_ids=sorted(node_id.split(":", 1)[1] for node_id in component),
                hypothesis_classes=hypothesis_classes,
                fingerprint_ids=[
                    adjudication.fingerprint.fingerprint_id
                    for adjudication in tranche_adjudications
                    if adjudication.fingerprint is not None
                    and adjudication.tranche_id in tranche_ids
                ],
                reason="measurement_indistinguishable",
                similarity_score=mean(
                    _legacy_measurement_equivalence_score(edge.equivalence_margin)
                    for edge in component_edges
                ),
                measurement_equivalence_score=mean(
                    edge.measurement_equivalence_score for edge in component_edges
                ),
                equivalence_margin=mean(edge.equivalence_margin for edge in component_edges),
            )
        )
    return clusters


def _equivalence_clusters(
    tranche_adjudications: list[TrancheAdjudication],
    *,
    noise_floor: float = 0.01,
    sampling_bandwidth: float = 1.0,
    observable_resolution: float = 0.01,
    threshold: float = 0.80,
) -> list[EquivalenceCluster]:
    members = [adjudication for adjudication in tranche_adjudications if adjudication.fingerprint is not None]
    adjacency: dict[str, set[str]] = {member.tranche_id: set() for member in members}
    score_by_pair: dict[tuple[str, str], float] = {}
    by_id = {member.tranche_id: member for member in members}
    for left, right in combinations(sorted(members, key=lambda item: item.tranche_id), 2):
        left_fp = left.fingerprint
        right_fp = right.fingerprint
        assert left_fp is not None and right_fp is not None
        score = _fingerprint_measurement_equivalence(
            left_fp,
            right_fp,
            noise_floor=noise_floor,
            sampling_bandwidth=sampling_bandwidth,
            observable_resolution=observable_resolution,
        )
        if left_fp.dominant_candidate_id != right_fp.dominant_candidate_id:
            continue
        if score < threshold:
            continue
        adjacency[left.tranche_id].add(right.tranche_id)
        adjacency[right.tranche_id].add(left.tranche_id)
        score_by_pair[(left.tranche_id, right.tranche_id)] = score
    clusters: list[EquivalenceCluster] = []
    visited: set[str] = set()
    for tranche_id in sorted(adjacency):
        if tranche_id in visited or not adjacency[tranche_id]:
            continue
        stack = [tranche_id]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(sorted(adjacency[current] - visited))
        group_members = [by_id[item] for item in sorted(component)]
        hypothesis_classes = sorted(
            {member.hypothesis_class for member in group_members},
            key=lambda value: value.value,
        )
        if len(group_members) < 2:
            continue
        pair_scores = [
            score_by_pair.get((left_id, right_id), score_by_pair.get((right_id, left_id), 1.0))
            for left_id, right_id in combinations(sorted(component), 2)
        ]
        clusters.append(
            EquivalenceCluster(
                cluster_id=f"equivalence_{len(clusters) + 1}",
                tranche_ids=sorted(member.tranche_id for member in group_members),
                hypothesis_classes=hypothesis_classes,
                fingerprint_ids=[
                    member.fingerprint.fingerprint_id
                    for member in group_members
                    if member.fingerprint is not None
                ],
                reason="measurement_indistinguishable",
                similarity_score=mean(pair_scores) if pair_scores else 1.0,
                measurement_equivalence_score=mean(pair_scores) if pair_scores else 1.0,
            )
        )
    return clusters


def _hypothesis_adjudications(
    tranche_adjudications: list[TrancheAdjudication],
    equivalence_clusters: list[EquivalenceCluster],
) -> list[HypothesisAdjudication]:
    grouped: dict[HypothesisClass, list[TrancheAdjudication]] = {}
    for adjudication in tranche_adjudications:
        grouped.setdefault(adjudication.hypothesis_class, []).append(adjudication)
    hypothesis_adjudications: list[HypothesisAdjudication] = []
    for hypothesis_class, adjudications in sorted(grouped.items(), key=lambda item: item[0].value):
        outcomes = sorted(
            {outcome for adjudication in adjudications for outcome in adjudication.outcomes},
            key=lambda value: value.value,
        )
        evidence = [
            AdjudicationEvidence(
                metric="tranche_recommendations",
                source=f"hypothesis:{hypothesis_class.value}",
                value=",".join(sorted({adjudication.recommendation.value for adjudication in adjudications})),
            )
        ]
        equivalent_classes = sorted(
            {
                candidate
                for cluster in equivalence_clusters
                if any(adjudication.tranche_id in cluster.tranche_ids for adjudication in adjudications)
                for candidate in cluster.hypothesis_classes
                if candidate != hypothesis_class
            },
            key=lambda value: value.value,
        )
        recommendation = _recommendation_for_outcomes(set(outcomes), [])
        if equivalent_classes:
            recommendation = GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY
        stop_reason = _discriminator_stop_reason(set(outcomes))
        hypothesis_adjudications.append(
            HypothesisAdjudication(
                hypothesis_class=hypothesis_class,
                tranche_ids=sorted(adjudication.tranche_id for adjudication in adjudications),
                outcomes=outcomes,
                recommendation=recommendation,
                evidence=evidence,
                equivalent_to_hypothesis_classes=equivalent_classes,
                discriminator_stop_reason=stop_reason,
                promotion_blocked=_promotion_blocked(recommendation),
                promotion_block_reason=_promotion_block_reason(
                    recommendation,
                    set(outcomes),
                    [],
                ),
            )
        )
    return hypothesis_adjudications


def _sweep_recommendation(
    hypothesis_adjudications: list[HypothesisAdjudication],
) -> GovernanceRecommendation:
    recommendations = {adjudication.recommendation for adjudication in hypothesis_adjudications}
    if GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY in recommendations:
        return GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY
    if GovernanceRecommendation.REJECT_BY_NULL_DOMINANCE in recommendations:
        return GovernanceRecommendation.REJECT_BY_NULL_DOMINANCE
    if GovernanceRecommendation.REJECT_BY_FAILURE_MODE_MATCH in recommendations:
        return GovernanceRecommendation.REJECT_BY_FAILURE_MODE_MATCH
    if GovernanceRecommendation.REJECT_BY_SCALING_INCONSISTENCY in recommendations:
        return GovernanceRecommendation.REJECT_BY_SCALING_INCONSISTENCY
    if GovernanceRecommendation.DEFER_FOR_CROSS_DEVICE_VALIDATION in recommendations:
        return GovernanceRecommendation.DEFER_FOR_CROSS_DEVICE_VALIDATION
    if GovernanceRecommendation.REQUIRES_HIGHER_RESOLUTION in recommendations:
        return GovernanceRecommendation.REQUIRES_HIGHER_RESOLUTION
    if GovernanceRecommendation.INSTRUMENT_LIMITED in recommendations:
        return GovernanceRecommendation.INSTRUMENT_LIMITED
    if GovernanceRecommendation.INDETERMINATE_EQUIVALENCE in recommendations:
        return GovernanceRecommendation.INDETERMINATE_EQUIVALENCE
    if GovernanceRecommendation.SANDBOX_ONLY in recommendations:
        return GovernanceRecommendation.SANDBOX_ONLY
    if GovernanceRecommendation.PROCEED_TO_REFINEMENT in recommendations:
        return GovernanceRecommendation.PROCEED_TO_REFINEMENT
    return GovernanceRecommendation.DEFER_FOR_MORE_EVIDENCE


def _recommendation_for_outcomes(
    outcomes: set[TrancheOutcome],
    guardrails: list[AdjudicationGuardrail],
) -> GovernanceRecommendation:
    blocked = {guardrail.blocked_recommendation for guardrail in guardrails}
    if TrancheOutcome.NULL_DOMINANT in outcomes:
        return GovernanceRecommendation.REJECT_BY_NULL_DOMINANCE
    if TrancheOutcome.FAILURE_MODE_MATCHED in outcomes and GovernanceRecommendation.REJECT_BY_FAILURE_MODE_MATCH not in blocked:
        return GovernanceRecommendation.REJECT_BY_FAILURE_MODE_MATCH
    if TrancheOutcome.SCALING_INCONSISTENT in outcomes:
        return GovernanceRecommendation.REJECT_BY_SCALING_INCONSISTENCY
    if TrancheOutcome.CROSS_DEVICE_UNSTABLE in outcomes:
        return GovernanceRecommendation.DEFER_FOR_CROSS_DEVICE_VALIDATION
    if TrancheOutcome.INSTRUMENT_LIMITED in outcomes:
        return GovernanceRecommendation.INSTRUMENT_LIMITED
    if (
        TrancheOutcome.EQUIVALENCE_UNBROKEN in outcomes
        or TrancheOutcome.DISCRIMINATOR_EXHAUSTED in outcomes
    ):
        return GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY
    if any(guardrail.code == AdjudicationGuardrailCode.EQUIVALENCE_PERSISTS for guardrail in guardrails):
        return GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY
    if any(guardrail.code == AdjudicationGuardrailCode.BELOW_MEASUREMENT_RESOLUTION for guardrail in guardrails):
        return GovernanceRecommendation.REQUIRES_HIGHER_RESOLUTION
    if TrancheOutcome.INDETERMINATE_EQUIVALENCE in outcomes:
        return GovernanceRecommendation.INSTRUMENT_LIMITED if guardrails else GovernanceRecommendation.INDETERMINATE_EQUIVALENCE
    if TrancheOutcome.BOUNDARY_FRAGILE in outcomes:
        return GovernanceRecommendation.SANDBOX_ONLY
    if TrancheOutcome.DISCRIMINATED in outcomes and not guardrails:
        return GovernanceRecommendation.PROCEED_TO_REFINEMENT
    return GovernanceRecommendation.DEFER_FOR_MORE_EVIDENCE


def _fingerprint_measurement_equivalence(
    left: EquivalenceFingerprint,
    right: EquivalenceFingerprint,
    *,
    noise_floor: float,
    sampling_bandwidth: float,
    observable_resolution: float,
) -> float:
    margin = compute_equivalence_margin(
        [
            abs(left.mean_null_equivalence_score - right.mean_null_equivalence_score),
            abs(left.mean_failure_mode_match_score - right.mean_failure_mode_match_score),
            abs(left.mean_scaling_separation_score - right.mean_scaling_separation_score),
            abs(left.mean_identifiability_score - right.mean_identifiability_score),
            abs(left.mean_measurement_equivalence_score - right.mean_measurement_equivalence_score),
            abs(left.mean_equivalence_margin - right.mean_equivalence_margin),
            abs(left.mean_utility_score - right.mean_utility_score),
        ],
        noise_floor=noise_floor,
        sampling_bandwidth=sampling_bandwidth,
        observable_resolution=observable_resolution,
    )
    return _legacy_measurement_equivalence_score(margin)


def _effective_measurement_resolution(
    measurement,
    observable_name: str,
) -> float:
    envelope = measurement.measurement_envelope
    explicit = envelope.resolution_vector.get(
        observable_name,
        envelope.resolution_vector.get("__default__", measurement.observable_resolution),
    )
    noise_bound = max(
        measurement.noise_floor,
        envelope.noise_model.absolute_bound,
        explicit * envelope.noise_model.relative_bound,
    )
    bandwidth_penalty = noise_bound / max(envelope.bandwidth, 1.0)
    sampling_penalty = noise_bound / max(envelope.sampling_window, 1.0)
    return max(explicit, noise_bound + bandwidth_penalty + sampling_penalty)


def _legacy_measurement_equivalence_score(margin: float) -> float:
    return clamp(1.0 - margin)


def _discriminator_history(
    manifest: SweepManifest,
    tranche_summaries: list[TrancheSummary],
) -> list[DiscriminatorHistoryEntry]:
    outcome_by_tranche = {
        summary.tranche_id: (
            summary.adjudication.outcomes[0] if summary.adjudication and summary.adjudication.outcomes else None
        )
        for summary in tranche_summaries
    }
    history: list[DiscriminatorHistoryEntry] = []
    for tranche in sorted(manifest.plan.tranches, key=lambda item: item.tranche_id):
        fields = tranche.discriminator_tranche
        if fields is None:
            continue
        history.append(
            DiscriminatorHistoryEntry(
                tranche_id=tranche.tranche_id,
                generation=fields.generation,
                target_hypothesis_pair=list(fields.target_hypothesis_pair),
                discriminator_axis=fields.discriminator_axis,
                discriminator_gain=fields.discriminator_gain,
                axis_cost=fields.axis_cost,
                redundancy_penalty=fields.redundancy_penalty,
                predicted_separation=fields.predicted_separation,
                observed_separation=fields.observed_separation,
                outcome=outcome_by_tranche.get(tranche.tranche_id),
                originating_equivalence_cluster=fields.originating_equivalence_cluster,
                discriminator_rationale=fields.discriminator_rationale,
                tested_axes=list(fields.tested_axes),
                tested_discriminator_axes=list(fields.tested_discriminator_axes),
                rejected_axes=[item.model_copy(deep=True) for item in fields.rejected_axes],
                rejected_discriminator_axes=list(fields.rejected_discriminator_axes),
                rejected_axis_rationale=[
                    item.model_copy(deep=True) for item in fields.rejected_axis_rationale
                ],
                measurement_config=manifest.measurement.model_copy(deep=True),
                measurement_config_provenance="manifest.measurement",
                stop_reason=_discriminator_stop_reason(
                    {
                        outcome_by_tranche[tranche.tranche_id]
                    }
                    if outcome_by_tranche.get(tranche.tranche_id) is not None
                    else set()
                ),
            )
        )
    return history


def _tested_axes_for_edge(
    *,
    left_tranche_id: str,
    right_tranche_id: str,
    discriminator_history: list[DiscriminatorHistoryEntry],
) -> list[str]:
    tested_axes = {
        axis
        for entry in discriminator_history
        if tuple(sorted(entry.target_hypothesis_pair))
        == tuple(sorted([left_tranche_id, right_tranche_id]))
        for axis in ([entry.discriminator_axis] + list(entry.tested_axes))
    }
    return sorted(tested_axes) if tested_axes else ["observable_envelope"]


def _weakest_edges_for_tranche(
    equivalence_graph: EquivalenceGraph,
    tranche_id: str,
) -> list[EquivalenceEdge]:
    return [
        edge
        for edge in equivalence_graph.edges
        if tranche_id in {edge.left_tranche_id, edge.right_tranche_id}
    ][:10]


def _discriminator_stop_reason(outcomes: set[TrancheOutcome]) -> TrancheOutcome | None:
    for candidate in [
        TrancheOutcome.INSTRUMENT_LIMITED,
        TrancheOutcome.DISCRIMINATOR_EXHAUSTED,
        TrancheOutcome.EQUIVALENCE_UNBROKEN,
        TrancheOutcome.INDETERMINATE_EQUIVALENCE,
    ]:
        if candidate in outcomes:
            return candidate
    return None


def _promotion_blocked(recommendation: GovernanceRecommendation) -> bool:
    return recommendation != GovernanceRecommendation.PROCEED_TO_REFINEMENT


def _promotion_block_reason(
    recommendation: GovernanceRecommendation,
    outcomes: set[TrancheOutcome],
    guardrails: list[AdjudicationGuardrail],
) -> str | None:
    if recommendation == GovernanceRecommendation.PROCEED_TO_REFINEMENT:
        return None
    stop_reason = _discriminator_stop_reason(outcomes)
    if stop_reason is not None:
        return stop_reason.value
    if guardrails:
        return guardrails[0].code.value
    return recommendation.value


def _mean_component(
    records: list[SliceExecutionRecord],
    selector,
) -> float:
    values = [float(selector(record)) for record in records]
    return mean(values) if values else 0.0


def _fingerprint_id(*parts: object) -> str:
    joined = "::".join(str(part) for part in parts)
    return joined.replace(" ", "_")


def _slice_winner(
    tranche_id: str,
    slice_id: str,
    profile: str,
    record: SliceExecutionRecord,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
) -> SliceWinner:
    results = slice_results.get((tranche_id, slice_id), [])
    top_result = results[0] if results else None
    return SliceWinner(
        tranche_id=tranche_id,
        slice_id=slice_id,
        scoring_profile=profile,
        candidate_id=top_result.genome_id if top_result else None,
        parent_structure_id=top_result.parent_structure_id if top_result else None,
        score=top_result.score if top_result else None,
        decision_band=top_result.decision_band if top_result else None,
        candidate_count=record.candidate_count,
        status=record.status,
    )


def _aggregate_candidates(
    *,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
    successful_slice_count: int,
    top_k: int,
) -> list[CandidateAggregate]:
    observations: dict[str, list[CandidateObservation]] = {}

    for (tranche_id, slice_id), results in slice_results.items():
        candidate_count = len(results)
        for rank, result in enumerate(results, start=1):
            observations.setdefault(result.genome_id, []).append(
                CandidateObservation(
                    tranche_id=tranche_id,
                    slice_id=slice_id,
                    rank=rank,
                    score=result.score,
                    parent_structure_id=result.parent_structure_id,
                    candidate_count=candidate_count,
                )
            )

    aggregates: list[CandidateAggregate] = []
    for genome_id, values in observations.items():
        ranks = [value.rank for value in values]
        scores = [value.score for value in values]
        normalized_ranks = [
            1.0
            if value.candidate_count <= 1
            else 1.0 - ((value.rank - 1) / (value.candidate_count - 1))
            for value in values
        ]
        top_k_appearances = sum(value.rank <= top_k for value in values)
        win_count = sum(value.rank == 1 for value in values)
        appearance_rate = len(values) / successful_slice_count if successful_slice_count else 0.0
        top_k_rate = top_k_appearances / successful_slice_count if successful_slice_count else 0.0
        mean_normalized_rank = mean(normalized_ranks) if normalized_ranks else 0.0
        robustness_score = clamp(
            0.55 * mean_normalized_rank + 0.30 * appearance_rate + 0.15 * top_k_rate
        )
        score_stddev = pstdev(scores) if len(scores) > 1 else 0.0
        rank_span = max(ranks) - min(ranks)
        rank_span_norm = rank_span / max(max(ranks) - 1, 1) if len(ranks) > 1 else 0.0
        profile_sensitivity_score = clamp(0.65 * rank_span_norm + 0.35 * score_stddev / 0.25)

        aggregates.append(
            CandidateAggregate(
                genome_id=genome_id,
                parent_structure_id=values[0].parent_structure_id,
                slice_ids=sorted({value.slice_id for value in values}),
                tranche_ids=sorted({value.tranche_id for value in values}),
                successful_slice_count=len(values),
                top_k_appearances=top_k_appearances,
                win_count=win_count,
                mean_rank=mean(ranks),
                best_rank=min(ranks),
                worst_rank=max(ranks),
                rank_span=rank_span,
                mean_score=mean(scores),
                score_stddev=score_stddev,
                robustness_score=robustness_score,
                profile_sensitivity_score=profile_sensitivity_score,
            )
        )

    return sorted(
        aggregates,
        key=lambda item: (
            -item.robustness_score,
            item.mean_rank,
            -item.top_k_appearances,
            -item.mean_score,
        ),
    )


def _build_slice_comparisons(
    *,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
    top_k: int,
    tranche_id: str | None,
) -> list[SliceComparison]:
    eligible_keys = [
        (current_tranche_id, slice_id)
        for (current_tranche_id, slice_id), results in slice_results.items()
        if results and (tranche_id is None or current_tranche_id == tranche_id)
    ]
    winners = {
        key: results[0].genome_id if results else None for key, results in slice_results.items()
    }

    comparisons: list[SliceComparison] = []
    for left_key, right_key in combinations(sorted(eligible_keys), 2):
        left_results = slice_results[left_key]
        right_results = slice_results[right_key]
        left_top = {result.genome_id for result in left_results[:top_k]}
        right_top = {result.genome_id for result in right_results[:top_k]}
        union = left_top | right_top
        shared = left_top & right_top
        comparisons.append(
            SliceComparison(
                tranche_id=tranche_id or "sweep",
                left_slice_id=left_key[1],
                right_slice_id=right_key[1],
                top_k=top_k,
                overlap_count=len(shared),
                jaccard_index=(len(shared) / len(union)) if union else 1.0,
                shared_top_candidates=sorted(shared),
                left_only_candidates=sorted(left_top - right_top),
                right_only_candidates=sorted(right_top - left_top),
                same_winner=winners[left_key] == winners[right_key],
            )
        )
    return comparisons


def _dominant_winner(slice_winners: list[SliceWinner]) -> tuple[str | None, int]:
    counts: dict[str, int] = {}
    for winner in slice_winners:
        if winner.status != SliceRunStatus.COMPLETED or winner.candidate_id is None:
            continue
        counts[winner.candidate_id] = counts.get(winner.candidate_id, 0) + 1
    if not counts:
        return None, 0
    dominant_candidate_id, dominant_win_count = max(
        counts.items(),
        key=lambda item: item[1],
    )
    return dominant_candidate_id, dominant_win_count


def _adaptive_audit_summary(
    manifest: SweepManifest,
    *,
    slice_records: list[SliceExecutionRecord],
    tranche_id: str | None,
) -> AdaptiveAuditSummary:
    relevant_decisions = [
        decision
        for decision in manifest.decision_log
        if tranche_id is None or decision.tranche_id == tranche_id
    ]
    utility_warning_slices = len(
        {record.slice_id for record in slice_records if record.utility.trace.warning_codes}
    )
    counts = {decision_type: 0 for decision_type in AdaptiveDecisionType}
    for decision in relevant_decisions:
        counts[decision.decision_type] += 1
    return AdaptiveAuditSummary(
        initial_utility_seeds=counts[AdaptiveDecisionType.INITIAL_UTILITY_SEED],
        utility_updates=counts[AdaptiveDecisionType.UTILITY_UPDATE],
        refinements_generated=counts[AdaptiveDecisionType.REFINEMENT_GENERATED],
        refinements_skipped=counts[AdaptiveDecisionType.REFINEMENT_SKIPPED],
        slices_pruned=counts[AdaptiveDecisionType.SLICE_PRUNED],
        pruning_retained=counts[AdaptiveDecisionType.PRUNING_RETAINED],
        cross_tranche_generated=counts[AdaptiveDecisionType.CROSS_TRANCHE_GENERATED],
        cross_tranche_skipped=counts[AdaptiveDecisionType.CROSS_TRANCHE_SKIPPED],
        utility_warning_slices=utility_warning_slices,
    )


def _residual_structure_summary(
    slice_records: list[SliceExecutionRecord],
) -> ResidualStructureSummary:
    completed = [record for record in slice_records if record.status == SliceRunStatus.COMPLETED]
    return ResidualStructureSummary(
        autocorrelation_scores=[
            record.utility.residual_diagnostics.autocorrelation_score for record in completed
        ],
        spectral_scores=[
            record.utility.residual_diagnostics.spectral_score for record in completed
        ],
        burst_scores=[record.utility.residual_diagnostics.burst_score for record in completed],
        decay_deviation_scores=[
            record.utility.residual_diagnostics.decay_deviation_score for record in completed
        ],
        residual_quality_scores=[record.utility.residual_quality_score for record in completed],
    )


def _null_model_summary(slice_records: list[SliceExecutionRecord]) -> NullModelSummary:
    comparisons = [
        record.null_model_comparison
        for record in slice_records
        if record.status == SliceRunStatus.COMPLETED
    ]
    available = [comparison for comparison in comparisons if comparison.available]
    top_deltas = [
        comparison.top_candidate_delta
        for comparison in available
        if comparison.top_candidate_delta is not None
    ]
    mean_deltas = [
        comparison.mean_score_delta
        for comparison in available
        if comparison.mean_score_delta is not None
    ]
    positive_rates = [
        comparison.positive_delta_rate
        for comparison in available
        if comparison.positive_delta_rate is not None
    ]
    delta_residuals = [
        comparison.delta_residual
        for comparison in available
        if comparison.delta_residual is not None
    ]
    delta_fit_qualities = [
        comparison.delta_fit_quality
        for comparison in available
        if comparison.delta_fit_quality is not None
    ]
    return NullModelSummary(
        requested_slices=sum(comparison.requested for comparison in comparisons),
        available_slices=len(available),
        winner_changed_slices=sum(comparison.winner_changed for comparison in available),
        mean_top_candidate_delta=mean(top_deltas) if top_deltas else None,
        mean_score_delta=mean(mean_deltas) if mean_deltas else None,
        positive_delta_rate=mean(positive_rates) if positive_rates else None,
        dominated_by_null_slices=sum(
            comparison.dominance_classification == NullDominanceClassification.DOMINATED_BY_NULL
            for comparison in available
        ),
        indeterminate_slices=sum(
            comparison.dominance_classification == NullDominanceClassification.INDETERMINATE
            for comparison in available
        ),
        improves_over_null_slices=sum(
            comparison.dominance_classification == NullDominanceClassification.IMPROVES_OVER_NULL
            for comparison in available
        ),
        mean_delta_residual=mean(delta_residuals) if delta_residuals else None,
        mean_delta_fit_quality=mean(delta_fit_qualities) if delta_fit_qualities else None,
    )


def _identifiability_summary(slice_records: list[SliceExecutionRecord]) -> IdentifiabilitySummary:
    completed = [record for record in slice_records if record.status == SliceRunStatus.COMPLETED]
    return IdentifiabilitySummary(
        evaluated_slices=len(completed),
        failure_count=sum(
            not record.utility.identifiability.is_identifiable for record in completed
        ),
    )


def _scaling_summary(slice_records: list[SliceExecutionRecord]) -> ScalingSummary:
    completed = [record for record in slice_records if record.status == SliceRunStatus.COMPLETED]
    evaluated = [
        record
        for record in completed
        if record.utility.scaling_validation.expected_scaling_type.value != "unknown"
    ]
    match_count = sum(
        record.utility.scaling_validation.observed_scaling_type
        == record.utility.scaling_validation.expected_scaling_type
        for record in evaluated
    )
    mismatch_count = len(evaluated) - match_count
    return ScalingSummary(
        evaluated_slices=len(evaluated),
        match_count=match_count,
        mismatch_count=mismatch_count,
        match_rate=(match_count / len(evaluated)) if evaluated else None,
    )


def _top_slices(slice_records: list[SliceExecutionRecord]) -> list[TopSliceSummary]:
    completed = [record for record in slice_records if record.status == SliceRunStatus.COMPLETED]
    ordered = sorted(
        completed,
        key=lambda record: (-record.utility.utility_score, record.slice_id),
    )
    return [
        TopSliceSummary(
            tranche_id=record.tranche_id,
            slice_id=record.slice_id,
            utility_score=record.utility.utility_score,
            total_utility=record.utility.utility_components.total_utility,
            top_candidate_id=record.top_candidate_id,
            top_score=record.top_score,
        )
        for record in ordered[:5]
    ]


def _utility_distribution(
    slice_records: list[SliceExecutionRecord],
) -> UtilityDistributionSummary:
    completed = [
        record.utility.utility_score
        for record in slice_records
        if record.status == SliceRunStatus.COMPLETED
    ]
    if not completed:
        return UtilityDistributionSummary()
    ordered = sorted(completed)
    midpoint = len(ordered) // 2
    median_value = (
        ordered[midpoint]
        if len(ordered) % 2 == 1
        else (ordered[midpoint - 1] + ordered[midpoint]) / 2.0
    )
    return UtilityDistributionSummary(
        min_utility=min(ordered),
        max_utility=max(ordered),
        mean_utility=mean(ordered),
        median_utility=median_value,
    )


def _null_model_win_loss(
    slice_records: list[SliceExecutionRecord],
) -> NullModelWinLossSummary:
    completed = [record for record in slice_records if record.status == SliceRunStatus.COMPLETED]
    return NullModelWinLossSummary(
        wins=sum(
            record.null_model_comparison.dominance_classification
            == NullDominanceClassification.IMPROVES_OVER_NULL
            for record in completed
        ),
        losses=sum(
            record.null_model_comparison.dominance_classification
            == NullDominanceClassification.DOMINATED_BY_NULL
            for record in completed
        ),
        indeterminate=sum(
            record.null_model_comparison.dominance_classification
            == NullDominanceClassification.INDETERMINATE
            for record in completed
        ),
    )


def _unstable_regions(slice_records: list[SliceExecutionRecord]) -> list[UnstableRegionSummary]:
    completed = [record for record in slice_records if record.status == SliceRunStatus.COMPLETED]
    unstable: list[UnstableRegionSummary] = []
    for record in completed:
        reason: str | None = None
        if record.utility.residual_quality_score < 0.5:
            reason = "low_residual_quality"
        elif record.utility.scaling_score < 0.5:
            reason = "scaling_mismatch"
        elif (
            record.utility.null_dominance_classification
            == NullDominanceClassification.DOMINATED_BY_NULL
        ):
            reason = "null_model_loss"
        if reason is None:
            continue
        unstable.append(
            UnstableRegionSummary(
                tranche_id=record.tranche_id,
                slice_id=record.slice_id,
                reason=reason,
                utility_score=record.utility.utility_score,
                residual_score=record.utility.residual_quality_score,
                scaling_score=record.utility.scaling_score,
                null_delta=record.utility.null_model_delta,
            )
        )
    return unstable


def _mechanism_separation_matrix(
    *,
    manifest: SweepManifest,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
) -> list[MechanismSeparationEntry]:
    comparisons = _build_slice_comparisons(
        slice_results=slice_results,
        top_k=_overall_top_k(manifest),
        tranche_id=None,
    )
    entries: list[MechanismSeparationEntry] = []
    for comparison in comparisons:
        left_tranche_id, right_tranche_id = "sweep", "sweep"
        for tranche in manifest.plan.tranches:
            if any(slice_plan.slice_id == comparison.left_slice_id for slice_plan in tranche.slices):
                left_tranche_id = tranche.tranche_id
            if any(slice_plan.slice_id == comparison.right_slice_id for slice_plan in tranche.slices):
                right_tranche_id = tranche.tranche_id
        entries.append(
            MechanismSeparationEntry(
                left_tranche_id=left_tranche_id,
                left_slice_id=comparison.left_slice_id,
                right_tranche_id=right_tranche_id,
                right_slice_id=comparison.right_slice_id,
                separation_score=clamp(1.0 - comparison.jaccard_index),
                shared_winner=comparison.same_winner,
            )
        )
    return entries


def _scaling_consistency_map(
    manifest: SweepManifest,
    slice_records: list[SliceExecutionRecord],
) -> list[ScalingConsistencyEntry]:
    by_tranche: dict[str, list[SliceExecutionRecord]] = {}
    for record in slice_records:
        if record.status != SliceRunStatus.COMPLETED:
            continue
        by_tranche.setdefault(record.tranche_id, []).append(record)
    entries: list[ScalingConsistencyEntry] = []
    tranche_lookup = {tranche.tranche_id: tranche for tranche in manifest.plan.tranches}
    for tranche_id, records in sorted(by_tranche.items()):
        scaling_scores = [record.utility.scaling_score for record in records]
        if not scaling_scores:
            continue
        tranche = tranche_lookup.get(tranche_id)
        entries.append(
            ScalingConsistencyEntry(
                tranche_id=tranche_id,
                hypothesis_class=(
                    tranche.hypothesis_class if tranche is not None else HypothesisClass.LEGACY
                ),
                consistency_score=clamp(mean(scaling_scores)),
                mean_scaling_score=mean(scaling_scores),
                evaluated_slices=len(records),
            )
        )
    return entries


def _null_model_win_rate_by_tranche_class(
    slice_records: list[SliceExecutionRecord],
) -> list[NullModelWinRateEntry]:
    grouped: dict[HypothesisClass, list[SliceExecutionRecord]] = {}
    for record in slice_records:
        if record.status != SliceRunStatus.COMPLETED:
            continue
        grouped.setdefault(record.hypothesis_class, []).append(record)
    entries: list[NullModelWinRateEntry] = []
    for hypothesis_class, records in sorted(grouped.items(), key=lambda item: item[0].value):
        wins = sum(
            record.null_model_comparison.dominance_classification
            == NullDominanceClassification.IMPROVES_OVER_NULL
            for record in records
        )
        entries.append(
            NullModelWinRateEntry(
                tranche_class=hypothesis_class,
                win_rate=(wins / len(records)) if records else 0.0,
                win_count=wins,
                total_count=len(records),
            )
        )
    return entries


def _degeneracy_clusters(slice_records: list[SliceExecutionRecord]) -> list[DegeneracyCluster]:
    completed = [record for record in slice_records if record.status == SliceRunStatus.COMPLETED]
    adjacency: dict[str, set[str]] = {}
    record_by_slice = {record.slice_id: record for record in completed}
    for record in completed:
        conflicting_slice_id = record.utility.identifiability.conflicting_slice_id
        if conflicting_slice_id is None:
            continue
        adjacency.setdefault(record.slice_id, set()).add(conflicting_slice_id)
        adjacency.setdefault(conflicting_slice_id, set()).add(record.slice_id)

    visited: set[str] = set()
    clusters: list[DegeneracyCluster] = []
    for slice_id in sorted(adjacency):
        if slice_id in visited:
            continue
        stack = [slice_id]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(sorted(adjacency.get(current, set()) - visited))
        records = [record_by_slice[candidate] for candidate in component if candidate in record_by_slice]
        if not records:
            continue
        clusters.append(
            DegeneracyCluster(
                cluster_id=f"degeneracy_{len(clusters) + 1}",
                tranche_ids=sorted({record.tranche_id for record in records}),
                slice_ids=sorted(component),
                hypothesis_classes=sorted(
                    {record.hypothesis_class for record in records},
                    key=lambda value: value.value,
                ),
                mean_identifiability_score=mean(
                    record.utility.identifiability_score for record in records
                ),
            )
        )
    return clusters


def _overall_top_k(manifest: SweepManifest) -> int:
    return max(tranche.comparison_strategy.top_k for tranche in manifest.plan.tranches)


def _build_summary_highlights(
    *,
    aggregate_rankings: list[CandidateAggregate],
    successful_slices: int,
    failed_slices: int,
    pruned_slices: int,
) -> list[str]:
    highlights: list[str] = []
    if aggregate_rankings:
        top_candidate = aggregate_rankings[0]
        highlights.append(
            f"{top_candidate.genome_id} achieved the highest robustness score across "
            f"{top_candidate.successful_slice_count} successful slices."
        )
        most_stable = min(aggregate_rankings, key=lambda item: (item.rank_span, item.mean_rank))
        highlights.append(
            f"{most_stable.genome_id} had the tightest rank spread ({most_stable.rank_span}) "
            f"among compared slices."
        )
        most_sensitive = max(
            aggregate_rankings,
            key=lambda item: (item.profile_sensitivity_score, item.rank_span),
        )
        highlights.append(
            f"{most_sensitive.genome_id} showed the strongest profile sensitivity signal "
            f"with score {most_sensitive.profile_sensitivity_score:.3f}."
        )
    if failed_slices:
        highlights.append(
            f"{failed_slices} slice failures were isolated while preserving {successful_slices} "
            "successful slice outputs."
        )
    if pruned_slices:
        highlights.append(
            f"{pruned_slices} planned slices were pruned before execution by the adaptive planner."
        )
    return highlights
