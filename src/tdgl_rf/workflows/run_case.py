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
from tdgl_rf.utils.logging import close_logger, configure_logger
from tdgl_rf.utils.timers import timed


@dataclass(frozen=True)
class RunSummary:
    status: str
    case_id: str
    run_dir: str
    start_timestamp: str
    stop_timestamp: str
    wall_clock_seconds: float
    seed_information: dict[str, Any]
    solver_iteration_stats: dict[str, Any]
    convergence_status: str
    observable_mode: str
    summary_metrics: dict[str, Any]
    observable_file_paths: dict[str, str]
    diagnostic_file_paths: dict[str, str]
    checkpoint_file_paths: list[str]
    failure_reason: str | None = None


def _build_observable_weights(config, grid, geometry):
    weights_f = (
        build_weight_profile(grid, config.observables.weight_profile_f, mask=geometry)
        if config.observables.compute_frequency_shift_proxy
        else None
    )
    weights_q = (
        build_weight_profile(grid, config.observables.weight_profile_q, mask=geometry)
        if config.observables.compute_qinv_proxy
        else None
    )
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


def _observable_mode(config) -> str:
    return "written" if config.output.write_observables else "computed_only"


def _observable_paths(run_dir: Path) -> dict[str, str]:
    return {
        "timeseries": str(run_dir / "observables" / "timeseries.csv"),
        "events": str(run_dir / "observables" / "events.csv"),
        "summary": str(run_dir / "observables" / "summary.json"),
    }


def _diagnostic_paths(run_dir: Path) -> dict[str, str]:
    return {
        "solver_iterations": str(run_dir / "diagnostics" / "solver_iterations.csv"),
        "profiling": str(run_dir / "diagnostics" / "profiling.json"),
        "convergence_report": str(run_dir / "diagnostics" / "convergence_report.json"),
        "run_summary": str(run_dir / "diagnostics" / "run_summary.json"),
    }


def _series_summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "max": 0.0, "final": 0.0}
    return {
        "mean": float(sum(values) / len(values)),
        "max": float(max(values)),
        "final": float(values[-1]),
    }


def _iteration_summary(values: list[int]) -> dict[str, float | int]:
    if not values:
        return {"mean": 0.0, "max": 0, "final": 0, "total": 0}
    return {
        "mean": float(sum(values) / len(values)),
        "max": int(max(values)),
        "final": int(values[-1]),
        "total": int(sum(values)),
    }


def _solver_method_counts(solver_rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in solver_rows:
        method = str(row.get(key, "unknown"))
        counts[method] = counts.get(method, 0) + 1
    return counts


def _fallback_count(method_counts: dict[str, int]) -> int:
    return int(sum(count for method, count in method_counts.items() if "+splu" in method))


def _solver_iteration_stats(requested_n_steps: int, solver_rows: list[dict[str, Any]]) -> dict[str, Any]:
    psi_iterations = [int(row["psi_iterations"]) for row in solver_rows]
    phi_iterations = [int(row["phi_iterations"]) for row in solver_rows]
    psi_residuals = [float(row["psi_residual_norm"]) for row in solver_rows]
    phi_residuals = [float(row["phi_residual_norm"]) for row in solver_rows]
    psi_methods = _solver_method_counts(solver_rows, "psi_solver_method")
    phi_methods = _solver_method_counts(solver_rows, "phi_solver_method")
    return {
        "requested_n_steps": int(requested_n_steps),
        "completed_step_count": len(solver_rows),
        "psi_iteration_summary": _iteration_summary(psi_iterations),
        "phi_iteration_summary": _iteration_summary(phi_iterations),
        "psi_residual_summary": _series_summary(psi_residuals),
        "phi_residual_summary": _series_summary(phi_residuals),
        "psi_solver_method_counts": psi_methods,
        "phi_solver_method_counts": phi_methods,
        "psi_fallback_count": _fallback_count(psi_methods),
        "phi_fallback_count": _fallback_count(phi_methods),
    }


def _running_status_payload(
    run_dir: Path,
    case_id: str,
    start_timestamp: str,
    observable_mode: str,
    state,
    checkpoint_paths: list[str],
    wall_clock_seconds: float | None = None,
) -> dict[str, Any]:
    payload = {
        "status": "running",
        "case_id": case_id,
        "start_timestamp": start_timestamp,
        "run_dir": str(run_dir),
        "observable_mode": observable_mode,
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
    observable_mode: str,
    state,
    checkpoint_paths: list[str],
    wall_clock_seconds: float | None = None,
) -> None:
    write_json(
        run_dir / "status.json",
        _running_status_payload(run_dir, case_id, start_timestamp, observable_mode, state, checkpoint_paths, wall_clock_seconds),
    )


def _profiling_payload(case_id: str, wall_clock: float, solver_stats: dict[str, Any]) -> dict[str, Any]:
    psi_iterations = solver_stats["psi_iteration_summary"]
    phi_iterations = solver_stats["phi_iteration_summary"]
    step_count = int(solver_stats["completed_step_count"])
    return {
        "case_id": case_id,
        "wall_clock_seconds": wall_clock,
        "requested_n_steps": int(solver_stats["requested_n_steps"]),
        "step_count": step_count,
        "steps_per_second": (step_count / wall_clock) if wall_clock > 0 else None,
        "mean_psi_iterations": float(psi_iterations["mean"]),
        "max_psi_iterations": int(psi_iterations["max"]),
        "mean_phi_iterations": float(phi_iterations["mean"]),
        "max_phi_iterations": int(phi_iterations["max"]),
        "psi_solver_method_counts": solver_stats["psi_solver_method_counts"],
        "phi_solver_method_counts": solver_stats["phi_solver_method_counts"],
        "psi_fallback_count": int(solver_stats["psi_fallback_count"]),
        "phi_fallback_count": int(solver_stats["phi_fallback_count"]),
        "psi_residual_summary": solver_stats["psi_residual_summary"],
        "phi_residual_summary": solver_stats["phi_residual_summary"],
    }


def _convergence_payload(
    case_id: str,
    config,
    summary_metrics: dict[str, Any],
    solver_stats: dict[str, Any],
    *,
    status: str,
    observable_mode: str,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    final_residual = summary_metrics.get("final_charge_residual_inf")
    return {
        "case_id": case_id,
        "status": status,
        "observable_mode": observable_mode,
        "mesh_levels": [f"{config.mesh.nx}x{config.mesh.ny}"],
        "dt_levels": [config.time.dt],
        "key_observables": summary_metrics,
        "solver_iteration_stats": solver_stats,
        "pass": status == "success" and final_residual is not None and final_residual < 1.0e-8,
        "failure_reason": failure_reason,
        "notes": "Phase-1 deterministic run summary for baseline acceptance and campaign setup.",
    }


def _write_final_summary(summary: RunSummary) -> None:
    payload = asdict(summary)
    write_json(Path(summary.diagnostic_file_paths["run_summary"]), payload)
    write_json(Path(summary.run_dir) / "status.json", payload)


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
    observable_mode = _observable_mode(config)
    observable_paths_all = _observable_paths(run_dir)
    diagnostic_file_paths = _diagnostic_paths(run_dir)

    start_timestamp = datetime.now().isoformat()
    write_json(
        run_dir / "status.json",
        {
            "status": "running",
            "case_id": config.metadata.case_id,
            "start_timestamp": start_timestamp,
            "run_dir": str(run_dir),
            "observable_mode": observable_mode,
        },
    )

    timeseries: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    solver_rows: list[dict[str, Any]] = []
    checkpoint_paths: list[str] = []
    observable_file_paths: dict[str, str] = {}
    wall_clock = 0.0

    try:
        grid = grid_from_config(config.mesh)
        geometry = build_geometry(grid, config.geometry, config_path.parent)
        alpha = build_alpha_field(grid, geometry, config.physics)
        stepper = TDGLStepper(grid, geometry, alpha, config, config_path.parent)
        state = initialize_state(grid, geometry, config, config_path.parent)
        if config.physics.initial_condition != "restart":
            state = stepper.align_state(state)

        weights_f, weights_q = _build_observable_weights(config, grid, geometry)

        links, supercurrent, normal_current = stepper.compute_currents(state)
        timeseries.append(_sample_observables(config, state, geometry, links, supercurrent, normal_current, weights_f, weights_q))
        prev_vortex_map = compute_vortex_map(state.psi, links, geometry) if config.observables.track_vortices else None

        _write_field_outputs(config, run_dir, state, checkpoint_paths)
        _write_running_status(
            run_dir,
            config.metadata.case_id,
            start_timestamp,
            observable_mode,
            state,
            checkpoint_paths,
            wall_clock_seconds=0.0,
        )

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
                        observable_mode,
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

        if timeseries[-1]["step"] != state.step:
            obs = _sample_observables(config, state, geometry, links, supercurrent, normal_current, weights_f, weights_q)
            if config.observables.track_vortices and prev_vortex_map is not None:
                curr_vortex_map = compute_vortex_map(state.psi, links, geometry)
                events.extend(track_vortices(prev_vortex_map, curr_vortex_map, {"step": state.step, "t": state.t}))
            timeseries.append(obs)

        summary_payload = compute_summary_stats(timeseries, events)
        solver_iteration_stats = _solver_iteration_stats(config.time.n_steps, solver_rows)
        if config.output.write_observables:
            write_csv(observable_paths_all["timeseries"], timeseries)
            write_csv(observable_paths_all["events"], events)
            write_json(observable_paths_all["summary"], summary_payload)
            observable_file_paths = observable_paths_all
        write_csv(diagnostic_file_paths["solver_iterations"], solver_rows)
        write_json(
            diagnostic_file_paths["convergence_report"],
            _convergence_payload(
                config.metadata.case_id,
                config,
                summary_payload,
                solver_iteration_stats,
                status="success",
                observable_mode=observable_mode,
            ),
        )
        write_json(diagnostic_file_paths["profiling"], _profiling_payload(config.metadata.case_id, wall_clock, solver_iteration_stats))

        stop_timestamp = datetime.now().isoformat()
        summary = RunSummary(
            status="success",
            case_id=config.metadata.case_id,
            run_dir=str(run_dir),
            start_timestamp=start_timestamp,
            stop_timestamp=stop_timestamp,
            wall_clock_seconds=wall_clock,
            seed_information={"master_seed": config.noise.master_seed, "pinning_seed": config.physics.pinning.seed},
            solver_iteration_stats=solver_iteration_stats,
            convergence_status="phase1_smoke",
            observable_mode=observable_mode,
            summary_metrics=summary_payload,
            observable_file_paths=observable_file_paths,
            diagnostic_file_paths=diagnostic_file_paths,
            checkpoint_file_paths=checkpoint_paths,
        )
        _write_final_summary(summary)
        logger.info("Completed run %s in %.3f s", config.metadata.case_id, wall_clock)
        return summary
    except BaseException as exc:
        summary_payload = compute_summary_stats(timeseries, events)
        solver_iteration_stats = _solver_iteration_stats(config.time.n_steps, solver_rows)
        write_csv(diagnostic_file_paths["solver_iterations"], solver_rows)
        write_json(
            diagnostic_file_paths["convergence_report"],
            _convergence_payload(
                config.metadata.case_id,
                config,
                summary_payload,
                solver_iteration_stats,
                status="failed",
                observable_mode=observable_mode,
                failure_reason=str(exc),
            ),
        )
        write_json(diagnostic_file_paths["profiling"], _profiling_payload(config.metadata.case_id, wall_clock, solver_iteration_stats))
        stop_timestamp = datetime.now().isoformat()
        summary = RunSummary(
            status="failed",
            case_id=config.metadata.case_id,
            run_dir=str(run_dir),
            start_timestamp=start_timestamp,
            stop_timestamp=stop_timestamp,
            wall_clock_seconds=wall_clock,
            seed_information={"master_seed": config.noise.master_seed, "pinning_seed": config.physics.pinning.seed},
            solver_iteration_stats=solver_iteration_stats,
            convergence_status="failed",
            observable_mode=observable_mode,
            summary_metrics=summary_payload,
            observable_file_paths=observable_file_paths,
            diagnostic_file_paths=diagnostic_file_paths,
            checkpoint_file_paths=checkpoint_paths,
            failure_reason=str(exc),
        )
        _write_final_summary(summary)
        logger.exception("Run %s failed", config.metadata.case_id)
        raise
    finally:
        close_logger(logger)
