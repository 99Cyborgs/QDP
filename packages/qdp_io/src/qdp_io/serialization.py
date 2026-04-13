from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, TypeVar, cast

import yaml
from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def load_json(path: str | Path) -> Any:
    """Load a JSON document from disk."""

    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_json_object(path: str | Path) -> dict[str, Any]:
    """Load one JSON document and require an object root."""

    source = Path(path)
    payload = load_json(source)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a mapping at {source}, got {type(payload).__name__}")
    return cast(dict[str, Any], payload)


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load one YAML document and require an object root."""

    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a mapping at {source}, got {type(payload).__name__}")
    return cast(dict[str, Any], payload)


def load_yaml_model(path: str | Path, model: type[ModelT]) -> ModelT:
    """Load a YAML document and validate it against a Pydantic model."""

    return model.model_validate(load_yaml(path))


def write_json(path: str | Path, payload: Any) -> Path:
    """Write a JSON payload with stable formatting."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return destination


def write_text(path: str | Path, text: str) -> Path:
    """Write UTF-8 text with parent directory creation."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return destination


def write_yaml(path: str | Path, payload: Any) -> Path:
    """Write a YAML payload with stable formatting."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
    return destination


def write_csv(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    """Write a CSV table using the first row to define the stable header."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        destination.write_text("", encoding="utf-8")
        return destination
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return destination
