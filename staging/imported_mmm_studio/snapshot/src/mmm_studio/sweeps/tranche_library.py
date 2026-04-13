from __future__ import annotations

from .models import (
    BoundaryStressTrancheFields,
    ComparisonStrategy,
    DiscriminationTrancheFields,
    FailureModeTrancheFields,
    IdentifiabilityTrancheFields,
    NullDominanceTrancheFields,
    OrthogonalAxis,
    RefinementReason,
    ScalingLawTrancheFields,
    SliceUtilityWeights,
    TrancheObjective,
    TrancheSamplingStrategy,
    TrancheSpec,
    TrancheType,
)
from .models import CandidateFilterField, FilterOperator
from ..models import ScalingType


def _default_axes() -> list[OrthogonalAxis]:
    return [
        OrthogonalAxis(
            axis_id="fabrication_complexity",
            field=CandidateFilterField.FABRICATION_COMPLEXITY,
            operator=FilterOperator.LTE,
            values=[6, 8],
            axis_family="fabrication_complexity",
            observable_name="score",
        ),
        OrthogonalAxis(
            axis_id="null_risk",
            field=CandidateFilterField.NULL_RISK,
            operator=FilterOperator.LTE,
            values=[4, 6],
            axis_family="null_risk",
            observable_name="score",
        ),
    ]


def _identifiability_axes() -> list[OrthogonalAxis]:
    return [
        OrthogonalAxis(
            axis_id="fabrication_complexity_resolution",
            field=CandidateFilterField.FABRICATION_COMPLEXITY,
            operator=FilterOperator.LTE,
            values=[5, 7],
            axis_family="fabrication_complexity",
            observable_name="score",
        ),
        OrthogonalAxis(
            axis_id="null_risk_resolution",
            field=CandidateFilterField.NULL_RISK,
            operator=FilterOperator.LTE,
            values=[3, 5],
            axis_family="null_risk",
            observable_name="score",
        ),
    ]


def build_discrimination_tranche(
    *,
    tranche_id: str = "mechanism_discrimination",
    shared_profile: str = "manufacturability_aware",
    max_slices: int = 4,
    utility_weights: SliceUtilityWeights | None = None,
) -> TrancheSpec:
    return TrancheSpec(
        tranche_id=tranche_id,
        objective="Probe orthogonal discriminants that separate competing mechanism hypotheses.",
        tranche_type=TrancheType.DISCRIMINATION_TRANCHE,
        tranche_objective=TrancheObjective.HYPOTHESIS_DISCRIMINATION,
        shared_profile=shared_profile,
        sampling_strategy=TrancheSamplingStrategy.GRID,
        max_slices=max_slices,
        utility_weights=utility_weights,
        comparison_strategy=ComparisonStrategy(top_k=5, robustness_top_k=5, leaderboard_size=10),
        discrimination_tranche=DiscriminationTrancheFields(
            primary_hypothesis="primary_mechanism",
            comparator_hypotheses=["artifact_null", "fabrication_bias"],
            orthogonal_axes=_default_axes(),
            parameter_count=2,
            observable_count=3,
            hypothesis_label="standard_discrimination",
        ),
    )


def build_scaling_law_tranche(
    *,
    tranche_id: str = "scaling_law_probe",
    shared_profile: str = "broadband",
    max_slices: int = 4,
) -> TrancheSpec:
    return TrancheSpec(
        tranche_id=tranche_id,
        objective="Resolve scaling-law separation on orthogonal deterministic axes.",
        tranche_type=TrancheType.SCALING_LAW_TRANCHE,
        tranche_objective=TrancheObjective.SCALING_LAW_DISCRIMINATION,
        shared_profile=shared_profile,
        sampling_strategy=TrancheSamplingStrategy.GRID,
        max_slices=max_slices,
        comparison_strategy=ComparisonStrategy(top_k=5, robustness_top_k=5, leaderboard_size=10),
        scaling_law_tranche=ScalingLawTrancheFields(
            orthogonal_axes=_default_axes(),
            parameter_count=2,
            observable_count=3,
            hypothesis_label="scaling_first",
            scaling_axis_id="fabrication_complexity",
            observable_name="score",
            expected_scaling_type=ScalingType.LINEAR,
        ),
        refinement_reason=RefinementReason.SCALING_EXPANSION,
    )


def build_identifiability_tranche(
    *,
    tranche_id: str = "identifiability_probe",
    shared_profile: str = "broadband",
    max_slices: int = 4,
) -> TrancheSpec:
    return TrancheSpec(
        tranche_id=tranche_id,
        objective="Verify that competing slices remain observable-separable on orthogonal axes.",
        tranche_type=TrancheType.IDENTIFIABILITY_TRANCHE,
        tranche_objective=TrancheObjective.IDENTIFIABILITY_RESOLUTION,
        shared_profile=shared_profile,
        sampling_strategy=TrancheSamplingStrategy.GRID,
        max_slices=max_slices,
        comparison_strategy=ComparisonStrategy(top_k=5, robustness_top_k=5, leaderboard_size=10),
        identifiability_tranche=IdentifiabilityTrancheFields(
            orthogonal_axes=_identifiability_axes(),
            parameter_count=2,
            observable_count=3,
            observable_names=["score", "null_model_delta"],
            resolution_threshold=0.08,
            hypothesis_label="identifiability_probe",
        ),
    )


def build_failure_mode_tranche(
    *,
    tranche_id: str = "failure_mode_probe",
    shared_profile: str = "manufacturability_aware",
    max_slices: int = 2,
) -> TrancheSpec:
    return TrancheSpec(
        tranche_id=tranche_id,
        objective="Deliberately sample expected failure regimes to constrain false positives.",
        tranche_type=TrancheType.FAILURE_MODE_TRANCHE,
        tranche_objective=TrancheObjective.FAILURE_MODE_CHARACTERIZATION,
        shared_profile=shared_profile,
        sampling_strategy=TrancheSamplingStrategy.EXPLICIT,
        max_slices=max_slices,
        comparison_strategy=ComparisonStrategy(top_k=5, robustness_top_k=5, leaderboard_size=10),
        failure_mode_tranche=FailureModeTrancheFields(
            orthogonal_axes=_default_axes(),
            parameter_count=2,
            observable_count=3,
            failure_modes=["artifact_risk", "fabrication_fragility"],
            hypothesis_label="failure_mode_probe",
        ),
    )


def build_null_dominance_tranche(
    *,
    source_tranche_ids: list[str],
    tranche_id: str = "null_dominance_controls",
    shared_profile: str = "manufacturability_aware",
    max_slices: int = 6,
) -> TrancheSpec:
    return TrancheSpec(
        tranche_id=tranche_id,
        objective="Mirror discriminative slices as mandatory null-dominance controls.",
        tranche_type=TrancheType.NULL_DOMINANCE_TRANCHE,
        tranche_objective=TrancheObjective.NULL_DOMINANCE_TEST,
        shared_profile=shared_profile,
        sampling_strategy=TrancheSamplingStrategy.SOURCE_COPY,
        max_slices=max_slices,
        source_tranche_ids=source_tranche_ids,
        comparison_strategy=ComparisonStrategy(top_k=5, robustness_top_k=5, leaderboard_size=10),
        null_dominance_tranche=NullDominanceTrancheFields(
            source_tranche_ids=source_tranche_ids,
            required=True,
            parameter_count=2,
            observable_count=3,
            hypothesis_label="null_dominance",
        ),
        refinement_reason=RefinementReason.NULL_PAIR,
    )


def build_boundary_stress_tranche(
    *,
    tranche_id: str = "boundary_stress_probe",
    shared_profile: str = "manufacturability_aware",
    max_slices: int = 4,
) -> TrancheSpec:
    return TrancheSpec(
        tranche_id=tranche_id,
        objective="Push orthogonal axes to boundary conditions to expose brittle regimes.",
        tranche_type=TrancheType.BOUNDARY_STRESS_TRANCHE,
        tranche_objective=TrancheObjective.BOUNDARY_STRESS_CHARACTERIZATION,
        shared_profile=shared_profile,
        sampling_strategy=TrancheSamplingStrategy.GRID,
        max_slices=max_slices,
        comparison_strategy=ComparisonStrategy(top_k=5, robustness_top_k=5, leaderboard_size=10),
        boundary_stress_tranche=BoundaryStressTrancheFields(
            orthogonal_axes=_default_axes(),
            parameter_count=2,
            observable_count=3,
            boundary_modes=["min", "max"],
            tolerance_margin=0.05,
            hypothesis_label="stress_probe",
        ),
    )


def build_preset_tranches(preset: str) -> list[TrancheSpec]:
    normalized = preset.strip().lower()
    if normalized in {"discriminative", "standard", "standard_discriminative"}:
        discrimination = build_discrimination_tranche()
        identifiability = build_identifiability_tranche()
        failure_mode = build_failure_mode_tranche()
        return [
            discrimination,
            identifiability,
            failure_mode,
            build_null_dominance_tranche(
                source_tranche_ids=[
                    discrimination.tranche_id,
                    identifiability.tranche_id,
                    failure_mode.tranche_id,
                ]
            ),
        ]
    if normalized in {"scaling_first", "scaling-heavy"}:
        scaling = build_scaling_law_tranche()
        discrimination = build_discrimination_tranche(tranche_id="discrimination_followup")
        identifiability = build_identifiability_tranche()
        failure_mode = build_failure_mode_tranche()
        return [
            scaling,
            discrimination,
            identifiability,
            failure_mode,
            build_null_dominance_tranche(
                source_tranche_ids=[
                    scaling.tranche_id,
                    discrimination.tranche_id,
                    identifiability.tranche_id,
                    failure_mode.tranche_id,
                ]
            ),
        ]
    if normalized in {"null_dominant", "aggressive"}:
        discrimination = build_discrimination_tranche()
        identifiability = build_identifiability_tranche()
        failure_mode = build_failure_mode_tranche()
        return [
            build_null_dominance_tranche(
                source_tranche_ids=[
                    discrimination.tranche_id,
                    identifiability.tranche_id,
                    failure_mode.tranche_id,
                ],
                max_slices=8,
            ),
            discrimination,
            identifiability,
            failure_mode,
        ]
    if normalized in {"stress_test_heavy", "stress-heavy"}:
        discrimination = build_discrimination_tranche()
        identifiability = build_identifiability_tranche()
        boundary = build_boundary_stress_tranche()
        failure_mode = build_failure_mode_tranche()
        return [
            discrimination,
            identifiability,
            boundary,
            failure_mode,
            build_null_dominance_tranche(
                source_tranche_ids=[
                    discrimination.tranche_id,
                    identifiability.tranche_id,
                    boundary.tranche_id,
                    failure_mode.tranche_id,
                ]
            ),
        ]
    raise ValueError(
        "Unknown sweep preset "
        f"'{preset}'. Expected one of: discriminative, null_dominant, "
        "scaling_first, stress_test_heavy."
    )
