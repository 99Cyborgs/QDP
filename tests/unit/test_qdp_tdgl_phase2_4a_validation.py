from __future__ import annotations

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_META_MATERIALS_SRC = ROOT / "packages" / "qdp_meta_materials" / "src"
QDP_TDGL_SRC = ROOT / "packages" / "qdp_tdgl" / "src"

for path in (QDP_IO_SRC, QDP_META_MATERIALS_SRC, QDP_TDGL_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from qdp_tdgl.workflows.phase2_4a_validation import (
    _collect_exact_mismatches,
    _compare_indexed_surfaces,
    _member_provenance_projection,
    load_phase2_4a_validation_manifest,
)


PHASE2_4A_VALIDATION_MANIFEST = (
    ROOT / "configs" / "validation" / "tdgl" / "seeded_vortex_phase2_4a_validation_manifest.yaml"
).resolve()


def _committed_expected_results() -> dict[str, object]:
    payload = yaml.safe_load(PHASE2_4A_VALIDATION_MANIFEST.read_text(encoding="utf-8"))
    return payload["expected_results"]


def test_load_phase2_4a_validation_manifest_committed_surface() -> None:
    manifest = load_phase2_4a_validation_manifest(PHASE2_4A_VALIDATION_MANIFEST)

    assert manifest.schema_version == "tdgl_rf.seeded_vortex_phase2_4a_validation.v1"
    assert manifest.validation_id == "seeded_vortex_phase2_4a_same_stack"
    assert Path(manifest.experiment_pack_path) == (
        ROOT / "configs" / "validation" / "tdgl" / "seeded_vortex_phase2_4a_experiment_pack.yaml"
    ).resolve()
    assert len(manifest.expected_parameter_points) == 2
    assert len(manifest.expected_members) == 6


def test_phase2_4a_top_level_mismatch_is_reported_at_exact_path() -> None:
    expected = _committed_expected_results()["top_level"]
    observed = dict(expected)
    observed["run_count"] = 7

    mismatches = _collect_exact_mismatches(
        expected,
        observed,
        surface="top_level",
        subject_id="overall",
    )

    assert len(mismatches) == 1
    assert mismatches[0]["path"] == "run_count"
    assert mismatches[0]["assessment"] == "value_mismatch"


def test_phase2_4a_parameter_point_aggregate_mismatch_is_reported() -> None:
    expected_points = _committed_expected_results()["parameter_points"]
    observed_points = [dict(point) for point in expected_points]
    observed_points[0] = dict(observed_points[0])
    observed_points[0]["aggregates"] = {
        "early_window.mean_abs2_final": {
            **observed_points[0]["aggregates"]["early_window.mean_abs2_final"],
            "mean": 0.0,
        }
    }

    _, mismatches = _compare_indexed_surfaces(
        surface="parameter_point",
        subject_label="parameter-point",
        expected_items=expected_points,
        observed_items=observed_points,
        identity_key="param_set_hash",
    )

    assert any(
        record["subject_id"] == "22c77fcc8895b7c6"
        and record["path"] == "aggregates.early_window.mean_abs2_final.mean"
        for record in mismatches
    )


def test_phase2_4a_parameter_point_robustness_mismatch_is_reported() -> None:
    expected_points = _committed_expected_results()["parameter_points"]
    observed_points = [dict(point) for point in expected_points]
    observed_points[1] = dict(observed_points[1])
    observed_points[1]["robustness_summary"] = dict(observed_points[1]["robustness_summary"])
    observed_points[1]["robustness_summary"]["observables"] = {
        "early_window.mean_abs2_final": {
            **observed_points[1]["robustness_summary"]["observables"]["early_window.mean_abs2_final"],
            "coefficient_of_variation_defined": False,
        }
    }

    _, mismatches = _compare_indexed_surfaces(
        surface="parameter_point",
        subject_label="parameter-point",
        expected_items=expected_points,
        observed_items=observed_points,
        identity_key="param_set_hash",
    )

    assert any(
        record["subject_id"] == "7e25b35f64dc7088"
        and record["path"] == "robustness_summary.observables.early_window.mean_abs2_final.coefficient_of_variation_defined"
        for record in mismatches
    )


def test_phase2_4a_member_provenance_mismatch_is_reported() -> None:
    expected_members = _committed_expected_results()["members"]
    observed_members = [dict(member) for member in expected_members]
    observed_members[0] = dict(observed_members[0])
    observed_members[0]["provenance"] = yaml.safe_load(yaml.safe_dump(observed_members[0]["provenance"]))
    observed_members[0]["provenance"]["initialization"]["resolved_vortex_seeds"][0]["plaquette_x"] = 99

    _, mismatches = _compare_indexed_surfaces(
        surface="member",
        subject_label="member",
        expected_items=expected_members,
        observed_items=observed_members,
        identity_key="run_id",
    )

    assert any(
        record["subject_id"] == "seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0"
        and record["path"] == "provenance.initialization.resolved_vortex_seeds[0].plaquette_x"
        for record in mismatches
    )


def test_member_provenance_projection_excludes_path_dependent_fields() -> None:
    baseline = {
        "schema_version": "tdgl_rf.run_provenance.v3.3",
        "experiment": {
            "base_case_hash": "abc",
            "manifest_path": "C:/different/path",
        },
        "seeds": {
            "master_seed": 1234,
            "noise_seed": 42,
            "initial_condition": "seeded_vortices",
            "vortex_seed_count": 1,
        },
        "noise": {
            "enabled": True,
            "strength": 0.05,
            "seed": 42,
            "contract_kind": "additive_complex_gaussian",
            "sampling": "run_local_complex_standard_normal",
        },
        "determinism": {
            "noise_enabled": True,
            "deterministic_expected": False,
            "master_seed": 1234,
            "noise_seed": 42,
            "pinning_seed": None,
            "reproducibility_scope": "same-stack seeded stochastic",
        },
        "ensemble": {
            "mode": "stochastic_ensemble",
            "member_count": 3,
            "member_index": 0,
            "noise_seed": 42,
            "master_seed": 1234,
            "parent_manifest_hash": "manifest",
        },
        "initialization": {
            "mode": "seeded_vortices",
            "configured_vortex_seeds": [
                {"seed_index": 0, "winding": 1, "x0": 6.0, "y0": 3.0, "core_radius": None}
            ],
            "resolved_vortex_seeds": [
                {"seed_index": 0, "winding": 1, "x0": 6.0, "y0": 3.0, "core_radius": 0.25, "plaquette_x": 11, "plaquette_y": 5}
            ],
            "seed_resolution_policy": "strict_interior_fully_active_plaquette",
            "seed_rejection_taxonomy_version": "seeded_vortex_phase2_1",
        },
        "config": {
            "output_root_dir": "C:/run/a",
            "source_config_path": "C:/run/a/source.yaml",
        },
        "execution": {
            "repo_root": "C:/repo/a",
            "hostname": "host-a",
        },
    }
    shifted = yaml.safe_load(yaml.safe_dump(baseline))
    shifted["config"]["output_root_dir"] = "D:/other/run"
    shifted["config"]["source_config_path"] = "D:/other/source.yaml"
    shifted["execution"]["repo_root"] = "D:/other/repo"
    shifted["execution"]["hostname"] = "host-b"

    assert _member_provenance_projection(baseline) == _member_provenance_projection(shifted)
