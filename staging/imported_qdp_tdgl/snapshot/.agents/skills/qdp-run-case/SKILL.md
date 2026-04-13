---
name: qdp-run-case
description: Validate one TDGL-RF config, execute one case, and inspect the resulting run directory. Use when working with a single config such as configs/d01_smoke.yaml or one seeded-vortex case file, including smoke runs and one-off local debugging. Do not use for matrix campaigns, phase-1 validation bundles, seeded-vortex suites, experiment packs, or contract/schema edits.
---

# Purpose

Run one config-driven case through the active `tdgl-rf` CLI surface and check that the produced run directory is internally consistent.

# Use when

- The task is about one concrete config file.
- The task is to smoke-test the runtime, inspect one run output, or reproduce one local case.
- The task needs `validate-config`, `run-case`, or `summarize` only.

# Do not use when

- The task is a matrix campaign or campaign postprocessing. Use `qdp-phase1-campaign`.
- The task is the thresholded deterministic validation tranche. Use `qdp-phase1-validation`.
- The task is the Phase-2.2 seeded suite. Use `qdp-seeded-vortex-suite`.
- The task is the Phase-2.3 deterministic experiment harness. Use `qdp-seeded-vortex-experiment-pack`.
- The task is the Phase-2.4A stochastic ensemble operator pack. Use `qdp-phase2-4a-ensemble`.
- The task changes schemas, manifests, CLI dispatch, or validation contracts. Use `qdp-contract-sync`.

# Inputs required

- One case config path.
- Optional expectation about whether observables should be persisted.
- Optional output inspection target if the run already exists.

# Files and directories to inspect first

- `README.md`
- `VALIDATION.md`
- `docs/PHASE1_ACCEPTANCE.md`
- `src/tdgl_rf/cli.py`
- `src/tdgl_rf/workflows/run_case.py`
- `tests/integration/test_run_case_outputs.py`
- `tests/integration/test_d01_clean_strip.py`

# Step-by-step procedure

1. Confirm the config path exists and read the relevant boundary docs if the run is phase-sensitive.
2. If `tdgl-rf` is unavailable in the environment, bootstrap the editable install first.
3. Run config validation before execution so schema or path failures stop early.
4. Execute the case with `run-case`.
5. Capture the emitted run directory from CLI JSON or inspect `runs/<case_id>/<timestamp>/`.
6. Check `status.json`, `diagnostics/run_summary.json`, and `provenance.json` for consistency.
7. If `output.write_observables: true`, verify `observables/summary.json` and `observables/timeseries.csv` exist.
8. If `output.write_observables: false`, confirm observables were intentionally kept in memory only and do not treat missing files as failure.
9. Use `summarize` only to print the stored `status.json` for an existing run directory.

# Exact commands

```bash
python -m pip install -e .[dev]
tdgl-rf validate-config configs/d01_smoke.yaml
tdgl-rf run-case configs/d01_smoke.yaml
tdgl-rf summarize runs/D01_smoke/<timestamp>
```

# Validation / definition of done

- `tdgl-rf validate-config <config>` exits successfully.
- `tdgl-rf run-case <config>` exits successfully and returns a JSON summary.
- The run directory contains `status.json`, `diagnostics/run_summary.json`, and `provenance.json`.
- If observables are enabled, `observables/summary.json` and `observables/timeseries.csv` exist and match the run summary.
- Unsupported surfaces from `docs/PHASE1_ACCEPTANCE.md` remain unsupported; do not overclaim beyond the configured run.

# Failure modes / escalation

- Schema or path validation failure:
  Fix the config or referenced file path before retrying.
- Disconnected custom mask or other unsupported geometry:
  Treat it as an explicit runtime boundary, not as a silent data issue.
- Seeded-vortex config needs claim-bounded validation:
  Stop using ad hoc single-case runs and switch to `qdp-seeded-vortex-suite` or `qdp-seeded-vortex-experiment-pack`.
- Run-directory inconsistency:
  Compare `status.json`, `diagnostics/run_summary.json`, and CLI output before assuming solver failure.

# Output artifacts

- `runs/<case_id>/<timestamp>/status.json`
- `runs/<case_id>/<timestamp>/provenance.json`
- `runs/<case_id>/<timestamp>/diagnostics/run_summary.json`
- Optional `runs/<case_id>/<timestamp>/observables/summary.json`
- Optional `runs/<case_id>/<timestamp>/observables/timeseries.csv`

# Example prompts that SHOULD trigger the skill

- "Validate and run `configs/d01_smoke.yaml`, then inspect the output."
- "Run one deterministic seeded-vortex config and tell me whether the run directory looks complete."
- "Check whether this single TDGL-RF config still executes after my change."

# Example prompts that should NOT trigger the skill

- "Run the full deterministic validation tranche."
- "Execute the seeded-vortex experiment pack and aggregate its results."
- "Update the seeded-vortex manifest schema and sync the tests."
