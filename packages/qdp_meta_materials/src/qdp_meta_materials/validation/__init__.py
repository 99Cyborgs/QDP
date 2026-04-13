from __future__ import annotations

import math
from collections.abc import Iterable
from pathlib import Path
from statistics import mean
from typing import Literal

from ..registry import load_dataset
from ..models import (
    IdentifiabilityResult,
    NullDominanceClassification,
    ScalingType,
    ScalingValidation,
    ValidationIssue,
    ValidationReport,
)
from ..scoring import clamp

REQUIRED_FILES = [
    "mmm_mechanism_registry.yaml",
    "mmm_structure_library.yaml",
    "mmm_material_genome_database.yaml",
    "mmm_candidate_generation_algorithms.yaml",
    "mmm_environment_model_registry.yaml",
    "mmm_benchmark_models.yaml",
    "mmm_scaling_discrimination_models.yaml",
    "mmm_device_architecture_registry.yaml",
    "mmm_material_system_registry.yaml",
    "mmm_experiment_registry.yaml",
    "mmm_instrument_constraints.yaml",
    "mmm_validation_rules.yaml",
    "mmm_cross_device_registry.yaml",
    "mmm_geometry_scaling_models.yaml",
    "mmm_tolerance_models.yaml",
    "mmm_analysis_pipeline_spec.md",
    "registry/mechanisms.yaml",
    "registry/structures.yaml",
    "genome/material_genome_database.yaml",
    "discovery/generation_algorithms.yaml",
    "simulation/environment_models.yaml",
    "benchmark/null_mechanism_models.yaml",
    "scaling/scaling_models.yaml",
    "integration/device_architecture.yaml",
    "fabrication/fabrication_methods.md",
    "experiments/protocols.md",
    "replication/replication_protocols.md",
    "analysis/analysis_pipeline.md",
    "publications/mmm_overview.tex",
]


def _unique(items: Iterable[str]) -> bool:
    items = list(items)
    return len(items) == len(set(items))


def _issue(
    issues: list[ValidationIssue],
    *,
    severity: Literal["warning", "error"],
    code: str,
    message: str,
    location: str | None = None,
) -> None:
    issues.append(ValidationIssue(severity=severity, code=code, message=message, location=location))


def infer_expected_scaling_type(description: str | None) -> ScalingType:
    """Infer a deterministic scaling class from mechanism text."""

    if description is None:
        return ScalingType.UNKNOWN
    text = description.lower()
    if any(token in text for token in ["saturat", "plateau", "until sink saturation"]):
        return ScalingType.SATURATING
    if any(token in text for token in ["exponential", "biexponential", "memory-kernel"]):
        return ScalingType.EXPONENTIAL
    if any(
        token in text
        for token in [
            "weak direct",
            "no direct",
            "no primary",
            "approximately constant",
            "stays approximately constant",
            "broadband",
        ]
    ):
        return ScalingType.FLAT
    if any(token in text for token in ["scales", "tracks", "follows", "depends", "rises"]):
        return ScalingType.LINEAR
    return ScalingType.UNKNOWN


def validate_scaling_behavior(
    axis_values: list[float],
    observable_values: list[float],
    *,
    expected_scaling_type: ScalingType,
    tolerance: float,
    scaling_axis: str | None = None,
    observable_name: str | None = None,
) -> ScalingValidation:
    """Fit a deterministic family of scaling laws and score mismatch."""

    observed_scaling_type, fit_quality, _ = fit_scaling_signature(axis_values, observable_values)
    if expected_scaling_type == ScalingType.UNKNOWN:
        mismatch_score = 0.0
    elif observed_scaling_type == expected_scaling_type:
        mismatch_score = clamp(max(0.0, 1.0 - fit_quality))
    else:
        mismatch_score = clamp(max(tolerance, 1.0 - fit_quality))
    return ScalingValidation(
        observed_scaling_type=observed_scaling_type,
        expected_scaling_type=expected_scaling_type,
        mismatch_score=mismatch_score,
        fit_quality=fit_quality,
        scaling_axis=scaling_axis,
        observable_name=observable_name,
    )


def fit_scaling_signature(
    axis_values: list[float],
    observable_values: list[float],
) -> tuple[ScalingType, float, list[float]]:
    """Return the best deterministic scaling family, fit quality, and fitted values."""

    if len(axis_values) != len(observable_values) or len(axis_values) < 2:
        return ScalingType.UNKNOWN, 0.0, observable_values
    spread = max(observable_values) - min(observable_values)
    scale = max(max(abs(value) for value in observable_values), 1e-9)
    if spread / scale <= 0.05:
        flat_value = sum(observable_values) / len(observable_values)
        return ScalingType.FLAT, 1.0, [flat_value for _ in observable_values]

    normalized_axis = _normalize_axis(axis_values)
    templates = {
        ScalingType.FLAT: [0.0 for _ in normalized_axis],
        ScalingType.LINEAR: normalized_axis,
        ScalingType.EXPONENTIAL: [
            (math.exp(3.0 * value) - 1.0) / (math.exp(3.0) - 1.0) for value in normalized_axis
        ],
        ScalingType.SATURATING: [
            (1.0 - math.exp(-3.0 * value)) / (1.0 - math.exp(-3.0)) for value in normalized_axis
        ],
    }
    best_type = ScalingType.UNKNOWN
    best_error = float("inf")
    best_fit = observable_values
    best_quality = 0.0
    for scaling_type, template in templates.items():
        fitted, error = _fit_template(template, observable_values)
        if error < best_error:
            best_error = error
            best_type = scaling_type
            best_fit = fitted
            best_quality = _fit_quality(observable_values, error)
    return best_type, best_quality, best_fit


def classify_null_model_dominance(
    *,
    delta_residual: float,
    delta_fit_quality: float,
    tolerance: float,
) -> NullDominanceClassification:
    """Classify whether a slice improves over its null comparator."""

    if delta_residual <= -tolerance or delta_fit_quality <= -tolerance:
        return NullDominanceClassification.DOMINATED_BY_NULL
    if abs(delta_residual) <= tolerance and abs(delta_fit_quality) <= tolerance:
        return NullDominanceClassification.INDETERMINATE
    return NullDominanceClassification.IMPROVES_OVER_NULL


def check_identifiability(
    left_axes: dict[str, list[float]],
    right_axes: dict[str, list[float]],
    *,
    resolution_threshold: float,
    conflicting_slice_id: str | None = None,
) -> IdentifiabilityResult:
    """Compare deterministic observable traces across the required discrimination axes."""

    temperature_difference = _axis_difference(
        left_axes.get("temperature", []),
        right_axes.get("temperature", []),
    )
    drive_difference = _axis_difference(
        left_axes.get("drive_amplitude", []),
        right_axes.get("drive_amplitude", []),
    )
    time_difference = _axis_difference(
        left_axes.get("time_evolution", []),
        right_axes.get("time_evolution", []),
    )
    compared = [
        value
        for value in [temperature_difference, drive_difference, time_difference]
        if value is not None
    ]
    mean_difference = mean(compared) if compared else 0.0
    is_identifiable = all(value >= resolution_threshold for value in compared) if compared else True
    return IdentifiabilityResult(
        is_identifiable=is_identifiable,
        conflicting_slice_id=None if is_identifiable else conflicting_slice_id,
        mean_observable_difference=mean_difference,
        temperature_difference=temperature_difference or 0.0,
        drive_amplitude_difference=drive_difference or 0.0,
        time_evolution_difference=time_difference or 0.0,
    )


def validate_repository(root: str | Path) -> ValidationReport:
    root = Path(root).resolve()
    issues: list[ValidationIssue] = []

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            _issue(
                issues,
                severity="error",
                code="missing_required_file",
                message=f"Missing required file: {rel}",
                location=rel,
            )

    if any(issue.severity == "error" for issue in issues):
        return ValidationReport(root=root, stats={}, issues=issues)

    dataset = load_dataset(root)

    observable_ids = [o.observable_id for o in dataset.observables]
    protocol_ids = [p.protocol_id for p in dataset.protocols]
    validation_ids = [v.validation_rule_id for v in dataset.validation_rules]
    mechanism_ids = [m.mechanism_id for m in dataset.mechanisms]
    structure_ids = [s.structure_id for s in dataset.structures]
    genome_ids = [g.genome_id for g in dataset.genomes]
    benchmark_ids = [b.null_model_id for b in dataset.benchmark_models]
    scaling_ids = [s.scaling_model_id for s in dataset.scaling_models]
    material_system_ids = [m.material_system_id for m in dataset.material_systems]
    environment_model_ids = [model.model_id for model in dataset.environment_models]
    replication_ids = [row.replication_id for row in dataset.replication_matrix]

    for name, ids in [
        ("observable_ids", observable_ids),
        ("protocol_ids", protocol_ids),
        ("validation_ids", validation_ids),
        ("mechanism_ids", mechanism_ids),
        ("structure_ids", structure_ids),
        ("genome_ids", genome_ids),
        ("benchmark_ids", benchmark_ids),
        ("scaling_ids", scaling_ids),
        ("material_system_ids", material_system_ids),
        ("environment_model_ids", environment_model_ids),
        ("replication_ids", replication_ids),
    ]:
        if not _unique(ids):
            _issue(
                issues,
                severity="error",
                code="duplicate_ids",
                message=f"Duplicate IDs detected in {name}",
                location=name,
            )

    observable_set = set(observable_ids)
    protocol_set = set(protocol_ids)
    validation_set = set(validation_ids)
    mechanism_set = set(mechanism_ids)
    structure_set = set(structure_ids)
    benchmark_set = set(benchmark_ids)
    replication_set = set(replication_ids)
    feature_names = {feature.feature for feature in dataset.ranking_model.feature_definitions}

    for mechanism in dataset.mechanisms:
        mid = mechanism.mechanism_id

        if not mechanism.predicted_observable_ids:
            _issue(
                issues,
                severity="error",
                code="mechanism_missing_observables",
                message=f"{mid}: missing predicted_observable_ids",
                location=mid,
            )
        if not mechanism.experimental_protocol_ids:
            _issue(
                issues,
                severity="error",
                code="mechanism_missing_protocols",
                message=f"{mid}: missing experimental_protocol_ids",
                location=mid,
            )
        if not mechanism.validation_rule_ids:
            _issue(
                issues,
                severity="error",
                code="mechanism_missing_validation_rules",
                message=f"{mid}: missing validation_rule_ids",
                location=mid,
            )

        for observable_id in mechanism.predicted_observable_ids:
            if observable_id not in observable_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_observable",
                    message=f"{mid}: unresolved observable {observable_id}",
                    location=mid,
                )
        for protocol_id in mechanism.experimental_protocol_ids:
            if protocol_id not in protocol_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_protocol",
                    message=f"{mid}: unresolved protocol {protocol_id}",
                    location=mid,
                )
        for validation_id in mechanism.validation_rule_ids:
            if validation_id not in validation_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_validation_rule",
                    message=f"{mid}: unresolved validation rule {validation_id}",
                    location=mid,
                )
        for benchmark_id in mechanism.baseline_null_priority:
            if benchmark_id not in benchmark_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_benchmark_model",
                    message=f"{mid}: unresolved benchmark null {benchmark_id}",
                    location=mid,
                )
        for structure_id in mechanism.related_structure_ids:
            if structure_id not in structure_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_related_structure",
                    message=f"{mid}: unresolved related structure {structure_id}",
                    location=mid,
                )

        if (
            mechanism.priority_tier == "A"
            and mechanism.fabrication_feasibility.exotic_fabrication_flag
        ):
            _issue(
                issues,
                severity="warning",
                code="tier_a_exotic_mechanism",
                message=f"{mid}: tier-A mechanism flagged exotic; verify governance intent.",
                location=mid,
            )

    for structure in dataset.structures:
        sid = structure.structure_id
        for mechanism_id in structure.implements_mechanisms:
            if mechanism_id not in mechanism_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_structure_mechanism",
                    message=f"{sid}: unresolved mechanism {mechanism_id}",
                    location=sid,
                )

        if structure.fabrication_requirements.exotic_flag and sid in {
            "STR-PH-SOI-JJ-PHC",
            "STR-PH-SOI-FULLCAP-PHC",
            "STR-PH-GRADED-SINK",
        }:
            _issue(
                issues,
                severity="warning",
                code="unexpected_exotic_flag",
                message=f"{sid}: lead phononic family marked exotic unexpectedly.",
                location=sid,
            )

    for genome in dataset.genomes:
        if genome.parent_structure_id not in structure_set:
            _issue(
                issues,
                severity="error",
                code="unresolved_parent_structure",
                message=(
                    f"{genome.genome_id}: unresolved parent structure {genome.parent_structure_id}"
                ),
                location=genome.genome_id,
            )

    for scaling_model in dataset.scaling_models:
        if scaling_model.mechanism_id not in mechanism_set:
            _issue(
                issues,
                severity="error",
                code="unresolved_scaling_mechanism",
                message=(
                    f"{scaling_model.scaling_model_id}: unresolved mechanism "
                    f"{scaling_model.mechanism_id}"
                ),
                location=scaling_model.scaling_model_id,
            )
        for protocol_id in scaling_model.required_protocols:
            if protocol_id not in protocol_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_scaling_protocol",
                    message=f"{scaling_model.scaling_model_id}: unresolved protocol {protocol_id}",
                    location=scaling_model.scaling_model_id,
                )
        for benchmark_id in scaling_model.null_comparators:
            if benchmark_id not in benchmark_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_scaling_null",
                    message=(
                        f"{scaling_model.scaling_model_id}: unresolved null "
                        f"comparator {benchmark_id}"
                    ),
                    location=scaling_model.scaling_model_id,
                )

    for device in dataset.device_architectures:
        for structure_id in device.allowed_structure_ids:
            if structure_id not in structure_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_device_structure",
                    message=f"{device.device_class}: unresolved structure {structure_id}",
                    location=device.device_class,
                )
        for metric in device.primary_metrics:
            if metric not in observable_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_device_metric",
                    message=f"{device.device_class}: unresolved primary metric {metric}",
                    location=device.device_class,
                )

    for material in dataset.material_systems:
        for compatibility_entry in material.mm_compatibility:
            structure_id = compatibility_entry.split()[0]
            if structure_id not in structure_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_material_compatibility",
                    message=(
                        f"{material.material_system_id}: unresolved compatible "
                        f"structure {compatibility_entry}"
                    ),
                    location=material.material_system_id,
                )

    for protocol in dataset.protocols:
        for observable_id in protocol.primary_observable_ids + protocol.secondary_observable_ids:
            if observable_id not in observable_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_protocol_observable",
                    message=f"{protocol.protocol_id}: unresolved observable {observable_id}",
                    location=protocol.protocol_id,
                )
        for benchmark_id in protocol.nulls_addressed:
            if benchmark_id not in benchmark_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_protocol_null",
                    message=f"{protocol.protocol_id}: unresolved null model {benchmark_id}",
                    location=protocol.protocol_id,
                )

    known_file_refs = {rel for rel in REQUIRED_FILES if rel.endswith((".yaml", ".md", ".tex"))}
    prefixed_entities = {
        "EXP-": protocol_set,
        "OBS-": observable_set,
        "VAL-": validation_set,
        "NULL-": benchmark_set,
        "STR-": structure_set,
        "MECH-": mechanism_set,
        "REPL-": replication_set,
    }

    for rule in dataset.validation_rules:
        for ref in rule.required_artifacts:
            matched_prefix = next(
                (prefix for prefix in prefixed_entities if ref.startswith(prefix)), None
            )
            if matched_prefix and ref not in prefixed_entities[matched_prefix]:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_validation_reference",
                    message=f"{rule.validation_rule_id}: unresolved reference {ref}",
                    location=rule.validation_rule_id,
                )
            elif (
                ref.endswith((".yaml", ".md", ".tex"))
                and ref not in known_file_refs
                and not (root / ref).exists()
            ):
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_validation_file_reference",
                    message=f"{rule.validation_rule_id}: missing referenced file {ref}",
                    location=rule.validation_rule_id,
                )

    for environment_model in dataset.environment_models:
        for ref in environment_model.validation_data:
            if ref not in observable_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_environment_validation_data",
                    message=f"{environment_model.model_id}: unresolved validation observable {ref}",
                    location=environment_model.model_id,
                )
        for crosslink in environment_model.crosslinks:
            if crosslink in {"all_mechanisms"} or crosslink.endswith((".md", ".yaml")):
                continue
            if crosslink.startswith("MECH-") and crosslink not in mechanism_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_environment_crosslink",
                    message=(
                        f"{environment_model.model_id}: unresolved mechanism crosslink {crosslink}"
                    ),
                    location=environment_model.model_id,
                )
            if crosslink.startswith("NULL-") and crosslink not in benchmark_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_environment_crosslink",
                    message=(
                        f"{environment_model.model_id}: unresolved null-model crosslink {crosslink}"
                    ),
                    location=environment_model.model_id,
                )
            if crosslink.startswith("VAL-") and crosslink not in validation_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_environment_crosslink",
                    message=(
                        f"{environment_model.model_id}: unresolved validation-rule "
                        f"crosslink {crosslink}"
                    ),
                    location=environment_model.model_id,
                )

    for replication in dataset.replication_matrix:
        for mechanism_id in replication.mechanism_ids:
            if mechanism_id not in mechanism_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_replication_mechanism",
                    message=f"{replication.replication_id}: unresolved mechanism {mechanism_id}",
                    location=replication.replication_id,
                )
        for structure_id in replication.required_structure_ids:
            if structure_id not in structure_set:
                _issue(
                    issues,
                    severity="error",
                    code="unresolved_replication_structure",
                    message=f"{replication.replication_id}: unresolved structure {structure_id}",
                    location=replication.replication_id,
                )

    tolerance_structure_ids = {row.structure_id for row in dataset.tolerance_models}
    geometry_structure_ids = {row.structure_id for row in dataset.geometry_scaling_models}

    for structure_id in [
        "STR-EM-CPW-EBG-RING",
        "STR-EM-LID-HIS",
        "STR-PH-SOI-JJ-PHC",
        "STR-PH-GRADED-SINK",
        "STR-VX-ANTIDOT-LATTICE",
        "STR-CTRL-BANDSTOP-INTERPOSER",
    ]:
        if structure_id not in tolerance_structure_ids:
            _issue(
                issues,
                severity="warning",
                code="missing_tolerance_model",
                message=f"{structure_id}: no tolerance model found",
                location=structure_id,
            )

    for structure_id in [
        "STR-EM-CPW-EBG-RING",
        "STR-PH-SOI-JJ-PHC",
        "STR-PH-GRADED-SINK",
        "STR-VX-ANTIDOT-LATTICE",
    ]:
        if structure_id not in geometry_structure_ids:
            _issue(
                issues,
                severity="warning",
                code="missing_geometry_scaling_model",
                message=f"{structure_id}: no geometry scaling model found",
                location=structure_id,
            )

    weights = {}
    for chunk in dataset.ranking_model.score_formula.split("+"):
        if "*" not in chunk:
            continue
        weight_text, feature_text = chunk.split("*", 1)
        try:
            weight = float(weight_text.split()[-1])
        except ValueError:
            continue
        weights[feature_text.strip().split()[0]] = weight

    if set(weights) != feature_names:
        _issue(
            issues,
            severity="error",
            code="ranking_model_feature_mismatch",
            message="Ranking model formula features do not match declared feature definitions.",
            location=dataset.ranking_model.model_id,
        )

    if abs(sum(weights.values()) - 1.0) > 1e-6:
        _issue(
            issues,
            severity="error",
            code="ranking_model_weights_invalid",
            message=f"{dataset.ranking_model.model_id}: score formula weights must sum to 1.0",
            location=dataset.ranking_model.model_id,
        )

    stats = {
        "required_files_checked": len(REQUIRED_FILES),
        "mechanisms": len(dataset.mechanisms),
        "structures": len(dataset.structures),
        "genomes": len(dataset.genomes),
        "observables": len(dataset.observables),
        "protocols": len(dataset.protocols),
        "validation_rules": len(dataset.validation_rules),
        "scaling_models": len(dataset.scaling_models),
        "material_systems": len(dataset.material_systems),
        "environment_models": len(dataset.environment_models),
        "replication_paths": len(dataset.replication_matrix),
    }

    return ValidationReport(root=root, stats=stats, issues=issues)


def _normalize_axis(values: list[float]) -> list[float]:
    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        return [0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def _fit_template(template: list[float], values: list[float]) -> tuple[list[float], float]:
    template_mean = sum(template) / len(template)
    values_mean = sum(values) / len(values)
    denominator = sum((value - template_mean) ** 2 for value in template)
    if denominator <= 1e-12:
        fitted = [values_mean for _ in values]
    else:
        slope = (
            sum(
                (template_value - template_mean) * (value - values_mean)
                for template_value, value in zip(template, values, strict=True)
            )
            / denominator
        )
        intercept = values_mean - (slope * template_mean)
        fitted = [intercept + (slope * template_value) for template_value in template]
    error = math.sqrt(
        sum((value - fitted_value) ** 2 for value, fitted_value in zip(values, fitted, strict=True))
        / len(values)
    )
    return fitted, error


def _fit_quality(values: list[float], error: float) -> float:
    spread = max(values) - min(values)
    scale = spread if spread > 1e-12 else max(abs(value) for value in values) if values else 1.0
    if scale <= 1e-12:
        return 1.0
    return clamp(1.0 - (error / scale))


def _axis_difference(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    scale = max(
        max(abs(value) for value in left),
        max(abs(value) for value in right),
        1e-9,
    )
    return sum(abs(l_value - r_value) for l_value, r_value in zip(left, right, strict=True)) / (
        len(left) * scale
    )
