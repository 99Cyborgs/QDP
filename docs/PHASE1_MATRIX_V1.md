# Phase-1 Experiment Matrix v1

`matrices/phase1_experiment_matrix_v1.csv` is the small deterministic campaign matrix for the phase-1 baseline.

## Axes

- Forcing amplitude: `a_rf in {0.05, 0.15}`
- Forcing frequency: `omega in {2.0, 4.0}`
- Geometry: `strip` and `strip_with_moat`

The matrix is intentionally limited to deterministic `phase=D` rows, a single mesh (`24x12`), and a short horizon (`n_steps=4`). It is a campaign-mechanism baseline, not a broad study.

## Base config

- Matrix rows inherit from `configs/phase1_matrix_base.yaml`
- `strip_with_moat` rows rely on the existing matrix default that inserts one centered circular moat when no explicit moat list is provided

## Execution

Run the full matrix:

```bash
tdgl-rf run-matrix matrices/phase1_experiment_matrix_v1.csv
```

Run one slice:

```bash
tdgl-rf run-matrix matrices/phase1_experiment_matrix_v1.csv --selector geometry_family=strip
```

Campaign outputs are written under `runs/campaigns/phase1_experiment_matrix_v1/<timestamp>/`.

## Proposal-facing summary

After a matrix run completes, aggregate compact inspection artifacts with:

```bash
tdgl-rf summarize-campaign runs/campaigns/phase1_experiment_matrix_v1/<timestamp>/
```

This writes `proposal_summary.csv` and `proposal_summary.md` under `proposal_artifacts/` inside the campaign directory.
