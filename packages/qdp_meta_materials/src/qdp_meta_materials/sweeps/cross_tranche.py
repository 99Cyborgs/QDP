from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ..models import MMMDataset
from .models import (
    AdaptiveDecisionRecord,
    AdaptiveDecisionType,
    RefinementReason,
    ResolvedSlicePlan,
    ResolvedTranchePlan,
    SliceLineage,
    SlicePlanningSource,
    SliceRunStatus,
    SweepManifest,
    TrancheExecutionMode,
    TrancheObjective,
    TrancheSamplingStrategy,
    TrancheType,
)
from .planner import (
    _candidate_filter_signature,
    _candidate_jaccard,
    _evaluate_slice_utility,
    _rank_slice_candidates,
    _sha256_bytes,
    _slugify,
)


def select_top_slices_by_tranche(
    manifest: SweepManifest,
) -> dict[str, list[ResolvedSlicePlan]]:
    config = manifest.adaptive.cross_tranche
    selected: dict[str, list[ResolvedSlicePlan]] = {}
    for tranche_plan, tranche_record in zip(manifest.plan.tranches, manifest.tranches, strict=True):
        if (
            tranche_plan.tranche_id == "cross_tranche_interactions"
            or tranche_plan.tranche_type == TrancheType.INTERACTION
            or tranche_plan.tranche_type in {TrancheType.NULL_MODEL, TrancheType.NULL_DOMINANCE_TRANCHE}
        ):
            continue
        completed = [
            slice_plan
            for slice_plan, slice_record in zip(
                tranche_plan.slices,
                tranche_record.slice_statuses,
                strict=True,
            )
            if slice_record.status == SliceRunStatus.COMPLETED
            and slice_plan.utility.utility_score >= config.priority_threshold
        ]
        completed.sort(key=lambda item: (-item.utility.utility_score, item.slice_id))
        if completed:
            selected[tranche_plan.tranche_id] = completed[: config.max_source_slices_per_tranche]
    return selected


def merge_parameter_vectors(
    left: ResolvedSlicePlan,
    right: ResolvedSlicePlan,
) -> list:
    merged: list = []
    seen: set[str] = set()
    for filter_spec in [*left.candidate_filters, *right.candidate_filters]:
        signature = json.dumps(_candidate_filter_signature(filter_spec), sort_keys=True)
        if signature in seen:
            continue
        seen.add(signature)
        merged.append(filter_spec.model_copy(deep=True))
    return merged


def dedupe_interaction_candidates(
    candidates: list[ResolvedSlicePlan],
) -> list[ResolvedSlicePlan]:
    deduped: list[ResolvedSlicePlan] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for candidate in candidates:
        signature = (candidate.resolved_profile, tuple(candidate.candidate_ids))
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(candidate)
    return deduped


def generate_interaction_slices(
    manifest: SweepManifest,
    *,
    dataset: MMMDataset,
    selected_by_tranche: dict[str, list[ResolvedSlicePlan]],
) -> list[ResolvedSlicePlan]:
    config = manifest.adaptive.cross_tranche
    eligible_sources = [
        slice_plan
        for tranche_id in sorted(selected_by_tranche)
        for slice_plan in selected_by_tranche[tranche_id]
    ]
    if len(eligible_sources) < 2:
        return []

    interaction_pairs: list[tuple[ResolvedSlicePlan, ResolvedSlicePlan]] = []
    for left in eligible_sources:
        for right in eligible_sources:
            if left.tranche_id >= right.tranche_id:
                continue
            interaction_pairs.append((left, right))
    interaction_pairs.sort(
        key=lambda pair: (
            -(pair[0].utility.utility_score + pair[1].utility.utility_score),
            pair[0].tranche_id,
            pair[0].slice_id,
            pair[1].tranche_id,
            pair[1].slice_id,
        )
    )

    generated: list[ResolvedSlicePlan] = []
    for left, right in interaction_pairs:
        if len(generated) >= config.max_interaction_slices:
            break
        candidate_ids = sorted(set(left.candidate_ids) & set(right.candidate_ids))
        if len(candidate_ids) < config.min_candidate_count:
            manifest.decision_log.append(
                AdaptiveDecisionRecord(
                    phase=3,
                    decision_type=AdaptiveDecisionType.CROSS_TRANCHE_SKIPPED,
                    tranche_id="cross_tranche_interactions",
                    related_slice_ids=[left.slice_id, right.slice_id],
                    reason="Interaction slice was below the configured minimum candidate count.",
                    metrics={
                        "candidate_count": len(candidate_ids),
                        "candidate_floor": config.min_candidate_count,
                    },
                    created_at=datetime.now(UTC),
                )
            )
            continue

        driving_parent = (
            left if left.utility.utility_score >= right.utility.utility_score else right
        )
        provisional_plan = driving_parent.model_copy(
            update={
                "candidate_ids": candidate_ids,
                "candidate_count": len(candidate_ids),
                "candidate_filters": merge_parameter_vectors(left, right),
                "phase": 3,
                "tranche_type": TrancheType.INTERACTION,
                "tranche_objective": TrancheObjective.CROSS_TRANCHE_INTERACTION,
            },
            deep=True,
        )
        provisional_results = _rank_slice_candidates(
            dataset=dataset,
            profile=driving_parent.resolved_profile,
            candidate_ids=candidate_ids,
            null_model_enabled=manifest.adaptive.null_model.enabled,
            baseline_mode=manifest.adaptive.null_model.mode.value,
            baseline_profile=manifest.adaptive.null_model.baseline_profile,
            tranche_type=TrancheType.INTERACTION,
        )
        utility, _ = _evaluate_slice_utility(
            dataset=dataset,
            slice_plan=provisional_plan,
            results=provisional_results,
            peer_results={
                source.slice_id: _rank_slice_candidates(
                    dataset=dataset,
                    profile=source.resolved_profile,
                    candidate_ids=source.candidate_ids,
                    null_model_enabled=manifest.adaptive.null_model.enabled,
                    baseline_mode=manifest.adaptive.null_model.mode.value,
                    baseline_profile=manifest.adaptive.null_model.baseline_profile,
                    tranche_type=source.tranche_type,
                )
                for source in eligible_sources
            },
            utility_weights=driving_parent.utility_weights or manifest.adaptive.utility_weights,
            residual_weights=manifest.residual_weights,
                candidate_floor=manifest.adaptive.refinement.candidate_count_floor,
                identifiability_threshold=manifest.identifiability_threshold,
                scaling_tolerance=manifest.scaling_tolerance,
                null_model_tolerance=manifest.null_model_tolerance,
                measurement=manifest.measurement,
                input_similarity=max(
                    _candidate_jaccard(candidate_ids, left.candidate_ids),
                    _candidate_jaccard(candidate_ids, right.candidate_ids),
                ),
            output_similarity=0.0,
            utility_basis="planned_cross_tranche",
        )
        slice_id = _unique_cross_slice_id(generated, left, right)
        interaction_slice = ResolvedSlicePlan(
            tranche_id="cross_tranche_interactions",
            slice_id=slice_id,
            phase=3,
            planning_source=SlicePlanningSource.CROSS_TRANCHE,
            tranche_type=TrancheType.INTERACTION,
            tranche_objective=TrancheObjective.CROSS_TRANCHE_INTERACTION,
            resolved_profile=driving_parent.resolved_profile,
            resolved_parameters=driving_parent.resolved_parameters.model_copy(deep=True),
            input_registry_scope=driving_parent.input_registry_scope.model_copy(deep=True),
            candidate_filters=merge_parameter_vectors(left, right),
            control_parameters=[],
            fixed_parameters=[],
            max_slices=config.max_interaction_slices,
            sampling_strategy=TrancheSamplingStrategy.TOP_UTILITY,
            source_tranche_ids=sorted({left.tranche_id, right.tranche_id}),
            perturbation_fraction=None,
            log_scale_parameters=[],
            interaction_mode=None,
            null_pair_id=None,
            parent_slice_id=driving_parent.slice_id,
            refinement_reason=RefinementReason.INTERACTION_SYNTHESIS,
            expected_signature=driving_parent.expected_signature,
            lineage_depth=max(left.lineage_depth, right.lineage_depth) + 1,
            utility_weights=driving_parent.utility_weights,
            output_requirements=driving_parent.output_requirements.model_copy(deep=True),
            tags=sorted(
                {
                    *left.tags,
                    *right.tags,
                    "adaptive",
                    "cross_tranche",
                    left.tranche_id,
                    right.tranche_id,
                }
            ),
            candidate_ids=candidate_ids,
            candidate_count=len(candidate_ids),
            output_dir=str(
                Path(manifest.output_root)
                / "tranches"
                / "cross_tranche_interactions"
                / "slices"
                / slice_id
            ),
            parameter_hash=_sha256_bytes(
                json.dumps(
                    {
                        "left": left.parameter_hash,
                        "right": right.parameter_hash,
                        "candidate_ids": candidate_ids,
                    },
                    sort_keys=True,
                ).encode("utf-8")
            ),
            lineage=SliceLineage(
                phase=3,
                reason="cross_tranche_interaction",
                parent_slice_id=driving_parent.slice_id,
                parent_slice_ids=[left.slice_id, right.slice_id],
                refinement_reason=RefinementReason.INTERACTION_SYNTHESIS,
                trigger_metric="utility_threshold",
                trigger_value=min(left.utility.utility_score, right.utility.utility_score),
                lineage_depth=max(left.lineage_depth, right.lineage_depth) + 1,
            ),
            utility=utility,
        )
        generated.append(interaction_slice)
        manifest.decision_log.append(
            AdaptiveDecisionRecord(
                phase=3,
                decision_type=AdaptiveDecisionType.CROSS_TRANCHE_GENERATED,
                tranche_id="cross_tranche_interactions",
                slice_id=slice_id,
                related_slice_ids=[left.slice_id, right.slice_id],
                reason="Generated cross-tranche interaction slice from high-utility tranche seeds.",
                metrics={
                    "utility_score": utility.utility_score,
                    "candidate_count": len(candidate_ids),
                    "left_utility": left.utility.utility_score,
                    "right_utility": right.utility.utility_score,
                },
                created_at=datetime.now(UTC),
            )
        )
    return dedupe_interaction_candidates(generated)


def generate_cross_tranche_tranche(
    manifest: SweepManifest,
    *,
    dataset: MMMDataset,
) -> ResolvedTranchePlan | None:
    config = manifest.adaptive.cross_tranche
    if not manifest.adaptive.enabled or not config.enabled:
        return None

    selected_by_tranche = select_top_slices_by_tranche(manifest)
    slices = generate_interaction_slices(
        manifest,
        dataset=dataset,
        selected_by_tranche=selected_by_tranche,
    )
    if not slices:
        return None

    return ResolvedTranchePlan(
        tranche_id="cross_tranche_interactions",
        objective="Evaluate interaction hypotheses between high-utility slices across tranches.",
        tranche_type=TrancheType.INTERACTION,
        tranche_objective=TrancheObjective.CROSS_TRANCHE_INTERACTION,
        execution_mode=TrancheExecutionMode.SEQUENTIAL,
        comparison_strategy=max(
            manifest.plan.tranches,
            key=lambda tranche: tranche.comparison_strategy.top_k,
        ).comparison_strategy.model_copy(deep=True),
        shared_profile=slices[0].resolved_profile,
        output_dir=str(Path(manifest.output_root) / "tranches" / "cross_tranche_interactions"),
        control_parameters=[],
        fixed_parameters=[],
        max_slices=config.max_interaction_slices,
        sampling_strategy=TrancheSamplingStrategy.TOP_UTILITY,
        source_tranche_ids=sorted(selected_by_tranche),
        perturbation_fraction=None,
        log_scale_parameters=[],
        interaction_mode=None,
        expected_signature=slices[0].expected_signature,
        utility_weights=slices[0].utility_weights,
        slices=slices,
    )


def _unique_cross_slice_id(
    current_slices: list[ResolvedSlicePlan],
    left: ResolvedSlicePlan,
    right: ResolvedSlicePlan,
) -> str:
    base = (
        f"{_slugify(left.tranche_id)}__{_slugify(left.slice_id)}"
        f"__x__{_slugify(right.tranche_id)}__{_slugify(right.slice_id)}"
    )
    existing = {slice_plan.slice_id for slice_plan in current_slices}
    candidate = base
    suffix = 2
    while candidate in existing:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate
