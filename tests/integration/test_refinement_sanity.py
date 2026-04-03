from __future__ import annotations

from pathlib import Path

import pytest

from tdgl_rf.testing.case_configs import read_csv_rows, read_json, write_case_config
from tdgl_rf.workflows.refinement import run_refinement_sanity


def test_refinement_sanity_writes_four_case_comparison(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "refinement_base",
        overrides={
            "forcing": {"a_rf": 0.15, "omega": 4.0, "phase": 0.2},
            "time": {"n_steps": 4},
            "output": {"write_fields": False},
        },
    )

    summary = run_refinement_sanity(config_path, output_dir=tmp_path / "refinement_outputs")
    rows = read_csv_rows(Path(summary.comparison_csv_path))
    payload = read_json(Path(summary.comparison_json_path))

    assert summary.status == "success"
    assert summary.case_count == 4
    assert summary.mesh_levels == ["16x8", "24x12"]
    assert summary.dt_levels == [0.01, 0.005]
    assert len(rows) == 4
    assert payload["reference_case_id"] == summary.reference_case_id

    reference = next(row for row in rows if row["case_id"] == summary.reference_case_id)
    assert float(reference["delta_mean_abs2_vs_reference"]) == pytest.approx(0.0)
    assert float(reference["delta_charge_residual_inf_vs_reference"]) == pytest.approx(0.0)
    assert Path(reference["run_dir"]).exists()
