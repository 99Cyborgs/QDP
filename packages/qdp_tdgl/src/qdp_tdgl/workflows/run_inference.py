"""Phase-gated inference workflow."""

from __future__ import annotations

from qdp_tdgl.exceptions import InferenceError


def run_inference(*_args, **_kwargs):
    """Fail explicitly until the inference phase is implemented."""

    raise InferenceError("run_inference is reserved for the inference phase and is not enabled in phase 1")


