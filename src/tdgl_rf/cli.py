"""Command-line interface for TDGL-RF workflows."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator
import typer
import yaml

from tdgl_rf.config.loaders import load_case_config, repo_root
from tdgl_rf.exceptions import ManifestDispatchError, ManifestValidationError, TDGLRFError
from tdgl_rf.workflows.convergence import run_convergence
from tdgl_rf.workflows.evidence import build_evidence_bundle
from tdgl_rf.workflows.experiment_sweep import (
    run_seeded_vortex_experiment_pack,
)
from tdgl_rf.workflows.postprocess import summarize_campaign
from tdgl_rf.workflows.refinement import run_refinement_sanity
from tdgl_rf.workflows.run_case import run_simulation
from tdgl_rf.workflows.run_ensemble import run_ensemble
from tdgl_rf.workflows.run_inference import run_inference
from tdgl_rf.workflows.run_matrix import run_experiment_matrix
from tdgl_rf.workflows.validation import (
    run_phase1_validation,
    run_reference_check,
    run_reproducibility_check,
    run_seeded_vortex_validation,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _fail(exc: Exception) -> None:
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=1) from exc


ExperimentManifestKind = Literal["phase2_2_suite", "phase2_3_deterministic", "phase2_4a_ensemble"]


def _read_manifest_payload(manifest_path: Path) -> dict[str, Any]:
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except FileNotFoundError as exc:
        raise ManifestValidationError(f"manifest does not exist: {manifest_path}") from exc
    except yaml.YAMLError as exc:
        raise ManifestValidationError(f"invalid YAML manifest at {manifest_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ManifestValidationError(f"expected mapping at top level of {manifest_path}")
    return payload


def _schema_error_location(parts: list[Any]) -> str:
    return ".".join(str(part) for part in parts) or "<root>"


def _schema_validation_error(payload: dict[str, Any], schema_path: Path) -> str | None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    if not errors:
        return None
    first = errors[0]
    return f"{_schema_error_location(list(first.absolute_path))}: {first.message}"


def classify_experiment_manifest(manifest_path: Path) -> ExperimentManifestKind:
    """Classify a run-experiment manifest by explicit schema contract with exact-one-match semantics."""

    resolved_path = manifest_path.resolve()
    payload = _read_manifest_payload(resolved_path)
    schema_root = repo_root() / "configs"
    validation_errors = {
        "phase2_2_suite": _schema_validation_error(
            payload,
            schema_root / "seeded_vortex_experiment_manifest.schema.json",
        ),
        "phase2_3_deterministic": _schema_validation_error(
            payload,
            schema_root / "seeded_vortex_experiment_pack.schema.json",
        ),
        "phase2_4a_ensemble": _schema_validation_error(
            payload,
            schema_root / "seeded_vortex_experiment_pack_v4.schema.json",
        ),
    }
    matches = [kind for kind, error in validation_errors.items() if error is None]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ManifestDispatchError(
            f"manifest dispatch is ambiguous for {resolved_path}: matched {', '.join(sorted(matches))}"
        )

    experiment_pack = payload.get("experiment_pack")
    declared_mode = experiment_pack.get("mode") if isinstance(experiment_pack, dict) else None
    schema_version = str(payload.get("schema_version", "")).strip()
    if declared_mode == "deterministic_sweep" or schema_version.startswith("3."):
        raise ManifestValidationError(
            "Phase-2.3 deterministic experiment-pack validation failed: "
            + str(validation_errors["phase2_3_deterministic"])
        )
    if declared_mode == "stochastic_ensemble" or schema_version.startswith("4."):
        raise ManifestValidationError(
            "Phase-2.4A ensemble experiment-pack validation failed: "
            + str(validation_errors["phase2_4a_ensemble"])
        )
    if payload.get("suite_id") is not None or schema_version == "tdgl_rf.seeded_vortex_experiment_pack.v1":
        raise ManifestValidationError(
            "Phase-2.2 suite manifest validation failed: " + str(validation_errors["phase2_2_suite"])
        )

    raise ManifestDispatchError(
        "manifest did not match any explicit Phase-2.2, Phase-2.3, or Phase-2.4A contract"
    )


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
    """Execute a stochastic ensemble from one case config."""

    try:
        summary = run_ensemble(config_path)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))


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


@app.command("evidence-bundle")
def evidence_bundle(validation_dir: Path, output_dir: Path | None = typer.Option(None, "--output-dir")) -> None:
    """Package a completed phase-1 validation run into a compact evidence bundle."""

    try:
        summary = build_evidence_bundle(validation_dir, output_dir=output_dir)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))


@app.command("reference-check")
def reference_check(manifest_path: Path, output_dir: Path | None = typer.Option(None, "--output-dir")) -> None:
    """Regenerate and compare the frozen reference-output set."""

    try:
        summary = run_reference_check(manifest_path, output_dir=output_dir)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))
    if summary.status != "success":
        raise typer.Exit(code=1)


@app.command("validate-seeded-vortices")
def validate_seeded_vortices(manifest_path: Path, output_dir: Path | None = typer.Option(None, "--output-dir")) -> None:
    """Run the seeded initialization / short-horizon experiment-pack validation suite."""

    try:
        summary = run_seeded_vortex_validation(manifest_path, output_dir=output_dir)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))
    if summary.status != "success":
        raise typer.Exit(code=1)


@app.command("run-experiment")
def run_experiment(manifest_path: Path, output_dir: Path | None = typer.Option(None, "--output-dir")) -> None:
    """Dispatch explicit Phase-2.2, Phase-2.3 deterministic, or Phase-2.4A ensemble manifests."""

    try:
        manifest_kind = classify_experiment_manifest(manifest_path)
        if manifest_kind == "phase2_2_suite":
            summary = run_seeded_vortex_validation(manifest_path, output_dir=output_dir)
        else:
            summary = run_seeded_vortex_experiment_pack(manifest_path, output_dir=output_dir)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))
    if summary.status != "success":
        raise typer.Exit(code=1)


@app.command("reproducibility-check")
def reproducibility_check(
    config_path: Path,
    thresholds_path: Path,
    output_dir: Path | None = typer.Option(None, "--output-dir"),
) -> None:
    """Run the cheap deterministic same-case-twice reproducibility check."""

    try:
        summary = run_reproducibility_check(config_path, tolerances_path=thresholds_path, output_dir=output_dir)
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))
    if summary.status != "success":
        raise typer.Exit(code=1)


@app.command("validate-phase1")
def validate_phase1(
    matrix_path: Path,
    thresholds_path: Path,
    reference_manifest_path: Path,
    refinement_config_path: Path,
    output_dir: Path | None = typer.Option(None, "--output-dir"),
) -> None:
    """Run the deterministic phase-1 validation tranche and write evidence artifacts."""

    try:
        summary = run_phase1_validation(
            matrix_path,
            thresholds_path=thresholds_path,
            reference_manifest_path=reference_manifest_path,
            refinement_config_path=refinement_config_path,
            output_dir=output_dir,
        )
    except Exception as exc:
        _fail(exc)
        return
    typer.echo(json.dumps(asdict(summary), indent=2))
    if summary.status != "success":
        raise typer.Exit(code=1)


@app.command("summarize")
def summarize(run_dir: Path) -> None:
    """Print the stored status summary for a run directory."""

    status_path = run_dir / "status.json"
    if not status_path.exists():
        _fail(TDGLRFError(f"missing status file: {status_path}"))
        return
    typer.echo(status_path.read_text(encoding="utf-8"))
