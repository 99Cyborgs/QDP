from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations, product
from pathlib import Path
from statistics import mean, median
from typing import Any, TypeAlias, cast

from qdp_io.serialization import load_yaml

from ..config import default_seed_root
from ..errors import SweepPlanningError
from ..registry import load_dataset
from ..models import (
    HypothesisClass,
    IdentifiabilityResult,
    MMMDataset,
    NullDominanceClassification,
    ResidualDiagnostics,
    ResidualWeightConfig,
    ScalarValue,
    ScalingType,
    ScalingValidation,
    ScoreResult,
    ScoringProfile,
    UtilityComponents,
)
from ..registry import DOCUMENT_SPECS
from ..scoring import (
    build_utility_components,
    clamp,
    compute_residual_diagnostics,
    equivalence_margin as compute_equivalence_margin,
    failure_mode_match_score,
    genome_numeric_observables,
    get_scoring_profile,
    identifiability_score as compute_identifiability_score,
    measurement_resolution_floor,
    null_equivalence_score,
    parameter_economy_penalty,
    rank_dataset,
    rank_dataset_with_profile,
    residual_quality_score,
    scaling_separation_score,
    weighted_utility_score,
)
from ..validation import (
    check_identifiability,
    classify_null_model_dominance,
    fit_scaling_signature,
    infer_expected_scaling_type,
    validate_scaling_behavior,
)
from .contracts import get_equivalence_edges
from .models import (
    AdaptiveDecisionRecord,
    AdaptiveDecisionType,
    CandidateFilter,
    CandidateFilterField,
    CrossDeviceTrancheFields,
    EquivalenceEdge,
    DiscriminatorTrancheFields,
    DiscriminationTrancheFields,
    ExpectedSignature,
    FilterOperator,
    FailureModeTrancheFields,
    hypothesis_class_for_tranche_type,
    HypothesisTrancheBase,
    InputHashRecord,
    NullDominanceTrancheFields,
    NullLineageLock,
    OrthogonalAxis,
    PlanSufficiencyAssessment,
    PerturbationDiagnostics,
    RedundancyPruningConfig,
    RefinementReason,
    RegistryScope,
    ResolvedSlicePlan,
    ResolvedSweepPlan,
    ResolvedTranchePlan,
    ScalingLawTrancheFields,
    SliceExecutionRecord,
    SliceLineage,
    SliceNullModelComparison,
    SlicePlanningSource,
    SlicePruningDecision,
    SlicePruningReasonCode,
    SliceRunStatus,
    SliceSpec,
    SliceUtility,
    SliceUtilityTrace,
    SweepExecutionParameters,
    SweepManifest,
    SweepRunStatus,
    SweepSpec,
    SufficiencyIssue,
    SufficiencyIssueCode,
    TrancheObjective,
    TrancheExecutionRecord,
    TrancheSamplingStrategy,
    TrancheSpec,
    TrancheType,
    UtilityPenaltyTrace,
    UtilityWarningCode,
    BoundaryStressTrancheFields,
    IdentifiabilityTrancheFields,
    MeasurementEquivalenceConfig,
    RejectedAxisRationale,
)

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_NUMERIC_FIELDS = {
    CandidateFilterField.FABRICATION_COMPLEXITY,
    CandidateFilterField.NULL_RISK,
    CandidateFilterField.CLEANROOM_LEVEL,
    CandidateFilterField.MICROWAVE_MIN_GHZ,
    CandidateFilterField.MICROWAVE_MAX_GHZ,
    CandidateFilterField.PHONONIC_MIN_GHZ,
    CandidateFilterField.PHONONIC_MAX_GHZ,
}
FilterSignature: TypeAlias = dict[str, ScalarValue | list[ScalarValue]]
_TRANCHE_PHASES = {
    TrancheType.BASELINE: 1,
    TrancheType.PRIMARY: 1,
    TrancheType.NULL_MODEL: 1,
    TrancheType.DISCRIMINATION_TRANCHE: 1,
    TrancheType.NULL_DOMINANCE_TRANCHE: 1,
    TrancheType.LOCAL_PERTURBATION: 2,
    TrancheType.SCALING: 2,
    TrancheType.SCALING_LAW_TRANCHE: 2,
    TrancheType.IDENTIFIABILITY_TRANCHE: 2,
    TrancheType.DISCRIMINATOR_TRANCHE: 2,
    TrancheType.CROSS_DEVICE_TRANCHE: 2,
    TrancheType.INTERACTION: 3,
    TrancheType.STRESS_TEST: 3,
    TrancheType.FAILURE_MODE_TRANCHE: 3,
    TrancheType.BOUNDARY_STRESS_TRANCHE: 3,
}


@dataclass(slots=True)
class AdversarialPairCandidate:
    edge: EquivalenceEdge
    pair_key: tuple[str, str]
    prior_plausibility: float
    left_genome_id: str
    right_genome_id: str


@dataclass(slots=True)
class AxisGainCandidate:
    axis: OrthogonalAxis
    axis_key: str
    expected_separation: float
    discriminator_gain: float
    axis_cost: float
    redundancy_penalty: float


@dataclass(slots=True)
class RejectedAxisCandidate:
    axis_key: str
    reason: str
    redundancy_penalty: float
    correlation: float | None = None
    blocking_axis: str | None = None


def load_sweep_spec(path: str | Path) -> SweepSpec:
    """Load a sweep spec from YAML or JSON."""

    spec_path = Path(path)
    if not spec_path.exists():
        raise SweepPlanningError(f"Sweep spec does not exist: {spec_path}")

    if spec_path.suffix.lower() == ".json":
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
    else:
        payload = load_yaml(spec_path)
    return SweepSpec.model_validate(payload)


def plan_sweep(
    spec: SweepSpec,
    *,
    dataset_root: str | Path | None = None,
    output_dir: str | Path | None = None,
    command: str = "qdp-meta-materials sweep-run",
    spec_source: str | Path | None = None,
) -> SweepManifest:
    """Resolve a declarative sweep spec into a normalized executable manifest."""

    dataset = load_dataset(dataset_root or default_seed_root())
    effective_spec = _build_effective_spec(spec)
    _validate_spec_ids(effective_spec)

    planned_at = datetime.now(UTC)
    sweep_id = _resolve_sweep_id(effective_spec.name, planned_at, output_dir)
    output_root = _resolve_output_root(effective_spec, output_dir, sweep_id)

    ordered_specs = sorted(
        enumerate(effective_spec.tranches),
        key=lambda item: (
            1 if _is_null_tranche_type(item[1].tranche_type) else 0,
            _TRANCHE_PHASES[item[1].tranche_type],
            item[0],
            item[1].tranche_id,
        ),
    )
    resolved_by_id: dict[str, ResolvedTranchePlan] = {}
    tranches: list[ResolvedTranchePlan] = []
    for _, tranche in ordered_specs:
        resolved = _resolve_tranche(
            effective_spec,
            tranche,
            dataset,
            output_root,
            resolved_tranches=resolved_by_id,
        )
        resolved_by_id[resolved.tranche_id] = resolved
        tranches.append(resolved)
    _link_null_pairs(tranches)
    sufficiency = _validate_resolved_plan(effective_spec, dataset, tranches)
    plan = ResolvedSweepPlan(
        sweep_name=effective_spec.name,
        description=effective_spec.description,
        version=effective_spec.version,
        dataset_root=str(dataset.root),
        output_root=str(output_root),
        adaptive_enabled=effective_spec.adaptive.enabled,
        sufficiency=sufficiency,
        tranches=tranches,
    )

    decision_log = _apply_initial_utilities(plan, effective_spec, dataset, planned_at)
    injected_discriminators = generate_discriminator_tranches_from_plan(
        plan,
        spec=effective_spec,
        dataset=dataset,
        output_root=output_root,
    )
    if injected_discriminators:
        plan.tranches.extend(injected_discriminators)
        plan.sufficiency = _validate_resolved_plan(effective_spec, dataset, plan.tranches)
        decision_log.extend(
            AdaptiveDecisionRecord(
                phase=1,
                decision_type=AdaptiveDecisionType.DISCRIMINATOR_GENERATED,
                tranche_id=tranche.tranche_id,
                reason="Pre-execution adversarial discriminator injected from simulated equivalence collapse.",
                related_slice_ids=list(
                    tranche.discriminator_tranche.target_hypothesis_pair
                    if tranche.discriminator_tranche is not None
                    else []
                ),
                metrics={
                    "generation": 1,
                    "predicted_separation": (
                        tranche.discriminator_tranche.predicted_separation
                        if tranche.discriminator_tranche is not None
                        else 0.0
                    ),
                },
                created_at=planned_at,
            )
            for tranche in injected_discriminators
        )
        decision_log.extend(_apply_initial_utilities(plan, effective_spec, dataset, planned_at))
    plan.plan_identity = _resolved_plan_identity(plan.tranches)
    tranche_records = [build_tranche_execution_record(tranche) for tranche in plan.tranches]

    return SweepManifest(
        sweep_id=sweep_id,
        sweep_name=effective_spec.name,
        description=effective_spec.description,
        spec_version=effective_spec.version,
        status=SweepRunStatus.PLANNED,
        output_root=str(output_root),
        dataset_root=str(dataset.root),
        command=command,
        planned_at=planned_at,
        residual_weights=effective_spec.residual_weights.model_copy(deep=True),
        identifiability_threshold=effective_spec.identifiability_threshold,
        scaling_tolerance=effective_spec.scaling_tolerance,
        null_model_tolerance=effective_spec.null_model_tolerance,
        measurement=effective_spec.measurement.model_copy(deep=True),
        input_hashes=_build_input_hashes(effective_spec, dataset.root, spec_source),
        adaptive=effective_spec.adaptive.model_copy(deep=True),
        plan=plan,
        tranches=tranche_records,
        decision_log=decision_log,
        artifact_paths={
            "manifest": str(output_root / "sweep_manifest.json"),
            "summary_json": str(output_root / "sweep_summary.json"),
            "summary_markdown": str(output_root / "sweep_summary.md"),
            "tranche_index": str(output_root / "tranche_index.json"),
            "aggregate_leaderboard_csv": str(output_root / "aggregate_leaderboard.csv"),
            "plots_dir": str(output_root / "plots"),
        },
    )


def build_tranche_execution_record(tranche: ResolvedTranchePlan) -> TrancheExecutionRecord:
    return TrancheExecutionRecord(
        tranche_id=tranche.tranche_id,
        tranche_type=tranche.tranche_type,
        tranche_objective=tranche.tranche_objective,
        hypothesis_class=tranche.hypothesis_class,
        status=SweepRunStatus.PLANNED,
        output_dir=tranche.output_dir,
        slice_statuses=[
            SliceExecutionRecord(
                tranche_id=tranche.tranche_id,
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
            for slice_plan in tranche.slices
        ],
        artifact_paths={
            "summary_json": str(Path(tranche.output_dir) / "tranche_summary.json"),
            "summary_markdown": str(Path(tranche.output_dir) / "tranche_summary.md"),
        },
    )


def _build_effective_spec(spec: SweepSpec) -> SweepSpec:
    effective = spec.model_copy(deep=True)
    should_inject_null = effective.require_null_dominance or effective.adaptive.enabled or any(
        hypothesis_class_for_tranche_type(tranche.tranche_type) != HypothesisClass.LEGACY
        for tranche in effective.tranches
    )
    if not should_inject_null:
        return effective
    null_tranche = _ensure_null_dominance_tranche(effective)
    if null_tranche is not None:
        effective.tranches.append(null_tranche)
    return effective


def _ensure_null_dominance_tranche(spec: SweepSpec) -> TrancheSpec | None:
    existing = next(
        (
            tranche
            for tranche in spec.tranches
            if tranche.tranche_type == TrancheType.NULL_DOMINANCE_TRANCHE
        ),
        None,
    )
    source_ids = [
        tranche.tranche_id
        for tranche in spec.tranches
        if not _is_null_tranche_type(tranche.tranche_type)
        and tranche.tranche_type != TrancheType.INTERACTION
    ]
    if existing is not None:
        if existing.null_dominance_tranche is not None and not existing.null_dominance_tranche.source_tranche_ids:
            existing.null_dominance_tranche.source_tranche_ids = list(source_ids)
        return None
    return TrancheSpec(
        tranche_id="auto_null_dominance",
        objective="Automatically mirror all hypothesis slices with deterministic null-dominance controls.",
        tranche_type=TrancheType.NULL_DOMINANCE_TRANCHE,
        tranche_objective=TrancheObjective.NULL_DOMINANCE_TEST,
        shared_profile=spec.shared_parameters.default_profile,
        sampling_strategy=TrancheSamplingStrategy.SOURCE_COPY,
        source_tranche_ids=list(source_ids),
        refinement_reason=RefinementReason.NULL_PAIR,
        null_dominance_tranche=NullDominanceTrancheFields(
            source_tranche_ids=list(source_ids),
            required=True,
        ),
    )


def _typed_tranche_fields(tranche: TrancheSpec | ResolvedTranchePlan) -> HypothesisTrancheBase | None:
    for field_name in [
        "discrimination_tranche",
        "scaling_law_tranche",
        "null_dominance_tranche",
        "identifiability_tranche",
        "discriminator_tranche",
        "failure_mode_tranche",
        "cross_device_tranche",
        "boundary_stress_tranche",
    ]:
        configured = getattr(tranche, field_name, None)
        if configured is not None:
            return cast(HypothesisTrancheBase, configured)
    return None


def _is_null_tranche_type(tranche_type: TrancheType) -> bool:
    return tranche_type in {TrancheType.NULL_MODEL, TrancheType.NULL_DOMINANCE_TRANCHE}


def _validate_resolved_plan(
    spec: SweepSpec,
    dataset: MMMDataset,
    tranches: list[ResolvedTranchePlan],
) -> PlanSufficiencyAssessment:
    hypothesis_tranches = [
        tranche
        for tranche in tranches
        if tranche.hypothesis_class not in {HypothesisClass.LEGACY, HypothesisClass.NULL_DOMINANCE}
    ]
    has_null = any(
        tranche.tranche_type == TrancheType.NULL_DOMINANCE_TRANCHE and tranche.slices
        for tranche in tranches
    )
    if (spec.require_null_dominance or spec.adaptive.enabled or hypothesis_tranches) and not has_null:
        raise SweepPlanningError("Resolved plan lacks NULL_DOMINANCE_TRANCHE coverage.")
    sufficiency = _build_plan_sufficiency(spec, tranches, hypothesis_tranches)
    if not sufficiency.passes:
        raise SweepPlanningError(
            "Resolved plan is structurally insufficient for adjudication: "
            + "; ".join(issue.message for issue in sufficiency.issues)
        )

    if spec.enforce_identifiability and not any(
        tranche.hypothesis_class == HypothesisClass.IDENTIFIABILITY for tranche in tranches
    ):
        raise SweepPlanningError("Identifiability enforcement requested without an identifiability tranche.")

    known_replication_ids = {row.replication_id for row in dataset.replication_matrix}
    for tranche in tranches:
        if tranche.tranche_type != TrancheType.CROSS_DEVICE_TRANCHE:
            continue
        fields = cast(CrossDeviceTrancheFields | None, tranche.cross_device_tranche)
        if fields is None:
            raise SweepPlanningError(
                f"Cross-device tranche '{tranche.tranche_id}' is missing typed cross-device fields."
            )
        unknown_replication_ids = sorted(set(fields.replication_ids) - known_replication_ids)
        if unknown_replication_ids:
            raise SweepPlanningError(
                f"Cross-device tranche '{tranche.tranche_id}' references unknown replication IDs: "
                + ", ".join(unknown_replication_ids)
            )
        if not tranche.slices:
            raise SweepPlanningError(
                f"Cross-device tranche '{tranche.tranche_id}' produced no deterministic slices."
            )

    duplicate_hashes: dict[str, set[HypothesisClass]] = {}
    for tranche in tranches:
        for slice_plan in tranche.slices:
            if slice_plan.parameter_hash is None:
                continue
            duplicate_hashes.setdefault(slice_plan.parameter_hash, set()).add(
                tranche.hypothesis_class
            )
            if slice_plan.parameter_count > slice_plan.observable_count > 0:
                raise SweepPlanningError(
                    f"Slice '{slice_plan.slice_id}' has parameter_count > observable_count."
                )
            if (
                spec.enforce_identifiability
                and slice_plan.hypothesis_class == HypothesisClass.IDENTIFIABILITY
                and slice_plan.observable_count == 0
            ):
                raise SweepPlanningError(
                    f"Identifiability slice '{slice_plan.slice_id}' must declare observable_count."
                )
    duplicated_across_classes = [
        parameter_hash
        for parameter_hash, tranche_types in duplicate_hashes.items()
        if len(tranche_types) > 1
    ]
    if duplicated_across_classes:
        raise SweepPlanningError(
            "Resolved plan produced duplicate parameter hashes across tranche classes."
        )
    _validate_null_lineage_locks(tranches)
    return sufficiency


def _build_plan_sufficiency(
    spec: SweepSpec,
    tranches: list[ResolvedTranchePlan],
    hypothesis_tranches: list[ResolvedTranchePlan],
) -> PlanSufficiencyAssessment:
    if not hypothesis_tranches:
        return PlanSufficiencyAssessment()
    orthogonal_families = {
        axis.axis_family or axis.field.value
        for tranche in hypothesis_tranches
        for axis in tranche.orthogonal_axes
    }
    null_tranches = [
        tranche for tranche in tranches if tranche.tranche_type == TrancheType.NULL_DOMINANCE_TRANCHE
    ]
    covered_sources = {
        source_tranche_id
        for tranche in null_tranches
        for source_tranche_id in tranche.source_tranche_ids
    }
    required_source_ids = {
        tranche.tranche_id
        for tranche in hypothesis_tranches
        if tranche.tranche_type != TrancheType.DISCRIMINATOR_TRANCHE
    }
    failure_mode_tranches = [
        tranche for tranche in tranches if tranche.tranche_type == TrancheType.FAILURE_MODE_TRANCHE
    ]
    discriminator_tranches = [
        tranche for tranche in tranches if tranche.tranche_type == TrancheType.DISCRIMINATOR_TRANCHE
    ]
    boundary_stress_tranches = [
        tranche for tranche in tranches if tranche.tranche_type == TrancheType.BOUNDARY_STRESS_TRANCHE
    ]
    cross_device_tranches = [
        tranche for tranche in tranches if tranche.tranche_type == TrancheType.CROSS_DEVICE_TRANCHE
    ]

    issues: list[SufficiencyIssue] = []
    if hypothesis_tranches and len(orthogonal_families) < spec.minimum_orthogonal_axes:
        issues.append(
            SufficiencyIssue(
                code=SufficiencyIssueCode.INSUFFICIENT_ORTHOGONAL_AXIS_DIVERSITY,
                message="Resolved plan lacks sufficient orthogonal axis family diversity.",
                tranche_ids=sorted(required_source_ids),
                observed_value=float(len(orthogonal_families)),
                required_value=float(spec.minimum_orthogonal_axes),
            )
        )
    if required_source_ids and (not null_tranches or covered_sources != required_source_ids):
        issues.append(
            SufficiencyIssue(
                code=SufficiencyIssueCode.INSUFFICIENT_NULL_DOMINANCE_COVERAGE,
                message="Resolved plan lacks sufficient null-dominance source coverage.",
                tranche_ids=sorted(required_source_ids - covered_sources),
                observed_value=float(len(covered_sources)),
                required_value=float(len(required_source_ids)),
            )
        )
    requires_failure_mode = any(
        tranche.hypothesis_class
        in {
            HypothesisClass.DISCRIMINATION,
            HypothesisClass.SCALING_LAW,
            HypothesisClass.IDENTIFIABILITY,
        }
        for tranche in hypothesis_tranches
    )
    if requires_failure_mode and not failure_mode_tranches:
        issues.append(
            SufficiencyIssue(
                code=SufficiencyIssueCode.INSUFFICIENT_FAILURE_MODE_OPPOSITION,
                message="Resolved plan lacks failure-mode opposition coverage.",
                tranche_ids=sorted(required_source_ids),
                observed_value=0.0,
                required_value=1.0,
            )
        )
    requires_boundary_stress = any(
        tranche.parameter_count >= tranche.observable_count > 0
        for tranche in hypothesis_tranches
    )
    if requires_boundary_stress and not boundary_stress_tranches:
        issues.append(
            SufficiencyIssue(
                code=SufficiencyIssueCode.INSUFFICIENT_BOUNDARY_STRESS_COVERAGE,
                message="Resolved plan lacks boundary-stress coverage for nontrivial claims.",
                tranche_ids=sorted(required_source_ids),
                observed_value=0.0,
                required_value=1.0,
            )
        )
    if spec.adaptive.robustness.enabled and hypothesis_tranches and not cross_device_tranches:
        issues.append(
            SufficiencyIssue(
                code=SufficiencyIssueCode.INSUFFICIENT_CROSS_DEVICE_COVERAGE,
                message="Resolved plan lacks cross-device coverage for requested robustness claims.",
                tranche_ids=sorted(required_source_ids),
                observed_value=0.0,
                required_value=1.0,
            )
        )
    requires_epistemic_falsifier = any(
        tranche.hypothesis_class
        in {
            HypothesisClass.DISCRIMINATION,
            HypothesisClass.SCALING_LAW,
            HypothesisClass.IDENTIFIABILITY,
        }
        for tranche in hypothesis_tranches
    )
    orthogonal_falsifier_present = bool(
        failure_mode_tranches or boundary_stress_tranches or discriminator_tranches
    )
    if requires_epistemic_falsifier and not orthogonal_falsifier_present:
        issues.append(
            SufficiencyIssue(
                code=SufficiencyIssueCode.MISSING_ORTHOGONAL_FALSIFIER,
                message="Resolved plan lacks an orthogonal falsifier or discriminator tranche.",
                tranche_ids=sorted(required_source_ids),
                observed_value=0.0,
                required_value=1.0,
            )
        )
    measurement_feasible = any(
        _predicted_measurement_gap(tranche, spec.measurement)
        >= _required_measurement_resolution(tranche, spec.measurement)
        for tranche in hypothesis_tranches
    ) or not hypothesis_tranches
    if not measurement_feasible:
        issues.append(
            SufficiencyIssue(
                code=SufficiencyIssueCode.MEASUREMENT_FEASIBILITY_FAILURE,
                message=(
                    "Resolved plan contains no tranche that can separate competing hypotheses "
                    "within the configured measurement envelope."
                ),
                tranche_ids=sorted(required_source_ids),
                observed_value=0.0,
                required_value=1.0,
            )
        )
    scaling_axis_separable = any(
        tranche.tranche_type in {TrancheType.SCALING_LAW_TRANCHE, TrancheType.DISCRIMINATOR_TRANCHE}
        and (
            tranche.expected_signature is not None
            or bool(tranche.orthogonal_axes)
            or any(axis.observable_name is not None for axis in tranche.orthogonal_axes)
        )
        for tranche in hypothesis_tranches + discriminator_tranches
    )
    if any(
        tranche.tranche_type in {TrancheType.SCALING_LAW_TRANCHE, TrancheType.DISCRIMINATOR_TRANCHE}
        for tranche in hypothesis_tranches + discriminator_tranches
    ) and not scaling_axis_separable:
        issues.append(
            SufficiencyIssue(
                code=SufficiencyIssueCode.INSUFFICIENT_SCALING_AXIS_SEPARABILITY,
                message="Resolved plan lacks a scaling-aware discriminator axis.",
                tranche_ids=sorted(required_source_ids),
                observed_value=0.0,
                required_value=1.0,
            )
        )

    return PlanSufficiencyAssessment(
        passes=not issues,
        orthogonal_axis_family_count=len(orthogonal_families),
        null_dominance_source_coverage=(
            len(covered_sources) / len(required_source_ids) if required_source_ids else 1.0
        ),
        failure_mode_coverage_count=len(failure_mode_tranches),
        boundary_stress_coverage_count=len(boundary_stress_tranches),
        cross_device_coverage_count=len(cross_device_tranches),
        discriminator_tranche_count=len(discriminator_tranches),
        orthogonal_falsifier_present=orthogonal_falsifier_present,
        measurement_feasible=measurement_feasible,
        scaling_axis_separable=scaling_axis_separable,
        issues=issues,
    )


def _required_measurement_resolution(
    tranche: ResolvedTranchePlan,
    measurement: MeasurementEquivalenceConfig,
) -> float:
    if tranche.discriminator_tranche is not None:
        return tranche.discriminator_tranche.required_resolution
    if tranche.identifiability_tranche is not None:
        return tranche.identifiability_tranche.resolution_threshold
    return _effective_measurement_resolution(measurement, "__default__")


def _predicted_measurement_gap(
    tranche: ResolvedTranchePlan,
    measurement: MeasurementEquivalenceConfig,
) -> float:
    if tranche.discriminator_tranche is not None:
        return tranche.discriminator_tranche.predicted_separation
    observable_signal = tranche.observable_count / max(tranche.parameter_count, 1)
    axis_signal = len(tranche.orthogonal_axes) / 4.0
    return clamp(max(observable_signal, axis_signal, measurement.observable_resolution))


def _validate_null_lineage_locks(tranches: list[ResolvedTranchePlan]) -> None:
    tranche_by_id = {tranche.tranche_id: tranche for tranche in tranches}
    for tranche in tranches:
        if tranche.tranche_type != TrancheType.NULL_DOMINANCE_TRANCHE:
            continue
        for slice_plan in tranche.slices:
            lock = slice_plan.lineage.null_lineage_lock
            if lock is None:
                raise SweepPlanningError(
                    f"Null-dominance slice '{slice_plan.slice_id}' is missing a lineage lock."
                )
            source_tranche = tranche_by_id.get(lock.source_tranche_id)
            if source_tranche is None:
                raise SweepPlanningError(
                    f"Null-dominance slice '{slice_plan.slice_id}' references unknown source tranche "
                    f"'{lock.source_tranche_id}'."
                )
            source_slice = next(
                (
                    candidate
                    for candidate in source_tranche.slices
                    if candidate.slice_id == lock.source_slice_id
                ),
                None,
            )
            if source_slice is None:
                raise SweepPlanningError(
                    f"Null-dominance slice '{slice_plan.slice_id}' references unknown source slice "
                    f"'{lock.source_slice_id}'."
                )
            if source_slice.parameter_hash != lock.source_parameter_hash:
                raise SweepPlanningError(
                    f"Null-dominance slice '{slice_plan.slice_id}' drifted from locked source "
                    f"parameter lineage."
                )
            if _candidate_id_hash(source_slice.candidate_ids) != lock.source_candidate_ids_sha256:
                raise SweepPlanningError(
                    f"Null-dominance slice '{slice_plan.slice_id}' drifted from locked source "
                    f"candidate lineage."
                )


def _resolved_plan_identity(tranches: list[ResolvedTranchePlan]) -> str:
    payload = []
    for tranche in sorted(tranches, key=lambda item: item.tranche_id):
        payload.append(
            {
                "tranche_id": tranche.tranche_id,
                "tranche_type": tranche.tranche_type.value,
                "hypothesis_class": tranche.hypothesis_class.value,
                "source_tranche_ids": sorted(tranche.source_tranche_ids),
                "slices": [
                    {
                        "slice_id": slice_plan.slice_id,
                        "parameter_hash": slice_plan.parameter_hash,
                        "null_pair_id": slice_plan.null_pair_id,
                        "parent_slice_id": slice_plan.parent_slice_id,
                        "null_lineage_lock": (
                            slice_plan.lineage.null_lineage_lock.model_dump(mode="json")
                            if slice_plan.lineage.null_lineage_lock is not None
                            else None
                        ),
                    }
                    for slice_plan in sorted(tranche.slices, key=lambda item: item.slice_id)
                ],
            }
        )
    return _sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))


def generate_discriminator_tranches_from_plan(
    plan: ResolvedSweepPlan,
    *,
    spec: SweepSpec,
    dataset: MMMDataset,
    output_root: Path,
) -> list[ResolvedTranchePlan]:
    if spec.measurement.max_discriminators_per_generation <= 0:
        return []
    resolved_by_id = {tranche.tranche_id: tranche for tranche in plan.tranches}
    provisional_results = {
        (slice_plan.tranche_id, slice_plan.slice_id): _rank_slice_candidates(
            dataset=dataset,
            profile=slice_plan.resolved_profile,
            candidate_ids=slice_plan.candidate_ids,
            null_model_enabled=spec.adaptive.null_model.enabled,
            baseline_mode=(
                spec.adaptive.null_model.mode.value if spec.adaptive.null_model.enabled else None
            ),
            baseline_profile=spec.adaptive.null_model.baseline_profile,
            tranche_type=slice_plan.tranche_type,
        )
        for tranche in plan.tranches
        if tranche.hypothesis_class
        not in {HypothesisClass.LEGACY, HypothesisClass.NULL_DOMINANCE}
        and tranche.tranche_type != TrancheType.DISCRIMINATOR_TRANCHE
        for slice_plan in tranche.slices
    }
    candidates = _pair_candidates_from_ranked_results(
        dataset=dataset,
        measurement=spec.measurement,
        ranked_results=provisional_results,
        slices_by_key={
            (slice_plan.tranche_id, slice_plan.slice_id): slice_plan
            for tranche in plan.tranches
            for slice_plan in tranche.slices
        },
        tranches_by_id=resolved_by_id,
    )
    generated: list[ResolvedTranchePlan] = []
    for candidate in candidates[: spec.measurement.max_discriminators_per_generation]:
        try:
            tranche_spec = _build_auto_discriminator_tranche_spec(
                candidate=candidate,
                source_tranches=resolved_by_id,
                measurement=spec.measurement,
                dataset=dataset,
                generation=1,
                cluster_id=f"preplan::{candidate.edge.edge_id}",
            )
        except SweepPlanningError:
            continue
        resolved = _resolve_tranche(
            spec,
            tranche_spec,
            dataset,
            output_root,
            resolved_tranches=resolved_by_id,
        )
        resolved_by_id[resolved.tranche_id] = resolved
        generated.append(resolved)
    return generated


def generate_discriminator_tranches_from_summary(
    manifest: SweepManifest,
    *,
    summary,
    dataset: MMMDataset,
    generation: int,
) -> list[ResolvedTranchePlan]:
    if generation > manifest.measurement.discriminator_generation_limit:
        return []
    resolved_by_id = {tranche.tranche_id: tranche for tranche in manifest.plan.tranches}
    candidate_by_pair: dict[tuple[str, str], AdversarialPairCandidate] = {}
    plan_slices = {
        (slice_plan.tranche_id, slice_plan.slice_id): slice_plan
        for tranche in manifest.plan.tranches
        for slice_plan in tranche.slices
    }
    weakest_edges = get_equivalence_edges(summary)
    for edge in sorted(
        weakest_edges,
        key=lambda item: (
            item.equivalence_margin,
            -_slice_pair_prior_plausibility(
                plan_slices.get((item.left_tranche_id, item.left_slice_id)),
                plan_slices.get((item.right_tranche_id, item.right_slice_id)),
            ),
            _stable_hash_token(item.edge_id),
        ),
    ):
        if edge.equivalence_margin >= 1.0:
            continue
        pair_key = tuple(sorted([edge.left_tranche_id, edge.right_tranche_id]))
        if pair_key in candidate_by_pair:
            continue
        left_plan = _resolve_edge_slice(
            plan_slices=plan_slices,
            tranches_by_id=resolved_by_id,
            tranche_id=edge.left_tranche_id,
            slice_id=edge.left_slice_id,
            allow_legacy_downgrade=getattr(summary, "legacy_contract_downgrade", False),
        )
        right_plan = _resolve_edge_slice(
            plan_slices=plan_slices,
            tranches_by_id=resolved_by_id,
            tranche_id=edge.right_tranche_id,
            slice_id=edge.right_slice_id,
            allow_legacy_downgrade=getattr(summary, "legacy_contract_downgrade", False),
        )
        if left_plan is None or right_plan is None:
            continue
        left_genome = _top_genome_for_slice_summary(summary, edge.left_tranche_id, edge.left_slice_id)
        right_genome = _top_genome_for_slice_summary(
            summary, edge.right_tranche_id, edge.right_slice_id
        )
        if left_genome is None:
            left_genome = left_plan.candidate_ids[0] if left_plan.candidate_ids else None
        if right_genome is None:
            right_genome = right_plan.candidate_ids[0] if right_plan.candidate_ids else None
        if left_genome is None or right_genome is None:
            continue
        candidate_by_pair[pair_key] = AdversarialPairCandidate(
            edge=edge,
            pair_key=pair_key,
            prior_plausibility=_slice_pair_prior_plausibility(left_plan, right_plan),
            left_genome_id=left_genome,
            right_genome_id=right_genome,
        )
    generated: list[ResolvedTranchePlan] = []
    for candidate in sorted(
        candidate_by_pair.values(),
        key=lambda item: (
            item.edge.equivalence_margin,
            -item.prior_plausibility,
            _stable_hash_token(item.edge.edge_id),
        ),
    )[: manifest.measurement.max_discriminators_per_generation]:
        try:
            tranche_spec = _build_auto_discriminator_tranche_spec(
                candidate=candidate,
                source_tranches=resolved_by_id,
                measurement=manifest.measurement,
                dataset=dataset,
                generation=generation,
                cluster_id=_cluster_id_for_edge(summary, candidate.edge),
            )
        except SweepPlanningError:
            continue
        resolved = _resolve_tranche(
            _sweep_spec_from_manifest(manifest),
            tranche_spec,
            dataset,
            Path(manifest.output_root),
            resolved_tranches=resolved_by_id,
        )
        resolved_by_id[resolved.tranche_id] = resolved
        generated.append(resolved)
    return generated


def _pair_candidates_from_ranked_results(
    *,
    dataset: MMMDataset,
    measurement: MeasurementEquivalenceConfig,
    ranked_results: dict[tuple[str, str], list[ScoreResult]],
    slices_by_key: dict[tuple[str, str], ResolvedSlicePlan],
    tranches_by_id: dict[str, ResolvedTranchePlan],
) -> list[AdversarialPairCandidate]:
    best_by_pair: dict[tuple[str, str], AdversarialPairCandidate] = {}
    eligible_keys = sorted(ranked_results)
    for left_key, right_key in combinations(eligible_keys, 2):
        left_slice = slices_by_key[left_key]
        right_slice = slices_by_key[right_key]
        if left_slice.tranche_id == right_slice.tranche_id:
            continue
        pair_key = tuple(sorted([left_slice.tranche_id, right_slice.tranche_id]))
        if _pair_has_existing_discriminator(pair_key, tranches_by_id):
            continue
        left_results = ranked_results[left_key]
        right_results = ranked_results[right_key]
        if not left_results or not right_results:
            continue
        edge = _build_equivalence_edge(
            left_tranche=tranches_by_id[left_slice.tranche_id],
            left_slice=left_slice,
            right_tranche=tranches_by_id[right_slice.tranche_id],
            right_slice=right_slice,
            left_genome_id=left_results[0].genome_id,
            right_genome_id=right_results[0].genome_id,
            dataset=dataset,
            measurement=measurement,
        )
        if edge.equivalence_margin >= 1.0:
            continue
        candidate = AdversarialPairCandidate(
            edge=edge,
            pair_key=pair_key,
            prior_plausibility=_slice_pair_prior_plausibility(left_slice, right_slice),
            left_genome_id=left_results[0].genome_id,
            right_genome_id=right_results[0].genome_id,
        )
        current = best_by_pair.get(pair_key)
        if current is None or _pair_candidate_sort_key(candidate) < _pair_candidate_sort_key(current):
            best_by_pair[pair_key] = candidate
    return sorted(best_by_pair.values(), key=_pair_candidate_sort_key)


def _pair_has_existing_discriminator(
    pair_key: tuple[str, str],
    tranches_by_id: dict[str, ResolvedTranchePlan],
) -> bool:
    return any(
        tranche.discriminator_tranche is not None
        and tuple(sorted(tranche.discriminator_tranche.target_hypothesis_pair)) == pair_key
        for tranche in tranches_by_id.values()
    )


def _pair_candidate_sort_key(candidate: AdversarialPairCandidate) -> tuple[float, float, str]:
    return (
        candidate.edge.equivalence_margin,
        -candidate.prior_plausibility,
        _stable_hash_token(candidate.edge.edge_id),
    )


def _slice_pair_prior_plausibility(
    left: ResolvedSlicePlan | None,
    right: ResolvedSlicePlan | None,
) -> float:
    if left is None or right is None:
        return 0.0
    overlap = _candidate_jaccard(left.candidate_ids, right.candidate_ids)
    return clamp(
        0.45 * ((left.utility.utility_score + right.utility.utility_score) / 2.0)
        + 0.35 * overlap
        + 0.20 * (1.0 - max(left.utility.parameter_penalty_score, right.utility.parameter_penalty_score))
    )


def _build_equivalence_edge(
    *,
    left_tranche: ResolvedTranchePlan,
    left_slice: ResolvedSlicePlan,
    right_tranche: ResolvedTranchePlan,
    right_slice: ResolvedSlicePlan,
    left_genome_id: str,
    right_genome_id: str,
    dataset: MMMDataset,
    measurement: MeasurementEquivalenceConfig,
) -> EquivalenceEdge:
    left_obs = genome_numeric_observables(dataset.genome_index[left_genome_id])
    right_obs = genome_numeric_observables(dataset.genome_index[right_genome_id])
    shared_observables = sorted(set(left_obs) & set(right_obs))
    if shared_observables:
        margin = max(
            abs(left_obs[name] - right_obs[name])
            / _effective_measurement_resolution(measurement, name)
            for name in shared_observables
        )
    else:
        margin = 0.0
    return EquivalenceEdge(
        edge_id=(
            f"{left_slice.tranche_id}:{left_slice.slice_id}__"
            f"{right_slice.tranche_id}:{right_slice.slice_id}"
        ),
        left_tranche_id=left_slice.tranche_id,
        left_slice_id=left_slice.slice_id,
        right_tranche_id=right_slice.tranche_id,
        right_slice_id=right_slice.slice_id,
        left_hypothesis_class=left_tranche.hypothesis_class,
        right_hypothesis_class=right_tranche.hypothesis_class,
        equivalence_margin=margin,
        measurement_equivalence_score=_legacy_measurement_equivalence_score(margin),
        tested_axes=["observable_envelope"],
    )


def _effective_measurement_resolution(
    measurement: MeasurementEquivalenceConfig,
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


def _build_auto_discriminator_tranche_spec(
    *,
    candidate: AdversarialPairCandidate,
    source_tranches: dict[str, ResolvedTranchePlan],
    measurement: MeasurementEquivalenceConfig,
    dataset: MMMDataset,
    generation: int,
    cluster_id: str,
) -> TrancheSpec:
    left = source_tranches[candidate.pair_key[0]]
    right = source_tranches[candidate.pair_key[1]]
    ranked_axes = _rank_discriminator_axes_for_pair(
        left=left,
        right=right,
        left_genome_id=candidate.left_genome_id,
        right_genome_id=candidate.right_genome_id,
        measurement=measurement,
        dataset=dataset,
        source_tranches=source_tranches,
    )
    rejected_axes = _rejected_discriminator_axes_for_pair(
        left=left,
        right=right,
        left_genome_id=candidate.left_genome_id,
        right_genome_id=candidate.right_genome_id,
        measurement=measurement,
        dataset=dataset,
        source_tranches=source_tranches,
    )
    if not ranked_axes or ranked_axes[0].discriminator_gain <= measurement.discriminator_gain_threshold:
        raise SweepPlanningError(
            "No deterministic discriminator axis exceeded the configured gain threshold."
        )
    primary_axis = ranked_axes[0]
    support_axis = _secondary_support_axis(primary_axis, ranked_axes)
    orthogonal_axes = [primary_axis.axis]
    if support_axis is not None:
        orthogonal_axes.append(support_axis.axis)
    required_resolution = _effective_measurement_resolution(
        measurement,
        primary_axis.axis.observable_name or primary_axis.axis_key,
    )
    tranche_id = f"auto_discriminator_g{generation}_{candidate.pair_key[0]}_{candidate.pair_key[1]}"
    return TrancheSpec(
        tranche_id=tranche_id,
        objective=(
            f"Adversarially separate {candidate.pair_key[0]} from {candidate.pair_key[1]} "
            f"for edge {candidate.edge.left_slice_id} vs {candidate.edge.right_slice_id}."
        ),
        tranche_type=TrancheType.DISCRIMINATOR_TRANCHE,
        tranche_objective=TrancheObjective.ADVERSARIAL_DISCRIMINATION,
        shared_profile=sorted([left.shared_profile, right.shared_profile])[0],
        sampling_strategy=TrancheSamplingStrategy.GRID,
        source_tranche_ids=list(candidate.pair_key),
        refinement_reason=RefinementReason.ADAPTIVE_REFINEMENT,
        discriminator_tranche=DiscriminatorTrancheFields(
            target_hypothesis_pair=list(candidate.pair_key),
            discriminator_axis=primary_axis.axis_key,
            expected_separation_signature=(
                f"{primary_axis.axis_key}_split_for_{candidate.edge.left_slice_id}"
                f"_vs_{candidate.edge.right_slice_id}"
            ),
            required_resolution=required_resolution,
            originating_equivalence_cluster=cluster_id,
            discriminator_rationale=(
                "Injected for the lowest-margin equivalent pair with deterministic "
                "observable-scaling separation gain."
            ),
            predicted_separation=primary_axis.expected_separation,
            discriminator_gain=primary_axis.discriminator_gain,
            axis_cost=primary_axis.axis_cost,
            redundancy_penalty=primary_axis.redundancy_penalty,
            generation=generation,
            orthogonal_axes=orthogonal_axes,
            parameter_count=max(left.parameter_count, right.parameter_count),
            observable_count=max(left.observable_count, right.observable_count, 1),
            tested_axes=[candidate.axis_key for candidate in ranked_axes],
            tested_discriminator_axes=[candidate.axis_key for candidate in ranked_axes],
            rejected_axes=[
                RejectedAxisRationale(
                    axis_key=item.axis_key,
                    reason=item.reason,
                    redundancy_penalty=item.redundancy_penalty,
                    correlation=item.correlation,
                    blocking_axis=item.blocking_axis,
                )
                for item in rejected_axes
            ],
            rejected_discriminator_axes=[item.axis_key for item in rejected_axes],
            rejected_axis_rationale=[
                RejectedAxisRationale(
                    axis_key=item.axis_key,
                    reason=item.reason,
                    redundancy_penalty=item.redundancy_penalty,
                    correlation=item.correlation,
                    blocking_axis=item.blocking_axis,
                )
                for item in rejected_axes
            ],
        ),
    )


def _rank_discriminator_axes_for_pair(
    *,
    left: ResolvedTranchePlan,
    right: ResolvedTranchePlan,
    left_genome_id: str,
    right_genome_id: str,
    measurement: MeasurementEquivalenceConfig,
    dataset: MMMDataset,
    source_tranches: dict[str, ResolvedTranchePlan],
) -> list[AxisGainCandidate]:
    combined = _candidate_discriminator_axes(left=left, right=right)
    history = _axis_history_for_pair(
        pair_key=tuple(sorted([left.tranche_id, right.tranche_id])),
        left_genome_id=left_genome_id,
        right_genome_id=right_genome_id,
        dataset=dataset,
        source_tranches=source_tranches,
    )
    ranked, _ = _score_discriminator_axes(
        axes=combined,
        history=history,
        left=left,
        right=right,
        left_genome_id=left_genome_id,
        right_genome_id=right_genome_id,
        measurement=measurement,
        dataset=dataset,
    )
    return ranked


def _rejected_discriminator_axes_for_pair(
    *,
    left: ResolvedTranchePlan,
    right: ResolvedTranchePlan,
    left_genome_id: str,
    right_genome_id: str,
    measurement: MeasurementEquivalenceConfig,
    dataset: MMMDataset,
    source_tranches: dict[str, ResolvedTranchePlan],
) -> list[RejectedAxisCandidate]:
    combined = _candidate_discriminator_axes(left=left, right=right)
    history = _axis_history_for_pair(
        pair_key=tuple(sorted([left.tranche_id, right.tranche_id])),
        left_genome_id=left_genome_id,
        right_genome_id=right_genome_id,
        dataset=dataset,
        source_tranches=source_tranches,
    )
    _, rejected = _score_discriminator_axes(
        axes=combined,
        history=history,
        left=left,
        right=right,
        left_genome_id=left_genome_id,
        right_genome_id=right_genome_id,
        measurement=measurement,
        dataset=dataset,
    )
    return rejected


def _candidate_discriminator_axes(
    *,
    left: ResolvedTranchePlan,
    right: ResolvedTranchePlan,
) -> list[OrthogonalAxis]:
    combined = [
        axis.model_copy(deep=True)
        for axis in [*left.orthogonal_axes, *right.orthogonal_axes]
        if len(axis.values) >= 2
    ]
    if not combined:
        primary = _fallback_discriminator_axis(exclude=set())
        secondary = _fallback_discriminator_axis(exclude={primary.field})
        combined = [primary, secondary]
    deduped: list[OrthogonalAxis] = []
    seen: set[tuple[str, str, str]] = set()
    for axis in combined + [
        _fallback_discriminator_axis(exclude={axis.field for axis in combined}),
        _fallback_discriminator_axis(exclude=set()),
    ]:
        key = (axis.axis_id, axis.axis_family or axis.field.value, axis.field.value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(axis)
    return deduped


def _score_discriminator_axes(
    *,
    axes: list[OrthogonalAxis],
    history: list[tuple[str, list[float]]],
    left: ResolvedTranchePlan,
    right: ResolvedTranchePlan,
    left_genome_id: str,
    right_genome_id: str,
    measurement: MeasurementEquivalenceConfig,
    dataset: MMMDataset,
) -> tuple[list[AxisGainCandidate], list[RejectedAxisCandidate]]:
    ranked: list[AxisGainCandidate] = []
    rejected: list[RejectedAxisCandidate] = []
    for axis in axes:
        axis_key = _semantic_discriminator_axis(axis)
        expected_separation = _expected_axis_separation(
            dataset=dataset,
            left_genome_id=left_genome_id,
            right_genome_id=right_genome_id,
            axis_key=axis_key,
            left_tranche=left,
            right_tranche=right,
        )
        axis_cost = _axis_cost(axis)
        redundancy_penalty, redundant = _axis_redundancy_penalty(
            axis_key=axis_key,
            history=history,
            left_genome_id=left_genome_id,
            right_genome_id=right_genome_id,
            dataset=dataset,
            threshold=measurement.axis_correlation_threshold,
            left_tranche=left,
            right_tranche=right,
        )
        if redundant:
            signature = _axis_signature_for_pair(
                dataset=dataset,
                left_genome_id=left_genome_id,
                right_genome_id=right_genome_id,
                axis_key=axis_key,
                left_tranche=left,
                right_tranche=right,
            )
            rejected.append(
                RejectedAxisCandidate(
                    axis_key=axis_key,
                    reason="orthogonality_rejected",
                    redundancy_penalty=redundancy_penalty,
                    correlation=redundancy_penalty,
                    blocking_axis=_blocking_axis_for_signature(
                        signature=signature,
                        history=history,
                    ),
                )
            )
            continue
        gain = expected_separation - axis_cost - redundancy_penalty
        ranked.append(
            AxisGainCandidate(
                axis=axis.model_copy(deep=True),
                axis_key=axis_key,
                expected_separation=expected_separation,
                discriminator_gain=gain,
                axis_cost=axis_cost,
                redundancy_penalty=redundancy_penalty,
            )
        )
    return (
        sorted(
            ranked,
            key=lambda item: (
                -item.discriminator_gain,
                item.axis_cost,
                _discriminator_axis_priority(item.axis),
                _stable_hash_token(item.axis.axis_id, item.axis_key),
            ),
        ),
        sorted(
            rejected,
            key=lambda item: (
                item.axis_key,
                item.blocking_axis or "",
                item.reason,
            ),
        ),
    )


def _secondary_support_axis(
    primary: AxisGainCandidate,
    ranked: list[AxisGainCandidate],
) -> AxisGainCandidate | None:
    for candidate in ranked[1:]:
        if candidate.axis_key == primary.axis_key:
            continue
        return candidate
    return None


def _discriminator_axis_priority(axis: OrthogonalAxis) -> tuple[int, str]:
    semantic = _semantic_discriminator_axis(axis)
    priority = {
        "temperature": 0,
        "drive_amplitude": 1,
        "geometry": 2,
        "time_evolution": 3,
    }.get(semantic, 4)
    return priority, semantic


def _semantic_discriminator_axis(axis: OrthogonalAxis) -> str:
    token = f"{axis.axis_id}::{axis.axis_family or axis.field.value}".lower()
    if "temp" in token or "ghz" in token:
        return "temperature"
    if "drive" in token or axis.field == CandidateFilterField.NULL_RISK:
        return "drive_amplitude"
    if "screening" in token or "cleanroom" in token:
        return "time_evolution"
    return "geometry"


def _fallback_discriminator_axis(
    *,
    exclude: set[CandidateFilterField],
) -> OrthogonalAxis:
    options = [
        (
            CandidateFilterField.FABRICATION_COMPLEXITY,
            FilterOperator.LTE,
            [6, 8],
            "geometry",
        ),
        (
            CandidateFilterField.NULL_RISK,
            FilterOperator.LTE,
            [4, 6],
            "drive_amplitude",
        ),
        (
            CandidateFilterField.SCREENING_STATUS,
            FilterOperator.EQ,
            ["screening", "sandbox"],
            "time_evolution",
        ),
    ]
    for field, operator, values, axis_id in options:
        if field in exclude:
            continue
        return OrthogonalAxis(
            axis_id=axis_id,
            field=field,
            operator=operator,
            values=values,
            axis_family=axis_id,
        )
    raise SweepPlanningError("Unable to construct a deterministic fallback discriminator axis.")


def _axis_history_for_pair(
    *,
    pair_key: tuple[str, str],
    left_genome_id: str,
    right_genome_id: str,
    dataset: MMMDataset,
    source_tranches: dict[str, ResolvedTranchePlan],
) -> list[tuple[str, list[float]]]:
    history: list[tuple[str, list[float]]] = []
    for tranche in source_tranches.values():
        fields = tranche.discriminator_tranche
        if fields is None:
            continue
        if tuple(sorted(fields.target_hypothesis_pair)) != pair_key:
            continue
        axis_key = fields.discriminator_axis
        history.append(
            (
                axis_key,
                _axis_signature_for_pair(
                    dataset=dataset,
                    left_genome_id=left_genome_id,
                    right_genome_id=right_genome_id,
                    axis_key=axis_key,
                    left_tranche=source_tranches[pair_key[0]],
                    right_tranche=source_tranches[pair_key[1]],
                ),
            )
        )
    return history


def _expected_axis_separation(
    *,
    dataset: MMMDataset,
    left_genome_id: str,
    right_genome_id: str,
    axis_key: str,
    left_tranche: ResolvedTranchePlan | None = None,
    right_tranche: ResolvedTranchePlan | None = None,
) -> float:
    left_trace = _trace_for_axis_key(axis_key, _predicted_axes_for_genome(dataset, left_genome_id))
    right_trace = _trace_for_axis_key(axis_key, _predicted_axes_for_genome(dataset, right_genome_id))
    genome_separation = 0.0
    if left_trace and right_trace:
        genome_separation = max(
            abs(left - right) for left, right in zip(left_trace, right_trace, strict=True)
        )
    tranche_separation = 0.0
    if left_tranche is not None and right_tranche is not None:
        left_fallback = _trace_for_axis_key(axis_key, _predicted_axes_for_tranche(left_tranche))
        right_fallback = _trace_for_axis_key(axis_key, _predicted_axes_for_tranche(right_tranche))
        if left_fallback and right_fallback:
            tranche_separation = max(
                abs(left - right)
                for left, right in zip(left_fallback, right_fallback, strict=True)
            )
    observable_floor = 0.0
    if left_tranche is not None and right_tranche is not None:
        observable_floor = _observable_scaling_floor(left_tranche, right_tranche, axis_key)
    return max(genome_separation, tranche_separation, observable_floor)


def _axis_cost(axis: OrthogonalAxis) -> float:
    semantic = _semantic_discriminator_axis(axis)
    base = {
        "geometry": 0.05,
        "drive_amplitude": 0.07,
        "temperature": 0.09,
        "time_evolution": 0.11,
    }.get(semantic, 0.08)
    return base + (0.01 * max(0, len(axis.values) - 2))


def _axis_redundancy_penalty(
    *,
    axis_key: str,
    history: list[tuple[str, list[float]]],
    left_genome_id: str,
    right_genome_id: str,
    dataset: MMMDataset,
    threshold: float,
    left_tranche: ResolvedTranchePlan | None = None,
    right_tranche: ResolvedTranchePlan | None = None,
) -> tuple[float, bool]:
    if not history:
        return 0.0, False
    signature = _axis_signature_for_pair(
        dataset=dataset,
        left_genome_id=left_genome_id,
        right_genome_id=right_genome_id,
        axis_key=axis_key,
        left_tranche=left_tranche,
        right_tranche=right_tranche,
    )
    correlations = [
        _absolute_correlation(signature, prior_signature) for _, prior_signature in history
    ]
    max_correlation = max(correlations, default=0.0)
    return max_correlation, max_correlation >= threshold


def _blocking_axis_for_signature(
    *,
    signature: list[float],
    history: list[tuple[str, list[float]]],
) -> str | None:
    ranked = sorted(
        (
            (_absolute_correlation(signature, prior_signature), axis_key)
            for axis_key, prior_signature in history
        ),
        key=lambda item: (-item[0], item[1]),
    )
    return ranked[0][1] if ranked else None


def _axis_signature_for_pair(
    *,
    dataset: MMMDataset,
    left_genome_id: str,
    right_genome_id: str,
    axis_key: str,
    left_tranche: ResolvedTranchePlan | None = None,
    right_tranche: ResolvedTranchePlan | None = None,
) -> list[float]:
    left_axes = _predicted_axes_for_genome(dataset, left_genome_id)
    right_axes = _predicted_axes_for_genome(dataset, right_genome_id)
    left_trace = _trace_for_axis_key(axis_key, left_axes)
    right_trace = _trace_for_axis_key(axis_key, right_axes)
    signature = _axis_signature_from_key(
        axis_key=axis_key,
        left_trace=left_trace,
        right_trace=right_trace,
    )
    if any(abs(value) > 1e-9 for value in signature):
        return signature
    if left_tranche is None or right_tranche is None:
        return signature
    left_fallback = _trace_for_axis_key(axis_key, _predicted_axes_for_tranche(left_tranche))
    right_fallback = _trace_for_axis_key(axis_key, _predicted_axes_for_tranche(right_tranche))
    return _axis_signature_from_key(
        axis_key=axis_key,
        left_trace=left_fallback,
        right_trace=right_fallback,
    )


def _resolve_edge_slice(
    *,
    plan_slices: dict[tuple[str, str], ResolvedSlicePlan],
    tranches_by_id: dict[str, ResolvedTranchePlan],
    tranche_id: str,
    slice_id: str,
    allow_legacy_downgrade: bool,
) -> ResolvedSlicePlan | None:
    plan = plan_slices.get((tranche_id, slice_id))
    if plan is not None:
        return plan
    tranche = tranches_by_id.get(tranche_id)
    if tranche is not None:
        for candidate in tranche.slices:
            if candidate.slice_id == slice_id:
                return candidate
    if not allow_legacy_downgrade:
        return None
    if (
        tranche is not None
        and slice_id == tranche_id
        and tranche.slices
    ):
        return sorted(tranche.slices, key=lambda item: item.slice_id)[0]
    return None


def _predicted_axes_for_tranche(tranche: ResolvedTranchePlan) -> dict[str, list[float]]:
    descriptor = _tranche_scaling_descriptor(tranche)
    observable_anchor = clamp(tranche.observable_count / max(tranche.parameter_count * 2.0, 1.0))
    parameter_anchor = clamp(tranche.parameter_count / 10.0)
    return {
        "geometry": _project_semantic_axis_trace(
            axis_key="geometry",
            descriptor=descriptor,
            axis_points=[0.0, 0.5, 1.0],
            observable_anchor=observable_anchor,
            parameter_anchor=parameter_anchor,
            variant_token=tranche.tranche_id,
        ),
        "temperature": _project_semantic_axis_trace(
            axis_key="temperature",
            descriptor=descriptor,
            axis_points=[0.0, 0.5, 1.0],
            observable_anchor=observable_anchor,
            parameter_anchor=parameter_anchor,
            variant_token=tranche.tranche_id,
        ),
        "drive_amplitude": _project_semantic_axis_trace(
            axis_key="drive_amplitude",
            descriptor=descriptor,
            axis_points=[0.0, 0.5, 1.0],
            observable_anchor=observable_anchor,
            parameter_anchor=parameter_anchor,
            variant_token=tranche.tranche_id,
        ),
        "time_evolution": _project_semantic_axis_trace(
            axis_key="time_evolution",
            descriptor=descriptor,
            axis_points=[0.0, 0.25, 0.5, 0.75, 1.0],
            observable_anchor=observable_anchor,
            parameter_anchor=parameter_anchor,
            variant_token=tranche.tranche_id,
        ),
    }


def _observable_scaling_floor(
    left: ResolvedTranchePlan,
    right: ResolvedTranchePlan,
    axis_key: str,
) -> float:
    observability = max(left.observable_count, right.observable_count, 1)
    complexity = max(left.parameter_count, right.parameter_count, 1)
    coverage = observability / complexity
    base = {
        "geometry": 0.06,
        "drive_amplitude": 0.08,
        "temperature": 0.07,
        "time_evolution": 0.05,
    }.get(axis_key, 0.06)
    return min(0.30, 0.06 + (base * coverage))


def _tranche_scaling_descriptor(tranche: ResolvedTranchePlan) -> str:
    parts = [tranche.tranche_id, tranche.objective or ""]
    if tranche.expected_signature is not None:
        parts.extend(
            [
                tranche.expected_signature.label or "",
                tranche.expected_signature.observable_name or "",
                tranche.expected_signature.scaling_type.value,
            ]
        )
    if tranche.discrimination_tranche is not None:
        parts.append(tranche.discrimination_tranche.primary_hypothesis)
        parts.extend(tranche.discrimination_tranche.comparator_hypotheses)
    if tranche.scaling_law_tranche is not None:
        parts.extend(
            [
                tranche.scaling_law_tranche.scaling_axis_id,
                tranche.scaling_law_tranche.observable_name,
                tranche.scaling_law_tranche.expected_scaling_type.value,
            ]
        )
    if tranche.discriminator_tranche is not None:
        parts.extend(
            [
                *tranche.discriminator_tranche.target_hypothesis_pair,
                tranche.discriminator_tranche.discriminator_axis,
                tranche.discriminator_tranche.expected_separation_signature,
            ]
        )
    return " ".join(part for part in parts if part)


def _project_semantic_axis_trace(
    *,
    axis_key: str,
    descriptor: str,
    axis_points: list[float],
    observable_anchor: float,
    parameter_anchor: float,
    variant_token: str,
) -> list[float]:
    scaling_type = infer_expected_scaling_type(f"{axis_key} {descriptor}")
    template = [_scaling_template_value(scaling_type, point) for point in axis_points]
    token = _stable_hash_token(axis_key, descriptor, variant_token)
    seed = int(token[:12], 16)
    offset = (((seed % 1000) / 999.0) - 0.5) * 0.10
    gain = 0.85 + ((((seed // 1000) % 1000) / 999.0) * 0.30)
    neutral_direction = -1.0 if ((seed // 1000000) % 2) else 1.0
    direction = (
        -1.0
        if any(
            token in descriptor.lower()
            for token in ["decrease", "decreases", "decay", "weakens", "collapse", "lower"]
        )
        else neutral_direction
    )
    base = clamp(0.18 + (0.42 * observable_anchor) + (0.18 * parameter_anchor) + offset)
    amplitude = 0.10 + (0.20 * observable_anchor) + (0.08 * parameter_anchor)
    return [clamp(base + (direction * amplitude * gain * value)) for value in template]


def _axis_signature_from_key(
    *,
    axis_key: str,
    left_trace: list[float] | None,
    right_trace: list[float] | None,
) -> list[float]:
    del axis_key
    if not left_trace or not right_trace:
        return [0.0]
    limit = min(len(left_trace), len(right_trace))
    return [
        left_trace[index] - right_trace[index]
        for index in range(limit)
    ]


def _trace_for_axis_key(
    axis_key: str,
    predicted_axes: dict[str, list[float]] | None,
) -> list[float] | None:
    if predicted_axes is None:
        return None
    if axis_key in predicted_axes:
        return predicted_axes[axis_key]
    fallback = {
        "drive": "drive_amplitude",
        "time": "time_evolution",
    }.get(axis_key)
    if fallback is not None:
        return predicted_axes.get(fallback)
    return predicted_axes.get("geometry", predicted_axes.get("temperature"))


def _absolute_correlation(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 1.0 if left == right else 0.0
    left_mean = mean(left)
    right_mean = mean(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    numerator = sum(
        left_value * right_value
        for left_value, right_value in zip(left_centered, right_centered, strict=True)
    )
    left_norm = math.sqrt(sum(value * value for value in left_centered))
    right_norm = math.sqrt(sum(value * value for value in right_centered))
    if left_norm <= 1e-12 or right_norm <= 1e-12:
        return 1.0 if left == right else 0.0
    return abs(numerator / (left_norm * right_norm))


def _stable_hash_token(*parts: object) -> str:
    payload = "::".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _top_genome_for_slice_summary(summary: object, tranche_id: str, slice_id: str) -> str | None:
    for winner in getattr(summary, "per_slice_winners", []):
        if winner.tranche_id == tranche_id and winner.slice_id == slice_id:
            return winner.candidate_id
    return None


def _cluster_id_for_edge(summary: object, edge: EquivalenceEdge) -> str:
    for cluster in getattr(summary, "equivalence_clusters", []):
        slice_ids = set(getattr(cluster, "slice_ids", []))
        if {edge.left_slice_id, edge.right_slice_id}.issubset(slice_ids):
            return cluster.cluster_id
        tranche_ids = set(getattr(cluster, "tranche_ids", []))
        if {edge.left_tranche_id, edge.right_tranche_id}.issubset(tranche_ids):
            return cluster.cluster_id
    for cluster in getattr(getattr(summary, "adjudication", None), "equivalence_clusters", []):
        slice_ids = set(getattr(cluster, "slice_ids", []))
        if {edge.left_slice_id, edge.right_slice_id}.issubset(slice_ids):
            return cluster.cluster_id
        tranche_ids = set(getattr(cluster, "tranche_ids", []))
        if {edge.left_tranche_id, edge.right_tranche_id}.issubset(tranche_ids):
            return cluster.cluster_id
    return f"edge::{edge.edge_id}"


def _sweep_spec_from_manifest(manifest: SweepManifest) -> SweepSpec:
    return SweepSpec(
        name=manifest.sweep_name,
        description=manifest.description,
        version=manifest.spec_version,
        default_output_root=manifest.output_root,
        shared_parameters=manifest.plan.tranches[0].slices[0].resolved_parameters
        if manifest.plan.tranches and manifest.plan.tranches[0].slices
        else SweepExecutionParameters(),
        residual_weights=manifest.residual_weights.model_copy(deep=True),
        identifiability_threshold=manifest.identifiability_threshold,
        scaling_tolerance=manifest.scaling_tolerance,
        null_model_tolerance=manifest.null_model_tolerance,
        measurement=manifest.measurement.model_copy(deep=True),
        adaptive=manifest.adaptive.model_copy(deep=True),
        tranches=[],
    )

def build_slices_from_tranche(
    spec: SweepSpec,
    tranche: TrancheSpec,
    resolved_tranches: dict[str, ResolvedTranchePlan],
    dataset: MMMDataset | None = None,
) -> list[SliceSpec]:
    explicit = [_merge_slice_defaults(spec, tranche, slice_spec) for slice_spec in tranche.slices]
    if explicit:
        return _dedupe_slice_specs(explicit)

    typed_generated = _build_typed_hypothesis_slices(spec, tranche, resolved_tranches, dataset)
    if typed_generated:
        return _dedupe_slice_specs(typed_generated)

    if tranche.sampling_strategy == TrancheSamplingStrategy.SOURCE_COPY:
        return _dedupe_slice_specs(_copy_source_slices(spec, tranche, resolved_tranches))
    if tranche.tranche_type == TrancheType.INTERACTION:
        return []
    generated = _build_controlled_slices(spec, tranche)
    if generated:
        return _dedupe_slice_specs(generated)
    return _dedupe_slice_specs(_copy_source_slices(spec, tranche, resolved_tranches))


def _build_typed_hypothesis_slices(
    spec: SweepSpec,
    tranche: TrancheSpec,
    resolved_tranches: dict[str, ResolvedTranchePlan],
    dataset: MMMDataset | None,
) -> list[SliceSpec]:
    match tranche.tranche_type:
        case TrancheType.DISCRIMINATION_TRANCHE:
            fields = cast(DiscriminationTrancheFields, tranche.discrimination_tranche)
            return _build_orthogonal_axis_slices(spec, tranche, fields)
        case TrancheType.SCALING_LAW_TRANCHE:
            fields = cast(ScalingLawTrancheFields, tranche.scaling_law_tranche)
            return _build_scaling_law_slices(spec, tranche, fields)
        case TrancheType.NULL_DOMINANCE_TRANCHE:
            return _copy_source_slices(spec, tranche, resolved_tranches)
        case TrancheType.IDENTIFIABILITY_TRANCHE:
            fields = cast(IdentifiabilityTrancheFields, tranche.identifiability_tranche)
            return _build_orthogonal_axis_slices(spec, tranche, fields)
        case TrancheType.DISCRIMINATOR_TRANCHE:
            fields = cast(DiscriminatorTrancheFields, tranche.discriminator_tranche)
            return _build_discriminator_slices(spec, tranche, fields)
        case TrancheType.FAILURE_MODE_TRANCHE:
            fields = cast(FailureModeTrancheFields, tranche.failure_mode_tranche)
            return _build_failure_mode_slices(spec, tranche, fields)
        case TrancheType.CROSS_DEVICE_TRANCHE:
            fields = cast(CrossDeviceTrancheFields, tranche.cross_device_tranche)
            if dataset is None:
                return []
            return _build_cross_device_slices(spec, tranche, fields, dataset)
        case TrancheType.BOUNDARY_STRESS_TRANCHE:
            fields = cast(BoundaryStressTrancheFields, tranche.boundary_stress_tranche)
            return _build_boundary_stress_slices(spec, tranche, fields)
        case _:
            return []


def _build_orthogonal_axis_slices(
    spec: SweepSpec,
    tranche: TrancheSpec,
    fields: HypothesisTrancheBase,
) -> list[SliceSpec]:
    combinations = product(*(axis.values for axis in fields.orthogonal_axes))
    generated: list[SliceSpec] = []
    for index, values in enumerate(combinations, start=1):
        if tranche.max_slices is not None and len(generated) >= tranche.max_slices:
            break
        candidate_filters = [*spec.fixed_parameters, *tranche.fixed_parameters]
        name_parts = [tranche.tranche_id]
        for axis, value in zip(fields.orthogonal_axes, values, strict=True):
            candidate_filters.append(
                CandidateFilter(field=axis.field, operator=axis.operator, value=value)
            )
            name_parts.append(f"{axis.axis_id}_{_slugify(str(value))}")
        generated.append(
            SliceSpec(
                slice_id="__".join(name_parts) or f"{tranche.tranche_id}_{index}",
                tranche_type=tranche.tranche_type,
                tranche_objective=tranche.tranche_objective,
                hypothesis_class=hypothesis_class_for_tranche_type(tranche.tranche_type),
                candidate_filters=candidate_filters,
                control_parameters=list(tranche.control_parameters),
                fixed_parameters=[*spec.fixed_parameters, *tranche.fixed_parameters],
                orthogonal_axes=[axis.model_copy(deep=True) for axis in fields.orthogonal_axes],
                parameter_count=fields.parameter_count,
                observable_count=fields.observable_count,
                profile_override=tranche.shared_profile,
                max_slices=tranche.max_slices,
                sampling_strategy=tranche.sampling_strategy,
                source_tranche_ids=list(tranche.source_tranche_ids),
                perturbation_fraction=tranche.perturbation_fraction,
                log_scale_parameters=list(tranche.log_scale_parameters),
                interaction_mode=tranche.interaction_mode,
                refinement_reason=tranche.refinement_reason or RefinementReason.PRESET_EXPANSION,
                expected_signature=tranche.expected_signature,
                lineage_depth=tranche.lineage_depth,
                utility_weights=tranche.utility_weights or spec.utility_weights,
                tags=[
                    "generated",
                    tranche.tranche_type.value,
                    hypothesis_class_for_tranche_type(tranche.tranche_type).value,
                ],
            )
        )
    return generated


def _build_scaling_law_slices(
    spec: SweepSpec,
    tranche: TrancheSpec,
    fields: ScalingLawTrancheFields,
) -> list[SliceSpec]:
    generated = _build_orthogonal_axis_slices(spec, tranche, fields)
    expected_signature = ExpectedSignature(
        label=fields.hypothesis_label or tranche.tranche_id,
        observable_name=fields.observable_name,
        scaling_type=fields.expected_scaling_type,
    )
    return [
        slice_spec.model_copy(update={"expected_signature": expected_signature}, deep=True)
        for slice_spec in generated
    ]


def _build_discriminator_slices(
    spec: SweepSpec,
    tranche: TrancheSpec,
    fields: DiscriminatorTrancheFields,
) -> list[SliceSpec]:
    expected_signature = ExpectedSignature(
        label=fields.expected_separation_signature,
        observable_name=fields.discriminator_axis,
    )
    generated = _build_orthogonal_axis_slices(spec, tranche, fields)
    return [
        slice_spec.model_copy(
            update={
                "expected_signature": expected_signature,
                "target_hypothesis_pair": list(fields.target_hypothesis_pair),
                "discriminator_axis": fields.discriminator_axis,
                "required_resolution": fields.required_resolution,
                "originating_equivalence_cluster_id": fields.originating_equivalence_cluster,
                "discriminator_rationale": fields.discriminator_rationale,
                "predicted_separation": fields.predicted_separation,
                "observed_separation": fields.observed_separation,
                "discriminator_gain": fields.discriminator_gain,
                "axis_cost": fields.axis_cost,
                "redundancy_penalty": fields.redundancy_penalty,
                "lineage_depth": max(slice_spec.lineage_depth, fields.generation),
                "tags": [
                    *slice_spec.tags,
                    "adversarial",
                    "discriminator",
                    _slugify(fields.discriminator_axis),
                ],
            },
            deep=True,
        )
        for slice_spec in generated
    ]


def _build_failure_mode_slices(
    spec: SweepSpec,
    tranche: TrancheSpec,
    fields: FailureModeTrancheFields,
) -> list[SliceSpec]:
    generated: list[SliceSpec] = []
    for failure_mode in fields.failure_modes:
        if tranche.max_slices is not None and len(generated) >= tranche.max_slices:
            break
        generated.append(
            SliceSpec(
                slice_id=f"{tranche.tranche_id}__{_slugify(failure_mode)}",
                tranche_type=tranche.tranche_type,
                tranche_objective=tranche.tranche_objective,
                hypothesis_class=HypothesisClass.FAILURE_MODE,
                candidate_filters=[
                    *spec.fixed_parameters,
                    *tranche.fixed_parameters,
                    *_failure_mode_filters(failure_mode),
                ],
                control_parameters=list(tranche.control_parameters),
                fixed_parameters=[*spec.fixed_parameters, *tranche.fixed_parameters],
                orthogonal_axes=[axis.model_copy(deep=True) for axis in fields.orthogonal_axes],
                parameter_count=fields.parameter_count,
                observable_count=fields.observable_count,
                failure_modes=[failure_mode],
                profile_override=tranche.shared_profile,
                max_slices=tranche.max_slices,
                sampling_strategy=tranche.sampling_strategy,
                source_tranche_ids=list(tranche.source_tranche_ids),
                perturbation_fraction=tranche.perturbation_fraction,
                log_scale_parameters=list(tranche.log_scale_parameters),
                interaction_mode=tranche.interaction_mode,
                refinement_reason=tranche.refinement_reason or RefinementReason.PRESET_EXPANSION,
                expected_signature=tranche.expected_signature,
                lineage_depth=tranche.lineage_depth,
                utility_weights=tranche.utility_weights or spec.utility_weights,
                tags=["generated", tranche.tranche_type.value, _slugify(failure_mode)],
            )
        )
    return generated


def _failure_mode_filters(failure_mode: str) -> list[CandidateFilter]:
    normalized = failure_mode.strip().lower()
    if normalized in {"artifact_risk", "null_alias", "null_dominance"}:
        return [
            CandidateFilter(
                field=CandidateFilterField.NULL_RISK,
                operator=FilterOperator.GTE,
                value=7,
            )
        ]
    if normalized in {"fabrication_fragility", "process_window"}:
        return [
            CandidateFilter(
                field=CandidateFilterField.FABRICATION_COMPLEXITY,
                operator=FilterOperator.GTE,
                value=8,
            )
        ]
    if normalized in {"screening_instability", "screening_bias"}:
        return [
            CandidateFilter(
                field=CandidateFilterField.SCREENING_STATUS,
                operator=FilterOperator.IN,
                value=["sandbox", "screening"],
            )
        ]
    return [
        CandidateFilter(
            field=CandidateFilterField.NULL_RISK,
            operator=FilterOperator.GTE,
            value=6,
        ),
        CandidateFilter(
            field=CandidateFilterField.FABRICATION_COMPLEXITY,
            operator=FilterOperator.GTE,
            value=7,
        ),
    ]


def _build_cross_device_slices(
    spec: SweepSpec,
    tranche: TrancheSpec,
    fields: CrossDeviceTrancheFields,
    dataset: MMMDataset,
) -> list[SliceSpec]:
    selected_rows = [
        row
        for row in dataset.replication_matrix
        if (
            not fields.replication_ids
            or row.replication_id in set(fields.replication_ids)
        )
        and (
            not fields.device_classes
            or bool(set(row.device_classes) & set(fields.device_classes))
        )
    ]
    generated: list[SliceSpec] = []
    for row in selected_rows:
        if tranche.max_slices is not None and len(generated) >= tranche.max_slices:
            break
        generated.append(
            SliceSpec(
                slice_id=f"{tranche.tranche_id}__{_slugify(row.replication_id)}",
                tranche_type=tranche.tranche_type,
                tranche_objective=tranche.tranche_objective,
                hypothesis_class=HypothesisClass.CROSS_DEVICE,
                candidate_filters=[
                    *spec.fixed_parameters,
                    *tranche.fixed_parameters,
                    CandidateFilter(
                        field=CandidateFilterField.PARENT_STRUCTURE_ID,
                        operator=FilterOperator.IN,
                        value=list(row.required_structure_ids),
                    ),
                ],
                control_parameters=list(tranche.control_parameters),
                fixed_parameters=[*spec.fixed_parameters, *tranche.fixed_parameters],
                orthogonal_axes=[axis.model_copy(deep=True) for axis in fields.orthogonal_axes],
                parameter_count=fields.parameter_count,
                observable_count=fields.observable_count,
                device_classes=list(row.device_classes),
                profile_override=tranche.shared_profile,
                max_slices=tranche.max_slices,
                sampling_strategy=tranche.sampling_strategy,
                source_tranche_ids=list(tranche.source_tranche_ids),
                perturbation_fraction=tranche.perturbation_fraction,
                log_scale_parameters=list(tranche.log_scale_parameters),
                interaction_mode=tranche.interaction_mode,
                refinement_reason=tranche.refinement_reason or RefinementReason.PRESET_EXPANSION,
                expected_signature=tranche.expected_signature,
                lineage_depth=tranche.lineage_depth,
                utility_weights=tranche.utility_weights or spec.utility_weights,
                tags=["generated", tranche.tranche_type.value, row.replication_id],
            )
        )
    return generated


def _build_boundary_stress_slices(
    spec: SweepSpec,
    tranche: TrancheSpec,
    fields: BoundaryStressTrancheFields,
) -> list[SliceSpec]:
    if not fields.orthogonal_axes:
        return []
    extreme_values = [[axis.values[0], axis.values[-1]] for axis in fields.orthogonal_axes]
    combinations = product(*extreme_values)
    generated: list[SliceSpec] = []
    for index, values in enumerate(combinations, start=1):
        if tranche.max_slices is not None and len(generated) >= tranche.max_slices:
            break
        candidate_filters = [*spec.fixed_parameters, *tranche.fixed_parameters]
        name_parts = [tranche.tranche_id]
        for axis, value in zip(fields.orthogonal_axes, values, strict=True):
            candidate_filters.append(
                CandidateFilter(field=axis.field, operator=axis.operator, value=value)
            )
            name_parts.append(f"{axis.axis_id}_{_slugify(str(value))}")
        generated.append(
            SliceSpec(
                slice_id="__".join(name_parts) or f"{tranche.tranche_id}_{index}",
                tranche_type=tranche.tranche_type,
                tranche_objective=tranche.tranche_objective,
                hypothesis_class=HypothesisClass.BOUNDARY_STRESS,
                candidate_filters=candidate_filters,
                control_parameters=list(tranche.control_parameters),
                fixed_parameters=[*spec.fixed_parameters, *tranche.fixed_parameters],
                orthogonal_axes=[axis.model_copy(deep=True) for axis in fields.orthogonal_axes],
                parameter_count=fields.parameter_count,
                observable_count=fields.observable_count,
                profile_override=tranche.shared_profile,
                max_slices=tranche.max_slices,
                sampling_strategy=tranche.sampling_strategy,
                source_tranche_ids=list(tranche.source_tranche_ids),
                perturbation_fraction=tranche.perturbation_fraction,
                log_scale_parameters=list(tranche.log_scale_parameters),
                interaction_mode=tranche.interaction_mode,
                refinement_reason=tranche.refinement_reason or RefinementReason.PRESET_EXPANSION,
                expected_signature=tranche.expected_signature,
                lineage_depth=tranche.lineage_depth,
                utility_weights=tranche.utility_weights or spec.utility_weights,
                tags=["generated", tranche.tranche_type.value, "boundary_stress"],
            )
        )
    return generated


def _merge_slice_defaults(
    spec: SweepSpec,
    tranche: TrancheSpec,
    slice_spec: SliceSpec,
) -> SliceSpec:
    return slice_spec.model_copy(
        update={
            "tranche_type": slice_spec.tranche_type or tranche.tranche_type,
            "tranche_objective": slice_spec.tranche_objective or tranche.tranche_objective,
            "hypothesis_class": (
                slice_spec.hypothesis_class or hypothesis_class_for_tranche_type(tranche.tranche_type)
            ),
            "control_parameters": [
                *tranche.control_parameters,
                *slice_spec.control_parameters,
            ],
            "fixed_parameters": [
                *spec.fixed_parameters,
                *tranche.fixed_parameters,
                *slice_spec.fixed_parameters,
            ],
            "orthogonal_axes": [
                *slice_spec.orthogonal_axes,
            ]
            or [
                axis.model_copy(deep=True)
                for axis in (_typed_tranche_fields(tranche).orthogonal_axes if _typed_tranche_fields(tranche) else [])
            ],
            "parameter_count": (
                slice_spec.parameter_count
                or (_typed_tranche_fields(tranche).parameter_count if _typed_tranche_fields(tranche) else 0)
            ),
            "observable_count": (
                slice_spec.observable_count
                or (_typed_tranche_fields(tranche).observable_count if _typed_tranche_fields(tranche) else 0)
            ),
            "failure_modes": [
                *slice_spec.failure_modes,
            ]
            or (
                list(cast(FailureModeTrancheFields, tranche.failure_mode_tranche).failure_modes)
                if tranche.failure_mode_tranche is not None
                else []
            ),
            "device_classes": [
                *slice_spec.device_classes,
            ]
            or (
                list(cast(CrossDeviceTrancheFields, tranche.cross_device_tranche).device_classes)
                if tranche.cross_device_tranche is not None
                else []
            ),
            "max_slices": slice_spec.max_slices or tranche.max_slices or spec.max_slices,
            "sampling_strategy": (
                slice_spec.sampling_strategy
                or tranche.sampling_strategy
                or spec.sampling_strategy
                or TrancheSamplingStrategy.EXPLICIT
            ),
            "source_tranche_ids": [
                *tranche.source_tranche_ids,
                *slice_spec.source_tranche_ids,
            ],
            "perturbation_fraction": (
                slice_spec.perturbation_fraction
                if slice_spec.perturbation_fraction is not None
                else tranche.perturbation_fraction
                if tranche.perturbation_fraction is not None
                else spec.perturbation_fraction
            ),
            "log_scale_parameters": [
                *tranche.log_scale_parameters,
                *slice_spec.log_scale_parameters,
            ],
            "interaction_mode": (
                slice_spec.interaction_mode or tranche.interaction_mode or spec.interaction_mode
            ),
            "refinement_reason": (
                slice_spec.refinement_reason
                or tranche.refinement_reason
                or spec.refinement_reason
                or RefinementReason.DECLARED
            ),
            "expected_signature": (
                slice_spec.expected_signature
                or tranche.expected_signature
                or spec.expected_signature
            ),
            "lineage_depth": max(
                slice_spec.lineage_depth,
                tranche.lineage_depth,
                spec.lineage_depth,
            ),
            "utility_weights": (
                slice_spec.utility_weights or tranche.utility_weights or spec.utility_weights
            ),
        },
        deep=True,
    )


def _build_controlled_slices(spec: SweepSpec, tranche: TrancheSpec) -> list[SliceSpec]:
    control_parameters = tranche.control_parameters or spec.control_parameters
    if not control_parameters:
        return []
    combinations = product(*(parameter.values for parameter in control_parameters))
    generated: list[SliceSpec] = []
    for index, values in enumerate(combinations, start=1):
        if tranche.max_slices is not None and len(generated) >= tranche.max_slices:
            break
        candidate_filters = [
            *spec.fixed_parameters,
            *tranche.fixed_parameters,
        ]
        name_parts = [tranche.tranche_id]
        for parameter, value in zip(control_parameters, values, strict=True):
            candidate_filters.append(
                CandidateFilter(
                    field=parameter.field,
                    operator=parameter.operator,
                    value=value,
                )
            )
            name_parts.append(f"{parameter.name}_{_slugify(str(value))}")
        generated.append(
            SliceSpec(
                slice_id="__".join(name_parts) or f"{tranche.tranche_id}_{index}",
                tranche_type=tranche.tranche_type,
                tranche_objective=tranche.tranche_objective,
                hypothesis_class=hypothesis_class_for_tranche_type(tranche.tranche_type),
                candidate_filters=candidate_filters,
                fixed_parameters=[*spec.fixed_parameters, *tranche.fixed_parameters],
                control_parameters=list(control_parameters),
                orthogonal_axes=[
                    axis.model_copy(deep=True)
                    for axis in (
                        _typed_tranche_fields(tranche).orthogonal_axes
                        if _typed_tranche_fields(tranche) is not None
                        else []
                    )
                ],
                parameter_count=(
                    _typed_tranche_fields(tranche).parameter_count
                    if _typed_tranche_fields(tranche) is not None
                    else 0
                ),
                observable_count=(
                    _typed_tranche_fields(tranche).observable_count
                    if _typed_tranche_fields(tranche) is not None
                    else 0
                ),
                profile_override=tranche.shared_profile,
                max_slices=tranche.max_slices,
                sampling_strategy=tranche.sampling_strategy,
                source_tranche_ids=list(tranche.source_tranche_ids),
                perturbation_fraction=tranche.perturbation_fraction,
                log_scale_parameters=list(tranche.log_scale_parameters),
                interaction_mode=tranche.interaction_mode,
                refinement_reason=tranche.refinement_reason or RefinementReason.PRESET_EXPANSION,
                expected_signature=tranche.expected_signature,
                lineage_depth=tranche.lineage_depth,
                utility_weights=tranche.utility_weights or spec.utility_weights,
                tags=["generated", tranche.tranche_type.value],
            )
        )
    return generated


def _copy_source_slices(
    spec: SweepSpec,
    tranche: TrancheSpec,
    resolved_tranches: dict[str, ResolvedTranchePlan],
) -> list[SliceSpec]:
    generated: list[SliceSpec] = []
    for source_tranche_id in tranche.source_tranche_ids:
        source_tranche = resolved_tranches.get(source_tranche_id)
        if source_tranche is None:
            continue
        for source_slice in source_tranche.slices:
            if tranche.max_slices is not None and len(generated) >= tranche.max_slices:
                return generated
            generated.append(
                SliceSpec(
                    slice_id=_derived_slice_id(tranche, source_slice.slice_id),
                    tranche_type=tranche.tranche_type,
                    tranche_objective=tranche.tranche_objective,
                    hypothesis_class=hypothesis_class_for_tranche_type(tranche.tranche_type),
                    input_registry_scope=source_slice.input_registry_scope.model_copy(deep=True),
                    candidate_filters=[
                        *source_slice.candidate_filters,
                        *tranche.fixed_parameters,
                    ],
                    control_parameters=list(tranche.control_parameters),
                    fixed_parameters=[*tranche.fixed_parameters],
                    orthogonal_axes=[axis.model_copy(deep=True) for axis in source_slice.orthogonal_axes],
                    parameter_count=source_slice.parameter_count,
                    observable_count=source_slice.observable_count,
                    failure_modes=list(source_slice.failure_modes),
                    device_classes=list(source_slice.device_classes),
                    profile_override=tranche.shared_profile or source_slice.resolved_profile,
                    max_slices=tranche.max_slices,
                    sampling_strategy=tranche.sampling_strategy,
                    source_tranche_ids=[source_tranche_id],
                    perturbation_fraction=tranche.perturbation_fraction,
                    log_scale_parameters=list(tranche.log_scale_parameters),
                    interaction_mode=tranche.interaction_mode,
                    null_pair_id=(
                        source_slice.slice_id
                        if _is_null_tranche_type(tranche.tranche_type)
                        else source_slice.null_pair_id
                    ),
                    parent_slice_id=source_slice.slice_id,
                    refinement_reason=(
                        tranche.refinement_reason
                        or _default_refinement_reason(tranche.tranche_type)
                    ),
                    expected_signature=tranche.expected_signature,
                    lineage_depth=source_slice.lineage_depth + 1,
                    utility_weights=tranche.utility_weights or spec.utility_weights,
                    tags=[
                        "generated",
                        tranche.tranche_type.value,
                        source_tranche_id,
                    ],
                    null_lineage_lock=(
                        NullLineageLock(
                            source_tranche_id=source_tranche_id,
                            source_slice_id=source_slice.slice_id,
                            source_parameter_hash=source_slice.parameter_hash,
                            source_candidate_ids_sha256=_candidate_id_hash(source_slice.candidate_ids),
                            source_candidate_count=source_slice.candidate_count,
                            source_lineage_depth=source_slice.lineage_depth,
                        )
                        if tranche.tranche_type == TrancheType.NULL_DOMINANCE_TRANCHE
                        else None
                    ),
                )
            )
    return generated


def _derived_slice_id(tranche: TrancheSpec, source_slice_id: str) -> str:
    suffix = tranche.tranche_type.value
    return f"{_slugify(source_slice_id)}__{suffix}"


def _default_refinement_reason(tranche_type: TrancheType) -> RefinementReason:
    match tranche_type:
        case TrancheType.NULL_MODEL:
            return RefinementReason.NULL_PAIR
        case TrancheType.NULL_DOMINANCE_TRANCHE:
            return RefinementReason.NULL_PAIR
        case TrancheType.LOCAL_PERTURBATION:
            return RefinementReason.LOCAL_PERTURBATION
        case TrancheType.SCALING:
            return RefinementReason.SCALING_EXPANSION
        case TrancheType.SCALING_LAW_TRANCHE:
            return RefinementReason.SCALING_EXPANSION
        case TrancheType.INTERACTION:
            return RefinementReason.INTERACTION_SYNTHESIS
        case _:
            return RefinementReason.PRESET_EXPANSION


def _dedupe_slice_specs(slice_specs: list[SliceSpec]) -> list[SliceSpec]:
    deduped: list[SliceSpec] = []
    seen_hashes: set[str] = set()
    seen_ids: set[str] = set()
    for slice_spec in slice_specs:
        parameter_hash = _slice_spec_parameter_hash(slice_spec)
        if parameter_hash in seen_hashes:
            continue
        slice_id = slice_spec.slice_id
        suffix = 2
        while slice_id in seen_ids:
            slice_id = f"{slice_spec.slice_id}_{suffix}"
            suffix += 1
        deduped.append(slice_spec.model_copy(update={"slice_id": slice_id}, deep=True))
        seen_hashes.add(parameter_hash)
        seen_ids.add(slice_id)
    return deduped


def _slice_spec_parameter_hash(slice_spec: SliceSpec) -> str:
    payload = {
        "scope": slice_spec.input_registry_scope.model_dump(mode="json"),
        "candidate_filters": [
            _candidate_filter_signature(filter_spec) for filter_spec in slice_spec.candidate_filters
        ],
        "control_parameters": [
            control.model_dump(mode="json") for control in slice_spec.control_parameters
        ],
        "fixed_parameters": [
            _candidate_filter_signature(filter_spec) for filter_spec in slice_spec.fixed_parameters
        ],
        "profile_override": slice_spec.profile_override,
        "sampling_strategy": (
            slice_spec.sampling_strategy.value if slice_spec.sampling_strategy else None
        ),
        "source_tranche_ids": sorted(slice_spec.source_tranche_ids),
        "perturbation_fraction": slice_spec.perturbation_fraction,
        "log_scale_parameters": [
            parameter.model_dump(mode="json") for parameter in slice_spec.log_scale_parameters
        ],
        "interaction_mode": (
            slice_spec.interaction_mode.value if slice_spec.interaction_mode else None
        ),
        "null_pair_id": slice_spec.null_pair_id,
        "parent_slice_id": slice_spec.parent_slice_id,
        "refinement_reason": (
            slice_spec.refinement_reason.value if slice_spec.refinement_reason else None
        ),
        "expected_signature": (
            slice_spec.expected_signature.model_dump(mode="json")
            if slice_spec.expected_signature is not None
            else None
        ),
        "lineage_depth": slice_spec.lineage_depth,
        "orthogonal_axes": [axis.model_dump(mode="json") for axis in slice_spec.orthogonal_axes],
        "parameter_count": slice_spec.parameter_count,
        "observable_count": slice_spec.observable_count,
        "failure_modes": sorted(slice_spec.failure_modes),
        "device_classes": sorted(slice_spec.device_classes),
        "target_hypothesis_pair": sorted(slice_spec.target_hypothesis_pair),
        "discriminator_axis": slice_spec.discriminator_axis,
        "required_resolution": slice_spec.required_resolution,
        "originating_equivalence_cluster_id": slice_spec.originating_equivalence_cluster_id,
        "predicted_separation": slice_spec.predicted_separation,
        "discriminator_gain": slice_spec.discriminator_gain,
        "axis_cost": slice_spec.axis_cost,
        "redundancy_penalty": slice_spec.redundancy_penalty,
    }
    return _sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))


def _candidate_filter_signature(filter_spec: CandidateFilter) -> FilterSignature:
    return {
        "field": filter_spec.field.value,
        "operator": filter_spec.operator.value,
        "value": filter_spec.value,
    }


def _link_null_pairs(tranches: list[ResolvedTranchePlan]) -> None:
    by_id = {tranche.tranche_id: tranche for tranche in tranches}
    for tranche in tranches:
        if not _is_null_tranche_type(tranche.tranche_type):
            continue
        for slice_plan in tranche.slices:
            if slice_plan.null_pair_id is None:
                continue
            for source_tranche_id in tranche.source_tranche_ids:
                source_tranche = by_id.get(source_tranche_id)
                if source_tranche is None:
                    continue
                source_slice = next(
                    (
                        candidate
                        for candidate in source_tranche.slices
                        if candidate.slice_id == slice_plan.null_pair_id
                    ),
                    None,
                )
                if source_slice is None:
                    continue
                lock = slice_plan.lineage.null_lineage_lock
                if lock is None and tranche.tranche_type == TrancheType.NULL_DOMINANCE_TRANCHE:
                    raise SweepPlanningError(
                        f"Null-dominance slice '{slice_plan.slice_id}' is missing a lineage lock."
                    )
                if lock is not None:
                    if lock.source_tranche_id != source_tranche_id or lock.source_slice_id != source_slice.slice_id:
                        raise SweepPlanningError(
                            f"Null-dominance slice '{slice_plan.slice_id}' resolved against the wrong source lineage."
                        )
                source_slice.null_pair_id = slice_plan.slice_id
                slice_plan.parent_slice_id = source_slice.slice_id
                slice_plan.lineage.parent_slice_id = source_slice.slice_id
                slice_plan.lineage.parent_slice_ids = [source_slice.slice_id]
                slice_plan.lineage.null_pair_id = source_slice.slice_id
                break


def _normalized_utility_weights(
    residual_weight: float,
    null_weight: float,
    identifiability_weight: float,
    scaling_weight: float,
    parameter_weight: float,
) -> tuple[float, float, float, float, float]:
    total_weight = (
        residual_weight + null_weight + identifiability_weight + scaling_weight + parameter_weight
    )
    if total_weight <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    return (
        residual_weight / total_weight,
        null_weight / total_weight,
        identifiability_weight / total_weight,
        scaling_weight / total_weight,
        parameter_weight / total_weight,
    )


def _utility_warning_codes(
    *,
    candidate_count: int,
    peer_count: int,
    candidate_floor: int,
    residual_weight: float,
    null_weight: float,
    identifiability_weight: float,
    scaling_weight: float,
    parameter_weight: float,
    has_scaling_axis: bool,
    has_null_baseline: bool,
    identifiability: IdentifiabilityResult,
) -> list[UtilityWarningCode]:
    warnings: list[UtilityWarningCode] = []
    normalized = _normalized_utility_weights(
        residual_weight,
        null_weight,
        identifiability_weight,
        scaling_weight,
        parameter_weight,
    )
    if peer_count == 0:
        warnings.append(UtilityWarningCode.NO_PEER_COMPARISON)
    if candidate_count <= max(candidate_floor, 3):
        warnings.append(UtilityWarningCode.SMALL_CANDIDATE_POOL)
    if max(normalized, default=0.0) >= 0.70:
        warnings.append(UtilityWarningCode.WEIGHT_CONCENTRATION)
    if not has_scaling_axis:
        warnings.append(UtilityWarningCode.NO_SCALING_AXIS)
    if not has_null_baseline:
        warnings.append(UtilityWarningCode.NO_NULL_BASELINE)
    if not identifiability.is_identifiable:
        warnings.append(UtilityWarningCode.UNIDENTIFIABLE_SLICE)
    return warnings


def _build_slice_utility(
    *,
    residual_weight: float,
    null_weight: float,
    identifiability_weight: float,
    scaling_weight: float,
    parameter_weight: float,
    residual_quality: float,
    null_model_delta: float,
    identifiability_score: float,
    measurement_equivalence_score: float,
    equivalence_margin: float,
    scaling_score: float,
    parameter_penalty_score: float,
    input_similarity: float,
    output_similarity: float,
    residual_weights: ResidualWeightConfig,
    residual_diagnostics: ResidualDiagnostics,
    null_residual_diagnostics: ResidualDiagnostics,
    null_dominance_classification: NullDominanceClassification,
    identifiability: IdentifiabilityResult,
    scaling_validation: ScalingValidation,
    utility_components: UtilityComponents,
    parameter_count: int,
    unconstrained_parameter_count: int,
    primary_fit_quality: float,
    null_fit_quality: float,
    utility_basis: str,
    candidate_count: int,
    peer_count: int,
    candidate_floor: int,
    has_null_baseline: bool,
    measurement_signal_gap: float,
    measurement_resolution_floor: float,
    measurement_conflicting_slice_id: str | None,
    perturbation: PerturbationDiagnostics | None = None,
) -> SliceUtility:
    normalized = _normalized_utility_weights(
        residual_weight,
        null_weight,
        identifiability_weight,
        scaling_weight,
        parameter_weight,
    )
    penalties = _utility_penalties(
        null_dominance_classification=null_dominance_classification,
        identifiability=identifiability,
        scaling_validation=scaling_validation,
        parameter_penalty_score=parameter_penalty_score,
    )
    utility_score = _combine_utility(
        residual_weight=residual_weight,
        null_weight=null_weight,
        identifiability_weight=identifiability_weight,
        scaling_weight=scaling_weight,
        parameter_weight=parameter_weight,
        residual_quality=residual_quality,
        null_model_delta=null_model_delta,
        identifiability_score=identifiability_score,
        scaling_score=scaling_score,
        parameter_penalty_score=parameter_penalty_score,
        penalties=penalties,
    )
    resolved_components = utility_components.model_copy(
        update={
            "baseline_score": utility_components.baseline_score,
            "null_score": utility_components.null_score,
            "delta_score": null_model_delta,
            "residual_score": residual_quality,
            "residual_quality_score": residual_quality,
            "null_model_delta": null_model_delta,
            "identifiability_score": identifiability_score,
            "scaling_score": scaling_score,
            "scaling_separation_score": utility_components.scaling_separation_score,
            "null_equivalence_score": utility_components.null_equivalence_score,
            "measurement_equivalence_score": measurement_equivalence_score,
            "equivalence_margin": equivalence_margin,
            "failure_mode_match_score": utility_components.failure_mode_match_score,
            "total_utility": utility_score,
            "parameter_penalty": parameter_penalty_score,
        },
        deep=True,
    )
    return SliceUtility(
        utility_score=utility_score,
        rank_stability=residual_quality,
        cross_slice_divergence=null_model_delta,
        robustness_metric=identifiability_score,
        redundancy_penalty=parameter_penalty_score,
        scaling_score=scaling_score,
        residual_quality_score=residual_quality,
        null_model_delta=null_model_delta,
        identifiability_score=identifiability_score,
        measurement_equivalence_score=measurement_equivalence_score,
        equivalence_margin=equivalence_margin,
        parameter_penalty_score=parameter_penalty_score,
        input_similarity=input_similarity,
        output_similarity=output_similarity,
        utility_basis=utility_basis,
        residual_diagnostics=residual_diagnostics.model_copy(deep=True),
        null_residual_diagnostics=null_residual_diagnostics.model_copy(deep=True),
        null_dominance_classification=null_dominance_classification,
        identifiability=identifiability.model_copy(deep=True),
        scaling_validation=scaling_validation.model_copy(deep=True),
        utility_components=resolved_components,
        parameter_count=parameter_count,
        unconstrained_parameter_count=unconstrained_parameter_count,
        perturbation=perturbation or PerturbationDiagnostics(),
        trace=SliceUtilityTrace(
            rank_weight=normalized[0],
            divergence_weight=normalized[1],
            robustness_weight=normalized[2],
            scaling_weight=normalized[3],
            redundancy_weight=normalized[4],
            rank_contribution=normalized[0] * residual_quality,
            divergence_contribution=normalized[1] * null_model_delta,
            robustness_contribution=normalized[2] * identifiability_score,
            scaling_contribution=normalized[3] * scaling_score,
            redundancy_contribution=-(normalized[4] * parameter_penalty_score),
            residual_weights=residual_weights.model_copy(deep=True),
            utility_components=resolved_components.model_copy(deep=True),
            penalties=penalties,
            residual_diagnostics=residual_diagnostics.model_copy(deep=True),
            null_residual_diagnostics=null_residual_diagnostics.model_copy(deep=True),
            null_dominance_classification=null_dominance_classification,
            identifiability=identifiability.model_copy(deep=True),
            scaling_validation=scaling_validation.model_copy(deep=True),
            parameter_count=parameter_count,
            unconstrained_parameter_count=unconstrained_parameter_count,
            scaling_axis=scaling_validation.scaling_axis,
            observable_name=scaling_validation.observable_name,
            primary_fit_quality=primary_fit_quality,
            null_fit_quality=null_fit_quality,
            measurement_signal_gap=measurement_signal_gap,
            measurement_resolution_floor=measurement_resolution_floor,
            equivalence_margin=equivalence_margin,
            measurement_conflicting_slice_id=measurement_conflicting_slice_id,
            candidate_count=candidate_count,
            peer_count=peer_count,
            warning_codes=_utility_warning_codes(
                candidate_count=candidate_count,
                peer_count=peer_count,
                candidate_floor=candidate_floor,
                residual_weight=residual_weight,
                null_weight=null_weight,
                identifiability_weight=identifiability_weight,
                scaling_weight=scaling_weight,
                parameter_weight=parameter_weight,
                has_scaling_axis=scaling_validation.scaling_axis is not None,
                has_null_baseline=has_null_baseline,
                identifiability=identifiability,
            ),
        ),
    )


def update_slice_utilities(
    manifest: SweepManifest,
    *,
    dataset: MMMDataset,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
    tranche_id: str | None = None,
) -> None:
    """Recompute observed utilities for completed slices and persist them into the manifest."""

    for tranche_plan, tranche_record in zip(manifest.plan.tranches, manifest.tranches, strict=True):
        if tranche_id is not None and tranche_plan.tranche_id != tranche_id:
            continue
        plan_by_slice_id = {slice_plan.slice_id: slice_plan for slice_plan in tranche_plan.slices}
        completed_keys = {
            (tranche_plan.tranche_id, record.slice_id)
            for record in tranche_record.slice_statuses
            if record.status == SliceRunStatus.COMPLETED
            and (tranche_plan.tranche_id, record.slice_id) in slice_results
        }
        for slice_plan, slice_record in zip(
            tranche_plan.slices, tranche_record.slice_statuses, strict=True
        ):
            key = (tranche_plan.tranche_id, slice_plan.slice_id)
            if key not in completed_keys:
                continue

            results = slice_results[key]
            peer_keys = [peer for peer in sorted(completed_keys) if peer != key]
            input_similarity = max(
                (
                    _candidate_jaccard(
                        slice_plan.candidate_ids,
                        plan_by_slice_id[peer[1]].candidate_ids,
                    )
                    for peer in peer_keys
                ),
                default=0.0,
            )
            output_similarity = max(
                (
                    _top_k_jaccard(
                        results,
                        slice_results[peer],
                        _tranche_plan_for(
                            manifest, tranche_plan.tranche_id
                        ).comparison_strategy.top_k,
                    )
                    for peer in peer_keys
                ),
                default=0.0,
            )
            peer_results = {peer[1]: slice_results[peer] for peer in peer_keys}
            utility, null_comparison = _evaluate_slice_utility(
                dataset=dataset,
                slice_plan=slice_plan,
                results=results,
                peer_results=peer_results,
                utility_weights=slice_plan.utility_weights or manifest.adaptive.utility_weights,
                residual_weights=manifest.residual_weights,
                candidate_floor=manifest.adaptive.refinement.candidate_count_floor,
                identifiability_threshold=manifest.identifiability_threshold,
                scaling_tolerance=manifest.scaling_tolerance,
                null_model_tolerance=manifest.null_model_tolerance,
                measurement=manifest.measurement,
                input_similarity=input_similarity,
                output_similarity=output_similarity,
                utility_basis="observed",
                perturbation=PerturbationDiagnostics(),
                existing_null_model=slice_record.null_model_comparison,
            )
            slice_plan.utility = utility
            slice_record.utility = utility.model_copy(deep=True)
            slice_record.score_breakdown = utility.utility_components.model_copy(deep=True)
            slice_record.null_model_comparison = null_comparison
            manifest.decision_log.append(
                AdaptiveDecisionRecord(
                    phase=slice_plan.phase,
                    decision_type=AdaptiveDecisionType.UTILITY_UPDATE,
                    tranche_id=tranche_plan.tranche_id,
                    slice_id=slice_plan.slice_id,
                    reason="Observed utility recomputed from deterministic QDP slice diagnostics.",
                    metrics={
                        "utility_score": utility.utility_score,
                        "residual_quality_score": utility.residual_quality_score,
                        "null_model_delta": utility.null_model_delta,
                        "identifiability_score": utility.identifiability_score,
                        "scaling_score": utility.scaling_score,
                        "parameter_penalty": utility.parameter_penalty_score,
                        "peer_count": len(peer_keys),
                    },
                    created_at=datetime.now(UTC),
                )
            )


def _evaluate_slice_utility(
    *,
    dataset: MMMDataset,
    slice_plan: ResolvedSlicePlan,
    results: list[ScoreResult],
    peer_results: dict[str, list[ScoreResult]],
    utility_weights: Any,
    residual_weights: ResidualWeightConfig,
    candidate_floor: int,
    identifiability_threshold: float,
    scaling_tolerance: float,
    null_model_tolerance: float,
    measurement: MeasurementEquivalenceConfig,
    input_similarity: float,
    output_similarity: float,
    utility_basis: str,
    perturbation: PerturbationDiagnostics | None = None,
    existing_null_model: SliceNullModelComparison | None = None,
) -> tuple[SliceUtility, SliceNullModelComparison]:
    ordered_results, axis_values, axis_name = _ordered_results_for_slice(
        dataset, slice_plan, results
    )
    primary_series = [result.score for result in ordered_results]
    residual_diagnostics, primary_fit_quality = _series_residual_summary(
        axis_values, primary_series
    )
    null_comparison = _slice_null_model_comparison(
        results=ordered_results,
        axis_values=axis_values,
        residual_weights=residual_weights,
        tolerance=null_model_tolerance,
        existing=existing_null_model,
    )
    identifiability = _slice_identifiability(
        dataset=dataset,
        result=ordered_results[0],
        peer_results=peer_results,
        resolution_threshold=identifiability_threshold,
    )
    identifiability_score = compute_identifiability_score(
        identifiability,
        resolution_threshold=identifiability_threshold,
    )
    equivalence_margin, measurement_gap, measurement_peer = _slice_measurement_equivalence(
        dataset=dataset,
        result=ordered_results[0],
        peer_results=peer_results,
        measurement=measurement,
    )
    measurement_equivalence = _legacy_measurement_equivalence_score(equivalence_margin)

    scaling_validation = _slice_scaling_validation(
        dataset=dataset,
        slice_plan=slice_plan,
        results=ordered_results,
        tolerance=scaling_tolerance,
        fallback_axis_name=axis_name,
    )
    scaling_score = (
        0.5
        if scaling_validation.expected_scaling_type == ScalingType.UNKNOWN
        and scaling_validation.scaling_axis is None
        else clamp(1.0 - scaling_validation.mismatch_score)
    )
    scaling_discrimination_score = scaling_separation_score(scaling_validation)

    top_genome = dataset.genome_index[ordered_results[0].genome_id]
    max_parameter_count = max(
        (
            len(dataset.genome_index[genome_id].geometric_parameters)
            for genome_id in slice_plan.candidate_ids
        ),
        default=len(top_genome.geometric_parameters),
    )
    parameter_penalty_score, unconstrained_parameter_count = parameter_economy_penalty(
        parameter_count=len(top_genome.geometric_parameters),
        observable_count=len(genome_numeric_observables(top_genome)),
        max_parameter_count=max_parameter_count,
    )
    null_equivalence = null_equivalence_score(
        null_comparison.dominance_classification,
        delta_signal=_normalized_null_delta(null_comparison) - 0.5,
    )
    failure_match = failure_mode_match_score(top_genome, slice_plan.failure_modes)

    components = build_utility_components(
        baseline_score=null_comparison.mean_baseline_score,
        null_score=null_comparison.mean_baseline_score,
        delta_score=_normalized_null_delta(null_comparison),
        residual_score=residual_quality_score(residual_diagnostics, residual_weights),
        identifiability_score=identifiability_score,
        scaling_score=scaling_score,
        scaling_separation_score=scaling_discrimination_score,
        null_equivalence_score=null_equivalence,
        measurement_equivalence_score=measurement_equivalence,
        equivalence_margin=equivalence_margin,
        failure_mode_match_score=failure_match,
        parameter_penalty=parameter_penalty_score,
    )
    utility = _build_slice_utility(
        residual_weight=utility_weights.residual_quality,
        null_weight=utility_weights.null_model_delta,
        identifiability_weight=utility_weights.identifiability,
        scaling_weight=utility_weights.scaling,
        parameter_weight=utility_weights.parameter_penalty,
        residual_quality=components.residual_score,
        null_model_delta=components.delta_score or 0.0,
        identifiability_score=components.identifiability_score,
        measurement_equivalence_score=measurement_equivalence,
        equivalence_margin=equivalence_margin,
        scaling_score=components.scaling_score,
        parameter_penalty_score=components.parameter_penalty,
        input_similarity=input_similarity,
        output_similarity=output_similarity,
        residual_weights=residual_weights,
        residual_diagnostics=residual_diagnostics,
        null_residual_diagnostics=null_comparison.null_residual_diagnostics,
        null_dominance_classification=null_comparison.dominance_classification,
        identifiability=identifiability,
        scaling_validation=scaling_validation,
        utility_components=components,
        parameter_count=len(top_genome.geometric_parameters),
        unconstrained_parameter_count=unconstrained_parameter_count,
        primary_fit_quality=primary_fit_quality,
        null_fit_quality=null_comparison.null_fit_quality or 0.0,
        utility_basis=utility_basis,
        candidate_count=slice_plan.candidate_count,
        peer_count=len(peer_results),
        candidate_floor=candidate_floor,
        has_null_baseline=null_comparison.available,
        measurement_signal_gap=measurement_gap,
        measurement_resolution_floor=_effective_measurement_resolution(
            measurement,
            "__default__",
        ),
        measurement_conflicting_slice_id=measurement_peer,
        perturbation=perturbation,
    )
    return utility, null_comparison


def _ordered_results_for_slice(
    dataset: MMMDataset,
    slice_plan: ResolvedSlicePlan,
    results: list[ScoreResult],
) -> tuple[list[ScoreResult], list[float], str]:
    axis_name, axis_values_by_candidate = _infer_scaling_axis(dataset, slice_plan, results)
    if axis_values_by_candidate is None:
        return results, [float(index) for index in range(len(results))], "rank"
    ordered = sorted(
        results,
        key=lambda result: (
            axis_values_by_candidate.get(result.genome_id, float("inf")),
            result.genome_id,
        ),
    )
    axis_values = [axis_values_by_candidate[result.genome_id] for result in ordered]
    return ordered, axis_values, axis_name


def _rank_slice_candidates(
    *,
    dataset: MMMDataset,
    profile: str,
    candidate_ids: list[str],
    null_model_enabled: bool,
    baseline_mode: str | None,
    baseline_profile: str | None,
    tranche_type: TrancheType = TrancheType.PRIMARY,
) -> list[ScoreResult]:
    results = rank_dataset(
        dataset,
        profile=profile,
        candidate_ids=set(candidate_ids),
        baseline_mode=baseline_mode if null_model_enabled else None,
        baseline_profile=baseline_profile if null_model_enabled else None,
    )
    if not _is_null_tranche_type(tranche_type):
        return results
    null_results = [
        result.model_copy(
            update={
                "score": result.null_score
                if result.null_score is not None
                else result.baseline_score
                if result.baseline_score is not None
                else result.score,
                "baseline_score": None,
                "total_utility": result.null_score
                if result.null_score is not None
                else result.baseline_score
                if result.baseline_score is not None
                else result.score,
                "score_delta": None,
                "delta_score": None,
            },
            deep=True,
        )
        for result in results
    ]
    return sorted(
        null_results,
        key=lambda result: (
            -result.score,
            dataset.genome_index[result.genome_id].null_risk_score,
            dataset.genome_index[result.genome_id].fabrication_complexity_score,
        ),
    )


def _series_residual_summary(
    axis_values: list[float],
    values: list[float],
) -> tuple[ResidualDiagnostics, float]:
    if len(values) < 2:
        return ResidualDiagnostics(), 1.0
    _, fit_quality, fitted = fit_scaling_signature(axis_values, values)
    residuals = [value - fitted_value for value, fitted_value in zip(values, fitted, strict=True)]
    return compute_residual_diagnostics(residuals), fit_quality


def _slice_null_model_comparison(
    *,
    results: list[ScoreResult],
    axis_values: list[float],
    residual_weights: ResidualWeightConfig,
    tolerance: float,
    existing: SliceNullModelComparison | None,
) -> SliceNullModelComparison:
    baseline_candidates = [result for result in results if result.baseline_score is not None]
    base_model = (
        existing.model_copy(deep=True) if existing is not None else SliceNullModelComparison()
    )
    if not baseline_candidates:
        return base_model.model_copy(
            update={
                "available": False,
                "candidate_count": len(results),
                "baseline_candidate_count": 0,
                "dominance_classification": NullDominanceClassification.INDETERMINATE,
                "within_tolerance": True,
            }
        )

    baseline_top = max(
        baseline_candidates,
        key=lambda result: (result.baseline_score or 0.0, result.genome_id),
    )
    primary_scores = [result.score for result in results]
    baseline_scores = [float(result.baseline_score or 0.0) for result in baseline_candidates]
    residual_diagnostics, primary_fit_quality = _series_residual_summary(
        axis_values, primary_scores
    )
    null_residual_diagnostics, null_fit_quality = _series_residual_summary(
        axis_values, baseline_scores
    )
    primary_quality = residual_quality_score(residual_diagnostics, residual_weights)
    null_quality = residual_quality_score(null_residual_diagnostics, residual_weights)
    delta_residual = primary_quality - null_quality
    delta_fit_quality = primary_fit_quality - null_fit_quality
    dominance = classify_null_model_dominance(
        delta_residual=delta_residual,
        delta_fit_quality=delta_fit_quality,
        tolerance=tolerance,
    )
    deltas = [
        result.score_delta for result in baseline_candidates if result.score_delta is not None
    ]
    baselines = [
        result.baseline_score
        for result in baseline_candidates
        if result.baseline_score is not None
    ]
    top_result = results[0]
    comparison = base_model.model_copy(
        update={
            "enabled": True,
            "requested": base_model.requested or bool(baselines),
            "available": True,
            "mode": top_result.baseline_mode,
            "baseline_profile": top_result.baseline_profile,
            "candidate_count": len(results),
            "baseline_candidate_count": len(baseline_candidates),
            "baseline_top_candidate_id": baseline_top.genome_id,
            "baseline_top_score": baseline_top.baseline_score,
            "top_candidate_primary_score": top_result.score,
            "top_candidate_baseline_score": top_result.baseline_score,
            "top_candidate_delta": top_result.score_delta,
            "mean_baseline_score": (sum(baselines) / len(baselines)) if baselines else None,
            "mean_score_delta": (sum(deltas) / len(deltas)) if deltas else None,
            "positive_delta_rate": (
                sum(delta > 0 for delta in deltas) / len(deltas) if deltas else None
            ),
            "primary_fit_quality": primary_fit_quality,
            "null_fit_quality": null_fit_quality,
            "delta_fit_quality": delta_fit_quality,
            "residual_diagnostics": residual_diagnostics,
            "null_residual_diagnostics": null_residual_diagnostics,
            "residual_quality_score": primary_quality,
            "null_residual_quality_score": null_quality,
            "delta_residual": delta_residual,
            "dominance_classification": dominance,
            "within_tolerance": dominance == NullDominanceClassification.INDETERMINATE,
            "winner_changed": baseline_top.genome_id != top_result.genome_id,
        }
    )
    return comparison


def _normalized_null_delta(comparison: SliceNullModelComparison) -> float:
    if not comparison.available:
        return 0.5
    delta_residual = comparison.delta_residual or 0.0
    delta_fit = comparison.delta_fit_quality or 0.0
    score = clamp(0.5 + (0.5 * ((delta_residual + delta_fit) / 2.0)))
    if comparison.dominance_classification == NullDominanceClassification.DOMINATED_BY_NULL:
        return 0.0
    if comparison.dominance_classification == NullDominanceClassification.INDETERMINATE:
        return min(score, 0.4)
    return score


def _slice_identifiability(
    *,
    dataset: MMMDataset,
    result: ScoreResult,
    peer_results: dict[str, list[ScoreResult]],
    resolution_threshold: float,
) -> IdentifiabilityResult:
    if not peer_results:
        return IdentifiabilityResult()
    current_axes = _predicted_axes_for_genome(dataset, result.genome_id)
    worst_result: IdentifiabilityResult | None = None
    for peer_slice_id, peer in sorted(peer_results.items()):
        if not peer:
            continue
        comparison = check_identifiability(
            current_axes,
            _predicted_axes_for_genome(dataset, peer[0].genome_id),
            resolution_threshold=resolution_threshold,
            conflicting_slice_id=peer_slice_id,
        )
        if worst_result is None or comparison.mean_observable_difference < (
            worst_result.mean_observable_difference
        ):
            worst_result = comparison
    return worst_result or IdentifiabilityResult()


def _slice_measurement_equivalence(
    *,
    dataset: MMMDataset,
    result: ScoreResult,
    peer_results: dict[str, list[ScoreResult]],
    measurement: MeasurementEquivalenceConfig,
) -> tuple[float, float, str | None]:
    if not peer_results:
        return 0.0, 0.0, None
    current = genome_numeric_observables(dataset.genome_index[result.genome_id])
    lowest_margin = float("inf")
    worst_gap = 0.0
    worst_peer: str | None = None
    for peer_slice_id, peer in sorted(peer_results.items()):
        if not peer:
            continue
        peer_current = genome_numeric_observables(dataset.genome_index[peer[0].genome_id])
        shared = sorted(set(current) & set(peer_current))
        differences = [abs(current[name] - peer_current[name]) for name in shared]
        margin = 0.0
        if shared:
            margin = max(
                abs(current[name] - peer_current[name])
                / _effective_measurement_resolution(measurement, name)
                for name in shared
            )
        gap = max(differences, default=0.0)
        if margin < lowest_margin or (
            margin == lowest_margin and (worst_peer is None or peer_slice_id < worst_peer)
        ):
            lowest_margin = margin
            worst_gap = gap
            worst_peer = peer_slice_id
    if lowest_margin == float("inf"):
        return 0.0, 0.0, None
    return lowest_margin, worst_gap, worst_peer


def _predicted_axes_for_genome(dataset: MMMDataset, genome_id: str) -> dict[str, list[float]]:
    genome = dataset.genome_index[genome_id]
    mechanism = _primary_mechanism_for_genome(dataset, genome_id)
    numeric_observables = genome_numeric_observables(genome)
    observable_anchor = (
        mean(min(1.0, math.log1p(abs(value)) / 6.0) for value in numeric_observables.values())
        if numeric_observables
        else 0.5
    )
    parameter_anchor = clamp(len(genome.geometric_parameters) / 10.0)
    time_description = " ".join(
        [
            *mechanism.predicted_observable_signatures,
            *mechanism.rejection_criteria,
        ]
    )
    return {
        "geometry": _project_axis_trace(
            mechanism.expected_scaling_laws.get("geometry"),
            [0.0, 0.5, 1.0],
            observable_anchor,
            parameter_anchor,
        ),
        "temperature": _project_axis_trace(
            mechanism.expected_scaling_laws.get("temperature"),
            [0.0, 0.5, 1.0],
            observable_anchor,
            parameter_anchor,
        ),
        "drive_amplitude": _project_axis_trace(
            mechanism.expected_scaling_laws.get("drive_amplitude"),
            [0.0, 0.5, 1.0],
            observable_anchor,
            parameter_anchor,
        ),
        "time_evolution": _project_axis_trace(
            time_description,
            [0.0, 0.25, 0.5, 0.75, 1.0],
            observable_anchor,
            parameter_anchor,
        ),
    }


def _project_axis_trace(
    description: str | None,
    axis_points: list[float],
    observable_anchor: float,
    parameter_anchor: float,
) -> list[float]:
    scaling_type = infer_expected_scaling_type(description)
    base = clamp(0.2 + (0.5 * observable_anchor) + (0.3 * parameter_anchor))
    amplitude = 0.15 + (0.35 * observable_anchor) + (0.15 * parameter_anchor)
    direction = (
        -1.0
        if description
        and any(
            token in description.lower()
            for token in ["decrease", "decreases", "decay", "weakens", "collapse", "lower"]
        )
        else 1.0
    )
    template = [_scaling_template_value(scaling_type, point) for point in axis_points]
    return [clamp(base + (direction * amplitude * value)) for value in template]


def _slice_scaling_validation(
    *,
    dataset: MMMDataset,
    slice_plan: ResolvedSlicePlan,
    results: list[ScoreResult],
    tolerance: float,
    fallback_axis_name: str,
) -> ScalingValidation:
    axis_name, axis_values_by_candidate = _infer_scaling_axis(dataset, slice_plan, results)
    if axis_values_by_candidate is None:
        return ScalingValidation(
            observed_scaling_type=ScalingType.UNKNOWN,
            expected_scaling_type=ScalingType.UNKNOWN,
            mismatch_score=0.0,
            fit_quality=0.0,
            scaling_axis=None,
            observable_name=None,
        )
    ordered_results = sorted(
        results,
        key=lambda result: (
            axis_values_by_candidate.get(result.genome_id, float("inf")),
            result.genome_id,
        ),
    )
    observable_name, observable_values = _slice_observable_series(
        dataset,
        ordered_results,
        axis_name=axis_name,
    )
    expected = _expected_scaling_type_for_slice(dataset, ordered_results[0].genome_id, axis_name)
    return validate_scaling_behavior(
        [axis_values_by_candidate[result.genome_id] for result in ordered_results],
        observable_values,
        expected_scaling_type=expected,
        tolerance=tolerance,
        scaling_axis=axis_name or fallback_axis_name,
        observable_name=observable_name,
    )


def _slice_observable_series(
    dataset: MMMDataset,
    results: list[ScoreResult],
    *,
    axis_name: str,
) -> tuple[str, list[float]]:
    candidates: dict[str, list[float]] = {}
    for result in results:
        for key, value in genome_numeric_observables(
            dataset.genome_index[result.genome_id]
        ).items():
            if key == axis_name:
                continue
            candidates.setdefault(key, []).append(value)
    viable = [
        (key, values)
        for key, values in candidates.items()
        if len(values) == len(results) and len({round(value, 9) for value in values}) > 1
    ]
    if not viable:
        return "score", [result.score for result in results]
    viable.sort(key=lambda item: (-len(item[1]), -_spread(item[1]), item[0]))
    return viable[0][0], viable[0][1]


def _expected_scaling_type_for_slice(
    dataset: MMMDataset,
    genome_id: str,
    axis_name: str,
) -> ScalingType:
    mechanism = _primary_mechanism_for_genome(dataset, genome_id)
    axis_key = _axis_category(axis_name)
    return infer_expected_scaling_type(mechanism.expected_scaling_laws.get(axis_key))


def _infer_scaling_axis(
    dataset: MMMDataset,
    slice_plan: ResolvedSlicePlan,
    results: list[ScoreResult],
) -> tuple[str, dict[str, float] | None]:
    if slice_plan.lineage.source_field is not None:
        lineage_values = {
            result.genome_id: value
            for result in results
            if (
                value := _candidate_axis_value(
                    dataset, result.genome_id, slice_plan.lineage.source_field
                )
            )
            is not None
        }
        if len(lineage_values) == len(results) and len(set(lineage_values.values())) > 1:
            return slice_plan.lineage.source_field, lineage_values

    structure_ids = {
        dataset.genome_index[result.genome_id].parent_structure_id for result in results
    }
    if len(structure_ids) == 1:
        structure_id = next(iter(structure_ids))
        geometry_models = [
            row for row in dataset.geometry_scaling_models if row.structure_id == structure_id
        ]
        for geometry_model in geometry_models:
            for variable in geometry_model.geometry_variables:
                values = {
                    result.genome_id: value
                    for result in results
                    if (value := _candidate_axis_value(dataset, result.genome_id, variable))
                    is not None
                }
                if len(values) == len(results) and len(set(values.values())) > 1:
                    return variable, values

    numeric_fields: dict[str, dict[str, float]] = {}
    for result in results:
        genome = dataset.genome_index[result.genome_id]
        numeric_fields.setdefault("fabrication_complexity_score", {})[result.genome_id] = float(
            genome.fabrication_complexity_score
        )
        numeric_fields.setdefault("null_risk_score", {})[result.genome_id] = float(
            genome.null_risk_score
        )
        for key, raw_value in genome.geometric_parameters.items():
            if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
                numeric_fields.setdefault(key, {})[result.genome_id] = float(raw_value)

    viable = [
        (key, values)
        for key, values in numeric_fields.items()
        if len(values) == len(results) and len(set(values.values())) > 1
    ]
    if not viable:
        return "rank", None
    viable.sort(key=lambda item: (-_spread(list(item[1].values())), item[0]))
    return viable[0][0], viable[0][1]


def _candidate_axis_value(
    dataset: MMMDataset,
    genome_id: str,
    axis_name: str,
) -> float | None:
    genome = dataset.genome_index[genome_id]
    if axis_name == "fabrication_complexity_score":
        return float(genome.fabrication_complexity_score)
    if axis_name == "null_risk_score":
        return float(genome.null_risk_score)
    value = genome.geometric_parameters.get(axis_name)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _primary_mechanism_for_genome(dataset: MMMDataset, genome_id: str) -> Any:
    genome = dataset.genome_index[genome_id]
    structure = dataset.structure_index[genome.parent_structure_id]
    priority = {"A": 0, "B": 1, "C": 2}
    return min(
        (dataset.mechanism_index[mechanism_id] for mechanism_id in structure.implements_mechanisms),
        key=lambda mechanism: (priority.get(mechanism.priority_tier, 99), mechanism.mechanism_id),
    )


def _axis_category(axis_name: str) -> str:
    lowered = axis_name.lower()
    if "temp" in lowered:
        return "temperature"
    if "drive" in lowered or "amp" in lowered or "power" in lowered:
        return "drive_amplitude"
    if "freq" in lowered or "ghz" in lowered:
        return "frequency"
    return "geometry"


def _scaling_template_value(scaling_type: ScalingType, axis_point: float) -> float:
    if scaling_type == ScalingType.LINEAR:
        return axis_point
    if scaling_type == ScalingType.EXPONENTIAL:
        return (math.exp(3.0 * axis_point) - 1.0) / (math.exp(3.0) - 1.0)
    if scaling_type == ScalingType.SATURATING:
        return (1.0 - math.exp(-3.0 * axis_point)) / (1.0 - math.exp(-3.0))
    return 0.0


def _spread(values: list[float]) -> float:
    if not values:
        return 0.0
    return max(values) - min(values)


def _utility_penalties(
    *,
    null_dominance_classification: NullDominanceClassification,
    identifiability: IdentifiabilityResult,
    scaling_validation: ScalingValidation,
    parameter_penalty_score: float,
) -> UtilityPenaltyTrace:
    null_penalty = (
        1.0
        if (
            null_dominance_classification
            == NullDominanceClassification.DOMINATED_BY_NULL
        )
        else 0.35
        if null_dominance_classification == NullDominanceClassification.INDETERMINATE
        else 0.0
    )
    identifiability_penalty = 0.75 if not identifiability.is_identifiable else 0.0
    return UtilityPenaltyTrace(
        null_model_penalty=null_penalty,
        identifiability_penalty=identifiability_penalty,
        scaling_penalty=scaling_validation.mismatch_score,
        parameter_penalty=parameter_penalty_score,
    )


def generate_refinement_slices(
    manifest: SweepManifest,
    *,
    dataset: MMMDataset,
    tranche_id: str,
) -> list[ResolvedSlicePlan]:
    """Generate deterministic phase-2 refinement slices from observed tranche evidence."""

    if not manifest.adaptive.enabled or not manifest.adaptive.refinement.fields:
        return []

    tranche_plan = _tranche_plan_for(manifest, tranche_id)
    tranche_record = _tranche_record_for(manifest, tranche_id)
    generated: list[ResolvedSlicePlan] = []
    existing_signatures = {
        (slice_plan.resolved_profile, tuple(slice_plan.candidate_ids))
        for slice_plan in tranche_plan.slices
    }
    current_generated = len(
        [slice_plan for slice_plan in tranche_plan.slices if slice_plan.phase == 2]
    )
    max_total = manifest.adaptive.refinement.max_total_refinements_per_tranche
    parents = [
        (slice_plan, slice_record)
        for slice_plan, slice_record in zip(
            tranche_plan.slices, tranche_record.slice_statuses, strict=True
        )
        if slice_plan.phase == 1 and slice_record.status == SliceRunStatus.COMPLETED
    ]
    parents.sort(
        key=lambda item: (
            -item[0].utility.utility_score,
            item[0].lineage.trigger_value or 0.0,
            item[0].slice_id,
        )
    )

    for parent_plan, _ in parents:
        if current_generated >= max_total:
            break
        trigger_metric, trigger_value = _refinement_trigger(manifest, parent_plan)
        if trigger_metric is None:
            continue

        refinements_for_parent = 0
        for field in manifest.adaptive.refinement.fields:
            if refinements_for_parent >= manifest.adaptive.refinement.max_refinements_per_slice:
                break
            candidates = _refinement_candidates(
                parent_plan,
                field,
                dataset,
                categorical_top_values=manifest.adaptive.refinement.categorical_top_values,
            )
            for split_label, refinement_filter, subset_ids in candidates:
                if current_generated >= max_total:
                    break
                if len(subset_ids) < manifest.adaptive.refinement.candidate_count_floor:
                    manifest.decision_log.append(
                        AdaptiveDecisionRecord(
                            phase=2,
                            decision_type=AdaptiveDecisionType.REFINEMENT_SKIPPED,
                            tranche_id=tranche_id,
                            slice_id=parent_plan.slice_id,
                            reason="Candidate subset fell below the configured refinement floor.",
                            metrics={
                                "candidate_count": len(subset_ids),
                                "candidate_floor": (
                                    manifest.adaptive.refinement.candidate_count_floor
                                ),
                            },
                            created_at=datetime.now(UTC),
                        )
                    )
                    continue

                signature = (parent_plan.resolved_profile, tuple(subset_ids))
                if signature in existing_signatures:
                    manifest.decision_log.append(
                        AdaptiveDecisionRecord(
                            phase=2,
                            decision_type=AdaptiveDecisionType.REFINEMENT_SKIPPED,
                            tranche_id=tranche_id,
                            slice_id=parent_plan.slice_id,
                            reason="Refinement would duplicate an existing slice candidate set.",
                            metrics={
                                "candidate_count": len(subset_ids),
                                "source_field": field.value,
                            },
                            created_at=datetime.now(UTC),
                        )
                    )
                    continue

                split_balance = clamp(
                    1.0 - abs((len(subset_ids) / max(parent_plan.candidate_count, 1)) - 0.5) / 0.5
                )
                redundancy_penalty = max(
                    (
                        _candidate_jaccard(subset_ids, other_plan.candidate_ids)
                        for other_plan in [*tranche_plan.slices, *generated]
                    ),
                    default=0.0,
                )
                provisional_results = _rank_slice_candidates(
                    dataset=dataset,
                    profile=parent_plan.resolved_profile,
                    candidate_ids=subset_ids,
                    null_model_enabled=manifest.adaptive.null_model.enabled,
                    baseline_mode=manifest.adaptive.null_model.mode.value,
                    baseline_profile=manifest.adaptive.null_model.baseline_profile,
                    tranche_type=parent_plan.tranche_type,
                )
                peer_provisional_results = {
                    other_plan.slice_id: _rank_slice_candidates(
                        dataset=dataset,
                        profile=other_plan.resolved_profile,
                        candidate_ids=other_plan.candidate_ids,
                        null_model_enabled=manifest.adaptive.null_model.enabled,
                        baseline_mode=manifest.adaptive.null_model.mode.value,
                        baseline_profile=manifest.adaptive.null_model.baseline_profile,
                        tranche_type=other_plan.tranche_type,
                    )
                    for other_plan in [*tranche_plan.slices, *generated]
                    if other_plan.candidate_ids
                }
                planned_utility, _ = _evaluate_slice_utility(
                    dataset=dataset,
                    slice_plan=parent_plan.model_copy(
                        update={"candidate_ids": subset_ids, "candidate_count": len(subset_ids)},
                        deep=True,
                    ),
                    results=provisional_results,
                    peer_results=peer_provisional_results,
                    utility_weights=parent_plan.utility_weights
                    or manifest.adaptive.utility_weights,
                    residual_weights=manifest.residual_weights,
                    candidate_floor=manifest.adaptive.refinement.candidate_count_floor,
                    identifiability_threshold=manifest.identifiability_threshold,
                    scaling_tolerance=manifest.scaling_tolerance,
                    null_model_tolerance=manifest.null_model_tolerance,
                    measurement=manifest.measurement,
                    input_similarity=redundancy_penalty,
                    output_similarity=1.0 - split_balance,
                    utility_basis="planned_refinement",
                    perturbation=PerturbationDiagnostics(),
                )
                slice_id = _unique_generated_slice_id(
                    tranche_plan,
                    f"{parent_plan.slice_id}__ref_{_slugify(field.value)}_{_slugify(split_label)}",
                )
                slice_plan = ResolvedSlicePlan(
                    tranche_id=tranche_id,
                    slice_id=slice_id,
                    phase=2,
                    planning_source=SlicePlanningSource.REFINEMENT,
                    tranche_type=parent_plan.tranche_type,
                    tranche_objective=parent_plan.tranche_objective,
                    resolved_profile=parent_plan.resolved_profile,
                    resolved_parameters=parent_plan.resolved_parameters.model_copy(deep=True),
                    input_registry_scope=parent_plan.input_registry_scope.model_copy(deep=True),
                    candidate_filters=[*parent_plan.candidate_filters, refinement_filter],
                    control_parameters=parent_plan.control_parameters,
                    fixed_parameters=parent_plan.fixed_parameters,
                    max_slices=parent_plan.max_slices,
                    sampling_strategy=parent_plan.sampling_strategy,
                    source_tranche_ids=parent_plan.source_tranche_ids,
                    perturbation_fraction=parent_plan.perturbation_fraction,
                    log_scale_parameters=parent_plan.log_scale_parameters,
                    interaction_mode=parent_plan.interaction_mode,
                    null_pair_id=parent_plan.null_pair_id,
                    parent_slice_id=parent_plan.slice_id,
                    refinement_reason=RefinementReason.ADAPTIVE_REFINEMENT,
                    expected_signature=parent_plan.expected_signature,
                    lineage_depth=parent_plan.lineage_depth + 1,
                    utility_weights=parent_plan.utility_weights,
                    output_requirements=parent_plan.output_requirements.model_copy(deep=True),
                    tags=sorted({*parent_plan.tags, "adaptive", "refinement", field.value}),
                    candidate_ids=subset_ids,
                    candidate_count=len(subset_ids),
                    output_dir=str(Path(tranche_plan.output_dir) / "slices" / slice_id),
                    parameter_hash=_sha256_bytes(
                        json.dumps(
                            {
                                "parent": parent_plan.parameter_hash,
                                "field": field.value,
                                "filter": _candidate_filter_signature(refinement_filter),
                                "candidate_ids": subset_ids,
                            },
                            sort_keys=True,
                        ).encode("utf-8")
                    ),
                    lineage=SliceLineage(
                        phase=2,
                        reason="adaptive_refinement",
                        parent_slice_id=parent_plan.slice_id,
                        parent_slice_ids=[parent_plan.slice_id],
                        null_pair_id=parent_plan.null_pair_id,
                        refinement_reason=RefinementReason.ADAPTIVE_REFINEMENT,
                        source_field=field.value,
                        trigger_metric=trigger_metric,
                        trigger_value=trigger_value,
                        lineage_depth=parent_plan.lineage_depth + 1,
                    ),
                    utility=planned_utility,
                )
                existing_signatures.add(signature)
                generated.append(slice_plan)
                refinements_for_parent += 1
                current_generated += 1
                manifest.decision_log.append(
                    AdaptiveDecisionRecord(
                        phase=2,
                        decision_type=AdaptiveDecisionType.REFINEMENT_GENERATED,
                        tranche_id=tranche_id,
                        slice_id=slice_id,
                        related_slice_ids=[parent_plan.slice_id],
                        reason="Generated phase-2 refinement from observed slice utility.",
                        metrics={
                            "utility_score": planned_utility.utility_score,
                            "trigger_value": trigger_value,
                            "candidate_count": len(subset_ids),
                            "source_field": field.value,
                        },
                        created_at=datetime.now(UTC),
                    )
                )
                if refinements_for_parent >= manifest.adaptive.refinement.max_refinements_per_slice:
                    break
    return generated


def prune_pending_slices(
    manifest: SweepManifest,
    *,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
    tranche_id: str | None = None,
) -> None:
    """Prune low-utility or redundant pending slices while recording the decision."""

    prune_threshold = manifest.adaptive.refinement.utility_prune_threshold
    redundancy_config = manifest.adaptive.redundancy
    minimum_pending = manifest.adaptive.refinement.minimum_pending_per_phase
    now = datetime.now(UTC)
    for current_tranche_plan, current_tranche_record in zip(
        manifest.plan.tranches,
        manifest.tranches,
        strict=True,
    ):
        if tranche_id is not None and current_tranche_plan.tranche_id != tranche_id:
            continue
        indexed_items = list(
            zip(current_tranche_plan.slices, current_tranche_record.slice_statuses, strict=True)
        )
        locked_plans = [
            slice_plan
            for slice_plan, record in indexed_items
            if record.status in {SliceRunStatus.COMPLETED, SliceRunStatus.RUNNING}
        ]
        for phase in sorted({slice_plan.phase for slice_plan, _ in indexed_items}):
            pending_items = [
                (slice_plan, slice_record)
                for slice_plan, slice_record in indexed_items
                if slice_plan.phase == phase and slice_record.status == SliceRunStatus.PENDING
            ]
            if not pending_items:
                continue

            pending_items.sort(key=lambda item: _pruning_sort_key(item[0]))
            retained_plans: list[ResolvedSlicePlan] = []
            pending_total = len(pending_items)
            minimum_retained = min(minimum_pending, pending_total)
            for index, (slice_plan, slice_record) in enumerate(pending_items):
                remaining_after_current = pending_total - index - 1
                pruning = _pruning_decision(
                    manifest=manifest,
                    slice_plan=slice_plan,
                    comparable_plans=[*locked_plans, *retained_plans],
                    slice_results=slice_results,
                    utility_threshold=prune_threshold,
                    redundancy_config=redundancy_config,
                )
                if pruning is None:
                    retained_plans.append(slice_plan)
                    continue

                projected_retained = len(retained_plans) + remaining_after_current
                if projected_retained < minimum_retained:
                    retained_plans.append(slice_plan)
                    manifest.decision_log.append(
                        AdaptiveDecisionRecord(
                            phase=slice_plan.phase,
                            decision_type=AdaptiveDecisionType.PRUNING_RETAINED,
                            tranche_id=slice_plan.tranche_id,
                            slice_id=slice_plan.slice_id,
                            related_slice_ids=pruning.compared_slice_ids,
                            reason=(
                                "Slice retained to preserve the minimum pending frontier for "
                                "this adaptive phase."
                            ),
                            metrics={
                                "minimum_pending_per_phase": minimum_pending,
                                "pending_phase_total": pending_total,
                                "retained_before_current": len(retained_plans) - 1,
                            },
                            created_at=now,
                        )
                    )
                    continue

                pruning.pending_phase_total = pending_total
                pruning.pending_phase_retained = len(retained_plans)
                slice_record.status = SliceRunStatus.PRUNED
                slice_record.completed_at = now
                slice_record.pruning_decision = pruning
                slice_record.utility = slice_plan.utility.model_copy(deep=True)
                manifest.decision_log.append(
                    AdaptiveDecisionRecord(
                        phase=slice_plan.phase,
                        decision_type=AdaptiveDecisionType.SLICE_PRUNED,
                        tranche_id=slice_plan.tranche_id,
                        slice_id=slice_plan.slice_id,
                        related_slice_ids=pruning.compared_slice_ids,
                        reason=pruning.reason or "Slice pruned.",
                        metrics={
                            "utility_score": pruning.utility_score,
                            "utility_threshold": pruning.utility_threshold,
                            "input_similarity": pruning.input_similarity,
                            "output_similarity": pruning.output_similarity,
                            "pending_phase_total": pending_total,
                            "pending_phase_retained": len(retained_plans),
                        },
                        created_at=now,
                    )
                )


def _pruning_sort_key(
    slice_plan: ResolvedSlicePlan,
) -> tuple[float, float, float, float, float, str]:
    return (
        -slice_plan.utility.null_model_delta,
        -slice_plan.utility.identifiability_score,
        -slice_plan.utility.scaling_score,
        slice_plan.utility.parameter_penalty_score,
        -slice_plan.utility.utility_score,
        slice_plan.slice_id,
    )


def _validate_spec_ids(spec: SweepSpec) -> None:
    tranche_ids = [tranche.tranche_id for tranche in spec.tranches]
    if len(tranche_ids) != len(set(tranche_ids)):
        raise SweepPlanningError("Tranche IDs must be unique within a sweep spec.")

    for tranche in spec.tranches:
        slice_ids = [slice_spec.slice_id for slice_spec in tranche.slices]
        if len(slice_ids) != len(set(slice_ids)):
            raise SweepPlanningError(
                f"Slice IDs must be unique within tranche '{tranche.tranche_id}'."
            )


def _resolve_tranche(
    spec: SweepSpec,
    tranche: TrancheSpec,
    dataset: MMMDataset,
    output_root: Path,
    *,
    resolved_tranches: dict[str, ResolvedTranchePlan],
) -> ResolvedTranchePlan:
    shared_profile = tranche.shared_profile or spec.shared_parameters.default_profile
    _validate_profile(shared_profile)

    tranche_dir = output_root / "tranches" / tranche.tranche_id
    hypothesis_fields = _typed_tranche_fields(tranche)
    slice_specs = build_slices_from_tranche(spec, tranche, resolved_tranches, dataset)
    resolved_slices = [
        _resolve_slice(
            spec=spec,
            tranche=tranche,
            shared_profile=shared_profile,
            slice_spec=slice_spec,
            dataset=dataset,
            tranche_dir=tranche_dir,
        )
        for slice_spec in slice_specs
    ]
    return ResolvedTranchePlan(
        tranche_id=tranche.tranche_id,
        objective=tranche.objective,
        tranche_type=tranche.tranche_type,
        tranche_objective=tranche.tranche_objective,
        hypothesis_class=hypothesis_class_for_tranche_type(tranche.tranche_type),
        execution_mode=tranche.execution_mode,
        comparison_strategy=tranche.comparison_strategy,
        shared_profile=shared_profile,
        output_dir=str(tranche_dir),
        control_parameters=list(tranche.control_parameters),
        fixed_parameters=list(tranche.fixed_parameters),
        orthogonal_axes=(
            [axis.model_copy(deep=True) for axis in hypothesis_fields.orthogonal_axes]
            if hypothesis_fields is not None
            else []
        ),
        parameter_count=hypothesis_fields.parameter_count if hypothesis_fields is not None else 0,
        observable_count=hypothesis_fields.observable_count if hypothesis_fields is not None else 0,
        failure_modes=(
            list(cast(FailureModeTrancheFields, hypothesis_fields).failure_modes)
            if isinstance(hypothesis_fields, FailureModeTrancheFields)
            else []
        ),
        device_classes=(
            list(cast(CrossDeviceTrancheFields, hypothesis_fields).device_classes)
            if isinstance(hypothesis_fields, CrossDeviceTrancheFields)
            else []
        ),
        max_slices=tranche.max_slices,
        sampling_strategy=tranche.sampling_strategy,
        source_tranche_ids=list(tranche.source_tranche_ids),
        perturbation_fraction=tranche.perturbation_fraction,
        log_scale_parameters=list(tranche.log_scale_parameters),
        interaction_mode=tranche.interaction_mode,
        expected_signature=tranche.expected_signature,
        utility_weights=tranche.utility_weights or spec.utility_weights,
        discrimination_tranche=tranche.discrimination_tranche,
        scaling_law_tranche=tranche.scaling_law_tranche,
        null_dominance_tranche=tranche.null_dominance_tranche,
        identifiability_tranche=tranche.identifiability_tranche,
        discriminator_tranche=tranche.discriminator_tranche,
        failure_mode_tranche=tranche.failure_mode_tranche,
        cross_device_tranche=tranche.cross_device_tranche,
        boundary_stress_tranche=tranche.boundary_stress_tranche,
        slices=resolved_slices,
    )


def _resolve_slice(
    *,
    spec: SweepSpec,
    tranche: TrancheSpec,
    shared_profile: str,
    slice_spec: SliceSpec,
    dataset: MMMDataset,
    tranche_dir: Path,
) -> ResolvedSlicePlan:
    resolved_profile = slice_spec.profile_override or shared_profile
    _validate_profile(resolved_profile)

    merged_parameters = SweepExecutionParameters(
        default_profile=resolved_profile,
        top_n=slice_spec.parameter_overrides.top_n or spec.shared_parameters.top_n,
    )
    filters = [
        *spec.global_filters,
        *slice_spec.fixed_parameters,
        *slice_spec.candidate_filters,
    ]
    candidate_ids = _resolve_candidate_ids(dataset, slice_spec.input_registry_scope, filters)
    if not candidate_ids:
        raise SweepPlanningError(
            f"Slice '{slice_spec.slice_id}' in tranche "
            f"'{tranche.tranche_id}' resolved to zero candidates."
        )

    parameter_hash = _sha256_bytes(
        json.dumps(
            {
                "profile": resolved_profile,
                "parameters": merged_parameters.model_dump(mode="json"),
                "scope": slice_spec.input_registry_scope.model_dump(mode="json"),
                "filters": [
                    _candidate_filter_signature(filter_spec)
                    for filter_spec in filters
                ],
                "candidate_ids": candidate_ids,
                "source_tranche_ids": sorted(slice_spec.source_tranche_ids),
                "perturbation_fraction": slice_spec.perturbation_fraction,
                "interaction_mode": (
                    slice_spec.interaction_mode.value
                    if slice_spec.interaction_mode is not None
                    else None
                ),
                "orthogonal_axes": [
                    axis.model_dump(mode="json") for axis in slice_spec.orthogonal_axes
                ],
                "parameter_count": slice_spec.parameter_count,
                "observable_count": slice_spec.observable_count,
                "failure_modes": sorted(slice_spec.failure_modes),
                "device_classes": sorted(slice_spec.device_classes),
                "target_hypothesis_pair": sorted(slice_spec.target_hypothesis_pair),
                "discriminator_axis": slice_spec.discriminator_axis,
                "required_resolution": slice_spec.required_resolution,
                "originating_equivalence_cluster_id": (
                    slice_spec.originating_equivalence_cluster_id
                ),
                "predicted_separation": slice_spec.predicted_separation,
                "discriminator_gain": slice_spec.discriminator_gain,
                "axis_cost": slice_spec.axis_cost,
                "redundancy_penalty": slice_spec.redundancy_penalty,
            },
            sort_keys=True,
        ).encode("utf-8")
    )
    phase = _TRANCHE_PHASES.get(tranche.tranche_type, 1)
    lineage_depth = max(slice_spec.lineage_depth, tranche.lineage_depth)
    return ResolvedSlicePlan(
        tranche_id=tranche.tranche_id,
        slice_id=slice_spec.slice_id,
        phase=phase,
        planning_source=SlicePlanningSource.DECLARED,
        tranche_type=slice_spec.tranche_type or tranche.tranche_type,
        tranche_objective=slice_spec.tranche_objective or tranche.tranche_objective,
        hypothesis_class=(
            slice_spec.hypothesis_class or hypothesis_class_for_tranche_type(tranche.tranche_type)
        ),
        resolved_profile=resolved_profile,
        resolved_parameters=merged_parameters,
        input_registry_scope=slice_spec.input_registry_scope,
        candidate_filters=filters,
        control_parameters=list(slice_spec.control_parameters),
        fixed_parameters=list(slice_spec.fixed_parameters),
        orthogonal_axes=[axis.model_copy(deep=True) for axis in slice_spec.orthogonal_axes],
        parameter_count=slice_spec.parameter_count,
        observable_count=slice_spec.observable_count,
        failure_modes=list(slice_spec.failure_modes),
        device_classes=list(slice_spec.device_classes),
        max_slices=slice_spec.max_slices,
        sampling_strategy=slice_spec.sampling_strategy or TrancheSamplingStrategy.EXPLICIT,
        source_tranche_ids=list(slice_spec.source_tranche_ids),
        perturbation_fraction=slice_spec.perturbation_fraction,
        log_scale_parameters=list(slice_spec.log_scale_parameters),
        interaction_mode=slice_spec.interaction_mode,
        null_pair_id=slice_spec.null_pair_id,
        parent_slice_id=slice_spec.parent_slice_id,
        refinement_reason=slice_spec.refinement_reason,
        expected_signature=slice_spec.expected_signature,
        lineage_depth=lineage_depth,
        utility_weights=(
            slice_spec.utility_weights
            or tranche.utility_weights
            or spec.utility_weights
        ),
        output_requirements=slice_spec.output_requirements,
        tags=slice_spec.tags,
        candidate_ids=candidate_ids,
        candidate_count=len(candidate_ids),
        target_hypothesis_pair=list(slice_spec.target_hypothesis_pair),
        discriminator_axis=slice_spec.discriminator_axis,
        required_resolution=slice_spec.required_resolution,
        originating_equivalence_cluster_id=slice_spec.originating_equivalence_cluster_id,
        discriminator_rationale=slice_spec.discriminator_rationale,
        predicted_separation=slice_spec.predicted_separation,
        observed_separation=slice_spec.observed_separation,
        discriminator_gain=slice_spec.discriminator_gain,
        axis_cost=slice_spec.axis_cost,
        redundancy_penalty=slice_spec.redundancy_penalty,
        output_dir=str(tranche_dir / "slices" / slice_spec.slice_id),
        parameter_hash=parameter_hash,
        lineage=SliceLineage(
            phase=phase,
            reason="declared",
            parent_slice_id=slice_spec.parent_slice_id,
            parent_slice_ids=(
                [slice_spec.parent_slice_id] if slice_spec.parent_slice_id is not None else []
            ),
            null_pair_id=slice_spec.null_pair_id,
            refinement_reason=slice_spec.refinement_reason or RefinementReason.DECLARED,
            lineage_depth=lineage_depth,
            null_lineage_lock=(
                slice_spec.null_lineage_lock.model_copy(deep=True)
                if slice_spec.null_lineage_lock is not None
                else None
            ),
            originating_equivalence_cluster_id=slice_spec.originating_equivalence_cluster_id,
            discriminator_rationale=slice_spec.discriminator_rationale,
            predicted_separation=slice_spec.predicted_separation,
            observed_separation=slice_spec.observed_separation,
        ),
    )


def _apply_initial_utilities(
    plan: ResolvedSweepPlan,
    spec: SweepSpec,
    dataset: MMMDataset,
    created_at: datetime,
) -> list[AdaptiveDecisionRecord]:
    decisions: list[AdaptiveDecisionRecord] = []
    for tranche in plan.tranches:
        provisional_results = {
            slice_plan.slice_id: _rank_slice_candidates(
                dataset=dataset,
                profile=slice_plan.resolved_profile,
                candidate_ids=slice_plan.candidate_ids,
                null_model_enabled=spec.adaptive.null_model.enabled,
                baseline_mode=(
                    spec.adaptive.null_model.mode.value
                    if spec.adaptive.null_model.enabled
                    else None
                ),
                baseline_profile=spec.adaptive.null_model.baseline_profile,
                tranche_type=slice_plan.tranche_type,
            )
            for slice_plan in tranche.slices
        }
        for slice_plan in tranche.slices:
            peer_jaccards = [
                _candidate_jaccard(slice_plan.candidate_ids, peer.candidate_ids)
                for peer in tranche.slices
                if peer.slice_id != slice_plan.slice_id
            ]
            input_similarity = max(peer_jaccards, default=0.0)
            utility, _ = _evaluate_slice_utility(
                dataset=dataset,
                slice_plan=slice_plan,
                results=provisional_results[slice_plan.slice_id],
                peer_results={
                    peer_slice_id: peer_scores
                    for peer_slice_id, peer_scores in provisional_results.items()
                    if peer_slice_id != slice_plan.slice_id
                },
                utility_weights=slice_plan.utility_weights or spec.adaptive.utility_weights,
                residual_weights=spec.residual_weights,
                candidate_floor=spec.adaptive.refinement.candidate_count_floor,
                identifiability_threshold=spec.identifiability_threshold,
                scaling_tolerance=spec.scaling_tolerance,
                null_model_tolerance=spec.null_model_tolerance,
                measurement=spec.measurement,
                input_similarity=input_similarity,
                output_similarity=0.0,
                utility_basis="planned_initial",
                perturbation=PerturbationDiagnostics(),
            )
            slice_plan.utility = utility
            decisions.append(
                AdaptiveDecisionRecord(
                    phase=1,
                    decision_type=AdaptiveDecisionType.INITIAL_UTILITY_SEED,
                    tranche_id=tranche.tranche_id,
                    slice_id=slice_plan.slice_id,
                    reason="Initial utility seeded from deterministic QDP slice diagnostics.",
                    metrics={
                        "utility_score": utility.utility_score,
                        "residual_quality_score": utility.residual_quality_score,
                        "null_model_delta": utility.null_model_delta,
                        "identifiability_score": utility.identifiability_score,
                        "scaling_score": utility.scaling_score,
                        "parameter_penalty": utility.parameter_penalty_score,
                        "peer_count": len(peer_jaccards),
                    },
                    created_at=created_at,
                )
            )

    return decisions


def _compute_perturbation_diagnostics(
    *,
    manifest: SweepManifest,
    dataset: MMMDataset,
    slice_plan: ResolvedSlicePlan,
) -> PerturbationDiagnostics:
    config = manifest.adaptive.robustness
    if not manifest.adaptive.enabled or not config.enabled or config.perturbation_runs <= 0:
        return PerturbationDiagnostics()

    base_profile = get_scoring_profile(slice_plan.resolved_profile)
    base_results = rank_dataset_with_profile(
        dataset,
        base_profile,
        candidate_ids=set(slice_plan.candidate_ids),
    )
    base_top_ids = [result.genome_id for result in base_results[: config.top_k]]
    base_rank = {result.genome_id: index for index, result in enumerate(base_results, start=1)}
    winner_matches = 0
    overlaps: list[float] = []
    rank_shifts: list[float] = []
    score_deltas: list[float] = []

    for iteration in range(config.perturbation_runs):
        perturbed_profile = _perturb_profile(
            base_profile,
            seed=manifest.adaptive.seed,
            slice_plan=slice_plan,
            iteration=iteration,
            noise_scale=config.noise_scale,
            target_frequency_shift_ghz=config.target_frequency_shift_ghz,
        )
        perturbed_results = _apply_score_noise(
            rank_dataset_with_profile(
                dataset,
                perturbed_profile,
                candidate_ids=set(slice_plan.candidate_ids),
            ),
            seed=manifest.adaptive.seed,
            slice_plan=slice_plan,
            iteration=iteration,
            noise_scale=config.noise_scale,
        )
        perturbed_top_ids = [result.genome_id for result in perturbed_results[: config.top_k]]
        winner_matches += int(
            bool(
                base_results
                and perturbed_results
                and base_results[0].genome_id == perturbed_results[0].genome_id
            )
        )
        overlaps.append(_set_jaccard(base_top_ids, perturbed_top_ids))
        perturbed_rank = {
            result.genome_id: index for index, result in enumerate(perturbed_results, start=1)
        }
        for genome_id in base_top_ids:
            rank_shifts.append(
                abs(
                    perturbed_rank.get(genome_id, len(perturbed_results))
                    - base_rank.get(genome_id, 0)
                )
                / max(len(base_results), 1)
            )
        base_scores = {result.genome_id: result.score for result in base_results[: config.top_k]}
        perturbed_scores = {
            result.genome_id: result.score for result in perturbed_results[: config.top_k]
        }
        shared_top = set(base_scores) & set(perturbed_scores)
        score_deltas.extend(
            abs(base_scores[genome_id] - perturbed_scores[genome_id]) for genome_id in shared_top
        )

    return PerturbationDiagnostics(
        perturbation_runs=config.perturbation_runs,
        winner_retention=winner_matches / config.perturbation_runs,
        mean_top_k_overlap=mean(overlaps) if overlaps else 1.0,
        mean_rank_shift=mean(rank_shifts) if rank_shifts else 0.0,
        score_noise_sensitivity=mean(score_deltas) if score_deltas else 0.0,
    )


def _perturb_profile(
    profile: ScoringProfile,
    *,
    seed: int,
    slice_plan: ResolvedSlicePlan,
    iteration: int,
    noise_scale: float,
    target_frequency_shift_ghz: float,
) -> ScoringProfile:
    perturbed = profile.model_copy(deep=True)
    freq_noise = (_stable_fraction(seed, slice_plan.slice_id, iteration, "freq") * 2.0) - 1.0
    perturbed.target_frequency_ghz = profile.target_frequency_ghz + (
        freq_noise * target_frequency_shift_ghz
    )
    multipliers = dict(profile.weight_multipliers)
    for feature in sorted(multipliers):
        multiplier_noise = (
            _stable_fraction(seed, slice_plan.slice_id, iteration, feature) * 2.0
        ) - 1.0
        multipliers[feature] = max(
            0.05,
            multipliers[feature] * (1.0 + multiplier_noise * noise_scale),
        )
    perturbed.weight_multipliers = multipliers
    perturbed.profile_id = f"{profile.profile_id}.perturbed.{iteration + 1}"
    return perturbed


def _apply_score_noise(
    results: list[ScoreResult],
    *,
    seed: int,
    slice_plan: ResolvedSlicePlan,
    iteration: int,
    noise_scale: float,
) -> list[ScoreResult]:
    noisy_results: list[ScoreResult] = []
    for result in results:
        noise = (
            (_stable_fraction(seed, slice_plan.slice_id, iteration, result.genome_id) * 2.0) - 1.0
        ) * noise_scale
        noisy_results.append(result.model_copy(update={"score": clamp(result.score + noise)}))
    return sorted(noisy_results, key=lambda item: (-item.score, item.genome_id))


def _rank_stability(results: list[ScoreResult], diagnostics: PerturbationDiagnostics) -> float:
    if diagnostics.perturbation_runs > 0:
        return clamp(
            0.55 * diagnostics.winner_retention
            + 0.30 * diagnostics.mean_top_k_overlap
            + 0.15 * (1.0 - diagnostics.mean_rank_shift)
        )
    if len(results) <= 1:
        return 1.0
    top_score = results[0].score
    comparison_score = results[min(len(results) - 1, 4)].score
    return clamp(0.5 + (top_score - comparison_score))


def _robustness_metric(
    null_model: SliceNullModelComparison,
    diagnostics: PerturbationDiagnostics,
) -> float:
    delta_rate = null_model.positive_delta_rate or 0.0
    delta_signal = clamp(0.5 + 0.5 * (null_model.mean_score_delta or 0.0))
    perturbation_signal = clamp(
        0.50 * diagnostics.mean_top_k_overlap
        + 0.30 * diagnostics.winner_retention
        + 0.20 * (1.0 - diagnostics.score_noise_sensitivity)
    )
    if diagnostics.perturbation_runs <= 0 and not null_model.enabled:
        return 0.5
    if diagnostics.perturbation_runs <= 0:
        return clamp(0.65 * delta_rate + 0.35 * delta_signal)
    return clamp(0.40 * delta_rate + 0.25 * delta_signal + 0.35 * perturbation_signal)


def _refinement_trigger(
    manifest: SweepManifest, slice_plan: ResolvedSlicePlan
) -> tuple[str | None, float]:
    if (
        slice_plan.utility.residual_quality_score
        <= manifest.adaptive.refinement.instability_threshold
    ):
        return "residual_quality_score", slice_plan.utility.residual_quality_score
    scaling_mismatch = 1.0 - slice_plan.utility.scaling_score
    if scaling_mismatch >= manifest.adaptive.refinement.divergence_threshold:
        return "scaling_mismatch", scaling_mismatch
    return None, 0.0


def _refinement_candidates(
    parent_plan: ResolvedSlicePlan,
    field: CandidateFilterField,
    dataset: MMMDataset,
    *,
    categorical_top_values: int,
) -> list[tuple[str, CandidateFilter, list[str]]]:
    values_by_candidate = {
        genome_id: _filter_value(dataset, genome_id, field)
        for genome_id in parent_plan.candidate_ids
    }
    non_null_values = [value for value in values_by_candidate.values() if value is not None]
    if not non_null_values:
        return []

    if field in _NUMERIC_FIELDS and all(_is_numeric_scalar(value) for value in non_null_values):
        numeric_values = sorted(float(value) for value in non_null_values)
        threshold = median(numeric_values)
        lower = sorted(
            [
                genome_id
                for genome_id, value in values_by_candidate.items()
                if _is_numeric_scalar(value) and float(cast(float, value)) <= threshold
            ]
        )
        upper = sorted(
            [
                genome_id
                for genome_id, value in values_by_candidate.items()
                if _is_numeric_scalar(value) and float(cast(float, value)) > threshold
            ]
        )
        return [
            (
                f"lte_{threshold:g}",
                CandidateFilter(field=field, operator=FilterOperator.LTE, value=threshold),
                lower,
            ),
            (
                f"gt_{threshold:g}",
                CandidateFilter(field=field, operator=FilterOperator.GT, value=threshold),
                upper,
            ),
        ]

    counts = Counter(non_null_values)
    candidates: list[tuple[str, CandidateFilter, list[str]]] = []
    for value, _ in sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[
        :categorical_top_values
    ]:
        subset = sorted(
            [
                genome_id
                for genome_id, candidate_value in values_by_candidate.items()
                if candidate_value == value
            ]
        )
        candidates.append(
            (
                f"eq_{_slugify(str(value))}",
                CandidateFilter(field=field, operator=FilterOperator.EQ, value=value),
                subset,
            )
        )
    return candidates


def _pruning_decision(
    *,
    manifest: SweepManifest,
    slice_plan: ResolvedSlicePlan,
    comparable_plans: list[ResolvedSlicePlan],
    slice_results: dict[tuple[str, str], list[ScoreResult]],
    utility_threshold: float,
    redundancy_config: RedundancyPruningConfig,
) -> SlicePruningDecision | None:
    max_input_similarity = max(
        (
            _candidate_jaccard(slice_plan.candidate_ids, other_plan.candidate_ids)
            for other_plan in comparable_plans
        ),
        default=0.0,
    )
    if (
        slice_plan.utility.null_dominance_classification
        == NullDominanceClassification.DOMINATED_BY_NULL
    ):
        return SlicePruningDecision(
            pruned=True,
            reason_code=SlicePruningReasonCode.NULL_DOMINATED,
            reason="Slice failed deterministic null-model dominance.",
            input_similarity=max_input_similarity,
            utility_score=slice_plan.utility.utility_score,
            utility_threshold=utility_threshold,
        )

    if not slice_plan.utility.identifiability.is_identifiable:
        return SlicePruningDecision(
            pruned=True,
            reason_code=SlicePruningReasonCode.NON_IDENTIFIABLE,
            reason=(
                "Slice was not identifiable against a peer slice within the "
                "configured threshold."
            ),
            compared_slice_ids=(
                [slice_plan.utility.identifiability.conflicting_slice_id]
                if slice_plan.utility.identifiability.conflicting_slice_id is not None
                else []
            ),
            input_similarity=max_input_similarity,
            utility_score=slice_plan.utility.utility_score,
            utility_threshold=utility_threshold,
        )

    if slice_plan.utility.utility_score < utility_threshold:
        return SlicePruningDecision(
            pruned=True,
            reason_code=SlicePruningReasonCode.LOW_UTILITY,
            reason="Slice utility fell below the configured pruning threshold.",
            utility_score=slice_plan.utility.utility_score,
            utility_threshold=utility_threshold,
        )

    if not manifest.adaptive.enabled or not redundancy_config.enabled:
        return None

    for other_plan in comparable_plans:
        input_similarity = _candidate_jaccard(slice_plan.candidate_ids, other_plan.candidate_ids)
        other_key = (other_plan.tranche_id, other_plan.slice_id)
        this_key = (slice_plan.tranche_id, slice_plan.slice_id)
        output_similarity = 0.0
        if other_key in slice_results and this_key in slice_results:
            output_similarity = _top_k_jaccard(
                slice_results[this_key],
                slice_results[other_key],
                _tranche_plan_for(manifest, slice_plan.tranche_id).comparison_strategy.top_k,
            )
        combined_similarity = 0.5 * input_similarity + 0.5 * output_similarity
        same_profile = slice_plan.resolved_profile == other_plan.resolved_profile
        should_prune = False
        if same_profile and input_similarity >= redundancy_config.input_similarity_threshold:
            should_prune = True
        if (
            output_similarity >= redundancy_config.output_similarity_threshold
            and combined_similarity >= redundancy_config.combined_similarity_threshold
        ):
            should_prune = True
        if should_prune:
            reason_code = (
                SlicePruningReasonCode.REDUNDANT_INPUT
                if same_profile and input_similarity >= redundancy_config.input_similarity_threshold
                else SlicePruningReasonCode.REDUNDANT_OUTPUT
            )
            return SlicePruningDecision(
                pruned=True,
                reason_code=reason_code,
                reason="Slice was redundant with a higher-priority retained slice.",
                compared_slice_ids=[other_plan.slice_id],
                retained_slice_id=other_plan.slice_id,
                retained_slice_utility=other_plan.utility.utility_score,
                input_similarity=input_similarity,
                output_similarity=output_similarity,
                combined_similarity=combined_similarity,
                utility_score=slice_plan.utility.utility_score,
                utility_threshold=utility_threshold,
            )

    return None


def _slice_plan_for(manifest: SweepManifest, tranche_id: str, slice_id: str) -> ResolvedSlicePlan:
    tranche = _tranche_plan_for(manifest, tranche_id)
    return next(slice_plan for slice_plan in tranche.slices if slice_plan.slice_id == slice_id)


def _tranche_plan_for(manifest: SweepManifest, tranche_id: str) -> ResolvedTranchePlan:
    return next(tranche for tranche in manifest.plan.tranches if tranche.tranche_id == tranche_id)


def _tranche_record_for(manifest: SweepManifest, tranche_id: str) -> TrancheExecutionRecord:
    return next(tranche for tranche in manifest.tranches if tranche.tranche_id == tranche_id)


def _unique_generated_slice_id(tranche: ResolvedTranchePlan, base: str) -> str:
    existing = {slice_plan.slice_id for slice_plan in tranche.slices}
    candidate = base
    suffix = 2
    while candidate in existing:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def _candidate_jaccard(left: list[str], right: list[str]) -> float:
    return _set_jaccard(left, right)


def _top_k_jaccard(left: list[ScoreResult], right: list[ScoreResult], top_k: int) -> float:
    return _set_jaccard(
        [result.genome_id for result in left[:top_k]],
        [result.genome_id for result in right[:top_k]],
    )


def _set_jaccard(left: list[str], right: list[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 1.0
    return len(left_set & right_set) / len(union)


def _combine_utility(
    *,
    residual_weight: float,
    null_weight: float,
    identifiability_weight: float,
    scaling_weight: float,
    parameter_weight: float,
    residual_quality: float,
    null_model_delta: float,
    identifiability_score: float,
    scaling_score: float,
    parameter_penalty_score: float,
    penalties: UtilityPenaltyTrace,
) -> float:
    base_score = weighted_utility_score(
        build_utility_components(
            delta_score=null_model_delta,
            residual_score=residual_quality,
            identifiability_score=identifiability_score,
            scaling_score=scaling_score,
            parameter_penalty=parameter_penalty_score,
        ),
        type(
            "UtilityWeights",
            (),
            {
                "residual_quality": residual_weight,
                "null_model_delta": null_weight,
                "identifiability": identifiability_weight,
                "scaling": scaling_weight,
                "parameter_penalty": parameter_weight,
            },
        )(),
    )
    return clamp(
        base_score
        - (0.20 * penalties.null_model_penalty)
        - (0.20 * penalties.identifiability_penalty)
    )


def _stable_fraction(*parts: object) -> float:
    payload = "::".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64 - 1)


def _is_numeric_scalar(value: ScalarValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _resolve_candidate_ids(
    dataset: MMMDataset,
    scope: RegistryScope,
    filters: list[CandidateFilter],
) -> list[str]:
    candidates = list(dataset.genomes)

    if scope.genome_ids:
        genome_ids = set(scope.genome_ids)
        candidates = [genome for genome in candidates if genome.genome_id in genome_ids]
    if scope.structure_ids:
        structure_ids = set(scope.structure_ids)
        candidates = [
            genome for genome in candidates if genome.parent_structure_id in structure_ids
        ]
    if scope.structure_families:
        structure_families = set(scope.structure_families)
        candidates = [
            genome
            for genome in candidates
            if dataset.structure_index[genome.parent_structure_id].structure_family
            in structure_families
        ]
    if scope.mechanism_ids:
        mechanism_ids = set(scope.mechanism_ids)
        candidates = [
            genome
            for genome in candidates
            if mechanism_ids.intersection(
                dataset.structure_index[genome.parent_structure_id].implements_mechanisms
            )
        ]
    if scope.material_systems:
        material_systems = set(scope.material_systems)
        candidates = [genome for genome in candidates if genome.material_system in material_systems]
    if scope.screening_statuses:
        screening_statuses = {value.lower() for value in scope.screening_statuses}
        candidates = [
            genome for genome in candidates if genome.screening_status.lower() in screening_statuses
        ]
    if scope.topologies:
        topologies = set(scope.topologies)
        candidates = [genome for genome in candidates if genome.lattice_topology in topologies]

    for filter_spec in filters:
        candidates = [
            genome
            for genome in candidates
            if _matches_filter(dataset, genome.genome_id, filter_spec)
        ]

    return sorted(genome.genome_id for genome in candidates)


def _matches_filter(dataset: MMMDataset, genome_id: str, filter_spec: CandidateFilter) -> bool:
    actual = _filter_value(dataset, genome_id, filter_spec.field)

    if filter_spec.operator == FilterOperator.CONTAINS:
        if actual is None:
            return False
        expected_text = cast(ScalarValue, filter_spec.value)
        if not isinstance(actual, str):
            return False
        if not isinstance(expected_text, str):
            return False
        return expected_text.lower() in actual.lower()
    if filter_spec.operator == FilterOperator.IN:
        values = cast(list[ScalarValue], filter_spec.value)
        return _normalize_value(actual) in {_normalize_value(value) for value in values}
    if filter_spec.operator == FilterOperator.NOT_IN:
        values = cast(list[ScalarValue], filter_spec.value)
        return _normalize_value(actual) not in {_normalize_value(value) for value in values}

    expected = cast(ScalarValue, filter_spec.value)
    left = _normalize_value(actual)
    right = _normalize_value(expected)

    if filter_spec.operator == FilterOperator.EQ:
        return left == right
    if filter_spec.operator == FilterOperator.NE:
        return left != right
    if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
        return False
    if filter_spec.operator == FilterOperator.LT:
        return actual < expected
    if filter_spec.operator == FilterOperator.LTE:
        return actual <= expected
    if filter_spec.operator == FilterOperator.GT:
        return actual > expected
    if filter_spec.operator == FilterOperator.GTE:
        return actual >= expected
    raise SweepPlanningError(f"Unsupported filter operator: {filter_spec.operator}")


def _filter_value(dataset: MMMDataset, genome_id: str, field: CandidateFilterField) -> ScalarValue:
    genome = dataset.genome_index[genome_id]
    structure = dataset.structure_index[genome.parent_structure_id]

    match field:
        case CandidateFilterField.FABRICATION_COMPLEXITY:
            return genome.fabrication_complexity_score
        case CandidateFilterField.NULL_RISK:
            return genome.null_risk_score
        case CandidateFilterField.SCREENING_STATUS:
            return genome.screening_status
        case CandidateFilterField.MATERIAL_SYSTEM:
            return genome.material_system
        case CandidateFilterField.STRUCTURE_FAMILY:
            return structure.structure_family
        case CandidateFilterField.PARENT_STRUCTURE_ID:
            return genome.parent_structure_id
        case CandidateFilterField.LATTICE_TOPOLOGY:
            return genome.lattice_topology
        case CandidateFilterField.FABRICATION_EXOTIC:
            return structure.fabrication_requirements.exotic_flag
        case CandidateFilterField.CLEANROOM_LEVEL:
            return structure.fabrication_requirements.cleanroom_level
        case CandidateFilterField.HAS_EM_PREDICTION:
            return any(
                value is not None for value in genome.predicted_electromagnetic_properties.values()
            )
        case CandidateFilterField.HAS_PHONONIC_PREDICTION:
            return any(
                value is not None for value in genome.predicted_phononic_band_structure.values()
            )
        case CandidateFilterField.MICROWAVE_MIN_GHZ:
            rng = structure.operating_frequency_range.microwave_GHz
            return None if rng is None else rng[0]
        case CandidateFilterField.MICROWAVE_MAX_GHZ:
            rng = structure.operating_frequency_range.microwave_GHz
            return None if rng is None else rng[1]
        case CandidateFilterField.PHONONIC_MIN_GHZ:
            rng = structure.operating_frequency_range.phononic_GHz
            return None if rng is None else rng[0]
        case CandidateFilterField.PHONONIC_MAX_GHZ:
            rng = structure.operating_frequency_range.phononic_GHz
            return None if rng is None else rng[1]
    raise SweepPlanningError(f"Unsupported filter field: {field}")


def _normalize_value(value: ScalarValue) -> ScalarValue:
    if isinstance(value, str):
        return value.lower()
    return value


def _validate_profile(profile: str) -> None:
    try:
        get_scoring_profile(profile)
    except ValueError as exc:
        raise SweepPlanningError(str(exc)) from exc


def _resolve_sweep_id(name: str, planned_at: datetime, output_dir: str | Path | None) -> str:
    if output_dir is not None:
        return Path(output_dir).name
    slug = _slugify(name)
    return f"{planned_at.strftime('%Y%m%dT%H%M%SZ')}-{slug}"


def _resolve_output_root(spec: SweepSpec, output_dir: str | Path | None, sweep_id: str) -> Path:
    if output_dir is not None:
        return Path(output_dir).resolve()
    return (Path(spec.default_output_root) / sweep_id).resolve()


def _slugify(value: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", value.lower()).strip("-")
    return normalized or "sweep"


def _build_input_hashes(
    spec: SweepSpec,
    dataset_root: Path,
    spec_source: str | Path | None,
) -> list[InputHashRecord]:
    spec_payload = spec.model_dump(mode="json")
    hashes = [
        InputHashRecord(
            label="sweep_spec",
            source=str(spec_source) if spec_source is not None else "<inline>",
            sha256=_sha256_bytes(json.dumps(spec_payload, sort_keys=True).encode("utf-8")),
        )
    ]

    document_hashes: list[InputHashRecord] = []
    bundle_hasher = hashlib.sha256()
    for spec_name, document_spec in sorted(DOCUMENT_SPECS.items()):
        document_path = dataset_root / document_spec.filename
        digest = _sha256_bytes(document_path.read_bytes())
        bundle_hasher.update(document_spec.filename.encode("utf-8"))
        bundle_hasher.update(digest.encode("utf-8"))
        document_hashes.append(
            InputHashRecord(
                label=spec_name,
                source=str(document_path),
                sha256=digest,
            )
        )

    hashes.append(
        InputHashRecord(
            label="dataset_bundle",
            source=str(dataset_root),
            sha256=bundle_hasher.hexdigest(),
        )
    )
    hashes.extend(document_hashes)
    return hashes


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _candidate_id_hash(candidate_ids: list[str]) -> str:
    return _sha256_bytes(json.dumps(sorted(candidate_ids)).encode("utf-8"))
