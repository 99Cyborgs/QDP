# Phase-1 Runtime Acceptance

This document defines the supported operational surface for the phase-1 TDGL-RF runtime on `mainline` deterministic work.

## Supported capabilities

- Deterministic 2D thin-film TDGL forward runs on structured Cartesian grids with nonperiodic boundaries
- `strip`, `strip_with_moat`, `strip_with_hole`, and connected `custom_mask` geometries
- Prescribed DC and RF vector-potential forcing profiles supported by the phase-1 config schema
- Gauge-invariant link-variable operators, scalar-potential solve with zero-mean gauge fixing, and IMEX stepping through the SciPy backend
- Run-directory creation, status tracking, provenance capture, HDF5 checkpoints / field snapshots, and compact diagnostics
- Observable computation for reduced run summaries, with optional persistence controlled by `output.write_observables`
- Zero-step deterministic runs for artifact, restart, and metadata sanity checks
- Small deterministic refinement sanity runs through `tdgl-rf refinement-sanity`
- Small deterministic campaign execution through `tdgl-rf run-matrix matrices/phase1_experiment_matrix_v1.csv`
- Compact campaign aggregation through `tdgl-rf summarize-campaign`

## Unsupported or explicitly out of scope

- Stochastic noise, ensemble workflows, and rare-event claims
- Inference workflows and posterior claims
- PETSc backend execution in phase-1 runtime
- Periodic boundary conditions
- Seeded-vortex initial conditions
- Observable weight profiles loaded from file
- Disconnected active masks for scalar-potential solves
- Deterministic convergence certification beyond the committed refinement sanity harness
- Broad physics-validation claims derived only from the phase-1 acceptance suite

## Observable semantics

- `output.write_observables: true`
  Compute observables and persist `observables/timeseries.csv`, `observables/events.csv`, and `observables/summary.json`.
- `output.write_observables: false`
  Compute observables in memory for status, diagnostics, and summary metadata, but do not write files under `observables/`.

## Numerical caveats

- The acceptance suite is a regression and sanity surface, not a publication-grade validation program.
- Charge residual checks are bounded, case-specific sanity thresholds. They are not proofs of asymptotic convergence.
- The refinement harness compares one mild deterministic RF-driven case across two meshes and two `dt` values. It is intended to detect coarse regressions in observable stability, not to establish an order-of-accuracy result.
- Short deterministic matrix runs are campaign-mechanism checks. They are not proposal evidence by themselves.
- Zero-step runs are accepted for workflow and metadata hardening, not for scientific interpretation.

## Required baseline tests for solver-touching changes

- `pytest tests/unit/test_linkvars.py tests/unit/test_observables.py tests/unit/test_phi_solver.py tests/unit/test_scipy_backend.py tests/unit/test_state_stepper.py`
- `pytest tests/integration/test_run_case_outputs.py tests/integration/test_d01_clean_strip.py`
- `pytest tests/acceptance`

If the change touches deterministic workflow wiring, also run:

- `pytest tests/integration/test_refinement_sanity.py`
- `tdgl-rf refinement-sanity configs/phase1_refinement_sanity.yaml`

If the change touches matrix or postprocessing workflows, also run:

- `pytest tests/unit/test_matrix_runner.py tests/integration/test_campaign_postprocess.py`
- `tdgl-rf run-matrix matrices/phase1_experiment_matrix_v1.csv`
- `tdgl-rf summarize-campaign <campaign_dir>`

## Merge criteria for phase-1 runtime PRs

- The PR scope stays within the supported phase-1 surface or explicitly updates this document to narrow or widen that surface.
- Solver semantics changes are documented in the PR summary artifact and covered by direct regression tests.
- `status.json`, `diagnostics/run_summary.json`, and returned `RunSummary` metadata remain mutually consistent on success and failure paths.
- No new production dependencies or runtime services are introduced without explicit justification.
- New campaign or proposal-facing outputs remain generated artifacts under `runs/` or another non-source output surface; they do not become implicit source-of-truth documents.
- Residual risks and unsupported regimes are called out explicitly when they remain unchanged.
