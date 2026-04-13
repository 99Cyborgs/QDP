from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from .touchstone import TouchstoneDataset


def plot_touchstone_magnitude(
    dataset: TouchstoneDataset,
    output: str | Path,
    port_pair_index: int = 0,
) -> Path:
    """Plot the magnitude proxy for a selected Touchstone parameter pair."""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    x_values = [point.frequency_hz / 1.0e9 for point in dataset.points]
    y_values = [point.values[port_pair_index * 2] for point in dataset.points]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x_values, y_values, color="#0f4c5c", linewidth=2.0)
    ax.set_title("Touchstone Magnitude Trace")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel(f"{dataset.header.parameter.upper()} magnitude proxy")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path
