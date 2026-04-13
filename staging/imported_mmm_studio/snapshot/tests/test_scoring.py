from mmm_studio.config import default_seed_root
from mmm_studio.io import load_dataset
from mmm_studio.models import NullDominanceClassification, ScalingType, ScalingValidation
from mmm_studio.scoring import (
    adjusted_feature_weights,
    build_utility_components,
    compute_residual_diagnostics,
    feature_weights,
    get_scoring_profile,
    leaderboard_dataframe,
    measurement_equivalence_score,
    measurement_resolution_floor,
    null_equivalence_score,
    rank_dataset,
    scaling_separation_score,
    weighted_utility_score,
)


def test_weights_sum_to_one():
    dataset = load_dataset(default_seed_root())
    weights = feature_weights(dataset.ranking_model.score_formula)
    assert round(sum(weights.values()), 6) == 1.0


def test_leaderboard_shape_and_bounds():
    dataset = load_dataset(default_seed_root())
    frame = leaderboard_dataframe(dataset)
    assert len(frame) == len(dataset.genomes)
    assert frame["score"].between(0, 1).all()
    assert frame["rank"].is_monotonic_increasing
    assert set(frame["decision_band"]).issubset(
        {"lead_branch", "primary_screen", "sandbox_only", "reject"}
    )


def test_adjusted_profile_weights_sum_to_one():
    dataset = load_dataset(default_seed_root())
    weights = adjusted_feature_weights(
        dataset.ranking_model.score_formula,
        get_scoring_profile("manufacturability_aware"),
    )
    assert round(sum(weights.values()), 6) == 1.0


def test_score_results_have_component_trace():
    dataset = load_dataset(default_seed_root())
    result = rank_dataset(dataset, profile="broadband")[0]
    assert result.score_backend == "baseline_surrogate_v1"
    assert len(result.components) == len(dataset.ranking_model.feature_definitions)


def test_residual_diagnostics_penalize_structured_and_bursty_signals():
    white_like = [0.45, -0.12, 0.33, -0.41, 0.18, -0.27, 0.39, -0.08]
    structured = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
    bursty = [0.02, -0.03, 0.04, -0.02, 1.2, -1.0, 1.1, -0.9]

    white_diag = compute_residual_diagnostics(white_like)
    structured_diag = compute_residual_diagnostics(structured)
    bursty_diag = compute_residual_diagnostics(bursty)

    assert white_diag.autocorrelation_score > structured_diag.autocorrelation_score
    assert white_diag.spectral_score > structured_diag.spectral_score
    assert white_diag.burst_score > bursty_diag.burst_score


def test_decay_deviation_prefers_exponential_residual_envelope():
    near_exponential = [1.0, 0.61, 0.37, 0.22, 0.14, 0.08]
    non_exponential = [1.0, 0.84, 0.73, 0.69, 0.67, 0.66]

    exponential_diag = compute_residual_diagnostics(near_exponential)
    non_exponential_diag = compute_residual_diagnostics(non_exponential)

    assert exponential_diag.decay_deviation_score > non_exponential_diag.decay_deviation_score


def test_weighted_utility_score_tracks_explicit_components():
    components = build_utility_components(
        baseline_score=0.3,
        null_score=0.3,
        delta_score=0.4,
        residual_score=0.8,
        identifiability_score=0.6,
        scaling_score=0.5,
        parameter_penalty=0.1,
        total_utility=0.0,
    )
    score = weighted_utility_score(
        components,
        type(
            "Weights",
            (),
            {
                "residual_quality": 0.4,
                "null_model_delta": 0.2,
                "identifiability": 0.2,
                "scaling": 0.1,
                "parameter_penalty": 0.1,
            },
        )(),
    )

    assert score > 0.0
    assert components.null_score == 0.3


def test_build_utility_components_exposes_discriminative_decomposition():
    components = build_utility_components(
        baseline_score=0.25,
        null_score=0.25,
        delta_score=0.35,
        residual_score=0.70,
        identifiability_score=0.60,
        scaling_score=0.55,
        scaling_separation_score=0.58,
        null_equivalence_score=0.20,
        failure_mode_match_score=0.40,
        parameter_penalty=0.15,
        total_utility=0.0,
    )

    assert components.scaling_separation_score == 0.58
    assert components.null_equivalence_score == 0.20
    assert components.failure_mode_match_score == 0.40


def test_scoring_primitives_preserve_governance_signals():
    assert null_equivalence_score(NullDominanceClassification.DOMINATED_BY_NULL) == 1.0
    assert null_equivalence_score(NullDominanceClassification.IMPROVES_OVER_NULL, delta_signal=0.4) < 0.5
    assert scaling_separation_score(
        ScalingValidation(
            expected_scaling_type=ScalingType.LINEAR,
            observed_scaling_type=ScalingType.LINEAR,
            fit_quality=0.8,
        )
    ) == 0.8


def test_measurement_equivalence_detects_indistinguishable_observables():
    floor = measurement_resolution_floor(
        noise_floor=0.02,
        sampling_bandwidth=1.0,
        observable_resolution=0.01,
    )
    indistinguishable = measurement_equivalence_score(
        [0.005, 0.01, 0.015],
        noise_floor=0.02,
        sampling_bandwidth=1.0,
        observable_resolution=0.01,
    )
    separable = measurement_equivalence_score(
        [floor * 2.0],
        noise_floor=0.02,
        sampling_bandwidth=1.0,
        observable_resolution=0.01,
    )

    assert indistinguishable > 0.0
    assert separable == 0.0
