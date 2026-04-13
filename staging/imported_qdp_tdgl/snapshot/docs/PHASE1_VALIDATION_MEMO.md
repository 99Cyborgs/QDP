# Phase-1 Validation Memo

## What Was Validated

- A 16-case deterministic validation campaign spanning:
  - forcing amplitude `a_rf in {0.05, 0.15}`
  - forcing frequency `omega in {2.0, 4.0}`
  - geometry conditions `strip` and `strip_with_moat`
  - mesh conditions `16x8` and `24x12`
- The committed refinement sanity harness on `configs/phase1_refinement_sanity.yaml`
- A frozen reference set of four canonical deterministic outputs
- A same-stack deterministic reproducibility check on the canonical RF-driven strip

## Metrics Checked

- Campaign row success / failure status
- Final charge residual infinity norm
- Final maximum vortex count
- Refinement drift in:
  - `final_mean_abs2`
  - `final_charge_residual_inf`
  - `final_delta_f_over_f0`
  - `final_qinv`
- Frozen reference compact payload hashes plus selected summary values
- Deterministic reproducibility of status, summary metrics, final observables, and compact payload hash

## Thresholds Used

- Campaign:
  - required campaign status `success`
  - required row status `success`
  - `final_charge_residual_inf <= 0.45`
  - `max_vortex_count == 0`
- Refinement sanity:
  - `delta_mean_abs2_vs_reference <= 5.0e-4`
  - `delta_charge_residual_inf_vs_reference <= 0.25`
  - `delta_delta_f_over_f0_vs_reference <= 2.0e-4`
  - `delta_qinv_vs_reference <= 5.0e-3`
- Reproducibility:
  - exact same-stack equality on selected summary metrics and final observables
  - matching compact payload hash

## Observed Outcome

- Validation campaign: `16/16` acceptable rows
- Worst observed campaign charge residual: `0.41763819642040456`
- Vortex count: `0` in all campaign rows
- Refinement sanity: `4/4` rows within bounds
- Worst observed refinement drifts:
  - `delta_mean_abs2_vs_reference = 0.00012398736272734023`
  - `delta_charge_residual_inf_vs_reference = 0.21251033858951696`
  - `delta_delta_f_over_f0_vs_reference = 0.00012398736272752222`
  - `delta_qinv_vs_reference = 0.0035482795776934726`
- Frozen references: `4/4` matched the committed manifest
- Reproducibility: exact same-stack match passed

## What This Does Not Establish

- Asymptotic convergence order
- Publication-grade physics validation
- Stochastic robustness or ensemble behavior
- PETSc parity
- Seeded-vortex or broader geometry support beyond the committed phase-1 surface
- Long-horizon stability claims beyond the short deterministic validation horizon

## Proposal-Usable Statement

The current deterministic phase-1 runtime can be cited as a scientifically characterized local baseline for short-horizon deterministic strip and simple masked-strip runs, with explicit numerical gates, frozen reference outputs, and exact same-stack reproducibility checks.

## Future Validation Still Required

- Longer-horizon deterministic studies
- Broader mesh and time-step studies beyond the current sanity harness
- Additional geometry families and boundary-condition regimes
- PETSc backend validation
- Stochastic / ensemble validation
- External benchmark comparison against stronger physical references
