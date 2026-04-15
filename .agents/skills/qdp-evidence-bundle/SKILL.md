---
name: qdp-evidence-bundle
description: Package one completed deterministic phase-1 validation run into the reviewer-facing evidence bundle produced by tdgl-rf evidence-bundle. Use when the task starts from an existing runs/validation/... directory and needs the copied source artifacts plus generated technical summary, operating conditions, limitations, and refinement summary. Do not use to run the validation tranche itself or for seeded-vortex workflows.
---

# Purpose

Turn one completed deterministic phase-1 validation run into the compact reviewer-facing evidence bundle defined by the repo.

# Use when

- The input is already a completed `runs/validation/...` directory.
- The task is to regenerate or inspect the reviewer-facing bundle contents.
- The task is to confirm bundle inputs and generated summary files remain aligned with the source validation artifacts.

# Do not use when

- The validation run has not been generated yet. Use `qdp-phase1-validation`.
- The task is only to run matrix or reference checks.
- The task is seeded-vortex work.
- The task changes bundle contracts or source-doc extraction rules. Use `qdp-contract-sync`.

# Inputs required

- One completed validation directory.
- Optional output directory.

# Files and directories to inspect first

- `README.md`
- `VALIDATION.md`
- `docs/PHASE1_VALIDATION_MEMO.md`
- `docs/PHASE1_VALIDATION_CAMPAIGN.md`
- `docs/PHASE1_ACCEPTANCE.md`
- `src/tdgl_rf/workflows/evidence.py`
- `tests/unit/test_evidence.py`

# Step-by-step procedure

1. Confirm the input directory already contains `validation_summary.json`, `validation_summary.csv`, and `validation_report.md`.
2. Confirm the nested campaign summary, reference checks, and refinement sanity artifacts exist; the bundle workflow requires all of them.
3. Run `tdgl-rf evidence-bundle <validation_dir>`.
4. Inspect the generated `README.md` and `manifest.json` in the bundle root first.
5. Spot-check the generated summaries under `summaries/` against the copied source artifacts under `source_artifacts/` and `source_docs/`.
6. Preserve the documented bundle boundary: it is a compact reviewer bundle for the deterministic phase-1 baseline, not a broader authorization.

# Exact commands

```bash
tdgl-rf evidence-bundle runs/validation/phase1_validation_matrix_v1/<timestamp>
tdgl-rf evidence-bundle runs/validation/phase1_validation_matrix_v1/<timestamp> --output-dir runs/evidence/manual_bundle
```

# Validation / definition of done

- The bundle command exits successfully.
- The output directory contains:
  `README.md`, `manifest.json`, `source_artifacts/`, `source_docs/`, `inputs/`, and `summaries/`.
- `summaries/` contains:
  `technical_summary.md`, `validated_operating_conditions.md`, `known_limitations.md`, and `refinement_sanity_summary.md`.
- `manifest.json` records copied and generated artifact paths.

# Failure modes / escalation

- Missing required validation artifact:
  Regenerate the phase-1 validation tranche first instead of hand-assembling the bundle.
- Missing expected bullet section in the source docs:
  Treat it as contract drift between bundle generation and source docs; switch to `qdp-contract-sync`.
- Invalid attempt to use a non-validation directory:
  Stop and supply a completed `runs/validation/...` directory.

# Output artifacts

- `runs/evidence/<matrix_stem>/<validation_timestamp>/README.md`
- `runs/evidence/<matrix_stem>/<validation_timestamp>/manifest.json`
- `runs/evidence/<matrix_stem>/<validation_timestamp>/source_artifacts/...`
- `runs/evidence/<matrix_stem>/<validation_timestamp>/source_docs/...`
- `runs/evidence/<matrix_stem>/<validation_timestamp>/summaries/technical_summary.md`
- `runs/evidence/<matrix_stem>/<validation_timestamp>/summaries/validated_operating_conditions.md`
- `runs/evidence/<matrix_stem>/<validation_timestamp>/summaries/known_limitations.md`
- `runs/evidence/<matrix_stem>/<validation_timestamp>/summaries/refinement_sanity_summary.md`

# Example prompts that SHOULD trigger the skill

- "Package this completed validation run into the reviewer bundle."
- "Regenerate the evidence bundle summaries from an existing validation directory."
- "Check whether the evidence bundle still pulls the right phase-1 source docs."

# Example prompts that should NOT trigger the skill

- "Run the validation tranche from scratch."
- "Run the seeded-vortex validation suite."
- "Change the limitations extraction rules in the bundle generator."
