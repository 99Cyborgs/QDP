---
name: qdp-seeded-vortex-experiment-pack
description: Execute an explicit Phase-2.3 deterministic seeded-vortex experiment pack through tdgl-rf run-experiment, validate the generated provenance and Tier-2 artifacts, and inspect the aggregated experiment_results outputs. Use when working with validation/seeded_vortex_phase2_3_experiment_pack.yaml or another committed 3.x deterministic experiment-pack manifest. Do not use for the Phase-2.2 seeded suite, for stochastic 4.x ensemble promotion work, or for schema/contract changes.
---

# Purpose

Run the deterministic same-stack seeded-vortex sweep/repetition harness and inspect its aggregate artifacts without treating it as broader seeded-vortex validation.

# Use when

- The task is to execute the committed Phase-2.3 deterministic experiment pack.
- The task is to inspect its aggregated `experiment_results` payloads or per-run provenance.
- The task is to debug deterministic sweep expansion, repetition stability, or aggregate observables.

# Do not use when

- The task is the Phase-2.2 validation suite. Use `qdp-seeded-vortex-suite`.
- The task is a 4.x stochastic ensemble or staged promotion flow; that runtime exists but is not encoded here as a committed recurring operator workflow.
- The task changes experiment-pack schemas, CLI dispatch, or replay contracts. Use `qdp-contract-sync`.

# Inputs required

- Explicit 3.x experiment-pack manifest path.
- Optional output directory.

# Files and directories to inspect first

- `README.md`
- `STATUS.md`
- `VALIDATION.md`
- `validation/seeded_vortex_phase2_3_experiment_pack.yaml`
- `configs/seeded_vortex_experiment_pack.schema.json`
- `configs/tdgl_run_provenance.schema.json`
- `configs/seeded_vortex_tier2.schema.json`
- `src/tdgl_rf/cli.py`
- `src/tdgl_rf/workflows/experiment_sweep.py`
- `src/tdgl_rf/analysis/experiment_aggregation.py`
- `tests/integration/test_experiment_sweep_workflows.py`

# Step-by-step procedure

1. Confirm the manifest is a 3.x deterministic experiment pack, not a Phase-2.2 suite and not a 4.x ensemble.
2. Read the seeded-vortex status docs so the run is interpreted as a deterministic sweep/repetition harness over committed Tier-2 observables only.
3. Run the manifest through `tdgl-rf run-experiment <manifest>`.
4. Inspect `experiment_results.json` first, then the CSV and Markdown views.
5. Spot-check one per-run `provenance.json` and `diagnostics/seeded_vortex_tier2.json` under the output tree.
6. Preserve the non-claim boundary:
   this harness is not a broader seeded-vortex validation artifact and does not authorize stochastic or long-time claims.

# Exact commands

```bash
tdgl-rf run-experiment validation/seeded_vortex_phase2_3_experiment_pack.yaml
tdgl-rf run-experiment validation/seeded_vortex_phase2_3_experiment_pack.yaml --output-dir runs/experiment_seeded_vortex_phase2_3_experiment_pack_manual
```

# Validation / definition of done

- The command exits successfully.
- The output directory contains `experiment_results.json`, `experiment_results.csv`, and `experiment_results.md`.
- Each recorded run directory contains `provenance.json` and `diagnostics/seeded_vortex_tier2.json`.
- Aggregate results reflect the expected parameter-point count and run count from the manifest.
- Summaries stay inside the deterministic same-stack sweep/repetition boundary.

# Failure modes / escalation

- Manifest dispatch or schema validation failure:
  Fix the manifest or use `qdp-contract-sync` if the schema must change. Do not rely on fallback behavior.
- Non-empty output directory:
  Use a fresh destination; the workflow is fail-closed on output promotion.
- Missing per-run provenance or Tier-2 payload:
  Treat the pack as failed even if some runs completed.
- Attempted interpretation as broad validation:
  Stop and restate the experiment-harness boundary from `VALIDATION.md` and `STATUS.md`.

# Output artifacts

- `runs/experiment_<pack_name>/experiment_results.json`
- `runs/experiment_<pack_name>/experiment_results.csv`
- `runs/experiment_<pack_name>/experiment_results.md`
- `runs/experiment_<pack_name>/param_<hash>/<run_id>/provenance.json`
- `runs/experiment_<pack_name>/param_<hash>/<run_id>/diagnostics/seeded_vortex_tier2.json`

# Example prompts that SHOULD trigger the skill

- "Run the committed deterministic seeded-vortex experiment pack and inspect the aggregates."
- "Check whether the experiment harness still writes stable provenance for each repetition."
- "Re-run the Phase-2.3 manifest after my aggregation change."

# Example prompts that should NOT trigger the skill

- "Run the Phase-2.2 seeded validation suite."
- "Add a new experiment-pack schema field."
- "Execute a stochastic 4.x ensemble manifest for publication claims."
