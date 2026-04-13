from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

import pandas as pd

from ..models import (
    Genome,
    IdentifiabilityResult,
    MMMDataset,
    NullDominanceClassification,
    ResidualDiagnostics,
    ResidualWeightConfig,
    ScoreComponent,
    ScoreResult,
    ScalingValidation,
    ScoringProfile,
    UtilityComponents,
)

SURROGATE_BACKEND_ID = "baseline_surrogate_v1"
DEFAULT_SCORING_PROFILE = "broadband"

_WEIGHT_PATTERN = re.compile(r"(?P<weight>\d*\.\d+|\d+)\*(?P<name>[a-z_]+)")


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a score-like value into the expected unit interval."""

    return max(low, min(high, value))


def compute_residual_diagnostics(
    residuals: list[float],
    *,
    max_lag: int | None = None,
) -> ResidualDiagnostics:
    """Evaluate deterministic residual structure diagnostics where 1.0 is best."""

    if len(residuals) < 3:
        return ResidualDiagnostics()

    centered = [value - mean(residuals) for value in residuals]
    variance = sum(value * value for value in centered) / len(centered)
    if variance <= 1e-12:
        return ResidualDiagnostics()

    lag_limit = max_lag or min(10, max(1, len(centered) // 2), len(centered) - 1)
    autocorrelation_score = _ljung_box_quality(centered, variance, lag_limit)
    spectral_score = _spectral_whiteness_quality(centered)
    burst_score = _burst_stationarity_quality(centered)
    decay_deviation_score = _exponential_decay_quality(residuals)
    return ResidualDiagnostics(
        autocorrelation_score=autocorrelation_score,
        spectral_score=spectral_score,
        burst_score=burst_score,
        decay_deviation_score=decay_deviation_score,
    )


def residual_quality_score(
    diagnostics: ResidualDiagnostics,
    weights: ResidualWeightConfig | None = None,
) -> float:
    """Combine residual diagnostics with explicit deterministic weights."""

    resolved = weights or ResidualWeightConfig()
    total = resolved.autocorrelation + resolved.spectral + resolved.burst + resolved.decay_deviation
    if total <= 0:
        return 0.0
    return clamp(
        (
            resolved.autocorrelation * diagnostics.autocorrelation_score
            + resolved.spectral * diagnostics.spectral_score
            + resolved.burst * diagnostics.burst_score
            + resolved.decay_deviation * diagnostics.decay_deviation_score
        )
        / total
    )


def genome_numeric_observables(genome: Genome) -> dict[str, float]:
    """Extract numeric predicted observables from a genome."""

    numeric: dict[str, float] = {}
    for mapping in (
        genome.predicted_electromagnetic_properties,
        genome.predicted_phononic_band_structure,
    ):
        for key, value in mapping.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric[key] = float(value)
    return numeric


def parameter_economy_penalty(
    *,
    parameter_count: int,
    observable_count: int,
    max_parameter_count: int,
) -> tuple[float, int]:
    """Compute the explicit parameter economy penalty and unconstrained count."""

    unconstrained_parameter_count = max(0, parameter_count - observable_count)
    normalizer = max(1, max_parameter_count)
    penalty = clamp(
        0.35 * (parameter_count / normalizer) + 0.65 * (unconstrained_parameter_count / normalizer)
    )
    return penalty, unconstrained_parameter_count


def identifiability_score(
    result: IdentifiabilityResult,
    *,
    resolution_threshold: float,
) -> float:
    """Project identifiability evidence into a bounded separation score."""

    if resolution_threshold <= 0:
        return 1.0
    return clamp(result.mean_observable_difference / resolution_threshold)


def scaling_separation_score(validation: ScalingValidation) -> float:
    """Reward slices whose observed response separates from mismatched scaling families."""

    if validation.expected_scaling_type == validation.observed_scaling_type:
        return clamp(validation.fit_quality)
    return clamp(0.5 * validation.fit_quality)


def measurement_resolution_floor(
    *,
    noise_floor: float,
    sampling_bandwidth: float,
    observable_resolution: float,
) -> float:
    """Collapse measurement constraints into one deterministic separation floor."""

    bandwidth_penalty = noise_floor / max(sampling_bandwidth, 1.0)
    return max(noise_floor + bandwidth_penalty, observable_resolution)


def measurement_equivalence_score(
    differences: list[float],
    *,
    noise_floor: float,
    sampling_bandwidth: float,
    observable_resolution: float,
) -> float:
    """Legacy indistinguishability score derived from the equivalence margin."""

    margin = equivalence_margin(
        differences,
        noise_floor=noise_floor,
        sampling_bandwidth=sampling_bandwidth,
        observable_resolution=observable_resolution,
    )
    return clamp(1.0 - margin)


def equivalence_margin(
    differences: list[float],
    *,
    noise_floor: float,
    sampling_bandwidth: float,
    observable_resolution: float,
) -> float:
    """Compute the deterministic measurement-envelope margin max(delta_i / resolution_i)."""

    if not differences:
        return 0.0
    floor = measurement_resolution_floor(
        noise_floor=noise_floor,
        sampling_bandwidth=sampling_bandwidth,
        observable_resolution=observable_resolution,
    )
    if floor <= 0:
        return 0.0
    return max(abs(value) / floor for value in differences)


def null_equivalence_score(
    classification: NullDominanceClassification,
    *,
    delta_signal: float = 0.0,
) -> float:
    """Measure how closely the tranche behaves like its null comparator."""

    match classification:
        case NullDominanceClassification.DOMINATED_BY_NULL:
            return 1.0
        case NullDominanceClassification.INDETERMINATE:
            return clamp(0.75 - (0.25 * abs(delta_signal)))
        case NullDominanceClassification.IMPROVES_OVER_NULL:
            return clamp(0.5 - (0.5 * max(delta_signal, 0.0)))
    return 0.5


def failure_mode_match_score(genome: Genome, failure_modes: list[str]) -> float:
    """Estimate whether a top candidate matches the intended failure-mode stress pattern."""

    if not failure_modes:
        return 0.0

    mode_scores: list[float] = []
    for raw_mode in failure_modes:
        mode = raw_mode.strip().lower()
        if mode in {"artifact_risk", "null_alias", "null_dominance"}:
            mode_scores.append(clamp((genome.null_risk_score - 1) / 9.0))
        elif mode in {"fabrication_fragility", "process_window"}:
            mode_scores.append(clamp((genome.fabrication_complexity_score - 1) / 9.0))
        elif mode in {"cross_device_drift", "portability_loss"}:
            mode_scores.append(clamp(1.0 - replication_portability_score(genome)))
        elif mode in {"screening_instability", "screening_bias"}:
            mode_scores.append(1.0 if genome.screening_status.lower() in {"sandbox", "screening"} else 0.0)
        else:
            mode_scores.append(
                clamp(
                    0.5 * ((genome.null_risk_score - 1) / 9.0)
                    + 0.5 * ((genome.fabrication_complexity_score - 1) / 9.0)
                )
            )
    return clamp(sum(mode_scores) / len(mode_scores))


def build_utility_components(
    *,
    baseline_score: float | None = None,
    null_score: float | None = None,
    delta_score: float | None = None,
    residual_score: float = 0.0,
    identifiability_score: float = 0.0,
    scaling_score: float = 0.0,
    scaling_separation_score: float | None = None,
    null_equivalence_score: float = 0.0,
    measurement_equivalence_score: float = 0.0,
    equivalence_margin: float = 0.0,
    failure_mode_match_score: float = 0.0,
    parameter_penalty: float = 0.0,
    total_utility: float = 0.0,
) -> UtilityComponents:
    resolved_null_score = null_score if null_score is not None else baseline_score
    resolved_delta = (
        delta_score
        if delta_score is not None
        else None
        if baseline_score is None
        else total_utility - baseline_score
    )
    return UtilityComponents(
        baseline_score=baseline_score,
        null_score=resolved_null_score,
        delta_score=resolved_delta,
        residual_score=residual_score,
        residual_quality_score=residual_score,
        null_model_delta=resolved_delta or 0.0,
        identifiability_score=identifiability_score,
        scaling_score=scaling_score,
        scaling_separation_score=(
            scaling_score if scaling_separation_score is None else scaling_separation_score
        ),
        null_equivalence_score=null_equivalence_score,
        measurement_equivalence_score=measurement_equivalence_score,
        equivalence_margin=equivalence_margin,
        failure_mode_match_score=failure_mode_match_score,
        total_utility=total_utility,
        parameter_penalty=parameter_penalty,
    )


def weighted_utility_score(components: UtilityComponents, weights: Any) -> float:
    residual_weight = float(getattr(weights, "residual_quality", 0.0))
    null_weight = float(getattr(weights, "null_model_delta", 0.0))
    identifiability_weight = float(getattr(weights, "identifiability", 0.0))
    scaling_weight = float(getattr(weights, "scaling", 0.0))
    parameter_weight = float(getattr(weights, "parameter_penalty", 0.0))
    total_weight = (
        residual_weight + null_weight + identifiability_weight + scaling_weight + parameter_weight
    )
    if total_weight <= 0:
        return 0.0
    return clamp(
        (
            residual_weight * components.residual_score
            + null_weight * (components.delta_score or 0.0)
            + identifiability_weight * components.identifiability_score
            + scaling_weight * components.scaling_score
            - parameter_weight * components.parameter_penalty
        )
        / total_weight
    )


def qualitative_score(value: Any) -> float:
    """Map free-form qualitative seed labels onto a bounded surrogate score."""

    mapping = {
        None: 0.0,
        "screening_only": 0.30,
        "low": 0.35,
        "moderate": 0.55,
        "moderate_to_high": 0.72,
        "high": 0.85,
        "extended": 0.60,
        "junction-local": 0.78,
        "escape_route": 0.70,
        "surface": 0.50,
        "co-localized": 0.82,
    }
    if isinstance(value, str):
        return mapping.get(value.strip().lower(), 0.50)
    return 0.0


def parse_multiplier(value: Any) -> float:
    """Convert string-like multiplicative improvement labels into a score."""

    if isinstance(value, str) and value.endswith("x"):
        try:
            multiple = float(value[:-1])
        except ValueError:
            return 0.0
        return clamp((multiple - 1.0) / 2.0)
    return 0.0


def center_match_score(center_ghz: Any, target_ghz: float = 5.0) -> float:
    """Reward alignment between a predicted band center and a target operating band."""

    if center_ghz is None:
        return 0.0
    try:
        center = float(center_ghz)
    except (TypeError, ValueError):
        return 0.0
    return clamp(1.0 - abs(center - target_ghz) / 4.0)


def width_score(width_ghz: Any) -> float:
    """Map a stopband or gap width onto a bounded broadband utility score."""

    if width_ghz is None:
        return 0.0
    try:
        width = float(width_ghz)
    except (TypeError, ValueError):
        return 0.0
    return clamp(width / 2.0)


def db_score(db: Any) -> float:
    """Map dB-like witness strengths into a 0-1 surrogate score."""

    if db is None:
        return 0.0
    try:
        value = float(db)
    except (TypeError, ValueError):
        return 0.0
    return clamp(value / 10.0)


def feature_weights(score_formula: str) -> dict[str, float]:
    """Extract raw feature weights from the ranking-model score expression."""

    weights: dict[str, float] = {}
    for match in _WEIGHT_PATTERN.finditer(score_formula):
        weights[match.group("name")] = float(match.group("weight"))
    return weights


def scoring_profiles() -> dict[str, ScoringProfile]:
    """Return the built-in scoring profile library."""

    return {
        "broadband": ScoringProfile(
            profile_id="broadband",
            description="Balances candidate breadth, detectability, and cross-device portability.",
            target_frequency_ghz=5.0,
            weight_multipliers={
                "detectability_margin": 1.10,
                "geometry_scaling_clarity": 1.05,
                "replication_portability": 1.05,
            },
            detectability_floor=0.25,
        ),
        "resonance_targeted": ScoringProfile(
            profile_id="resonance_targeted",
            description=(
                "Biases ranking toward candidates aligned to a specific GHz target "
                "with stronger witness support."
            ),
            target_frequency_ghz=5.0,
            weight_multipliers={
                "coherence_uplift": 1.15,
                "detectability_margin": 1.15,
                "simulation_confidence": 1.10,
                "fabrication_robustness": 0.90,
                "standard_lab_feasibility": 0.90,
            },
            detectability_floor=0.30,
        ),
        "manufacturability_aware": ScoringProfile(
            profile_id="manufacturability_aware",
            description=(
                "Prefers candidates that preserve standard-lab execution margin "
                "and replication feasibility."
            ),
            target_frequency_ghz=5.0,
            weight_multipliers={
                "fabrication_robustness": 1.35,
                "standard_lab_feasibility": 1.35,
                "replication_portability": 1.20,
                "geometry_scaling_clarity": 1.05,
                "coherence_uplift": 0.90,
            },
            detectability_floor=0.20,
        ),
    }


def get_scoring_profile(profile: str) -> ScoringProfile:
    """Look up a built-in scoring profile by name."""

    profiles = scoring_profiles()
    if profile not in profiles:
        available = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown scoring profile '{profile}'. Expected one of: {available}")
    return profiles[profile]


def adjusted_feature_weights(score_formula: str, profile: ScoringProfile) -> dict[str, float]:
    """Apply profile multipliers to the base model weights and renormalize."""

    base_weights = feature_weights(score_formula)
    adjusted = {
        name: weight * profile.weight_multipliers.get(name, 1.0)
        for name, weight in base_weights.items()
    }
    total = sum(adjusted.values())
    if total <= 0:
        raise ValueError("Adjusted feature weights sum to zero.")
    return {name: weight / total for name, weight in adjusted.items()}


def non_null_count(mapping: dict[str, Any]) -> int:
    """Count non-null values in a dictionary-like property map."""

    return sum(value is not None for value in mapping.values())


@dataclass(slots=True)
class ScoreCard:
    genome_id: str
    parent_structure_id: str
    screening_status: str
    fabrication_complexity_score: int
    null_risk_score: int
    coherence_uplift: float
    null_separation: float
    detectability_margin: float
    geometry_scaling_clarity: float
    fabrication_robustness: float
    replication_portability: float
    simulation_confidence: float
    standard_lab_feasibility: float
    score: float
    baseline_score: float | None
    null_score: float | None
    score_delta: float | None
    delta_score: float | None
    residual_score: float | None
    identifiability_score: float | None
    scaling_score: float | None
    total_utility: float | None
    delta_ratio: float | None
    decision_band: str
    score_backend: str
    scoring_profile: str
    reject_reason: str = ""


def replication_portability_score(genome: Genome) -> float:
    material = genome.material_system.lower()
    notes = genome.notes.lower()

    if "lid" in material:
        base = 0.80
    elif "sapphire" in material:
        base = 0.72
    elif "soi" in material:
        base = 0.58
    elif "si" in material:
        base = 0.65
    else:
        base = 0.60

    if "release" in notes or "membrane" in notes:
        base -= 0.12
    if "removable lid" in notes:
        base += 0.05
    return clamp(base)


def standard_lab_feasibility_score(genome: Genome) -> float:
    score = 0.95 - 0.08 * max(genome.fabrication_complexity_score - 3, 0)
    notes = genome.notes.lower()
    if "release" in notes:
        score -= 0.08
    if "exotic" in notes:
        score -= 0.25
    return clamp(score)


def geometry_scaling_score(genome: Genome) -> float:
    n_params = len(genome.geometric_parameters)
    base = clamp(n_params / 6.0) * 0.70
    if any(
        key in genome.geometric_parameters for key in ["cell_count", "stage_count", "fill_factor"]
    ):
        base += 0.18
    if any(
        key in genome.geometric_parameters
        for key in ["lattice_constant_um", "lattice_constant_nm", "patch_pitch_um"]
    ):
        base += 0.12
    return clamp(base)


def simulation_confidence_score(genome: Genome) -> float:
    predicted_count = non_null_count(genome.predicted_electromagnetic_properties) + non_null_count(
        genome.predicted_phononic_band_structure
    )
    return clamp(0.35 + 0.10 * predicted_count)


def detectability_score(genome: Genome, profile: ScoringProfile) -> float:
    em = genome.predicted_electromagnetic_properties
    ph = genome.predicted_phononic_band_structure
    band_match = max(
        center_match_score(em.get("stopband_center_GHz"), target_ghz=profile.target_frequency_ghz),
        center_match_score(ph.get("gap_center_GHz"), target_ghz=profile.target_frequency_ghz),
    )
    spread = max(
        width_score(em.get("stopband_width_GHz")),
        width_score(ph.get("gap_width_GHz")),
        db_score(ph.get("broadband_escape_gain_dB")),
        parse_multiplier(ph.get("estimated_qp_recovery_improvement")),
    )
    status_bonus = {
        "prioritized": 0.18,
        "screening": 0.10,
        "sandbox": 0.04,
        "rejected": 0.00,
    }.get(genome.screening_status.lower(), 0.05)
    return clamp(0.55 * band_match + 0.30 * spread + status_bonus)


def coherence_uplift_score(genome: Genome, profile: ScoringProfile) -> float:
    em = genome.predicted_electromagnetic_properties
    ph = genome.predicted_phononic_band_structure

    band_match = max(
        center_match_score(em.get("stopband_center_GHz"), target_ghz=profile.target_frequency_ghz),
        center_match_score(ph.get("gap_center_GHz"), target_ghz=profile.target_frequency_ghz),
    )
    spread = max(
        width_score(em.get("stopband_width_GHz")),
        width_score(ph.get("gap_width_GHz")),
        db_score(ph.get("broadband_escape_gain_dB")),
        parse_multiplier(ph.get("estimated_qp_recovery_improvement")),
    )
    qualitative = max(
        qualitative_score(ph.get("estimated_tls_coupling_reduction")),
        qualitative_score(ph.get("mode_localization")),
    )

    if qualitative == 0.0:
        qualitative = 0.45

    return clamp(0.40 * band_match + 0.35 * spread + 0.25 * qualitative)


def null_separation_score(genome: Genome) -> float:
    return clamp(1.0 - ((genome.null_risk_score - 1) / 9.0))


def fabrication_robustness_score(genome: Genome) -> float:
    return clamp(1.0 - ((genome.fabrication_complexity_score - 1) / 9.0))


def artifact_risk_baseline_score(genome: Genome, profile: ScoringProfile) -> float:
    """Score how easily a candidate could be explained by conventional artifact risks."""

    null_artifact_risk = 1.0 - null_separation_score(genome)
    low_specificity = 1.0 - coherence_uplift_score(genome, profile)
    easy_to_reproduce = fabrication_robustness_score(genome)
    return clamp(0.60 * null_artifact_risk + 0.25 * low_specificity + 0.15 * easy_to_reproduce)


def extract_features(genome: Genome, profile: ScoringProfile) -> dict[str, float]:
    """Separate feature extraction from weighting and ranking."""

    return {
        "coherence_uplift": coherence_uplift_score(genome, profile),
        "null_separation": null_separation_score(genome),
        "detectability_margin": detectability_score(genome, profile),
        "geometry_scaling_clarity": geometry_scaling_score(genome),
        "fabrication_robustness": fabrication_robustness_score(genome),
        "replication_portability": replication_portability_score(genome),
        "simulation_confidence": simulation_confidence_score(genome),
        "standard_lab_feasibility": standard_lab_feasibility_score(genome),
    }


def hard_reject_reason(genome: Genome, features: dict[str, float], profile: ScoringProfile) -> str:
    """Apply hard gates that remain explicit even inside a surrogate scorer."""

    if features["detectability_margin"] < profile.detectability_floor:
        return "below_detectability_gate"
    if features["null_separation"] < 0.20:
        return "null_model_could_explain_most_of_effect"
    if genome.fabrication_complexity_score >= 10:
        return "fabrication_complexity_too_high_for_standard_workbench"
    return ""


def decision_band(
    genome: Genome, score: float, features: dict[str, float], profile: ScoringProfile
) -> str:
    """Map a score vector into the ranking model's decision bands."""

    reject = hard_reject_reason(genome, features, profile)
    if reject:
        return "reject"
    if (
        score >= 0.75
        and genome.null_risk_score <= 5
        and features["replication_portability"] >= 0.5
        and features["standard_lab_feasibility"] >= 0.5
    ):
        return "lead_branch"
    if score >= 0.60 and features["detectability_margin"] >= max(0.40, profile.detectability_floor):
        return "primary_screen"
    if score >= 0.40:
        return "sandbox_only"
    return "reject"


def _component_table(
    dataset: MMMDataset,
    genome: Genome,
    profile: ScoringProfile,
    features: dict[str, float],
    weights: dict[str, float],
) -> list[ScoreComponent]:
    definitions = {
        definition.feature: definition.definition
        for definition in dataset.ranking_model.feature_definitions
    }
    return [
        ScoreComponent(
            feature=feature_name,
            value=features[feature_name],
            weight=weight,
            weighted_value=weight * features[feature_name],
            definition=definitions.get(feature_name, ""),
        )
        for feature_name, weight in weights.items()
    ]


def _score_against_profile(
    dataset: MMMDataset,
    genome: Genome,
    scoring_profile: ScoringProfile,
) -> tuple[dict[str, float], list[ScoreComponent], float, str, str]:
    weights = adjusted_feature_weights(dataset.ranking_model.score_formula, scoring_profile)
    features = extract_features(genome, scoring_profile)
    score = clamp(sum(weights[name] * features[name] for name in weights))
    reject_reason = hard_reject_reason(genome, features, scoring_profile)
    return (
        features,
        _component_table(dataset, genome, scoring_profile, features, weights),
        score,
        decision_band(genome, score, features, scoring_profile),
        reject_reason,
    )


def score_genome_with_profile(
    dataset: MMMDataset,
    genome: Genome,
    scoring_profile: ScoringProfile,
) -> ScoreResult:
    """Score a genome against an explicit profile object."""

    _, components, score, band, reject_reason = _score_against_profile(
        dataset,
        genome,
        scoring_profile,
    )
    notes = [
        "Baseline surrogate ranking only; no full-wave simulation or measured RF data executed.",
    ]
    if genome.screening_status.lower() == "sandbox":
        notes.append("Candidate is already marked sandbox in the seed registry.")

    return ScoreResult(
        genome_id=genome.genome_id,
        parent_structure_id=genome.parent_structure_id,
        screening_status=genome.screening_status,
        score_backend=SURROGATE_BACKEND_ID,
        scoring_profile=scoring_profile.profile_id,
        score=score,
        total_utility=score,
        decision_band=band,
        reject_reason=reject_reason,
        components=components,
        notes=notes,
    )


def score_genome(
    dataset: MMMDataset,
    genome: Genome,
    profile: str = DEFAULT_SCORING_PROFILE,
    *,
    baseline_mode: str | None = None,
    baseline_profile: str | None = None,
) -> ScoreResult:
    """Score a single genome and return a traceable result object."""

    scoring_profile = get_scoring_profile(profile)
    features, components, score, band, reject_reason = _score_against_profile(
        dataset,
        genome,
        scoring_profile,
    )

    notes = [
        "Baseline surrogate ranking only; no full-wave simulation or measured RF data executed.",
    ]
    if genome.screening_status.lower() == "sandbox":
        notes.append("Candidate is already marked sandbox in the seed registry.")

    resolved_baseline_mode: str | None = None
    resolved_baseline_profile: str | None = None
    baseline_score: float | None = None
    score_delta: float | None = None
    delta_ratio: float | None = None
    if baseline_mode is not None:
        if baseline_mode == "profile":
            comparison_profile = get_scoring_profile(baseline_profile or DEFAULT_SCORING_PROFILE)
            _, _, baseline_score, _, _ = _score_against_profile(dataset, genome, comparison_profile)
            resolved_baseline_mode = baseline_mode
            resolved_baseline_profile = comparison_profile.profile_id
        elif baseline_mode == "artifact_risk":
            baseline_score = artifact_risk_baseline_score(genome, scoring_profile)
            resolved_baseline_mode = baseline_mode
            resolved_baseline_profile = baseline_profile
        else:
            raise ValueError(f"Unsupported baseline mode '{baseline_mode}'.")

        if baseline_score is not None:
            score_delta = score - baseline_score
            delta_ratio = None if baseline_score == 0 else score_delta / baseline_score
            notes.append(
                f"Null-model baseline '{resolved_baseline_mode}' computed for delta comparison."
            )

    return ScoreResult(
        genome_id=genome.genome_id,
        parent_structure_id=genome.parent_structure_id,
        screening_status=genome.screening_status,
        score_backend=SURROGATE_BACKEND_ID,
        scoring_profile=scoring_profile.profile_id,
        score=score,
        baseline_score=baseline_score,
        null_score=baseline_score,
        baseline_profile=resolved_baseline_profile,
        baseline_mode=resolved_baseline_mode,
        score_delta=score_delta,
        delta_score=score_delta,
        total_utility=score,
        delta_ratio=delta_ratio,
        decision_band=band,
        reject_reason=reject_reason,
        components=components,
        notes=notes,
    )


def rank_dataset_with_profile(
    dataset: MMMDataset,
    scoring_profile: ScoringProfile,
    *,
    screening_status: str | None = None,
    candidate_ids: set[str] | None = None,
) -> list[ScoreResult]:
    """Score and rank genomes against an explicit profile object."""

    genomes = dataset.genomes
    if candidate_ids is not None:
        genomes = [genome for genome in genomes if genome.genome_id in candidate_ids]
    results = [score_genome_with_profile(dataset, genome, scoring_profile) for genome in genomes]
    if screening_status is not None:
        results = [
            result
            for result in results
            if result.screening_status.lower() == screening_status.lower()
        ]
    return sorted(
        results,
        key=lambda result: (
            -result.score,
            dataset.genome_index[result.genome_id].null_risk_score,
            dataset.genome_index[result.genome_id].fabrication_complexity_score,
        ),
    )


def rank_dataset(
    dataset: MMMDataset,
    profile: str = DEFAULT_SCORING_PROFILE,
    screening_status: str | None = None,
    candidate_ids: set[str] | None = None,
    baseline_mode: str | None = None,
    baseline_profile: str | None = None,
) -> list[ScoreResult]:
    """Score and rank all genomes in a dataset under a chosen profile."""

    genomes = dataset.genomes
    if candidate_ids is not None:
        genomes = [genome for genome in genomes if genome.genome_id in candidate_ids]
    results = [
        score_genome(
            dataset,
            genome,
            profile=profile,
            baseline_mode=baseline_mode,
            baseline_profile=baseline_profile,
        )
        for genome in genomes
    ]
    if screening_status is not None:
        results = [
            result
            for result in results
            if result.screening_status.lower() == screening_status.lower()
        ]
    return sorted(
        results,
        key=lambda result: (
            -result.score,
            dataset.genome_index[result.genome_id].null_risk_score,
            dataset.genome_index[result.genome_id].fabrication_complexity_score,
        ),
    )


def to_score_card(dataset: MMMDataset, result: ScoreResult) -> ScoreCard:
    """Project a rich score result into the flat leaderboard schema."""

    features = {component.feature: component.value for component in result.components}
    genome = dataset.genome_index[result.genome_id]
    return ScoreCard(
        genome_id=result.genome_id,
        parent_structure_id=result.parent_structure_id,
        screening_status=result.screening_status,
        fabrication_complexity_score=genome.fabrication_complexity_score,
        null_risk_score=genome.null_risk_score,
        coherence_uplift=features["coherence_uplift"],
        null_separation=features["null_separation"],
        detectability_margin=features["detectability_margin"],
        geometry_scaling_clarity=features["geometry_scaling_clarity"],
        fabrication_robustness=features["fabrication_robustness"],
        replication_portability=features["replication_portability"],
        simulation_confidence=features["simulation_confidence"],
        standard_lab_feasibility=features["standard_lab_feasibility"],
        score=result.score,
        baseline_score=result.baseline_score,
        null_score=result.null_score,
        score_delta=result.score_delta,
        delta_score=result.delta_score,
        residual_score=result.residual_score,
        identifiability_score=result.identifiability_score,
        scaling_score=result.scaling_score,
        total_utility=result.total_utility,
        delta_ratio=result.delta_ratio,
        decision_band=result.decision_band,
        score_backend=result.score_backend,
        scoring_profile=result.scoring_profile,
        reject_reason=result.reject_reason,
    )


def results_dataframe(dataset: MMMDataset, results: list[ScoreResult]) -> pd.DataFrame:
    """Build a leaderboard-shaped dataframe from precomputed score results."""

    rows = [to_score_card(dataset, result) for result in results]
    frame = pd.DataFrame([asdict(row) for row in rows])
    if frame.empty:
        return frame
    frame["rank"] = range(1, len(frame) + 1)
    columns = [
        "rank",
        "genome_id",
        "parent_structure_id",
        "screening_status",
        "scoring_profile",
        "score_backend",
        "score",
        "baseline_score",
        "null_score",
        "score_delta",
        "delta_score",
        "residual_score",
        "identifiability_score",
        "scaling_score",
        "total_utility",
        "delta_ratio",
        "decision_band",
        "fabrication_complexity_score",
        "null_risk_score",
        "coherence_uplift",
        "null_separation",
        "detectability_margin",
        "geometry_scaling_clarity",
        "fabrication_robustness",
        "replication_portability",
        "simulation_confidence",
        "standard_lab_feasibility",
        "reject_reason",
    ]
    return frame[columns]


def leaderboard_dataframe(
    dataset: MMMDataset,
    profile: str = DEFAULT_SCORING_PROFILE,
    screening_status: str | None = None,
    candidate_ids: set[str] | None = None,
) -> pd.DataFrame:
    """Build a tabular leaderboard for CLI, API, reporting, and tests."""

    return results_dataframe(
        dataset,
        rank_dataset(
            dataset,
            profile=profile,
            screening_status=screening_status,
            candidate_ids=candidate_ids,
        ),
    )


def _ljung_box_quality(centered: list[float], variance: float, max_lag: int) -> float:
    n = len(centered)
    q_stat = 0.0
    for lag in range(1, max_lag + 1):
        numerator = sum(centered[index] * centered[index - lag] for index in range(lag, n))
        autocorrelation = numerator / (n * variance)
        q_stat += (autocorrelation * autocorrelation) / max(n - lag, 1)
    q_stat *= n * (n + 2)
    return clamp(1.0 / (1.0 + (q_stat / max(max_lag, 1))))


def _spectral_whiteness_quality(centered: list[float]) -> float:
    spectrum: list[float] = []
    n = len(centered)
    for frequency_index in range(1, max(1, n // 2) + 1):
        real = 0.0
        imag = 0.0
        for sample_index, value in enumerate(centered):
            angle = (2.0 * math.pi * frequency_index * sample_index) / n
            real += value * math.cos(angle)
            imag -= value * math.sin(angle)
        spectrum.append(real * real + imag * imag)
    if not spectrum:
        return 1.0
    mean_power = sum(spectrum) / len(spectrum)
    if mean_power <= 1e-12:
        return 1.0
    deviation = sum(abs(power - mean_power) for power in spectrum) / (len(spectrum) * mean_power)
    return clamp(1.0 / (1.0 + deviation))


def _burst_stationarity_quality(centered: list[float]) -> float:
    window_count = min(4, max(2, len(centered) // 3))
    window_size = max(1, len(centered) // window_count)
    variances: list[float] = []
    for start in range(0, len(centered), window_size):
        window = centered[start : start + window_size]
        if not window:
            continue
        window_mean = sum(window) / len(window)
        variances.append(sum((value - window_mean) ** 2 for value in window) / len(window))
    if not variances:
        return 1.0
    mean_variance = sum(variances) / len(variances)
    if mean_variance <= 1e-12:
        return 1.0
    burst_ratio = (max(variances) - min(variances)) / mean_variance
    return clamp(1.0 / (1.0 + burst_ratio))


def _exponential_decay_quality(centered: list[float]) -> float:
    magnitudes = [abs(value) + 1e-9 for value in centered]
    if len(magnitudes) < 3:
        return 1.0
    x_values = [float(index) for index in range(len(magnitudes))]
    y_values = [math.log(value) for value in magnitudes]
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    denominator = sum((value - x_mean) ** 2 for value in x_values)
    if denominator <= 1e-12:
        return 1.0
    slope = (
        sum(
            (x_value - x_mean) * (y_value - y_mean)
            for x_value, y_value in zip(x_values, y_values, strict=True)
        )
        / denominator
    )
    intercept = y_mean - (slope * x_mean)
    fitted = [math.exp(intercept + slope * x_value) for x_value in x_values]
    residual = math.sqrt(
        sum((actual - expected) ** 2 for actual, expected in zip(magnitudes, fitted, strict=True))
        / len(magnitudes)
    )
    scale = sum(magnitudes) / len(magnitudes)
    if scale <= 1e-12:
        return 1.0
    return clamp(1.0 / (1.0 + (residual / scale)))
