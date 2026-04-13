"""Convergence workflow entry point."""

from __future__ import annotations

from qdp_tdgl.exceptions import InferenceError


def run_convergence(*_args, **_kwargs):
    """Fail explicitly until the deterministic V&V phase is implemented."""

    raise InferenceError("convergence workflows are reserved for deterministic V&V after phase 1")


