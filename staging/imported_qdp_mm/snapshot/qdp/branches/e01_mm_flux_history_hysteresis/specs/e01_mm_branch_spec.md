# E01 MM Branch Spec

## Canonical Fields

| Field | Value |
| --- | --- |
| `branch_tag` | `E01_MM_FLUX_HISTORY_HYSTERESIS` |
| `branch_slug` | `e01_mm_flux_history_hysteresis` |
| `declared_bath_class` | `METASTABLE_C_STATE` |
| `conditional_promoted_interpretation` | `VORTEX` |
| `primary_observable` | `hysteresis index in 1/Qi versus field history` |
| `secondary_observables` | `selected field T1`; `delta fr over fr` |
| `minimal_discriminant_measurement` | `ZFC versus FC plus up and down loops with dwell convergence and sham timing control` |
| `invariant_preserved` | `standard GKSL baseline and ordinary dissipative interpretation` |
| `reduction_limit` | `zero history dependence recovers memoryless field dependent baseline` |
| `count_new_free_parameters` | `no more than 2 beyond baseline in phase 1 interpretation` |
| `promotion_condition` | `matched geometry replication with consistent susceptibility ordering` |
| `recommended_governance_posture` | `conservative and non promotional` |

## Registration Rule

Register this branch at intake as `METASTABLE_C_STATE`.

Do not register it as vortex-proven.
Do not merge metastable memory and vortex into a single claim.
Treat `VORTEX` only as a conditional promoted interpretation after the geometry gate passes.

## Phase 1 Scope

- Fixed low temperature only.
- Fixed low drive only.
- Broad power sweeps are forbidden.
- Broad temperature sweeps are forbidden.
- The primary branch discriminator is history dependence in `1/Qi`.
- `T1` and `delta fr over fr` are secondary observables and cannot override the primary observable.

## Required Evidence and Controls

- `ZFC` versus `FC` comparison is mandatory.
- Up-field and down-field loops are mandatory.
- Dwell convergence is mandatory.
- Sham timing control is mandatory.
- Package witness or reference measurement is mandatory.
- Cooldown replication minimum is `3`.
- Same-chip matched widths are preferred and treated as mandatory for any later vortex promotion.

## Interpretive Boundaries

- Cross-device confirmation must not be assumed.
- The first interpretive layer may add no more than `2` free parameters beyond the baseline field-dependent loss model.
- H0, H1, H3, and H4 must be evaluated before any H2 vortex-specific interpretation is allowed.
- Failure of the geometry gate downgrades vortex interpretation only; it does not by itself erase a generic metastable memory branch.

## Explicit Non-Claims

- Not a proof of vortex trapping.
- Not a proof of cross-device universality.
- Not a broad mapping of power dependence.
- Not a broad mapping of temperature dependence.
- Not a closure claim on microscopic origin.
