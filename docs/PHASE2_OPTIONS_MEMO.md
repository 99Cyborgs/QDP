# Phase-2 Options Memo

## Decision Context

Deterministic phase-1 validation now establishes a bounded local short-horizon baseline with explicit thresholds, frozen references, and same-stack reproducibility. A first committed `n_steps=8` longer-horizon tranche also now exists; it passes campaign, frozen-reference, and reproducibility checks, but still fails the copied refinement drift limits at `2/4`. The next decision is still not whether to add more features immediately, but which phase-2 direction best uses the accepted baseline without overstating what the current evidence proves.

Current branch note: seeded-vortex initialization has now been implemented as the first bounded phase-2 tranche. The ranking below remains useful as planning context for what should follow or what still lacks broader validation after the flagged longer-horizon follow-on run.

## Option Comparison

| Option | Why it matters | Dependencies | Risks | Expected scientific value | Implementation cost / complexity | Prioritize next |
| --- | --- | --- | --- | --- | --- | --- |
| Longer-horizon validation | Extends confidence beyond the current short deterministic horizon and tests whether the validated baseline stays usable once transients have more time to develop. | Existing deterministic baseline, new horizon definitions, updated thresholds, additional runtime budget. | May expose drift or threshold pressure that forces baseline revisions before any new capability work. | High leverage because it strengthens every later option. | Low-to-medium. Mostly validation and reporting work, not new solver surface. | **Yes** |
| Seeded vortex initial conditions | Opens a controlled deterministic path into vortex-dynamics studies without immediately adding stochastic variance. | Deterministic baseline, initialization schema, new reference cases, new acceptance checks for intended vortex content. | Initialization artifacts can masquerade as physics and contaminate conclusions if the control surface is weak. | Medium-to-high for targeted mechanism studies. | Medium. New deterministic capability plus new validation burden. | Conditional, after longer-horizon validation |
| PETSc parity / scale-up | Enables larger meshes and longer runs, and creates a path to more realistic studies once backend agreement is demonstrated. | Deterministic parity cases, backend-specific environment capture, parity tolerances, likely more engineering effort. | High engineering risk, platform burden, and parity-debug cost before there is a broader validated science surface to exploit. | Medium as immediate science, high as infrastructure. | High. Backend work plus validation work. | Conditional, but not first by default |
| Stochastic noise / ensembles | Most directly expands toward realistic fluctuation-driven behavior and statistical claims. | Stable deterministic baseline, seed contract, stochastic acceptance surface, ensemble summaries, likely more compute scale. | Highest risk of confounding implementation errors with stochastic variance; reproducibility and interpretation get harder immediately. | High if the surrounding controls exist. | High. New capability, new validation model, new reporting semantics. | No, not before the deterministic baseline is extended further |

## Ranked Recommendation

1. **Longer-horizon validation**
   This is the highest-leverage next step because it hardens the deterministic control surface that every other option depends on. It also stays closest to the current validated baseline and avoids opening a new feature class before the present short-horizon evidence is better understood.

2. **Seeded vortex initial conditions**
   This is the most defensible deterministic feature expansion after longer-horizon validation. It adds scientifically meaningful structure while keeping variance sources controlled and keeping the evidence problem smaller than stochastic ensembles or backend scale-up.

3. **PETSc parity / scale-up**
   This should follow once there is a clearer target surface worth scaling. It is valuable infrastructure, but the engineering cost is high and the science return is limited until the deterministic regime itself is extended.

4. **Stochastic noise / ensembles**
   This should be deferred until the deterministic baseline is stronger, the initialization surface is clearer, and the reporting/reproducibility contract is explicit. Otherwise the project will lose interpretability before it gains credible new claims.

## Recommendation Boundary

If the near-term external need changes from scientific-surface expansion to scale or backend credibility, items 2 and 3 can be swapped. Without that change in objective, the default recommendation remains:

`longer-horizon validation -> seeded vortex initialization -> PETSc parity / scale-up -> stochastic noise / ensembles`
