"""Checkpoint persistence for simulation states."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

from tdgl_rf.io.hdf5_writer import write_field_snapshot


def write_checkpoint(path: str | Path, state, compression: str) -> None:
    """Write a checkpoint using the HDF5 field format."""

    write_field_snapshot(path, state, compression)


def read_checkpoint(path: str | Path) -> dict[str, np.ndarray | float | int]:
    """Read a previously stored checkpoint."""

    source = Path(path)
    with h5py.File(source, "r") as handle:
        return {
            "t": float(handle.attrs["t"]),
            "step": int(handle.attrs["step"]),
            "psi": handle["psi_real"][()] + 1j * handle["psi_imag"][()],
            "phi": handle["phi"][()],
            "ax": handle["ax"][()],
            "ay": handle["ay"][()],
            "ax_dot": handle["ax_dot"][()],
            "ay_dot": handle["ay_dot"][()],
        }

