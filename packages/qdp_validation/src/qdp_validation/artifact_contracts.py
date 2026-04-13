from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable

import jsonschema

from qdp_io.serialization import load_json


def _path_str(err: jsonschema.ValidationError) -> str:
    if not err.path:
        return "$"
    return "$." + ".".join(str(part) for part in err.path)


SemanticValidator = Callable[[Any], Iterable[str]]


def validate_instance(
    instance: Any,
    schema_path: Path,
    *,
    artifact_kind: str,
    semantic_validate: SemanticValidator | None = None,
) -> Dict[str, Any]:
    schema_path = Path(schema_path)
    if not schema_path.exists():
        return {
            "artifact_kind": artifact_kind,
            "schema_path": str(schema_path),
            "valid": False,
            "errors": [f"schema file not found: {schema_path}"],
        }
    try:
        schema = load_json(schema_path)
    except Exception as exc:
        return {
            "artifact_kind": artifact_kind,
            "schema_path": str(schema_path),
            "valid": False,
            "errors": [f"schema could not be parsed: {exc}"],
        }
    validator = jsonschema.Draft202012Validator(schema)
    errors = [
        f"{_path_str(err)}: {err.message}"
        for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    ]
    if semantic_validate is not None:
        try:
            errors.extend(str(error) for error in semantic_validate(instance))
        except Exception as exc:
            errors.append(f"semantic validation failed: {exc}")
    return {
        "artifact_kind": artifact_kind,
        "schema_path": str(schema_path),
        "valid": not errors,
        "errors": errors,
    }


def validate_file(
    path: Path,
    schema_path: Path,
    *,
    artifact_kind: str,
    semantic_validate: SemanticValidator | None = None,
) -> Dict[str, Any]:
    path = Path(path)
    try:
        payload = load_json(path)
    except FileNotFoundError:
        return {
            "artifact_kind": artifact_kind,
            "schema_path": str(schema_path),
            "path": str(path),
            "valid": False,
            "errors": [f"artifact file not found: {path}"],
        }
    except Exception as exc:
        return {
            "artifact_kind": artifact_kind,
            "schema_path": str(schema_path),
            "path": str(path),
            "valid": False,
            "errors": [f"artifact JSON could not be parsed: {exc}"],
        }
    result = validate_instance(
        payload,
        schema_path,
        artifact_kind=artifact_kind,
        semantic_validate=semantic_validate,
    )
    result["path"] = str(path)
    return result


def emit_validation_result(result: Dict[str, Any]) -> None:
    if result.get("valid", False):
        print("VALID")
        print(f"- artifact_kind: {result.get('artifact_kind', '')}")
        if result.get("path"):
            print(f"- path: {result['path']}")
        print(f"- schema: {result.get('schema_path', '')}")
        return
    print("INVALID")
    for error in result.get("errors", []):
        print(f"- {error}")


def require_no_errors(results: Iterable[Dict[str, Any]]) -> bool:
    return all(result.get("valid", False) for result in results)
