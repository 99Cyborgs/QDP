# Status

- class: `incubate`
- activity: `active`
- last reviewed: `2026-04-13`
- owner: `forre`
- suggested promotion mode: `incubation link`

## Summary

QDP now has an accepted deterministic phase-1 short-horizon baseline plus a committed `n_steps=8` longer-horizon deterministic tranche. The short-horizon tranche remains validated at campaign `16/16`, refinement `4/4`, frozen references `4/4`, and same-stack reproducibility `pass`. The longer-horizon tranche reuses the same 16-case strip / `strip_with_moat` grid and now passes campaign `16/16`, frozen references `4/4`, and same-stack reproducibility `pass`, but it remains flagged under the copied refinement drift limits at `2/4`; that surface is committed and informative, but not yet part of the accepted deterministic baseline. The seeded-vortex surface is explicit, mask-aware, deterministic, and split into `initialization_only`, `short_horizon`, and rejection-taxonomy validation cases with schema-validated provenance and Tier-2 outputs; the Phase-2.3 harness only sweeps parameters, repeats same-stack runs, and aggregates committed Tier-2 observables without widening the validation claim boundary. Phase-2.4A v4 stochastic execution is runtime-enabled as a sequential fail-fast ensemble path with staged promotion, strict full-member aggregation, normalized noise provenance, and replay-oriented member identity capture. The committed small Phase-2.4A runtime smoke manifest remains an implementation/runtime statement only, not a scientific validation claim.

## Current risks

- generated artifacts and source materials are still too interleaved,
- the accepted short-horizon baseline and the flagged `n_steps=8` longer-horizon tranche could both be overread as broader solver validity if their claim boundaries are not kept explicit,
- the longer-horizon refinement sanity surface currently exceeds the copied short-horizon drift limits for `d(delta_f_over_f0)` and `d(qinv)` on the `dt=0.01` rows,
- seeded-vortex ansatz cases could be overread as relaxed or broadly validated vortex physics if the Phase-2.2 initialization-only versus short-horizon split is ignored,
- aggregated Phase-2.3 observables could be overread as broader dynamics evidence if the experiment-harness interpretation boundary is not kept explicit,
- Phase-2.4A stochastic execution now exists as a fail-closed runtime surface, but there are still no grounded scientific acceptance thresholds or parameter guardrails for `noise.strength` beyond the explicit config contract `noise.enabled=true`, `noise.seed`, and `noise.strength > 0`,
- longer-horizon seeded-vortex behavior and backend parity are still unvalidated,
- core/candidate boundary could blur if ALL-MIND starts loading QDP wholesale.

## Next Decision Point

- Accepted deterministic short-horizon baseline: `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml`
- Longer-horizon deterministic tranche disposition: `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v2_long_horizon.csv validation/thresholds_long_horizon.yaml validation/reference_manifest_long_horizon.yaml configs/phase1_refinement_sanity_long_horizon.yaml`, plus [docs/PHASE1_VALIDATION_MEMO.md](docs/PHASE1_VALIDATION_MEMO.md)
- Seeded-vortex tranche definition and caveats: `docs/PHASE2_SEEDED_VORTICES.md`, `docs/PHASE2_2_SEEDED_EXPERIMENT_PACK.md`
- Seeded-vortex experiment-pack validation: `tdgl-rf validate-seeded-vortices validation/seeded_vortex_phase2_2_manifest.yaml`
- Seeded-vortex experiment harness: `tdgl-rf run-experiment validation/seeded_vortex_phase2_3_experiment_pack.yaml`
- Phase-2.4A stochastic runtime hardening: `tdgl-rf run-experiment validation/seeded_vortex_phase2_4a_runtime_smoke.yaml`, targeted Phase-2.4A experiment-sweep / CLI tests, plus `configs/tdgl_run_provenance.schema.json`
- Seeded-run replay metadata contract: `configs/tdgl_run_provenance.schema.json`
- Seeded Tier-2 and rejection contracts: `configs/seeded_vortex_tier2.schema.json`, `configs/seeded_vortex_rejection.schema.json`
- Phase-2 follow-on options and residual gate logic: `docs/PHASE2_ENTRY_CRITERIA.md`, `docs/PHASE2_OPTIONS_MEMO.md`
- Reviewer-facing evidence packaging: `tdgl-rf evidence-bundle <validation_dir>`
