# Phase-1 Validation Memo

## Current Deterministic Validation Surfaces

- Accepted short-horizon tranche:
  `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml`
- Committed longer-horizon tranche:
  `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v2_long_horizon.csv validation/thresholds_long_horizon.yaml validation/reference_manifest_long_horizon.yaml configs/phase1_refinement_sanity_long_horizon.yaml`
- The short-horizon tranche is the accepted deterministic baseline.
- The longer-horizon tranche is committed and reproducible, but as of `2026-04-13` it remains flagged under the copied short-horizon refinement limits, so it does not widen the accepted baseline yet.

## Short-Horizon Tranche

- Surface:
  16 deterministic campaign rows spanning `a_rf in {0.05, 0.15}`, `omega in {2.0, 4.0}`, geometry families `strip` and `strip_with_moat`, and meshes `16x8` plus `24x12`, with `dt=0.01` and `n_steps=4`.
- Companion controls:
  `configs/phase1_refinement_sanity.yaml`, `validation/reference_manifest.yaml`, and same-stack reproducibility on `configs/validation/reference_rf_strip.yaml`.
- Thresholds:
  `final_charge_residual_inf <= 0.45`, `max_vortex_count == 0`, `delta_mean_abs2_vs_reference <= 5.0e-4`, `delta_charge_residual_inf_vs_reference <= 0.25`, `delta_delta_f_over_f0_vs_reference <= 2.0e-4`, `delta_qinv_vs_reference <= 5.0e-3`, plus exact same-stack reproducibility.
- Observed outcome:
  campaign `16/16`, worst campaign charge residual `0.41763819642040456`, vortex count `0` in all rows, refinement `4/4`, worst refinement drifts `0.00012398736272734023` for `delta_mean_abs2_vs_reference`, `0.21251033858951696` for `delta_charge_residual_inf_vs_reference`, `0.00012398736272752222` for `delta_delta_f_over_f0_vs_reference`, and `0.0035482795776934726` for `delta_qinv_vs_reference`, frozen references `4/4`, reproducibility `pass`.

## Longer-Horizon Tranche

- Surface:
  the same 16 deterministic campaign rows and forcing / geometry grid as the accepted tranche, but with `n_steps=8`.
- Companion controls:
  `configs/phase1_refinement_sanity_long_horizon.yaml`, `validation/reference_manifest_long_horizon.yaml`, and same-stack reproducibility on `configs/validation/reference_rf_strip_long_horizon.yaml`.
- Threshold posture:
  the numeric campaign, refinement, and reproducibility gates are copied unchanged from the short-horizon tranche.
- Observed outcome on `2026-04-13`:
  campaign `16/16`, worst campaign charge residual `0.36470134240585783`, vortex count `0` in all rows, frozen references `4/4`, reproducibility `pass`, but refinement only `2/4`.
- Flagged refinement rows:
  `phase1_refinement_sanity_long_horizon_m16x8_dt0p01` and `phase1_refinement_sanity_long_horizon_m24x12_dt0p01`.
- Largest observed refinement drifts:
  `delta_mean_abs2_vs_reference = 0.00023144314499368157`, `delta_charge_residual_inf_vs_reference = 0.12930967507571614`, `delta_delta_f_over_f0_vs_reference = 0.00023144314499370434`, and `delta_qinv_vs_reference = 0.018298939107024535`.
- Interpretation:
  the committed `n_steps=8` tranche is a real deterministic surface, but under the copied short-horizon limits it remains a flagged strengthening run, not a widened accepted baseline.

## What This Does Not Establish

- Asymptotic convergence order
- Publication-grade physics validation
- Stochastic robustness or ensemble behavior
- PETSc parity
- Seeded-vortex or broader geometry support beyond the committed phase-1 surface
- Long-horizon and very-long-time stability beyond the committed `n_steps=8` deterministic horizon

## Proposal-Usable Statement

The current deterministic phase-1 runtime can still be cited as a scientifically characterized local baseline for short-horizon deterministic strip and simple masked-strip runs, with explicit numerical gates, frozen reference outputs, and exact same-stack reproducibility checks.

The committed longer-horizon `n_steps=8` tranche is not proposal-usable yet because the copied refinement gate still flags `2/4` rows even though campaign, frozen-reference, and reproducibility checks pass.

## Future Validation Still Required

- Decide whether the `n_steps=8` longer-horizon tranche becomes accepted, is narrowed, or remains advisory after its refinement drift is understood
- Broader mesh and time-step studies beyond the current sanity harness
- Additional geometry families and boundary-condition regimes
- PETSc backend validation
- Stochastic / ensemble validation
- External benchmark comparison against stronger physical references
