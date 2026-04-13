"""Lightweight refinement-sanity workflow for deterministic phase-1 runs."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from tdgl_rf.config.loaders import load_case_config, repo_root, write_expanded_config
from tdgl_rf.io.reports import write_csv, write_json
from tdgl_rf.workflows.run_case import run_simulation


@dataclass(frozen=True)
class RefinementComparison:
    case_id: str
    mesh_level: str
    nx: int
    ny: int
    dt: float
    run_dir: str
    summary_path: str
    timeseries_path: str
    wall_clock_seconds: float
    final_mean_abs2: float
    final_charge_residual_inf: float
    final_vortex_count: int
    final_delta_f_over_f0: float | None
    final_qinv: float | None
    delta_mean_abs2_vs_reference: float
    delta_charge_residual_inf_vs_reference: float
    delta_delta_f_over_f0_vs_reference: float | None
    delta_qinv_vs_reference: float | None


@dataclass(frozen=True)
class RefinementSummary:
    status: str
    base_config_path: str
    output_dir: str
    comparison_csv_path: str
    comparison_json_path: str
    reference_case_id: str
    case_count: int
    mesh_levels: list[str]
    dt_levels: list[float]


def _read_last_timeseries_row(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-1]


def _mesh_label(nx: int, ny: int) -> str:
    return f"{nx}x{ny}"


def _dt_token(dt: float) -> str:
    text = f"{dt:.6f}".rstrip("0").rstrip(".")
    return text.replace(".", "p")


def _scaled_mesh(nx: int, ny: int, factor: float) -> tuple[int, int]:
    def _round_even(value: float) -> int:
        rounded = int(round(value / 2.0) * 2)
        return max(8, rounded)

    return _round_even(nx * factor), _round_even(ny * factor)


def _default_mesh_levels(base_nx: int, base_ny: int) -> list[tuple[int, int]]:
    return [_scaled_mesh(base_nx, base_ny, factor) for factor in (1.0, 1.5)]


def _variant_payload(base_payload: dict, *, case_id: str, output_root: Path, nx: int, ny: int, dt: float) -> dict:
    payload = json.loads(json.dumps(base_payload))
    payload["base_config"] = None
    payload["metadata"]["case_id"] = case_id
    payload["mesh"]["nx"] = int(nx)
    payload["mesh"]["ny"] = int(ny)
    payload["time"]["dt"] = float(dt)
    payload["output"]["root_dir"] = str(output_root)
    payload["output"]["write_fields"] = False
    payload["output"]["write_observables"] = True
    return payload


def run_refinement_sanity(config_path: str | Path, output_dir: str | Path | None = None) -> RefinementSummary:
    """Run a small deterministic mesh/dt refinement sanity sweep."""

    config_source = Path(config_path).resolve()
    config = load_case_config(config_source)
    base_payload = config.model_dump(mode="json")

    destination = (
        Path(output_dir).resolve()
        if output_dir is not None
        else (repo_root() / "runs" / "refinement_sanity" / config.metadata.case_id / datetime.now().strftime("%Y%m%d-%H%M%S")).resolve()
    )
    config_dir = destination / "configs"
    output_root = destination / "case_runs"
    config_dir.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    mesh_levels = _default_mesh_levels(config.mesh.nx, config.mesh.ny)
    dt_levels = [float(config.time.dt), float(config.time.dt) / 2.0]

    raw_results: list[dict] = []
    for nx, ny in mesh_levels:
        for dt in dt_levels:
            case_id = f"{config.metadata.case_id}_m{nx}x{ny}_dt{_dt_token(dt)}"
            payload = _variant_payload(base_payload, case_id=case_id, output_root=output_root, nx=nx, ny=ny, dt=dt)
            variant_path = config_dir / f"{case_id}.yaml"
            write_expanded_config(payload, variant_path)
            summary = run_simulation(variant_path)
            summary_path = Path(summary.observable_file_paths["summary"])
            timeseries_path = Path(summary.observable_file_paths["timeseries"])
            final_row = _read_last_timeseries_row(timeseries_path)
            raw_results.append(
                {
                    "case_id": case_id,
                    "mesh_level": _mesh_label(nx, ny),
                    "nx": nx,
                    "ny": ny,
                    "dt": dt,
                    "run_dir": summary.run_dir,
                    "summary_path": str(summary_path),
                    "timeseries_path": str(timeseries_path),
                    "wall_clock_seconds": summary.wall_clock_seconds,
                    "final_mean_abs2": float(summary.summary_metrics["final_mean_abs2"]),
                    "final_charge_residual_inf": float(summary.summary_metrics["final_charge_residual_inf"]),
                    "final_vortex_count": int(summary.summary_metrics["max_vortex_count"]),
                    "final_delta_f_over_f0": float(final_row["delta_f_over_f0"]) if "delta_f_over_f0" in final_row else None,
                    "final_qinv": float(final_row["qinv"]) if "qinv" in final_row else None,
                }
            )

    reference = max(raw_results, key=lambda row: (int(row["nx"]) * int(row["ny"]), -float(row["dt"])))
    comparisons = [
        RefinementComparison(
            **row,
            delta_mean_abs2_vs_reference=abs(float(row["final_mean_abs2"]) - float(reference["final_mean_abs2"])),
            delta_charge_residual_inf_vs_reference=abs(
                float(row["final_charge_residual_inf"]) - float(reference["final_charge_residual_inf"])
            ),
            delta_delta_f_over_f0_vs_reference=(
                abs(float(row["final_delta_f_over_f0"]) - float(reference["final_delta_f_over_f0"]))
                if row["final_delta_f_over_f0"] is not None and reference["final_delta_f_over_f0"] is not None
                else None
            ),
            delta_qinv_vs_reference=(
                abs(float(row["final_qinv"]) - float(reference["final_qinv"]))
                if row["final_qinv"] is not None and reference["final_qinv"] is not None
                else None
            ),
        )
        for row in raw_results
    ]

    comparison_csv_path = destination / "comparison_table.csv"
    comparison_json_path = destination / "comparison_table.json"
    write_csv(comparison_csv_path, [asdict(row) for row in comparisons])
    write_json(
        comparison_json_path,
        {
            "base_config_path": str(config_source),
            "output_dir": str(destination),
            "reference_case_id": str(reference["case_id"]),
            "mesh_levels": [_mesh_label(nx, ny) for nx, ny in mesh_levels],
            "dt_levels": dt_levels,
            "results": [asdict(row) for row in comparisons],
        },
    )

    return RefinementSummary(
        status="success",
        base_config_path=str(config_source),
        output_dir=str(destination),
        comparison_csv_path=str(comparison_csv_path),
        comparison_json_path=str(comparison_json_path),
        reference_case_id=str(reference["case_id"]),
        case_count=len(comparisons),
        mesh_levels=[_mesh_label(nx, ny) for nx, ny in mesh_levels],
        dt_levels=dt_levels,
    )
