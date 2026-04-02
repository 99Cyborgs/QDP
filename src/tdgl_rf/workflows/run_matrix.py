"""Experiment-matrix execution with durable campaign state."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import csv
import numpy as np
import yaml

from tdgl_rf.config.loaders import deep_merge, default_schema_path, load_raw_config, repo_root, write_expanded_config
from tdgl_rf.config.models import TDGLRFCaseConfig
from tdgl_rf.config.validators import validate_case_config
from tdgl_rf.exceptions import ConfigError
from tdgl_rf.io.reports import write_csv, write_json
from tdgl_rf.utils.logging import configure_logger
from tdgl_rf.workflows.run_case import run_simulation
from tdgl_rf.workflows.run_ensemble import run_ensemble
from tdgl_rf.workflows.run_inference import run_inference

REQUIRED_MATRIX_COLUMNS = (
    "case_id",
    "phase",
    "base_config",
    "geometry_family",
    "nx",
    "ny",
    "pinning_model",
    "pinning_mu",
    "pinning_sigma",
    "pinning_lcorr",
    "defect_count",
    "b_dc",
    "a_rf",
    "omega",
    "gamma_noise",
    "dt",
    "n_steps",
    "ensemble_size",
    "obs_stride",
    "field_stride",
    "goal",
    "success_metric",
    "promotion_rule",
    "notes",
)
INT_COLUMNS = {"nx", "ny", "defect_count", "n_steps", "ensemble_size", "obs_stride", "field_stride"}
FLOAT_COLUMNS = {"pinning_mu", "pinning_sigma", "pinning_lcorr", "b_dc", "a_rf", "omega", "gamma_noise", "dt"}
ROW_RESULTS_FILENAME = "row_results.csv"
STATE_FILENAME = "campaign_state.json"
SUMMARY_FILENAME = "campaign_summary.json"
@dataclass(frozen=True)
class CampaignRow:
    row_index: int
    case_id: str
    phase: str
    values: dict[str, Any]


@dataclass(frozen=True)
class MatrixRowResult:
    row_index: int
    case_id: str
    phase: str
    status: str
    dispatcher: str | None
    attempts: int
    expanded_config_path: str
    base_config_ref: str
    base_config_path: str
    goal: str
    success_metric: str
    promotion_rule: str | None
    notes: str
    start_timestamp: str | None = None
    stop_timestamp: str | None = None
    wall_clock_seconds: float | None = None
    run_dir: str | None = None
    summary_path: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class CampaignSummary:
    status: str
    matrix_path: str
    campaign_dir: str
    log_path: str
    selected_row_count: int
    attempted_row_count: int
    success_count: int
    failed_count: int
    blocked_count: int
    validated_count: int
    pending_count: int
    skipped_success_count: int
    gate_status: dict[str, Any]
    start_timestamp: str
    stop_timestamp: str
    row_results_path: str
    state_path: str
    summary_path: str


def _matrix_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_matrix_row(raw_row: dict[str, Any], row_index: int) -> CampaignRow:
    missing = [column for column in REQUIRED_MATRIX_COLUMNS if column not in raw_row]
    if missing:
        raise ConfigError(f"matrix row {row_index} is missing required columns: {', '.join(missing)}")

    values: dict[str, Any] = {}
    for key in REQUIRED_MATRIX_COLUMNS:
        raw_value = raw_row.get(key)
        if raw_value is None:
            value = None
        elif isinstance(raw_value, str):
            value = raw_value.strip()
        else:
            value = raw_value

        if key in INT_COLUMNS and value not in (None, ""):
            values[key] = int(value)
        elif key in FLOAT_COLUMNS and value not in (None, ""):
            values[key] = float(value)
        else:
            values[key] = value

    case_id = str(values["case_id"])
    phase = str(values["phase"])
    return CampaignRow(row_index=row_index, case_id=case_id, phase=phase, values=values)


def load_experiment_matrix(matrix_path: str | Path) -> list[CampaignRow]:
    """Load a CSV or YAML experiment matrix into normalized row records."""

    path = Path(matrix_path).resolve()
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    elif suffix in {".yaml", ".yml"}:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or []
        if isinstance(payload, dict):
            rows = payload.get("rows", [])
        else:
            rows = payload
        if not isinstance(rows, list):
            raise ConfigError(f"expected a list of row mappings in {path}")
        if rows and not isinstance(rows[0], dict):
            raise ConfigError(f"expected row mappings in {path}")
    else:
        raise ConfigError(f"unsupported matrix format: {path.suffix}")

    return [_normalize_matrix_row(raw_row, row_index) for row_index, raw_row in enumerate(rows, start=1)]


def parse_selectors(selectors: list[str] | None) -> list[tuple[str, str]]:
    """Parse CLI selectors of the form ``column=value``."""

    parsed: list[tuple[str, str]] = []
    for selector in selectors or []:
        if "=" not in selector:
            raise ConfigError(f"invalid selector '{selector}'; expected key=value")
        key, value = selector.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ConfigError(f"invalid selector '{selector}'; missing key")
        parsed.append((key, value))
    return parsed


def filter_matrix_rows(rows: list[CampaignRow], selectors: list[str] | None = None) -> list[CampaignRow]:
    """Filter rows by exact-match selectors."""

    parsed = parse_selectors(selectors)
    if not parsed:
        return rows

    selected: list[CampaignRow] = []
    for row in rows:
        if all(str(row.values.get(key)) == value for key, value in parsed):
            selected.append(row)
    return selected


def _resolve_base_config(base_config_ref: str, matrix_dir: Path) -> Path:
    candidate = Path(base_config_ref)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        matrix_relative = (matrix_dir / candidate).resolve()
        repo_relative = (repo_root() / candidate).resolve()
        resolved = matrix_relative if matrix_relative.exists() else repo_relative
    if not resolved.exists():
        raise ConfigError(f"matrix base_config does not exist: {base_config_ref}")
    return resolved


def _absolutize_optional_path(payload: dict[str, Any], section: str, key: str, source_dir: Path) -> None:
    section_payload = payload.get(section)
    if not isinstance(section_payload, dict):
        return
    value = section_payload.get(key)
    if not value:
        return
    resolved = Path(value)
    if not resolved.is_absolute():
        section_payload[key] = str((source_dir / resolved).resolve())


def _execution_snapshot_payload(expanded_raw: dict[str, Any], source_dir: Path, case_output_root: Path) -> dict[str, Any]:
    snapshot = deepcopy(expanded_raw)
    snapshot["base_config"] = None
    snapshot.setdefault("output", {})
    snapshot["output"]["root_dir"] = str(case_output_root.resolve())
    _absolutize_optional_path(snapshot, "physics", "restart_file", source_dir)
    _absolutize_optional_path(snapshot, "geometry", "mask_file", source_dir)
    _absolutize_optional_path(snapshot, "forcing", "rf_profile_file", source_dir)
    _absolutize_optional_path(snapshot, "inference", "dataset_path", source_dir)
    return snapshot


def _default_gaussian_defects(row: CampaignRow, snapshot: dict[str, Any]) -> list[dict[str, float]]:
    mesh = snapshot.get("mesh", {})
    physics = snapshot.get("physics", {})
    pinning = physics.get("pinning", {})
    defect_count = int(pinning.get("defect_count", 0))
    if defect_count < 1:
        return []

    lx = float(mesh["lx"])
    ly = float(mesh["ly"])
    width = max(min(ly / 8.0, lx / 16.0), min(lx / max(int(mesh["nx"]), 1), ly / max(int(mesh["ny"]), 1)))
    x_positions = np.linspace(lx / (defect_count + 1), lx * defect_count / (defect_count + 1), defect_count, dtype=float)
    y0 = 0.5 * ly
    return [
        {
            "x0": float(x0),
            "y0": float(y0),
            "amplitude": 1.0,
            "width": float(width),
        }
        for x0 in x_positions
    ]


def _default_circular_exclusion(snapshot: dict[str, Any]) -> dict[str, float]:
    mesh = snapshot.get("mesh", {})
    lx = float(mesh["lx"])
    ly = float(mesh["ly"])
    radius = min(lx, ly) / 8.0
    return {
        "x0": 0.5 * lx,
        "y0": 0.5 * ly,
        "radius": radius,
    }


def _apply_matrix_defaults(row: CampaignRow, snapshot: dict[str, Any]) -> dict[str, Any]:
    adjusted = deepcopy(snapshot)
    geometry = adjusted.get("geometry", {})
    pinning = adjusted.get("physics", {}).get("pinning", {})
    if pinning.get("model") == "gaussian_defects" and not pinning.get("defects"):
        pinning["defects"] = _default_gaussian_defects(row, adjusted)
    if geometry.get("family") == "strip_with_moat" and not geometry.get("moats"):
        geometry["moats"] = [_default_circular_exclusion(adjusted)]
    if geometry.get("family") == "strip_with_hole" and not geometry.get("holes"):
        geometry["holes"] = [_default_circular_exclusion(adjusted)]
    return adjusted


def _row_overrides(row: CampaignRow, case_output_root: Path) -> dict[str, Any]:
    values = row.values
    gamma_noise = float(values["gamma_noise"])
    return {
        "base_config": str(values["base_config"]),
        "metadata": {
            "case_id": row.case_id,
            "phase": row.phase,
        },
        "mesh": {
            "nx": int(values["nx"]),
            "ny": int(values["ny"]),
        },
        "geometry": {
            "family": values["geometry_family"],
        },
        "physics": {
            "pinning": {
                "model": values["pinning_model"],
                "mu": float(values["pinning_mu"]),
                "sigma": float(values["pinning_sigma"]),
                "lcorr": float(values["pinning_lcorr"]),
                "defect_count": int(values["defect_count"]),
            },
        },
        "forcing": {
            "b_dc": float(values["b_dc"]),
            "a_rf": float(values["a_rf"]),
            "omega": float(values["omega"]),
        },
        "noise": {
            "enabled": gamma_noise > 0.0,
            "gamma_psi": gamma_noise,
        },
        "time": {
            "dt": float(values["dt"]),
            "n_steps": int(values["n_steps"]),
            "obs_stride": int(values["obs_stride"]),
            "field_stride": int(values["field_stride"]),
        },
        "campaign": {
            "ensemble_size": int(values["ensemble_size"]),
            "matrix_row_id": row.case_id,
            "promotion_rule": values["promotion_rule"],
        },
        "output": {
            "root_dir": str(case_output_root.resolve()),
        },
    }


def build_execution_config(row: CampaignRow, matrix_path: Path, campaign_dir: Path) -> tuple[dict[str, Any], Path, Path]:
    """Expand one matrix row into a self-contained execution config."""

    resolved_base = _resolve_base_config(str(row.values["base_config"]), matrix_path.parent)
    base_raw = load_raw_config(resolved_base)
    expanded_raw = deep_merge(base_raw, _row_overrides(row, campaign_dir / "case_runs"))
    snapshot = _execution_snapshot_payload(expanded_raw, resolved_base.parent, campaign_dir / "case_runs")
    snapshot = _apply_matrix_defaults(row, snapshot)
    config_path = campaign_dir / "expanded_configs" / f"{row.row_index:03d}_{row.case_id}.yaml"
    write_expanded_config(snapshot, config_path)
    return snapshot, config_path, resolved_base


def _planned_dispatcher(row: CampaignRow, config: TDGLRFCaseConfig | None = None) -> str:
    if config is not None:
        if config.inference.enabled or config.inference.mode != "none":
            return "run_inference"
        if config.noise.enabled or config.campaign.ensemble_size > 1 or config.metadata.phase == "S":
            return "run_ensemble"
        return "run_simulation"

    if row.phase == "I":
        return "run_inference"
    if row.phase == "S":
        return "run_ensemble"
    if row.phase == "P":
        if float(row.values["gamma_noise"]) > 0.0 or int(row.values["ensemble_size"]) > 1:
            return "run_ensemble"
        return "run_simulation"
    return "run_simulation"


def _planned_dispatcher_from_snapshot(row: CampaignRow, snapshot: dict[str, Any]) -> str:
    metadata = snapshot.get("metadata", {})
    inference = snapshot.get("inference", {})
    noise = snapshot.get("noise", {})
    campaign = snapshot.get("campaign", {})
    if inference.get("enabled") or inference.get("mode") not in (None, "none"):
        return "run_inference"
    if noise.get("enabled") or int(campaign.get("ensemble_size", 1)) > 1 or metadata.get("phase") == "S":
        return "run_ensemble"
    return _planned_dispatcher(row)


def _dispatch(config: TDGLRFCaseConfig):
    if config.inference.enabled or config.inference.mode != "none":
        return "run_inference", run_inference
    if config.noise.enabled or config.campaign.ensemble_size > 1 or config.metadata.phase == "S":
        return "run_ensemble", run_ensemble
    return "run_simulation", run_simulation


def _default_result(row: CampaignRow, campaign_dir: Path) -> MatrixRowResult:
    values = row.values
    return MatrixRowResult(
        row_index=row.row_index,
        case_id=row.case_id,
        phase=row.phase,
        status="pending",
        dispatcher=_planned_dispatcher(row),
        attempts=0,
        expanded_config_path=str(campaign_dir / "expanded_configs" / f"{row.row_index:03d}_{row.case_id}.yaml"),
        base_config_ref=str(values["base_config"]),
        base_config_path="",
        goal=str(values["goal"]),
        success_metric=str(values["success_metric"]),
        promotion_rule=str(values["promotion_rule"]) if values["promotion_rule"] else None,
        notes=str(values["notes"]),
    )


def _result_dicts(results: list[MatrixRowResult]) -> list[dict[str, Any]]:
    return [asdict(result) for result in results]


def _gate_status(results: list[MatrixRowResult]) -> dict[str, Any]:
    gates: dict[str, Any] = {}
    for gate_name in ("gate:G1", "gate:G2", "gate:G3"):
        matching = [result for result in results if result.promotion_rule == gate_name]
        success = sum(result.status == "success" for result in matching)
        validated = sum(result.status == "validated" for result in matching)
        gates[gate_name] = {
            "required": len(matching),
            "success": success,
            "validated": validated,
            "passed": bool(matching) and success == len(matching),
            "dry_run_ready": bool(matching) and (success + validated) == len(matching),
        }
    return gates


def _aggregate_summary(
    *,
    matrix_path: Path,
    campaign_dir: Path,
    results: list[MatrixRowResult],
    attempted_row_count: int,
    skipped_success_count: int,
    start_timestamp: str,
    stop_timestamp: str,
    dry_run: bool,
) -> CampaignSummary:
    counts = {
        "success": 0,
        "failed": 0,
        "blocked": 0,
        "validated": 0,
        "pending": 0,
        "running": 0,
    }
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1

    if dry_run:
        overall = "dry_run" if counts["failed"] == 0 else "dry_run_with_issues"
    else:
        overall = "success" if counts["failed"] == 0 and counts["blocked"] == 0 and counts["pending"] == 0 and counts["running"] == 0 else "partial_failure"

    return CampaignSummary(
        status=overall,
        matrix_path=str(matrix_path),
        campaign_dir=str(campaign_dir),
        log_path=str(campaign_dir / "logs" / "campaign.log"),
        selected_row_count=len(results),
        attempted_row_count=attempted_row_count,
        success_count=counts["success"],
        failed_count=counts["failed"],
        blocked_count=counts["blocked"],
        validated_count=counts["validated"],
        pending_count=counts["pending"] + counts["running"],
        skipped_success_count=skipped_success_count,
        gate_status=_gate_status(results),
        start_timestamp=start_timestamp,
        stop_timestamp=stop_timestamp,
        row_results_path=str(campaign_dir / ROW_RESULTS_FILENAME),
        state_path=str(campaign_dir / STATE_FILENAME),
        summary_path=str(campaign_dir / SUMMARY_FILENAME),
    )


def _state_payload(
    *,
    matrix_path: Path,
    campaign_dir: Path,
    results: list[MatrixRowResult],
    selectors: list[str],
    start_timestamp: str,
    stop_timestamp: str,
    attempted_row_count: int,
    skipped_success_count: int,
    dry_run: bool,
) -> dict[str, Any]:
    summary = _aggregate_summary(
        matrix_path=matrix_path,
        campaign_dir=campaign_dir,
        results=results,
        attempted_row_count=attempted_row_count,
        skipped_success_count=skipped_success_count,
        start_timestamp=start_timestamp,
        stop_timestamp=stop_timestamp,
        dry_run=dry_run,
    )
    return {
        "matrix_path": str(matrix_path),
        "matrix_hash": _matrix_hash(matrix_path),
        "campaign_dir": str(campaign_dir),
        "selectors": selectors,
        "dry_run": dry_run,
        "start_timestamp": start_timestamp,
        "stop_timestamp": stop_timestamp,
        "rows": _result_dicts(results),
        "summary": asdict(summary),
    }


def _persist_campaign_state(
    *,
    matrix_path: Path,
    campaign_dir: Path,
    results: list[MatrixRowResult],
    selectors: list[str],
    start_timestamp: str,
    stop_timestamp: str,
    attempted_row_count: int,
    skipped_success_count: int,
    dry_run: bool,
) -> CampaignSummary:
    payload = _state_payload(
        matrix_path=matrix_path,
        campaign_dir=campaign_dir,
        results=results,
        selectors=selectors,
        start_timestamp=start_timestamp,
        stop_timestamp=stop_timestamp,
        attempted_row_count=attempted_row_count,
        skipped_success_count=skipped_success_count,
        dry_run=dry_run,
    )
    write_json(campaign_dir / STATE_FILENAME, payload)
    write_csv(campaign_dir / ROW_RESULTS_FILENAME, payload["rows"])
    write_json(campaign_dir / SUMMARY_FILENAME, payload["summary"])
    return CampaignSummary(**payload["summary"])


def _load_existing_state(campaign_dir: Path) -> dict[str, Any]:
    state_path = campaign_dir / STATE_FILENAME
    if not state_path.exists():
        raise ConfigError(f"resume campaign state does not exist: {state_path}")
    with state_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_resume_request(existing: dict[str, Any], matrix_path: Path, selectors: list[str], dry_run: bool) -> None:
    if dry_run:
        raise ConfigError("resume is not supported with --dry-run")
    existing_hash = existing.get("matrix_hash")
    if existing_hash != _matrix_hash(matrix_path):
        raise ConfigError("resume requested with a different experiment matrix")
    existing_selectors = existing.get("selectors", [])
    if list(existing_selectors) != list(selectors):
        raise ConfigError("resume selectors do not match the stored campaign state")


def _initialize_campaign_dir(matrix_path: Path, resume_dir: Path | None) -> tuple[Path, str]:
    if resume_dir is not None:
        return resume_dir.resolve(), ""

    start_timestamp = datetime.now().isoformat()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    campaign_dir = (repo_root() / "runs" / "campaigns" / matrix_path.stem / stamp).resolve()
    for relative in ("logs", "expanded_configs", "inputs", "case_runs"):
        (campaign_dir / relative).mkdir(parents=True, exist_ok=True)
    snapshot_path = campaign_dir / "inputs" / matrix_path.name
    snapshot_path.write_bytes(matrix_path.read_bytes())
    return campaign_dir, start_timestamp


def _row_from_state(row_payload: dict[str, Any]) -> MatrixRowResult:
    return MatrixRowResult(**row_payload)


def _update_result(results: list[MatrixRowResult], result: MatrixRowResult) -> None:
    for index, current in enumerate(results):
        if current.row_index == result.row_index:
            results[index] = result
            return
    raise ConfigError(f"unknown campaign row index: {result.row_index}")


def _start_row_attempt(current_result: MatrixRowResult) -> MatrixRowResult:
    return MatrixRowResult(
        **{
            **asdict(current_result),
            "status": "running",
            "attempts": current_result.attempts + 1,
            "start_timestamp": datetime.now().isoformat(),
            "stop_timestamp": None,
            "wall_clock_seconds": None,
            "run_dir": None,
            "summary_path": None,
            "failure_reason": None,
        }
    )


def _gate_block_reason(row: CampaignRow, results: list[MatrixRowResult]) -> str | None:
    gates = _gate_status(results)
    if row.phase == "S" and not gates["gate:G1"]["passed"]:
        return "blocked until gate:G1 rows succeed"
    if row.phase == "I" and not gates["gate:G2"]["passed"]:
        return "blocked until gate:G2 rows succeed"
    return None


def _extract_run_artifacts(summary: Any) -> tuple[str | None, str | None]:
    observable_paths = getattr(summary, "observable_file_paths", None)
    if not isinstance(observable_paths, dict):
        return None, None
    summary_path = observable_paths.get("summary")
    if not summary_path:
        return None, None
    run_dir = str(Path(summary_path).resolve().parents[1])
    return run_dir, str(summary_path)


def _run_row(
    row: CampaignRow,
    *,
    matrix_path: Path,
    campaign_dir: Path,
    current_result: MatrixRowResult,
    logger,
    dry_run: bool,
) -> MatrixRowResult:
    timer_start: float | None = None
    running_result = current_result
    try:
        snapshot, config_path, resolved_base = build_execution_config(row, matrix_path, campaign_dir)
        current_result = MatrixRowResult(
            **{
                **asdict(running_result if not dry_run else current_result),
                "expanded_config_path": str(config_path),
                "base_config_path": str(resolved_base),
                "dispatcher": _planned_dispatcher_from_snapshot(row, snapshot),
            }
        )
        validation_context = config_path.parent

        if dry_run:
            config = validate_case_config(snapshot, default_schema_path(), validation_context)
            logger.info("Validated matrix row %s (%s)", row.case_id, row.phase)
            return MatrixRowResult(
                **{
                    **asdict(current_result),
                    "status": "validated",
                    "dispatcher": _planned_dispatcher(row, config),
                    "failure_reason": None,
                    "run_dir": None,
                    "summary_path": None,
                    "start_timestamp": None,
                    "stop_timestamp": None,
                    "wall_clock_seconds": 0.0,
                }
            )
        running_result = current_result
        timer_start = perf_counter()
        config = validate_case_config(snapshot, default_schema_path(), validation_context)
        dispatcher_name, dispatcher = _dispatch(config)
        summary = dispatcher(config_path)
        wall_clock = perf_counter() - timer_start
        run_dir, summary_path = _extract_run_artifacts(summary)
        logger.info("Completed matrix row %s via %s", row.case_id, dispatcher_name)
        return MatrixRowResult(
            **{
                **asdict(running_result),
                "status": "success",
                "dispatcher": dispatcher_name,
                "stop_timestamp": datetime.now().isoformat(),
                "wall_clock_seconds": wall_clock,
                "run_dir": run_dir,
                "summary_path": summary_path,
            }
        )
    except Exception as exc:
        wall_clock = None if dry_run or timer_start is None else perf_counter() - timer_start
        logger.exception("Matrix row %s failed", row.case_id)
        return MatrixRowResult(
            **{
                **asdict(running_result if not dry_run else current_result),
                "dispatcher": current_result.dispatcher or _planned_dispatcher(row),
                "status": "failed",
                "stop_timestamp": datetime.now().isoformat(),
                "wall_clock_seconds": wall_clock,
                "failure_reason": str(exc),
            }
        )


def run_experiment_matrix(
    matrix_path: str | Path,
    *,
    selectors: list[str] | None = None,
    dry_run: bool = False,
    resume_dir: str | Path | None = None,
) -> CampaignSummary:
    """Execute or dry-run a matrix campaign with durable state and aggregation."""

    resolved_matrix_path = Path(matrix_path).resolve()
    selected_rows = filter_matrix_rows(load_experiment_matrix(resolved_matrix_path), selectors)
    if not selected_rows:
        raise ConfigError("matrix selection produced zero rows")

    selectors = selectors or []
    campaign_dir: Path
    start_timestamp: str
    if resume_dir is None:
        campaign_dir, start_timestamp = _initialize_campaign_dir(resolved_matrix_path, None)
        state_results: dict[int, MatrixRowResult] = {}
        attempted_row_count = 0
        skipped_success_count = 0
    else:
        campaign_dir, _ = _initialize_campaign_dir(resolved_matrix_path, Path(resume_dir))
        existing = _load_existing_state(campaign_dir)
        _validate_resume_request(existing, resolved_matrix_path, selectors, dry_run)
        start_timestamp = str(existing["start_timestamp"])
        attempted_row_count = int(existing["summary"]["attempted_row_count"])
        skipped_success_count = int(existing["summary"]["skipped_success_count"])
        state_results = {
            int(row_payload["row_index"]): _row_from_state(row_payload)
            for row_payload in existing.get("rows", [])
        }

    logger = configure_logger(campaign_dir / "logs" / "campaign.log", append=resume_dir is not None)
    logger.info("Campaign start for %s with %d selected rows", resolved_matrix_path.name, len(selected_rows))

    results: list[MatrixRowResult] = []
    for row in selected_rows:
        if row.row_index in state_results:
            results.append(state_results[row.row_index])
        else:
            results.append(_default_result(row, campaign_dir))

    summary = _persist_campaign_state(
        matrix_path=resolved_matrix_path,
        campaign_dir=campaign_dir,
        results=results,
        selectors=selectors,
        start_timestamp=start_timestamp or datetime.now().isoformat(),
        stop_timestamp=datetime.now().isoformat(),
        attempted_row_count=attempted_row_count,
        skipped_success_count=skipped_success_count,
        dry_run=dry_run,
    )

    for row, current_result in zip(selected_rows, list(results), strict=True):
        if resume_dir is not None and current_result.status == "success":
            skipped_success_count += 1
            logger.info("Skipping completed row %s during resume", row.case_id)
            continue
        if resume_dir is not None and current_result.status == "running":
            raise ConfigError(
                f"row {row.case_id} is still marked running in {campaign_dir}; review the active process before resuming"
            )

        if not dry_run:
            block_reason = _gate_block_reason(row, results)
            if block_reason is not None:
                blocked = MatrixRowResult(
                    **{
                        **asdict(current_result),
                        "status": "blocked",
                        "dispatcher": current_result.dispatcher or _planned_dispatcher(row),
                        "stop_timestamp": datetime.now().isoformat(),
                        "wall_clock_seconds": 0.0,
                        "failure_reason": block_reason,
                    }
                )
                _update_result(results, blocked)
                summary = _persist_campaign_state(
                    matrix_path=resolved_matrix_path,
                    campaign_dir=campaign_dir,
                    results=results,
                    selectors=selectors,
                    start_timestamp=start_timestamp or datetime.now().isoformat(),
                    stop_timestamp=datetime.now().isoformat(),
                    attempted_row_count=attempted_row_count,
                    skipped_success_count=skipped_success_count,
                    dry_run=dry_run,
                )
                logger.warning("Blocked matrix row %s: %s", row.case_id, block_reason)
                continue

        current_for_attempt = current_result
        if not dry_run:
            attempted_row_count += 1
            current_for_attempt = _start_row_attempt(current_result)
            _update_result(results, current_for_attempt)
            summary = _persist_campaign_state(
                matrix_path=resolved_matrix_path,
                campaign_dir=campaign_dir,
                results=results,
                selectors=selectors,
                start_timestamp=start_timestamp or datetime.now().isoformat(),
                stop_timestamp=datetime.now().isoformat(),
                attempted_row_count=attempted_row_count,
                skipped_success_count=skipped_success_count,
                dry_run=dry_run,
            )

        row_result = _run_row(
            row,
            matrix_path=resolved_matrix_path,
            campaign_dir=campaign_dir,
            current_result=current_for_attempt,
            logger=logger,
            dry_run=dry_run,
        )
        _update_result(results, row_result)
        summary = _persist_campaign_state(
            matrix_path=resolved_matrix_path,
            campaign_dir=campaign_dir,
            results=results,
            selectors=selectors,
            start_timestamp=start_timestamp or datetime.now().isoformat(),
            stop_timestamp=datetime.now().isoformat(),
            attempted_row_count=attempted_row_count,
            skipped_success_count=skipped_success_count,
            dry_run=dry_run,
        )

    summary = _persist_campaign_state(
        matrix_path=resolved_matrix_path,
        campaign_dir=campaign_dir,
        results=results,
        selectors=selectors,
        start_timestamp=start_timestamp or datetime.now().isoformat(),
        stop_timestamp=datetime.now().isoformat(),
        attempted_row_count=attempted_row_count,
        skipped_success_count=skipped_success_count,
        dry_run=dry_run,
    )
    logger.info("Campaign completed with status %s", summary.status)
    return summary
