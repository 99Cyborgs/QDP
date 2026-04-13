from pathlib import Path
import sys

from typer.testing import CliRunner


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
APP_SRC = ROOT / "apps" / "mmm_studio" / "src"
PACKAGE_SRC = ROOT / "packages" / "qdp_meta_materials" / "src"
for path in [QDP_IO_SRC, APP_SRC, PACKAGE_SRC]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mmm_studio.cli import app
from mmm_studio.config import default_seed_root


runner = CliRunner()


def test_score_command_writes_json(tmp_path: Path) -> None:
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


def test_run_demo_command_writes_manifest(tmp_path: Path) -> None:
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
