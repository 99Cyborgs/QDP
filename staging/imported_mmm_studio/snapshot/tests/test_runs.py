from pathlib import Path

from mmm_studio.runs import compare_runs, execute_demo_run, load_run_manifest


def test_execute_demo_run_persists_artifacts(tmp_path: Path):
    manifest = execute_demo_run(output_dir=tmp_path / "run-a", profile="broadband")

    assert manifest.top_candidate_id is not None
    assert (tmp_path / "run-a" / "run_manifest.json").exists()
    assert (tmp_path / "run-a" / "simulation_preflight.json").exists()
    assert (tmp_path / "run-a" / "meep_geometry_scaffold.json").exists()


def test_compare_runs(tmp_path: Path):
    left = execute_demo_run(output_dir=tmp_path / "run-left", profile="broadband")
    right = execute_demo_run(output_dir=tmp_path / "run-right", profile="manufacturability_aware")
    comparison = compare_runs(tmp_path / "run-left", tmp_path / "run-right")

    assert comparison.left_run_id == left.run_id
    assert comparison.right_run_id == right.run_id
    assert "top_score" in comparison.score_deltas
    assert comparison.top_candidate_shift["right"] == right.top_candidate_id


def test_load_run_manifest_from_directory(tmp_path: Path):
    manifest = execute_demo_run(output_dir=tmp_path / "run-manifest", profile="broadband")
    loaded = load_run_manifest(tmp_path / "run-manifest")
    assert loaded.run_id == manifest.run_id
