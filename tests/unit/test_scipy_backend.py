from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse

from tdgl_rf.exceptions import SolverDivergenceError
from tdgl_rf.solvers.scipy_backend import SciPyLinearBackend


def test_scipy_backend_rejects_nonfinite_rhs() -> None:
    backend = SciPyLinearBackend()
    matrix = sparse.identity(2, format="csr")
    rhs = np.array([1.0, np.nan])

    with pytest.raises(SolverDivergenceError, match="right-hand side contains NaN or inf"):
        backend.solve(matrix, rhs, method="cg", rtol=1.0e-8, atol=1.0e-12, max_it=20)


def test_scipy_backend_falls_back_to_sparse_direct_solve_on_iterative_failure() -> None:
    backend = SciPyLinearBackend()
    matrix = sparse.diags([2.0, 3.0, 4.0], format="csr")
    rhs = np.array([2.0, 3.0, 8.0])

    result = backend.solve(matrix, rhs, method="cg", rtol=1.0e-14, atol=1.0e-16, max_it=1, cache_key="phi")

    assert result.converged is True
    assert result.method == "cg+splu"
    np.testing.assert_allclose(result.solution, np.array([1.0, 1.0, 2.0]))
    assert "phi" in backend._direct_factor_cache


def test_scipy_backend_reuses_cached_direct_factorization() -> None:
    backend = SciPyLinearBackend()
    matrix = sparse.diags([5.0, 7.0], format="csr")

    first = backend.solve(matrix, np.array([5.0, 14.0]), method="spsolve", rtol=1.0e-8, atol=1.0e-12, max_it=5, cache_key="phi")
    second = backend.solve(matrix, np.array([10.0, 21.0]), method="spsolve", rtol=1.0e-8, atol=1.0e-12, max_it=5, cache_key="phi")

    assert first.method == "spsolve"
    assert second.method == "spsolve"
    assert len(backend._direct_factor_cache) == 1
    np.testing.assert_allclose(first.solution, np.array([1.0, 2.0]))
    np.testing.assert_allclose(second.solution, np.array([2.0, 3.0]))


def test_scipy_backend_switches_cached_key_to_direct_after_first_iterative_fallback() -> None:
    backend = SciPyLinearBackend()
    matrix = sparse.diags([2.0, 3.0, 4.0], format="csr")
    rhs = np.array([2.0, 3.0, 8.0])

    first = backend.solve(matrix, rhs, method="cg", rtol=1.0e-14, atol=1.0e-16, max_it=1, cache_key="phi")
    second = backend.solve(matrix, rhs, method="cg", rtol=1.0e-14, atol=1.0e-16, max_it=1, cache_key="phi")

    assert first.method == "cg+splu"
    assert second.method == "cg+splu_cached"
    np.testing.assert_allclose(first.solution, second.solution)
