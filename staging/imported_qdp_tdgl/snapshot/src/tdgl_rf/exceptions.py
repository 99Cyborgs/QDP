"""Structured exceptions used by workflows and CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TDGLRFError(RuntimeError):
    """Base exception for TDGL-RF workflow failures."""


class ConfigError(TDGLRFError):
    """Raised when configuration loading or validation fails."""


class ManifestValidationError(ConfigError):
    """Raised when an experiment manifest fails schema or contract validation."""


class ManifestDispatchError(TDGLRFError):
    """Raised when manifest routing is ambiguous or unsupported."""


class Tier2ContractError(TDGLRFError):
    """Raised when the committed Tier-2 observable contract is violated."""


class ObservableExtractionError(Tier2ContractError):
    """Raised when Tier-2 observable extraction fails at the committed boundary."""


class SeedRejectionCode(StrEnum):
    """Explicit taxonomy for seeded-vortex rejection paths."""

    MISSING_SEEDS = "missing_seeds"
    UNEXPECTED_SEEDS = "unexpected_seeds"
    SCHEMA_INVALID = "schema_invalid"
    OUTSIDE_DOMAIN = "outside_domain"
    AMBIGUOUS_PLAQUETTE = "ambiguous_plaquette"
    INACTIVE_PLAQUETTE = "inactive_plaquette"
    OVERLAPPING_PLAQUETTE = "overlapping_plaquette"


SEED_REJECTION_TAXONOMY_VERSION = "seeded_vortex_phase2_1"
SEED_REJECTION_PAYLOAD_SCHEMA_VERSION = "tdgl_rf.seeded_vortex_rejection.v1"


@dataclass(frozen=True)
class SeedRejectionError(ConfigError):
    """Structured seeded-vortex config rejection with a stable taxonomy code."""

    code: SeedRejectionCode
    message: str
    seed_index: int | None = None
    field_path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.__str__())

    def __str__(self) -> str:
        prefix = f"[seed_rejection:{self.code}]"
        location = f" {self.field_path}" if self.field_path else ""
        return f"{prefix}{location} {self.message}"

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": SEED_REJECTION_PAYLOAD_SCHEMA_VERSION,
            "taxonomy_version": SEED_REJECTION_TAXONOMY_VERSION,
            "exception_type": type(self).__name__,
            "code": str(self.code),
            "message": self.message,
            "field_path": self.field_path,
            "seed_index": self.seed_index,
        }
        if self.details:
            payload["details"] = dict(self.details)
        return payload


class GeometryError(TDGLRFError):
    """Raised when geometry construction fails."""


class SolverDivergenceError(TDGLRFError):
    """Raised when a linear solve or time integration step fails."""


class OutputWriteError(TDGLRFError):
    """Raised when output persistence fails."""


class AggregationError(TDGLRFError):
    """Raised when experiment aggregation cannot produce a valid summary."""


class OutputDirectoryError(OutputWriteError):
    """Raised when an experiment output directory is invalid for execution."""


class InferenceError(TDGLRFError):
    """Raised when an inference workflow is requested before it exists."""


class RuntimeCapabilityError(ConfigError):
    """Raised when a requested runtime mode is intentionally unavailable."""

