"""SciPy sparse linear solver backend."""

from __future__ import annotations

from dataclasses import dataclass
import warnings
from typing import Protocol

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import MatrixRankWarning, bicgstab, cg, gmres, minres, splu

from tdgl_rf.exceptions import SolverDivergenceError


@dataclass(frozen=True)
class LinearSolveResult:
    solution: np.ndarray
    iterations: int
    residual_norm: float
    converged: bool
    method: str


class LinearSolverBackend(Protocol):
    """Common protocol for linear solver backends."""

    def solve(
        self,
        matrix,
        rhs: np.ndarray,
        method: str,
        rtol: float,
        atol: float,
        max_it: int,
        cache_key: str | int | None = None,
    ) -> LinearSolveResult:
        """Solve a linear system and return solver diagnostics."""


class SciPyLinearBackend:
    """Sparse linear solver wrapper with iteration statistics.

    Iterative methods remain the first choice so solver diagnostics reflect the requested method,
    but repeated sparse failures are upgraded to cached direct factorizations to fail closed
    without re-incurring decomposition cost on later steps.
    """

    _ITERATIVE_SOLVERS = {
        "cg": cg,
        "gmres": gmres,
        "bicgstab": bicgstab,
        "minres": minres,
    }

    def __init__(self) -> None:
        self._direct_factor_cache: dict[str | int, object] = {}
        self._prefer_direct_cache_keys: set[str | int] = set()

    @staticmethod
    def _normalize_matrix(matrix):
        normalized = matrix.tocsr() if sparse.issparse(matrix) else np.asarray(matrix)
        if normalized.ndim != 2:
            raise SolverDivergenceError("linear solve requires a two-dimensional matrix")
        rows, cols = normalized.shape
        if rows != cols:
            raise SolverDivergenceError(f"linear solve requires a square matrix; got shape {(rows, cols)}")
        data = normalized.data if sparse.issparse(normalized) else normalized
        if not np.isfinite(data).all():
            raise SolverDivergenceError("linear system matrix contains NaN or inf entries")
        return normalized

    @staticmethod
    def _normalize_rhs(rhs: np.ndarray, size: int) -> np.ndarray:
        normalized = np.asarray(rhs)
        if normalized.ndim != 1:
            raise SolverDivergenceError("linear solve requires a one-dimensional right-hand side")
        if normalized.shape[0] != size:
            raise SolverDivergenceError(
                f"right-hand side length {normalized.shape[0]} does not match matrix size {size}"
            )
        if not np.isfinite(normalized).all():
            raise SolverDivergenceError("linear right-hand side contains NaN or inf entries")
        return normalized

    @staticmethod
    def _build_result(solution, residual, iterations: int, method: str) -> LinearSolveResult:
        solution_array = np.asarray(solution)
        if not np.isfinite(solution_array).all():
            raise SolverDivergenceError(f"{method} produced NaN or inf values in the solution")
        residual_array = np.asarray(residual)
        if not np.isfinite(residual_array).all():
            raise SolverDivergenceError(f"{method} produced NaN or inf values in the residual")
        return LinearSolveResult(
            solution=solution_array,
            iterations=iterations,
            residual_norm=float(np.linalg.norm(residual_array)),
            converged=True,
            method=method,
        )

    @staticmethod
    def _validate_direct_residual(method: str, residual, rhs: np.ndarray, rtol: float, atol: float) -> None:
        residual_norm = float(np.linalg.norm(np.asarray(residual)))
        tolerance = float(atol + rtol * np.linalg.norm(rhs))
        if residual_norm > tolerance:
            raise SolverDivergenceError(
                f"direct solve residual {residual_norm:.3e} exceeds tolerance {tolerance:.3e} for {method}"
            )

    def _solve_direct(
        self,
        matrix,
        rhs: np.ndarray,
        method: str,
        rtol: float,
        atol: float,
        cache_key: str | int | None = None,
    ) -> LinearSolveResult:
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            if sparse.issparse(matrix):
                if cache_key is not None and cache_key in self._direct_factor_cache:
                    solution = self._direct_factor_cache[cache_key].solve(rhs)
                else:
                    lu = splu(matrix.tocsc())
                    if cache_key is not None:
                        self._direct_factor_cache[cache_key] = lu
                    solution = lu.solve(rhs)
            else:
                solution = np.linalg.solve(matrix, rhs)
        residual = matrix @ solution - rhs
        self._validate_direct_residual(method, residual, rhs, rtol=rtol, atol=atol)
        return self._build_result(solution, residual, iterations=1, method=method)

    def clear_cached_factor(self, cache_key: str | int) -> None:
        """Drop a cached direct factorization when it is no longer reusable."""

        self._direct_factor_cache.pop(cache_key, None)
        self._prefer_direct_cache_keys.discard(cache_key)

    def solve(
        self,
        matrix,
        rhs: np.ndarray,
        method: str,
        rtol: float,
        atol: float,
        max_it: int,
        cache_key: str | int | None = None,
    ) -> LinearSolveResult:
        matrix = self._normalize_matrix(matrix)
        rhs = self._normalize_rhs(rhs, matrix.shape[0])
        method_key = method.lower()
        if method_key == "spsolve":
            return self._solve_direct(matrix, rhs, method_key, rtol=rtol, atol=atol, cache_key=cache_key)
        if cache_key is not None and cache_key in self._prefer_direct_cache_keys:
            # Once an iterative solve has failed for a reusable operator, subsequent solves stay on
            # the direct path so the runtime does not oscillate between methods across timesteps.
            return self._solve_direct(
                matrix,
                rhs,
                f"{method_key}+splu_cached",
                rtol=rtol,
                atol=atol,
                cache_key=cache_key,
            )

        if method_key not in self._ITERATIVE_SOLVERS:
            raise SolverDivergenceError(f"unsupported SciPy linear solver '{method}'")

        iterations = 0

        def _callback(_arg) -> None:
            nonlocal iterations
            iterations += 1

        solver = self._ITERATIVE_SOLVERS[method_key]
        kwargs = {"rtol": rtol, "atol": atol, "maxiter": max_it, "callback": _callback}
        if method_key == "gmres":
            kwargs["callback_type"] = "pr_norm"
        if method_key == "minres":
            kwargs.pop("atol")
        solution, info = solver(matrix, rhs, **kwargs)
        residual = matrix @ solution - rhs
        converged = info == 0
        if not converged:
            if sparse.issparse(matrix):
                # Sparse iterative failures degrade to LU instead of surfacing partial solutions;
                # dense failures are rare enough that fail-fast remains clearer than retry logic.
                if cache_key is not None:
                    self._prefer_direct_cache_keys.add(cache_key)
                return self._solve_direct(
                    matrix,
                    rhs,
                    f"{method_key}+splu",
                    rtol=rtol,
                    atol=atol,
                    cache_key=cache_key,
                )
            raise SolverDivergenceError(f"{method_key} failed to converge; info={info}")
        return self._build_result(solution, residual, iterations=max(iterations, 1), method=method_key)
