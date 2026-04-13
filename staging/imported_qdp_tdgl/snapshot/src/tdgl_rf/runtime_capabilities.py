"""Centralized runtime capability policy for deterministic and stochastic execution."""

from __future__ import annotations

from dataclasses import dataclass

from tdgl_rf.exceptions import RuntimeCapabilityError

PHASE2_4A_STOCHASTIC_RUNTIME_DENIAL_MESSAGE = (
    "runtime capability denied: stochastic TDGL noise support is not implemented and "
    "ensemble execution support is not implemented; Phase-2.4A stochastic runtime support remains gated"
)

STOCHASTIC_CONFIG_VALIDATION_DENIAL_MESSAGE = (
    "runtime capability denied: stochastic TDGL noise support is not implemented; "
    "set noise.enabled=false"
)


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Explicit runtime capability surface for control-plane dispatch and validation."""

    supports_deterministic_seeded_vortex_experiments: bool
    supports_stochastic_tdgl_noise: bool
    supports_ensemble_execution: bool


_RUNTIME_CAPABILITIES = RuntimeCapabilities(
    supports_deterministic_seeded_vortex_experiments=True,
    supports_stochastic_tdgl_noise=True,
    supports_ensemble_execution=True,
)


def get_runtime_capabilities() -> RuntimeCapabilities:
    """Return the single audited runtime capability policy."""

    return _RUNTIME_CAPABILITIES


def require_noise_runtime_support(*, enabled: bool) -> None:
    """Fail closed when a case config requests unsupported stochastic noise."""

    capabilities = get_runtime_capabilities()
    if enabled and not capabilities.supports_stochastic_tdgl_noise:
        raise RuntimeCapabilityError(STOCHASTIC_CONFIG_VALIDATION_DENIAL_MESSAGE)


def require_phase2_4a_stochastic_runtime(*, context: str) -> None:
    """Fail closed when a Phase-2.4A workflow reaches the execution boundary."""

    capabilities = get_runtime_capabilities()
    if capabilities.supports_stochastic_tdgl_noise and capabilities.supports_ensemble_execution:
        return
    raise RuntimeCapabilityError(f"{context}: {PHASE2_4A_STOCHASTIC_RUNTIME_DENIAL_MESSAGE}")
