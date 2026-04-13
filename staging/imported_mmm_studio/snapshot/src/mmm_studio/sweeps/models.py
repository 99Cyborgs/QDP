from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from ..models import (
    HypothesisClass,
    IdentifiabilityResult,
    MMMBaseModel,
    NullDominanceClassification,
    ResidualDiagnostics,
    ResidualWeightConfig,
    ScalarValue,
    ScalingType,
    ScalingValidation,
    UtilityComponents,
    VersionedSchema,
)


class TrancheExecutionMode(StrEnum):
    SEQUENTIAL = "sequential"


class TrancheType(StrEnum):
    BASELINE = "baseline"
    NULL_MODEL = "null_model"
    PRIMARY = "primary"
    LOCAL_PERTURBATION = "local_perturbation"
    SCALING = "scaling"
    INTERACTION = "interaction"
    STRESS_TEST = "stress_test"
    DISCRIMINATION_TRANCHE = "discrimination_tranche"
    SCALING_LAW_TRANCHE = "scaling_law_tranche"
    NULL_DOMINANCE_TRANCHE = "null_dominance_tranche"
    IDENTIFIABILITY_TRANCHE = "identifiability_tranche"
    DISCRIMINATOR_TRANCHE = "discriminator_tranche"
    FAILURE_MODE_TRANCHE = "failure_mode_tranche"
    CROSS_DEVICE_TRANCHE = "cross_device_tranche"
    BOUNDARY_STRESS_TRANCHE = "boundary_stress_tranche"


class TrancheObjective(StrEnum):
    BASELINE_REFERENCE = "baseline_reference"
    NULL_DISCRIMINATION = "null_discrimination"
    PRIMARY_DISCOVERY = "primary_discovery"
    LOCAL_STABILITY = "local_stability"
    SCALING_SIGNATURE = "scaling_signature"
    CROSS_TRANCHE_INTERACTION = "cross_tranche_interaction"
    STRESS_BOUNDARY = "stress_boundary"
    HYPOTHESIS_DISCRIMINATION = "hypothesis_discrimination"
    SCALING_LAW_DISCRIMINATION = "scaling_law_discrimination"
    NULL_DOMINANCE_TEST = "null_dominance_test"
    IDENTIFIABILITY_RESOLUTION = "identifiability_resolution"
    ADVERSARIAL_DISCRIMINATION = "adversarial_discrimination"
    FAILURE_MODE_CHARACTERIZATION = "failure_mode_characterization"
    CROSS_DEVICE_CONSISTENCY = "cross_device_consistency"
    BOUNDARY_STRESS_CHARACTERIZATION = "boundary_stress_characterization"


class TrancheSamplingStrategy(StrEnum):
    EXPLICIT = "explicit"
    GRID = "grid"
    LINEAR = "linear"
    LOG = "log"
    SOURCE_COPY = "source_copy"
    TOP_UTILITY = "top_utility"


class InteractionMode(StrEnum):
    INTERSECTION = "intersection"
    UNION = "union"
    BLEND = "blend"


class RefinementReason(StrEnum):
    DECLARED = "declared"
    NULL_PAIR = "null_pair"
    LOCAL_PERTURBATION = "local_perturbation"
    SCALING_EXPANSION = "scaling_expansion"
    INTERACTION_SYNTHESIS = "interaction_synthesis"
    ADAPTIVE_REFINEMENT = "adaptive_refinement"
    PRESET_EXPANSION = "preset_expansion"


class SlicePlanningSource(StrEnum):
    DECLARED = "declared"
    REFINEMENT = "refinement"
    CROSS_TRANCHE = "cross_tranche"


class AdaptiveDecisionType(StrEnum):
    INITIAL_UTILITY_SEED = "initial_utility_seed"
    UTILITY_UPDATE = "utility_update"
    REFINEMENT_GENERATED = "refinement_generated"
    REFINEMENT_SKIPPED = "refinement_skipped"
    SLICE_PRUNED = "slice_pruned"
    PRUNING_RETAINED = "pruning_retained"
    CROSS_TRANCHE_GENERATED = "cross_tranche_generated"
    CROSS_TRANCHE_SKIPPED = "cross_tranche_skipped"
    DISCRIMINATOR_GENERATED = "discriminator_generated"
    DISCRIMINATOR_SKIPPED = "discriminator_skipped"


class NullModelMode(StrEnum):
    ARTIFACT_RISK = "artifact_risk"
    PROFILE = "profile"


class UtilityWarningCode(StrEnum):
    NO_PEER_COMPARISON = "no_peer_comparison"
    SMALL_CANDIDATE_POOL = "small_candidate_pool"
    WEIGHT_CONCENTRATION = "weight_concentration"
    NO_SCALING_AXIS = "no_scaling_axis"
    NO_NULL_BASELINE = "no_null_baseline"
    UNIDENTIFIABLE_SLICE = "unidentifiable_slice"


class TrancheOutcome(StrEnum):
    DISCRIMINATED = "DISCRIMINATED"
    INDETERMINATE_EQUIVALENCE = "INDETERMINATE_EQUIVALENCE"
    INSTRUMENT_LIMITED = "INSTRUMENT_LIMITED"
    EQUIVALENCE_UNBROKEN = "EQUIVALENCE_UNBROKEN"
    DISCRIMINATOR_EXHAUSTED = "DISCRIMINATOR_EXHAUSTED"
    NULL_DOMINANT = "NULL_DOMINANT"
    NULL_EQUIVALENT = "NULL_EQUIVALENT"
    FAILURE_MODE_MATCHED = "FAILURE_MODE_MATCHED"
    SCALING_INCONSISTENT = "SCALING_INCONSISTENT"
    CROSS_DEVICE_UNSTABLE = "CROSS_DEVICE_UNSTABLE"
    BOUNDARY_FRAGILE = "BOUNDARY_FRAGILE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class GovernanceRecommendation(StrEnum):
    PROCEED_TO_REFINEMENT = "PROCEED_TO_REFINEMENT"
    SANDBOX_ONLY = "SANDBOX_ONLY"
    DEFER_FOR_MORE_EVIDENCE = "DEFER_FOR_MORE_EVIDENCE"
    INDETERMINATE_EQUIVALENCE = "INDETERMINATE_EQUIVALENCE"
    INSTRUMENT_LIMITED = "INSTRUMENT_LIMITED"
    REQUIRES_HIGHER_RESOLUTION = "REQUIRES_HIGHER_RESOLUTION"
    REJECT_BY_NULL_DOMINANCE = "REJECT_BY_NULL_DOMINANCE"
    REJECT_BY_FAILURE_MODE_MATCH = "REJECT_BY_FAILURE_MODE_MATCH"
    REJECT_BY_SCALING_INCONSISTENCY = "REJECT_BY_SCALING_INCONSISTENCY"
    DEFER_FOR_CROSS_DEVICE_VALIDATION = "DEFER_FOR_CROSS_DEVICE_VALIDATION"
    REJECT_BY_EQUIVALENCE_COLLAPSE = "REJECT_BY_EQUIVALENCE_COLLAPSE"
    REJECTED_BY_INDISCRIMINABILITY = "REJECTED_BY_INDISCRIMINABILITY"


class SufficiencyIssueCode(StrEnum):
    INSUFFICIENT_ORTHOGONAL_AXIS_DIVERSITY = "INSUFFICIENT_ORTHOGONAL_AXIS_DIVERSITY"
    INSUFFICIENT_NULL_DOMINANCE_COVERAGE = "INSUFFICIENT_NULL_DOMINANCE_COVERAGE"
    INSUFFICIENT_FAILURE_MODE_OPPOSITION = "INSUFFICIENT_FAILURE_MODE_OPPOSITION"
    INSUFFICIENT_BOUNDARY_STRESS_COVERAGE = "INSUFFICIENT_BOUNDARY_STRESS_COVERAGE"
    INSUFFICIENT_CROSS_DEVICE_COVERAGE = "INSUFFICIENT_CROSS_DEVICE_COVERAGE"
    MISSING_ORTHOGONAL_FALSIFIER = "MISSING_ORTHOGONAL_FALSIFIER"
    MEASUREMENT_FEASIBILITY_FAILURE = "MEASUREMENT_FEASIBILITY_FAILURE"
    INSUFFICIENT_SCALING_AXIS_SEPARABILITY = "INSUFFICIENT_SCALING_AXIS_SEPARABILITY"


class AdjudicationGuardrailCode(StrEnum):
    SCALING_LAYOUT_INFLATION = "SCALING_LAYOUT_INFLATION"
    FAILURE_MODE_CONGENIAL_OPPOSITION = "FAILURE_MODE_CONGENIAL_OPPOSITION"
    NULL_EQUIVALENCE_UNDERCOVERED = "NULL_EQUIVALENCE_UNDERCOVERED"
    DISCRIMINATOR_COVERAGE_GAP = "DISCRIMINATOR_COVERAGE_GAP"
    BELOW_MEASUREMENT_RESOLUTION = "BELOW_MEASUREMENT_RESOLUTION"
    EQUIVALENCE_PERSISTS = "EQUIVALENCE_PERSISTS"


class SlicePruningReasonCode(StrEnum):
    LOW_UTILITY = "low_utility"
    NULL_DOMINATED = "null_dominated"
    NON_IDENTIFIABLE = "non_identifiable"
    REDUNDANT_INPUT = "redundant_input"
    REDUNDANT_OUTPUT = "redundant_output"


class FilterOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"


class CandidateFilterField(StrEnum):
    FABRICATION_COMPLEXITY = "fabrication_complexity_score"
    NULL_RISK = "null_risk_score"
    SCREENING_STATUS = "screening_status"
    MATERIAL_SYSTEM = "material_system"
    STRUCTURE_FAMILY = "structure_family"
    PARENT_STRUCTURE_ID = "parent_structure_id"
    LATTICE_TOPOLOGY = "lattice_topology"
    FABRICATION_EXOTIC = "fabrication_exotic"
    CLEANROOM_LEVEL = "cleanroom_level"
    HAS_EM_PREDICTION = "has_em_prediction"
    HAS_PHONONIC_PREDICTION = "has_phononic_prediction"
    MICROWAVE_MIN_GHZ = "microwave_min_ghz"
    MICROWAVE_MAX_GHZ = "microwave_max_ghz"
    PHONONIC_MIN_GHZ = "phononic_min_ghz"
    PHONONIC_MAX_GHZ = "phononic_max_ghz"


class CandidateFilter(MMMBaseModel):
    field: CandidateFilterField
    operator: FilterOperator
    value: ScalarValue | list[ScalarValue]

    @model_validator(mode="after")
    def _validate_operator_value(self) -> CandidateFilter:
        if self.operator in {FilterOperator.IN, FilterOperator.NOT_IN} and not isinstance(
            self.value, list
        ):
            raise ValueError(f"{self.operator.value} requires a list value.")
        if self.operator not in {FilterOperator.IN, FilterOperator.NOT_IN} and isinstance(
            self.value, list
        ):
            raise ValueError(f"{self.operator.value} requires a scalar value.")
        return self


class RegistryScope(MMMBaseModel):
    genome_ids: list[str] = Field(default_factory=list)
    structure_ids: list[str] = Field(default_factory=list)
    structure_families: list[str] = Field(default_factory=list)
    mechanism_ids: list[str] = Field(default_factory=list)
    material_systems: list[str] = Field(default_factory=list)
    screening_statuses: list[str] = Field(default_factory=list)
    topologies: list[str] = Field(default_factory=list)


class SweepExecutionParameters(MMMBaseModel):
    default_profile: str = "broadband"
    top_n: int = Field(default=10, ge=1, le=100)


class SliceParameterOverrides(MMMBaseModel):
    top_n: int | None = Field(default=None, ge=1, le=100)


class SliceOutputRequirements(MMMBaseModel):
    write_leaderboard_csv: bool = True
    write_candidate_report: bool = True
    write_plots: bool = True


class ComparisonStrategy(MMMBaseModel):
    top_k: int = Field(default=5, ge=1, le=20)
    robustness_top_k: int = Field(default=5, ge=1, le=20)
    leaderboard_size: int = Field(default=10, ge=1, le=50)


class TrancheControlParameter(MMMBaseModel):
    name: str
    field: CandidateFilterField
    operator: FilterOperator
    values: list[ScalarValue] = Field(default_factory=list)


class LogScaleParameter(MMMBaseModel):
    name: str
    field: str
    start: float
    stop: float
    steps: int = Field(default=3, ge=1, le=32)
    base: float = Field(default=10.0, gt=1.0)


class OrthogonalAxis(MMMBaseModel):
    axis_id: str
    field: CandidateFilterField
    operator: FilterOperator = FilterOperator.EQ
    values: list[ScalarValue] = Field(default_factory=list, min_length=2)
    axis_family: str | None = None
    observable_name: str | None = None

    @model_validator(mode="after")
    def _validate_axis(self) -> OrthogonalAxis:
        if len({repr(value) for value in self.values}) < 2:
            raise ValueError("Orthogonal axes must define at least two distinct values.")
        if self.axis_family is None:
            self.axis_family = self.field.value
        return self


class HypothesisTrancheBase(MMMBaseModel):
    orthogonal_axes: list[OrthogonalAxis] = Field(default_factory=list)
    parameter_count: int = Field(default=0, ge=0)
    observable_count: int = Field(default=0, ge=0)
    hypothesis_label: str | None = None


class DiscriminationTrancheFields(HypothesisTrancheBase):
    primary_hypothesis: str
    comparator_hypotheses: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_discrimination_axes(self) -> DiscriminationTrancheFields:
        if len({axis.axis_family or axis.field.value for axis in self.orthogonal_axes}) < 2:
            raise ValueError("Discrimination tranches require at least 2 orthogonal axes.")
        return self


class ScalingLawTrancheFields(HypothesisTrancheBase):
    scaling_axis_id: str
    observable_name: str
    expected_scaling_type: ScalingType = ScalingType.UNKNOWN

    @model_validator(mode="after")
    def _validate_scaling_axes(self) -> ScalingLawTrancheFields:
        axis_ids = {axis.axis_id for axis in self.orthogonal_axes}
        if len({axis.axis_family or axis.field.value for axis in self.orthogonal_axes}) < 2:
            raise ValueError("Scaling-law tranches require at least 2 orthogonal axes.")
        if self.scaling_axis_id not in axis_ids:
            raise ValueError("scaling_axis_id must reference one of the configured orthogonal axes.")
        return self


class NullDominanceTrancheFields(HypothesisTrancheBase):
    source_tranche_ids: list[str] = Field(default_factory=list)
    required: bool = True


class IdentifiabilityTrancheFields(HypothesisTrancheBase):
    observable_names: list[str] = Field(default_factory=list, min_length=1)
    resolution_threshold: float = Field(default=0.08, ge=0.0)

    @model_validator(mode="after")
    def _validate_identifiability_axes(self) -> IdentifiabilityTrancheFields:
        if len({axis.axis_family or axis.field.value for axis in self.orthogonal_axes}) < 2:
            raise ValueError("Identifiability tranches require at least 2 orthogonal axes.")
        return self


class DiscriminatorTrancheFields(HypothesisTrancheBase):
    target_hypothesis_pair: list[str] = Field(min_length=2, max_length=2)
    discriminator_axis: str
    expected_separation_signature: str
    required_resolution: float = Field(default=0.05, ge=0.0)
    originating_equivalence_cluster: str | None = None
    discriminator_rationale: str | None = None
    predicted_separation: float = Field(default=0.0, ge=0.0)
    observed_separation: float | None = Field(default=None, ge=0.0)
    discriminator_gain: float = 0.0
    axis_cost: float = 0.0
    redundancy_penalty: float = 0.0
    generation: int = Field(default=1, ge=1, le=8)
    tested_axes: list[str] = Field(default_factory=list)
    rejected_axes: list["RejectedAxisRationale"] = Field(default_factory=list)
    tested_discriminator_axes: list[str] = Field(default_factory=list)
    rejected_discriminator_axes: list[str] = Field(default_factory=list)
    rejected_axis_rationale: list["RejectedAxisRationale"] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_target_pair(self) -> DiscriminatorTrancheFields:
        _normalize_discriminator_axis_contract(self)
        if len(set(self.target_hypothesis_pair)) != 2:
            raise ValueError("Discriminator tranches require two distinct target hypotheses.")
        if not self.orthogonal_axes:
            raise ValueError("Discriminator tranches require at least one discriminator axis.")
        return self


class FailureModeTrancheFields(HypothesisTrancheBase):
    failure_modes: list[str] = Field(default_factory=list, min_length=1)


class CrossDeviceTrancheFields(HypothesisTrancheBase):
    replication_ids: list[str] = Field(default_factory=list)
    device_classes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_cross_device_scope(self) -> CrossDeviceTrancheFields:
        if not self.replication_ids and not self.device_classes:
            raise ValueError("Cross-device tranches require replication_ids or device_classes.")
        return self


class BoundaryStressTrancheFields(HypothesisTrancheBase):
    boundary_modes: list[str] = Field(default_factory=lambda: ["min", "max"], min_length=1)
    tolerance_margin: float = Field(default=0.05, ge=0.0)

    @model_validator(mode="after")
    def _validate_boundary_axes(self) -> BoundaryStressTrancheFields:
        if len({axis.axis_family or axis.field.value for axis in self.orthogonal_axes}) < 2:
            raise ValueError("Boundary-stress tranches require at least 2 orthogonal axes.")
        return self


def _configured_typed_tranche_fields(model: object) -> dict[str, object]:
    configured: dict[str, object] = {}
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
        value = getattr(model, field_name, None)
        if value is not None:
            configured[field_name] = value
    return configured


_TYPED_TRANCHE_FIELD_BY_TYPE = {
    TrancheType.DISCRIMINATION_TRANCHE: "discrimination_tranche",
    TrancheType.SCALING_LAW_TRANCHE: "scaling_law_tranche",
    TrancheType.NULL_DOMINANCE_TRANCHE: "null_dominance_tranche",
    TrancheType.IDENTIFIABILITY_TRANCHE: "identifiability_tranche",
    TrancheType.DISCRIMINATOR_TRANCHE: "discriminator_tranche",
    TrancheType.FAILURE_MODE_TRANCHE: "failure_mode_tranche",
    TrancheType.CROSS_DEVICE_TRANCHE: "cross_device_tranche",
    TrancheType.BOUNDARY_STRESS_TRANCHE: "boundary_stress_tranche",
}


def hypothesis_class_for_tranche_type(tranche_type: TrancheType) -> HypothesisClass:
    match tranche_type:
        case TrancheType.DISCRIMINATION_TRANCHE:
            return HypothesisClass.DISCRIMINATION
        case TrancheType.SCALING_LAW_TRANCHE:
            return HypothesisClass.SCALING_LAW
        case TrancheType.NULL_DOMINANCE_TRANCHE:
            return HypothesisClass.NULL_DOMINANCE
        case TrancheType.IDENTIFIABILITY_TRANCHE:
            return HypothesisClass.IDENTIFIABILITY
        case TrancheType.DISCRIMINATOR_TRANCHE:
            return HypothesisClass.DISCRIMINATION
        case TrancheType.FAILURE_MODE_TRANCHE:
            return HypothesisClass.FAILURE_MODE
        case TrancheType.CROSS_DEVICE_TRANCHE:
            return HypothesisClass.CROSS_DEVICE
        case TrancheType.BOUNDARY_STRESS_TRANCHE:
            return HypothesisClass.BOUNDARY_STRESS
        case _:
            return HypothesisClass.LEGACY


class ExpectedSignature(MMMBaseModel):
    label: str | None = None
    observable_name: str | None = None
    scaling_type: ScalingType = ScalingType.UNKNOWN


class SliceUtilityWeights(MMMBaseModel):
    residual_quality: float = Field(default=0.30, ge=0.0)
    null_model_delta: float = Field(default=0.25, ge=0.0)
    identifiability: float = Field(default=0.20, ge=0.0)
    scaling: float = Field(default=0.15, ge=0.0)
    parameter_penalty: float = Field(default=0.10, ge=0.0)

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_weights(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if any(
            key in value
            for key in [
                "residual_quality",
                "null_model_delta",
                "identifiability",
                "scaling",
                "parameter_penalty",
            ]
        ):
            return value
        legacy_rank = float(value.get("rank_stability", 0.0))
        legacy_divergence = float(value.get("cross_slice_divergence", 0.0))
        legacy_robustness = float(value.get("robustness", 0.0))
        legacy_penalty = float(value.get("redundancy_penalty", 0.0))
        if legacy_rank or legacy_divergence or legacy_robustness or legacy_penalty:
            return {
                "residual_quality": legacy_rank,
                "null_model_delta": legacy_robustness,
                "identifiability": legacy_divergence / 2.0,
                "scaling": legacy_divergence / 2.0,
                "parameter_penalty": legacy_penalty,
            }
        return value

    @model_validator(mode="after")
    def _validate_weight_sum(self) -> SliceUtilityWeights:
        total = (
            self.residual_quality
            + self.null_model_delta
            + self.identifiability
            + self.scaling
            + self.parameter_penalty
        )
        if total <= 0:
            raise ValueError("Slice utility weights must sum to a positive value.")
        return self


class AdaptiveNullModelConfig(MMMBaseModel):
    enabled: bool = False
    mode: NullModelMode = NullModelMode.ARTIFACT_RISK
    baseline_profile: str | None = None


class RobustnessExpansionConfig(MMMBaseModel):
    enabled: bool = False
    perturbation_runs: int = Field(default=4, ge=0, le=16)
    noise_scale: float = Field(default=0.03, ge=0.0, le=0.25)
    target_frequency_shift_ghz: float = Field(default=0.20, ge=0.0, le=2.0)
    top_k: int = Field(default=5, ge=1, le=20)


class AdaptiveRefinementConfig(MMMBaseModel):
    fields: list[CandidateFilterField] = Field(default_factory=list)
    max_refinements_per_slice: int = Field(default=2, ge=1, le=10)
    max_total_refinements_per_tranche: int = Field(default=4, ge=1, le=50)
    candidate_count_floor: int = Field(default=3, ge=1)
    minimum_pending_per_phase: int = Field(default=1, ge=0, le=10)
    instability_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    divergence_threshold: float = Field(default=0.30, ge=0.0, le=1.0)
    utility_prune_threshold: float = Field(default=0.20, ge=0.0, le=1.0)
    categorical_top_values: int = Field(default=2, ge=1, le=5)


class RedundancyPruningConfig(MMMBaseModel):
    enabled: bool = False
    input_similarity_threshold: float = Field(default=0.92, ge=0.0, le=1.0)
    output_similarity_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    combined_similarity_threshold: float = Field(default=0.91, ge=0.0, le=1.0)


class CrossTrancheConfig(MMMBaseModel):
    enabled: bool = False
    priority_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    max_source_slices_per_tranche: int = Field(default=1, ge=1, le=10)
    max_interaction_slices: int = Field(default=4, ge=1, le=20)
    min_candidate_count: int = Field(default=2, ge=1)


class BoundedNoiseModel(MMMBaseModel):
    mode: str = "bounded"
    absolute_bound: float = Field(default=0.01, ge=0.0)
    relative_bound: float = Field(default=0.0, ge=0.0, le=1.0)


class MeasurementEnvelope(MMMBaseModel):
    resolution_vector: dict[str, float] = Field(default_factory=dict)
    noise_model: BoundedNoiseModel = Field(default_factory=BoundedNoiseModel)
    bandwidth: float = Field(default=1.0, gt=0.0)
    sampling_window: float = Field(default=1.0, gt=0.0)


class MeasurementEquivalenceConfig(MMMBaseModel):
    noise_floor: float = Field(default=0.01, ge=0.0)
    sampling_bandwidth: float = Field(default=1.0, gt=0.0)
    observable_resolution: float = Field(default=0.01, ge=0.0)
    equivalence_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    discriminator_generation_limit: int = Field(default=2, ge=0, le=8)
    max_discriminators_per_generation: int = Field(default=2, ge=1, le=8)
    discriminator_gain_threshold: float = Field(default=0.05, ge=0.0)
    axis_correlation_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    measurement_envelope: MeasurementEnvelope = Field(default_factory=MeasurementEnvelope)

    @model_validator(mode="after")
    def _synchronize_measurement_envelope(self) -> MeasurementEquivalenceConfig:
        resolution_vector = dict(self.measurement_envelope.resolution_vector)
        if not resolution_vector:
            resolution_vector["__default__"] = self.observable_resolution
            object.__setattr__(
                self,
                "measurement_envelope",
                self.measurement_envelope.model_copy(
                    update={
                        "resolution_vector": resolution_vector,
                        "noise_model": self.measurement_envelope.noise_model.model_copy(
                            update={"absolute_bound": self.noise_floor}
                        ),
                        "bandwidth": self.sampling_bandwidth,
                    }
                ),
            )
        else:
            object.__setattr__(
                self,
                "observable_resolution",
                resolution_vector.get("__default__", min(resolution_vector.values())),
            )
            object.__setattr__(
                self,
                "noise_floor",
                self.measurement_envelope.noise_model.absolute_bound,
            )
            object.__setattr__(self, "sampling_bandwidth", self.measurement_envelope.bandwidth)
        return self


class AdaptiveSearchConfig(MMMBaseModel):
    enabled: bool = False
    seed: int = 0
    utility_weights: SliceUtilityWeights = Field(default_factory=SliceUtilityWeights)
    null_model: AdaptiveNullModelConfig = Field(default_factory=AdaptiveNullModelConfig)
    robustness: RobustnessExpansionConfig = Field(default_factory=RobustnessExpansionConfig)
    refinement: AdaptiveRefinementConfig = Field(default_factory=AdaptiveRefinementConfig)
    redundancy: RedundancyPruningConfig = Field(default_factory=RedundancyPruningConfig)
    cross_tranche: CrossTrancheConfig = Field(default_factory=CrossTrancheConfig)


class SliceSpec(MMMBaseModel):
    slice_id: str
    tranche_type: TrancheType | None = None
    tranche_objective: TrancheObjective | None = None
    hypothesis_class: HypothesisClass | None = None
    input_registry_scope: RegistryScope = Field(default_factory=RegistryScope)
    candidate_filters: list[CandidateFilter] = Field(default_factory=list)
    control_parameters: list[TrancheControlParameter] = Field(default_factory=list)
    fixed_parameters: list[CandidateFilter] = Field(default_factory=list)
    orthogonal_axes: list[OrthogonalAxis] = Field(default_factory=list)
    parameter_count: int = Field(default=0, ge=0)
    observable_count: int = Field(default=0, ge=0)
    failure_modes: list[str] = Field(default_factory=list)
    device_classes: list[str] = Field(default_factory=list)
    profile_override: str | None = None
    max_slices: int | None = Field(default=None, ge=1, le=256)
    sampling_strategy: TrancheSamplingStrategy | None = None
    source_tranche_ids: list[str] = Field(default_factory=list)
    perturbation_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    log_scale_parameters: list[LogScaleParameter] = Field(default_factory=list)
    interaction_mode: InteractionMode | None = None
    null_pair_id: str | None = None
    parent_slice_id: str | None = None
    refinement_reason: RefinementReason | None = None
    expected_signature: ExpectedSignature | None = None
    lineage_depth: int = Field(default=0, ge=0, le=32)
    utility_weights: SliceUtilityWeights | None = None
    parameter_overrides: SliceParameterOverrides = Field(default_factory=SliceParameterOverrides)
    output_requirements: SliceOutputRequirements = Field(default_factory=SliceOutputRequirements)
    tags: list[str] = Field(default_factory=list)
    null_lineage_lock: NullLineageLock | None = None
    target_hypothesis_pair: list[str] = Field(default_factory=list)
    discriminator_axis: str | None = None
    required_resolution: float | None = Field(default=None, ge=0.0)
    originating_equivalence_cluster_id: str | None = None
    discriminator_rationale: str | None = None
    predicted_separation: float | None = Field(default=None, ge=0.0)
    observed_separation: float | None = Field(default=None, ge=0.0)
    discriminator_gain: float | None = None
    axis_cost: float | None = None
    redundancy_penalty: float | None = None


class TrancheSpec(MMMBaseModel):
    tranche_id: str
    objective: str
    tranche_type: TrancheType = TrancheType.PRIMARY
    tranche_objective: TrancheObjective = TrancheObjective.PRIMARY_DISCOVERY
    execution_mode: TrancheExecutionMode = TrancheExecutionMode.SEQUENTIAL
    shared_profile: str | None = None
    slices: list[SliceSpec] = Field(default_factory=list)
    control_parameters: list[TrancheControlParameter] = Field(default_factory=list)
    fixed_parameters: list[CandidateFilter] = Field(default_factory=list)
    max_slices: int | None = Field(default=None, ge=1, le=256)
    sampling_strategy: TrancheSamplingStrategy = TrancheSamplingStrategy.EXPLICIT
    source_tranche_ids: list[str] = Field(default_factory=list)
    perturbation_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    log_scale_parameters: list[LogScaleParameter] = Field(default_factory=list)
    interaction_mode: InteractionMode | None = None
    null_pair_id: str | None = None
    parent_slice_id: str | None = None
    refinement_reason: RefinementReason | None = None
    expected_signature: ExpectedSignature | None = None
    lineage_depth: int = Field(default=0, ge=0, le=32)
    utility_weights: SliceUtilityWeights | None = None
    comparison_strategy: ComparisonStrategy = Field(default_factory=ComparisonStrategy)
    discrimination_tranche: DiscriminationTrancheFields | None = None
    scaling_law_tranche: ScalingLawTrancheFields | None = None
    null_dominance_tranche: NullDominanceTrancheFields | None = None
    identifiability_tranche: IdentifiabilityTrancheFields | None = None
    discriminator_tranche: DiscriminatorTrancheFields | None = None
    failure_mode_tranche: FailureModeTrancheFields | None = None
    cross_device_tranche: CrossDeviceTrancheFields | None = None
    boundary_stress_tranche: BoundaryStressTrancheFields | None = None

    @model_validator(mode="after")
    def _validate_typed_tranche_schema(self) -> TrancheSpec:
        configured = _configured_typed_tranche_fields(self)
        expected_field = _TYPED_TRANCHE_FIELD_BY_TYPE.get(self.tranche_type)
        if expected_field is None:
            if configured:
                raise ValueError(
                    "Legacy tranche types cannot declare typed hypothesis tranche fields."
                )
            return self
        if set(configured) != {expected_field}:
            raise ValueError(
                f"{self.tranche_type.value} requires only '{expected_field}' to be populated."
            )
        return self


class SweepSpec(VersionedSchema):
    schema_name: str = "mmm_studio.sweep_spec"
    name: str
    description: str
    version: str
    default_output_root: str = "artifacts/runs/sweeps"
    global_filters: list[CandidateFilter] = Field(default_factory=list)
    shared_parameters: SweepExecutionParameters = Field(default_factory=SweepExecutionParameters)
    residual_weights: ResidualWeightConfig = Field(default_factory=ResidualWeightConfig)
    identifiability_threshold: float = Field(default=0.08, ge=0.0)
    scaling_tolerance: float = Field(default=0.20, ge=0.0)
    null_model_tolerance: float = Field(default=0.05, ge=0.0)
    measurement: MeasurementEquivalenceConfig = Field(default_factory=MeasurementEquivalenceConfig)
    enforce_identifiability: bool = False
    require_null_dominance: bool = False
    minimum_orthogonal_axes: int = Field(default=2, ge=0, le=12)
    tranche_type: TrancheType | None = None
    tranche_objective: TrancheObjective | None = None
    control_parameters: list[TrancheControlParameter] = Field(default_factory=list)
    fixed_parameters: list[CandidateFilter] = Field(default_factory=list)
    max_slices: int | None = Field(default=None, ge=1, le=256)
    sampling_strategy: TrancheSamplingStrategy | None = None
    source_tranche_ids: list[str] = Field(default_factory=list)
    perturbation_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    log_scale_parameters: list[LogScaleParameter] = Field(default_factory=list)
    interaction_mode: InteractionMode | None = None
    null_pair_id: str | None = None
    parent_slice_id: str | None = None
    refinement_reason: RefinementReason | None = None
    expected_signature: ExpectedSignature | None = None
    lineage_depth: int = Field(default=0, ge=0, le=32)
    utility_weights: SliceUtilityWeights | None = None
    adaptive: AdaptiveSearchConfig = Field(default_factory=AdaptiveSearchConfig)
    tranches: list[TrancheSpec]


class SufficiencyIssue(MMMBaseModel):
    code: SufficiencyIssueCode
    message: str
    tranche_ids: list[str] = Field(default_factory=list)
    observed_value: float | None = None
    required_value: float | None = None


class PlanSufficiencyAssessment(MMMBaseModel):
    passes: bool = True
    orthogonal_axis_family_count: int = 0
    null_dominance_source_coverage: float = 1.0
    failure_mode_coverage_count: int = 0
    boundary_stress_coverage_count: int = 0
    cross_device_coverage_count: int = 0
    discriminator_tranche_count: int = 0
    orthogonal_falsifier_present: bool = False
    measurement_feasible: bool = True
    scaling_axis_separable: bool = True
    issues: list[SufficiencyIssue] = Field(default_factory=list)


class NullLineageLock(MMMBaseModel):
    source_tranche_id: str
    source_slice_id: str
    source_parameter_hash: str | None = None
    source_candidate_ids_sha256: str
    source_candidate_count: int = 0
    source_lineage_depth: int = 0


class SliceLineage(MMMBaseModel):
    phase: int = 1
    reason: str = "declared"
    parent_slice_id: str | None = None
    parent_slice_ids: list[str] = Field(default_factory=list)
    null_pair_id: str | None = None
    refinement_reason: RefinementReason | None = None
    source_field: str | None = None
    trigger_metric: str | None = None
    trigger_value: float | None = None
    lineage_depth: int = 0
    null_lineage_lock: NullLineageLock | None = None
    originating_equivalence_cluster_id: str | None = None
    discriminator_rationale: str | None = None
    predicted_separation: float | None = None
    observed_separation: float | None = None


class PerturbationDiagnostics(MMMBaseModel):
    perturbation_runs: int = 0
    winner_retention: float = 1.0
    mean_top_k_overlap: float = 1.0
    mean_rank_shift: float = 0.0
    score_noise_sensitivity: float = 0.0


class UtilityPenaltyTrace(MMMBaseModel):
    null_model_penalty: float = 0.0
    identifiability_penalty: float = 0.0
    scaling_penalty: float = 0.0
    parameter_penalty: float = 0.0


class SliceUtilityTrace(MMMBaseModel):
    rank_weight: float = 0.0
    divergence_weight: float = 0.0
    robustness_weight: float = 0.0
    redundancy_weight: float = 0.0
    scaling_weight: float = 0.0
    rank_contribution: float = 0.0
    divergence_contribution: float = 0.0
    robustness_contribution: float = 0.0
    redundancy_contribution: float = 0.0
    scaling_contribution: float = 0.0
    residual_weights: ResidualWeightConfig = Field(default_factory=ResidualWeightConfig)
    utility_components: UtilityComponents = Field(default_factory=UtilityComponents)
    penalties: UtilityPenaltyTrace = Field(default_factory=UtilityPenaltyTrace)
    residual_diagnostics: ResidualDiagnostics = Field(default_factory=ResidualDiagnostics)
    null_residual_diagnostics: ResidualDiagnostics = Field(default_factory=ResidualDiagnostics)
    null_dominance_classification: NullDominanceClassification = (
        NullDominanceClassification.INDETERMINATE
    )
    identifiability: IdentifiabilityResult = Field(default_factory=IdentifiabilityResult)
    scaling_validation: ScalingValidation = Field(default_factory=ScalingValidation)
    parameter_count: int = 0
    unconstrained_parameter_count: int = 0
    scaling_axis: str | None = None
    observable_name: str | None = None
    primary_fit_quality: float = 0.0
    null_fit_quality: float = 0.0
    measurement_signal_gap: float = 0.0
    measurement_resolution_floor: float = 0.0
    equivalence_margin: float = 0.0
    measurement_conflicting_slice_id: str | None = None
    candidate_count: int = 0
    peer_count: int = 0
    warning_codes: list[UtilityWarningCode] = Field(default_factory=list)


class SliceUtility(MMMBaseModel):
    utility_score: float = 0.0
    rank_stability: float = 0.0
    cross_slice_divergence: float = 0.0
    robustness_metric: float = 0.0
    redundancy_penalty: float = 0.0
    scaling_score: float = 0.0
    residual_quality_score: float = 0.0
    null_model_delta: float = 0.0
    identifiability_score: float = 0.0
    measurement_equivalence_score: float = 0.0
    equivalence_margin: float = 0.0
    parameter_penalty_score: float = 0.0
    input_similarity: float = 0.0
    output_similarity: float = 0.0
    utility_basis: str = "planned"
    residual_diagnostics: ResidualDiagnostics = Field(default_factory=ResidualDiagnostics)
    null_residual_diagnostics: ResidualDiagnostics = Field(default_factory=ResidualDiagnostics)
    null_dominance_classification: NullDominanceClassification = (
        NullDominanceClassification.INDETERMINATE
    )
    identifiability: IdentifiabilityResult = Field(default_factory=IdentifiabilityResult)
    scaling_validation: ScalingValidation = Field(default_factory=ScalingValidation)
    utility_components: UtilityComponents = Field(default_factory=UtilityComponents)
    parameter_count: int = 0
    unconstrained_parameter_count: int = 0
    perturbation: PerturbationDiagnostics = Field(default_factory=PerturbationDiagnostics)
    trace: SliceUtilityTrace = Field(default_factory=SliceUtilityTrace)


class SliceNullModelComparison(MMMBaseModel):
    enabled: bool = False
    requested: bool = False
    available: bool = False
    mode: str | None = None
    baseline_profile: str | None = None
    candidate_count: int = 0
    baseline_candidate_count: int = 0
    baseline_top_candidate_id: str | None = None
    baseline_top_score: float | None = None
    top_candidate_primary_score: float | None = None
    top_candidate_baseline_score: float | None = None
    top_candidate_delta: float | None = None
    mean_baseline_score: float | None = None
    mean_score_delta: float | None = None
    positive_delta_rate: float | None = None
    residual_diagnostics: ResidualDiagnostics = Field(default_factory=ResidualDiagnostics)
    null_residual_diagnostics: ResidualDiagnostics = Field(default_factory=ResidualDiagnostics)
    primary_fit_quality: float | None = None
    null_fit_quality: float | None = None
    delta_fit_quality: float | None = None
    residual_quality_score: float | None = None
    null_residual_quality_score: float | None = None
    delta_residual: float | None = None
    dominance_classification: NullDominanceClassification = (
        NullDominanceClassification.INDETERMINATE
    )
    within_tolerance: bool = False
    winner_changed: bool = False
    missing_reason: str | None = None


class SlicePruningDecision(MMMBaseModel):
    pruned: bool = False
    reason_code: SlicePruningReasonCode | None = None
    reason: str | None = None
    compared_slice_ids: list[str] = Field(default_factory=list)
    retained_slice_id: str | None = None
    retained_slice_utility: float | None = None
    input_similarity: float | None = None
    output_similarity: float | None = None
    combined_similarity: float | None = None
    utility_score: float | None = None
    utility_threshold: float | None = None
    pending_phase_total: int | None = None
    pending_phase_retained: int | None = None
    protected_by_exploration_floor: bool = False


class ResolvedSlicePlan(MMMBaseModel):
    tranche_id: str
    slice_id: str
    phase: int = 1
    planning_source: SlicePlanningSource = SlicePlanningSource.DECLARED
    tranche_type: TrancheType = TrancheType.PRIMARY
    tranche_objective: TrancheObjective = TrancheObjective.PRIMARY_DISCOVERY
    hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    resolved_profile: str
    resolved_parameters: SweepExecutionParameters
    input_registry_scope: RegistryScope
    candidate_filters: list[CandidateFilter]
    control_parameters: list[TrancheControlParameter] = Field(default_factory=list)
    fixed_parameters: list[CandidateFilter] = Field(default_factory=list)
    orthogonal_axes: list[OrthogonalAxis] = Field(default_factory=list)
    parameter_count: int = 0
    observable_count: int = 0
    failure_modes: list[str] = Field(default_factory=list)
    device_classes: list[str] = Field(default_factory=list)
    max_slices: int | None = None
    sampling_strategy: TrancheSamplingStrategy = TrancheSamplingStrategy.EXPLICIT
    source_tranche_ids: list[str] = Field(default_factory=list)
    perturbation_fraction: float | None = None
    log_scale_parameters: list[LogScaleParameter] = Field(default_factory=list)
    interaction_mode: InteractionMode | None = None
    null_pair_id: str | None = None
    parent_slice_id: str | None = None
    refinement_reason: RefinementReason | None = None
    expected_signature: ExpectedSignature | None = None
    lineage_depth: int = 0
    utility_weights: SliceUtilityWeights | None = None
    output_requirements: SliceOutputRequirements
    tags: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    candidate_count: int = 0
    target_hypothesis_pair: list[str] = Field(default_factory=list)
    discriminator_axis: str | None = None
    required_resolution: float | None = Field(default=None, ge=0.0)
    originating_equivalence_cluster_id: str | None = None
    discriminator_rationale: str | None = None
    predicted_separation: float | None = Field(default=None, ge=0.0)
    observed_separation: float | None = Field(default=None, ge=0.0)
    discriminator_gain: float | None = None
    axis_cost: float | None = None
    redundancy_penalty: float | None = None
    output_dir: str
    parameter_hash: str | None = None
    lineage: SliceLineage = Field(default_factory=SliceLineage)
    utility: SliceUtility = Field(default_factory=SliceUtility)


class ResolvedTranchePlan(MMMBaseModel):
    tranche_id: str
    objective: str
    tranche_type: TrancheType = TrancheType.PRIMARY
    tranche_objective: TrancheObjective = TrancheObjective.PRIMARY_DISCOVERY
    hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    execution_mode: TrancheExecutionMode
    comparison_strategy: ComparisonStrategy
    shared_profile: str
    output_dir: str
    control_parameters: list[TrancheControlParameter] = Field(default_factory=list)
    fixed_parameters: list[CandidateFilter] = Field(default_factory=list)
    orthogonal_axes: list[OrthogonalAxis] = Field(default_factory=list)
    parameter_count: int = 0
    observable_count: int = 0
    failure_modes: list[str] = Field(default_factory=list)
    device_classes: list[str] = Field(default_factory=list)
    max_slices: int | None = None
    sampling_strategy: TrancheSamplingStrategy = TrancheSamplingStrategy.EXPLICIT
    source_tranche_ids: list[str] = Field(default_factory=list)
    perturbation_fraction: float | None = None
    log_scale_parameters: list[LogScaleParameter] = Field(default_factory=list)
    interaction_mode: InteractionMode | None = None
    expected_signature: ExpectedSignature | None = None
    utility_weights: SliceUtilityWeights | None = None
    discrimination_tranche: DiscriminationTrancheFields | None = None
    scaling_law_tranche: ScalingLawTrancheFields | None = None
    null_dominance_tranche: NullDominanceTrancheFields | None = None
    identifiability_tranche: IdentifiabilityTrancheFields | None = None
    discriminator_tranche: DiscriminatorTrancheFields | None = None
    failure_mode_tranche: FailureModeTrancheFields | None = None
    cross_device_tranche: CrossDeviceTrancheFields | None = None
    boundary_stress_tranche: BoundaryStressTrancheFields | None = None
    slices: list[ResolvedSlicePlan]


class ResolvedSweepPlan(MMMBaseModel):
    sweep_name: str
    description: str
    version: str
    dataset_root: str
    output_root: str
    adaptive_enabled: bool = False
    plan_identity: str | None = None
    sufficiency: PlanSufficiencyAssessment = Field(default_factory=PlanSufficiencyAssessment)
    tranches: list[ResolvedTranchePlan]


class SliceRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PRUNED = "pruned"


class SweepRunStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_FAILURES = "completed_with_failures"
    FAILED = "failed"


class InputHashRecord(MMMBaseModel):
    label: str
    source: str
    sha256: str


class SliceExecutionRecord(MMMBaseModel):
    tranche_id: str
    slice_id: str
    phase: int = 1
    tranche_type: TrancheType = TrancheType.PRIMARY
    tranche_objective: TrancheObjective = TrancheObjective.PRIMARY_DISCOVERY
    hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    status: SliceRunStatus = SliceRunStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    candidate_count: int = 0
    top_candidate_id: str | None = None
    top_score: float | None = None
    priority_order: int | None = None
    execution_order: int | None = None
    null_pair_id: str | None = None
    parent_slice_id: str | None = None
    lineage_depth: int = 0
    output_dir: str
    parameter_hash: str | None = None
    utility: SliceUtility = Field(default_factory=SliceUtility)
    score_breakdown: UtilityComponents = Field(default_factory=UtilityComponents)
    null_model_comparison: SliceNullModelComparison = Field(
        default_factory=SliceNullModelComparison
    )
    null_lineage_lock_verified: bool | None = None
    null_lineage_source: str | None = None
    pruning_decision: SlicePruningDecision | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    error_message: str | None = None


class TrancheExecutionRecord(MMMBaseModel):
    tranche_id: str
    tranche_type: TrancheType = TrancheType.PRIMARY
    tranche_objective: TrancheObjective = TrancheObjective.PRIMARY_DISCOVERY
    hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    status: SweepRunStatus = SweepRunStatus.PLANNED
    output_dir: str
    slice_statuses: list[SliceExecutionRecord] = Field(default_factory=list)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    metrics_summary: dict[str, ScalarValue] = Field(default_factory=dict)


class AdaptiveDecisionRecord(MMMBaseModel):
    phase: int
    decision_type: AdaptiveDecisionType
    tranche_id: str | None = None
    slice_id: str | None = None
    related_slice_ids: list[str] = Field(default_factory=list)
    reason: str
    metrics: dict[str, ScalarValue] = Field(default_factory=dict)
    created_at: datetime


class ExecutionPriorityEntry(MMMBaseModel):
    tranche_id: str
    slice_id: str
    phase: int
    tranche_type: TrancheType = TrancheType.PRIMARY
    hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    utility_score: float
    priority_order: int
    queue_serial: int | None = None
    null_pair_id: str | None = None
    parent_slice_id: str | None = None
    lineage_depth: int = 0
    tie_break_policy: str = "utility_desc,phase_asc,queue_serial_asc"
    source: str


class SweepManifest(VersionedSchema):
    schema_name: str = "mmm_studio.sweep_manifest"
    sweep_id: str
    sweep_name: str
    description: str
    spec_version: str
    status: SweepRunStatus = SweepRunStatus.PLANNED
    output_root: str
    dataset_root: str
    command: str
    planned_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    residual_weights: ResidualWeightConfig = Field(default_factory=ResidualWeightConfig)
    identifiability_threshold: float = Field(default=0.08, ge=0.0)
    scaling_tolerance: float = Field(default=0.20, ge=0.0)
    null_model_tolerance: float = Field(default=0.05, ge=0.0)
    measurement: MeasurementEquivalenceConfig = Field(default_factory=MeasurementEquivalenceConfig)
    input_hashes: list[InputHashRecord] = Field(default_factory=list)
    adaptive: AdaptiveSearchConfig = Field(default_factory=AdaptiveSearchConfig)
    plan: ResolvedSweepPlan
    tranches: list[TrancheExecutionRecord] = Field(default_factory=list)
    execution_order: list[ExecutionPriorityEntry] = Field(default_factory=list)
    decision_log: list[AdaptiveDecisionRecord] = Field(default_factory=list)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    metrics_summary: dict[str, ScalarValue] = Field(default_factory=dict)


class SliceWinner(MMMBaseModel):
    tranche_id: str
    slice_id: str
    scoring_profile: str
    candidate_id: str | None = None
    parent_structure_id: str | None = None
    score: float | None = None
    decision_band: str | None = None
    candidate_count: int = 0
    status: SliceRunStatus


class SliceComparison(MMMBaseModel):
    tranche_id: str
    left_slice_id: str
    right_slice_id: str
    top_k: int
    overlap_count: int
    jaccard_index: float
    shared_top_candidates: list[str] = Field(default_factory=list)
    left_only_candidates: list[str] = Field(default_factory=list)
    right_only_candidates: list[str] = Field(default_factory=list)
    same_winner: bool = False


class CandidateAggregate(MMMBaseModel):
    genome_id: str
    parent_structure_id: str
    slice_ids: list[str] = Field(default_factory=list)
    tranche_ids: list[str] = Field(default_factory=list)
    successful_slice_count: int = 0
    top_k_appearances: int = 0
    win_count: int = 0
    mean_rank: float
    best_rank: int
    worst_rank: int
    rank_span: int
    mean_score: float
    score_stddev: float
    robustness_score: float
    profile_sensitivity_score: float


class TrancheWinnerConsistency(MMMBaseModel):
    dominant_candidate_id: str | None = None
    dominant_win_count: int = 0
    successful_slice_count: int = 0
    winner_consistency_ratio: float = 0.0


class AdaptiveAuditSummary(MMMBaseModel):
    initial_utility_seeds: int = 0
    utility_updates: int = 0
    refinements_generated: int = 0
    refinements_skipped: int = 0
    slices_pruned: int = 0
    pruning_retained: int = 0
    cross_tranche_generated: int = 0
    cross_tranche_skipped: int = 0
    utility_warning_slices: int = 0


class ResidualStructureSummary(MMMBaseModel):
    autocorrelation_scores: list[float] = Field(default_factory=list)
    spectral_scores: list[float] = Field(default_factory=list)
    burst_scores: list[float] = Field(default_factory=list)
    decay_deviation_scores: list[float] = Field(default_factory=list)
    residual_quality_scores: list[float] = Field(default_factory=list)


class NullModelSummary(MMMBaseModel):
    requested_slices: int = 0
    available_slices: int = 0
    winner_changed_slices: int = 0
    mean_top_candidate_delta: float | None = None
    mean_score_delta: float | None = None
    positive_delta_rate: float | None = None
    dominated_by_null_slices: int = 0
    indeterminate_slices: int = 0
    improves_over_null_slices: int = 0
    mean_delta_residual: float | None = None
    mean_delta_fit_quality: float | None = None


class IdentifiabilitySummary(MMMBaseModel):
    evaluated_slices: int = 0
    failure_count: int = 0


class ScalingSummary(MMMBaseModel):
    evaluated_slices: int = 0
    match_count: int = 0
    mismatch_count: int = 0
    match_rate: float | None = None


class TopSliceSummary(MMMBaseModel):
    tranche_id: str
    slice_id: str
    utility_score: float = 0.0
    total_utility: float = 0.0
    top_candidate_id: str | None = None
    top_score: float | None = None


class UtilityDistributionSummary(MMMBaseModel):
    min_utility: float | None = None
    max_utility: float | None = None
    mean_utility: float | None = None
    median_utility: float | None = None


class NullModelWinLossSummary(MMMBaseModel):
    wins: int = 0
    losses: int = 0
    indeterminate: int = 0


class UnstableRegionSummary(MMMBaseModel):
    tranche_id: str
    slice_id: str
    reason: str
    utility_score: float = 0.0
    residual_score: float = 0.0
    scaling_score: float = 0.0
    null_delta: float = 0.0


class MechanismSeparationEntry(MMMBaseModel):
    left_tranche_id: str
    left_slice_id: str
    right_tranche_id: str
    right_slice_id: str
    separation_score: float = 0.0
    shared_winner: bool = False


class ScalingConsistencyEntry(MMMBaseModel):
    tranche_id: str
    hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    consistency_score: float = 0.0
    mean_scaling_score: float = 0.0
    evaluated_slices: int = 0


class NullModelWinRateEntry(MMMBaseModel):
    tranche_class: HypothesisClass = HypothesisClass.LEGACY
    win_rate: float = 0.0
    win_count: int = 0
    total_count: int = 0


class DegeneracyCluster(MMMBaseModel):
    cluster_id: str
    tranche_ids: list[str] = Field(default_factory=list)
    slice_ids: list[str] = Field(default_factory=list)
    hypothesis_classes: list[HypothesisClass] = Field(default_factory=list)
    mean_identifiability_score: float = 0.0


class EquivalenceFingerprint(MMMBaseModel):
    fingerprint_id: str
    dominant_candidate_id: str | None = None
    winner_consistency_ratio: float = 0.0
    mean_null_equivalence_score: float = 0.0
    mean_failure_mode_match_score: float = 0.0
    mean_scaling_separation_score: float = 0.0
    mean_identifiability_score: float = 0.0
    mean_measurement_equivalence_score: float = 0.0
    mean_equivalence_margin: float = 0.0
    mean_utility_score: float = 0.0
    null_dominance_losses: int = 0
    scaling_mismatches: int = 0
    identifiability_failures: int = 0


class EquivalenceEdge(MMMBaseModel):
    edge_id: str
    left_tranche_id: str
    left_slice_id: str
    right_tranche_id: str
    right_slice_id: str
    left_hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    right_hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    equivalence_margin: float = 0.0
    measurement_equivalence_score: float = 0.0
    tested_axes: list[str] = Field(default_factory=list)


class EquivalenceGraph(MMMBaseModel):
    nodes: list[str] = Field(default_factory=list)
    edges: list[EquivalenceEdge] = Field(default_factory=list)


class EquivalenceCluster(MMMBaseModel):
    cluster_id: str
    tranche_ids: list[str] = Field(default_factory=list)
    slice_ids: list[str] = Field(default_factory=list)
    hypothesis_classes: list[HypothesisClass] = Field(default_factory=list)
    fingerprint_ids: list[str] = Field(default_factory=list)
    reason: str
    similarity_score: float = 1.0
    measurement_equivalence_score: float = 0.0
    equivalence_margin: float = 0.0


class RejectedAxisRationale(MMMBaseModel):
    axis_key: str
    reason: str
    redundancy_penalty: float | None = None
    correlation: float | None = None
    blocking_axis: str | None = None


def _copy_rejected_axis_rationale(
    items: list[RejectedAxisRationale],
) -> list[RejectedAxisRationale]:
    return [item.model_copy(deep=True) for item in items]


def _normalize_discriminator_axis_contract(model: object) -> None:
    tested_axes = list(
        getattr(model, "tested_discriminator_axes", [])
        or getattr(model, "tested_axes", [])
    )
    object.__setattr__(model, "tested_discriminator_axes", tested_axes)
    object.__setattr__(model, "tested_axes", list(tested_axes))

    rationale_items = _copy_rejected_axis_rationale(
        list(
            getattr(model, "rejected_axis_rationale", [])
            or getattr(model, "rejected_axes", [])
        )
    )
    object.__setattr__(
        model,
        "rejected_axis_rationale",
        _copy_rejected_axis_rationale(rationale_items),
    )
    object.__setattr__(model, "rejected_axes", _copy_rejected_axis_rationale(rationale_items))

    rejected_axes = list(getattr(model, "rejected_discriminator_axes", []))
    if not rejected_axes:
        rejected_axes = [item.axis_key for item in rationale_items]
    object.__setattr__(model, "rejected_discriminator_axes", list(dict.fromkeys(rejected_axes)))


def _default_measurement_config_provenance(model: object) -> None:
    if (
        getattr(model, "measurement_config", None) is not None
        and getattr(model, "measurement_config_provenance", None) is None
    ):
        object.__setattr__(model, "measurement_config_provenance", "manifest.measurement")


class DiscriminatorHistoryEntry(MMMBaseModel):
    tranche_id: str
    generation: int = 1
    target_hypothesis_pair: list[str] = Field(default_factory=list)
    discriminator_axis: str
    discriminator_gain: float = 0.0
    axis_cost: float = 0.0
    redundancy_penalty: float = 0.0
    predicted_separation: float = 0.0
    observed_separation: float | None = None
    outcome: TrancheOutcome | None = None
    originating_equivalence_cluster: str | None = None
    discriminator_rationale: str | None = None
    tested_axes: list[str] = Field(default_factory=list)
    rejected_axes: list[RejectedAxisRationale] = Field(default_factory=list)
    tested_discriminator_axes: list[str] = Field(default_factory=list)
    rejected_discriminator_axes: list[str] = Field(default_factory=list)
    rejected_axis_rationale: list[RejectedAxisRationale] = Field(default_factory=list)
    measurement_config: MeasurementEquivalenceConfig | None = None
    measurement_config_provenance: str | None = None
    stop_reason: TrancheOutcome | None = None

    @model_validator(mode="after")
    def _normalize_compatibility_fields(self) -> DiscriminatorHistoryEntry:
        _normalize_discriminator_axis_contract(self)
        _default_measurement_config_provenance(self)
        return self


class AdjudicationEvidence(MMMBaseModel):
    metric: str
    source: str
    value: ScalarValue


class AdjudicationGuardrail(MMMBaseModel):
    code: AdjudicationGuardrailCode
    message: str
    source: str
    blocked_recommendation: GovernanceRecommendation | None = None


class TrancheAdjudication(MMMBaseModel):
    tranche_id: str
    hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    outcomes: list[TrancheOutcome] = Field(default_factory=list)
    recommendation: GovernanceRecommendation = GovernanceRecommendation.DEFER_FOR_MORE_EVIDENCE
    evidence: list[AdjudicationEvidence] = Field(default_factory=list)
    guardrails: list[AdjudicationGuardrail] = Field(default_factory=list)
    fingerprint: EquivalenceFingerprint | None = None
    equivalent_to_tranche_ids: list[str] = Field(default_factory=list)
    weakest_unresolved_edges: list[EquivalenceEdge] = Field(default_factory=list)
    discriminator_history: list[DiscriminatorHistoryEntry] = Field(default_factory=list)
    measurement_config: MeasurementEquivalenceConfig | None = None
    measurement_config_provenance: str | None = None
    discriminator_stop_reason: TrancheOutcome | None = None
    promotion_blocked: bool = False
    promotion_block_reason: str | None = None

    @model_validator(mode="after")
    def _normalize_compatibility_fields(self) -> TrancheAdjudication:
        _default_measurement_config_provenance(self)
        return self


class HypothesisAdjudication(MMMBaseModel):
    hypothesis_class: HypothesisClass = HypothesisClass.LEGACY
    tranche_ids: list[str] = Field(default_factory=list)
    outcomes: list[TrancheOutcome] = Field(default_factory=list)
    recommendation: GovernanceRecommendation = GovernanceRecommendation.DEFER_FOR_MORE_EVIDENCE
    evidence: list[AdjudicationEvidence] = Field(default_factory=list)
    equivalent_to_hypothesis_classes: list[HypothesisClass] = Field(default_factory=list)
    discriminator_stop_reason: TrancheOutcome | None = None
    promotion_blocked: bool = False
    promotion_block_reason: str | None = None


class SweepAdjudication(MMMBaseModel):
    recommendation: GovernanceRecommendation = GovernanceRecommendation.DEFER_FOR_MORE_EVIDENCE
    tranche_adjudications: list[TrancheAdjudication] = Field(default_factory=list)
    hypothesis_adjudications: list[HypothesisAdjudication] = Field(default_factory=list)
    equivalence_clusters: list[EquivalenceCluster] = Field(default_factory=list)
    equivalence_graph: EquivalenceGraph = Field(default_factory=EquivalenceGraph)
    weakest_unresolved_edges: list[EquivalenceEdge] = Field(default_factory=list)
    discriminator_history: list[DiscriminatorHistoryEntry] = Field(default_factory=list)
    measurement_config: MeasurementEquivalenceConfig | None = None
    measurement_config_provenance: str | None = None
    discriminator_stop_reason: TrancheOutcome | None = None
    promotion_blocked: bool = False
    promotion_block_reason: str | None = None

    @model_validator(mode="after")
    def _normalize_compatibility_fields(self) -> SweepAdjudication:
        _default_measurement_config_provenance(self)
        return self


class TrancheSummary(VersionedSchema):
    schema_name: str = "mmm_studio.tranche_summary"
    sweep_id: str
    tranche_id: str
    objective: str
    status: SweepRunStatus
    successful_slices: int
    failed_slices: int
    pruned_slices: int = 0
    slice_records: list[SliceExecutionRecord] = Field(default_factory=list)
    slice_winners: list[SliceWinner] = Field(default_factory=list)
    candidate_leaderboard: list[CandidateAggregate] = Field(default_factory=list)
    overlap_matrix: list[SliceComparison] = Field(default_factory=list)
    winner_consistency: TrancheWinnerConsistency = Field(default_factory=TrancheWinnerConsistency)
    adaptive_audit: AdaptiveAuditSummary = Field(default_factory=AdaptiveAuditSummary)
    residual_structure_summary: ResidualStructureSummary = Field(
        default_factory=ResidualStructureSummary
    )
    null_model_summary: NullModelSummary = Field(default_factory=NullModelSummary)
    identifiability_summary: IdentifiabilitySummary = Field(default_factory=IdentifiabilitySummary)
    scaling_summary: ScalingSummary = Field(default_factory=ScalingSummary)
    top_slices: list[TopSliceSummary] = Field(default_factory=list)
    utility_distribution: UtilityDistributionSummary = Field(
        default_factory=UtilityDistributionSummary
    )
    null_model_win_loss: NullModelWinLossSummary = Field(default_factory=NullModelWinLossSummary)
    unstable_regions: list[UnstableRegionSummary] = Field(default_factory=list)
    mechanism_separation_matrix: list[MechanismSeparationEntry] = Field(default_factory=list)
    scaling_consistency_map: list[ScalingConsistencyEntry] = Field(default_factory=list)
    null_model_win_rate_by_tranche_class: list[NullModelWinRateEntry] = Field(default_factory=list)
    degeneracy_clusters: list[DegeneracyCluster] = Field(default_factory=list)
    consistent_top_performers: list[str] = Field(default_factory=list)
    profile_sensitive_candidates: list[str] = Field(default_factory=list)
    adjudication: TrancheAdjudication | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    legacy_contract_downgrade: bool = False
    legacy_contract_notes: list[str] = Field(default_factory=list)


class TrancheIndexEntry(MMMBaseModel):
    tranche_id: str
    status: SweepRunStatus
    output_dir: str
    summary_path: str | None = None
    slice_ids: list[str] = Field(default_factory=list)


class SweepSummary(VersionedSchema):
    schema_name: str = "mmm_studio.sweep_summary"
    sweep_id: str
    sweep_name: str
    generated_at: datetime
    successful_slices: int
    failed_slices: int
    pruned_slices: int = 0
    aggregate_rankings: list[CandidateAggregate] = Field(default_factory=list)
    per_slice_winners: list[SliceWinner] = Field(default_factory=list)
    cross_slice_comparisons: list[SliceComparison] = Field(default_factory=list)
    tranches: list[TrancheSummary] = Field(default_factory=list)
    adaptive_audit: AdaptiveAuditSummary = Field(default_factory=AdaptiveAuditSummary)
    residual_structure_summary: ResidualStructureSummary = Field(
        default_factory=ResidualStructureSummary
    )
    null_model_summary: NullModelSummary = Field(default_factory=NullModelSummary)
    identifiability_summary: IdentifiabilitySummary = Field(default_factory=IdentifiabilitySummary)
    scaling_summary: ScalingSummary = Field(default_factory=ScalingSummary)
    top_slices: list[TopSliceSummary] = Field(default_factory=list)
    utility_distribution: UtilityDistributionSummary = Field(
        default_factory=UtilityDistributionSummary
    )
    null_model_win_loss: NullModelWinLossSummary = Field(default_factory=NullModelWinLossSummary)
    unstable_regions: list[UnstableRegionSummary] = Field(default_factory=list)
    mechanism_separation_matrix: list[MechanismSeparationEntry] = Field(default_factory=list)
    scaling_consistency_map: list[ScalingConsistencyEntry] = Field(default_factory=list)
    null_model_win_rate_by_tranche_class: list[NullModelWinRateEntry] = Field(default_factory=list)
    degeneracy_clusters: list[DegeneracyCluster] = Field(default_factory=list)
    consistent_top_performers: list[str] = Field(default_factory=list)
    profile_sensitive_candidates: list[str] = Field(default_factory=list)
    sufficiency: PlanSufficiencyAssessment = Field(default_factory=PlanSufficiencyAssessment)
    adjudication: SweepAdjudication = Field(default_factory=SweepAdjudication)
    equivalence_clusters: list[EquivalenceCluster] = Field(default_factory=list)
    weakest_edges: list[EquivalenceEdge] = Field(default_factory=list)
    discriminator_history: list[DiscriminatorHistoryEntry] = Field(default_factory=list)
    summary_highlights: list[str] = Field(default_factory=list)
    legacy_contract_downgrade: bool = False
    legacy_contract_notes: list[str] = Field(default_factory=list)
