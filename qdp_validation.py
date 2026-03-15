from __future__ import annotations

import importlib.util
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List


def load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def load_schema(schema_path_str: str) -> Dict[str, Any]:
    schema_path = Path(schema_path_str)
    data = load_json_file(schema_path)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {schema_path}")
    return data


@lru_cache(maxsize=None)
def load_validator_module(validator_path_str: str):
    validator_path = Path(validator_path_str)
    if not validator_path.exists():
        raise FileNotFoundError(f"validator file not found: {validator_path}")
    module_name = f"qdp_validator_{abs(hash(validator_path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import validator module from {validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fatal_result(
    message: str,
    *,
    candidate_path: Path | None,
    validator_path: Path,
    schema_path: Path,
    mode: str,
    returncode: int = 2,
) -> Dict[str, Any]:
    return {
        "candidate_path": str(candidate_path) if candidate_path else "",
        "returncode": returncode,
        "stdout": "",
        "stderr": f"{message}\n",
        "valid": False,
        "errors": [],
        "mode": mode,
        "schema_path": str(schema_path),
        "validator_path": str(validator_path),
    }


def _invalid_root_result(
    *,
    candidate_path: Path | None,
    validator_path: Path,
    schema_path: Path,
    mode: str,
) -> Dict[str, Any]:
    return {
        "candidate_path": str(candidate_path) if candidate_path else "",
        "returncode": 1,
        "stdout": "",
        "stderr": "INVALID: candidate root must be exactly one JSON object\n",
        "valid": False,
        "errors": ["candidate root must be exactly one JSON object"],
        "mode": mode,
        "schema_path": str(schema_path),
        "validator_path": str(validator_path),
    }


def _invalid_result(
    errors: Iterable[str],
    *,
    candidate_path: Path | None,
    validator_path: Path,
    schema_path: Path,
    mode: str,
) -> Dict[str, Any]:
    error_list = list(errors)
    lines = ["INVALID", *[f"- {msg}" for msg in error_list]]
    return {
        "candidate_path": str(candidate_path) if candidate_path else "",
        "returncode": 1,
        "stdout": "\n".join(lines) + "\n",
        "stderr": "",
        "valid": False,
        "errors": error_list,
        "mode": mode,
        "schema_path": str(schema_path),
        "validator_path": str(validator_path),
    }


def _valid_result(
    *,
    candidate_path: Path | None,
    validator_path: Path,
    schema_path: Path,
    mode: str,
) -> Dict[str, Any]:
    candidate_label = str(candidate_path) if candidate_path else "<in-memory>"
    lines = [
        "VALID",
        f"- mode: {mode}",
        f"- candidate: {candidate_label}",
        f"- schema: {schema_path}",
    ]
    return {
        "candidate_path": str(candidate_path) if candidate_path else "",
        "returncode": 0,
        "stdout": "\n".join(lines) + "\n",
        "stderr": "",
        "valid": True,
        "errors": [],
        "mode": mode,
        "schema_path": str(schema_path),
        "validator_path": str(validator_path),
    }


def validate_candidate_instance(
    instance: Any,
    validator_path: Path,
    schema_path: Path,
    mode: str = "final",
    *,
    candidate_path: Path | None = None,
) -> Dict[str, Any]:
    validator_path = Path(validator_path)
    schema_path = Path(schema_path)

    if not schema_path.exists():
        return _fatal_result(
            f"FATAL: schema file not found: {schema_path}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )
    if not isinstance(instance, dict):
        return _invalid_root_result(
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    try:
        validator_module = load_validator_module(str(validator_path.resolve()))
    except Exception as exc:
        return _fatal_result(
            f"FATAL: could not import validator module: {exc}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    try:
        schema = load_schema(str(schema_path.resolve()))
    except Exception as exc:
        return _fatal_result(
            f"FATAL: could not parse schema JSON: {exc}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    errors: List[str] = validator_module.schema_validate(instance, schema)
    errors.extend(validator_module.semantic_validate(instance, mode))
    if errors:
        return _invalid_result(
            errors,
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )
    return _valid_result(
        candidate_path=candidate_path,
        validator_path=validator_path,
        schema_path=schema_path,
        mode=mode,
    )


def validate_candidate_file(
    candidate_path: Path,
    validator_path: Path,
    schema_path: Path,
    mode: str = "final",
) -> Dict[str, Any]:
    candidate_path = Path(candidate_path)
    validator_path = Path(validator_path)
    schema_path = Path(schema_path)

    if not candidate_path.exists():
        return _fatal_result(
            f"FATAL: candidate file not found: {candidate_path}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    try:
        instance = load_json_file(candidate_path)
    except Exception as exc:
        return _fatal_result(
            f"FATAL: could not parse candidate JSON: {exc}",
            candidate_path=candidate_path,
            validator_path=validator_path,
            schema_path=schema_path,
            mode=mode,
        )

    return validate_candidate_instance(
        instance,
        validator_path,
        schema_path,
        mode=mode,
        candidate_path=candidate_path,
    )


def emit_validation_result(result: Dict[str, Any]) -> None:
    stdout = str(result.get("stdout", "") or "")
    stderr = str(result.get("stderr", "") or "")
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")
