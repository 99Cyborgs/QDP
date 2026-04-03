"""Frozen nondimensional unit metadata."""

from __future__ import annotations


NONDIMENSIONAL_UNITS = {
    "length": "xi",
    "time": "tau_GL",
    "vector_potential": "Phi0 / (2 pi xi)",
    "scalar_potential": "hbar / (2 e tau_GL)",
    "order_parameter": "psi0",
}
