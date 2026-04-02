"""Structured exceptions used by workflows and CLI."""

from __future__ import annotations


class TDGLRFError(RuntimeError):
    """Base exception for TDGL-RF workflow failures."""


class ConfigError(TDGLRFError):
    """Raised when configuration loading or validation fails."""


class GeometryError(TDGLRFError):
    """Raised when geometry construction fails."""


class SolverDivergenceError(TDGLRFError):
    """Raised when a linear solve or time integration step fails."""


class OutputWriteError(TDGLRFError):
    """Raised when output persistence fails."""


class InferenceError(TDGLRFError):
    """Raised when an inference workflow is requested before it exists."""

