"""Command-line interface for TDGL-RF workflows."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import typer

from tdgl_rf.config.loaders import load_case_config
from tdgl_rf.exceptions import TDGLRFError
from tdgl_rf.workflows.convergence import run_convergence
from tdgl_rf.workflows.postprocess import summarize_campaign
from tdgl_rf.workflows.refinement import run_refinement_sanity
from tdgl_rf.workflows.run_case import run_simulation
from tdgl_rf.workflows.run_ensemble import run_ensemble
from tdgl_rf.workflows.run_inference import run_inference
from tdgl_rf.workflows.run_matrix import run_experiment_matrix

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _fail(exc: Exception) -> None:
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=1) from exc


@app.command("validate-config")
def validate_config(config_path: Path) -> None:
    """Validate a YAML config and print the expanded result."""

    try:
        config = load_case_config(config_path)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(config.model_dump(mode="json"), indent=2))


@app.command("run-case")
def run_case(config_path: Path) -> None:
    """Run a deterministic case from config."""

    try:
        summary = run_simulation(config_path)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(summary.__dict__, indent=2))


@app.command("run-matrix")
def run_matrix(
    matrix_path: Path,
    dry_run: bool = typer.Option(False, "--dry-run"),
    selector: list[str] = typer.Option(None, "--selector"),
    resume: Path | None = typer.Option(None, "--resume"),
) -> None:
    """Execute a matrix campaign or expand it in dry-run mode."""

    try:
        summary = run_experiment_matrix(matrix_path, selectors=selector, dry_run=dry_run, resume_dir=resume)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))
    if summary.status not in {"success", "dry_run"}:
        raise typer.Exit(code=1)


@app.command("run-ensemble")
def run_ensemble_cmd(config_path: Path) -> None:
    """Reserved for the stochastic ensemble phase."""

    try:
        run_ensemble(config_path)
    except Exception as exc:
        _fail(exc)


@app.command("run-inference")
def run_inference_cmd(config_path: Path) -> None:
    """Reserved for the inference phase."""

    try:
        run_inference(config_path)
    except Exception as exc:
        _fail(exc)


@app.command("verify")
def verify(_benchmark_id: str) -> None:
    """Reserved for the benchmark verification phase."""

    _fail(TDGLRFError("verify is reserved for the deterministic V&V phase"))


@app.command("convergence")
def convergence(config_path: Path) -> None:
    """Reserved for deterministic V&V convergence studies."""

    try:
        run_convergence(config_path)
    except Exception as exc:
        _fail(exc)


@app.command("refinement-sanity")
def refinement_sanity(config_path: Path, output_dir: Path | None = typer.Option(None, "--output-dir")) -> None:
    """Run a cheap mesh/dt refinement sanity sweep for one deterministic case."""

    try:
        summary = run_refinement_sanity(config_path, output_dir=output_dir)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))


@app.command("summarize-campaign")
def summarize_campaign_cmd(campaign_dir: Path, output_dir: Path | None = typer.Option(None, "--output-dir")) -> None:
    """Aggregate one matrix campaign into compact CSV and Markdown artifacts."""

    try:
        summary = summarize_campaign(campaign_dir, output_dir=output_dir)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))


@app.command("summarize")
def summarize(run_dir: Path) -> None:
    """Print the stored status summary for a run directory."""

    status_path = run_dir / "status.json"
    if not status_path.exists():
        _fail(TDGLRFError(f"missing status file: {status_path}"))
        return
    typer.echo(status_path.read_text(encoding="utf-8"))
