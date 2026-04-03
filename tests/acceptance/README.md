# Phase-1 Acceptance Suite

This directory holds fast deterministic acceptance checks for the phase-1 local solver baseline.

## Baseline cases

- `clean_strip`
  No-drive clean strip. Verifies the baseline Meissner state remains stable and produces the expected summary artifacts.
- `rf_driven_strip`
  Clean strip with nonzero RF forcing. Verifies the deterministic driven path produces finite observables and nontrivial current response.
- `masked_moat`
  Strip-with-moat geometry under mild forcing. Verifies masked geometries run successfully and still produce stable reduced observables.
- `disconnected_custom_mask`
  Custom mask with two disconnected active islands. Verifies the scalar-potential solve fails fast instead of attempting an ill-posed run.

## Scientific sanity checks

- `gauge_observable_invariance`
  Confirms a discrete gauge transform preserves gauge-invariant observables.
- `bounded_charge_residual`
  Confirms a short deterministic driven run keeps the charge residual within a conservative ceiling.
- `meissner_relaxation_sanity`
  Confirms a no-drive Meissner run stays vortex-free and near equilibrium.

These are acceptance and sanity checks, not full physics validation.
