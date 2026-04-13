---
name: qdp-module-ops
description: List, self-test, and directly run legacy QDP modules through python qdp.py module .... Use when working on modules/m03 through modules/m10, their selftest packs, or their report/output surfaces under artifacts/. Do not use for tdgl-rf workflows or for the repo-level bootstrap/check sweep.
---

# Purpose

Operate the legacy module harness behind `python qdp.py module` for discovery, selftests, and direct module runs.

# Use when

- The task is to list supported modules or confirm a module key.
- The task is to run a module selftest pack.
- The task is to run one module directly with its required inputs and capture its report/output artifacts.

# Do not use when

- The task is the repo-level bootstrap/check sweep. Use `qdp-governance-check`.
- The task is any `tdgl-rf` simulation, validation, or evidence workflow.
- The task is a one-off candidate validation only.

# Inputs required

- Module key such as `m03`, `m05`, or `m10`.
- Module-specific inputs for direct runs:
  `--intake` for `m04`, `--candidate` for `m05` and `m07` through `m10`, optional `--mode` for `m03`, optional `--output`, `--report`, and `--stage-inputs`.

# Files and directories to inspect first

- `qdp.py`
- `qdp_paths.py`
- `docs/repo/module_registry.md`
- `modules/m03_reference_resolution/runner.py`
- `modules/m04_branch_registration/runner.py`
- `modules/m05_stage_machine/runner.py`
- `modules/m05_stage_machine/selftest_cases.json`
- `modules/m07_family_triage/selftest_cases.json`
- `modules/m08_baseline_fit/selftest_cases.json`
- `modules/m09_mechanism_competition/selftest_cases.json`
- `modules/m10_artifact_audit/selftest_cases.json`
- `artifacts/reports/`
- `artifacts/outputs/`

# Step-by-step procedure

1. Start with `python qdp.py module list` to confirm the module key and name.
2. For regression coverage on a supported module, run `python qdp.py module selftest <module>`.
3. For direct execution, inspect `qdp.py` and `qdp_paths.py` first to see the module-specific required arguments and default output locations.
4. Supply the required inputs for that module:
   `m03` uses its default manifest/registry/root and optional `--mode`;
   `m04` requires `--intake`;
   `m05` requires `--candidate` and optionally `--stage-inputs`;
   `m06` runs with no extra args;
   `m07` through `m10` require `--candidate`.
5. Inspect the written report and output candidate paths under `artifacts/reports/` and `artifacts/outputs/`.
6. Keep these legacy module outputs separate from the `tdgl-rf` run trees.

# Exact commands

```bash
python qdp.py module list
python qdp.py module selftest m05
python qdp.py module run m03 --mode ordinary
```

# Validation / definition of done

- `module list` prints the supported module keys and names.
- `module selftest <module>` exits successfully and writes the module’s selftest report and outputs.
- Direct `module run` writes the requested report and any output candidate files for the chosen module.
- For modules with required extra inputs such as `m04` or `m05`, the exact argument shape must come from `qdp.py` and `qdp_paths.py` for that module before execution.
- Written candidates still validate under the repo’s candidate schema and validator.

# Failure modes / escalation

- Unknown module key:
  Re-run `module list` and use the canonical key.
- Missing required module arguments:
  Supply the correct `--intake` or `--candidate` input instead of forcing the runner.
- Selftest not supported:
  Respect the module boundary; `m03`, `m04`, and `m06` do not expose the same selftest workflow.
- Report/output path confusion:
  Inspect `qdp_paths.py` and the module metadata before changing default locations.

# Output artifacts

- `artifacts/reports/m05/selftest_report.json`
- `artifacts/reports/m07/selftest_report.json`
- `artifacts/reports/m08/selftest_report.json`
- `artifacts/reports/m09/selftest_report.json`
- `artifacts/reports/m10/selftest_report.json`
- `artifacts/outputs/m05/selftests/...`
- `artifacts/outputs/m07/selftests/...`
- `artifacts/outputs/m08/selftests/...`
- `artifacts/outputs/m09/selftests/...`
- `artifacts/outputs/m10/selftests/...`

# Example prompts that SHOULD trigger the skill

- "List the supported legacy modules and run the m05 selftest pack."
- "Run the m04 branch-registration module on this intake file."
- "Execute the m03 reference-resolution module in ordinary mode."

# Example prompts that should NOT trigger the skill

- "Run the repo-level bootstrap and candidate sweep."
- "Run the deterministic phase-1 TDGL validation."
- "Execute the seeded-vortex Phase-2.2 suite."
