"""TDGL-RF package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from tdgl_rf.workflows.run_case import run_simulation

try:
    __version__ = version("tdgl-rf")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.0"

__all__ = ["__version__", "run_simulation"]

