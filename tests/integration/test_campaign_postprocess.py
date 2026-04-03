from __future__ import annotations

import csv
from pathlib import Path

import yaml

from tdgl_rf.testing.case_configs import base_case_payload, read_csv_rows
from tdgl_rf.workflows.postprocess import summarize_campaign
from tdgl_rf.workflows.run_matrix import run_experiment_matrix


def _write_base_config(path: Path) -> None:
    payload = base_case_payload("campaign_base", path.parent / "runs")
    payload["output"]["root_dir"] = "runs"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_matrix(path: Path, base_config_ref: str) -> None:
    rows = [
        {
            "case_id": "P01",
            "phase": "D",
            "base_config": base_config_ref,
            "geometry_family": "strip",
            "nx": 16,
            "ny": 8,
            "pinning_model": "none",
            "pinning_mu": 0.0,
            "pinning_sigma": 0.0,
            "pinning_lcorr": 0.0,
            "defect_count": 0,
            "b_dc": 0.0,
            "a_rf": 0.10,
            "omega": 2.0,
            "gamma_noise": 0.0,
            "dt": 0.01,
            "n_steps": 2,
            "ensemble_size": 1,
            "obs_stride": 1,
            "field_stride": 2,
            "goal": "proposal summary strip",
            "success_metric": "completes",
            "promotion_rule": "gate:G1",
            "notes": "strip row",
        },
        {
            "case_id": "P02",
            "phase": "D",
            "base_config": base_config_ref,
            "geometry_family": "strip_with_moat",
            "nx": 16,
            "ny": 8,
            "pinning_model": "none",
            "pinning_mu": 0.0,
            "pinning_sigma": 0.0,
            "pinning_lcorr": 0.0,
            "defect_count": 0,
            "b_dc": 0.0,
            "a_rf": 0.15,
            "omega": 4.0,
            "gamma_noise": 0.0,
            "dt": 0.01,
            "n_steps": 2,
            "ensemble_size": 1,
            "obs_stride": 1,
            "field_stride": 2,
            "goal": "proposal summary moat",
            "success_metric": "completes",
            "promotion_rule": "gate:G1",
            "notes": "moat row",
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_campaign_postprocess_writes_csv_and_markdown(tmp_path: Path) -> None:
    base_path = tmp_path / "campaign_base.yaml"
    matrix_path = tmp_path / "campaign_matrix.csv"
    _write_base_config(base_path)
    _write_matrix(matrix_path, "campaign_base.yaml")

    campaign = run_experiment_matrix(matrix_path)
    summary = summarize_campaign(campaign.campaign_dir, output_dir=tmp_path / "proposal_artifacts")

    rows = read_csv_rows(Path(summary.summary_csv_path))
    markdown = Path(summary.summary_markdown_path).read_text(encoding="utf-8")

    assert summary.status == "success"
    assert summary.processed_row_count == 2
    assert summary.skipped_row_count == 0
    assert len(rows) == 2
    assert rows[0]["case_id"] in {"P01", "P02"}
    assert "| case_id | geometry | a_rf | omega | mesh | dt |" in markdown
    assert "P01" in markdown
    assert "P02" in markdown
