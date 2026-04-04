"""Sequential ensemble execution helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import shutil
import tempfile
from typing import Any, Sequence

from tdgl_rf.config.loaders import load_case_config, load_raw_config, repo_root, write_expanded_config
from tdgl_rf.exceptions import ConfigError, OutputDirectoryError, TDGLRFError
from tdgl_rf.io.reports import write_json
from tdgl_rf.utils.seeds import derive_seed
from tdgl_rf.workflows.run_case import run_simulation


@dataclass(frozen=True)
class PlannedEnsembleMember:
    run_id: str
    run_dir: str
    config_path: str
    member_index: int
    noise_seed: int
    experiment_metadata: dict[str, Any] | None = None
    ensemble_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class EnsembleRunSummary:
    status: str
    output_dir: str
    member_count: int
    member_run_dirs: list[str]
    diagnostic_file_paths: dict[str, str]


def _member_value(member: Any, key: str) -> Any:
    if isinstance(member, dict):
        return member[key]
    return getattr(member, key)


def execute_ensemble_plan(members: Sequence[Any]) -> list[Any]:
    """Execute ensemble members sequentially and fail fast on the first error."""

    summaries: list[Any] = []
    for member in members:
        try:
            summaries.append(
                run_simulation(
                    _member_value(member, "config_path"),
                    run_dir_override=_member_value(member, "run_dir"),
                    experiment_metadata=_member_value(member, "experiment_metadata"),
                    ensemble_metadata=_member_value(member, "ensemble_metadata"),
                )
            )
        except Exception as exc:
            raise TDGLRFError(
                f"ensemble member {_member_value(member, 'member_index')} ({_member_value(member, 'run_id')}) failed: {exc}"
            ) from exc
    return summaries


def _normalize_noise_payload(payload: dict[str, Any]) -> None:
    noise_payload = payload.setdefault("noise", {})
    if "strength" not in noise_payload and "gamma_psi" in noise_payload:
        noise_payload["strength"] = noise_payload["gamma_psi"]
    if "seed" not in noise_payload and "master_seed" in noise_payload:
        noise_payload["seed"] = noise_payload["master_seed"]
    noise_payload.pop("gamma_psi", None)
    noise_payload.pop("master_seed", None)


def _prepare_output_transaction(destination: Path) -> tuple[Path, Path]:
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if any(destination.iterdir()):
            raise OutputDirectoryError(f"ensemble output directory already exists and is not empty: {destination}")
        destination.rmdir()
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent))
    return destination, staging_dir


def _cleanup_destination(destination: Path) -> None:
    shutil.rmtree(destination, ignore_errors=True)


def run_ensemble(config_path: str | Path) -> EnsembleRunSummary:
    """Execute a local stochastic ensemble from one validated case config."""

    resolved_config_path = Path(config_path).resolve()
    config = load_case_config(resolved_config_path)
    if not config.noise.enabled:
        raise ConfigError("run-ensemble requires noise.enabled=true; deterministic fallback is disabled")

    member_count = int(config.campaign.ensemble_size)
    output_root = Path(config.output.root_dir)
    if not output_root.is_absolute():
        output_root = (repo_root() / output_root).resolve()
    destination = (output_root / config.metadata.case_id / "ensemble").resolve()
    destination, staging_destination = _prepare_output_transaction(destination)

    raw_payload = load_raw_config(resolved_config_path)
    _normalize_noise_payload(raw_payload)

    members: list[PlannedEnsembleMember] = []
    for member_index in range(member_count):
        member_seed = derive_seed(config.noise.seed, config.metadata.case_id, member_index)
        run_id = f"{config.metadata.case_id}__m{member_index}"
        run_dir = staging_destination / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        member_payload = dict(raw_payload)
        member_payload["metadata"] = dict(member_payload.get("metadata", {}))
        member_payload["metadata"]["case_id"] = run_id
        member_payload["output"] = dict(member_payload.get("output", {}))
        member_payload["output"]["root_dir"] = str(destination)
        member_payload["noise"] = dict(member_payload.get("noise", {}))
        member_payload["noise"]["seed"] = int(member_seed)
        staged_config_path = run_dir / "source_config.yaml"
        write_expanded_config(member_payload, staged_config_path)
        members.append(
            PlannedEnsembleMember(
                run_id=run_id,
                run_dir=str(run_dir),
                config_path=str(staged_config_path),
                member_index=member_index,
                noise_seed=member_seed,
            )
        )

    try:
        execute_ensemble_plan(members)
        staging_destination.replace(destination)
        summary_path = destination / "ensemble_summary.json"
        write_json(
            summary_path,
            {
                "status": "success",
                "output_dir": str(destination),
                "member_count": member_count,
                "member_run_dirs": [str(destination / Path(member.run_dir).name) for member in members],
            },
        )
        return EnsembleRunSummary(
            status="success",
            output_dir=str(destination),
            member_count=member_count,
            member_run_dirs=[str(destination / Path(member.run_dir).name) for member in members],
            diagnostic_file_paths={"run_summary": str(summary_path)},
        )
    except Exception:
        shutil.rmtree(staging_destination, ignore_errors=True)
        _cleanup_destination(destination)
        raise
