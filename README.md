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

Run a deterministic seeded-vortex example:

```bash
tdgl-rf run-case configs/phase2_seeded_single_vortex.yaml
```

Run a deterministic seeded-vortex experiment harness:

```bash
tdgl-rf run-experiment validation/seeded_vortex_phase2_3_experiment_pack.yaml
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
- seeded-vortex runs write replay-oriented `provenance.json` metadata that conforms to `configs/tdgl_run_provenance.schema.json`.
- seeded-vortex runs also write `diagnostics/seeded_vortex_tier2.json` with explicit `initialization_only` or `short_horizon` horizon contracts plus claim-bounded initialization/early-window observables.
- `tdgl-rf validate-seeded-vortices validation/seeded_vortex_phase2_2_manifest.yaml` runs the deterministic same-stack seeded experiment-pack suite, including frozen canonical references, invariant-only exercise cases, and first-class rejection-taxonomy checks.
- `tdgl-rf run-experiment <manifest>` dispatches Phase-2.2 suite manifests unchanged, runs Phase-2.3 experiment-pack manifests as deterministic same-stack sweep/repetition harnesses over the committed Tier-2 observable surface, and executes Phase-2.4A v4 manifests as sequential fail-fast stochastic ensembles with staged promotion, strict full-member aggregation, and replay-oriented provenance.
- Phase-2.4A runtime support is an implementation capability only. It is not a scientific validation claim, and the repo does not currently define grounded acceptance guardrails for `noise.strength` beyond the explicit runtime contract `noise.enabled=true`, `noise.seed`, and `noise.strength > 0`.

## Validation Surface

- Acceptance boundary: [docs/PHASE1_ACCEPTANCE.md](docs/PHASE1_ACCEPTANCE.md)
- Validation campaign definition: [docs/PHASE1_VALIDATION_CAMPAIGN.md](docs/PHASE1_VALIDATION_CAMPAIGN.md)
- Validation interpretation memo: [docs/PHASE1_VALIDATION_MEMO.md](docs/PHASE1_VALIDATION_MEMO.md)
- Thresholds and frozen references: [validation/thresholds.yaml](validation/thresholds.yaml), [validation/reference_manifest.yaml](validation/reference_manifest.yaml)
- Evidence bundle workflow: `tdgl-rf evidence-bundle <validation_dir>`
- Phase-2 entry gate: [docs/PHASE2_ENTRY_CRITERIA.md](docs/PHASE2_ENTRY_CRITERIA.md)
- Phase-2 option ranking: [docs/PHASE2_OPTIONS_MEMO.md](docs/PHASE2_OPTIONS_MEMO.md)
- Phase-2 seeded-vortex tranche: [docs/PHASE2_SEEDED_VORTICES.md](docs/PHASE2_SEEDED_VORTICES.md)
- Phase-2.2 seeded experiment pack: [docs/PHASE2_2_SEEDED_EXPERIMENT_PACK.md](docs/PHASE2_2_SEEDED_EXPERIMENT_PACK.md)
- Seeded-run provenance schema: [configs/tdgl_run_provenance.schema.json](configs/tdgl_run_provenance.schema.json)
- Seeded Tier-2 schema: [configs/seeded_vortex_tier2.schema.json](configs/seeded_vortex_tier2.schema.json)
- Seeded experiment-suite manifest: [validation/seeded_vortex_phase2_2_manifest.yaml](validation/seeded_vortex_phase2_2_manifest.yaml)
- Current status and next decision point: [STATUS.md](STATUS.md)
- Repo-level validation guidance: [VALIDATION.md](VALIDATION.md)

