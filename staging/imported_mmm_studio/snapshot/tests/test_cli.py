from pathlib import Path

from typer.testing import CliRunner

from mmm_studio.cli import app
from mmm_studio.config import default_seed_root

runner = CliRunner()


def test_score_command_writes_json(tmp_path: Path):
    result = runner.invoke(
        app,
        [
            "score",
            "--root",
            str(default_seed_root()),
            "--profile",
            "broadband",
            "--json-out",
            str(tmp_path / "scores.json"),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "scores.json").exists()


def test_run_demo_command_writes_manifest(tmp_path: Path):
    result = runner.invoke(
        app,
        [
            "run-demo",
            "--root",
            str(default_seed_root()),
            "--output-dir",
            str(tmp_path / "demo-run"),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "demo-run" / "run_manifest.json").exists()
