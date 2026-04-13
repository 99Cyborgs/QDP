"""Optional PETSc backend shim."""

from __future__ import annotations

from tdgl_rf.exceptions import SolverDivergenceError


class PETScLinearBackend:
    """Thin wrapper that fails explicitly when petsc4py is unavailable."""

    def __init__(self) -> None:
        try:
            import petsc4py  # noqa: F401
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise SolverDivergenceError("petsc backend requested but petsc4py is not installed") from exc

    def solve(self, *args, **kwargs):  # pragma: no cover - optional dependency path
        raise SolverDivergenceError("petsc backend is reserved for a later milestone in this repository")

