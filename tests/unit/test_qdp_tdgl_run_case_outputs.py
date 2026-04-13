from __future__ import annotations

import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_META_MATERIALS_SRC = ROOT / "packages" / "qdp_meta_materials" / "src"
QDP_TDGL_SRC = ROOT / "packages" / "qdp_tdgl" / "src"

for path in (QDP_IO_SRC, QDP_META_MATERIALS_SRC, QDP_TDGL_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_tdgl.testing.case_configs import latest_run_dir, read_csv_rows, read_json, write_case_config
from qdp_tdgl.workflows.run_case import run_simulation


RUN_PROVENANCE_SCHEMA = ROOT / "configs" / "tdgl" / "tdgl_run_provenance.schema.json"


def test_run_simulation_appends_terminal_observable_sample(tmp_path: Path) -> None:
    config_path = write_case_config(tmp_path, "terminal_sample", overrides={"time": {"n_steps": 3, "obs_stride": 2}})

    summary = run_simulation(config_path)
    summary_path = Path(summary.observable_file_paths["summary"])
    timeseries_path = Path(summary.observable_file_paths["timeseries"])

    summary_payload = read_json(summary_path)
    rows = read_csv_rows(timeseries_path)

    assert len(rows) == 3
    assert float(rows[-1]["t"]) == 0.03
    assert summary.summary_metrics == summary_payload
    assert summary_payload["final_time"] == 0.03
    assert summary_payload["final_time"] == float(rows[-1]["t"])
    assert summary_payload["final_mean_abs2"] == float(rows[-1]["mean_abs2"])


def test_run_simulation_compute_only_observables_mode_keeps_summary_metadata(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = write_case_config(
        tmp_path,
        "compute_only_observables",
        overrides={"time": {"n_steps": 2}, "output": {"write_observables": False}},
    )

    summary = run_simulation(config_path)
    run_dir = latest_run_dir(output_root, "compute_only_observables")
    observables_dir = run_dir / "observables"
    status_payload = read_json(run_dir / "status.json")
    run_summary_payload = read_json(run_dir / "diagnostics" / "run_summary.json")
    convergence_payload = read_json(run_dir / "diagnostics" / "convergence_report.json")

    assert summary.observable_mode == "computed_only"
    assert summary.observable_file_paths == {}
    assert summary.summary_metrics["n_samples"] == 3
    assert list(observables_dir.iterdir()) == []
    assert status_payload == run_summary_payload
    assert status_payload["summary_metrics"] == summary.summary_metrics
    assert status_payload["diagnostic_file_paths"] == summary.diagnostic_file_paths
    assert convergence_payload["observable_mode"] == "computed_only"
    assert convergence_payload["key_observables"] == summary.summary_metrics


def test_seeded_run_writes_replayable_provenance_and_tier2_diagnostics(tmp_path: Path) -> None:
    output_root = tmp_path / "runs"
    config_path = write_case_config(
        tmp_path,
        "seeded_metadata",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 4},
            "output": {"write_fields": False},
        },
    )

    summary = run_simulation(config_path)
    run_dir = latest_run_dir(output_root, "seeded_metadata")
    provenance_payload = read_json(run_dir / "provenance.json")
    tier2_payload = read_json(run_dir / "diagnostics" / "seeded_vortex_tier2.json")
    schema = json.loads(RUN_PROVENANCE_SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(provenance_payload)

    assert provenance_payload["schema_version"] == "tdgl_rf.run_provenance.v3"
    assert provenance_payload["noise"]["contract_kind"] == "additive_complex_gaussian"
    assert provenance_payload["noise"]["sampling"] == "run_local_complex_standard_normal"
    assert provenance_payload["noise"]["enabled"] is False
    assert provenance_payload["config"]["source_config_path"] == str(config_path.resolve())
    assert provenance_payload["config"]["expanded_config_path"] == str((run_dir / "expanded_config.yaml").resolve())
    assert provenance_payload["config"]["output_root_dir"] == str(output_root.resolve())
    assert provenance_payload["numeric_environment"]["real_dtype"] == "float64"
    assert provenance_payload["numeric_environment"]["complex_dtype"] == "complex128"
    assert provenance_payload["initialization"]["mode"] == "seeded_vortices"
    assert provenance_payload["initialization"]["seed_resolution_policy"] == "strict_interior_fully_active_plaquette"
    assert provenance_payload["initialization"]["seed_rejection_taxonomy_version"] == "seeded_vortex_phase2_1"
    assert provenance_payload["initialization"]["resolved_vortex_seeds"][0]["plaquette_x"] == 7
    assert summary.seed_information["resolved_vortex_seeds"][0]["plaquette_x"] == 7
    assert Path(summary.diagnostic_file_paths["seeded_vortex_tier2"]).exists()
    assert tier2_payload["schema_version"] == "tdgl_rf.seeded_vortex_tier2.v2"
    assert tier2_payload["case_class"] == "short_horizon"
    assert tier2_payload["horizon_contract"]["n_steps"] == 4
    assert tier2_payload["tier2_overall_pass"] is True
