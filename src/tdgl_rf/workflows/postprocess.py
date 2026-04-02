"""Postprocessing entry points."""

from __future__ import annotations

from tdgl_rf.exceptions import InferenceError


def summarize_run(*_args, **_kwargs):
    """Fail explicitly until the postprocessing phase is implemented."""

    raise InferenceError("postprocess workflows are reserved for later phases")

