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

## Operational Notes

- `output.write_observables: false` means observables are still computed in memory for status and diagnostics, but no files are written under `observables/`.
- `tdgl-rf refinement-sanity configs/phase1_refinement_sanity.yaml` runs the cheap mesh/dt sanity sweep and writes `comparison_table.csv` plus `comparison_table.json`.
- `tdgl-rf run-matrix matrices/phase1_experiment_matrix_v1.csv` executes the small deterministic phase-1 matrix described in [docs/PHASE1_MATRIX_V1.md](docs/PHASE1_MATRIX_V1.md).
- `tdgl-rf summarize-campaign <campaign_dir>` converts matrix outputs into `proposal_summary.csv` and `proposal_summary.md`.

