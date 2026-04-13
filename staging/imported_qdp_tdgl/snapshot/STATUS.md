# Status

- class: `incubate`
- activity: `active`
- last reviewed: `2026-04-08`
- owner: `forre`
- suggested promotion mode: `incubation link`

## Summary

QDP now has a validated deterministic phase-1 baseline plus a bounded Phase-2.2 seeded-vortex experiment pack and a Phase-2.3 experiment harness. The seeded-vortex surface is explicit, mask-aware, deterministic, and split into `initialization_only`, `short_horizon`, and rejection-taxonomy validation cases with schema-validated provenance and Tier-2 outputs; the new harness only sweeps parameters, repeats same-stack runs, and aggregates committed Tier-2 observables without widening the validation claim boundary. Phase-2.4A v4 stochastic execution is now runtime-enabled as a sequential fail-fast ensemble path with staged promotion, strict full-member aggregation, normalized noise provenance, replay-oriented member identity capture, one committed operator manifest at `validation/seeded_vortex_phase2_4a_experiment_pack.yaml`, and one committed same-stack validation surface at `validation/seeded_vortex_phase2_4a_validation_manifest.yaml`. That validation surface freezes fixed-seed member identity, selected replay metadata, aggregate observables, and robustness summaries only. It is still a runtime/control-plane statement, not a scientific stochastic validation claim.

## Current risks

- generated artifacts and source materials are still too interleaved,
- short-horizon deterministic evidence could be overread as broader solver validity if the suite claim boundary is not kept explicit,
- seeded-vortex ansatz cases could be overread as relaxed or broadly validated vortex physics if the Phase-2.2 initialization-only versus short-horizon split is ignored,
- aggregated Phase-2.3 observables could be overread as broader dynamics evidence if the experiment-harness interpretation boundary is not kept explicit,
- Phase-2.4A stochastic execution and same-stack validation now exist as fail-closed runtime surfaces, but there are still no grounded scientific acceptance thresholds or parameter guardrails for `noise.strength` beyond the explicit config contract `noise.enabled=true`, `noise.seed`, and `noise.strength > 0`,
- longer-horizon seeded-vortex behavior and backend parity are still unvalidated,
- core/candidate boundary could blur if ALL-MIND starts loading QDP wholesale.

## Next Decision Point

- Seeded-vortex tranche definition and caveats: `docs/PHASE2_SEEDED_VORTICES.md`, `docs/PHASE2_2_SEEDED_EXPERIMENT_PACK.md`
- Seeded-vortex experiment-pack validation: `tdgl-rf validate-seeded-vortices validation/seeded_vortex_phase2_2_manifest.yaml`
- Seeded-vortex experiment harness: `tdgl-rf run-experiment validation/seeded_vortex_phase2_3_experiment_pack.yaml`
- Phase-2.4A committed operator pack: `tdgl-rf run-experiment validation/seeded_vortex_phase2_4a_experiment_pack.yaml`
- Phase-2.4A same-stack validation surface: `tdgl-rf validate-phase2-4a validation/seeded_vortex_phase2_4a_validation_manifest.yaml`
- Phase-2.4A stochastic runtime hardening: targeted Phase-2.4A validation / experiment-sweep / CLI tests plus `configs/tdgl_run_provenance.schema.json`
- Seeded-run replay metadata contract: `configs/tdgl_run_provenance.schema.json`
- Seeded Tier-2 and rejection contracts: `configs/seeded_vortex_tier2.schema.json`, `configs/seeded_vortex_rejection.schema.json`
- Phase-2 follow-on options and residual gate logic: `docs/PHASE2_ENTRY_CRITERIA.md`, `docs/PHASE2_OPTIONS_MEMO.md`
- Reviewer-facing evidence packaging: `tdgl-rf evidence-bundle <validation_dir>`
