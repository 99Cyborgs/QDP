from mmm_studio.config import default_seed_root
from mmm_studio.models import NullDominanceClassification, ScalingType
from mmm_studio.validation import (
    check_identifiability,
    classify_null_model_dominance,
    validate_repository,
    validate_scaling_behavior,
)


def test_seed_repository_validates():
    report = validate_repository(default_seed_root())
    assert report.ok, report.errors
    assert report.stats["material_systems"] == 9


def test_identifiability_detection_flags_near_equivalent_predictions():
    left = {
        "temperature": [0.25, 0.41, 0.62],
        "drive_amplitude": [0.18, 0.32, 0.47],
        "time_evolution": [0.11, 0.16, 0.22, 0.29, 0.37],
    }
    right = {
        "temperature": [0.24, 0.40, 0.61],
        "drive_amplitude": [0.19, 0.31, 0.48],
        "time_evolution": [0.10, 0.15, 0.21, 0.28, 0.36],
    }

    result = check_identifiability(
        left,
        right,
        resolution_threshold=0.08,
        conflicting_slice_id="peer-slice",
    )

    assert not result.is_identifiable
    assert result.conflicting_slice_id == "peer-slice"


def test_scaling_classification_matches_synthetic_signatures():
    x_values = [0.0, 1.0, 2.0, 3.0, 4.0]

    linear = validate_scaling_behavior(
        x_values,
        [1.0, 2.0, 3.0, 4.0, 5.0],
        expected_scaling_type=ScalingType.LINEAR,
        tolerance=0.1,
    )
    exponential = validate_scaling_behavior(
        x_values,
        [1.0, 1.8, 3.0, 5.0, 8.2],
        expected_scaling_type=ScalingType.EXPONENTIAL,
        tolerance=0.1,
    )
    saturating = validate_scaling_behavior(
        x_values,
        [0.0, 0.52, 0.77, 0.89, 0.95],
        expected_scaling_type=ScalingType.SATURATING,
        tolerance=0.1,
    )
    flat = validate_scaling_behavior(
        x_values,
        [2.0, 2.02, 1.98, 2.01, 1.99],
        expected_scaling_type=ScalingType.FLAT,
        tolerance=0.1,
    )

    assert linear.observed_scaling_type == ScalingType.LINEAR
    assert exponential.observed_scaling_type == ScalingType.EXPONENTIAL
    assert saturating.observed_scaling_type == ScalingType.SATURATING
    assert flat.observed_scaling_type == ScalingType.FLAT
    assert linear.mismatch_score < 0.2
    assert exponential.mismatch_score < 0.2
    assert saturating.mismatch_score < 0.2
    assert flat.mismatch_score < 0.2


def test_null_model_dominance_classification_respects_tolerance():
    assert (
        classify_null_model_dominance(
            delta_residual=-0.08,
            delta_fit_quality=0.01,
            tolerance=0.05,
        )
        == NullDominanceClassification.DOMINATED_BY_NULL
    )
    assert (
        classify_null_model_dominance(
            delta_residual=0.02,
            delta_fit_quality=0.01,
            tolerance=0.05,
        )
        == NullDominanceClassification.INDETERMINATE
    )
    assert (
        classify_null_model_dominance(
            delta_residual=0.12,
            delta_fit_quality=0.09,
            tolerance=0.05,
        )
        == NullDominanceClassification.IMPROVES_OVER_NULL
    )
