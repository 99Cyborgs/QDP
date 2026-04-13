from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

from qdp_paths import CANDIDATE_VALIDATOR, OUTPUTS_DIR, SCHEMA


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


def run_candidate_sweep(
    outputs_root: Path,
    validator_path: Path,
    schema_path: Path,
    *,
    mode: str = "final",
    max_workers: int = 8,
) -> Dict[str, Any]:
    outputs_root = Path(outputs_root)
    validator_path = Path(validator_path)
    schema_path = Path(schema_path)

    if not outputs_root.exists():
        return {
            "returncode": 1,
            "status": "failure",
            "outputs_root": str(outputs_root),
            "candidates_total": 0,
            "candidates_failed": 0,
            "failed_results": [],
            "error": f"outputs_root_missing: {outputs_root}",
        }

    candidates = sorted(path for path in outputs_root.rglob("*_candidate.json") if path.is_file())
    if not candidates:
        return {
            "returncode": 1,
            "status": "failure",
            "outputs_root": str(outputs_root),
            "candidates_total": 0,
            "candidates_failed": 0,
            "failed_results": [],
            "error": "candidates_total: 0",
        }

    worker_count = max(1, min(int(max_workers), len(candidates)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(
            executor.map(
                lambda path: validate_candidate_file(path, validator_path, schema_path, mode=mode),
                candidates,
            )
        )

    failed_results = [result for result in results if not result["valid"]]
    return {
        "returncode": 0 if not failed_results else 1,
        "status": "success" if not failed_results else "failure",
        "outputs_root": str(outputs_root),
        "candidates_total": len(results),
        "candidates_failed": len(failed_results),
        "failed_results": failed_results,
        "error": None,
    }


def emit_sweep_result(summary: Dict[str, Any]) -> None:
    failed_results = list(summary.get("failed_results", []))
    print("CHECK PASSED" if not failed_results else "CHECK FAILED")
    print(f"- candidates_total: {int(summary.get('candidates_total', 0))}")
    print(f"- candidates_failed: {int(summary.get('candidates_failed', 0))}")
    print(f"- outputs_root: {summary.get('outputs_root', '')}")
    error = summary.get("error")
    if error:
        print(f"- {error}")
    for result in failed_results:
        print(f"- failed_candidate: {result['candidate_path']}")
        emit_validation_result(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one legacy QDP candidate JSON file or sweep emitted "
            "artifacts/outputs/**/*_candidate.json files."
        )
    )
    parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help="Optional candidate JSON path. When omitted, run a repo-level candidate sweep.",
    )
    parser.add_argument("--outputs-root", type=Path, default=OUTPUTS_DIR)
    parser.add_argument("--validator", type=Path, default=CANDIDATE_VALIDATOR)
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    parser.add_argument("--mode", choices=["template", "final"], default="final")
    parser.add_argument("--max-workers", type=int, default=8)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.target is not None:
        result = validate_candidate_file(args.target, args.validator, args.schema, mode=args.mode)
        emit_validation_result(result)
        return int(result["returncode"])

    summary = run_candidate_sweep(
        args.outputs_root,
        args.validator,
        args.schema,
        mode=args.mode,
        max_workers=args.max_workers,
    )
    emit_sweep_result(summary)
    return int(summary["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
