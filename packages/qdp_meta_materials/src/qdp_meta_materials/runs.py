from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qdp_io.serialization import write_json, write_text, write_yaml

from . import __version__
from .config import default_seed_root
from .registry import load_dataset
from .logging_utils import get_logger
from .models import (
    MMMDataset,
    RunComparison,
    RunManifest,
    RunSliceProvenance,
    ScalarValue,
    ScoreResult,
    SweepSpecification,
    UtilityComponents,
    build_provenance,
)
from .reporting import (
    plot_leaderboard,
    plot_score_breakdown,
    render_candidate_report,
    render_run_report,
    write_leaderboard_csv,
)
from .scoring import (
    DEFAULT_SCORING_PROFILE,
    SURROGATE_BACKEND_ID,
    get_scoring_profile,
    rank_dataset,
    results_dataframe,
)
from .sim import LocalPlaceholderBackend, MeepScaffoldBackend

LOGGER = get_logger("runs")


def default_run_directory(base_dir: str | Path | None = None) -> Path:
    """Return the root directory used for persisted run artifacts."""

    base = Path(base_dir) if base_dir is not None else Path("artifacts") / "runs"
    return base.resolve()


def _json_model_payload(model: Any) -> Any:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model


def build_run_metrics(results: list[ScoreResult]) -> dict[str, ScalarValue]:
    """Build the standard metrics payload for a scored run."""

    metrics: dict[str, ScalarValue] = {
        "candidate_count": len(results),
        "top_score": results[0].score if results else 0.0,
        "top_total_utility": results[0].total_utility if results else None,
        "lead_branch_count": sum(result.decision_band == "lead_branch" for result in results),
        "primary_screen_count": sum(result.decision_band == "primary_screen" for result in results),
        "sandbox_count": sum(result.decision_band == "sandbox_only" for result in results),
        "reject_count": sum(result.decision_band == "reject" for result in results),
    }
    deltas = [result.score_delta for result in results if result.score_delta is not None]
    baselines = [result.baseline_score for result in results if result.baseline_score is not None]
    if deltas:
        metrics.update(
            {
                "top_baseline_score": results[0].baseline_score,
                "top_null_score": results[0].null_score,
                "top_score_delta": results[0].score_delta,
                "mean_baseline_score": sum(baselines) / len(baselines) if baselines else None,
                "mean_score_delta": sum(deltas) / len(deltas),
                "positive_delta_rate": sum(delta > 0 for delta in deltas) / len(deltas),
            }
        )
    return metrics


def execute_scoring_run(
    *,
    dataset: MMMDataset,
    results: list[ScoreResult],
    profile: str,
    top_n: int,
    output_dir: str | Path,
    command: str,
    run_id: str | None = None,
    created_at: datetime | None = None,
    params: dict[str, ScalarValue] | None = None,
    slice_provenance: RunSliceProvenance | None = None,
    score_breakdown: UtilityComponents | None = None,
    results_filename: str = "score_results.json",
    write_leaderboard_csv_artifact: bool = True,
    include_plots: bool = True,
    include_candidate_report: bool = True,
    include_simulation_artifacts: bool = False,
) -> RunManifest:
    """Persist the standard scored-run artifact bundle for a result set."""

    created = created_at or datetime.now(UTC)
    resolved_run_id = run_id or created.strftime("%Y%m%dT%H%M%SZ") + f"-{profile}"
    run_dir = Path(output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    frame = results_dataframe(dataset, results)

    leaderboard_csv_path: Path | None = None
    if write_leaderboard_csv_artifact:
        leaderboard_csv_path = write_leaderboard_csv(frame, run_dir / "leaderboard.csv")
    leaderboard_plot_path: Path | None = None
    breakdown_plot_path: Path | None = None
    if include_plots:
        leaderboard_plot_path = plot_leaderboard(frame, run_dir / "leaderboard.png", top_n=top_n)
        breakdown_plot_path = plot_score_breakdown(
            frame,
            run_dir / "score_breakdown.png",
            top_n=min(top_n, 5),
        )

    top_candidate_report = reports_dir / "candidate_report.md"
    if include_candidate_report and results:
        write_text(top_candidate_report, render_candidate_report(dataset, results[0]))

    artifact_paths: dict[str, str] = {
        "summary_report": str(run_dir / "RUN_SUMMARY.md"),
        "manifest": str(run_dir / "run_manifest.json"),
        "provenance": str(run_dir / "provenance.json"),
        "metrics": str(run_dir / "metrics.json"),
        "params": str(run_dir / "params.yaml"),
        "scores": str(run_dir / results_filename),
    }
    if leaderboard_csv_path is not None:
        artifact_paths["leaderboard_csv"] = str(leaderboard_csv_path)
    if include_plots and leaderboard_plot_path is not None and breakdown_plot_path is not None:
        artifact_paths["leaderboard_plot"] = str(leaderboard_plot_path)
        artifact_paths["score_breakdown_plot"] = str(breakdown_plot_path)
    if include_candidate_report and results:
        artifact_paths["candidate_report"] = str(top_candidate_report)

    if include_simulation_artifacts and results:
        scoring_profile = get_scoring_profile(profile)
        sweep = SweepSpecification(
            sweep_id=f"{resolved_run_id}-default-sweep",
            domain="electromagnetic",
            target_frequency_window_ghz=(
                scoring_profile.target_frequency_ghz - 1.0,
                scoring_profile.target_frequency_ghz + 1.0,
            ),
            sample_count=201,
            observables=["OBS-BG-SHIFT", "OBS-PKG-S21"],
            notes="Repository demo sweep definition for backend scaffolding.",
        )
        local_backend = LocalPlaceholderBackend()
        local_bundle = local_backend.build_bundle(dataset, results[0].genome_id, sweep)
        local_result = local_backend.run(local_bundle)
        meep_backend = MeepScaffoldBackend()
        meep_geometry = meep_backend.translate_geometry(dataset, results[0].genome_id)
        simulation_job_path = run_dir / "simulation_job.json"
        simulation_preflight_path = run_dir / "simulation_preflight.json"
        meep_scaffold_path = run_dir / "meep_geometry_scaffold.json"
        write_json(simulation_job_path, local_bundle.job.model_dump(mode="json"))
        write_json(simulation_preflight_path, local_result.model_dump(mode="json"))
        write_json(meep_scaffold_path, meep_geometry.model_dump(mode="json"))
        artifact_paths.update(
            {
                "simulation_job": str(simulation_job_path),
                "simulation_preflight": str(simulation_preflight_path),
                "meep_geometry_scaffold": str(meep_scaffold_path),
            }
        )

    provenance = build_provenance(
        run_id=resolved_run_id,
        source_root=dataset.root,
        source_artifacts=dataset.artifact_ids,
        scoring_profile=profile,
        score_backend=SURROGATE_BACKEND_ID,
        command=command,
        application_version=__version__,
        environment={"python_entrypoint": "qdp-meta-materials"},
    )

    merged_params: dict[str, ScalarValue] = {
        "profile": profile,
        "top_n": top_n,
        "dataset_root": str(dataset.root),
        "score_backend": SURROGATE_BACKEND_ID,
    }
    if params is not None:
        merged_params.update(params)

    manifest = RunManifest(
        run_id=resolved_run_id,
        created_at=created,
        root=str(dataset.root),
        scoring_profile=profile,
        score_backend=SURROGATE_BACKEND_ID,
        top_candidate_id=results[0].genome_id if results else None,
        artifact_paths=artifact_paths,
        parameters=merged_params,
        metrics=build_run_metrics(results),
        score_breakdown=score_breakdown.model_copy(deep=True) if score_breakdown else None,
        slice_provenance=slice_provenance.model_copy(deep=True) if slice_provenance else None,
        provenance=provenance,
    )
    if score_breakdown is not None:
        manifest.metrics.update(
            {
                "identifiability_score": score_breakdown.identifiability_score,
                "scaling_score": score_breakdown.scaling_score,
                "scaling_separation_score": score_breakdown.scaling_separation_score,
                "null_equivalence_score": score_breakdown.null_equivalence_score,
                "failure_mode_match_score": score_breakdown.failure_mode_match_score,
            }
        )

    write_text(run_dir / "RUN_SUMMARY.md", render_run_report(dataset, results, manifest))
    write_json(run_dir / "provenance.json", provenance.model_dump(mode="json"))
    write_json(run_dir / "metrics.json", manifest.metrics)
    write_yaml(run_dir / "params.yaml", manifest.parameters)
    write_json(run_dir / "run_manifest.json", manifest.model_dump(mode="json"))
    write_json(
        run_dir / results_filename,
        [_json_model_payload(result) for result in results],
    )
    LOGGER.info("Persisted scored run artifacts to %s", run_dir)
    return manifest


def execute_demo_run(
    *,
    root: str | Path | None = None,
    profile: str = DEFAULT_SCORING_PROFILE,
    top_n: int = 10,
    output_dir: str | Path | None = None,
    command: str = "qdp-meta-materials run-demo",
) -> RunManifest:
    """Execute the end-to-end demo scoring pipeline and persist its artifacts."""

    LOGGER.info("Executing demo run with profile=%s top_n=%s", profile, top_n)
    dataset = load_dataset(root or default_seed_root())
    results = rank_dataset(dataset, profile=profile)
    created_at = datetime.now(UTC)
    run_id = created_at.strftime("%Y%m%dT%H%M%SZ") + f"-{profile}"
    run_dir = Path(output_dir) if output_dir is not None else default_run_directory() / run_id
    return execute_scoring_run(
        dataset=dataset,
        results=results,
        profile=profile,
        top_n=top_n,
        output_dir=run_dir,
        command=command,
        run_id=run_id,
        created_at=created_at,
        include_plots=True,
        include_candidate_report=True,
        include_simulation_artifacts=True,
    )


def load_run_manifest(path: str | Path) -> RunManifest:
    """Load a persisted run manifest from a directory or manifest path."""

    manifest_path = Path(path)
    if manifest_path.is_dir():
        manifest_path = manifest_path / "run_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return RunManifest.model_validate(payload)


def compare_runs(left: str | Path, right: str | Path) -> RunComparison:
    """Compare two persisted run manifests."""

    left_manifest = load_run_manifest(left)
    right_manifest = load_run_manifest(right)
    left_top = left_manifest.metrics.get("top_score", 0.0)
    right_top = right_manifest.metrics.get("top_score", 0.0)
    left_count = left_manifest.metrics.get("candidate_count", 0)
    right_count = right_manifest.metrics.get("candidate_count", 0)

    def _as_float(value: str | int | float | bool | None) -> float:
        if value is None:
            return 0.0
        if isinstance(value, bool):
            return float(int(value))
        return float(value)

    return RunComparison(
        left_run_id=left_manifest.run_id,
        right_run_id=right_manifest.run_id,
        score_deltas={
            "top_score": _as_float(right_top) - _as_float(left_top),
            "candidate_count": _as_float(right_count) - _as_float(left_count),
        },
        top_candidate_shift={
            "left": left_manifest.top_candidate_id,
            "right": right_manifest.top_candidate_id,
            "profile_left": left_manifest.scoring_profile,
            "profile_right": right_manifest.scoring_profile,
        },
        summary=(
            f"Compared {left_manifest.run_id} ({left_manifest.scoring_profile}) to "
            f"{right_manifest.run_id} ({right_manifest.scoring_profile})."
        ),
    )
