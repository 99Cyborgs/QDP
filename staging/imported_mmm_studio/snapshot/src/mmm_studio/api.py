from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException

from . import __version__
from .api_models import (
    HealthResponse,
    RegistryValidationRequest,
    RunSummaryResponse,
    ScoringRequest,
    ScoringResponse,
    SummaryResponse,
    SweepPlanRequest,
    SweepPlanResponse,
    SweepRunRequest,
    SweepRunResponse,
    SweepSummaryResponse,
    SweepValidationRequest,
    SweepValidationResponse,
    TrancheSummaryResponse,
)
from .config import default_seed_root
from .errors import MMMStudioError
from .io import load_dataset, write_json
from .models import MMMDataset, ScoreResult, ValidationReport
from .runs import default_run_directory, load_run_manifest
from .scoring import DEFAULT_SCORING_PROFILE, rank_dataset
from .sweeps import (
    default_sweep_directory,
    execute_sweep,
    load_sweep_summary,
    load_tranche_summary,
    plan_sweep,
)
from .validation import validate_repository

app = FastAPI(title="MMM Studio API", version=__version__)


@lru_cache(maxsize=8)
def _dataset(root: str) -> MMMDataset:
    return load_dataset(root)


def _resolve_root(root: str | None) -> str:
    return str(Path(root).resolve()) if root else str(default_seed_root())


def _latest_manifest_path() -> Path:
    manifests = sorted(default_run_directory().glob("*/run_manifest.json"))
    if not manifests:
        raise HTTPException(status_code=404, detail="No persisted run manifests found.")
    return manifests[-1]


def _sweep_root(sweep_id: str) -> Path:
    path = default_sweep_directory() / sweep_id
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Sweep '{sweep_id}' was not found.")
    return path


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=__version__)


@app.get("/summary", response_model=SummaryResponse)
def summary(root: str | None = None, profile: str = DEFAULT_SCORING_PROFILE) -> SummaryResponse:
    dataset = _dataset(_resolve_root(root))
    results = rank_dataset(dataset, profile=profile)[:5]
    return SummaryResponse(
        registry=dataset.to_summary(),
        scoring_profile=profile,
        top_candidates=results,
    )


@app.post("/registry/validate", response_model=ValidationReport)
def validation(request: RegistryValidationRequest) -> ValidationReport:
    return validate_repository(_resolve_root(request.root))


@app.post("/scoring/score", response_model=ScoringResponse)
def scoring(request: ScoringRequest) -> ScoringResponse:
    dataset = _dataset(_resolve_root(request.root))
    results = rank_dataset(
        dataset,
        profile=request.profile,
        screening_status=request.screening_status,
    )
    return ScoringResponse(
        profile=request.profile,
        score_backend=results[0].score_backend if results else "baseline_surrogate_v1",
        candidate_count=len(results),
        results=results[: request.top_n],
    )


@app.get("/runs/summary", response_model=RunSummaryResponse)
def run_summary(run_dir: str | None = None) -> RunSummaryResponse:
    manifest = load_run_manifest(run_dir or _latest_manifest_path())
    return RunSummaryResponse(manifest=manifest)


@app.get("/leaderboard", response_model=list[ScoreResult])
def leaderboard(
    top_n: int = 10,
    screening_status: str | None = None,
    profile: str = DEFAULT_SCORING_PROFILE,
    root: str | None = None,
) -> list:
    dataset = _dataset(_resolve_root(root))
    return rank_dataset(dataset, profile=profile, screening_status=screening_status)[:top_n]


@app.get("/candidate/{genome_id}", response_model=ScoreResult)
def candidate(
    genome_id: str,
    profile: str = DEFAULT_SCORING_PROFILE,
    root: str | None = None,
) -> ScoreResult:
    dataset = _dataset(_resolve_root(root))
    for result in rank_dataset(dataset, profile=profile):
        if result.genome_id == genome_id:
            return result
    raise HTTPException(status_code=404, detail=f"Unknown genome_id: {genome_id}")


@app.post("/sweeps/validate", response_model=SweepValidationResponse)
def sweep_validation(request: SweepValidationRequest) -> SweepValidationResponse:
    try:
        manifest = plan_sweep(
            request.spec,
            dataset_root=_resolve_root(request.root),
            command="api:/sweeps/validate",
        )
    except (MMMStudioError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SweepValidationResponse(manifest=manifest)


@app.post("/sweeps/plan", response_model=SweepPlanResponse)
def sweep_plan(request: SweepPlanRequest) -> SweepPlanResponse:
    try:
        manifest = plan_sweep(
            request.spec,
            dataset_root=_resolve_root(request.root),
            output_dir=request.output_dir,
            command="api:/sweeps/plan",
        )
        if request.output_dir is not None:
            write_json(
                Path(request.output_dir) / "sweep_manifest.json",
                manifest.model_dump(mode="json"),
            )
    except (MMMStudioError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SweepPlanResponse(manifest=manifest)


@app.post("/sweeps/run", response_model=SweepRunResponse)
def sweep_run(request: SweepRunRequest) -> SweepRunResponse:
    try:
        manifest, summary = execute_sweep(
            request.spec,
            dataset_root=_resolve_root(request.root),
            output_dir=request.output_dir,
            command="api:/sweeps/run",
        )
    except (MMMStudioError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SweepRunResponse(manifest=manifest, summary=summary)


@app.get("/sweeps/{sweep_id}/summary", response_model=SweepSummaryResponse)
def get_sweep_summary(sweep_id: str) -> SweepSummaryResponse:
    root = _sweep_root(sweep_id)
    return SweepSummaryResponse(summary=load_sweep_summary(root))


@app.get("/sweeps/{sweep_id}/tranches/{tranche_id}", response_model=TrancheSummaryResponse)
def get_tranche_summary(sweep_id: str, tranche_id: str) -> TrancheSummaryResponse:
    root = _sweep_root(sweep_id)
    return TrancheSummaryResponse(summary=load_tranche_summary(root, tranche_id))
