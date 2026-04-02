"""Config validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tdgl_rf.config.models import TDGLRFCaseConfig
from tdgl_rf.exceptions import ConfigError


def validate_against_schema(data: dict[str, Any], schema_path: Path) -> None:
    """Validate raw data against the frozen artifact-pack JSON schema."""

    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ConfigError(f"schema validation failed at {location}: {first.message}")


def validate_semantics(config: TDGLRFCaseConfig, config_dir: Path) -> None:
    """Validate semantic constraints not expressed cleanly in the JSON schema."""

    if config.mesh.periodic_x or config.mesh.periodic_y:
        raise ConfigError("periodic boundaries are intentionally out of scope for the phase-1 implementation")

    if config.physics.initial_condition == "restart" and not config.physics.restart_file:
        raise ConfigError("restart initial conditions require physics.restart_file")

    if config.physics.initial_condition != "restart" and config.physics.restart_file:
        raise ConfigError("physics.restart_file is only valid for restart initial conditions")

    if config.physics.initial_condition == "seeded_vortices":
        raise ConfigError("seeded_vortices are a later deterministic V&V phase and are not enabled in phase 1")

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

    if config.noise.enabled:
        raise ConfigError("stochastic forcing is reserved for phase 3; set noise.enabled=false for phase 1")

    if config.inference.enabled or config.inference.mode != "none":
        raise ConfigError("inference workflows are reserved for phase 6; disable inference for phase 1")

    if config.observables.weight_profile_f == "from_file" or config.observables.weight_profile_q == "from_file":
        raise ConfigError("from_file observable weight profiles are reserved for a later phase")


def validate_case_config(data: dict[str, Any], schema_path: Path, config_dir: Path) -> TDGLRFCaseConfig:
    """Validate and parse a case configuration."""

    validate_against_schema(data, schema_path)
    try:
        config = TDGLRFCaseConfig.model_validate(data)
    except Exception as exc:  # pragma: no cover - pydantic detail passthrough
        raise ConfigError(str(exc)) from exc
    validate_semantics(config, config_dir)
    return config
