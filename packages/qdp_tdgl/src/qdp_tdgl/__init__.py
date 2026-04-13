"""Canonical QDP TDGL runtime package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from qdp_tdgl.workflows.run_case import run_simulation

for _distribution_name in ("qdp-tdgl", "tdgl-rf"):
    try:
        __version__ = version(_distribution_name)
        break
    except PackageNotFoundError:  # pragma: no cover
        continue
else:  # pragma: no cover
    __version__ = "0.1.0"

__all__ = ["__version__", "run_simulation"]
