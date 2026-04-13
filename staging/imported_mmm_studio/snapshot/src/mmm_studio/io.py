from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar, cast

import yaml
from pydantic import BaseModel

from .models import MMMDataset

ModelT = TypeVar("ModelT", bound=BaseModel)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a mapping at {path}, got {type(payload).__name__}")
    return cast(dict[str, Any], payload)


def load_yaml_model(path: Path, model: type[ModelT]) -> ModelT:
    """Load a YAML document and validate it against a Pydantic model."""

    return model.model_validate(load_yaml(path))


def write_json(path: str | Path, payload: Any) -> Path:
    """Write a JSON payload with stable formatting."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return output


def write_text(path: str | Path, text: str) -> Path:
    """Write UTF-8 text with parent directory creation."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return output


def write_yaml(path: str | Path, payload: Any) -> Path:
    """Write a YAML payload with stable formatting."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
    return output


def load_dataset(root: str | Path) -> MMMDataset:
    """Backward-compatible dataset entry point."""

    from .registry import load_dataset as load_typed_dataset

    return load_typed_dataset(root)
