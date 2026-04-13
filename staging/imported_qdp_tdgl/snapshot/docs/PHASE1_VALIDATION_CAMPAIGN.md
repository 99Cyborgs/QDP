# Phase-1 Validation Campaign

`matrices/phase1_validation_matrix_v1.csv` is the deterministic characterization matrix for the phase-1 baseline.

## Purpose

This campaign extends the smaller phase-1 experiment matrix into a validation-oriented local campaign. It remains intentionally small enough to run on one workstation, but it exercises the committed deterministic baseline across the minimum axes needed for proposal-usable characterization.

## Axes

- Forcing amplitude: `a_rf in {0.05, 0.15}`
  Checks that the baseline remains stable under a mild-to-stronger RF drive within the currently supported regime.
- Forcing frequency: `omega in {2.0, 4.0}`
  Checks that the response is not tuned to one drive timescale.
- Geometry condition: `strip` and `strip_with_moat`
  Checks that the same deterministic runtime behaves acceptably on both a clean strip and a simple masked geometry.
- Mesh condition: `16x8` and `24x12`
  Checks that the characterization does not depend on one single mesh choice. This is a coarse robustness axis, not a convergence proof.

The campaign is a 16-row deterministic matrix with fixed `dt=0.01` and `n_steps=4`. Time-step sensitivity remains delegated to the separate refinement sanity harness so the matrix can hold the physical horizon fixed while still spanning a second discretization condition.

## Execution

Run the matrix alone:

```bash
tdgl-rf run-matrix matrices/phase1_validation_matrix_v1.csv
```

Generate the thresholded validation evidence bundle:

```bash
tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml
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

## What This Does Not Check

- Asymptotic convergence order
- Stochastic robustness
- PETSc parity
- Publication-grade scientific validation
- Any inference or ensemble workflow
