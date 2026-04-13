from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from .config import default_seed_root
from .errors import MMMStudioError
from .io import load_dataset, write_json, write_text
from .reporting import (
    plot_leaderboard,
    render_candidate_report,
    write_leaderboard_csv,
)
from .runs import compare_runs, execute_demo_run, load_run_manifest
from .scoring import (
    DEFAULT_SCORING_PROFILE,
    get_scoring_profile,
    leaderboard_dataframe,
    rank_dataset,
)
from .sweeps import (
    execute_sweep,
    load_sweep_spec,
    load_sweep_summary,
    load_tranche_summary,
    plan_sweep,
)
from .sweeps.models import NullModelMode
from .sweeps.tranche_library import build_preset_tranches
from .validation import validate_repository

app = typer.Typer(add_completion=False, no_args_is_help=True)


def resolve_root(root: Path | None) -> Path:
    return root if root is not None else default_seed_root()


def _format_display_frame(frame: Any) -> Any:
    display = frame.copy()
    numeric_cols = [
        column
        for column in [
            "score",
            "coherence_uplift",
            "null_separation",
            "detectability_margin",
            "geometry_scaling_clarity",
            "fabrication_robustness",
            "replication_portability",
            "simulation_confidence",
            "standard_lab_feasibility",
        ]
        if column in display.columns
    ]
    for col in numeric_cols:
        display[col] = display[col].map(lambda value: f"{value:.3f}")
    return display


def _fail_with_message(message: str) -> None:
    typer.echo(f"ERROR: {message}", err=True)
    raise typer.Exit(code=1)


def _apply_sweep_overrides(
    spec: Any,
    *,
    adaptive: bool,
    baseline_profile: str | None,
    preset: str | None = None,
    enforce_identifiability: bool = False,
    require_null_dominance: bool = False,
) -> Any:
    if adaptive:
        spec.adaptive.enabled = True
    if baseline_profile is not None:
        spec.adaptive.enabled = True
        spec.adaptive.null_model.enabled = True
        spec.adaptive.null_model.mode = NullModelMode.PROFILE
        spec.adaptive.null_model.baseline_profile = baseline_profile
    if preset is not None:
        _apply_sweep_preset(spec, preset)
    if enforce_identifiability:
        spec.enforce_identifiability = True
    if require_null_dominance:
        spec.require_null_dominance = True
    return spec


def _apply_sweep_preset(spec: Any, preset: str) -> None:
    normalized = preset.strip().lower()
    spec.adaptive.enabled = True
    spec.adaptive.null_model.enabled = True
    spec.adaptive.cross_tranche.enabled = True
    spec.tranches = build_preset_tranches(normalized)
    if normalized in {"discriminative", "standard", "standard_discriminative"}:
        spec.enforce_identifiability = True
        spec.require_null_dominance = True
        spec.adaptive.refinement.max_refinements_per_slice = 1
        spec.adaptive.refinement.max_total_refinements_per_tranche = 2
        spec.adaptive.cross_tranche.max_interaction_slices = 2
    elif normalized in {"null_dominant", "aggressive"}:
        spec.enforce_identifiability = True
        spec.require_null_dominance = True
        spec.adaptive.refinement.max_refinements_per_slice = 2
        spec.adaptive.refinement.max_total_refinements_per_tranche = 6
        spec.adaptive.cross_tranche.max_interaction_slices = 3
    elif normalized in {"scaling_first", "scaling-heavy"}:
        spec.enforce_identifiability = True
        spec.require_null_dominance = True
        spec.adaptive.refinement.max_refinements_per_slice = 1
        spec.adaptive.refinement.max_total_refinements_per_tranche = 4
        spec.adaptive.cross_tranche.max_interaction_slices = 2
        spec.adaptive.utility_weights.scaling = 0.35
        spec.adaptive.utility_weights.residual_quality = 0.20
        spec.adaptive.utility_weights.null_model_delta = 0.20
        spec.adaptive.utility_weights.identifiability = 0.15
        spec.adaptive.utility_weights.parameter_penalty = 0.10
    elif normalized in {"stress_test_heavy", "stress-heavy"}:
        spec.enforce_identifiability = True
        spec.require_null_dominance = True
        spec.adaptive.refinement.max_refinements_per_slice = 2
        spec.adaptive.refinement.max_total_refinements_per_tranche = 4
        spec.adaptive.cross_tranche.max_interaction_slices = 2
    else:
        raise ValueError(
            "Unknown sweep preset "
            f"'{preset}'. Expected one of: discriminative, null_dominant, "
            "scaling_first, stress_test_heavy."
        )


def _echo_adaptive_configuration(manifest: Any) -> None:
    adaptive = manifest.adaptive
    typer.echo(f"Adaptive enabled: {adaptive.enabled}")
    if not adaptive.enabled:
        return
    typer.echo(f"Adaptive seed: {adaptive.seed}")
    typer.echo(
        "Utility weights: "
        f"residual={adaptive.utility_weights.residual_quality:.2f}, "
        f"null={adaptive.utility_weights.null_model_delta:.2f}, "
        f"identifiability={adaptive.utility_weights.identifiability:.2f}, "
        f"scaling={adaptive.utility_weights.scaling:.2f}, "
        f"parameter_penalty={adaptive.utility_weights.parameter_penalty:.2f}"
    )
    typer.echo(
        "Refinement policy: "
        f"floor={adaptive.refinement.candidate_count_floor}, "
        f"min_pending={adaptive.refinement.minimum_pending_per_phase}, "
        f"instability_threshold={adaptive.refinement.instability_threshold:.2f}, "
        f"divergence_threshold={adaptive.refinement.divergence_threshold:.2f}, "
        f"prune_threshold={adaptive.refinement.utility_prune_threshold:.2f}"
    )
    typer.echo(
        "Null model: "
        f"enabled={adaptive.null_model.enabled}, "
        f"mode={adaptive.null_model.mode.value}, "
        f"baseline_profile={adaptive.null_model.baseline_profile or 'n/a'}"
    )
    typer.echo(
        "Cross-tranche: "
        f"enabled={adaptive.cross_tranche.enabled}, "
        f"priority_threshold={adaptive.cross_tranche.priority_threshold:.2f}, "
        f"max_interactions={adaptive.cross_tranche.max_interaction_slices}"
    )
    typer.echo(
        "Require null dominance: "
        f"{any(tranche.tranche_type.value == 'null_dominance_tranche' for tranche in manifest.plan.tranches)}"
    )
    typer.echo(
        "Enforce identifiability: "
        f"{any(tranche.hypothesis_class.value == 'identifiability' for tranche in manifest.plan.tranches)}"
    )


@app.command()
def validate(root: Path | None = typer.Option(None, help="Path to the MMM seed root.")) -> None:
    """Validate the typed seed registry and reference graph."""

    report = validate_repository(resolve_root(root))
    typer.echo("MMM STUDIO VALIDATION")
    typer.echo("=====================")
    typer.echo(f"Root: {report.root}")

    if report.stats:
        for key, value in report.stats.items():
            typer.echo(f"{key}: {value}")

    if report.issues:
        typer.echo("\nIssues")
        typer.echo("------")
        for issue in report.issues:
            label = issue.severity.upper()
            location = f" [{issue.location}]" if issue.location else ""
            typer.echo(f"- {label} {issue.code}{location}: {issue.message}")

    if report.warnings:
        typer.echo("\nWarnings")
        typer.echo("--------")
        for warning in report.warnings:
            typer.echo(f"- {warning}")

    if report.errors:
        typer.echo("\nFAIL")
        typer.echo("----")
        for error in report.errors:
            typer.echo(f"- {error}")
        raise typer.Exit(code=1)

    typer.echo("\nPASS")
    typer.echo("----")
    typer.echo("All required files exist and all critical references resolve.")


@app.command()
def summary(root: Path | None = typer.Option(None, help="Path to the MMM seed root.")) -> None:
    """Print a concise summary of the registry and current leaderboard."""

    dataset = load_dataset(resolve_root(root))
    frame = leaderboard_dataframe(dataset, profile=DEFAULT_SCORING_PROFILE)
    summary = dataset.to_summary()

    typer.echo("MMM STUDIO SUMMARY")
    typer.echo("==================")
    typer.echo(f"Root: {dataset.root}")
    typer.echo(f"Artifacts: {len(summary.artifact_ids)}")
    typer.echo(f"Mechanisms: {summary.mechanisms}")
    typer.echo(f"Structures: {summary.structures}")
    typer.echo(f"Genomes: {summary.genomes}")
    typer.echo(f"Protocols: {summary.protocols}")
    typer.echo(f"Validation rules: {summary.validation_rules}")
    typer.echo(f"Material systems: {summary.material_systems}")
    typer.echo(f"Environment models: {summary.environment_models}")
    typer.echo("")
    typer.echo("Top candidates")
    typer.echo("--------------")
    display = _format_display_frame(
        frame[
            [
                "rank",
                "genome_id",
                "parent_structure_id",
                "screening_status",
                "scoring_profile",
                "score",
                "decision_band",
            ]
        ].head(5)
    )
    typer.echo(display.to_string(index=False))


@app.command()
def leaderboard(
    top_n: int = typer.Option(10, min=1, help="Number of rows to print."),
    root: Path | None = typer.Option(None, help="Path to the MMM seed root."),
    out: Path | None = typer.Option(None, help="Optional CSV output path."),
    profile: str = typer.Option(DEFAULT_SCORING_PROFILE, help="Scoring profile."),
    screening_status: str | None = typer.Option(None, help="Optional screening-status filter."),
) -> None:
    """Print the candidate leaderboard under a selected scoring profile."""

    get_scoring_profile(profile)
    dataset = load_dataset(resolve_root(root))
    frame = leaderboard_dataframe(dataset, profile=profile, screening_status=screening_status)

    display = _format_display_frame(frame.head(top_n))

    typer.echo("MMM STUDIO LEADERBOARD")
    typer.echo("======================")
    typer.echo(display.to_string(index=False))

    if out is not None:
        write_leaderboard_csv(frame, out)
        typer.echo(f"\nWrote {out}")


@app.command()
def plot(
    output: Path = typer.Option(Path("outputs/leaderboard.png"), help="PNG output path."),
    top_n: int = typer.Option(10, min=1, help="Number of candidates to include."),
    root: Path | None = typer.Option(None, help="Path to the MMM seed root."),
    profile: str = typer.Option(DEFAULT_SCORING_PROFILE, help="Scoring profile."),
) -> None:
    """Create a PNG leaderboard plot."""

    get_scoring_profile(profile)
    dataset = load_dataset(resolve_root(root))
    frame = leaderboard_dataframe(dataset, profile=profile)
    plot_leaderboard(frame, output=output, top_n=top_n)
    typer.echo(f"Wrote {output}")


@app.command()
def score(
    top_n: int = typer.Option(10, min=1, help="Number of ranked rows to print."),
    root: Path | None = typer.Option(None, help="Path to the MMM seed root."),
    profile: str = typer.Option(DEFAULT_SCORING_PROFILE, help="Scoring profile."),
    screening_status: str | None = typer.Option(None, help="Optional screening-status filter."),
    csv_out: Path | None = typer.Option(None, help="Optional CSV artifact path."),
    json_out: Path | None = typer.Option(None, help="Optional JSON artifact path."),
) -> None:
    """Score candidates and optionally export machine-readable results."""

    dataset = load_dataset(resolve_root(root))
    results = rank_dataset(dataset, profile=profile, screening_status=screening_status)
    frame = leaderboard_dataframe(dataset, profile=profile, screening_status=screening_status)

    typer.echo("MMM STUDIO SCORING RUN")
    typer.echo("======================")
    typer.echo(f"Profile: {profile}")
    typer.echo(f"Backend: {results[0].score_backend if results else 'n/a'}")
    typer.echo(_format_display_frame(frame.head(top_n)).to_string(index=False))

    if csv_out is not None:
        write_leaderboard_csv(frame, csv_out)
        typer.echo(f"\nWrote {csv_out}")
    if json_out is not None:
        write_json(json_out, [result.model_dump(mode="json") for result in results])
        typer.echo(f"Wrote {json_out}")


@app.command("run-demo")
def run_demo(
    root: Path | None = typer.Option(None, help="Path to the MMM seed root."),
    profile: str = typer.Option(DEFAULT_SCORING_PROFILE, help="Scoring profile."),
    top_n: int = typer.Option(
        10, min=1, help="Number of candidates to include in plots and summaries."
    ),
    output_dir: Path | None = typer.Option(None, help="Optional explicit run directory."),
) -> None:
    """Execute the end-to-end demo pipeline and persist artifacts."""

    manifest = execute_demo_run(
        root=resolve_root(root),
        profile=profile,
        top_n=top_n,
        output_dir=output_dir,
        command="mmm-studio run-demo",
    )
    typer.echo("MMM STUDIO DEMO RUN")
    typer.echo("===================")
    typer.echo(f"Run ID: {manifest.run_id}")
    typer.echo(f"Profile: {manifest.scoring_profile}")
    typer.echo(f"Top candidate: {manifest.top_candidate_id}")
    typer.echo(f"Manifest: {manifest.artifact_paths['manifest']}")
    typer.echo(f"Summary: {manifest.artifact_paths['summary_report']}")


@app.command("export-report")
def export_report(
    candidate_id: str | None = typer.Option(
        None, help="Candidate genome ID. Defaults to the current top candidate."
    ),
    root: Path | None = typer.Option(None, help="Path to the MMM seed root."),
    profile: str = typer.Option(DEFAULT_SCORING_PROFILE, help="Scoring profile."),
    output: Path = typer.Option(Path("outputs/candidate_report.md"), help="Markdown output path."),
) -> None:
    """Export a Markdown candidate report for the chosen profile."""

    dataset = load_dataset(resolve_root(root))
    results = rank_dataset(dataset, profile=profile)
    target_result = (
        results[0]
        if candidate_id is None
        else next(
            (result for result in results if result.genome_id == candidate_id),
            None,
        )
    )
    if target_result is None:
        raise typer.BadParameter(f"Unknown genome_id: {candidate_id}")

    write_text(output, render_candidate_report(dataset, target_result))
    typer.echo(f"Wrote {output}")


@app.command()
def provenance(run_dir: Path = typer.Argument(..., help="Run directory or manifest path.")) -> None:
    """Inspect a persisted run manifest and provenance record."""

    manifest = load_run_manifest(run_dir)
    typer.echo("MMM STUDIO PROVENANCE")
    typer.echo("====================")
    typer.echo(f"Run ID: {manifest.run_id}")
    typer.echo(f"Created: {manifest.created_at.isoformat()}")
    typer.echo(f"Dataset root: {manifest.root}")
    typer.echo(f"Profile: {manifest.scoring_profile}")
    typer.echo(f"Backend: {manifest.score_backend}")
    typer.echo(f"Top candidate: {manifest.top_candidate_id}")
    typer.echo(f"Artifacts: {len(manifest.artifact_paths)}")
    typer.echo("")
    for name, path in sorted(manifest.artifact_paths.items()):
        typer.echo(f"- {name}: {path}")


@app.command("compare-runs")
def compare_runs_command(
    left: Path = typer.Argument(..., help="Left run directory or manifest path."),
    right: Path = typer.Argument(..., help="Right run directory or manifest path."),
) -> None:
    """Compare two persisted runs at the manifest level."""

    comparison = compare_runs(left, right)
    typer.echo("MMM STUDIO RUN COMPARISON")
    typer.echo("=========================")
    typer.echo(comparison.summary)
    typer.echo("")
    typer.echo("Score deltas")
    typer.echo("------------")
    for key, value in comparison.score_deltas.items():
        typer.echo(f"- {key}: {value:+.3f}")
    typer.echo("")
    typer.echo("Top candidate shift")
    typer.echo("-------------------")
    for key, shift_value in comparison.top_candidate_shift.items():
        typer.echo(f"- {key}: {shift_value}")


@app.command("sweep-validate")
def sweep_validate(
    spec: Path = typer.Argument(..., help="Path to the sweep YAML or JSON spec."),
    root: Path | None = typer.Option(None, help="Optional path to the MMM seed root."),
    adaptive: bool = typer.Option(
        False,
        "--adaptive",
        help="Enable adaptive sweep planning for this invocation.",
    ),
    baseline_profile: str | None = typer.Option(
        None,
        help="Override the adaptive null-model baseline scoring profile.",
    ),
    preset: str | None = typer.Option(
        None,
        help=(
            "Optional preset tranche library: discriminative, scaling_first, "
            "null_dominant, or stress_test_heavy."
        ),
    ),
    enforce_identifiability: bool = typer.Option(
        False,
        "--enforce-identifiability",
        help="Reject plans that do not include identifiability tranche coverage.",
    ),
    require_null_dominance: bool = typer.Option(
        False,
        "--require-null-dominance",
        help="Reject plans that do not include null-dominance tranche coverage.",
    ),
) -> None:
    """Validate and normalize a sweep spec without executing it."""

    try:
        sweep_spec = load_sweep_spec(spec)
        _apply_sweep_overrides(
            sweep_spec,
            adaptive=adaptive,
            baseline_profile=baseline_profile,
            preset=preset,
            enforce_identifiability=enforce_identifiability,
            require_null_dominance=require_null_dominance,
        )
        manifest = plan_sweep(
            sweep_spec,
            dataset_root=resolve_root(root),
            command="mmm-studio sweep-validate",
            spec_source=spec,
        )
    except (MMMStudioError, FileNotFoundError, ValueError) as exc:
        _fail_with_message(str(exc))

    typer.echo("MMM STUDIO SWEEP VALIDATION")
    typer.echo("===========================")
    typer.echo(f"Sweep ID: {manifest.sweep_id}")
    typer.echo(f"Sweep: {manifest.sweep_name}")
    typer.echo(f"Dataset root: {manifest.dataset_root}")
    typer.echo(f"Planned tranches: {len(manifest.plan.tranches)}")
    _echo_adaptive_configuration(manifest)
    typer.echo("")
    for tranche in manifest.plan.tranches:
        typer.echo(f"[{tranche.tranche_id}] {tranche.objective}")
        for slice_plan in tranche.slices:
            typer.echo(
                f"  - {slice_plan.slice_id}: profile={slice_plan.resolved_profile} "
                f"candidates={slice_plan.candidate_count}"
            )


@app.command("sweep-plan")
def sweep_plan(
    spec: Path = typer.Argument(..., help="Path to the sweep YAML or JSON spec."),
    output: Path = typer.Option(..., "--output", help="Directory for the planned sweep manifest."),
    root: Path | None = typer.Option(None, help="Optional path to the MMM seed root."),
    adaptive: bool = typer.Option(
        False,
        "--adaptive",
        help="Enable adaptive sweep planning for this invocation.",
    ),
    baseline_profile: str | None = typer.Option(
        None,
        help="Override the adaptive null-model baseline scoring profile.",
    ),
    preset: str | None = typer.Option(
        None,
        help=(
            "Optional preset tranche library: discriminative, scaling_first, "
            "null_dominant, or stress_test_heavy."
        ),
    ),
    enforce_identifiability: bool = typer.Option(
        False,
        "--enforce-identifiability",
        help="Reject plans that do not include identifiability tranche coverage.",
    ),
    require_null_dominance: bool = typer.Option(
        False,
        "--require-null-dominance",
        help="Reject plans that do not include null-dominance tranche coverage.",
    ),
) -> None:
    """Write a normalized sweep manifest without executing slices."""

    try:
        sweep_spec = load_sweep_spec(spec)
        _apply_sweep_overrides(
            sweep_spec,
            adaptive=adaptive,
            baseline_profile=baseline_profile,
            preset=preset,
            enforce_identifiability=enforce_identifiability,
            require_null_dominance=require_null_dominance,
        )
        manifest = plan_sweep(
            sweep_spec,
            dataset_root=resolve_root(root),
            output_dir=output,
            command="mmm-studio sweep-plan",
            spec_source=spec,
        )
        write_json(output / "sweep_manifest.json", manifest.model_dump(mode="json"))
    except (MMMStudioError, FileNotFoundError, ValueError) as exc:
        _fail_with_message(str(exc))

    typer.echo("MMM STUDIO SWEEP PLAN")
    typer.echo("=====================")
    typer.echo(f"Sweep ID: {manifest.sweep_id}")
    typer.echo(f"Manifest: {output / 'sweep_manifest.json'}")
    typer.echo(f"Planned slices: {sum(len(tranche.slices) for tranche in manifest.plan.tranches)}")
    _echo_adaptive_configuration(manifest)


@app.command("sweep-run")
def sweep_run(
    spec: Path = typer.Argument(..., help="Path to the sweep YAML or JSON spec."),
    output_dir: Path | None = typer.Option(None, help="Optional explicit sweep run directory."),
    root: Path | None = typer.Option(None, help="Optional path to the MMM seed root."),
    adaptive: bool = typer.Option(
        False,
        "--adaptive",
        help="Enable adaptive sweep execution for this invocation.",
    ),
    baseline_profile: str | None = typer.Option(
        None,
        help="Override the adaptive null-model baseline scoring profile.",
    ),
    preset: str | None = typer.Option(
        None,
        help=(
            "Optional preset tranche library: discriminative, scaling_first, "
            "null_dominant, or stress_test_heavy."
        ),
    ),
    enforce_identifiability: bool = typer.Option(
        False,
        "--enforce-identifiability",
        help="Reject plans that do not include identifiability tranche coverage.",
    ),
    require_null_dominance: bool = typer.Option(
        False,
        "--require-null-dominance",
        help="Reject plans that do not include null-dominance tranche coverage.",
    ),
) -> None:
    """Execute a sweep spec end to end."""

    try:
        sweep_spec = load_sweep_spec(spec)
        _apply_sweep_overrides(
            sweep_spec,
            adaptive=adaptive,
            baseline_profile=baseline_profile,
            preset=preset,
            enforce_identifiability=enforce_identifiability,
            require_null_dominance=require_null_dominance,
        )
        manifest, summary = execute_sweep(
            sweep_spec,
            dataset_root=resolve_root(root),
            output_dir=output_dir,
            command="mmm-studio sweep-run",
            spec_source=spec,
        )
    except (MMMStudioError, FileNotFoundError, ValueError) as exc:
        _fail_with_message(str(exc))

    typer.echo("MMM STUDIO SWEEP RUN")
    typer.echo("====================")
    typer.echo(f"Sweep ID: {manifest.sweep_id}")
    typer.echo(f"Output: {manifest.output_root}")
    typer.echo(f"Successful slices: {summary.successful_slices}")
    typer.echo(f"Failed slices: {summary.failed_slices}")
    typer.echo(f"Pruned slices: {summary.pruned_slices}")
    mean_delta = (
        f"{summary.null_model_summary.mean_score_delta:.3f}"
        if summary.null_model_summary.mean_score_delta is not None
        else "n/a"
    )
    typer.echo(
        "Adaptive audit: "
        f"generated_refinements={summary.adaptive_audit.refinements_generated}, "
        f"retained_frontier={summary.adaptive_audit.pruning_retained}, "
        f"cross_tranche_generated={summary.adaptive_audit.cross_tranche_generated}"
    )
    typer.echo(
        "Null-model rollup: "
        f"requested={summary.null_model_summary.requested_slices}, "
        f"available={summary.null_model_summary.available_slices}, "
        f"mean_delta={mean_delta}"
    )
    typer.echo(
        "Governance: "
        f"recommendation={summary.adjudication.recommendation.value}, "
        f"promotion_blocked={summary.adjudication.promotion_blocked}, "
        f"promotion_block_reason={summary.adjudication.promotion_block_reason or 'none'}, "
        f"stop_reason="
        f"{summary.adjudication.discriminator_stop_reason.value if summary.adjudication.discriminator_stop_reason is not None else 'n/a'}"
    )
    if summary.legacy_contract_downgrade:
        typer.echo(
            "Downgrade: "
            f"{'; '.join(summary.legacy_contract_notes) if summary.legacy_contract_notes else 'legacy compatibility mode'}"
        )
    typer.echo(f"Manifest: {manifest.artifact_paths['manifest']}")
    typer.echo(f"Summary: {manifest.artifact_paths['summary_json']}")


@app.command("sweep-summary")
def sweep_summary(
    sweep_run_dir: Path = typer.Argument(..., help="Sweep run directory."),
) -> None:
    """Print the sweep-level aggregate summary."""

    try:
        summary = load_sweep_summary(sweep_run_dir)
    except (MMMStudioError, FileNotFoundError, ValueError) as exc:
        _fail_with_message(str(exc))

    typer.echo("MMM STUDIO SWEEP SUMMARY")
    typer.echo("========================")
    typer.echo(f"Sweep ID: {summary.sweep_id}")
    typer.echo(f"Successful slices: {summary.successful_slices}")
    typer.echo(f"Failed slices: {summary.failed_slices}")
    typer.echo(f"Pruned slices: {summary.pruned_slices}")
    typer.echo(
        f"Null-model availability: {summary.null_model_summary.available_slices}/"
        f"{summary.null_model_summary.requested_slices}"
    )
    typer.echo(f"Governance: {summary.adjudication.recommendation.value}")
    typer.echo(
        "Promotion block: "
        f"{summary.adjudication.promotion_block_reason or 'none'}"
    )
    typer.echo(
        "Discriminator stop: "
        f"{summary.adjudication.discriminator_stop_reason.value if summary.adjudication.discriminator_stop_reason is not None else 'n/a'}"
    )
    if summary.legacy_contract_downgrade:
        typer.echo(
            "Downgrade notes: "
            f"{'; '.join(summary.legacy_contract_notes)}"
        )
    typer.echo("")
    typer.echo("Highlights")
    typer.echo("----------")
    for highlight in summary.summary_highlights:
        typer.echo(f"- {highlight}")
    typer.echo("")
    typer.echo("Top aggregate candidates")
    typer.echo("------------------------")
    for index, aggregate in enumerate(summary.aggregate_rankings[:10], start=1):
        typer.echo(
            f"{index}. {aggregate.genome_id} "
            f"(robustness={aggregate.robustness_score:.3f}, "
            f"mean_rank={aggregate.mean_rank:.2f}, "
            f"sensitivity={aggregate.profile_sensitivity_score:.3f})"
        )
    if summary.adjudication.weakest_unresolved_edges:
        typer.echo("")
        typer.echo("Weakest unresolved edges")
        typer.echo("-----------------------")
        for edge in summary.adjudication.weakest_unresolved_edges[:5]:
            typer.echo(
                f"- {edge.left_tranche_id}/{edge.left_slice_id} vs "
                f"{edge.right_tranche_id}/{edge.right_slice_id}: "
                f"margin={edge.equivalence_margin:.3f}, "
                f"tested_axes={','.join(edge.tested_axes) if edge.tested_axes else 'n/a'}"
            )
    if summary.adjudication.discriminator_history:
        typer.echo("")
        typer.echo("Discriminator history")
        typer.echo("---------------------")
        for entry in summary.adjudication.discriminator_history[:5]:
            rejected = (
                "; ".join(
                    f"{item.axis_key}:{item.reason}"
                    for item in entry.rejected_axis_rationale
                )
                if entry.rejected_axis_rationale
                else "none"
            )
            typer.echo(
                f"- {entry.tranche_id}: axis={entry.discriminator_axis}, "
                f"gain={entry.discriminator_gain:.3f}, "
                f"stop={entry.stop_reason.value if entry.stop_reason is not None else 'n/a'}, "
                f"rejected={rejected}"
            )


@app.command("tranche-summary")
def tranche_summary(
    sweep_run_dir: Path = typer.Argument(..., help="Sweep run directory."),
    tranche: str = typer.Option(..., help="Tranche ID to inspect."),
) -> None:
    """Print the summary for one tranche inside a sweep run."""

    try:
        summary = load_tranche_summary(sweep_run_dir, tranche)
    except (MMMStudioError, FileNotFoundError, ValueError) as exc:
        _fail_with_message(str(exc))

    typer.echo("MMM STUDIO TRANCHE SUMMARY")
    typer.echo("==========================")
    typer.echo(f"Tranche: {summary.tranche_id}")
    typer.echo(f"Objective: {summary.objective}")
    typer.echo(f"Successful slices: {summary.successful_slices}")
    typer.echo(f"Failed slices: {summary.failed_slices}")
    typer.echo(f"Pruned slices: {summary.pruned_slices}")
    typer.echo(f"Winner consistency: {summary.winner_consistency.winner_consistency_ratio:.3f}")
    typer.echo(
        f"Null-model availability: {summary.null_model_summary.available_slices}/"
        f"{summary.null_model_summary.requested_slices}"
    )
    if summary.adjudication is not None:
        typer.echo(f"Governance: {summary.adjudication.recommendation.value}")
        typer.echo(
            "Promotion block: "
            f"{summary.adjudication.promotion_block_reason or 'none'}"
        )
        typer.echo(
            "Discriminator stop: "
            f"{summary.adjudication.discriminator_stop_reason.value if summary.adjudication.discriminator_stop_reason is not None else 'n/a'}"
        )
    if summary.legacy_contract_downgrade:
        typer.echo(
            "Downgrade notes: "
            f"{'; '.join(summary.legacy_contract_notes)}"
        )
    typer.echo("")
    typer.echo("Slice winners")
    typer.echo("-------------")
    for winner in summary.slice_winners:
        typer.echo(
            f"- {winner.slice_id}: {winner.candidate_id or 'n/a'} "
            f"(profile={winner.scoring_profile}, status={winner.status.value})"
        )
    if summary.adjudication is not None and summary.adjudication.weakest_unresolved_edges:
        typer.echo("")
        typer.echo("Weakest unresolved edges")
        typer.echo("-----------------------")
        for edge in summary.adjudication.weakest_unresolved_edges[:5]:
            typer.echo(
                f"- {edge.left_slice_id} vs {edge.right_slice_id}: "
                f"margin={edge.equivalence_margin:.3f}, "
                f"tested_axes={','.join(edge.tested_axes) if edge.tested_axes else 'n/a'}"
            )
    if summary.adjudication is not None and summary.adjudication.discriminator_history:
        typer.echo("")
        typer.echo("Discriminator history")
        typer.echo("---------------------")
        for entry in summary.adjudication.discriminator_history[:5]:
            rejected = (
                "; ".join(
                    f"{item.axis_key}:{item.reason}"
                    for item in entry.rejected_axis_rationale
                )
                if entry.rejected_axis_rationale
                else "none"
            )
            typer.echo(
                f"- {entry.tranche_id}: axis={entry.discriminator_axis}, "
                f"gain={entry.discriminator_gain:.3f}, "
                f"rejected={rejected}"
            )


@app.command("compare-slices")
def compare_slices(
    sweep_run_dir: Path = typer.Argument(..., help="Sweep run directory."),
    tranche: str = typer.Option(..., help="Tranche ID to compare within."),
) -> None:
    """Print pairwise slice overlap and divergence for one tranche."""

    try:
        summary = load_tranche_summary(sweep_run_dir, tranche)
    except (MMMStudioError, FileNotFoundError, ValueError) as exc:
        _fail_with_message(str(exc))

    typer.echo("MMM STUDIO SLICE COMPARISON")
    typer.echo("===========================")
    typer.echo(f"Tranche: {summary.tranche_id}")
    for comparison in summary.overlap_matrix:
        typer.echo(
            f"- {comparison.left_slice_id} vs {comparison.right_slice_id}: "
            f"overlap={comparison.overlap_count}, "
            f"jaccard={comparison.jaccard_index:.3f}, "
            f"same_winner={'yes' if comparison.same_winner else 'no'}"
        )


if __name__ == "__main__":
    app()
