# Phase-1 Validation Campaign

`matrices/phase1_validation_matrix_v1.csv` is the accepted short-horizon deterministic characterization matrix for the phase-1 baseline.

`matrices/phase1_validation_matrix_v2_long_horizon.csv` is the committed `n_steps=8` follow-on tranche. It reuses the same forcing, geometry, mesh, and deterministic-stack grid, but as of `2026-04-13` it remains flagged by the copied refinement drift limits and therefore does not widen the accepted baseline yet.

## Purpose

This campaign extends the smaller phase-1 experiment matrix into a validation-oriented local campaign. It remains intentionally small enough to run on one workstation. The accepted short-horizon tranche supplies the proposal-usable characterization surface, while the committed longer-horizon tranche is a follow-on diagnostic surface until its own gates pass.

## Axes

- Forcing amplitude: `a_rf in {0.05, 0.15}`
  Checks that the baseline remains stable under a mild-to-stronger RF drive within the currently supported regime.
- Forcing frequency: `omega in {2.0, 4.0}`
  Checks that the response is not tuned to one drive timescale.
- Geometry condition: `strip` and `strip_with_moat`
  Checks that the same deterministic runtime behaves acceptably on both a clean strip and a simple masked geometry.
- Mesh condition: `16x8` and `24x12`
  Checks that the characterization does not depend on one single mesh choice. This is a coarse robustness axis, not a convergence proof.

The accepted short-horizon campaign is a 16-row deterministic matrix with fixed `dt=0.01` and `n_steps=4`. The committed longer-horizon tranche keeps the same 16 rows and `dt=0.01` but extends the horizon to `n_steps=8`. Time-step sensitivity remains delegated to the paired refinement sanity harnesses so the matrix can hold the physical horizon fixed while still spanning a second discretization condition.

## Execution

Run the matrix alone:

```bash
tdgl-rf run-matrix matrices/phase1_validation_matrix_v1.csv
```

Generate the accepted short-horizon thresholded validation evidence bundle:

```bash
tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml
```

Run the committed longer-horizon follow-on tranche:

```bash
tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v2_long_horizon.csv validation/thresholds_long_horizon.yaml validation/reference_manifest_long_horizon.yaml configs/phase1_refinement_sanity_long_horizon.yaml
```

The validation command runs:

- the deterministic validation matrix
- campaign postprocessing
- the refinement sanity harness
- the frozen reference checks
- the deterministic reproducibility check

and then writes `validation_summary.csv`, `validation_summary.json`, and `validation_report.md` under `runs/validation/...`.

## What This Checks

- Each campaign row completes successfully.
- Final charge residuals stay within a conservative baseline threshold.
- Vortex count remains zero for the committed phase-1 deterministic surface.
- Refinement drift in selected observables stays within explicit sanity bounds.
- A frozen set of canonical deterministic runs still reproduces the committed compact payloads.
- One canonical RF-driven case reproduces exactly when run twice on the same local software stack.

As of `2026-04-13`, the longer-horizon follow-on tranche still fails the copied refinement drift limits on the `dt=0.01` rows even though its campaign, frozen-reference, and reproducibility checks pass.

## What This Does Not Check

- Asymptotic convergence order
- Stochastic robustness
- PETSc parity
- Publication-grade scientific validation
- Any inference or ensemble workflow
