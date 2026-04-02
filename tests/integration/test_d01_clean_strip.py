from __future__ import annotations

import json
from pathlib import Path

import yaml

from tdgl_rf.workflows.run_case import run_simulation


def test_d01_clean_strip_smoke(tmp_path: Path) -> None:
    config_path = tmp_path / "d01_test.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "base_config": str(Path("configs/d01_smoke.yaml").resolve()),
                "metadata": {"case_id": "D01_test", "phase": "D", "version": "0.1.0"},
                "output": {"root_dir": str(tmp_path / "runs"), "write_fields": True, "write_observables": True, "compression": "gzip"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    summary = run_simulation(config_path)
    assert summary.status == "success"

    summary_payload = json.loads(Path(summary.observable_file_paths["summary"]).read_text(encoding="utf-8"))
    assert summary_payload["max_vortex_count"] == 0
    assert abs(summary_payload["final_mean_abs2"] - 1.0) < 1.0e-9
    assert summary_payload["final_charge_residual_inf"] < 1.0e-8

    timeseries_path = Path(summary.observable_file_paths["timeseries"])
    content = timeseries_path.read_text(encoding="utf-8")
    assert "delta_f_over_f0" in content
    assert "qinv" in content

    run_dir = Path(summary.observable_file_paths["summary"]).resolve().parents[1]
    profiling_payload = json.loads((run_dir / "diagnostics" / "profiling.json").read_text(encoding="utf-8"))
    status_payload = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    assert profiling_payload["step_count"] == 8
    assert profiling_payload["steps_per_second"] is not None
    assert "phi_solver_method_counts" in profiling_payload
    assert status_payload["status"] == "success"
