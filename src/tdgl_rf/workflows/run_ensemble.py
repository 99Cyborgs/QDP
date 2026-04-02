"""Phase-gated ensemble workflow."""

from __future__ import annotations

from tdgl_rf.exceptions import InferenceError


def run_ensemble(*_args, **_kwargs):
    """Fail explicitly until the stochastic ensemble phase is implemented."""

    raise InferenceError("run_ensemble is reserved for the stochastic phase and is not enabled in phase 1")

