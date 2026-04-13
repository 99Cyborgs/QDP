# 05. Verification and validation plan

This document defines the acceptance gates that must be passed before advancing from one project phase to the next.

## 5.1 Test hierarchy

### Level 0: config and schema tests
- config loads and validates,
- illegal parameter combinations are rejected,
- base-config inheritance works,
- matrix row overrides are deterministic.

### Level 1: unit tests
- link-variable construction,
- covariant Laplacian on trivial fields,
- current computation on constant states,
- noise moment checks,
- vortex winding extraction on seeded fields,
- masking and moat boundary handling.

### Level 2: integration tests
- deterministic clean-strip run,
- deterministic pinned-strip run,
- stochastic short-ensemble run,
- synthetic observable extraction,
- inverse dry-run using synthetic data.

### Level 3: regression tests
- stored reference outputs for selected benchmarks,
- tolerance-based comparison on:
  - vortex count trajectories,
  - event counts,
  - reduced observable traces,
  - summary statistics.

## 5.2 Acceptance criteria

### A. Gauge and stencil consistency
1. **Gauge covariance test**: after an admissible discrete gauge transformation, gauge-invariant quantities change by less than `1e-10` in relative L2 norm.
2. **Constant-state Laplacian test**: with `A=0` and constant `psi`, the covariant Laplacian norm is below `1e-12`.
3. **Current sanity test**: with constant real `psi`, zero `A`, zero `phi`, both `J_s` and `J_n` are below `1e-12`.

### B. Deterministic solver integrity
4. **Charge-conservation residual**: `||div(J_s + J_n)||_inf < 1e-8` on each saved deterministic frame.
5. **No-NaN criterion**: zero NaN/inf entries in all saved fields and observables.
6. **Refinement stability**: for reference deterministic cases, key observables differ by less than `5%` between medium and fine grids.
7. **Time-step stability**: key observables differ by less than `3%` between `dt` and `dt/2` on the fine grid.

### C. Vortex detection
8. **Seeded-vortex recovery**: seeded configurations recover the correct signed vortex count exactly on the initial frame.
9. **Boundary-crossing consistency**: event counts derived from boundary crossings agree with changes in total vortex count within one event per run for deterministic tests.
10. **Refinement stability of event timing**: event timestamps shift by less than `5%` of total simulation horizon between medium and fine runs.

### D. Stochastic discretization
11. **Noise mean test**: sample mean of the real and imaginary parts of the discrete noise over `>=10^6` draws stays within `3` standard errors of zero.
12. **Noise variance test**: empirical variance is within `5%` of the target discrete variance.
13. **Seed reproducibility**: rerunning the same config with the same seed reproduces bitwise-equal reduced observables where the backend permits deterministic arithmetic; otherwise require relative agreement below `1e-12`.

### E. Inference
14. **Synthetic-truth coverage**: true values lie inside the 95% credible intervals for at least `90%` of repeated synthetic trials across the calibrated parameter subset.
15. **Posterior mean accuracy**: posterior means for the default small parameter set are within `15%` relative error on the baseline synthetic case.
16. **Posterior predictive check**: posterior predictive summary statistics overlap the observed synthetic summary statistics within one posterior standard deviation for at least `80%` of tracked summaries.

## 5.3 Reference benchmark suite

### D01 — clean strip, zero forcing
Purpose:
- sanity check that the Meissner-like state remains stable.

Pass criteria:
- no vortices created,
- observables remain flat within `1e-8`,
- current residual acceptance passes.

### D02 — clean strip, static bias field ramp
Purpose:
- verify vortex entry threshold behavior qualitatively.

Pass criteria:
- vortex entry occurs only above a threshold in the ramp,
- threshold estimate converges under refinement.

### D03 — strip with one strong defect
Purpose:
- verify pinning and depinning.

Pass criteria:
- a vortex can become trapped near the defect for an interval larger than the clean-strip transit time,
- depinning time shifts with RF amplitude.

### D04 — strip with moat / hole mask
Purpose:
- verify masked geometry handling.

Pass criteria:
- no solver leakage through masked cells,
- boundary currents remain consistent.

### S01 — stochastic clean strip
Purpose:
- verify that additive noise alone does not create pathological outputs at low noise.

Pass criteria:
- finite observables,
- event counts remain low,
- ensemble means are well-behaved.

### S02 — stochastic pinned strip
Purpose:
- establish bursty rare-event behavior in a plausible regime.

Pass criteria:
- nontrivial event table,
- stable ensemble summary statistics when doubling ensemble size from `N` to `2N`, with relative shifts below `10%` for the core summaries.

### I01 — synthetic inverse baseline
Purpose:
- verify low-dimensional inference on generated data.

Pass criteria:
- synthetic-truth coverage and posterior mean accuracy criteria pass.

## 5.4 Convergence report format
Each benchmark must emit a machine-readable report with:
- case ID
- mesh levels
- time-step levels
- key observables
- percent changes
- pass/fail
- notes

Suggested file:
`diagnostics/convergence_report.json`

## 5.5 Promotion gates

### Gate G1: deterministic complete
Required:
- D01–D04 pass.

### Gate G2: stochastic complete
Required:
- G1 plus S01–S02 pass.

### Gate G3: inference complete
Required:
- G2 plus I01 pass.

Codex must not move to the next phase unless the current gate is green.

## 5.6 Proposal-grade figure gates
Before proposal writing, the code must generate:
1. `fig_geometry_pinning.png`
2. `fig_vortex_trajectories.png`
3. `fig_observable_traces_events.png`
4. `fig_synthetic_posterior_recovery.png`

These figures are the minimal narrative evidence package.
