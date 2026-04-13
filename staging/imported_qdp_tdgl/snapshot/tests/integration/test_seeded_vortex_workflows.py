from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner
import yaml

from tdgl_rf.cli import app
from tdgl_rf.testing.case_configs import read_csv_rows, read_json, write_case_config
from tdgl_rf.workflows.run_case import run_simulation
from tdgl_rf.workflows.seeded_vortex_suite import (
    _canonical_sha256,
    _extract_run_payload,
    _extract_seeded_tier2_payload,
)
from tdgl_rf.workflows.validation import run_seeded_vortex_validation


def _write_suite_manifest(
    path: Path,
    *,
    canonical_cases: list[dict[str, object]],
    exercise_cases: list[dict[str, object]],
    rejection_cases: list[dict[str, object]],
) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "tdgl_rf.seeded_vortex_experiment_pack.v1",
                "suite_id": "integration_seeded_suite",
                "claim_scope": "Deterministic same-stack seeded initialization / bounded short-horizon expectation matching and seeded input rejection taxonomy only.",
                "defaults": {
                    "horizon_contracts": {
                        "initialization_only": {"n_steps": 0, "sampling_policy": "initialization_surface"},
                        "short_horizon": {"n_steps": 4, "sampling_policy": "all_observable_samples_through_n_steps"},
                    }
                },
                "canonical_cases": canonical_cases,
                "exercise_cases": exercise_cases,
                "rejection_cases": rejection_cases,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _canonical_case_entry(config_path: Path, case_id: str, *, case_class: str) -> dict[str, object]:
    summary = run_simulation(config_path)
    observed_summary, observed_final, payload_for_hash = _extract_run_payload(Path(summary.run_dir))
    tier2_payload = _extract_seeded_tier2_payload(Path(summary.run_dir))
    entry: dict[str, object] = {
        "case_id": case_id,
        "case_class": case_class,
        "config_path": str(config_path),
        "expected_summary": observed_summary,
        "expected_final_observables": observed_final,
        "expected_payload_sha256": _canonical_sha256(payload_for_hash),
        "expected_tier2": {
            "case_class": case_class,
            "horizon_contract": dict(tier2_payload["horizon_contract"]),
            "initialization_observables": {
                "overall_pass": True,
                "local_winding_verification": {
                    "all_host_winding_match": True,
                    "all_local_winding_match": True,
                },
                "core_contrast_observables": {
                    "all_core_observable": True,
                },
            },
            "tier2_overall_pass": True,
        },
    }
    if case_class == "initialization_only":
        entry["expected_tier2"]["early_window_observables"] = None
    else:
        entry["expected_tier2"]["early_window_observables"] = {
            "checked_sample_count": tier2_payload["early_window_observables"]["checked_sample_count"],
            "expected_vortex_count": tier2_payload["early_window_observables"]["expected_vortex_count"],
            "vortex_count_series": list(tier2_payload["early_window_observables"]["vortex_count_series"]),
            "finite_observables_pass": True,
            "positive_amplitude_pass": True,
            "vortex_count_matches_expected_pass": True,
            "overall_pass": True,
        }
    return entry


def _exercise_case_entry(config_path: Path, case_id: str) -> dict[str, object]:
    summary = run_simulation(config_path)
    tier2_payload = _extract_seeded_tier2_payload(Path(summary.run_dir))
    return {
        "case_id": case_id,
        "case_class": "short_horizon",
        "config_path": str(config_path),
        "expected_invariants": {
            "case_class": "short_horizon",
            "horizon_contract": dict(tier2_payload["horizon_contract"]),
            "initialization_observables": {
                "overall_pass": True,
                "local_winding_verification": {
                    "all_host_winding_match": True,
                    "all_local_winding_match": True,
                },
                "core_contrast_observables": {
                    "all_core_observable": True,
                },
            },
            "early_window_observables": {
                "checked_sample_count": tier2_payload["early_window_observables"]["checked_sample_count"],
                "expected_vortex_count": tier2_payload["early_window_observables"]["expected_vortex_count"],
                "vortex_count_series": list(tier2_payload["early_window_observables"]["vortex_count_series"]),
                "overall_pass": True,
            },
            "tier2_overall_pass": True,
        },
    }


def test_seeded_vortex_run_case_cli_writes_step0_vortex_observables(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "seeded_cli_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 2},
            "output": {"write_fields": False},
        },
    )
    runner = CliRunner()

    result = runner.invoke(app, ["run-case", str(config_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    rows = read_csv_rows(Path(payload["observable_file_paths"]["timeseries"]))
    status_payload = read_json(Path(payload["run_dir"]) / "status.json")

    assert len(rows) == 3
    assert float(rows[0]["vortex_count"]) == 1.0
    assert float(rows[1]["t"]) > float(rows[0]["t"])
    assert status_payload["seed_information"]["initial_condition"] == "seeded_vortices"
    assert status_payload["seed_information"]["vortex_seed_count"] == 1
    assert status_payload["summary_metrics"]["max_vortex_count"] >= 1


def test_run_seeded_vortex_validation_writes_boundary_aware_outputs(tmp_path: Path) -> None:
    canonical_config = write_case_config(
        tmp_path,
        "seeded_canonical_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 0},
            "output": {"write_fields": False},
        },
    )
    reject_config = write_case_config(
        tmp_path,
        "seeded_reject_case",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_suite_manifest(
        tmp_path / "seeded_suite.yaml",
        canonical_cases=[_canonical_case_entry(canonical_config, "init_case", case_class="initialization_only")],
        exercise_cases=[],
        rejection_cases=[
            {
                "case_id": "reject_missing",
                "config_path": str(reject_config),
                "expected_stage": "config_validation",
                "expected_rejection": {"code": "missing_seeds", "field_path": "physics.vortex_seeds", "seed_index": None},
            }
        ],
    )

    summary = run_seeded_vortex_validation(manifest_path, output_dir=tmp_path / "seeded_validation")
    payload = json.loads(Path(summary.results_json_path).read_text(encoding="utf-8"))
    markdown = Path(summary.results_markdown_path).read_text(encoding="utf-8")
    case_table = Path(summary.case_table_csv_path).read_text(encoding="utf-8")

    assert summary.status == "success"
    assert summary.case_count == 2
    assert summary.pass_count == 2
    assert payload["overall_status"] == "success"
    assert payload["suite_id"] == "integration_seeded_suite"
    assert payload["non_claims"]["equilibrium_preparation"] == "not established by this suite"
    assert payload["case_class_counts"]["initialization_only"]["passed"] == 1
    assert payload["case_class_counts"]["rejection_case"]["passed"] == 1
    assert "## Interpretation Boundary" in markdown
    assert "cross_stack_portability" in markdown
    assert "mismatch_records_json" in case_table


def test_seeded_vortex_validation_fails_on_canonical_payload_hash_mismatch(tmp_path: Path) -> None:
    canonical_config = write_case_config(
        tmp_path,
        "seeded_hash_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 0},
            "output": {"write_fields": False},
        },
    )
    reject_config = write_case_config(
        tmp_path,
        "seeded_hash_reject",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )
    canonical_entry = _canonical_case_entry(canonical_config, "init_case", case_class="initialization_only")
    canonical_entry["expected_payload_sha256"] = "0" * 64
    manifest_path = _write_suite_manifest(
        tmp_path / "hash_mismatch_suite.yaml",
        canonical_cases=[canonical_entry],
        exercise_cases=[],
        rejection_cases=[
            {
                "case_id": "reject_missing",
                "config_path": str(reject_config),
                "expected_stage": "config_validation",
                "expected_rejection": {"code": "missing_seeds", "field_path": "physics.vortex_seeds", "seed_index": None},
            }
        ],
    )

    summary = run_seeded_vortex_validation(manifest_path, output_dir=tmp_path / "hash_validation")
    payload = json.loads(Path(summary.results_json_path).read_text(encoding="utf-8"))

    assert summary.status == "failed"
    assert payload["overall_status"] == "failed"
    assert any(mismatch["path"] == "payload_sha256" for mismatch in payload["mismatch_records"])


def test_seeded_vortex_validation_fails_on_exercise_invariant_mismatch(tmp_path: Path) -> None:
    exercise_config = write_case_config(
        tmp_path,
        "seeded_exercise_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 4},
            "output": {"write_fields": False},
        },
    )
    reject_config = write_case_config(
        tmp_path,
        "seeded_exercise_reject",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )
    exercise_entry = _exercise_case_entry(exercise_config, "exercise_case")
    exercise_entry["expected_invariants"]["early_window_observables"]["vortex_count_series"] = [99, 99, 99, 99, 99]
    manifest_path = _write_suite_manifest(
        tmp_path / "exercise_mismatch_suite.yaml",
        canonical_cases=[],
        exercise_cases=[exercise_entry],
        rejection_cases=[
            {
                "case_id": "reject_missing",
                "config_path": str(reject_config),
                "expected_stage": "config_validation",
                "expected_rejection": {"code": "missing_seeds", "field_path": "physics.vortex_seeds", "seed_index": None},
            }
        ],
    )

    summary = run_seeded_vortex_validation(manifest_path, output_dir=tmp_path / "exercise_validation")
    payload = json.loads(Path(summary.results_json_path).read_text(encoding="utf-8"))

    assert summary.status == "failed"
    assert payload["overall_status"] == "failed"
    assert any(mismatch["path"] == "early_window_observables.vortex_count_series" for mismatch in payload["mismatch_records"])


def test_seeded_vortex_validation_fails_on_rejection_mismatch(tmp_path: Path) -> None:
    reject_config = write_case_config(
        tmp_path,
        "seeded_reject_wrong_code",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_suite_manifest(
        tmp_path / "reject_mismatch_suite.yaml",
        canonical_cases=[],
        exercise_cases=[],
        rejection_cases=[
            {
                "case_id": "reject_missing",
                "config_path": str(reject_config),
                "expected_stage": "config_validation",
                "expected_rejection": {"code": "unexpected_seeds", "field_path": "physics.vortex_seeds", "seed_index": None},
            }
        ],
    )

    summary = run_seeded_vortex_validation(manifest_path, output_dir=tmp_path / "reject_validation")
    payload = json.loads(Path(summary.results_json_path).read_text(encoding="utf-8"))

    assert summary.status == "failed"
    assert payload["overall_status"] == "failed"
    assert payload["mismatch_records"][0]["artifact"] == "rejection"
    assert payload["mismatch_records"][0]["path"] == "code"


def test_validate_seeded_vortices_cli_exit_semantics_and_help_text(tmp_path: Path) -> None:
    reject_config = write_case_config(
        tmp_path,
        "seeded_cli_reject",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_suite_manifest(
        tmp_path / "cli_suite.yaml",
        canonical_cases=[],
        exercise_cases=[],
        rejection_cases=[
            {
                "case_id": "reject_missing",
                "config_path": str(reject_config),
                "expected_stage": "config_validation",
                "expected_rejection": {"code": "unexpected_seeds", "field_path": "physics.vortex_seeds", "seed_index": None},
            }
        ],
    )
    runner = CliRunner()

    help_result = runner.invoke(app, ["validate-seeded-vortices", "--help"])
    fail_result = runner.invoke(
        app,
        ["validate-seeded-vortices", str(manifest_path), "--output-dir", str(tmp_path / "cli_validation")],
    )

    assert help_result.exit_code == 0
    assert "seeded initialization / short-horizon experiment-pack validation" in help_result.stdout
    assert "suite." in help_result.stdout
    assert fail_result.exit_code == 1
