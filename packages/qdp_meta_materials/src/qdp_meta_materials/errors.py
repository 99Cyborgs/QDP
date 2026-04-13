from __future__ import annotations

from pathlib import Path


class QDPMetaMaterialsError(Exception):
    """Base exception for the extracted QDP metamaterials core."""


MMMStudioError = QDPMetaMaterialsError


class DatasetLoadError(QDPMetaMaterialsError):
    """Raised when a seed dataset cannot be loaded or validated."""

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"{path}: {detail}")


class RepositoryValidationError(QDPMetaMaterialsError):
    """Raised when repository validation detects non-recoverable errors."""


class OptionalDependencyUnavailable(QDPMetaMaterialsError):
    """Raised when an optional integration backend is requested but unavailable."""


class SweepPlanningError(QDPMetaMaterialsError):
    """Raised when a sweep specification cannot be normalized into an executable plan."""


class SweepExecutionError(QDPMetaMaterialsError):
    """Raised when sweep execution fails before a coherent manifest can be produced."""
