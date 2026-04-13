# E01 MM Analysis Protocol

## Model Order

Analyze in the following mandatory order:

1. `H0`: memoryless field-dependent scalar loss.
2. `H1` versus `H3` versus `H4`: compare generic metastable hidden state, quasiparticle-assisted field response, and package or EM drift.
3. `H2`: vortex candidate with geometry-constrained interpretation, only if the geometry gate passes first.

No H2 fit, discussion, or ranking is allowed before the geometry gate is satisfied.

## Drift Correction Rules

- Apply one drift rule per cooldown, not one drift rule per branch.
- Allowed drift correction sources are:
  `1.` zero-field return checkpoints,
  `2.` sham timing traces,
  `3.` package witness traces.
- Use at most an affine-in-time drift correction unless the witness channel independently justifies a fixed transfer function.
- Do not use branch-specific high-order background subtraction.
- If an allowed drift correction removes the apparent loop while also explaining the witness behavior, H4 wins.

## Metric Construction

- Build a common field grid for each cooldown before computing loop metrics.
- Use `y(B) = 1/Qi(B)` as the primary scalar.
- Compute `H_O = integral |y_up(B) - y_down(B)| dB`.
- Compute `A_O = integral (y_up(B) - y_down(B)) dB`.
- Compute `delta fr over fr` on the same field grid.
- Treat selected-field `T1` as a secondary metric tied to the same history label used for the primary loop.
- Archive both raw and drift-corrected metrics; do not overwrite the raw values.

## H0 Evaluation

- Fit the memoryless baseline first using only field value and the allowed cooldown-level drift term.
- H0 passes if it explains the primary observable, the return-to-zero checkpoints, and the sham behavior without structured branch residuals.
- If H0 passes on held-out cooldowns, terminate model escalation and mark the branch falsified.

## H1 versus H3 versus H4 Comparison

- `H1` may add no more than two free parameters beyond H0 in phase 1.
- Prefer matched parameter budgets across H1, H3, and H4 wherever possible.
- `H1` should capture retained history that survives dwell convergence and sham timing control.
- `H3` should capture lagged loss or `T1` recovery tied to field steps or quasiparticle bursts.
- `H4` should capture common-mode drift aligned with the package witness or elapsed time.
- Choose among H1, H3, and H4 using cooldown-replicated or held-out comparison, not same-trace fit quality alone.

## Cooldown Reproducibility Logic

- Minimum dataset for branch retention is three cooldowns with the required controls present.
- Preserve the branch only if the sign convention for `A_O`, the magnitude scale for `H_O`, and the branch ranking between `ZFC` and `FC` remain stable enough to distinguish from sham and witness envelopes in at least two cooldowns.
- If one cooldown is discarded, document the exclusion cause before any model ranking.
- Do not average away a failed cooldown to rescue promotion.

## Geometry Ordering Logic

- The geometry gate applies only to same-chip matched geometry or matched widths measured under the same protocol.
- For vortex promotion, require a consistent susceptibility ordering across all three minimum cooldowns.
- Ordering must be evaluated on the primary observable first and may be supported, but not replaced, by `delta fr over fr`.
- If ordering is absent or inconsistent, H2 is not eligible and the analysis remains at the generic metastable memory layer.

## Held-Out Comparison Logic

- Use leave-one-cooldown-out comparison when exactly three cooldowns are available.
- Fit model class hyperparameters on two cooldowns and score the third without retuning the model class itself.
- When within-cooldown repeated loops exist, fit the first repeat and score the second repeat with frozen settings.
- Promote a mechanism only if its held-out residuals improve materially relative to the simpler alternative and the residual structure is physically cleaner.

## Residual Inspection Rules

- Inspect residuals versus field, time, branch direction, witness channel, and cooldown identifier.
- Residual correlation with elapsed time or the witness channel is evidence against H1 and H2.
- Residual bursts localized to field steps or recovery windows are evidence for H3.
- Residual sign flips tied to geometry labels invalidate vortex ordering claims.

## Required Plots

- `1.` raw `1/Qi` versus field for `ZFC` and `FC`, with up and down branches separated,
- `2.` drift-corrected `1/Qi` versus field with the integration grid marked,
- `3.` `delta fr over fr` versus field on the same branch labels,
- `4.` selected-field `T1` versus elapsed time after field steps,
- `5.` `H_O` and `A_O` by cooldown and history label,
- `6.` target versus witness response over time,
- `7.` geometry-ordered summary plot for same-chip matched widths when available,
- `8.` held-out residual comparison for H0, H1, H3, and H4.

## Pass-Fail Gates

- `Gate 1: data completeness`
  Requires three cooldowns, sham timing control, witness coverage, return-to-zero checkpoints, and logged fixed `T_base` and `P_read`.
- `Gate 2: dwell validity`
  Requires the production dwell to satisfy the convergence rule from the measurement protocol.
- `Gate 3: H0 rejection`
  Required before any retained-history interpretation.
- `Gate 4: H1 versus H3 versus H4 competition`
  Required before any geometry-specific interpretation.
- `Gate 5: geometry gate`
  Required before H2 is even scored.
- `Gate 6: governance`
  Even after H2 passes, keep the status as a conservative vortex candidate rather than a proven mechanism.
