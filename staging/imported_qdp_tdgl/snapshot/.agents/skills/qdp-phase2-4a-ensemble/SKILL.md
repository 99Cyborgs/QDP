---
name: qdp-phase2-4a-ensemble
description: Execute the committed Phase-2.4A stochastic seeded-vortex operator pack through tdgl-rf run-experiment, validate the generated replay metadata and Tier-2 artifacts, and inspect the aggregated experiment_results outputs without overstating the scientific boundary. Use when working with validation/seeded_vortex_phase2_4a_experiment_pack.yaml or another committed 4.x operator manifest. Do not use for the dedicated same-stack validation command, for Phase-2.2 validation, for Phase-2.3 deterministic packs, or for schema/contract changes.
---

# Purpose

Run the committed runtime-only stochastic same-stack ensemble pack and inspect its artifacts while keeping the scientific non-claim boundary explicit.

# Use when

- The task is to execute the committed Phase-2.4A operator pack.
- The task is to inspect aggregated `experiment_results` payloads or one ensemble member's replay metadata.
- The task is to debug fail-fast staging, member identity, promotion, or aggregation on the committed 4.x surface.

# Do not use when

- The task is the Phase-2.2 validation suite. Use `qdp-seeded-vortex-suite`.
- The task is a deterministic 3.x experiment pack. Use `qdp-seeded-vortex-experiment-pack`.
- The task is the fixed-seed Phase-2.4A validation surface. Use `qdp-phase2-4a-validation`.
- The task changes schemas, manifest contracts, or replay metadata surfaces. Use `qdp-contract-sync`.

# Inputs required

- Explicit 4.x operator manifest path.
- Optional output directory.

# Files and directories to inspect first

- `README.md`
- `STATUS.md`
- `VALIDATION.md`
- `docs/PHASE2_ENTRY_CRITERIA.md`
- `docs/PHASE2_SEEDED_VORTICES.md`
- `validation/seeded_vortex_phase2_4a_experiment_pack.yaml`
- `configs/seeded_vortex_experiment_pack_v4.schema.json`
- `configs/tdgl_run_provenance.schema.json`
- `configs/seeded_vortex_tier2.schema.json`
- `src/tdgl_rf/cli.py`
- `src/tdgl_rf/workflows/experiment_sweep.py`
- `src/tdgl_rf/analysis/experiment_aggregation.py`
- `tests/integration/test_experiment_sweep_workflows.py`

# Step-by-step procedure

1. Confirm the manifest is a 4.x stochastic ensemble operator pack, not a Phase-2.2 suite and not a 3.x deterministic pack.
2. Read the seeded-vortex and phase-2 entry docs so the run is interpreted as runtime-only control-plane evidence, not as a scientific validation artifact.
3. Run the manifest through `tdgl-rf run-experiment <manifest>`.
4. Inspect `experiment_results.json` first, then the CSV and Markdown views.
5. Spot-check one per-member `provenance.json` and `diagnostics/seeded_vortex_tier2.json` under the output tree.
6. Preserve the non-claim boundary:
   this operator pack exercises stochastic execution, replay metadata, and fail-closed aggregation only; it does not authorize stochastic robustness, long-time dynamics, or broader vortex-physics claims.

# Exact commands

```bash
tdgl-rf run-experiment validation/seeded_vortex_phase2_4a_experiment_pack.yaml
tdgl-rf run-experiment validation/seeded_vortex_phase2_4a_experiment_pack.yaml --output-dir runs/experiment_seeded_vortex_phase2_4a_manual
```

# Validation / definition of done

- The command exits successfully.
- The output directory contains `experiment_results.json`, `experiment_results.csv`, and `experiment_results.md`.
- Each recorded ensemble member run directory contains `provenance.json` and `diagnostics/seeded_vortex_tier2.json`.
- Aggregate results reflect the expected parameter-point count and member count from the manifest.
- Summaries stay inside the runtime-only stochastic same-stack operator boundary.

# Failure modes / escalation

- Manifest dispatch or schema validation failure:
  Fix the manifest or use `qdp-contract-sync` if the schema must change. Do not rely on fallback behavior.
- Non-empty output directory:
  Use a fresh destination; the workflow is fail-closed on output promotion.
- Missing per-member provenance or Tier-2 payload:
  Treat the pack as failed even if some members completed.
- Attempted interpretation as scientific validation:
  Stop and restate the runtime-only boundary from `VALIDATION.md`, `STATUS.md`, and `docs/PHASE2_ENTRY_CRITERIA.md`.

# Output artifacts

- `runs/experiment_<pack_name>/experiment_results.json`
- `runs/experiment_<pack_name>/experiment_results.csv`
- `runs/experiment_<pack_name>/experiment_results.md`
- `runs/experiment_<pack_name>/param_<hash>/<run_id>/provenance.json`
- `runs/experiment_<pack_name>/param_<hash>/<run_id>/diagnostics/seeded_vortex_tier2.json`

# Example prompts that SHOULD trigger the skill

- "Run the committed Phase-2.4A operator pack and inspect the aggregates."
- "Check whether the committed stochastic ensemble manifest still writes replay-stable member provenance."
- "Re-run the canonical 4.x operator manifest after my aggregation change."

# Example prompts that should NOT trigger the skill

- "Run the Phase-2.2 seeded validation suite."
- "Run the Phase-2.3 deterministic experiment pack."
- "Add a new field to the v4 experiment-pack schema."
