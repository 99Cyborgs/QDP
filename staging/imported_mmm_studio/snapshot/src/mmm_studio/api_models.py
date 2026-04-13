from __future__ import annotations

from pydantic import Field

from .models import MMMBaseModel, RegistrySummary, RunManifest, ScoreResult
from .sweeps.models import SweepManifest, SweepSpec, SweepSummary, TrancheSummary


class HealthResponse(MMMBaseModel):
    status: str = "ok"
    service: str = "MMM Studio API"
    version: str


class RegistryValidationRequest(MMMBaseModel):
    root: str | None = None


class SummaryResponse(MMMBaseModel):
    registry: RegistrySummary
    scoring_profile: str
    top_candidates: list[ScoreResult]


class ScoringRequest(MMMBaseModel):
    root: str | None = None
    profile: str = "broadband"
    top_n: int = Field(default=10, ge=1, le=100)
    screening_status: str | None = None


class ScoringResponse(MMMBaseModel):
    profile: str
    score_backend: str
    candidate_count: int
    results: list[ScoreResult]


class RunSummaryResponse(MMMBaseModel):
    manifest: RunManifest


class SweepValidationRequest(MMMBaseModel):
    root: str | None = None
    spec: SweepSpec


class SweepPlanRequest(SweepValidationRequest):
    output_dir: str | None = None


class SweepRunRequest(SweepPlanRequest):
    pass


class SweepValidationResponse(MMMBaseModel):
    manifest: SweepManifest


class SweepPlanResponse(MMMBaseModel):
    manifest: SweepManifest


class SweepRunResponse(MMMBaseModel):
    manifest: SweepManifest
    summary: SweepSummary


class SweepSummaryResponse(MMMBaseModel):
    summary: SweepSummary


class TrancheSummaryResponse(MMMBaseModel):
    summary: TrancheSummary
