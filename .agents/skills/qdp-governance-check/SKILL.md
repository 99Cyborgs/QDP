---
name: qdp-governance-check
description: Run the legacy QDP bootstrap harness and final candidate-validation sweep through python qdp.py bootstrap and python qdp.py check. Use when working on the repo’s non-TDGL governance/module surface under config/, modules/, tools/, and artifacts/, and the job is to regenerate bootstrap outputs or validate emitted *_candidate.json artifacts. Do not use for tdgl-rf simulation or validation workflows.
---

# Purpose

Operate the legacy QDP governance harness that writes `artifacts/reports/` and validates emitted candidates under `artifacts/outputs/`.

# Use when

- The task is to regenerate the M06 bootstrap outputs.
- The task is to run the final repo-level candidate sweep across `artifacts/outputs/`.
- The task is to verify that emitted legacy candidates still satisfy the candidate schema and validator.

# Do not use when

- The task is a `tdgl-rf` runtime, validation, seeded-vortex, or evidence-bundle workflow.
- The task is one module selftest or one direct module run. Use `qdp-module-ops`.
- The task is only one candidate file. Use `python qdp.py validate ...` directly as a leaf command; do not create a broader workflow.

# Inputs required

- Optional `--outputs-root` override for the validation sweep.
- Optional `--skip-bootstrap` flag when reusing existing artifacts.

# Files and directories to inspect first

- `AGENTS.md`
- `REPO_MAP.md`
- `qdp.py`
- `qdp_paths.py`
- `config/schema/candidate_template.json`
- `config/schema/candidate_schema.json`
- `tools/validators/candidate_validator.py`
- `artifacts/reports/m06/bootstrap_report.json`
- `artifacts/reports/m06/closure_report.json`
- `artifacts/reports/system/module_closure_evaluation.json`
- `artifacts/outputs/`

# Step-by-step procedure

1. Confirm the task is on the legacy QDP control plane, not the active `tdgl-rf` runtime surface.
2. Run `python qdp.py bootstrap` when the M06 harness outputs need to be regenerated from source.
3. Run `python qdp.py check` for a full bootstrap-plus-validation sweep, or `python qdp.py check --skip-bootstrap` to validate the current outputs tree only.
4. Read the reported candidate totals and failure list before concluding the surface is healthy.
5. Inspect `artifacts/reports/m06/bootstrap_report.json`, `artifacts/reports/m06/closure_report.json`, and `artifacts/reports/system/module_closure_evaluation.json` when bootstrap changes matter.
6. Keep `artifacts/outputs/` as generated artifacts; do not treat them as governing source.

# Exact commands

```bash
python qdp.py bootstrap
python qdp.py check
python qdp.py check --skip-bootstrap
```

# Validation / definition of done

- `python qdp.py bootstrap` exits successfully and refreshes the M06 bootstrap reports and outputs.
- `python qdp.py check` or `--skip-bootstrap` prints `CHECK PASSED` with zero failed candidates.
- The outputs root contains `*_candidate.json` files and the validator sweep reports them all valid.
- Updated reports land under `artifacts/reports/` and outputs under `artifacts/outputs/`.

# Failure modes / escalation

- Missing outputs root or zero candidates:
  Bootstrap first or confirm the legacy harness is the intended surface.
- Candidate validation failures:
  Inspect the printed failing candidate path and the schema validator output before retrying.
- Confusion between legacy QDP and `tdgl-rf` surfaces:
  Stop and restate which control plane the task belongs to.

# Output artifacts

- `artifacts/reports/m06/bootstrap_report.json`
- `artifacts/reports/m06/closure_report.json`
- `artifacts/reports/system/module_closure_evaluation.json`
- `artifacts/outputs/m06/bootstrap/...`
- validated `artifacts/outputs/**/*_candidate.json`

# Example prompts that SHOULD trigger the skill

- "Re-run the legacy bootstrap harness and validate all emitted candidates."
- "Check whether the current artifacts output tree still passes the repo-level candidate sweep."
- "I changed the candidate schema plumbing; rerun the QDP bootstrap/check flow."

# Example prompts that should NOT trigger the skill

- "Run the phase-1 deterministic validation tranche."
- "Execute the seeded-vortex experiment pack."
- "Run one module selftest for m05."
