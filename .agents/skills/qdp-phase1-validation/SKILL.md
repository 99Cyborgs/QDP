---
name: qdp-phase1-validation
description: Run the committed deterministic phase-1 validation tranche and its component checks: refinement-sanity, reference-check, reproducibility-check, and validate-phase1. Use when the task is to regenerate or inspect the conservative phase-1 validation evidence defined by VALIDATION.md, validation/thresholds.yaml, validation/reference_manifest.yaml, and configs/phase1_refinement_sanity.yaml. Do not use for reviewer bundle packaging, campaign-only work, single-case runs, or phase-2 seeded workflows.
---

# Purpose

Regenerate and inspect the conservative deterministic phase-1 validation surface without widening its claim boundary.

# Use when

- The task is to rerun the official phase-1 validation tranche.
- The task is to inspect or debug one of its component checks.
- The task changes the deterministic phase-1 runtime or validation thresholds and needs the committed evidence bundle regenerated.

# Do not use when

- The task is only a matrix campaign. Use `qdp-phase1-campaign`.
- The task is only to package an already completed validation run for reviewers. Use `qdp-evidence-bundle`.
- The task is a seeded-vortex suite or experiment pack.
- The task changes contract surfaces rather than just rerunning them. Use `qdp-contract-sync`.

# Inputs required

- Validation matrix path.
- Threshold spec path.
- Reference manifest path.
- Refinement sanity config path.
- Optional output directory.

# Files and directories to inspect first

- `VALIDATION.md`
- `docs/PHASE1_ACCEPTANCE.md`
- `docs/PHASE1_VALIDATION_CAMPAIGN.md`
- `docs/PHASE1_VALIDATION_MEMO.md`
- `validation/thresholds.yaml`
- `validation/reference_manifest.yaml`
- `configs/phase1_refinement_sanity.yaml`
- `src/tdgl_rf/workflows/refinement.py`
- `src/tdgl_rf/workflows/validation.py`
- `tests/integration/test_validation_workflows.py`
- `tests/unit/test_validation.py`

# Step-by-step procedure

1. Read the validation docs first so the run is interpreted as a conservative regression surface, not as broad physics certification.
2. If you only need one component, run the smallest sufficient check first: refinement, reference, or reproducibility.
3. For the full tranche, run `validate-phase1` with the committed matrix, thresholds, reference manifest, and refinement config.
4. Inspect `validation_summary.json` and `validation_report.md` before making any claim.
5. Verify that campaign results, refinement sanity, frozen references, and reproducibility all passed together.
6. Preserve the stated non-claims from the docs: no asymptotic convergence certification, no PETSc parity, no stochastic claim, no broader physics validation.

# Exact commands

```bash
tdgl-rf refinement-sanity configs/phase1_refinement_sanity.yaml
tdgl-rf reference-check validation/reference_manifest.yaml
tdgl-rf reproducibility-check configs/validation/reference_rf_strip.yaml validation/thresholds.yaml
tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml
```

# Validation / definition of done

- `refinement-sanity` writes `comparison_table.csv` and `comparison_table.json`.
- `reference-check` writes `reference_check.json` and `reference_check.md`.
- `reproducibility-check` writes a comparison JSON and Markdown report with exact same-stack pass status.
- `validate-phase1` writes `validation_summary.csv`, `validation_summary.json`, and `validation_report.md` under `runs/validation/...`.
- Overall success requires campaign, refinement, reference, and reproducibility all to pass together.

# Failure modes / escalation

- Threshold failures:
  Report the exact failing rows or metrics from the generated JSON instead of hand-waving.
- Reference hash mismatch:
  Treat it as frozen-reference drift and inspect the referenced config or output payloads.
- Reproducibility mismatch:
  Treat it as same-stack drift; do not collapse it into generic nondeterminism.
- Documentation drift:
  If the docs no longer match the validation behavior, switch to `qdp-contract-sync` and synchronize the contract surfaces.

# Output artifacts

- `runs/refinement_sanity/.../comparison_table.csv`
- `runs/refinement_sanity/.../comparison_table.json`
- `runs/reference_check/.../reference_check.json`
- `runs/reference_check/.../reference_check.md`
- `runs/reproducibility/...`
- `runs/validation/<matrix_stem>/<timestamp>/validation_summary.csv`
- `runs/validation/<matrix_stem>/<timestamp>/validation_summary.json`
- `runs/validation/<matrix_stem>/<timestamp>/validation_report.md`

# Example prompts that SHOULD trigger the skill

- "Re-run the official deterministic validation tranche after my solver change."
- "Check whether the frozen reference manifest still matches."
- "Run the refinement sanity harness and the reproducibility check."

# Example prompts that should NOT trigger the skill

- "Package this finished validation run into the reviewer bundle."
- "Run the phase-1 matrix and make the proposal summary."
- "Update the seeded-vortex schema and manifest tests."
