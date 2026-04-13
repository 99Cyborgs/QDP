from __future__ import annotations

from pathlib import Path


class MMMStudioError(Exception):
    """Base exception for MMM Studio."""


class DatasetLoadError(MMMStudioError):
    """Raised when a seed dataset cannot be loaded or validated."""

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"{path}: {detail}")


class RepositoryValidationError(MMMStudioError):
    """Raised when repository validation detects non-recoverable errors."""


class OptionalDependencyUnavailable(MMMStudioError):
    """Raised when an optional integration backend is requested but unavailable."""


class SweepPlanningError(MMMStudioError):
    """Raised when a sweep specification cannot be normalized into an executable plan."""


class SweepExecutionError(MMMStudioError):
    """Raised when sweep execution fails before a coherent manifest can be produced."""
