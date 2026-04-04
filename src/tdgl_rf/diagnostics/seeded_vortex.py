"""Deterministic seeded-vortex Tier-2 diagnostics with explicit claim boundaries."""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

from tdgl_rf.exceptions import ObservableExtractionError, Tier2ContractError
from tdgl_rf.solvers.seeded_vortices import ResolvedVortexSeed, SEED_RESOLUTION_POLICY

SEEDED_VORTEX_TIER2_SCHEMA_VERSION = "tdgl_rf.seeded_vortex_tier2.v2"
SEEDED_VORTEX_DIAGNOSTIC_INTERPRETATION_VERSION = "seeded_vortex_phase2_2"

SEEDED_CASE_CLASS_INITIALIZATION_ONLY = "initialization_only"
SEEDED_CASE_CLASS_SHORT_HORIZON = "short_horizon"

SEEDED_SAMPLING_POLICY_INITIALIZATION_SURFACE = "initialization_surface"
SEEDED_SAMPLING_POLICY_ALL_OBSERVABLE_SAMPLES = "all_observable_samples_through_n_steps"

SUPPORTED_TIER2_OBSERVABLES = (
    "initialization.seed_count",
    "initialization.local_winding.initial_total_signed_winding",
    "initialization.local_winding.initial_total_abs_winding",
    "initialization.local_winding.all_host_winding_match",
    "initialization.local_winding.all_local_winding_match",
    "initialization.core_contrast.all_core_observable",
    "initialization.core_contrast.mean_core_to_ring_ratio",
    "initialization.core_contrast.min_core_to_ring_ratio",
    "initialization.core_contrast.max_core_to_ring_ratio",
    "initialization.overall_pass",
    "early_window.checked_sample_count",
    "early_window.expected_vortex_count",
    "early_window.vortex_count_initial",
    "early_window.vortex_count_final",
    "early_window.vortex_count_min",
    "early_window.vortex_count_max",
    "early_window.mean_abs2_initial",
    "early_window.mean_abs2_final",
    "early_window.mean_abs2_min",
    "early_window.mean_abs2_max",
    "early_window.charge_residual_inf_initial",
    "early_window.charge_residual_inf_final",
    "early_window.charge_residual_inf_min",
    "early_window.charge_residual_inf_max",
    "early_window.finite_observables_pass",
    "early_window.positive_amplitude_pass",
    "early_window.vortex_count_matches_expected_pass",
    "early_window.overall_pass",
)


def infer_seeded_case_class(n_steps: int) -> str:
    """Infer the conservative seeded-vortex case class from the configured horizon."""

    return SEEDED_CASE_CLASS_INITIALIZATION_ONLY if int(n_steps) == 0 else SEEDED_CASE_CLASS_SHORT_HORIZON


def infer_seeded_sampling_policy(n_steps: int) -> str:
    """Infer the seeded-vortex sampling policy from the configured horizon."""

    return (
        SEEDED_SAMPLING_POLICY_INITIALIZATION_SURFACE
        if int(n_steps) == 0
        else SEEDED_SAMPLING_POLICY_ALL_OBSERVABLE_SAMPLES
    )


def _coerce_row_value(row: dict[str, Any], key: str) -> float:
    return float(row[key])


def _local_window(vortex_map: np.ndarray, seed: ResolvedVortexSeed) -> np.ndarray:
    x0 = max(seed.plaquette_x - 1, 0)
    x1 = min(seed.plaquette_x + 2, vortex_map.shape[0])
    y0 = max(seed.plaquette_y - 1, 0)
    y1 = min(seed.plaquette_y + 2, vortex_map.shape[1])
    return vortex_map[x0:x1, y0:y1]


def _ring_values(abs_psi: np.ndarray, seed: ResolvedVortexSeed) -> np.ndarray:
    x0 = max(seed.plaquette_x - 1, 0)
    x1 = min(seed.plaquette_x + 3, abs_psi.shape[0])
    y0 = max(seed.plaquette_y - 1, 0)
    y1 = min(seed.plaquette_y + 3, abs_psi.shape[1])
    window = abs_psi[x0:x1, y0:y1]
    mask = np.ones_like(window, dtype=bool)
    mask[(seed.plaquette_x - x0) : (seed.plaquette_x - x0 + 2), (seed.plaquette_y - y0) : (seed.plaquette_y - y0 + 2)] = False
    return window[mask]


def _local_winding_payload(vortex_map: np.ndarray, seed: ResolvedVortexSeed, *, seed_index: int) -> dict[str, Any]:
    local = _local_window(vortex_map, seed)
    host_winding = int(vortex_map[seed.plaquette_x, seed.plaquette_y])
    local_signed_winding = int(np.sum(local))
    local_abs_winding = int(np.sum(np.abs(local)))
    return {
        "seed_index": seed_index,
        "configured_winding": int(seed.winding),
        "plaquette_x": int(seed.plaquette_x),
        "plaquette_y": int(seed.plaquette_y),
        "host_winding": host_winding,
        "local_signed_winding": local_signed_winding,
        "local_abs_winding": local_abs_winding,
        "host_winding_match": host_winding == int(seed.winding),
        "local_winding_match": local_signed_winding == int(seed.winding) and local_abs_winding == abs(int(seed.winding)),
    }


def _core_contrast_payload(psi: np.ndarray, seed: ResolvedVortexSeed, *, seed_index: int) -> dict[str, Any]:
    abs_psi = np.abs(psi)
    core = abs_psi[seed.plaquette_x : seed.plaquette_x + 2, seed.plaquette_y : seed.plaquette_y + 2]
    ring = _ring_values(abs_psi, seed)
    core_min = float(np.min(core))
    core_mean = float(np.mean(core))
    ring_mean = float(np.mean(ring)) if ring.size else core_mean
    core_to_ring_ratio = (core_mean / ring_mean) if ring_mean > 0 else None
    core_observable = bool(ring_mean > 0.0 and core_mean < ring_mean and core_min < ring_mean)
    return {
        "seed_index": seed_index,
        "configured_winding": int(seed.winding),
        "plaquette_x": int(seed.plaquette_x),
        "plaquette_y": int(seed.plaquette_y),
        "core_min_abs": core_min,
        "core_mean_abs": core_mean,
        "ring_mean_abs": ring_mean,
        "core_to_ring_ratio": core_to_ring_ratio,
        "core_observable": core_observable,
    }


def _sample_rows(
    timeseries: Sequence[dict[str, Any]],
    *,
    n_steps: int,
    sampling_policy: str,
) -> list[dict[str, Any]]:
    """Select the observable rows admitted by the current claim boundary."""

    rows = list(timeseries)
    if sampling_policy == SEEDED_SAMPLING_POLICY_INITIALIZATION_SURFACE:
        return rows[:1]
    if sampling_policy == SEEDED_SAMPLING_POLICY_ALL_OBSERVABLE_SAMPLES:
        return [row for row in rows if int(_coerce_row_value(row, "step")) <= int(n_steps)]
    raise ValueError(f"unsupported seeded-vortex sampling policy: {sampling_policy}")


def _early_window_payload(
    timeseries: Sequence[dict[str, Any]],
    expected_vortex_count: int,
    *,
    n_steps: int,
    sampling_policy: str,
) -> dict[str, Any] | None:
    """Summarize short-horizon observables without widening the seeded-vortex contract."""

    rows = _sample_rows(timeseries, n_steps=n_steps, sampling_policy=sampling_policy)
    if sampling_policy == SEEDED_SAMPLING_POLICY_INITIALIZATION_SURFACE:
        return None

    vortex_count_series = [int(_coerce_row_value(row, "vortex_count")) for row in rows]
    mean_abs2_series = [float(_coerce_row_value(row, "mean_abs2")) for row in rows]
    charge_residual_series = [float(_coerce_row_value(row, "charge_residual_inf")) for row in rows]
    steps = [int(_coerce_row_value(row, "step")) for row in rows]
    times = [float(_coerce_row_value(row, "t")) for row in rows]
    finite_observables_pass = all(math.isfinite(value) for value in (*mean_abs2_series, *charge_residual_series))
    positive_amplitude_pass = all(value > 0.0 for value in mean_abs2_series)
    vortex_count_matches_expected_pass = all(value == expected_vortex_count for value in vortex_count_series)
    overall_pass = finite_observables_pass and positive_amplitude_pass and vortex_count_matches_expected_pass
    return {
        "checked_sample_count": len(rows),
        "sample_steps": steps,
        "sample_times": times,
        "vortex_count_series": vortex_count_series,
        "mean_abs2_series": mean_abs2_series,
        "charge_residual_inf_series": charge_residual_series,
        "finite_observables_pass": finite_observables_pass,
        "positive_amplitude_pass": positive_amplitude_pass,
        "vortex_count_matches_expected_pass": vortex_count_matches_expected_pass,
        "expected_vortex_count": int(expected_vortex_count),
        "overall_pass": overall_pass,
    }


def compute_seeded_vortex_tier2_diagnostics(
    *,
    psi: np.ndarray,
    vortex_map: np.ndarray,
    resolved_seeds: Sequence[ResolvedVortexSeed],
    timeseries: Sequence[dict[str, Any]],
    n_steps: int,
    sampling_policy: str,
) -> dict[str, Any]:
    """Compute bounded seeded-vortex diagnostics without widening physical claims.

    The payload separates initialization observables from early-window observables so downstream
    validators can enforce different evidence thresholds for `n_steps == 0` versus short-horizon
    deterministic runs.
    """

    case_class = infer_seeded_case_class(n_steps)
    local_winding = [_local_winding_payload(vortex_map, seed, seed_index=index) for index, seed in enumerate(resolved_seeds)]
    core_contrast = [_core_contrast_payload(psi, seed, seed_index=index) for index, seed in enumerate(resolved_seeds)]
    expected_vortex_count = int(sum(abs(int(seed.winding)) for seed in resolved_seeds))

    local_winding_verification = {
        "seed_count": len(local_winding),
        "configured_winding_series": [int(seed.winding) for seed in resolved_seeds],
        "host_winding_series": [int(entry["host_winding"]) for entry in local_winding],
        "local_signed_winding_series": [int(entry["local_signed_winding"]) for entry in local_winding],
        "local_abs_winding_series": [int(entry["local_abs_winding"]) for entry in local_winding],
        "initial_total_signed_winding": int(np.sum(vortex_map)),
        "initial_total_abs_winding": int(np.sum(np.abs(vortex_map))),
        "all_host_winding_match": all(bool(entry["host_winding_match"]) for entry in local_winding),
        "all_local_winding_match": all(bool(entry["local_winding_match"]) for entry in local_winding),
        "per_seed": local_winding,
    }
    core_contrast_observables = {
        "seed_count": len(core_contrast),
        "core_observable_series": [bool(entry["core_observable"]) for entry in core_contrast],
        "core_to_ring_ratio_series": [entry["core_to_ring_ratio"] for entry in core_contrast],
        "all_core_observable": all(bool(entry["core_observable"]) for entry in core_contrast),
        "per_seed": core_contrast,
    }
    initialization_observables = {
        "local_winding_verification": local_winding_verification,
        "core_contrast_observables": core_contrast_observables,
        "overall_pass": local_winding_verification["all_host_winding_match"]
        and local_winding_verification["all_local_winding_match"]
        and core_contrast_observables["all_core_observable"],
    }
    sampled_rows = _sample_rows(timeseries, n_steps=n_steps, sampling_policy=sampling_policy)
    early_window_observables = _early_window_payload(
        timeseries,
        expected_vortex_count,
        n_steps=n_steps,
        sampling_policy=sampling_policy,
    )
    tier2_overall_pass = bool(initialization_observables["overall_pass"]) and (
        True if early_window_observables is None else bool(early_window_observables["overall_pass"])
    )
    return {
        "schema_version": SEEDED_VORTEX_TIER2_SCHEMA_VERSION,
        "diagnostic_interpretation_version": SEEDED_VORTEX_DIAGNOSTIC_INTERPRETATION_VERSION,
        "resolution_policy": SEED_RESOLUTION_POLICY,
        "case_class": case_class,
        "horizon_contract": {
            "n_steps": int(n_steps),
            "sampling_policy": sampling_policy,
            "observed_sample_count": len(sampled_rows),
            "observed_step_series": [int(_coerce_row_value(row, "step")) for row in sampled_rows],
        },
        "diagnostic_classification": {
            "initialization_observables": "initialization_observable",
            "early_window_observables": "early_window_observable",
        },
        "seed_count": len(resolved_seeds),
        "configured_signed_winding": int(sum(int(seed.winding) for seed in resolved_seeds)),
        "configured_abs_winding": expected_vortex_count,
        "expected_vortex_count": expected_vortex_count,
        "initialization_observables": initialization_observables,
        "early_window_observables": early_window_observables,
        "tier2_overall_pass": tier2_overall_pass,
    }


def _require_mapping(payload: dict[str, Any], key: str, *, label: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ObservableExtractionError(f"{label} is missing required mapping '{key}'")
    return dict(value)


def _require_nonempty_series(payload: dict[str, Any], key: str, *, label: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ObservableExtractionError(f"{label} is missing required non-empty series '{key}'")
    return list(value)


def extract_observables(
    tier2_payload: dict[str, Any],
    required: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Extract the supported Tier-2 observable surface and enforce required keys when requested.

    This accessor is intentionally fail-closed: unsupported names and absent required observables
    both raise contract errors instead of silently returning partial payloads.
    """

    initialization = _require_mapping(tier2_payload, "initialization_observables", label="Tier-2 payload")
    local_winding = _require_mapping(initialization, "local_winding_verification", label="initialization_observables")
    core_contrast = _require_mapping(initialization, "core_contrast_observables", label="initialization_observables")
    ratio_series = [
        float(value)
        for value in _require_nonempty_series(core_contrast, "core_to_ring_ratio_series", label="core_contrast_observables")
        if value is not None
    ]

    observables: dict[str, Any] = {
        "initialization.seed_count": int(local_winding["seed_count"]),
        "initialization.local_winding.initial_total_signed_winding": int(local_winding["initial_total_signed_winding"]),
        "initialization.local_winding.initial_total_abs_winding": int(local_winding["initial_total_abs_winding"]),
        "initialization.local_winding.all_host_winding_match": bool(local_winding["all_host_winding_match"]),
        "initialization.local_winding.all_local_winding_match": bool(local_winding["all_local_winding_match"]),
        "initialization.core_contrast.all_core_observable": bool(core_contrast["all_core_observable"]),
        "initialization.overall_pass": bool(initialization["overall_pass"]),
    }
    if ratio_series:
        observables["initialization.core_contrast.mean_core_to_ring_ratio"] = float(np.mean(ratio_series))
        observables["initialization.core_contrast.min_core_to_ring_ratio"] = float(min(ratio_series))
        observables["initialization.core_contrast.max_core_to_ring_ratio"] = float(max(ratio_series))

    early_window = tier2_payload.get("early_window_observables")
    if early_window is None:
        if required:
            missing = [name for name in required if name.startswith("early_window.")]
            if missing:
                raise Tier2ContractError(
                    "Tier-2 payload did not provide required early_window observables: " + ", ".join(sorted(missing))
                )
    elif not isinstance(early_window, dict):
        raise ObservableExtractionError("Tier-2 payload 'early_window_observables' must be a mapping or null")
    else:
        mean_abs2_series = [float(value) for value in _require_nonempty_series(early_window, "mean_abs2_series", label="early_window_observables")]
        charge_residual_series = [
            float(value) for value in _require_nonempty_series(early_window, "charge_residual_inf_series", label="early_window_observables")
        ]
        vortex_count_series = [int(value) for value in _require_nonempty_series(early_window, "vortex_count_series", label="early_window_observables")]
        observables.update(
            {
                "early_window.checked_sample_count": int(early_window["checked_sample_count"]),
                "early_window.expected_vortex_count": int(early_window["expected_vortex_count"]),
                "early_window.vortex_count_initial": int(vortex_count_series[0]),
                "early_window.vortex_count_final": int(vortex_count_series[-1]),
                "early_window.vortex_count_min": int(min(vortex_count_series)),
                "early_window.vortex_count_max": int(max(vortex_count_series)),
                "early_window.mean_abs2_initial": float(mean_abs2_series[0]),
                "early_window.mean_abs2_final": float(mean_abs2_series[-1]),
                "early_window.mean_abs2_min": float(min(mean_abs2_series)),
                "early_window.mean_abs2_max": float(max(mean_abs2_series)),
                "early_window.charge_residual_inf_initial": float(charge_residual_series[0]),
                "early_window.charge_residual_inf_final": float(charge_residual_series[-1]),
                "early_window.charge_residual_inf_min": float(min(charge_residual_series)),
                "early_window.charge_residual_inf_max": float(max(charge_residual_series)),
                "early_window.finite_observables_pass": bool(early_window["finite_observables_pass"]),
                "early_window.positive_amplitude_pass": bool(early_window["positive_amplitude_pass"]),
                "early_window.vortex_count_matches_expected_pass": bool(early_window["vortex_count_matches_expected_pass"]),
                "early_window.overall_pass": bool(early_window["overall_pass"]),
            }
        )

    if required:
        unsupported = sorted(name for name in required if name not in SUPPORTED_TIER2_OBSERVABLES)
        if unsupported:
            raise ObservableExtractionError(
                "Unsupported Tier-2 observables requested: " + ", ".join(unsupported)
            )
        missing = sorted(name for name in required if name not in observables)
        if missing:
            raise Tier2ContractError(
                "Tier-2 payload is missing required observables: " + ", ".join(missing)
            )
    return observables
