"""Campaign postprocessing for compact proposal-facing summaries."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qdp_io.serialization import write_csv, write_json
from qdp_tdgl.workflows.run_matrix import load_experiment_matrix


@dataclass(frozen=True)
class CampaignArtifactSummary:
    status: str
    campaign_dir: str
    output_dir: str
    summary_csv_path: str
    summary_markdown_path: str
    processed_row_count: int
    skipped_row_count: int


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_last_csv_row(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-1] if rows else None


def _row_lookup(matrix_path: Path) -> dict[int, dict[str, Any]]:
    return {row.row_index: row.values for row in load_experiment_matrix(matrix_path)}


def _campaign_rows(campaign_dir: Path) -> list[dict[str, Any]]:
    state = _read_json(campaign_dir / "campaign_state.json")
    return list(state.get("rows", []))


def _row_artifact_record(row_payload: dict[str, Any], matrix_values: dict[str, Any]) -> dict[str, Any] | None:
    run_dir_value = row_payload.get("run_dir")
    if row_payload.get("status") != "success" or not run_dir_value:
        return None

    run_dir = Path(run_dir_value)
    run_summary = _read_json(run_dir / "diagnostics" / "run_summary.json")
    summary_metrics = dict(run_summary.get("summary_metrics", {}))
    final_row = _read_last_csv_row(run_dir / "observables" / "timeseries.csv")

    record: dict[str, Any] = {
        "row_index": int(row_payload["row_index"]),
        "case_id": str(row_payload["case_id"]),
        "phase": str(row_payload["phase"]),
        "geometry_family": matrix_values.get("geometry_family"),
        "a_rf": matrix_values.get("a_rf"),
        "omega": matrix_values.get("omega"),
        "nx": matrix_values.get("nx"),
        "ny": matrix_values.get("ny"),
        "dt": matrix_values.get("dt"),
        "wall_clock_seconds": run_summary.get("wall_clock_seconds"),
        "final_mean_abs2": summary_metrics.get("final_mean_abs2"),
        "final_charge_residual_inf": summary_metrics.get("final_charge_residual_inf"),
        "max_vortex_count": summary_metrics.get("max_vortex_count"),
        "run_dir": str(run_dir),
        "run_summary_path": str(run_dir / "diagnostics" / "run_summary.json"),
    }
    if final_row is not None:
        record["final_delta_f_over_f0"] = float(final_row["delta_f_over_f0"]) if "delta_f_over_f0" in final_row else None
        record["final_qinv"] = float(final_row["qinv"]) if "qinv" in final_row else None
    else:
        record["final_delta_f_over_f0"] = None
        record["final_qinv"] = None
    return record


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    header = (
        "| case_id | geometry | a_rf | omega | mesh | dt | final_mean_abs2 | charge_residual_inf | delta_f_over_f0 | qinv | max_vortex_count |\n"
        "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    )
    body_lines = []
    for row in rows:
        mesh = f"{row['nx']}x{row['ny']}"
        body_lines.append(
            "| {case_id} | {geometry_family} | {a_rf:.3f} | {omega:.3f} | {mesh} | {dt:.4f} | {final_mean_abs2:.6f} | {final_charge_residual_inf:.6f} | {final_delta_f_over_f0} | {final_qinv} | {max_vortex_count} |".format(
                case_id=row["case_id"],
                geometry_family=row["geometry_family"],
                a_rf=float(row["a_rf"]),
                omega=float(row["omega"]),
                mesh=mesh,
                dt=float(row["dt"]),
                final_mean_abs2=float(row["final_mean_abs2"]),
                final_charge_residual_inf=float(row["final_charge_residual_inf"]),
                final_delta_f_over_f0=(
                    f"{float(row['final_delta_f_over_f0']):.6f}" if row["final_delta_f_over_f0"] is not None else "n/a"
                ),
                final_qinv=(f"{float(row['final_qinv']):.6f}" if row["final_qinv"] is not None else "n/a"),
                max_vortex_count=int(row["max_vortex_count"]),
            )
        )
    intro = [
        "# Campaign Summary",
        "",
        "This report is a compact inspection aid for phase-1 deterministic matrix runs.",
        "It records run outputs as observed; it is not a claim of convergence or broader physics validation.",
        "",
    ]
    return "\n".join(intro) + header + "\n".join(body_lines) + "\n"


def summarize_campaign(campaign_dir: str | Path, output_dir: str | Path | None = None) -> CampaignArtifactSummary:
    """Aggregate one matrix campaign into compact CSV and Markdown artifacts."""

    campaign_path = Path(campaign_dir).resolve()
    state = _read_json(campaign_path / "campaign_state.json")
    matrix_path = Path(state["matrix_path"]).resolve()
    lookup = _row_lookup(matrix_path)

    destination = Path(output_dir).resolve() if output_dir is not None else (campaign_path / "proposal_artifacts").resolve()
    destination.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    skipped = 0
    for row_payload in _campaign_rows(campaign_path):
        matrix_values = lookup.get(int(row_payload["row_index"]))
        if matrix_values is None:
            skipped += 1
            continue
        record = _row_artifact_record(row_payload, matrix_values)
        if record is None:
            skipped += 1
            continue
        rows.append(record)

    rows.sort(key=lambda row: (str(row["geometry_family"]), float(row["omega"]), float(row["a_rf"]), str(row["case_id"])))

    summary_csv_path = destination / "proposal_summary.csv"
    summary_markdown_path = destination / "proposal_summary.md"
    write_csv(summary_csv_path, rows)
    summary_markdown_path.write_text(_markdown_table(rows), encoding="utf-8")
    write_json(
        destination / "proposal_summary.json",
        {
            "campaign_dir": str(campaign_path),
            "matrix_path": str(matrix_path),
            "processed_row_count": len(rows),
            "skipped_row_count": skipped,
            "rows": rows,
        },
    )

    return CampaignArtifactSummary(
        status="success",
        campaign_dir=str(campaign_path),
        output_dir=str(destination),
        summary_csv_path=str(summary_csv_path),
        summary_markdown_path=str(summary_markdown_path),
        processed_row_count=len(rows),
        skipped_row_count=skipped,
    )

