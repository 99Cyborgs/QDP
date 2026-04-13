---
name: qdp-contract-sync
description: Change formal TDGL-RF contract surfaces and keep schemas, manifests, validators, CLI dispatch, docs, and tests synchronized. Use when editing configs/*.schema.json, validation manifests, provenance or Tier-2 contracts, manifest classification in src/tdgl_rf/cli.py, or workflow validators in src/tdgl_rf/workflows/validation.py, seeded_vortex_suite.py, or experiment_sweep.py. Do not use for merely rerunning an unchanged workflow.
---

# Purpose

Modify formal runtime or validation contracts without leaving the repo in a partially synchronized state.

# Use when

- The task changes a JSON schema under `configs/`.
- The task changes a committed validation or experiment manifest under `validation/`.
- The task changes provenance, Tier-2, or rejection payload structure.
- The task changes manifest dispatch or explicit contract routing in `src/tdgl_rf/cli.py`.
- The task changes validation semantics that are mirrored in docs and tests.

# Do not use when

- The task only reruns an existing workflow with no contract edits.
- The task is a pure docs clarification with no contract-bearing file change.
- The task is a one-off refactor plan or repo migration item.

# Inputs required

- The changed contract surface.
- The intended compatibility posture: preserve contract, narrow it, or widen it.
- The affected validation command surface.

# Files and directories to inspect first

- `VALIDATION.md`
- `README.md`
- `STATUS.md`
- `configs/tdgl_case.schema.json`
- `configs/seeded_vortex_experiment_manifest.schema.json`
- `configs/seeded_vortex_experiment_pack.schema.json`
- `configs/seeded_vortex_experiment_pack_v4.schema.json`
- `configs/tdgl_run_provenance.schema.json`
- `configs/seeded_vortex_tier2.schema.json`
- `configs/seeded_vortex_rejection.schema.json`
- `validation/thresholds.yaml`
- `validation/reference_manifest.yaml`
- `validation/seeded_vortex_phase2_2_manifest.yaml`
- `validation/seeded_vortex_phase2_3_experiment_pack.yaml`
- `src/tdgl_rf/cli.py`
- `src/tdgl_rf/workflows/validation.py`
- `src/tdgl_rf/workflows/seeded_vortex_suite.py`
- `src/tdgl_rf/workflows/experiment_sweep.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_validation.py`
- `tests/unit/test_seeded_vortex_suite.py`
- `tests/integration/test_validation_workflows.py`
- `tests/integration/test_experiment_sweep_workflows.py`

# Step-by-step procedure

1. Identify the exact governing contract files first: schema, manifest, validator, CLI dispatch, and doc surfaces.
2. Decide whether the change preserves, narrows, or widens the contract. Do not mix these without stating it.
3. Update the authoritative schema or manifest first, then the corresponding validator or dispatcher.
4. Update the affected docs so the supported surface, unsupported cases, and non-claims stay explicit.
5. Update the focused unit and integration tests that pin the changed surface.
6. Run the smallest sufficient pytest slice for the touched contract area.
7. Run the live CLI command that exercises the changed contract surface.
8. If the contract widens or narrows the active boundary, update `STATUS.md` and `PROMOTION_NOTES.md` accordingly.

# Exact commands

```bash
pytest tests/unit/test_cli.py tests/unit/test_validation.py tests/unit/test_seeded_vortex_suite.py tests/integration/test_validation_workflows.py tests/integration/test_experiment_sweep_workflows.py
tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml
tdgl-rf validate-seeded-vortices validation/seeded_vortex_phase2_2_manifest.yaml
tdgl-rf run-experiment validation/seeded_vortex_phase2_3_experiment_pack.yaml
```

# Validation / definition of done

- All changed schemas or manifests are reflected in validators, docs, and tests.
- The targeted pytest slice for the changed surface passes.
- The live CLI command for the changed surface passes.
- Unsupported or reserved cases remain explicit; they are not silently relaxed.
- Boundary docs and status docs are updated when the contract meaning changes.

# Failure modes / escalation

- Schema updated without matching validator or dispatcher updates:
  Stop and synchronize the code path before trusting test output.
- Docs still describe the old surface:
  Treat that as incomplete contract work, not as a follow-up nicety.
- Live command passes but schema-backed tests fail:
  Keep the contract narrow until both agree.
- Boundary widened without status or promotion note updates:
  Update `STATUS.md` and `PROMOTION_NOTES.md` before closing the task.

# Output artifacts

- Updated schema or manifest files.
- Updated validator or workflow code.
- Updated docs describing the supported and unsupported surface.
- Updated targeted tests covering the new contract.

# Example prompts that SHOULD trigger the skill

- "Add a new field to the seeded-vortex Tier-2 contract and sync the repo."
- "Tighten the experiment manifest schema and update dispatch/tests."
- "Change the phase-1 validation thresholds and make the docs and checks agree."

# Example prompts that should NOT trigger the skill

- "Run the current seeded suite and tell me whether it passes."
- "Execute the phase-1 matrix and summarize it."
- "Package this completed validation run for reviewers."
