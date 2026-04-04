---
name: qdp-phase1-campaign
description: Execute, dry-run, slice, resume, and summarize deterministic phase-1 matrix campaigns through tdgl-rf run-matrix and summarize-campaign. Use when working with matrices/phase1_experiment_matrix_v1.csv or another experiment matrix and the job is campaign execution or compact campaign aggregation. Do not use for thresholded validation, single-case runs, seeded-vortex suites, experiment packs, or contract changes.
---

# Purpose

Operate the deterministic matrix campaign mechanism and generate the compact proposal-facing summary artifacts for one completed campaign.

# Use when

- The task is to dry-run or execute a campaign matrix.
- The task is to run only a selector-defined slice of a matrix.
- The task is to resume an interrupted campaign from stored state.
- The task is to summarize one completed campaign into `proposal_artifacts/`.

# Do not use when

- The task is just one config or one run directory. Use `qdp-run-case`.
- The task is the thresholded phase-1 validation tranche. Use `qdp-phase1-validation`.
- The task is a seeded-vortex suite or experiment pack. Use the phase-2 skills.
- The task changes matrix contract columns or dispatcher semantics. Use `qdp-contract-sync`.

# Inputs required

- Matrix path.
- Optional selector list of `column=value` filters.
- Optional resume campaign directory.
- Optional output directory for campaign summary artifacts.

# Files and directories to inspect first

- `docs/PHASE1_MATRIX_V1.md`
- `matrices/phase1_experiment_matrix_v1.csv`
- `src/tdgl_rf/cli.py`
- `src/tdgl_rf/workflows/run_matrix.py`
- `src/tdgl_rf/workflows/postprocess.py`
- `tests/unit/test_matrix_runner.py`
- `tests/integration/test_campaign_postprocess.py`

# Step-by-step procedure

1. Inspect the matrix definition and confirm the intended slice, full run, or resume target.
2. Use `--dry-run` first when changing selectors or checking a new matrix.
3. For an actual run, launch `tdgl-rf run-matrix <matrix>`.
4. If the run was interrupted, inspect `campaign_state.json` and resume only with the exact same matrix and selectors.
5. After a successful run, summarize it with `tdgl-rf summarize-campaign <campaign_dir>`.
6. Read `campaign_summary.json`, `row_results.csv`, and the proposal summary Markdown before making any proposal-facing interpretation.
7. Keep the interpretation boundary from `docs/PHASE1_MATRIX_V1.md`: this is a campaign-mechanism baseline, not broad validation by itself.

# Exact commands

```bash
tdgl-rf run-matrix matrices/phase1_experiment_matrix_v1.csv --dry-run
tdgl-rf run-matrix matrices/phase1_experiment_matrix_v1.csv --selector geometry_family=strip
tdgl-rf run-matrix matrices/phase1_experiment_matrix_v1.csv
tdgl-rf run-matrix matrices/phase1_experiment_matrix_v1.csv --resume runs/campaigns/phase1_experiment_matrix_v1/<timestamp>
tdgl-rf summarize-campaign runs/campaigns/phase1_experiment_matrix_v1/<timestamp>
```

# Validation / definition of done

- Dry-run returns `status: dry_run` or a concrete validation error.
- Executed campaigns write `campaign_state.json`, `row_results.csv`, and `campaign_summary.json`.
- Successful rows have `run_dir` and `summary_path` recorded in `row_results.csv`.
- `summarize-campaign` writes `proposal_summary.csv`, `proposal_summary.json`, and `proposal_summary.md`.
- Resume is used only against a stored campaign state with matching matrix hash and selectors.

# Failure modes / escalation

- Selector produces zero rows:
  Fix selectors instead of creating a new workflow.
- Gate-blocked rows:
  Inspect `promotion_rule`, `phase`, and prior row status in `campaign_state.json`.
- Resume mismatch:
  Do not force it; rerun from a fresh campaign directory.
- Missing or partial row outputs during summary:
  Treat the summary as incomplete and inspect the affected row’s run directory.

# Output artifacts

- `runs/campaigns/<matrix_stem>/<timestamp>/campaign_state.json`
- `runs/campaigns/<matrix_stem>/<timestamp>/row_results.csv`
- `runs/campaigns/<matrix_stem>/<timestamp>/campaign_summary.json`
- `runs/campaigns/<matrix_stem>/<timestamp>/proposal_artifacts/proposal_summary.csv`
- `runs/campaigns/<matrix_stem>/<timestamp>/proposal_artifacts/proposal_summary.json`
- `runs/campaigns/<matrix_stem>/<timestamp>/proposal_artifacts/proposal_summary.md`

# Example prompts that SHOULD trigger the skill

- "Dry-run the phase-1 matrix and tell me whether the selectors are valid."
- "Resume this interrupted campaign and then regenerate the proposal summary."
- "Run the phase-1 experiment matrix and aggregate the results."

# Example prompts that should NOT trigger the skill

- "Run the full validation tranche with thresholds and references."
- "Validate one config and execute a single smoke case."
- "Run the seeded-vortex Phase-2.2 suite."
