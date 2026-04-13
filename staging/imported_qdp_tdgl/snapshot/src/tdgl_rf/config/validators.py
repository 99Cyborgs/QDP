"""Config validation helpers."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from tdgl_rf.config.models import TDGLRFCaseConfig
from tdgl_rf.exceptions import ConfigError, SeedRejectionCode, SeedRejectionError
from tdgl_rf.geometry.masks import build_geometry, grid_from_config
from tdgl_rf.runtime_capabilities import require_noise_runtime_support
from tdgl_rf.solvers.seeded_vortices import resolve_vortex_seeds


def _absolute_path_text(parts: tuple[Any, ...] | list[Any]) -> str:
    return ".".join(str(part) for part in parts) or "<root>"


def _seed_index_from_path(parts: list[Any]) -> int | None:
    try:
        vortex_idx = parts.index("vortex_seeds")
    except ValueError:
        return None
    if vortex_idx + 1 < len(parts) and isinstance(parts[vortex_idx + 1], int):
        return int(parts[vortex_idx + 1])
    return None


def _raise_seed_schema_error(message: str, parts: list[Any]) -> None:
    raise SeedRejectionError(
        code=SeedRejectionCode.SCHEMA_INVALID,
        message=message,
        seed_index=_seed_index_from_path(parts),
        field_path=_absolute_path_text(parts),
    )


def validate_against_schema(data: dict[str, Any], schema_path: Path) -> None:
    """Validate raw data against the frozen artifact-pack JSON schema."""

    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.absolute_path))
    if errors:
        first = errors[0]
        path_parts = list(first.absolute_path)
        location = _absolute_path_text(path_parts)
        if len(path_parts) >= 2 and path_parts[0] == "physics" and path_parts[1] == "vortex_seeds":
            _raise_seed_schema_error(f"schema validation failed at {location}: {first.message}", path_parts)
        raise ConfigError(f"schema validation failed at {location}: {first.message}")


def _validate_noise_semantics(config: TDGLRFCaseConfig, raw_data: dict[str, Any]) -> None:
    noise_payload = raw_data.get("noise", {})
    if not isinstance(noise_payload, dict):
        raise ConfigError("noise must be a mapping")

    require_noise_runtime_support(enabled=config.noise.enabled)
    if not config.noise.enabled:
        return

    if "seed" not in noise_payload:
        raise ConfigError("noise.seed is required when noise.enabled=true; implicit RNG is rejected")
    if "strength" not in noise_payload:
        raise ConfigError("noise.strength is required when noise.enabled=true")
    if config.noise.strength <= 0:
        raise ConfigError("noise.strength must be > 0 when noise.enabled=true")


def _normalize_model_aliases(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy alias keys for model parsing without weakening semantic checks."""

    normalized = deepcopy(data)
    noise_payload = normalized.get("noise")
    if isinstance(noise_payload, dict):
        if "strength" not in noise_payload and "gamma_psi" in noise_payload:
            noise_payload["strength"] = noise_payload["gamma_psi"]
        if "seed" not in noise_payload and "master_seed" in noise_payload:
            noise_payload["seed"] = noise_payload["master_seed"]
        noise_payload.pop("gamma_psi", None)
        noise_payload.pop("master_seed", None)
    return normalized


def validate_semantics(config: TDGLRFCaseConfig, config_dir: Path, raw_data: dict[str, Any]) -> None:
    """Validate semantic constraints not expressed cleanly in the JSON schema."""

    if config.mesh.periodic_x or config.mesh.periodic_y:
        raise ConfigError("periodic boundaries are intentionally out of scope for the phase-1 implementation")

    if config.physics.initial_condition == "restart" and not config.physics.restart_file:
        raise ConfigError("restart initial conditions require physics.restart_file")

    if config.physics.initial_condition != "restart" and config.physics.restart_file:
        raise ConfigError("physics.restart_file is only valid for restart initial conditions")

    if config.physics.initial_condition == "seeded_vortices" and not config.physics.vortex_seeds:
        raise SeedRejectionError(
            code=SeedRejectionCode.MISSING_SEEDS,
            field_path="physics.vortex_seeds",
            message="seeded_vortices initial conditions require one or more physics.vortex_seeds entries",
        )

    if config.physics.initial_condition != "seeded_vortices" and config.physics.vortex_seeds:
        raise SeedRejectionError(
            code=SeedRejectionCode.UNEXPECTED_SEEDS,
            field_path="physics.vortex_seeds",
            message="physics.vortex_seeds are only valid when physics.initial_condition == 'seeded_vortices'",
        )

    if config.forcing.rf_profile == "from_file" and not config.forcing.rf_profile_file:
        raise ConfigError("forcing.rf_profile_file is required when forcing.rf_profile == 'from_file'")

    if config.forcing.rf_profile_file:
        rf_path = (config_dir / config.forcing.rf_profile_file).resolve()
        if not rf_path.exists():
            raise ConfigError(f"forcing.rf_profile_file does not exist: {rf_path}")

    if config.geometry.family == "custom_mask" and not config.geometry.mask_file:
        raise ConfigError("geometry.mask_file is required when geometry.family == 'custom_mask'")

    if config.geometry.mask_file:
        mask_path = (config_dir / config.geometry.mask_file).resolve()
        if not mask_path.exists():
            raise ConfigError(f"geometry.mask_file does not exist: {mask_path}")

    if config.physics.initial_condition == "seeded_vortices":
        grid = grid_from_config(config.mesh)
        geometry = build_geometry(grid, config.geometry, config_dir)
        resolve_vortex_seeds(grid, geometry, config.physics.vortex_seeds)

    _validate_noise_semantics(config, raw_data)

    if config.inference.enabled or config.inference.mode != "none":
        raise ConfigError("inference workflows are reserved for phase 6; disable inference for phase 1")

    if config.observables.weight_profile_f == "from_file" or config.observables.weight_profile_q == "from_file":
        raise ConfigError("from_file observable weight profiles are reserved for a later phase")


def validate_case_config(data: dict[str, Any], schema_path: Path, config_dir: Path) -> TDGLRFCaseConfig:
    """Validate and parse a case configuration."""

    validate_against_schema(data, schema_path)
    normalized_for_model = _normalize_model_aliases(data)
    try:
        config = TDGLRFCaseConfig.model_validate(normalized_for_model)
    except ValidationError as exc:
        for error in exc.errors():
            parts = list(error.get("loc", ()))
            if len(parts) >= 2 and parts[0] == "physics" and parts[1] == "vortex_seeds":
                _raise_seed_schema_error(f"model validation failed at {_absolute_path_text(parts)}: {error.get('msg')}", parts)
        raise ConfigError(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - pydantic detail passthrough
        raise ConfigError(str(exc)) from exc
    validate_semantics(config, config_dir, data)
    return config
