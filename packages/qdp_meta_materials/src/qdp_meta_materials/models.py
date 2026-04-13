from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

ScalarValue: TypeAlias = str | int | float | bool | None
NumericValue: TypeAlias = int | float
NumericRange: TypeAlias = tuple[NumericValue, NumericValue]


class MMMBaseModel(BaseModel):
    """Strict base model used across the extracted metamaterials core."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class VersionedSchema(MMMBaseModel):
    """Versioned schema surface used for generated artifacts and APIs."""

    schema_name: str
    schema_version: str = "1.0"


class ArtifactMeta(MMMBaseModel):
    program_id: str
    program_name: str
    module_acronym: str
    version: str
    generated_on: date
    governance_rules: list[str]
    artifact_id: str


class ArtifactDocument(MMMBaseModel):
    artifact: ArtifactMeta


class Genome(MMMBaseModel):
    genome_id: str
    parent_structure_id: str
    lattice_topology: str
    material_system: str
    geometric_parameters: dict[str, ScalarValue] = Field(default_factory=dict)
    predicted_electromagnetic_properties: dict[str, ScalarValue] = Field(default_factory=dict)
    predicted_phononic_band_structure: dict[str, ScalarValue] = Field(default_factory=dict)
    fabrication_complexity_score: int = Field(ge=1, le=10)
    null_risk_score: int = Field(ge=1, le=10)
    screening_status: str
    notes: str = ""


class GenomeFile(ArtifactDocument):
    parameter_schema: dict[str, Any]
    genomes: list[Genome]


class RankingFeature(MMMBaseModel):
    feature: str
    range: NumericRange
    definition: str


class DecisionBand(MMMBaseModel):
    band: str
    score_min: float
    requirements: list[str]


class RankingModel(MMMBaseModel):
    model_id: str
    name: str
    objective_direction: str
    score_formula: str
    feature_definitions: list[RankingFeature]
    hard_reject_rules: list[str]
    decision_bands: list[DecisionBand]


class RankingModelFile(ArtifactDocument):
    ranking_model: RankingModel


class TargetDecoherenceChannels(MMMBaseModel):
    primary: list[str]
    secondary: list[str] = Field(default_factory=list)


class FabricationFeasibility(MMMBaseModel):
    standard_academic_cleanroom: bool
    dilution_refrigerator_compatible: bool
    millikelvin_compatible: bool
    exotic_fabrication_flag: bool
    gating_notes: str


class Mechanism(MMMBaseModel):
    mechanism_id: str
    name: str
    mechanism_class: str
    priority_tier: str
    status: str
    physical_principle: str
    target_decoherence_channels: TargetDecoherenceChannels
    predicted_observable_ids: list[str]
    predicted_observable_signatures: list[str]
    expected_scaling_laws: dict[str, str]
    device_compatibility: dict[str, str]
    fabrication_feasibility: FabricationFeasibility
    experimental_protocol_ids: list[str]
    validation_rule_ids: list[str]
    baseline_null_priority: list[str]
    related_structure_ids: list[str]
    rejection_criteria: list[str]
    literature_basis: list[str]


class MechanismRegistryFile(ArtifactDocument):
    baseline_mechanism_hierarchy: list[str]
    mechanisms: list[Mechanism]


class GeometryDefinition(MMMBaseModel):
    topology: str
    parameters: dict[str, NumericRange]


class OperatingFrequencyRange(MMMBaseModel):
    microwave_GHz: NumericRange | None = None
    phononic_GHz: NumericRange | None = None


class FabricationRequirements(MMMBaseModel):
    process_flow: list[str]
    cleanroom_level: str
    exotic_flag: bool


class IntegrationInterface(MMMBaseModel):
    placement: str
    electrical_interface: str
    packaging_interface: str


class Structure(MMMBaseModel):
    structure_id: str
    name: str
    structure_family: str
    implements_mechanisms: list[str]
    geometry: GeometryDefinition
    material_composition: list[str]
    operating_frequency_range: OperatingFrequencyRange
    fabrication_requirements: FabricationRequirements
    integration_interface: IntegrationInterface
    device_compatibility: dict[str, str]
    notes: str


class LabFeasibilityRequirement(MMMBaseModel):
    dilution_refrigerator_operation: bool
    millikelvin_operation: bool
    standard_nanofabrication_processes: bool
    academic_cleanroom_facilities: bool
    exotic_structures_flagged: bool


class StructureLibraryFile(ArtifactDocument):
    lab_feasibility_requirement: LabFeasibilityRequirement
    structures: list[Structure]


class Observable(MMMBaseModel):
    observable_id: str
    name: str
    quantity: str
    units: str
    extraction_method: str
    interpretation: str


class MinimumRepeats(MMMBaseModel):
    devices_per_condition: int
    cooldowns: int


class Protocol(MMMBaseModel):
    protocol_id: str
    title: str
    purpose: str
    primary_observable_ids: list[str]
    secondary_observable_ids: list[str] = Field(default_factory=list)
    device_classes: list[str]
    required_controls: list[str]
    nulls_addressed: list[str]
    minimum_repeats: MinimumRepeats
    analysis_route: str


class ExperimentRegistryFile(ArtifactDocument):
    observable_registry: list[Observable]
    protocols: list[Protocol]


class ValidationRule(MMMBaseModel):
    validation_rule_id: str
    title: str
    category: str
    logic: str
    pass_condition: str
    fail_condition: str
    required_artifacts: list[str]


class ValidationRulesFile(ArtifactDocument):
    validation_rules: list[ValidationRule]


class BenchmarkModel(MMMBaseModel):
    null_model_id: str
    name: str
    category: str
    claim_can_mimic: str
    inputs: list[str]
    matching_requirements: list[str]
    decisive_observables: list[str]
    failure_mode: str
    governance_priority: int


class BenchmarkModelFile(ArtifactDocument):
    benchmark_models: list[BenchmarkModel]


class ScalingModel(MMMBaseModel):
    scaling_model_id: str
    mechanism_id: str
    independent_variables: list[str]
    predicted_form: str
    distinctive_signature: str
    null_comparators: list[str]
    required_protocols: list[str]


class ScalingModelFile(ArtifactDocument):
    scaling_models: list[ScalingModel]


class DeviceArchitecture(MMMBaseModel):
    device_class: str
    integration_modes: list[str]
    allowed_structure_ids: list[str]
    keepout_rules: list[str]
    readout_modes: list[str]
    primary_metrics: list[str]
    preferred_witnesses: list[str]
    packaging_notes: str


class DeviceArchitectureFile(ArtifactDocument):
    device_architectures: list[DeviceArchitecture]


class CriticalDimension(MMMBaseModel):
    name: str
    nominal_tolerance: str
    sensitivity: str


class ToleranceModel(MMMBaseModel):
    structure_id: str
    critical_dimensions: list[CriticalDimension]
    stopband_shift_budget_percent: float | int | None = None
    yield_floor: float
    intentional_bias_doe: list[str]


class ToleranceModelFile(ArtifactDocument):
    tolerance_models: list[ToleranceModel]


class GeometryScalingModel(MMMBaseModel):
    model_id: str
    structure_id: str
    response_variables: list[str]
    geometry_variables: list[str]
    predicted_relationship: str
    required_series_size: int
    acceptance_criterion: str


class GeometryScalingModelFile(ArtifactDocument):
    geometry_scaling_models: list[GeometryScalingModel]


class MaterialSystem(MMMBaseModel):
    material_system_id: str
    name: str
    device_roles: list[str]
    mm_compatibility: list[str]
    cryogenic_status: str
    fabrication_notes: str


class MaterialSystemRegistryFile(ArtifactDocument):
    material_systems: list[MaterialSystem]


class EnvironmentModel(MMMBaseModel):
    model_id: str
    domain: str
    fidelity_level: str
    state_variables: list[str]
    inputs: list[str]
    outputs: list[str]
    validation_data: list[str]
    software_candidates: list[str]
    surrogate_ready: bool
    crosslinks: list[str]


class EnvironmentModelRegistryFile(ArtifactDocument):
    models: list[EnvironmentModel]


class BaseTemperatureConstraint(MMMBaseModel):
    target: ScalarValue
    max_for_primary_claims: ScalarValue


class TemperatureStabilityConstraint(MMMBaseModel):
    over_1h: float
    over_24h: float


class FieldSweepCapability(MMMBaseModel):
    range: NumericRange
    resolution_uT: float


class MagneticEnvironmentConstraint(MMMBaseModel):
    ambient_field_at_sample_uT: dict[str, ScalarValue]
    field_sweep_capability_mT: FieldSweepCapability


class CryostatConstraint(MMMBaseModel):
    base_temperature_mK: BaseTemperatureConstraint
    temperature_stability_mK: TemperatureStabilityConstraint
    magnetic_environment: MagneticEnvironmentConstraint


class MicrowaveMeasurementConstraint(MMMBaseModel):
    qubit_frequency_coverage_GHz: NumericRange
    readout_chain_noise_temperature_K: dict[str, ScalarValue]
    vna_dynamic_range_dB: float
    time_domain_t1_resolution_us: float
    ramsey_trace_duration_h: float
    calibrated_S_parameter_accuracy_dB: float


class QuasiparticleConstraint(MMMBaseModel):
    minimum_detectable_parity_rate_change_percent: float
    injection_energy_repeatability_percent: float
    recovery_time_resolution_us: float


class PhononicWitnessConstraint(MMMBaseModel):
    saw_witness_frequency_coverage_GHz: NumericRange
    minimum_detectable_saw_notch_dB: float
    phonon_injection_repeatability_percent: float


class FabricationMetrologyConstraint(MMMBaseModel):
    sem_cd_precision_nm: float
    afm_roughness_precision_nm: float
    film_thickness_precision_nm: float
    junction_resistance_repeatability_percent: float


class MinimumClaimMargins(MMMBaseModel):
    T1_fractional_change: float
    T2_fractional_change: float
    parity_rate_fractional_change: float
    recovery_time_fractional_change: float
    vortex_slope_change_fractional_change: float
    witness_band_marker_shift_MHz: float


class InstrumentConstraintFile(ArtifactDocument):
    cryostat: CryostatConstraint
    microwave_measurement: MicrowaveMeasurementConstraint
    quasiparticle_and_parity: QuasiparticleConstraint
    phononic_and_saw_witness: PhononicWitnessConstraint
    fabrication_metrology: FabricationMetrologyConstraint
    minimum_claim_margins: MinimumClaimMargins


class ReplicationRequirement(MMMBaseModel):
    replication_id: str
    mechanism_ids: list[str]
    device_classes: list[str]
    substrates: list[str]
    fabrication_batches_min: int
    cooldowns_per_batch_min: int
    required_structure_ids: list[str]
    claim_grade_if_passed: str


class CrossDeviceRegistryFile(ArtifactDocument):
    replication_matrix: list[ReplicationRequirement]


class CandidateGeometryMetadata(VersionedSchema):
    schema_name: str = "mmm_studio.candidate_geometry"
    candidate_id: str
    parent_structure_id: str
    topology: str
    parameters: dict[str, ScalarValue]


class MaterialParameterSet(VersionedSchema):
    schema_name: str = "mmm_studio.material_parameters"
    material_system: str
    parameters: dict[str, ScalarValue] = Field(default_factory=dict)


class SweepSpecification(VersionedSchema):
    schema_name: str = "mmm_studio.sweep_specification"
    sweep_id: str
    domain: Literal["electromagnetic", "phononic", "rf", "multiphysics"] = "electromagnetic"
    target_frequency_window_ghz: NumericRange | None = None
    sample_count: int = Field(default=201, ge=3)
    temperature_points_mK: list[float] = Field(default_factory=list)
    observables: list[str] = Field(default_factory=list)
    notes: str = ""


class SimulationJobDefinition(VersionedSchema):
    schema_name: str = "mmm_studio.simulation_job"
    job_id: str
    backend: str
    candidate: CandidateGeometryMetadata
    materials: MaterialParameterSet
    sweep: SweepSpecification
    requested_outputs: list[str] = Field(default_factory=list)
    notes: str = ""


class SimulationJobResult(VersionedSchema):
    schema_name: str = "mmm_studio.simulation_result"
    job_id: str
    backend: str
    status: Literal["preflight_only", "completed", "failed", "unsupported"]
    summary: str
    extracted_metrics: dict[str, ScalarValue] = Field(default_factory=dict)
    artifact_paths: list[str] = Field(default_factory=list)


class ScoreComponent(MMMBaseModel):
    feature: str
    value: float
    weight: float
    weighted_value: float
    definition: str


class ScalingType(StrEnum):
    UNKNOWN = "unknown"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    SATURATING = "saturating"
    FLAT = "flat"


class NullDominanceClassification(StrEnum):
    DOMINATED_BY_NULL = "DOMINATED_BY_NULL"
    INDETERMINATE = "INDETERMINATE"
    IMPROVES_OVER_NULL = "IMPROVES_OVER_NULL"


class HypothesisClass(StrEnum):
    LEGACY = "legacy"
    DISCRIMINATION = "discrimination"
    SCALING_LAW = "scaling_law"
    NULL_DOMINANCE = "null_dominance"
    IDENTIFIABILITY = "identifiability"
    FAILURE_MODE = "failure_mode"
    CROSS_DEVICE = "cross_device"
    BOUNDARY_STRESS = "boundary_stress"


class ResidualDiagnostics(MMMBaseModel):
    autocorrelation_score: float = 1.0
    spectral_score: float = 1.0
    burst_score: float = 1.0
    decay_deviation_score: float = 1.0


class ResidualWeightConfig(MMMBaseModel):
    autocorrelation: float = Field(default=0.30, ge=0.0)
    spectral: float = Field(default=0.25, ge=0.0)
    burst: float = Field(default=0.20, ge=0.0)
    decay_deviation: float = Field(default=0.25, ge=0.0)

    @field_validator("decay_deviation", mode="after")
    @classmethod
    def _validate_positive_total(cls, value: float, info: Any) -> float:
        data = info.data
        total = (
            float(data.get("autocorrelation", 0.0))
            + float(data.get("spectral", 0.0))
            + float(data.get("burst", 0.0))
            + float(value)
        )
        if total <= 0:
            raise ValueError("Residual weights must sum to a positive value.")
        return value


class IdentifiabilityResult(MMMBaseModel):
    is_identifiable: bool = True
    conflicting_slice_id: str | None = None
    mean_observable_difference: float = 1.0
    temperature_difference: float = 1.0
    drive_amplitude_difference: float = 1.0
    time_evolution_difference: float = 1.0


class ScalingValidation(MMMBaseModel):
    observed_scaling_type: ScalingType = ScalingType.UNKNOWN
    expected_scaling_type: ScalingType = ScalingType.UNKNOWN
    mismatch_score: float = 0.0
    fit_quality: float = 0.0
    scaling_axis: str | None = None
    observable_name: str | None = None


class UtilityComponents(MMMBaseModel):
    baseline_score: float | None = None
    null_score: float | None = None
    delta_score: float | None = None
    residual_score: float = 0.0
    residual_quality_score: float = 0.0
    null_model_delta: float = 0.0
    identifiability_score: float = 0.0
    scaling_score: float = 0.0
    scaling_separation_score: float = 0.0
    null_equivalence_score: float = 0.0
    measurement_equivalence_score: float = 0.0
    equivalence_margin: float = 0.0
    failure_mode_match_score: float = 0.0
    total_utility: float = 0.0
    parameter_penalty: float = 0.0


class ScoringProfile(MMMBaseModel):
    profile_id: str
    description: str
    target_frequency_ghz: float = 5.0
    weight_multipliers: dict[str, float] = Field(default_factory=dict)
    detectability_floor: float = 0.25


class ScoreResult(VersionedSchema):
    schema_name: str = "mmm_studio.score_result"
    genome_id: str
    parent_structure_id: str
    screening_status: str
    score_backend: str
    scoring_profile: str
    score: float
    baseline_score: float | None = None
    null_score: float | None = None
    baseline_profile: str | None = None
    baseline_mode: str | None = None
    score_delta: float | None = None
    delta_score: float | None = None
    residual_score: float | None = None
    identifiability_score: float | None = None
    scaling_score: float | None = None
    total_utility: float | None = None
    delta_ratio: float | None = None
    decision_band: str
    reject_reason: str = ""
    components: list[ScoreComponent]
    notes: list[str] = Field(default_factory=list)


class ProvenanceMetadata(VersionedSchema):
    schema_name: str = "mmm_studio.provenance"
    run_id: str
    created_at: datetime
    application_version: str
    source_root: str
    source_artifacts: list[str]
    scoring_profile: str
    score_backend: str
    command: str
    environment: dict[str, str] = Field(default_factory=dict)

    @field_validator("created_at", mode="before")
    @classmethod
    def _normalize_created_at(cls, value: datetime | str) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC)
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class RunSliceProvenance(MMMBaseModel):
    sweep_id: str | None = None
    tranche_id: str | None = None
    tranche_origin: str | None = None
    tranche_type: str | None = None
    tranche_objective: str | None = None
    hypothesis_class: str | None = None
    null_pair_id: str | None = None
    parent_slice_id: str | None = None
    lineage_depth: int = 0
    execution_order: int | None = None
    parameter_hash: str | None = None
    null_lineage_source_tranche_id: str | None = None
    null_lineage_source_slice_id: str | None = None
    null_lineage_source_parameter_hash: str | None = None
    originating_equivalence_cluster_id: str | None = None
    discriminator_rationale: str | None = None
    discriminator_axis: str | None = None
    target_hypothesis_pair: list[str] = Field(default_factory=list)
    required_resolution: float | None = None
    predicted_separation: float | None = None
    observed_separation: float | None = None
    discriminator_gain: float | None = None
    axis_cost: float | None = None
    redundancy_penalty: float | None = None
    equivalence_margin: float | None = None


class RunManifest(VersionedSchema):
    schema_name: str = "mmm_studio.run_manifest"
    run_id: str
    created_at: datetime
    root: str
    scoring_profile: str
    score_backend: str
    top_candidate_id: str | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, ScalarValue] = Field(default_factory=dict)
    metrics: dict[str, ScalarValue] = Field(default_factory=dict)
    score_breakdown: UtilityComponents | None = None
    slice_provenance: RunSliceProvenance | None = None
    provenance: ProvenanceMetadata


class RunComparison(VersionedSchema):
    schema_name: str = "mmm_studio.run_comparison"
    left_run_id: str
    right_run_id: str
    score_deltas: dict[str, float] = Field(default_factory=dict)
    top_candidate_shift: dict[str, ScalarValue] = Field(default_factory=dict)
    summary: str


class RegistrySummary(MMMBaseModel):
    root: Path
    artifact_ids: list[str]
    mechanisms: int
    structures: int
    genomes: int
    observables: int
    protocols: int
    validation_rules: int
    material_systems: int
    environment_models: int


class ValidationIssue(MMMBaseModel):
    severity: Literal["warning", "error"]
    code: str
    message: str
    location: str | None = None


class ValidationReport(MMMBaseModel):
    root: Path
    stats: dict[str, int]
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def warnings(self) -> list[str]:
        return [issue.message for issue in self.issues if issue.severity == "warning"]

    @property
    def errors(self) -> list[str]:
        return [issue.message for issue in self.issues if issue.severity == "error"]


@dataclass(slots=True)
class MMMDataset:
    root: Path
    genome_doc: GenomeFile
    ranking_model_doc: RankingModelFile
    mechanism_doc: MechanismRegistryFile
    structure_doc: StructureLibraryFile
    experiment_doc: ExperimentRegistryFile
    validation_doc: ValidationRulesFile
    benchmark_doc: BenchmarkModelFile
    scaling_doc: ScalingModelFile
    device_doc: DeviceArchitectureFile
    tolerance_doc: ToleranceModelFile
    geometry_doc: GeometryScalingModelFile
    material_system_doc: MaterialSystemRegistryFile
    environment_model_doc: EnvironmentModelRegistryFile
    instrument_constraint_doc: InstrumentConstraintFile
    cross_device_doc: CrossDeviceRegistryFile
    genome_index: dict[str, Genome] = field(init=False)
    mechanism_index: dict[str, Mechanism] = field(init=False)
    structure_index: dict[str, Structure] = field(init=False)
    observable_index: dict[str, Observable] = field(init=False)
    protocol_index: dict[str, Protocol] = field(init=False)

    def __post_init__(self) -> None:
        self.genome_index = {genome.genome_id: genome for genome in self.genomes}
        self.mechanism_index = {mechanism.mechanism_id: mechanism for mechanism in self.mechanisms}
        self.structure_index = {structure.structure_id: structure for structure in self.structures}
        self.observable_index = {
            observable.observable_id: observable for observable in self.observables
        }
        self.protocol_index = {protocol.protocol_id: protocol for protocol in self.protocols}

    @property
    def genomes(self) -> list[Genome]:
        return self.genome_doc.genomes

    @property
    def ranking_model(self) -> RankingModel:
        return self.ranking_model_doc.ranking_model

    @property
    def mechanisms(self) -> list[Mechanism]:
        return self.mechanism_doc.mechanisms

    @property
    def structures(self) -> list[Structure]:
        return self.structure_doc.structures

    @property
    def observables(self) -> list[Observable]:
        return self.experiment_doc.observable_registry

    @property
    def protocols(self) -> list[Protocol]:
        return self.experiment_doc.protocols

    @property
    def validation_rules(self) -> list[ValidationRule]:
        return self.validation_doc.validation_rules

    @property
    def benchmark_models(self) -> list[BenchmarkModel]:
        return self.benchmark_doc.benchmark_models

    @property
    def scaling_models(self) -> list[ScalingModel]:
        return self.scaling_doc.scaling_models

    @property
    def device_architectures(self) -> list[DeviceArchitecture]:
        return self.device_doc.device_architectures

    @property
    def tolerance_models(self) -> list[ToleranceModel]:
        return self.tolerance_doc.tolerance_models

    @property
    def geometry_scaling_models(self) -> list[GeometryScalingModel]:
        return self.geometry_doc.geometry_scaling_models

    @property
    def material_systems(self) -> list[MaterialSystem]:
        return self.material_system_doc.material_systems

    @property
    def environment_models(self) -> list[EnvironmentModel]:
        return self.environment_model_doc.models

    @property
    def replication_matrix(self) -> list[ReplicationRequirement]:
        return self.cross_device_doc.replication_matrix

    @property
    def artifact_ids(self) -> list[str]:
        return [
            self.genome_doc.artifact.artifact_id,
            self.ranking_model_doc.artifact.artifact_id,
            self.mechanism_doc.artifact.artifact_id,
            self.structure_doc.artifact.artifact_id,
            self.experiment_doc.artifact.artifact_id,
            self.validation_doc.artifact.artifact_id,
            self.benchmark_doc.artifact.artifact_id,
            self.scaling_doc.artifact.artifact_id,
            self.device_doc.artifact.artifact_id,
            self.tolerance_doc.artifact.artifact_id,
            self.geometry_doc.artifact.artifact_id,
            self.material_system_doc.artifact.artifact_id,
            self.environment_model_doc.artifact.artifact_id,
            self.instrument_constraint_doc.artifact.artifact_id,
            self.cross_device_doc.artifact.artifact_id,
        ]

    def to_summary(self) -> RegistrySummary:
        return RegistrySummary(
            root=self.root,
            artifact_ids=self.artifact_ids,
            mechanisms=len(self.mechanisms),
            structures=len(self.structures),
            genomes=len(self.genomes),
            observables=len(self.observables),
            protocols=len(self.protocols),
            validation_rules=len(self.validation_rules),
            material_systems=len(self.material_systems),
            environment_models=len(self.environment_models),
        )


def build_provenance(
    *,
    run_id: str,
    source_root: Path,
    source_artifacts: list[str],
    scoring_profile: str,
    score_backend: str,
    command: str,
    application_version: str,
    environment: dict[str, str] | None = None,
) -> ProvenanceMetadata:
    """Create a normalized provenance record for generated artifacts."""

    return ProvenanceMetadata(
        run_id=run_id,
        created_at=datetime.now(UTC),
        application_version=application_version,
        source_root=str(source_root),
        source_artifacts=source_artifacts,
        scoring_profile=scoring_profile,
        score_backend=score_backend,
        command=command,
        environment=environment or {},
    )
