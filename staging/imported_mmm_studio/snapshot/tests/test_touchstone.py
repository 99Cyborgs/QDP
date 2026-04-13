from pathlib import Path

from mmm_studio.rf.plotting import plot_touchstone_magnitude
from mmm_studio.rf.touchstone import parse_touchstone


def test_parse_touchstone_and_plot(tmp_path: Path):
    path = tmp_path / "example.s2p"
    path.write_text(
        "# GHZ S MA R 50\n1.0 0.10 0 0.00 0 0.00 0 0.20 0\n2.0 0.15 0 0.00 0 0.00 0 0.25 0\n",
        encoding="utf-8",
    )

    dataset = parse_touchstone(path)
    plot_path = plot_touchstone_magnitude(dataset, tmp_path / "touchstone.png")

    assert dataset.ports == 2
    assert len(dataset.points) == 2
    assert plot_path.exists()
