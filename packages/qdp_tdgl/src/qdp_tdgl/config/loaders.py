"""Recursive config loading and validation."""

from __future__ import annotations

import os
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from qdp_tdgl.config.models import TDGLRFCaseConfig
from qdp_tdgl.config.validators import validate_case_config


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return the QDP monorepo root resolved from this module path."""

    override = os.environ.get("QDP_REPO_ROOT")
    if override:
        candidate = Path(override).expanduser().resolve()
        if (candidate / "CONSOLIDATION_PLAN.md").exists() and (candidate / "packages").is_dir():
            return candidate
        raise FileNotFoundError(
            f"QDP_REPO_ROOT does not point at a QDP monorepo root: {candidate}"
        )

    module_path = Path(__file__).resolve()
    for candidate in module_path.parents:
        if (candidate / "CONSOLIDATION_PLAN.md").exists() and (candidate / "packages").is_dir():
            return candidate
    raise FileNotFoundError(f"unable to resolve QDP monorepo root from {module_path}")


def tdgl_config_root() -> Path:
    """Return the canonical TDGL config directory inside QDP."""

    return repo_root() / "configs" / "tdgl"


def tdgl_validation_root() -> Path:
    """Return the canonical TDGL validation-config directory inside QDP."""

    return repo_root() / "configs" / "validation" / "tdgl"


def default_schema_path() -> Path:
    """Return the canonical schema path."""

    return tdgl_config_root() / "tdgl_case.schema.json"


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge nested dictionaries with override precedence."""

    merged = deepcopy(base)
    for key, value in override.items():
        if key == "base_config":
            merged[key] = value
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise TypeError(f"expected mapping at top level of {path}")
    return data


def load_raw_config(path: str | Path) -> dict[str, Any]:
    """Load a raw YAML config with recursive base-config inheritance applied."""

    config_path = Path(path).resolve()
    data = _read_yaml(config_path)
    base_config = data.get("base_config")
    if not base_config:
        return data
    base_path = (config_path.parent / base_config).resolve()
    base_data = load_raw_config(base_path)
    return deep_merge(base_data, data)


def load_case_config(path: str | Path, schema_path: str | Path | None = None) -> TDGLRFCaseConfig:
    """Load, validate, and parse a case configuration."""

    config_path = Path(path).resolve()
    raw = load_raw_config(config_path)
    schema = Path(schema_path).resolve() if schema_path else default_schema_path()
    return validate_case_config(raw, schema, config_path.parent)


def write_expanded_config(config: TDGLRFCaseConfig | dict[str, Any], destination: str | Path) -> None:
    """Persist the fully expanded config snapshot for provenance."""

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.model_dump(mode="json") if isinstance(config, TDGLRFCaseConfig) else deepcopy(config)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)

