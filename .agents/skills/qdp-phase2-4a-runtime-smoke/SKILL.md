---
name: qdp-phase2-4a-runtime-smoke
description: Execute the committed Phase-2.4A stochastic seeded-vortex runtime smoke manifest through tdgl-rf run-experiment, inspect fail-closed ensemble outputs, and keep the runtime-only claim boundary explicit. Use when working with validation/seeded_vortex_phase2_4a_runtime_smoke.yaml or its committed seeded stochastic base config. Do not use for broader stochastic validation claims, for Phase-2.2 or Phase-2.3 deterministic surfaces, or for schema/contract changes.
---

# Purpose

Execute and inspect the committed small Phase-2.4A runtime smoke surface without overstating it as a stochastic validation artifact.

# Use when

- The task is to rerun `validation/seeded_vortex_phase2_4a_runtime_smoke.yaml`.
- The task is to inspect fail-fast ensemble execution, replay-oriented provenance, or aggregate smoke outputs for the committed 4.x manifest.
- The task is to verify the committed runtime smoke path still executes the seeded short-horizon stochastic control plane.

# Do not use when

- The task is the Phase-2.2 deterministic seeded-vortex suite. Use `qdp-seeded-vortex-suite`.
- The task is the Phase-2.3 deterministic sweep/repetition harness. Use `qdp-seeded-vortex-experiment-pack`.
- The task changes 4.x schema fields, manifest dispatch, provenance contracts, or claim language. Use `qdp-contract-sync`.
- The task aims to establish stochastic acceptance thresholds or broader scientific claims. This smoke surface does not do that.

# Inputs required

- Phase-2.4A manifest path, normally `validation/seeded_vortex_phase2_4a_runtime_smoke.yaml`.
- Optional fresh output directory.

# Files and directories to inspect first

- `README.md`
- `STATUS.md`
- `VALIDATION.md`
- `docs/PHASE2_ENTRY_CRITERIA.md`
- `docs/PHASE2_SEEDED_VORTICES.md`
- `validation/seeded_vortex_phase2_4a_runtime_smoke.yaml`
- `configs/validation/seeded_vortex/short_horizon/stochastic_single_positive.yaml`
- `configs/seeded_vortex_experiment_pack_v4.schema.json`
- `configs/tdgl_run_provenance.schema.json`
- `configs/seeded_vortex_tier2.schema.json`
- `src/tdgl_rf/cli.py`
- `src/tdgl_rf/workflows/experiment_sweep.py`
- `src/tdgl_rf/analysis/experiment_aggregation.py`
- `tests/integration/test_experiment_sweep_workflows.py`

# Step-by-step procedure

1. Read the seeded-vortex and validation boundary docs first so the run is interpreted as runtime smoke, not as a stochastic acceptance surface.
2. Run the committed manifest with `tdgl-rf run-experiment`.
3. Inspect `experiment_results.json` before the Markdown report so member counts, noise seeds, and aggregate observables are explicit.
4. Spot-check one member `provenance.json` and `diagnostics/seeded_vortex_tier2.json`.
5. Preserve the non-claim boundary:
   this manifest checks control-plane dispatch, fail-closed staging/promotion, ensemble provenance, and replay integrity only.

# Exact commands

```bash
tdgl-rf run-experiment validation/seeded_vortex_phase2_4a_runtime_smoke.yaml
tdgl-rf run-experiment validation/seeded_vortex_phase2_4a_runtime_smoke.yaml --output-dir runs/experiment_seeded_vortex_phase2_4a_runtime_smoke_manual
```

# Validation / definition of done

- The command exits successfully.
- The output directory contains `experiment_results.json`, `experiment_results.csv`, and `experiment_results.md`.
- The aggregate payload reports `mode: stochastic_ensemble`.
- The aggregate payload reports the expected member count and parameter-point count from the committed manifest.
- Each member run directory contains `provenance.json` and `diagnostics/seeded_vortex_tier2.json`.
- Summaries keep the runtime-only, scientifically unvalidated boundary explicit.

# Failure modes / escalation

- Non-empty output directory:
  Use a fresh destination; the workflow is fail-closed on promotion.
- Missing member provenance or Tier-2 payload:
  Treat the pack as failed even if some members completed.
- Partial aggregate outputs after failure:
  Treat that as a regression in fail-closed staging/promotion semantics.
- Attempted interpretation as stochastic validation:
  Stop and restate the explicit runtime-smoke boundary from `VALIDATION.md` and `STATUS.md`.

# Output artifacts

- `runs/experiment_seeded_vortex_phase2_4a_runtime_smoke/.../experiment_results.json`
- `runs/experiment_seeded_vortex_phase2_4a_runtime_smoke/.../experiment_results.csv`
- `runs/experiment_seeded_vortex_phase2_4a_runtime_smoke/.../experiment_results.md`
- `runs/experiment_seeded_vortex_phase2_4a_runtime_smoke/.../param_<hash>/<run_id>/provenance.json`
- `runs/experiment_seeded_vortex_phase2_4a_runtime_smoke/.../param_<hash>/<run_id>/diagnostics/seeded_vortex_tier2.json`

# Example prompts that SHOULD trigger the skill

- "Run the committed Phase-2.4A runtime smoke manifest."
- "Check whether the seeded stochastic smoke manifest still writes stable ensemble provenance."
- "Re-run the committed 4.x smoke manifest after my experiment-sweep change."

# Example prompts that should NOT trigger the skill

- "Run the deterministic seeded-vortex validation suite."
- "Add a new field to the 4.x manifest schema."
- "Use the stochastic smoke run as proof of accepted stochastic physics."
