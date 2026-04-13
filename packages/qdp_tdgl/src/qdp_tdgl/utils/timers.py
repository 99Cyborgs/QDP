"""Simple timing helpers."""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter


@contextmanager
def timed():
    """Yield a callable that returns elapsed wall-clock time."""

    start = perf_counter()
    yield lambda: perf_counter() - start


