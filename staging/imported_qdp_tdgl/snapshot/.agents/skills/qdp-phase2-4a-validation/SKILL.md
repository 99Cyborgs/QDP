---
name: qdp-phase2-4a-validation
description: Run the committed Phase-2.4A fixed-seed same-stack validation surface through tdgl-rf validate-phase2-4a, inspect mismatch records and validation artifacts, and keep the runtime-only interpretation boundary explicit. Use when working with validation/seeded_vortex_phase2_4a_validation_manifest.yaml or the generated phase2_4a_validation outputs. Do not use for raw operator-pack reruns, Phase-2.2 validation, Phase-2.3 deterministic packs, or schema/contract changes.
---

# Purpose

Execute and inspect the committed Phase-2.4A same-stack validation surface without overstating it as scientific stochastic validation.

# Use when

- The task is to run `tdgl-rf validate-phase2-4a validation/seeded_vortex_phase2_4a_validation_manifest.yaml`.
- The task is to inspect `phase2_4a_validation.json`, `phase2_4a_validation.md`, or `phase2_4a_validation_cases.csv`.
- The task is to diagnose mismatches in fixed-seed member identity, selected replay metadata, aggregate observables, or robustness summaries.

# Do not use when

- The task is only to rerun or inspect the raw Phase-2.4A operator pack. Use `qdp-phase2-4a-ensemble`.
- The task is a Phase-2.2 seeded-vortex validation suite. Use `qdp-seeded-vortex-suite`.
- The task is a deterministic Phase-2.3 experiment pack. Use `qdp-seeded-vortex-experiment-pack`.
- The task changes schemas, manifests, CLI dispatch, or replay contract surfaces. Use `qdp-contract-sync`.

# Inputs required

- Phase-2.4A validation manifest path.
- Optional validation output directory.

# Files and directories to inspect first

- `README.md`
- `STATUS.md`
- `VALIDATION.md`
- `docs/PHASE2_ENTRY_CRITERIA.md`
- `docs/PHASE2_SEEDED_VORTICES.md`
- `validation/seeded_vortex_phase2_4a_validation_manifest.yaml`
- `validation/seeded_vortex_phase2_4a_experiment_pack.yaml`
- `configs/seeded_vortex_phase2_4a_validation_manifest.schema.json`
- `configs/seeded_vortex_experiment_pack_v4.schema.json`
- `configs/tdgl_run_provenance.schema.json`
- `src/tdgl_rf/cli.py`
- `src/tdgl_rf/workflows/phase2_4a_validation.py`
- `src/tdgl_rf/workflows/experiment_sweep.py`
- `tests/unit/test_phase2_4a_validation.py`
- `tests/integration/test_phase2_4a_validation_workflows.py`

# Step-by-step procedure

1. Read the Phase-2 seeded docs first so the run stays inside the runtime/control-plane boundary.
2. Run the committed validation manifest through `tdgl-rf validate-phase2-4a <manifest>`.
3. Inspect `phase2_4a_validation.json` before the Markdown report so mismatch records are explicit.
4. Confirm the validation surface still freezes only stable semantic fields:
   fixed-seed member identity, selected replay metadata, aggregate observables, and robustness summaries.
5. If the run fails, inspect the mismatch records first, then the nested `experiment_run/experiment_results.json` payload and the referenced member `provenance.json` files.
6. Restate the non-claim boundary whenever you summarize the result:
   this surface validates same-stack runtime stability only, not scientific stochastic robustness or long-time dynamics.

# Exact commands

```bash
tdgl-rf validate-phase2-4a validation/seeded_vortex_phase2_4a_validation_manifest.yaml
tdgl-rf validate-phase2-4a validation/seeded_vortex_phase2_4a_validation_manifest.yaml --output-dir runs/phase2_4a_validation/manual
```

# Validation / definition of done

- The command exits successfully.
- The output directory contains `phase2_4a_validation.json`, `phase2_4a_validation.md`, and `phase2_4a_validation_cases.csv`.
- The JSON reports `overall_status: success` with zero mismatch records.
- The nested `experiment_run/` directory contains the rerun pack artifacts.
- Summaries preserve the runtime-only same-stack interpretation boundary.

# Failure modes / escalation

- Validation-manifest schema failure:
  Fix the manifest or use `qdp-contract-sync` if the contract must change.
- Missing per-member provenance:
  Treat the validation as fail-closed even if the aggregate pack run completed.
- Aggregate or robustness mismatch:
  Report the exact `param_set_hash` and field path from the mismatch records before speculating.
- Attempted scientific interpretation:
  Stop and restate the explicit non-claims from `VALIDATION.md`, `STATUS.md`, and `docs/PHASE2_SEEDED_VORTICES.md`.

# Output artifacts

- `runs/phase2_4a_validation/.../phase2_4a_validation.json`
- `runs/phase2_4a_validation/.../phase2_4a_validation.md`
- `runs/phase2_4a_validation/.../phase2_4a_validation_cases.csv`
- `runs/phase2_4a_validation/.../experiment_run/experiment_results.json`

# Example prompts that SHOULD trigger the skill

- "Run the committed Phase-2.4A validation manifest and show me any mismatches."
- "Check whether the fixed-seed 4.x validation surface still passes after my provenance change."
- "Inspect the Phase-2.4A validation report, not just the raw operator-pack output."

# Example prompts that should NOT trigger the skill

- "Just rerun the committed 4.x operator pack."
- "Run the deterministic seeded-vortex experiment pack."
- "Add a field to the Phase-2.4A validation schema."
