from datetime import UTC, datetime
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from mmm_studio.api import app
from mmm_studio.cli import app as cli_app
from mmm_studio.config import default_seed_root
from mmm_studio.errors import SweepPlanningError
from mmm_studio.io import load_dataset
from types import SimpleNamespace

from mmm_studio.models import (
    HypothesisClass,
    NullDominanceClassification,
    ScalingType,
    UtilityComponents,
)
from mmm_studio.runs import load_run_manifest
from mmm_studio.sweeps import (
    execute_sweep,
    execute_sweep_from_path,
    load_sweep_spec,
    load_sweep_summary,
    plan_sweep,
)
from mmm_studio.sweeps import aggregator as sweep_aggregator
from mmm_studio.sweeps import contracts as sweep_contracts
from mmm_studio.sweeps import executor as sweep_executor
from mmm_studio.sweeps import planner as sweep_planner
from mmm_studio.sweeps.cross_tranche import dedupe_interaction_candidates
from mmm_studio.sweeps.models import (
    AdjudicationGuardrailCode,
    AdaptiveRefinementConfig,
    AdaptiveSearchConfig,
    CandidateFilter,
    CandidateFilterField,
    ComparisonStrategy,
    CrossDeviceTrancheFields,
    DiscriminatorTrancheFields,
    DiscriminationTrancheFields,
    EquivalenceCluster,
    EquivalenceEdge,
    EquivalenceFingerprint,
    EquivalenceGraph,
    FilterOperator,
    FailureModeTrancheFields,
    GovernanceRecommendation,
    MeasurementEquivalenceConfig,
    OrthogonalAxis,
    RejectedAxisRationale,
    RedundancyPruningConfig,
    SliceLineage,
    SliceExecutionRecord,
    SliceNullModelComparison,
    SlicePlanningSource,
    SliceRunStatus,
    SliceSpec,
    SliceUtility,
    SweepExecutionParameters,
    SweepRunStatus,
    SweepAdjudication,
    SweepSpec,
    SweepSummary,
    TrancheAdjudication,
    TrancheOutcome,
    TrancheSpec,
    TrancheObjective,
    TrancheSamplingStrategy,
    TrancheSummary,
    TrancheType,
)
from mmm_studio.sweeps.planner import (
    generate_discriminator_tranches_from_summary,
    generate_refinement_slices,
    prune_pending_slices,
)
from mmm_studio.sweeps.tranche_library import build_preset_tranches

runner = CliRunner()

EXAMPLES_ROOT = Path(__file__).resolve().parents[1] / "examples" / "sweeps"


def _mock_completed_slice_record(
    *,
    tranche_id: str,
    slice_id: str,
    hypothesis_class: HypothesisClass,
    null_equivalence_score: float = 0.0,
    scaling_separation_score: float = 0.0,
    identifiability_score: float = 1.0,
    utility_score: float = 0.5,
    equivalence_margin: float = 0.0,
    measurement_equivalence_score: float = 1.0,
    measurement_gap: float = 0.2,
):
    return SimpleNamespace(
        status=SliceRunStatus.COMPLETED,
        hypothesis_class=hypothesis_class,
        tranche_id=tranche_id,
        slice_id=slice_id,
        null_model_comparison=SimpleNamespace(
            dominance_classification=NullDominanceClassification.INDETERMINATE,
            available=True,
        ),
        utility=SimpleNamespace(
            utility_components=UtilityComponents(
                null_equivalence_score=null_equivalence_score,
                scaling_separation_score=scaling_separation_score,
                identifiability_score=identifiability_score,
                measurement_equivalence_score=measurement_equivalence_score,
                equivalence_margin=equivalence_margin,
                total_utility=utility_score,
            ),
            identifiability=SimpleNamespace(is_identifiable=True),
            identifiability_score=identifiability_score,
            scaling_validation=SimpleNamespace(
                expected_scaling_type=ScalingType.UNKNOWN,
                observed_scaling_type=ScalingType.UNKNOWN,
                scaling_axis=None,
            ),
            utility_score=utility_score,
            equivalence_margin=equivalence_margin,
            trace=SimpleNamespace(measurement_signal_gap=measurement_gap, warning_codes=[]),
        ),
    )


def test_plan_profile_comparison_spec(tmp_path: Path):
    spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    manifest = plan_sweep(spec, dataset_root=default_seed_root(), output_dir=tmp_path / "plan")

    assert manifest.sweep_name == "profile-comparison"
    assert len(manifest.plan.tranches) == 1
    assert [slice_plan.resolved_profile for slice_plan in manifest.plan.tranches[0].slices] == [
        "broadband",
        "resonance_targeted",
        "manufacturability_aware",
    ]
    assert all(slice_plan.candidate_count == 18 for slice_plan in manifest.plan.tranches[0].slices)
    assert manifest.input_hashes


def test_plan_threshold_spec_resolves_expected_candidate_counts(tmp_path: Path):
    spec = load_sweep_spec(EXAMPLES_ROOT / "threshold_sensitivity.yaml")
    manifest = plan_sweep(spec, dataset_root=default_seed_root(), output_dir=tmp_path / "plan")

    counts = [slice_plan.candidate_count for slice_plan in manifest.plan.tranches[0].slices]
    assert counts == [9, 13, 16, 18]


def test_invalid_profile_fails_validation():
    spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    spec.tranches[0].slices[0].profile_override = "not-a-profile"

    with pytest.raises(SweepPlanningError):
        plan_sweep(spec, dataset_root=default_seed_root())


def test_execute_sweep_writes_expected_artifacts(tmp_path: Path):
    manifest, summary = execute_sweep_from_path(
        EXAMPLES_ROOT / "profile_comparison.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "profile-sweep",
    )

    assert summary.successful_slices == 3
    assert summary.failed_slices == 0
    assert (tmp_path / "profile-sweep" / "sweep_manifest.json").exists()
    assert (tmp_path / "profile-sweep" / "sweep_summary.json").exists()
    assert (tmp_path / "profile-sweep" / "aggregate_leaderboard.csv").exists()
    assert (tmp_path / "profile-sweep" / "plots" / "cross_slice_score_comparison.png").exists()
    assert (tmp_path / "profile-sweep" / "plots" / "robustness_overview.png").exists()
    assert (
        tmp_path / "profile-sweep" / "tranches" / "profile_comparison" / "tranche_summary.json"
    ).exists()
    assert (
        tmp_path
        / "profile-sweep"
        / "tranches"
        / "profile_comparison"
        / "slices"
        / "broadband"
        / "run_manifest.json"
    ).exists()
    assert (
        tmp_path
        / "profile-sweep"
        / "tranches"
        / "profile_comparison"
        / "slices"
        / "broadband"
        / "scores.json"
    ).exists()
    assert manifest.status.value == "completed"
    assert summary.aggregate_rankings[0].robustness_score <= 1.0
    assert summary.cross_slice_comparisons


def test_failure_isolation_preserves_sweep_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    original_execute_slice = sweep_executor._execute_slice

    def failing_slice(**kwargs):
        slice_plan = kwargs["slice_plan"]
        if slice_plan.slice_id == "resonance_targeted":
            raise RuntimeError("forced slice failure")
        return original_execute_slice(**kwargs)

    monkeypatch.setattr(sweep_executor, "_execute_slice", failing_slice)

    manifest, summary = sweep_executor.execute_sweep_from_path(
        EXAMPLES_ROOT / "profile_comparison.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "failure-sweep",
    )

    assert manifest.status.value == "completed_with_failures"
    assert summary.successful_slices == 2
    assert summary.failed_slices == 1
    failed_record = next(
        record
        for tranche in manifest.tranches
        for record in tranche.slice_statuses
        if record.slice_id == "resonance_targeted"
    )
    assert failed_record.status.value == "failed"
    assert "forced slice failure" in (failed_record.error_message or "")
    assert (tmp_path / "failure-sweep" / "sweep_summary.json").exists()
    assert (
        tmp_path
        / "failure-sweep"
        / "tranches"
        / "profile_comparison"
        / "slices"
        / "resonance_targeted"
        / "error.json"
    ).exists()


def test_sweep_cli_command_runs_end_to_end(tmp_path: Path):
    result = runner.invoke(
        cli_app,
        [
            "sweep-run",
            str(EXAMPLES_ROOT / "geometry_family_tranche.yaml"),
            "--output-dir",
            str(tmp_path / "cli-sweep"),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "cli-sweep" / "sweep_manifest.json").exists()
    assert (tmp_path / "cli-sweep" / "sweep_summary.md").exists()


def test_sweep_api_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    client = TestClient(app)
    spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    spec.default_output_root = str(tmp_path)

    monkeypatch.setattr("mmm_studio.api.default_sweep_directory", lambda: tmp_path)

    validate_response = client.post(
        "/sweeps/validate",
        json={"root": str(default_seed_root()), "spec": spec.model_dump(mode="json")},
    )
    assert validate_response.status_code == 200

    run_response = client.post(
        "/sweeps/run",
        json={"root": str(default_seed_root()), "spec": spec.model_dump(mode="json")},
    )
    assert run_response.status_code == 200
    payload = run_response.json()
    sweep_id = payload["manifest"]["sweep_id"]
    assert payload["summary"]["successful_slices"] == 3

    summary_response = client.get(f"/sweeps/{sweep_id}/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["summary"]["sweep_id"] == sweep_id

    tranche_response = client.get(f"/sweeps/{sweep_id}/tranches/profile_comparison")
    assert tranche_response.status_code == 200
    assert tranche_response.json()["summary"]["tranche_id"] == "profile_comparison"


def test_adaptive_example_generates_refinement_lineage_and_cross_tranche(tmp_path: Path):
    manifest, summary = execute_sweep_from_path(
        EXAMPLES_ROOT / "adaptive_hypothesis_search.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "adaptive-sweep",
    )

    assert "cross_tranche_interactions" in [
        tranche.tranche_id for tranche in manifest.plan.tranches
    ]
    refinement_slices = [
        slice_plan
        for tranche in manifest.plan.tranches
        for slice_plan in tranche.slices
        if slice_plan.phase == 2
    ]
    assert refinement_slices
    assert all(slice_plan.lineage.parent_slice_ids for slice_plan in refinement_slices)
    assert summary.pruned_slices > 0
    assert any(
        record.status == SliceRunStatus.COMPLETED for record in manifest.tranches[-1].slice_statuses
    )


def test_adaptive_execution_order_is_deterministic(tmp_path: Path):
    first_manifest, _ = execute_sweep_from_path(
        EXAMPLES_ROOT / "adaptive_hypothesis_search.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "adaptive-a",
    )
    second_manifest, _ = execute_sweep_from_path(
        EXAMPLES_ROOT / "adaptive_hypothesis_search.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "adaptive-b",
    )

    first_order = [
        (entry.tranche_id, entry.slice_id, entry.phase, round(entry.utility_score, 6))
        for entry in first_manifest.execution_order
    ]
    second_order = [
        (entry.tranche_id, entry.slice_id, entry.phase, round(entry.utility_score, 6))
        for entry in second_manifest.execution_order
    ]
    assert first_order == second_order


def test_preset_planning_is_deterministic_and_null_paired(tmp_path: Path):
    first_spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    second_spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    for spec in [first_spec, second_spec]:
        spec.adaptive.enabled = True
        spec.adaptive.null_model.enabled = True
        spec.adaptive.cross_tranche.enabled = True
        spec.tranches = build_preset_tranches("standard")

    first_manifest = plan_sweep(
        first_spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "preset-a",
    )
    second_manifest = plan_sweep(
        second_spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "preset-b",
    )

    first_signature = [
        (
            tranche.tranche_id,
            tranche.tranche_type.value,
            slice_plan.slice_id,
            slice_plan.parameter_hash,
            tuple(slice_plan.candidate_ids),
        )
        for tranche in first_manifest.plan.tranches
        for slice_plan in tranche.slices
    ]
    second_signature = [
        (
            tranche.tranche_id,
            tranche.tranche_type.value,
            slice_plan.slice_id,
            slice_plan.parameter_hash,
            tuple(slice_plan.candidate_ids),
        )
        for tranche in second_manifest.plan.tranches
        for slice_plan in tranche.slices
    ]

    assert first_signature == second_signature
    discrimination_slices = [
        slice_plan
        for tranche in first_manifest.plan.tranches
        if tranche.tranche_type == TrancheType.DISCRIMINATION_TRANCHE
        for slice_plan in tranche.slices
    ]
    null_slices = {
        slice_plan.slice_id
        for tranche in first_manifest.plan.tranches
        if tranche.tranche_type == TrancheType.NULL_DOMINANCE_TRANCHE
        for slice_plan in tranche.slices
    }
    assert discrimination_slices
    assert all(slice_plan.null_pair_id in null_slices for slice_plan in discrimination_slices)


def test_null_model_enforcement_writes_baseline_outputs(tmp_path: Path):
    manifest, _ = execute_sweep_from_path(
        EXAMPLES_ROOT / "adaptive_hypothesis_search.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "adaptive-null-model",
    )

    completed_records = [
        record
        for tranche in manifest.tranches
        for record in tranche.slice_statuses
        if record.status == SliceRunStatus.COMPLETED
    ]
    assert completed_records
    first_record = completed_records[0]
    assert first_record.null_model_comparison.enabled
    assert first_record.null_model_comparison.mean_score_delta is not None
    scores_path = Path(first_record.artifact_paths["scores"])
    scores_payload = json.loads(scores_path.read_text(encoding="utf-8"))
    assert scores_payload
    assert all(item["baseline_score"] is not None for item in scores_payload)
    assert all(item["score_delta"] is not None for item in scores_payload)


def test_refinement_lineage_records_parent_and_depth(tmp_path: Path):
    manifest, _ = execute_sweep_from_path(
        EXAMPLES_ROOT / "adaptive_hypothesis_search.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "lineage-depth",
    )

    refinement_slices = [
        slice_plan
        for tranche in manifest.plan.tranches
        for slice_plan in tranche.slices
        if slice_plan.phase == 2
    ]
    assert refinement_slices
    assert all(slice_plan.parent_slice_id is not None for slice_plan in refinement_slices)
    assert all(slice_plan.lineage.parent_slice_id is not None for slice_plan in refinement_slices)
    assert all(slice_plan.lineage.lineage_depth >= 1 for slice_plan in refinement_slices)


def test_interaction_dedupe_keeps_unique_candidate_sets(tmp_path: Path):
    manifest, _ = execute_sweep_from_path(
        EXAMPLES_ROOT / "adaptive_hypothesis_search.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "interaction-dedupe",
    )
    interaction_tranche = next(
        tranche
        for tranche in manifest.plan.tranches
        if tranche.tranche_id == "cross_tranche_interactions"
    )
    duplicated = [interaction_tranche.slices[0], interaction_tranche.slices[0]]
    deduped = dedupe_interaction_candidates(duplicated)
    assert len(deduped) == 1


def test_slice_run_provenance_is_persisted(tmp_path: Path):
    manifest, _ = execute_sweep_from_path(
        EXAMPLES_ROOT / "adaptive_hypothesis_search.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "provenance-sweep",
    )

    completed = next(
        record
        for tranche in manifest.tranches
        for record in tranche.slice_statuses
        if record.status == SliceRunStatus.COMPLETED
    )
    run_manifest = load_run_manifest(Path(completed.output_dir))

    assert run_manifest.slice_provenance is not None
    assert run_manifest.slice_provenance.tranche_id == completed.tranche_id
    assert run_manifest.slice_provenance.parameter_hash == completed.parameter_hash
    assert run_manifest.score_breakdown is not None
    assert (
        run_manifest.score_breakdown.total_utility
        == completed.utility.utility_components.total_utility
    )


def test_cli_preset_replaces_tranches_without_breaking_validation():
    result = runner.invoke(
        cli_app,
        [
            "sweep-validate",
            str(EXAMPLES_ROOT / "profile_comparison.yaml"),
            "--preset",
            "scaling-heavy",
        ],
    )

    assert result.exit_code == 0
    assert "Planned tranches: 7" in result.output
    assert "Adaptive enabled: True" in result.output
    assert "auto_discriminator_g1_" in result.output


def test_equivalence_graph_construction_emits_margin_weighted_edges():
    manifest = SimpleNamespace(
        measurement=MeasurementEquivalenceConfig(
            noise_floor=0.0,
            sampling_bandwidth=1.0,
            observable_resolution=0.1,
        ),
        plan=SimpleNamespace(
            tranches=[
                SimpleNamespace(
                    tranche_id="disc_a",
                    hypothesis_class=HypothesisClass.DISCRIMINATION,
                ),
                SimpleNamespace(
                    tranche_id="disc_b",
                    hypothesis_class=HypothesisClass.SCALING_LAW,
                ),
            ]
        ),
        tranches=[
            SimpleNamespace(
                slice_statuses=[
                    _mock_completed_slice_record(
                        tranche_id="disc_a",
                        slice_id="slice_a",
                        hypothesis_class=HypothesisClass.DISCRIMINATION,
                        null_equivalence_score=0.20,
                        scaling_separation_score=0.40,
                        identifiability_score=0.90,
                        utility_score=0.60,
                        equivalence_margin=0.20,
                        measurement_equivalence_score=0.80,
                    )
                ]
            ),
            SimpleNamespace(
                slice_statuses=[
                    _mock_completed_slice_record(
                        tranche_id="disc_b",
                        slice_id="slice_b",
                        hypothesis_class=HypothesisClass.SCALING_LAW,
                        null_equivalence_score=0.22,
                        scaling_separation_score=0.39,
                        identifiability_score=0.88,
                        utility_score=0.58,
                        equivalence_margin=0.18,
                        measurement_equivalence_score=0.82,
                    )
                ]
            ),
        ],
    )

    graph = sweep_aggregator._build_equivalence_graph(manifest)

    assert graph.nodes == ["disc_a:slice_a", "disc_b:slice_b"]
    assert len(graph.edges) == 1
    assert graph.edges[0].left_tranche_id == "disc_a"
    assert graph.edges[0].right_tranche_id == "disc_b"
    assert graph.edges[0].equivalence_margin < 1.0


def test_orthogonal_axis_enforcement_rejects_single_axis_family():
    with pytest.raises(ValueError):
        TrancheSpec(
            tranche_id="bad-discrimination",
            objective="Invalid orthogonal-axis configuration.",
            tranche_type=TrancheType.DISCRIMINATION_TRANCHE,
            tranche_objective=TrancheObjective.HYPOTHESIS_DISCRIMINATION,
            discrimination_tranche=DiscriminationTrancheFields(
                primary_hypothesis="test",
                orthogonal_axes=[
                    OrthogonalAxis(
                        axis_id="a",
                        field=CandidateFilterField.FABRICATION_COMPLEXITY,
                        operator=FilterOperator.LTE,
                        values=[6, 8],
                        axis_family="shared",
                    ),
                    OrthogonalAxis(
                        axis_id="b",
                        field=CandidateFilterField.NULL_RISK,
                        operator=FilterOperator.LTE,
                        values=[4, 6],
                        axis_family="shared",
                    ),
                ],
                parameter_count=2,
                observable_count=3,
            ),
        )


def test_null_dominance_tranches_execute_after_locked_sources(tmp_path: Path):
    spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    spec.adaptive.enabled = True
    spec.adaptive.null_model.enabled = True
    spec.tranches = build_preset_tranches("discriminative")

    manifest, _ = execute_sweep(
        spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "null-ordering",
    )

    order_by_slice = {
        (entry.tranche_id, entry.slice_id): entry.priority_order for entry in manifest.execution_order
    }
    discrimination_tranche = next(
        tranche
        for tranche in manifest.plan.tranches
        if tranche.tranche_type == TrancheType.DISCRIMINATION_TRANCHE
    )
    assert manifest.execution_order[0].tranche_type == TrancheType.DISCRIMINATION_TRANCHE
    for slice_plan in discrimination_tranche.slices:
        assert slice_plan.null_pair_id is not None
        null_key = ("null_dominance_controls", slice_plan.null_pair_id)
        discrimination_key = (slice_plan.tranche_id, slice_plan.slice_id)
        assert order_by_slice[null_key] > order_by_slice[discrimination_key]


def test_failure_mode_tranche_is_injected_by_discriminative_preset():
    tranches = build_preset_tranches("discriminative")
    failure_mode = next(
        tranche for tranche in tranches if tranche.tranche_type == TrancheType.FAILURE_MODE_TRANCHE
    )

    assert failure_mode.failure_mode_tranche is not None
    assert failure_mode.failure_mode_tranche.failure_modes


def test_cross_device_consistency_summary_is_emitted(tmp_path: Path):
    dataset = load_dataset(default_seed_root())
    replication = dataset.replication_matrix[0]
    spec = SweepSpec(
        name="cross-device-consistency",
        description="Exercise deterministic cross-device tranche planning and summary aggregation.",
        version="1.0.0",
        shared_parameters=SweepExecutionParameters(default_profile="broadband", top_n=8),
        adaptive=AdaptiveSearchConfig(enabled=True),
        tranches=[
            TrancheSpec(
                tranche_id="cross_device",
                objective="Compare required structures across one replication path.",
                tranche_type=TrancheType.CROSS_DEVICE_TRANCHE,
                tranche_objective=TrancheObjective.CROSS_DEVICE_CONSISTENCY,
                shared_profile="broadband",
                sampling_strategy=TrancheSamplingStrategy.EXPLICIT,
                cross_device_tranche=CrossDeviceTrancheFields(
                    replication_ids=[replication.replication_id],
                    device_classes=list(replication.device_classes),
                    orthogonal_axes=[
                        OrthogonalAxis(
                            axis_id="fabrication_complexity",
                            field=CandidateFilterField.FABRICATION_COMPLEXITY,
                            operator=FilterOperator.LTE,
                            values=[6, 8],
                            axis_family="fabrication_complexity",
                        ),
                        OrthogonalAxis(
                            axis_id="null_risk",
                            field=CandidateFilterField.NULL_RISK,
                            operator=FilterOperator.LTE,
                            values=[4, 6],
                            axis_family="null_risk",
                        ),
                    ],
                    parameter_count=2,
                    observable_count=3,
                ),
            )
        ],
    )

    manifest, summary = execute_sweep(
        spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "cross-device",
    )

    cross_device_record = next(
        record for record in manifest.tranches if record.tranche_id == "cross_device"
    )
    assert cross_device_record.slice_statuses
    assert any(entry.tranche_id == "cross_device" for entry in summary.scaling_consistency_map)


def test_legacy_spec_path_still_plans_without_preset(tmp_path: Path):
    spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    manifest = plan_sweep(spec, dataset_root=default_seed_root(), output_dir=tmp_path / "legacy")

    assert len(manifest.plan.tranches) == 1
    assert [slice_plan.slice_id for slice_plan in manifest.plan.tranches[0].slices] == [
        "broadband",
        "resonance_targeted",
        "manufacturability_aware",
    ]


def test_redundancy_pruning_marks_pending_refinements(tmp_path: Path):
    spec = SweepSpec(
        name="adaptive-pruning-inline",
        description="Inline adaptive sweep for redundancy pruning validation.",
        version="1.0.0",
        shared_parameters=SweepExecutionParameters(
            default_profile="manufacturability_aware",
            top_n=8,
        ),
        adaptive=AdaptiveSearchConfig(
            enabled=True,
            seed=7,
            refinement=AdaptiveRefinementConfig(
                fields=[CandidateFilterField.FABRICATION_COMPLEXITY],
                max_refinements_per_slice=2,
                max_total_refinements_per_tranche=2,
                candidate_count_floor=3,
                instability_threshold=1.0,
                divergence_threshold=0.0,
                utility_prune_threshold=0.0,
            ),
            redundancy=RedundancyPruningConfig(
                enabled=True,
                input_similarity_threshold=0.5,
                output_similarity_threshold=1.0,
                combined_similarity_threshold=1.0,
            ),
        ),
        tranches=[
            TrancheSpec(
                tranche_id="complexity",
                objective="Trigger redundant refinements against the parent candidate set.",
                shared_profile="manufacturability_aware",
                comparison_strategy=ComparisonStrategy(
                    top_k=5, robustness_top_k=5, leaderboard_size=10
                ),
                slices=[
                    SliceSpec(
                        slice_id="complexity_le_8",
                        candidate_filters=[
                            CandidateFilter(
                                field=CandidateFilterField.FABRICATION_COMPLEXITY,
                                operator=FilterOperator.LTE,
                                value=8,
                            )
                        ],
                    )
                ],
            )
        ],
    )

    manifest, summary = execute_sweep(
        spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "adaptive-pruning-inline",
    )

    pruned_records = [
        record
        for tranche in manifest.tranches
        for record in tranche.slice_statuses
        if record.status == SliceRunStatus.PRUNED
    ]
    assert summary.pruned_slices >= 1
    assert pruned_records
    assert all(record.pruning_decision is not None for record in pruned_records)
    assert any(
        (record.pruning_decision.input_similarity or 0.0) >= 0.5 for record in pruned_records
    )


def test_refinement_respects_categorical_top_values(tmp_path: Path):
    spec = SweepSpec(
        name="adaptive-categorical-refinement",
        description="Exercise categorical refinement fanout control.",
        version="1.0.0",
        shared_parameters=SweepExecutionParameters(default_profile="broadband", top_n=8),
        adaptive=AdaptiveSearchConfig(
            enabled=True,
            refinement=AdaptiveRefinementConfig(
                fields=[CandidateFilterField.SCREENING_STATUS],
                max_refinements_per_slice=3,
                max_total_refinements_per_tranche=3,
                candidate_count_floor=1,
                instability_threshold=1.0,
                divergence_threshold=0.0,
                utility_prune_threshold=0.0,
                categorical_top_values=3,
            ),
        ),
        tranches=[
            TrancheSpec(
                tranche_id="screening_status_space",
                objective="Split the seed pool by screening status.",
                shared_profile="broadband",
                comparison_strategy=ComparisonStrategy(
                    top_k=5, robustness_top_k=5, leaderboard_size=10
                ),
                slices=[SliceSpec(slice_id="all_candidates")],
            )
        ],
    )

    manifest = plan_sweep(
        spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "categorical-refinement-plan",
    )
    dataset = load_dataset(default_seed_root())
    manifest.tranches[0].slice_statuses[0].status = SliceRunStatus.COMPLETED

    generated = generate_refinement_slices(
        manifest,
        dataset=dataset,
        tranche_id="screening_status_space",
    )

    assert len(generated) == 3
    assert all(
        slice_plan.lineage.source_field == CandidateFilterField.SCREENING_STATUS.value
        for slice_plan in generated
    )


def test_pruning_preserves_one_pending_slice_under_symmetric_redundancy(tmp_path: Path):
    spec = SweepSpec(
        name="adaptive-pruning-frontier",
        description="Verify that symmetric redundant pending slices do not all collapse.",
        version="1.0.0",
        shared_parameters=SweepExecutionParameters(
            default_profile="manufacturability_aware",
            top_n=8,
        ),
        adaptive=AdaptiveSearchConfig(
            enabled=True,
            refinement=AdaptiveRefinementConfig(
                fields=[CandidateFilterField.FABRICATION_COMPLEXITY],
                max_refinements_per_slice=2,
                max_total_refinements_per_tranche=2,
                candidate_count_floor=3,
                minimum_pending_per_phase=1,
                instability_threshold=1.0,
                divergence_threshold=0.0,
                utility_prune_threshold=0.0,
            ),
            redundancy=RedundancyPruningConfig(
                enabled=True,
                input_similarity_threshold=0.5,
                output_similarity_threshold=1.0,
                combined_similarity_threshold=1.0,
            ),
        ),
        tranches=[
            TrancheSpec(
                tranche_id="frontier",
                objective="Inject duplicate pending slices and preserve one.",
                shared_profile="manufacturability_aware",
                comparison_strategy=ComparisonStrategy(
                    top_k=5, robustness_top_k=5, leaderboard_size=10
                ),
                slices=[SliceSpec(slice_id="seed_slice")],
            )
        ],
    )

    manifest = plan_sweep(
        spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "adaptive-pruning-frontier",
    )
    tranche_plan = manifest.plan.tranches[0]
    tranche_record = manifest.tranches[0]
    parent = tranche_plan.slices[0]
    duplicate_utility = parent.utility.model_copy(
        update={
            "utility_score": 0.40,
            "utility_basis": "planned_refinement",
        },
        deep=True,
    )

    for slice_id in ["dup_a", "dup_b"]:
        duplicate = parent.model_copy(
            update={
                "slice_id": slice_id,
                "phase": 2,
                "planning_source": SlicePlanningSource.REFINEMENT,
                "output_dir": str(tmp_path / "adaptive-pruning-frontier" / slice_id),
                "lineage": SliceLineage(
                    phase=2,
                    reason="adaptive_refinement",
                    parent_slice_ids=[parent.slice_id],
                ),
                "utility": duplicate_utility.model_copy(deep=True),
            },
            deep=True,
        )
        tranche_plan.slices.append(duplicate)
        tranche_record.slice_statuses.append(
            tranche_record.slice_statuses[0].model_copy(
                update={
                    "slice_id": slice_id,
                    "phase": 2,
                    "status": SliceRunStatus.PENDING,
                    "utility": duplicate.utility.model_copy(deep=True),
                    "pruning_decision": None,
                    "completed_at": None,
                },
                deep=True,
            )
        )

    prune_pending_slices(
        manifest,
        slice_results={},
        tranche_id="frontier",
    )

    phase_two_records = [
        record for record in manifest.tranches[0].slice_statuses if record.phase == 2
    ]
    pruned = [record for record in phase_two_records if record.status == SliceRunStatus.PRUNED]
    pending = [record for record in phase_two_records if record.status == SliceRunStatus.PENDING]

    assert len(pruned) == 1
    assert len(pending) == 1
    assert pruned[0].pruning_decision is not None
    assert pruned[0].pruning_decision.retained_slice_id == pending[0].slice_id


def test_adaptive_summary_surfaces_null_model_rollup(tmp_path: Path):
    _, summary = execute_sweep_from_path(
        EXAMPLES_ROOT / "adaptive_hypothesis_search.yaml",
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "adaptive-summary-rollup",
    )

    assert summary.adaptive_audit.refinements_generated >= 1
    assert summary.null_model_summary.requested_slices >= 1
    assert summary.null_model_summary.available_slices >= 1
    assert summary.null_model_summary.mean_score_delta is not None
    assert summary.residual_structure_summary.residual_quality_scores
    assert summary.identifiability_summary.evaluated_slices >= 1
    assert summary.scaling_summary.evaluated_slices >= 1
    assert summary.top_slices
    assert summary.utility_distribution.mean_utility is not None
    assert summary.null_model_win_loss.wins + summary.null_model_win_loss.losses >= 0


def test_sweep_validate_cli_echoes_adaptive_policy(tmp_path: Path):
    result = runner.invoke(
        cli_app,
        [
            "sweep-validate",
            str(EXAMPLES_ROOT / "adaptive_hypothesis_search.yaml"),
            "--adaptive",
        ],
    )

    assert result.exit_code == 0
    assert "Adaptive enabled: True" in result.output
    assert "Adaptive seed: 11" in result.output
    assert "Refinement policy:" in result.output


def test_typed_plan_fails_for_structural_insufficiency(tmp_path: Path):
    spec = SweepSpec(
        name="typed-insufficient",
        description="Typed discrimination without enough adjudication coverage.",
        version="1.0.0",
        shared_parameters=SweepExecutionParameters(default_profile="broadband", top_n=8),
        tranches=[
            TrancheSpec(
                tranche_id="discrimination_only",
                objective="Valid typed tranche types but structurally weak adjudication coverage.",
                tranche_type=TrancheType.DISCRIMINATION_TRANCHE,
                tranche_objective=TrancheObjective.HYPOTHESIS_DISCRIMINATION,
                shared_profile="broadband",
                sampling_strategy=TrancheSamplingStrategy.GRID,
                discrimination_tranche=DiscriminationTrancheFields(
                    primary_hypothesis="signal",
                    comparator_hypotheses=["null"],
                    orthogonal_axes=[
                        OrthogonalAxis(
                            axis_id="fabrication_complexity",
                            field=CandidateFilterField.FABRICATION_COMPLEXITY,
                            operator=FilterOperator.LTE,
                            values=[6, 8],
                            axis_family="fabrication_complexity",
                        ),
                        OrthogonalAxis(
                            axis_id="null_risk",
                            field=CandidateFilterField.NULL_RISK,
                            operator=FilterOperator.LTE,
                            values=[4, 6],
                            axis_family="null_risk",
                        ),
                    ],
                    parameter_count=3,
                    observable_count=2,
                ),
            )
        ],
    )

    with pytest.raises(SweepPlanningError, match="structurally insufficient"):
        plan_sweep(spec, dataset_root=default_seed_root(), output_dir=tmp_path / "typed-insufficient")


def test_null_dominance_lineage_is_frozen_and_auditable(tmp_path: Path):
    spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    spec.adaptive.enabled = True
    spec.adaptive.null_model.enabled = True
    spec.tranches = build_preset_tranches("discriminative")

    manifest, _ = execute_sweep(
        spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "lineage-audit",
    )

    null_tranche = next(
        tranche for tranche in manifest.plan.tranches if tranche.tranche_type == TrancheType.NULL_DOMINANCE_TRANCHE
    )
    null_slice = null_tranche.slices[0]
    assert null_slice.lineage.null_lineage_lock is not None
    assert null_slice.lineage.null_lineage_lock.source_tranche_id in null_tranche.source_tranche_ids

    null_record = next(
        record
        for tranche in manifest.tranches
        if tranche.tranche_id == null_tranche.tranche_id
        for record in tranche.slice_statuses
        if record.slice_id == null_slice.slice_id
    )
    assert null_record.null_lineage_lock_verified is True
    run_manifest = load_run_manifest(Path(null_record.output_dir))
    assert run_manifest.slice_provenance is not None
    assert run_manifest.slice_provenance.null_lineage_source_tranche_id == null_slice.lineage.null_lineage_lock.source_tranche_id
    assert run_manifest.slice_provenance.null_lineage_source_slice_id == null_slice.lineage.null_lineage_lock.source_slice_id

    source_tranche = next(
        tranche
        for tranche in manifest.plan.tranches
        if tranche.tranche_id == null_slice.lineage.null_lineage_lock.source_tranche_id
    )
    source_slice = next(
        candidate
        for candidate in source_tranche.slices
        if candidate.slice_id == null_slice.lineage.null_lineage_lock.source_slice_id
    )
    source_slice.parameter_hash = "drifted"
    with pytest.raises(Exception, match="lineage lock mismatch"):
        sweep_executor._validate_null_lineage_lock(manifest, null_slice, null_record)


def test_reordered_typed_tranche_declarations_preserve_plan_identity_and_lineage_basis(tmp_path: Path):
    base_spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    base_spec.adaptive.enabled = True
    base_spec.adaptive.null_model.enabled = True
    base_tranches = build_preset_tranches("discriminative")

    first = base_spec.model_copy(deep=True)
    second = base_spec.model_copy(deep=True)
    first.tranches = base_tranches
    second.tranches = list(reversed(base_tranches))

    first_manifest = plan_sweep(first, dataset_root=default_seed_root(), output_dir=tmp_path / "identity-a")
    second_manifest = plan_sweep(second, dataset_root=default_seed_root(), output_dir=tmp_path / "identity-b")

    assert first_manifest.plan.plan_identity == second_manifest.plan.plan_identity
    first_basis = sorted(
        (
            slice_plan.slice_id,
            slice_plan.lineage.null_lineage_lock.source_tranche_id,
            slice_plan.lineage.null_lineage_lock.source_slice_id,
        )
        for tranche in first_manifest.plan.tranches
        if tranche.tranche_type == TrancheType.NULL_DOMINANCE_TRANCHE
        for slice_plan in tranche.slices
        if slice_plan.lineage.null_lineage_lock is not None
    )
    second_basis = sorted(
        (
            slice_plan.slice_id,
            slice_plan.lineage.null_lineage_lock.source_tranche_id,
            slice_plan.lineage.null_lineage_lock.source_slice_id,
        )
        for tranche in second_manifest.plan.tranches
        if tranche.tranche_type == TrancheType.NULL_DOMINANCE_TRANCHE
        for slice_plan in tranche.slices
        if slice_plan.lineage.null_lineage_lock is not None
    )
    assert first_basis == second_basis


def test_aggregation_emits_machine_readable_adjudication_outputs_and_recommendations(tmp_path: Path):
    spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    spec.adaptive.enabled = True
    spec.adaptive.null_model.enabled = True
    spec.tranches = build_preset_tranches("discriminative")

    _, summary = execute_sweep(
        spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "adjudication-surfaces",
    )

    assert summary.adjudication.tranche_adjudications
    assert summary.adjudication.hypothesis_adjudications
    assert isinstance(summary.adjudication.recommendation, GovernanceRecommendation)
    assert all(
        tranche_summary.adjudication is not None for tranche_summary in summary.tranches
    )


def test_effective_equivalence_detected_beyond_parameter_hash():
    fingerprint_members = [
        TrancheAdjudication(
            tranche_id="discrimination_a",
            hypothesis_class=HypothesisClass.DISCRIMINATION,
            outcomes=[TrancheOutcome.NULL_EQUIVALENT],
            recommendation=GovernanceRecommendation.SANDBOX_ONLY,
            fingerprint=EquivalenceFingerprint(
                fingerprint_id="fp_a",
                dominant_candidate_id="g1",
                winner_consistency_ratio=0.75,
                mean_null_equivalence_score=0.9,
                mean_failure_mode_match_score=0.2,
                mean_scaling_separation_score=0.4,
                mean_identifiability_score=0.7,
                mean_utility_score=0.5,
                null_dominance_losses=0,
                scaling_mismatches=0,
                identifiability_failures=0,
            ),
        ),
        TrancheAdjudication(
            tranche_id="scaling_b",
            hypothesis_class=HypothesisClass.SCALING_LAW,
            outcomes=[TrancheOutcome.NULL_EQUIVALENT],
            recommendation=GovernanceRecommendation.SANDBOX_ONLY,
            fingerprint=EquivalenceFingerprint(
                fingerprint_id="fp_b",
                dominant_candidate_id="g1",
                winner_consistency_ratio=0.75,
                mean_null_equivalence_score=0.9,
                mean_failure_mode_match_score=0.2,
                mean_scaling_separation_score=0.4,
                mean_identifiability_score=0.7,
                mean_utility_score=0.5,
                null_dominance_losses=0,
                scaling_mismatches=0,
                identifiability_failures=0,
            ),
        ),
    ]

    clusters = sweep_aggregator._equivalence_clusters(fingerprint_members)

    assert clusters
    assert clusters[0].tranche_ids == ["discrimination_a", "scaling_b"]
    assert clusters[0].hypothesis_classes == [
        HypothesisClass.DISCRIMINATION,
        HypothesisClass.SCALING_LAW,
    ]


def test_adversarial_utility_inflation_attempts_are_caught():
    resolved_tranche = SimpleNamespace(
        tranche_id="scaling_probe",
        tranche_type=TrancheType.SCALING_LAW_TRANCHE,
        hypothesis_class=HypothesisClass.SCALING_LAW,
        failure_modes=[],
    )
    record = SliceExecutionRecord(
        tranche_id=resolved_tranche.tranche_id,
        slice_id="scaling_slice",
        tranche_type=resolved_tranche.tranche_type,
        hypothesis_class=resolved_tranche.hypothesis_class,
        status=SliceRunStatus.COMPLETED,
        output_dir="artifacts/scaling_slice",
        utility=SliceUtility(
            utility_score=0.8,
            scaling_score=0.8,
            identifiability_score=0.8,
            utility_components=UtilityComponents().model_copy(
                update={"scaling_separation_score": 0.95, "null_equivalence_score": 0.85},
                deep=True,
            ),
        ),
        null_model_comparison=SliceNullModelComparison(
            available=False,
            requested=True,
            dominance_classification=NullDominanceClassification.INDETERMINATE,
        ),
    )
    record.utility.scaling_validation.scaling_axis = None
    adjudication = sweep_aggregator._build_tranche_adjudication(
        manifest=None,  # unused by helper
        tranche_plan=resolved_tranche,
        tranche_record=None,
        slice_winners=[],
        successful_slice_records=[record],
        winner_consistency_ratio=0.0,
    )

    assert TrancheOutcome.INSUFFICIENT_EVIDENCE in adjudication.outcomes
    assert {
        guardrail.code for guardrail in adjudication.guardrails
    } >= {
        AdjudicationGuardrailCode.SCALING_LAYOUT_INFLATION,
        AdjudicationGuardrailCode.NULL_EQUIVALENCE_UNDERCOVERED,
    }


def _build_adversarial_discriminator_spec() -> SweepSpec:
    return SweepSpec(
        name="preflight-discriminator",
        description="Inject discriminator tranches before execution for equivalent hypotheses.",
        version="1.0.0",
        shared_parameters=SweepExecutionParameters(default_profile="broadband", top_n=8),
        adaptive=AdaptiveSearchConfig(enabled=True),
        tranches=[
            TrancheSpec(
                tranche_id="disc_a",
                objective="First mechanism hypothesis.",
                tranche_type=TrancheType.DISCRIMINATION_TRANCHE,
                tranche_objective=TrancheObjective.HYPOTHESIS_DISCRIMINATION,
                shared_profile="broadband",
                sampling_strategy=TrancheSamplingStrategy.GRID,
                discrimination_tranche=DiscriminationTrancheFields(
                    primary_hypothesis="signal_a",
                    comparator_hypotheses=["signal_b"],
                    orthogonal_axes=[
                        OrthogonalAxis(
                            axis_id="fabrication_complexity",
                            field=CandidateFilterField.FABRICATION_COMPLEXITY,
                            operator=FilterOperator.LTE,
                            values=[6, 8],
                            axis_family="fabrication_complexity",
                        ),
                        OrthogonalAxis(
                            axis_id="null_risk",
                            field=CandidateFilterField.NULL_RISK,
                            operator=FilterOperator.LTE,
                            values=[4, 6],
                            axis_family="null_risk",
                        ),
                    ],
                    parameter_count=2,
                    observable_count=3,
                ),
            ),
            TrancheSpec(
                tranche_id="disc_b",
                objective="Second mechanism hypothesis with the same predicted footprint.",
                tranche_type=TrancheType.DISCRIMINATION_TRANCHE,
                tranche_objective=TrancheObjective.HYPOTHESIS_DISCRIMINATION,
                shared_profile="broadband",
                sampling_strategy=TrancheSamplingStrategy.GRID,
                discrimination_tranche=DiscriminationTrancheFields(
                    primary_hypothesis="signal_b",
                    comparator_hypotheses=["signal_a"],
                    orthogonal_axes=[
                        OrthogonalAxis(
                            axis_id="fabrication_complexity",
                            field=CandidateFilterField.FABRICATION_COMPLEXITY,
                            operator=FilterOperator.LTE,
                            values=[6, 8],
                            axis_family="fabrication_complexity",
                        ),
                        OrthogonalAxis(
                            axis_id="null_risk",
                            field=CandidateFilterField.NULL_RISK,
                            operator=FilterOperator.LTE,
                            values=[4, 6],
                            axis_family="null_risk",
                        ),
                    ],
                    parameter_count=2,
                    observable_count=3,
                ),
            ),
            TrancheSpec(
                tranche_id="failure_probe",
                objective="Add orthogonal falsifier coverage.",
                tranche_type=TrancheType.FAILURE_MODE_TRANCHE,
                tranche_objective=TrancheObjective.FAILURE_MODE_CHARACTERIZATION,
                shared_profile="broadband",
                failure_mode_tranche=FailureModeTrancheFields(
                    failure_modes=["artifact_risk"],
                    orthogonal_axes=[
                        OrthogonalAxis(
                            axis_id="fabrication_complexity",
                            field=CandidateFilterField.FABRICATION_COMPLEXITY,
                            operator=FilterOperator.LTE,
                            values=[6, 8],
                            axis_family="fabrication_complexity",
                        )
                    ],
                    parameter_count=1,
                    observable_count=2,
                ),
            ),
        ],
    )


def test_adversarial_pair_selection_prioritizes_lowest_margin_pair(tmp_path: Path):
    manifest = plan_sweep(
        _build_adversarial_discriminator_spec(),
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "pair-selection",
    )
    dataset = load_dataset(default_seed_root())
    tranche_ids = {"disc_a", "disc_b", "failure_probe"}
    ranked_results = {}
    slices_by_key = {}
    tranches_by_id = {
        tranche.tranche_id: tranche
        for tranche in manifest.plan.tranches
        if tranche.tranche_id in tranche_ids
    }
    for tranche in manifest.plan.tranches:
        if tranche.tranche_id not in tranche_ids:
            continue
        slice_plan = tranche.slices[0]
        ranked_results[(slice_plan.tranche_id, slice_plan.slice_id)] = sweep_planner._rank_slice_candidates(
            dataset=dataset,
            profile=slice_plan.resolved_profile,
            candidate_ids=slice_plan.candidate_ids,
            null_model_enabled=manifest.adaptive.null_model.enabled,
            baseline_mode=(
                manifest.adaptive.null_model.mode.value
                if manifest.adaptive.null_model.enabled
                else None
            ),
            baseline_profile=manifest.adaptive.null_model.baseline_profile,
            tranche_type=slice_plan.tranche_type,
        )
        slices_by_key[(slice_plan.tranche_id, slice_plan.slice_id)] = slice_plan

    candidates = sweep_planner._pair_candidates_from_ranked_results(
        dataset=dataset,
        measurement=manifest.measurement,
        ranked_results=ranked_results,
        slices_by_key=slices_by_key,
        tranches_by_id=tranches_by_id,
    )

    assert candidates
    assert candidates[0].pair_key == ("disc_a", "disc_b")
    assert candidates[0].edge.equivalence_margin == pytest.approx(0.0)


def test_discriminator_gain_ranking_is_stable(tmp_path: Path):
    manifest = plan_sweep(
        _build_adversarial_discriminator_spec(),
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "gain-stability",
    )
    dataset = load_dataset(default_seed_root())
    tranches_by_id = {tranche.tranche_id: tranche for tranche in manifest.plan.tranches}
    left = tranches_by_id["disc_a"]
    right = tranches_by_id["disc_b"]

    first = sweep_planner._rank_discriminator_axes_for_pair(
        left=left,
        right=right,
        left_genome_id=left.slices[0].candidate_ids[0],
        right_genome_id=right.slices[0].candidate_ids[0],
        measurement=manifest.measurement,
        dataset=dataset,
        source_tranches=tranches_by_id,
    )
    second = sweep_planner._rank_discriminator_axes_for_pair(
        left=left,
        right=right,
        left_genome_id=left.slices[0].candidate_ids[0],
        right_genome_id=right.slices[0].candidate_ids[0],
        measurement=manifest.measurement,
        dataset=dataset,
        source_tranches=tranches_by_id,
    )

    assert [(item.axis_key, round(item.discriminator_gain, 6)) for item in first] == [
        (item.axis_key, round(item.discriminator_gain, 6)) for item in second
    ]
    assert first[0].discriminator_gain >= first[1].discriminator_gain


def test_orthogonality_enforcement_blocks_redundant_discriminator_axis(tmp_path: Path):
    manifest = plan_sweep(
        _build_adversarial_discriminator_spec(),
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "orthogonality",
    )
    dataset = load_dataset(default_seed_root())
    tranches_by_id = {tranche.tranche_id: tranche for tranche in manifest.plan.tranches}
    discriminator = next(
        tranche
        for tranche in manifest.plan.tranches
        if tranche.tranche_type == TrancheType.DISCRIMINATOR_TRANCHE
    )

    ranked = sweep_planner._rank_discriminator_axes_for_pair(
        left=tranches_by_id["disc_a"],
        right=tranches_by_id["disc_b"],
        left_genome_id=tranches_by_id["disc_a"].slices[0].candidate_ids[0],
        right_genome_id=tranches_by_id["disc_b"].slices[0].candidate_ids[0],
        measurement=manifest.measurement,
        dataset=dataset,
        source_tranches=tranches_by_id,
    )

    assert ranked
    assert all(
        item.axis_key != discriminator.discriminator_tranche.discriminator_axis for item in ranked
    )


def test_planner_injects_discriminator_tranche_for_preflight_equivalence(tmp_path: Path):
    manifest = plan_sweep(
        _build_adversarial_discriminator_spec(),
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "preflight-discriminator",
    )

    discriminator = next(
        tranche
        for tranche in manifest.plan.tranches
        if tranche.tranche_type == TrancheType.DISCRIMINATOR_TRANCHE
    )
    assert discriminator.discriminator_tranche is not None
    assert discriminator.discriminator_tranche.target_hypothesis_pair == ["disc_a", "disc_b"]


def test_epistemic_sufficiency_can_fail_under_measurement_limits(tmp_path: Path):
    spec = SweepSpec(
        name="measurement-infeasible",
        description="Structural validity is not enough when instrument limits preclude separation.",
        version="1.0.0",
        shared_parameters=SweepExecutionParameters(default_profile="broadband", top_n=8),
        measurement=MeasurementEquivalenceConfig(
            noise_floor=1.0,
            sampling_bandwidth=1.0,
            observable_resolution=1.0,
        ),
        adaptive=AdaptiveSearchConfig(enabled=True),
        tranches=[
            TrancheSpec(
                tranche_id="disc_only",
                objective="Valid typed tranche that cannot clear the measurement floor.",
                tranche_type=TrancheType.DISCRIMINATION_TRANCHE,
                tranche_objective=TrancheObjective.HYPOTHESIS_DISCRIMINATION,
                shared_profile="broadband",
                sampling_strategy=TrancheSamplingStrategy.GRID,
                discrimination_tranche=DiscriminationTrancheFields(
                    primary_hypothesis="signal",
                    comparator_hypotheses=["null"],
                    orthogonal_axes=[
                        OrthogonalAxis(
                            axis_id="fabrication_complexity",
                            field=CandidateFilterField.FABRICATION_COMPLEXITY,
                            operator=FilterOperator.LTE,
                            values=[6, 8],
                            axis_family="fabrication_complexity",
                        ),
                        OrthogonalAxis(
                            axis_id="null_risk",
                            field=CandidateFilterField.NULL_RISK,
                            operator=FilterOperator.LTE,
                            values=[4, 6],
                            axis_family="null_risk",
                        ),
                    ],
                    parameter_count=2,
                    observable_count=2,
                ),
            ),
            TrancheSpec(
                tranche_id="failure_probe",
                objective="Structural falsifier exists, but not one that clears measurement limits.",
                tranche_type=TrancheType.FAILURE_MODE_TRANCHE,
                tranche_objective=TrancheObjective.FAILURE_MODE_CHARACTERIZATION,
                shared_profile="broadband",
                failure_mode_tranche=FailureModeTrancheFields(
                    failure_modes=["artifact_risk"],
                    orthogonal_axes=[
                        OrthogonalAxis(
                            axis_id="fabrication_complexity",
                            field=CandidateFilterField.FABRICATION_COMPLEXITY,
                            operator=FilterOperator.LTE,
                            values=[6, 8],
                            axis_family="fabrication_complexity",
                        )
                    ],
                    parameter_count=1,
                    observable_count=2,
                ),
            ),
        ],
    )

    with pytest.raises(SweepPlanningError, match="measurement envelope"):
        plan_sweep(
            spec,
            dataset_root=default_seed_root(),
            output_dir=tmp_path / "measurement-infeasible",
        )


def test_adaptive_discriminator_generation_advances_deterministically(tmp_path: Path):
    spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    spec.adaptive.enabled = True
    manifest = plan_sweep(
        spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "adaptive-discriminator-plan",
    )
    summary = SimpleNamespace(
        adjudication=SimpleNamespace(
            equivalence_clusters=[
                sweep_aggregator.EquivalenceCluster(
                    cluster_id="equivalence_1",
                    tranche_ids=[manifest.plan.tranches[0].tranche_id, manifest.plan.tranches[0].tranche_id + "_peer"],
                    hypothesis_classes=[HypothesisClass.DISCRIMINATION, HypothesisClass.SCALING_LAW],
                    fingerprint_ids=["fp_a", "fp_b"],
                    reason="measurement_indistinguishable",
                    similarity_score=0.95,
                    measurement_equivalence_score=0.95,
                )
            ]
        )
    )
    peer = manifest.plan.tranches[0].model_copy(
        update={"tranche_id": manifest.plan.tranches[0].tranche_id + "_peer"},
        deep=True,
    )
    manifest.plan.tranches.append(peer)

    generated = generate_discriminator_tranches_from_summary(
        manifest,
        summary=summary,
        dataset=load_dataset(default_seed_root()),
        generation=2,
    )

    assert len(generated) == 1
    assert generated[0].tranche_id.startswith("auto_discriminator_g2_")


def test_discriminator_generation_prefers_canonical_equivalence_graph(tmp_path: Path):
    spec = load_sweep_spec(EXAMPLES_ROOT / "profile_comparison.yaml")
    spec.adaptive.enabled = True
    manifest = plan_sweep(
        spec,
        dataset_root=default_seed_root(),
        output_dir=tmp_path / "canonical-equivalence-graph",
    )
    peer = manifest.plan.tranches[0].model_copy(
        update={"tranche_id": manifest.plan.tranches[0].tranche_id + "_peer"},
        deep=True,
    )
    manifest.plan.tranches.append(peer)
    canonical_edge = EquivalenceEdge(
        edge_id="canonical",
        left_tranche_id=manifest.plan.tranches[0].tranche_id,
        left_slice_id=manifest.plan.tranches[0].slices[0].slice_id,
        right_tranche_id=peer.tranche_id,
        right_slice_id=peer.slices[0].slice_id,
        equivalence_margin=0.2,
    )
    misleading_edge = EquivalenceEdge(
        edge_id="misleading",
        left_tranche_id="unknown_left",
        left_slice_id="unknown_left_slice",
        right_tranche_id="unknown_right",
        right_slice_id="unknown_right_slice",
        equivalence_margin=0.01,
    )
    summary = SimpleNamespace(
        weakest_edges=[misleading_edge],
        equivalence_clusters=[],
        adjudication=SimpleNamespace(
            equivalence_graph=EquivalenceGraph(edges=[canonical_edge]),
            equivalence_clusters=[],
        ),
        per_slice_winners=[],
    )

    generated = generate_discriminator_tranches_from_summary(
        manifest,
        summary=summary,
        dataset=load_dataset(default_seed_root()),
        generation=2,
    )

    assert len(generated) == 1
    assert generated[0].discriminator_tranche is not None
    assert generated[0].discriminator_tranche.target_hypothesis_pair == sorted(
        [manifest.plan.tranches[0].tranche_id, peer.tranche_id]
    )


def test_governance_escalates_when_indistinguishability_persists():
    recommendation = sweep_aggregator._recommendation_for_outcomes(
        {TrancheOutcome.INDETERMINATE_EQUIVALENCE},
        [
            sweep_aggregator.AdjudicationGuardrail(
                code=AdjudicationGuardrailCode.EQUIVALENCE_PERSISTS,
                message="Still indistinguishable after discriminator coverage.",
                source="tranche:disc",
            )
        ],
    )

    assert recommendation == GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY


def test_governance_escalates_when_discriminator_cannot_break_equivalence():
    manifest = SimpleNamespace(
        measurement=MeasurementEquivalenceConfig(
            noise_floor=0.0,
            sampling_bandwidth=1.0,
            observable_resolution=0.1,
        ),
        plan=SimpleNamespace(
            tranches=[
                SimpleNamespace(
                    discriminator_tranche=SimpleNamespace(
                        target_hypothesis_pair=["disc_pair", "peer_pair"]
                    )
                )
            ]
        ),
    )
    tranche_plan = SimpleNamespace(
        tranche_id="disc_pair",
        tranche_type=TrancheType.DISCRIMINATOR_TRANCHE,
        hypothesis_class=HypothesisClass.DISCRIMINATION,
        failure_modes=[],
    )
    adjudication = sweep_aggregator._build_tranche_adjudication(
        manifest=manifest,
        tranche_plan=tranche_plan,
        tranche_record=SimpleNamespace(),
        slice_winners=[
            SimpleNamespace(
                status=SliceRunStatus.COMPLETED,
                candidate_id="GEN-001",
            )
        ],
        successful_slice_records=[
            _mock_completed_slice_record(
                tranche_id="disc_pair",
                slice_id="disc_slice",
                hypothesis_class=HypothesisClass.DISCRIMINATION,
                equivalence_margin=0.4,
                measurement_equivalence_score=0.6,
                measurement_gap=0.2,
            )
        ],
        winner_consistency_ratio=1.0,
    )

    assert TrancheOutcome.EQUIVALENCE_UNBROKEN in adjudication.outcomes
    assert TrancheOutcome.DISCRIMINATOR_EXHAUSTED in adjudication.outcomes
    assert adjudication.recommendation == GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY


def test_resolution_limits_block_false_promotion():
    manifest = SimpleNamespace(
        measurement=MeasurementEquivalenceConfig(
            noise_floor=0.1,
            sampling_bandwidth=1.0,
            observable_resolution=0.1,
        ),
        plan=SimpleNamespace(tranches=[]),
    )
    resolved_tranche = SimpleNamespace(
        tranche_id="scaling_probe",
        tranche_type=TrancheType.SCALING_LAW_TRANCHE,
        hypothesis_class=HypothesisClass.SCALING_LAW,
        failure_modes=[],
    )
    record = SliceExecutionRecord(
        tranche_id="scaling_probe",
        slice_id="s1",
        tranche_type=TrancheType.SCALING_LAW_TRANCHE,
        hypothesis_class=HypothesisClass.SCALING_LAW,
        status=SliceRunStatus.COMPLETED,
        output_dir="artifacts/s1",
        utility=SliceUtility(
            utility_score=0.9,
            scaling_score=0.9,
            identifiability_score=0.8,
            measurement_equivalence_score=0.95,
            trace=SliceUtility().trace.model_copy(
                update={"measurement_signal_gap": 0.01},
                deep=True,
            ),
            utility_components=UtilityComponents().model_copy(
                update={
                    "scaling_separation_score": 0.9,
                    "measurement_equivalence_score": 0.95,
                },
                deep=True,
            ),
        ),
        null_model_comparison=SliceNullModelComparison(
            available=True,
            requested=True,
            dominance_classification=NullDominanceClassification.IMPROVES_OVER_NULL,
        ),
    )

    adjudication = sweep_aggregator._build_tranche_adjudication(
        manifest=manifest,
        tranche_plan=resolved_tranche,
        tranche_record=None,
        slice_winners=[],
        successful_slice_records=[record],
        winner_consistency_ratio=1.0,
    )

    assert adjudication.recommendation != GovernanceRecommendation.PROCEED_TO_REFINEMENT
    assert {
        guardrail.code for guardrail in adjudication.guardrails
    } & {
        AdjudicationGuardrailCode.BELOW_MEASUREMENT_RESOLUTION,
        AdjudicationGuardrailCode.DISCRIMINATOR_COVERAGE_GAP,
    }


def test_load_sweep_summary_marks_legacy_contract_downgrade(tmp_path: Path):
    payload = SweepSummary(
        sweep_id="legacy-sweep",
        sweep_name="legacy",
        generated_at=datetime.now(UTC),
        successful_slices=0,
        failed_slices=0,
        equivalence_clusters=[
            EquivalenceCluster(
                cluster_id="equivalence_1",
                tranche_ids=["left", "right"],
                slice_ids=["left_slice", "right_slice"],
                reason="measurement_indistinguishable",
                measurement_equivalence_score=0.94,
                equivalence_margin=0.06,
            )
        ],
    ).model_dump(mode="json")
    payload["weakest_edges"] = []
    payload["adjudication"]["equivalence_clusters"] = payload["equivalence_clusters"]
    payload["adjudication"]["equivalence_graph"] = {"nodes": [], "edges": []}
    path = tmp_path / "legacy_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_sweep_summary(path)

    assert loaded.legacy_contract_downgrade is True
    assert loaded.weakest_edges
    assert any("persisted equivalence graph" in note for note in loaded.legacy_contract_notes)


def test_load_sweep_summary_preserves_persisted_discriminator_contracts(tmp_path: Path):
    payload = SweepSummary(
        sweep_id="canonical-sweep",
        sweep_name="canonical",
        generated_at=datetime.now(UTC),
        successful_slices=1,
        failed_slices=0,
        adjudication=SweepAdjudication(
            weakest_unresolved_edges=[
                EquivalenceEdge(
                    edge_id="canonical-edge",
                    left_tranche_id="left",
                    left_slice_id="left_slice",
                    right_tranche_id="right",
                    right_slice_id="right_slice",
                    equivalence_margin=0.15,
                    tested_axes=["temperature"],
                )
            ],
            equivalence_graph=EquivalenceGraph(
                nodes=["left:left_slice", "right:right_slice"],
                edges=[
                    EquivalenceEdge(
                        edge_id="canonical-edge",
                        left_tranche_id="left",
                        left_slice_id="left_slice",
                        right_tranche_id="right",
                        right_slice_id="right_slice",
                        equivalence_margin=0.15,
                        tested_axes=["temperature"],
                    )
                ],
            ),
        ),
    ).model_dump(mode="json")
    path = tmp_path / "canonical_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_sweep_summary(path)

    assert loaded.legacy_contract_downgrade is False
    assert loaded.weakest_edges[0].edge_id == "canonical-edge"
    assert loaded.adjudication.weakest_unresolved_edges[0].tested_axes == ["temperature"]


def test_sweep_metrics_preserve_distinct_discriminator_stop_reasons():
    instrument_limited = SweepSummary(
        sweep_id="instrument",
        sweep_name="instrument",
        generated_at=datetime.now(UTC),
        successful_slices=0,
        failed_slices=0,
        adjudication=SweepAdjudication(
            recommendation=GovernanceRecommendation.INSTRUMENT_LIMITED,
            promotion_blocked=True,
            promotion_block_reason="INSTRUMENT_LIMITED",
            discriminator_stop_reason=TrancheOutcome.INSTRUMENT_LIMITED,
        ),
    )
    exhausted = instrument_limited.model_copy(
        update={
            "sweep_id": "exhausted",
            "sweep_name": "exhausted",
            "adjudication": SweepAdjudication(
                recommendation=GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY,
                promotion_blocked=True,
                promotion_block_reason="DISCRIMINATOR_EXHAUSTED",
                discriminator_stop_reason=TrancheOutcome.DISCRIMINATOR_EXHAUSTED,
            ),
        },
        deep=True,
    )

    instrument_metrics = sweep_executor._build_sweep_metrics(instrument_limited)
    exhausted_metrics = sweep_executor._build_sweep_metrics(exhausted)

    assert instrument_metrics["discriminator_stop_reason"] == "INSTRUMENT_LIMITED"
    assert exhausted_metrics["discriminator_stop_reason"] == "DISCRIMINATOR_EXHAUSTED"


def test_canonical_graph_priority():
    canonical_edge = EquivalenceEdge(
        edge_id="canonical",
        left_tranche_id="left",
        left_slice_id="left_slice",
        right_tranche_id="right",
        right_slice_id="right_slice",
        equivalence_margin=0.2,
    )
    misleading_edge = EquivalenceEdge(
        edge_id="misleading",
        left_tranche_id="legacy_left",
        left_slice_id="legacy_left_slice",
        right_tranche_id="legacy_right",
        right_slice_id="legacy_right_slice",
        equivalence_margin=0.01,
    )
    summary = SweepSummary(
        sweep_id="priority",
        sweep_name="priority",
        generated_at=datetime.now(UTC),
        successful_slices=0,
        failed_slices=0,
        weakest_edges=[misleading_edge],
        equivalence_clusters=[
            EquivalenceCluster(
                cluster_id="legacy-cluster",
                tranche_ids=["legacy_left", "legacy_right"],
                slice_ids=["legacy_left_slice", "legacy_right_slice"],
                reason="legacy",
                measurement_equivalence_score=0.99,
            )
        ],
        adjudication=SweepAdjudication(
            equivalence_graph=EquivalenceGraph(
                nodes=["left:left_slice", "right:right_slice"],
                edges=[canonical_edge],
            )
        ),
    )

    edges = sweep_contracts.get_equivalence_edges(summary)

    assert [edge.edge_id for edge in edges] == ["canonical"]
    assert summary.legacy_contract_downgrade is False


def test_legacy_downgrade_flag(tmp_path: Path):
    payload = SweepSummary(
        sweep_id="legacy-only",
        sweep_name="legacy-only",
        generated_at=datetime.now(UTC),
        successful_slices=0,
        failed_slices=0,
        equivalence_clusters=[
            EquivalenceCluster(
                cluster_id="cluster_only",
                tranche_ids=["left", "right"],
                slice_ids=["left_slice", "right_slice"],
                reason="measurement_indistinguishable",
                measurement_equivalence_score=0.94,
                equivalence_margin=0.06,
            )
        ],
    ).model_dump(mode="json")
    payload["weakest_edges"] = []
    payload["adjudication"]["equivalence_graph"] = {"nodes": [], "edges": []}
    payload["adjudication"]["equivalence_clusters"] = payload["equivalence_clusters"]
    path = tmp_path / "legacy_downgrade_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_sweep_summary(path)

    assert loaded.legacy_contract_downgrade is True
    assert loaded.adjudication.weakest_unresolved_edges
    assert any("reduced fidelity" in note for note in loaded.legacy_contract_notes)


def test_replay_fidelity(tmp_path: Path):
    canonical_edge = EquivalenceEdge(
        edge_id="roundtrip",
        left_tranche_id="left",
        left_slice_id="left_slice",
        right_tranche_id="right",
        right_slice_id="right_slice",
        equivalence_margin=0.15,
        tested_axes=["temperature"],
    )
    payload = SweepSummary(
        sweep_id="roundtrip",
        sweep_name="roundtrip",
        generated_at=datetime.now(UTC),
        successful_slices=1,
        failed_slices=0,
        adjudication=SweepAdjudication(
            equivalence_graph=EquivalenceGraph(
                nodes=["left:left_slice", "right:right_slice"],
                edges=[canonical_edge],
            ),
            weakest_unresolved_edges=[canonical_edge],
        ),
    ).model_dump(mode="json")
    path = tmp_path / "replay_fidelity_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_sweep_summary(path)

    assert loaded.legacy_contract_downgrade is False
    assert loaded.adjudication.equivalence_graph.edges[0].model_dump() == canonical_edge.model_dump()
    assert loaded.adjudication.weakest_unresolved_edges[0].model_dump() == canonical_edge.model_dump()


def test_stop_reason_integrity():
    instrument_limited = SweepSummary(
        sweep_id="instrument",
        sweep_name="instrument",
        generated_at=datetime.now(UTC),
        successful_slices=0,
        failed_slices=0,
        adjudication=SweepAdjudication(
            recommendation=GovernanceRecommendation.INSTRUMENT_LIMITED,
            promotion_blocked=True,
            promotion_block_reason="INSTRUMENT_LIMITED",
            discriminator_stop_reason=TrancheOutcome.INSTRUMENT_LIMITED,
        ),
    )
    discriminator_exhausted = instrument_limited.model_copy(
        update={
            "sweep_id": "exhausted",
            "sweep_name": "exhausted",
            "adjudication": SweepAdjudication(
                recommendation=GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY,
                promotion_blocked=True,
                promotion_block_reason="DISCRIMINATOR_EXHAUSTED",
                discriminator_stop_reason=TrancheOutcome.DISCRIMINATOR_EXHAUSTED,
            ),
        },
        deep=True,
    )

    instrument_metrics = sweep_executor._build_sweep_metrics(instrument_limited)
    exhausted_metrics = sweep_executor._build_sweep_metrics(discriminator_exhausted)

    assert instrument_metrics["discriminator_stop_reason"] == "INSTRUMENT_LIMITED"
    assert exhausted_metrics["discriminator_stop_reason"] == "DISCRIMINATOR_EXHAUSTED"


def test_rejected_axis_visibility():
    discriminator_fields = DiscriminatorTrancheFields(
        target_hypothesis_pair=["left", "right"],
        discriminator_axis="temperature",
        expected_separation_signature="temperature split",
        orthogonal_axes=[
            OrthogonalAxis(
                axis_id="temperature",
                field=CandidateFilterField.MICROWAVE_MAX_GHZ,
                operator=FilterOperator.GTE,
                values=[1.0, 2.0],
                axis_family="temperature",
            )
        ],
        tested_discriminator_axes=["temperature", "drive_amplitude"],
        rejected_discriminator_axes=["drive_amplitude"],
        rejected_axis_rationale=[
            RejectedAxisRationale(
                axis_key="drive_amplitude",
                reason="orthogonality_rejected",
                redundancy_penalty=0.9,
                blocking_axis="temperature",
            )
        ],
    )
    manifest = SimpleNamespace(
        measurement=MeasurementEquivalenceConfig(),
        plan=SimpleNamespace(
            tranches=[
                SimpleNamespace(
                    tranche_id="disc_a",
                    discriminator_tranche=discriminator_fields,
                )
            ]
        ),
    )
    tranche_summaries = [
        TrancheSummary(
            sweep_id="visibility",
            tranche_id="disc_a",
            objective="visibility",
            status=SweepRunStatus.COMPLETED,
            successful_slices=1,
            failed_slices=0,
            adjudication=TrancheAdjudication(
                tranche_id="disc_a",
                outcomes=[TrancheOutcome.DISCRIMINATOR_EXHAUSTED],
            ),
        )
    ]

    history = sweep_aggregator._discriminator_history(manifest, tranche_summaries)

    assert history[0].tested_discriminator_axes == ["temperature", "drive_amplitude"]
    assert history[0].rejected_discriminator_axes == ["drive_amplitude"]
    assert history[0].rejected_axis_rationale[0].reason == "orthogonality_rejected"


def test_promotion_block_propagation(tmp_path: Path):
    summary = SweepSummary(
        sweep_id="promotion",
        sweep_name="promotion",
        generated_at=datetime.now(UTC),
        successful_slices=0,
        failed_slices=0,
        adjudication=SweepAdjudication(
            recommendation=GovernanceRecommendation.REJECTED_BY_INDISCRIMINABILITY,
            promotion_blocked=True,
            promotion_block_reason="DISCRIMINATOR_EXHAUSTED",
            discriminator_stop_reason=TrancheOutcome.DISCRIMINATOR_EXHAUSTED,
        ),
    )
    metrics = sweep_executor._build_sweep_metrics(summary)
    path = tmp_path / "promotion_block_summary.json"
    path.write_text(json.dumps(summary.model_dump(mode="json")), encoding="utf-8")

    loaded = load_sweep_summary(path)

    assert metrics["promotion_blocked"] is True
    assert metrics["promotion_block_reason"] == "DISCRIMINATOR_EXHAUSTED"
    assert loaded.adjudication.promotion_blocked is True
    assert loaded.adjudication.promotion_block_reason == "DISCRIMINATOR_EXHAUSTED"
