"""Phase-1 deterministic run workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import math
from pathlib import Path
from typing import Any

from tdgl_rf.config.loaders import load_case_config, repo_root, write_expanded_config
from tdgl_rf.exceptions import OutputWriteError
from tdgl_rf.fields.observables import build_weight_profile, compute_basic_observables, compute_summary_stats
from tdgl_rf.fields.vortices import compute_vortex_map, track_vortices
from tdgl_rf.geometry.defects import build_alpha_field
from tdgl_rf.geometry.masks import build_geometry, grid_from_config
from tdgl_rf.io.checkpoints import write_checkpoint
from tdgl_rf.io.hdf5_writer import write_field_snapshot
from tdgl_rf.io.metadata import build_provenance, create_run_directory
from tdgl_rf.io.reports import write_csv, write_json
from tdgl_rf.solvers.state import initialize_state
from tdgl_rf.solvers.tdgl_stepper import TDGLStepper
from tdgl_rf.utils.logging import configure_logger
from tdgl_rf.utils.timers import timed


@dataclass(frozen=True)
class RunSummary:
    status: str
    case_id: str
    start_timestamp: str
    stop_timestamp: str
    wall_clock_seconds: float
    seed_information: dict[str, Any]
    solver_iteration_stats: dict[str, Any]
    convergence_status: str
    observable_file_paths: dict[str, str]
    checkpoint_file_paths: list[str]
    failure_reason: str | None = None


def _build_observable_weights(config, grid):
    weights_f = build_weight_profile(grid, config.observables.weight_profile_f) if config.observables.compute_frequency_shift_proxy else None
    weights_q = build_weight_profile(grid, config.observables.weight_profile_q) if config.observables.compute_qinv_proxy else None
    return weights_f, weights_q


def _sample_observables(config, state, geometry, links, supercurrent, normal_current, weights_f, weights_q) -> dict[str, Any]:
    return compute_basic_observables(
        state,
        geometry,
        links,
        supercurrent,
        normal_current,
        weights_f,
        weights_q,
        track_vortices=config.observables.track_vortices,
        compute_freq=config.observables.compute_frequency_shift_proxy,
        compute_qinv=config.observables.compute_qinv_proxy,
        c_f=config.observables.c_f,
        c_q=config.observables.c_q,
        qinv_bg=config.observables.qinv_bg,
    )


def _write_field_outputs(config, run_dir: Path, state, checkpoint_paths: list[str]) -> str | None:
    if not config.output.write_fields:
        return None
    if state.step == 0:
        checkpoint_path = run_dir / "fields" / f"checkpoint_{state.step:06d}.h5"
        write_field_snapshot(checkpoint_path, state, config.output.compression)
        checkpoint_paths.append(str(checkpoint_path))
        return str(checkpoint_path)
    if state.step % config.time.field_stride == 0:
        write_field_snapshot(run_dir / "fields" / f"field_{state.step:06d}.h5", state, config.output.compression)
    if state.step % config.time.checkpoint_stride == 0:
        checkpoint_path = run_dir / "fields" / f"checkpoint_{state.step:06d}.h5"
        write_checkpoint(checkpoint_path, state, config.output.compression)
        checkpoint_paths.append(str(checkpoint_path))
        return str(checkpoint_path)
    return None


def _status_payload(run_dir: Path, summary: RunSummary) -> dict[str, Any]:
    payload = asdict(summary)
    payload["run_dir"] = str(run_dir)
    return payload


def _running_status_payload(
    run_dir: Path,
    case_id: str,
    start_timestamp: str,
    state,
    checkpoint_paths: list[str],
    wall_clock_seconds: float | None = None,
) -> dict[str, Any]:
    payload = {
        "status": "running",
        "case_id": case_id,
        "start_timestamp": start_timestamp,
        "run_dir": str(run_dir),
        "latest_step": state.step,
        "latest_time": state.t,
        "latest_checkpoint_path": checkpoint_paths[-1] if checkpoint_paths else None,
    }
    if wall_clock_seconds is not None:
        payload["elapsed_wall_clock_seconds"] = wall_clock_seconds
    return payload


def _write_running_status(
    run_dir: Path,
    case_id: str,
    start_timestamp: str,
    state,
    checkpoint_paths: list[str],
    wall_clock_seconds: float | None = None,
) -> None:
    write_json(
        run_dir / "status.json",
        _running_status_payload(run_dir, case_id, start_timestamp, state, checkpoint_paths, wall_clock_seconds),
    )


def _profiling_payload(case_id: str, wall_clock: float, solver_rows: list[dict[str, Any]]) -> dict[str, Any]:
    psi_iterations = [int(row["psi_iterations"]) for row in solver_rows]
    phi_iterations = [int(row["phi_iterations"]) for row in solver_rows]
    psi_methods: dict[str, int] = {}
    phi_methods: dict[str, int] = {}
    for row in solver_rows:
        psi_method = str(row.get("psi_solver_method", "unknown"))
        phi_method = str(row.get("phi_solver_method", "unknown"))
        psi_methods[psi_method] = psi_methods.get(psi_method, 0) + 1
        phi_methods[phi_method] = phi_methods.get(phi_method, 0) + 1
    return {
        "case_id": case_id,
        "wall_clock_seconds": wall_clock,
        "step_count": len(solver_rows),
        "steps_per_second": (len(solver_rows) / wall_clock) if wall_clock > 0 else None,
        "mean_psi_iterations": (sum(psi_iterations) / len(psi_iterations)) if psi_iterations else 0.0,
        "max_psi_iterations": max(psi_iterations, default=0),
        "mean_phi_iterations": (sum(phi_iterations) / len(phi_iterations)) if phi_iterations else 0.0,
        "max_phi_iterations": max(phi_iterations, default=0),
        "psi_solver_method_counts": psi_methods,
        "phi_solver_method_counts": phi_methods,
    }


def run_simulation(config_path: str | Path) -> RunSummary:
    """Run a deterministic TDGL case from config."""

    config_path = Path(config_path).resolve()
    config = load_case_config(config_path)
    output_root = Path(config.output.root_dir)
    if not output_root.is_absolute():
        output_root = (repo_root() / output_root).resolve()
    run_dir = create_run_directory(output_root, config.metadata.case_id, datetime.now())
    logger = configure_logger(run_dir / "logs" / "run.log")
    write_expanded_config(config, run_dir / "expanded_config.yaml")
    write_json(run_dir / "provenance.json", build_provenance(config, repo_root()))

    start_timestamp = datetime.now().isoformat()
    write_json(
        run_dir / "status.json",
        {
            "status": "running",
            "case_id": config.metadata.case_id,
            "start_timestamp": start_timestamp,
        },
    )

    timeseries: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    solver_rows: list[dict[str, Any]] = []
    checkpoint_paths: list[str] = []

    try:
        grid = grid_from_config(config.mesh)
        geometry = build_geometry(grid, config.geometry, config_path.parent)
        alpha = build_alpha_field(grid, geometry, config.physics)
        stepper = TDGLStepper(grid, geometry, alpha, config, config_path.parent)
        state = initialize_state(grid, geometry, config, config_path.parent)

        weights_f, weights_q = _build_observable_weights(config, grid)

        links, supercurrent, normal_current = stepper.compute_currents(state)
        timeseries.append(_sample_observables(config, state, geometry, links, supercurrent, normal_current, weights_f, weights_q))
        prev_vortex_map = compute_vortex_map(state.psi, links, geometry) if config.observables.track_vortices else None

        _write_field_outputs(config, run_dir, state, checkpoint_paths)
        _write_running_status(run_dir, config.metadata.case_id, start_timestamp, state, checkpoint_paths, wall_clock_seconds=0.0)

        with timed() as elapsed:
            for _ in range(config.time.n_steps):
                state = stepper.advance(state)
                solver_rows.append(state.diagnostics)
                links, supercurrent, normal_current = stepper.compute_currents(state)

                if state.step % config.time.obs_stride == 0:
                    obs = _sample_observables(config, state, geometry, links, supercurrent, normal_current, weights_f, weights_q)
                    if config.observables.track_vortices and prev_vortex_map is not None:
                        curr_vortex_map = compute_vortex_map(state.psi, links, geometry)
                        events.extend(track_vortices(prev_vortex_map, curr_vortex_map, {"step": state.step, "t": state.t}))
                        prev_vortex_map = curr_vortex_map
                    timeseries.append(obs)

                checkpoint_path = _write_field_outputs(config, run_dir, state, checkpoint_paths)
                if checkpoint_path is not None or state.step % max(config.time.obs_stride, 250) == 0:
                    _write_running_status(
                        run_dir,
                        config.metadata.case_id,
                        start_timestamp,
                        state,
                        checkpoint_paths,
                        wall_clock_seconds=elapsed(),
                    )
                    logger.info(
                        "Run %s progress step=%d/%d phi=%s psi=%s",
                        config.metadata.case_id,
                        state.step,
                        config.time.n_steps,
                        state.diagnostics.get("phi_solver_method"),
                        state.diagnostics.get("psi_solver_method"),
                    )

                last_obs = timeseries[-1]
                if not (math.isfinite(last_obs["mean_abs2"]) and math.isfinite(last_obs["charge_residual_inf"])):
                    raise OutputWriteError("invalid observable encountered during run")

            wall_clock = elapsed()

        write_csv(run_dir / "observables" / "timeseries.csv", timeseries)
        write_csv(run_dir / "observables" / "events.csv", events)
        write_csv(run_dir / "diagnostics" / "solver_iterations.csv", solver_rows)
        summary_payload = compute_summary_stats(timeseries, events)
        write_json(run_dir / "observables" / "summary.json", summary_payload)
        write_json(
            run_dir / "diagnostics" / "convergence_report.json",
            {
                "case_id": config.metadata.case_id,
                "mesh_levels": [f"{grid.nx}x{grid.ny}"],
                "dt_levels": [config.time.dt],
                "key_observables": summary_payload,
                "pass": summary_payload["final_charge_residual_inf"] < 1.0e-8,
                "notes": "Phase-1 single-level deterministic smoke report.",
            },
        )
        write_json(run_dir / "diagnostics" / "profiling.json", _profiling_payload(config.metadata.case_id, wall_clock, solver_rows))

        stop_timestamp = datetime.now().isoformat()
        summary = RunSummary(
            status="success",
            case_id=config.metadata.case_id,
            start_timestamp=start_timestamp,
            stop_timestamp=stop_timestamp,
            wall_clock_seconds=wall_clock,
            seed_information={"master_seed": config.noise.master_seed, "pinning_seed": config.physics.pinning.seed},
            solver_iteration_stats={
                "n_steps": config.time.n_steps,
                "max_psi_iterations": max((row["psi_iterations"] for row in solver_rows), default=0),
                "max_phi_iterations": max((row["phi_iterations"] for row in solver_rows), default=0),
            },
            convergence_status="phase1_smoke",
            observable_file_paths={
                "timeseries": str(run_dir / "observables" / "timeseries.csv"),
                "events": str(run_dir / "observables" / "events.csv"),
                "summary": str(run_dir / "observables" / "summary.json"),
            },
            checkpoint_file_paths=checkpoint_paths,
        )
        write_json(run_dir / "status.json", _status_payload(run_dir, summary))
        logger.info("Completed run %s in %.3f s", config.metadata.case_id, wall_clock)
        return summary
    except BaseException as exc:
        stop_timestamp = datetime.now().isoformat()
        summary = RunSummary(
            status="failed",
            case_id=config.metadata.case_id,
            start_timestamp=start_timestamp,
            stop_timestamp=stop_timestamp,
            wall_clock_seconds=0.0,
            seed_information={"master_seed": config.noise.master_seed, "pinning_seed": config.physics.pinning.seed},
            solver_iteration_stats={},
            convergence_status="failed",
            observable_file_paths={},
            checkpoint_file_paths=checkpoint_paths,
            failure_reason=str(exc),
        )
        write_json(run_dir / "status.json", _status_payload(run_dir, summary))
        logger.exception("Run %s failed", config.metadata.case_id)
        raise
