from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tdgl_rf.config.loaders import load_case_config
from tdgl_rf.exceptions import SeedRejectionError
from tdgl_rf.testing.case_configs import write_case_config
from tdgl_rf.workflows.run_case import run_simulation
from tdgl_rf.workflows.seeded_vortex_suite import (
    _canonical_sha256,
    _evaluate_seeded_provenance,
    _extract_run_payload,
    _extract_seeded_tier2_payload,
    load_seeded_vortex_experiment_suite,
    run_seeded_vortex_validation_suite,
)


def _write_suite_manifest(
    path: Path,
    *,
    canonical_cases: list[dict[str, object]],
    exercise_cases: list[dict[str, object]],
    rejection_cases: list[dict[str, object]],
    short_horizon_n_steps: int = 4,
) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "tdgl_rf.seeded_vortex_experiment_pack.v1",
                "suite_id": "test_seeded_suite",
                "claim_scope": "Deterministic same-stack seeded initialization / bounded short-horizon expectation matching and seeded input rejection taxonomy only.",
                "defaults": {
                    "horizon_contracts": {
                        "initialization_only": {
                            "n_steps": 0,
                            "sampling_policy": "initialization_surface",
                        },
                        "short_horizon": {
                            "n_steps": short_horizon_n_steps,
                            "sampling_policy": "all_observable_samples_through_n_steps",
                        },
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


def _build_canonical_case_entry(config_path: Path, case_id: str, *, case_class: str) -> dict[str, object]:
    summary = run_simulation(config_path)
    run_dir = Path(summary.run_dir)
    observed_summary, observed_final, payload_for_hash = _extract_run_payload(run_dir)
    tier2_payload = _extract_seeded_tier2_payload(run_dir)
    expected_tier2 = {
        "case_class": case_class,
        "horizon_contract": dict(tier2_payload["horizon_contract"]),
        "initialization_observables": {
            "overall_pass": True,
            "local_winding_verification": {
                "all_host_winding_match": True,
                "all_local_winding_match": True,
                "initial_total_signed_winding": tier2_payload["initialization_observables"]["local_winding_verification"]["initial_total_signed_winding"],
                "initial_total_abs_winding": tier2_payload["initialization_observables"]["local_winding_verification"]["initial_total_abs_winding"],
            },
            "core_contrast_observables": {
                "all_core_observable": True,
            },
        },
        "tier2_overall_pass": True,
    }
    if case_class == "initialization_only":
        expected_tier2["early_window_observables"] = None
    else:
        expected_tier2["early_window_observables"] = {
            "checked_sample_count": tier2_payload["early_window_observables"]["checked_sample_count"],
            "expected_vortex_count": tier2_payload["early_window_observables"]["expected_vortex_count"],
            "vortex_count_series": list(tier2_payload["early_window_observables"]["vortex_count_series"]),
            "overall_pass": True,
            "finite_observables_pass": True,
            "positive_amplitude_pass": True,
            "vortex_count_matches_expected_pass": True,
        }
    return {
        "case_id": case_id,
        "case_class": case_class,
        "config_path": str(config_path),
        "expected_summary": observed_summary,
        "expected_final_observables": observed_final,
        "expected_payload_sha256": _canonical_sha256(payload_for_hash),
        "expected_tier2": expected_tier2,
    }


def _build_exercise_case_entry(config_path: Path, case_id: str) -> dict[str, object]:
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


def test_load_seeded_vortex_experiment_suite_rejects_unknown_keys(tmp_path: Path) -> None:
    manifest_path = tmp_path / "bad_manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "tdgl_rf.seeded_vortex_experiment_pack.v1",
                "suite_id": "bad_suite",
                "claim_scope": "Deterministic same-stack only.",
                "defaults": {
                    "horizon_contracts": {
                        "initialization_only": {"n_steps": 0, "sampling_policy": "initialization_surface"},
                        "short_horizon": {"n_steps": 4, "sampling_policy": "all_observable_samples_through_n_steps"},
                    }
                },
                "canonical_cases": [],
                "exercise_cases": [],
                "rejection_cases": [
                    {
                        "case_id": "bad_reject",
                        "config_path": "missing.yaml",
                        "expected_stage": "config_validation",
                        "expected_rejection": {"code": "missing_seeds", "field_path": "physics.vortex_seeds", "seed_index": None},
                        "unexpected_key": "boom",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="schema validation failed"):
        load_seeded_vortex_experiment_suite(manifest_path)


def test_seeded_vortex_suite_flags_horizon_contract_mismatch(tmp_path: Path) -> None:
    success_config = write_case_config(
        tmp_path,
        "short_horizon_mismatch_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [{"x0": 4.0, "y0": 2.0, "winding": 1}],
            },
            "time": {"n_steps": 2},
            "output": {"write_fields": False},
        },
    )
    reject_config = write_case_config(
        tmp_path,
        "reject_missing_seeds_case",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_suite_manifest(
        tmp_path / "mismatch_manifest.yaml",
        canonical_cases=[],
        exercise_cases=[_build_exercise_case_entry(success_config, "exercise_mismatch_case")],
        rejection_cases=[
            {
                "case_id": "reject_missing",
                "config_path": str(reject_config),
                "expected_stage": "config_validation",
                "expected_rejection": {"code": "missing_seeds", "field_path": "physics.vortex_seeds", "seed_index": None},
            }
        ],
        short_horizon_n_steps=4,
    )

    result = run_seeded_vortex_validation_suite(manifest_path, output_dir=tmp_path / "suite_out")
    payload = json.loads(Path(result["results_json_path"]).read_text(encoding="utf-8"))
    mismatch_paths = {(row["artifact"], row["path"]) for row in payload["mismatch_records"]}

    assert result["status"] == "failed"
    assert ("config", "time.n_steps") in mismatch_paths
    assert ("tier2", "horizon_contract.n_steps") in mismatch_paths


def test_seeded_vortex_suite_rejection_exact_matching_detects_code_drift(tmp_path: Path) -> None:
    reject_config = write_case_config(
        tmp_path,
        "reject_wrong_code_case",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_suite_manifest(
        tmp_path / "reject_manifest.yaml",
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

    result = run_seeded_vortex_validation_suite(manifest_path, output_dir=tmp_path / "reject_out")
    payload = json.loads(Path(result["results_json_path"]).read_text(encoding="utf-8"))

    assert result["status"] == "failed"
    assert payload["mismatch_records"][0]["artifact"] == "rejection"
    assert payload["mismatch_records"][0]["path"] == "code"


def test_evaluate_seeded_provenance_flags_seed_order_drift(tmp_path: Path) -> None:
    config_path = write_case_config(
        tmp_path,
        "provenance_order_case",
        overrides={
            "physics": {
                "initial_condition": "seeded_vortices",
                "vortex_seeds": [
                    {"x0": 2.0, "y0": 2.0, "winding": 1},
                    {"x0": 6.0, "y0": 2.0, "winding": -1},
                ],
            },
            "output": {"write_fields": False},
        },
    )

    summary = run_simulation(config_path)
    provenance_payload = json.loads((Path(summary.run_dir) / "provenance.json").read_text(encoding="utf-8"))
    provenance_payload["initialization"]["configured_vortex_seeds"] = list(reversed(provenance_payload["initialization"]["configured_vortex_seeds"]))
    config = load_case_config(config_path)

    mismatches = _evaluate_seeded_provenance(
        provenance_payload,
        case_id="provenance_order_case",
        case_class="short_horizon",
        config=config,
        config_path=config_path,
    )

    assert any(mismatch["path"] == "initialization.configured_vortex_seeds" for mismatch in mismatches)


def test_seeded_vortex_suite_writes_non_claims_and_interpretation_boundary(tmp_path: Path) -> None:
    success_config = write_case_config(
        tmp_path,
        "suite_boundary_case",
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
        "suite_boundary_reject",
        overrides={
            "physics": {"initial_condition": "seeded_vortices", "vortex_seeds": []},
            "output": {"write_fields": False},
        },
    )
    manifest_path = _write_suite_manifest(
        tmp_path / "suite_manifest.yaml",
        canonical_cases=[_build_canonical_case_entry(success_config, "init_case", case_class="initialization_only")],
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

    result = run_seeded_vortex_validation_suite(manifest_path, output_dir=tmp_path / "boundary_out")
    payload = json.loads(Path(result["results_json_path"]).read_text(encoding="utf-8"))
    markdown = Path(result["results_markdown_path"]).read_text(encoding="utf-8")

    assert result["status"] == "success"
    assert payload["non_claims"]["equilibrium_preparation"] == "not established by this suite"
    assert payload["non_claims"]["long_time_dynamics"] == "not established by this suite"
    assert payload["non_claims"]["stochastic_behavior"] == "not established by this suite"
    assert payload["non_claims"]["cross_stack_portability"] == "not established by this suite"
    assert "## Interpretation Boundary" in markdown
    assert "equilibrium_preparation" in markdown
