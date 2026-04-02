"""HDF5 field snapshot writing."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np


def _compression_name(compression: str) -> str | None:
    return None if compression == "none" else compression


def write_field_snapshot(path: str | Path, state, compression: str) -> None:
    """Persist a field snapshot to HDF5."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(destination, "w") as handle:
        comp = _compression_name(compression)
        handle.attrs["t"] = state.t
        handle.attrs["step"] = state.step
        handle.create_dataset("psi_real", data=np.real(state.psi), compression=comp)
        handle.create_dataset("psi_imag", data=np.imag(state.psi), compression=comp)
        handle.create_dataset("phi", data=state.phi, compression=comp)
        handle.create_dataset("ax", data=state.A.ax, compression=comp)
        handle.create_dataset("ay", data=state.A.ay, compression=comp)
        handle.create_dataset("ax_dot", data=state.A_dot.ax, compression=comp)
        handle.create_dataset("ay_dot", data=state.A_dot.ay, compression=comp)

