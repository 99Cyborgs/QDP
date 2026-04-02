# TDGL-RF

Phase-1 implementation of the constrained ORNL TDGL-RF artifact pack.

Implemented in this repository:
- config-driven deterministic 2D thin-film TDGL forward solve,
- structured Cartesian grid and geometry masks,
- prescribed vector-potential forcing,
- gauge-invariant link-variable operators,
- scalar-potential solve with zero-mean gauge fixing,
- IMEX time stepping,
- run-directory creation, logging, provenance, HDF5 checkpoints, and CSV observables,
- unit and integration tests for the phase-1 kernels and clean-strip benchmark.

## Install

```bash
python -m pip install -e .[dev]
```

## Run

Validate a config:

```bash
tdgl-rf validate-config configs/d01_smoke.yaml
```

Run a deterministic case:

```bash
tdgl-rf run-case configs/d01_smoke.yaml
```

The run directory is created under `runs/<case_id>/<timestamp>/`.

