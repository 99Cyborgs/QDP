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
- `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml` runs the full deterministic validation tranche and writes `validation_summary.csv`, `validation_summary.json`, and `validation_report.md` under `runs/validation/...`.
- `tdgl-rf evidence-bundle <validation_dir>` packages one completed validation run into a compact reviewer-facing bundle under `runs/evidence/...`.
- `tdgl-rf reference-check validation/reference_manifest.yaml` regenerates the frozen canonical reference cases and checks their compact payload hashes.
- `tdgl-rf reproducibility-check configs/validation/reference_rf_strip.yaml validation/thresholds.yaml` runs the same deterministic canonical case twice and checks exact same-stack reproducibility.

## Validation Surface

- Acceptance boundary: [docs/PHASE1_ACCEPTANCE.md](docs/PHASE1_ACCEPTANCE.md)
- Validation campaign definition: [docs/PHASE1_VALIDATION_CAMPAIGN.md](docs/PHASE1_VALIDATION_CAMPAIGN.md)
- Validation interpretation memo: [docs/PHASE1_VALIDATION_MEMO.md](docs/PHASE1_VALIDATION_MEMO.md)
- Thresholds and frozen references: [validation/thresholds.yaml](validation/thresholds.yaml), [validation/reference_manifest.yaml](validation/reference_manifest.yaml)
- Evidence bundle workflow: `tdgl-rf evidence-bundle <validation_dir>`
- Phase-2 entry gate: [docs/PHASE2_ENTRY_CRITERIA.md](docs/PHASE2_ENTRY_CRITERIA.md)
- Phase-2 option ranking: [docs/PHASE2_OPTIONS_MEMO.md](docs/PHASE2_OPTIONS_MEMO.md)
- Current status and next decision point: [STATUS.md](STATUS.md)
- Repo-level validation guidance: [VALIDATION.md](VALIDATION.md)

