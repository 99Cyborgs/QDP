# QDP Repo Refactor Plan

## Why this needs to change

The current repo is difficult to work with from a normal engineering workflow because:

- source code, specs, generated reports, and generated outputs all live at the repo root
- filenames encode too much context directly in the filename instead of in directories
- module code uses one naming pattern (`run_qdp_*_Mxx.py`) while reports use another (`QDP_v10_6_Mxx_*`)
- the workflow is file-name driven instead of command-driven
- generated artifacts are treated like first-class source files in the same namespace
- module-local files are not grouped together, so reading or changing one module requires scanning the whole repo

## Refactor goals

1. Make the repo browsable without prior QDP-specific filename knowledge.
2. Make module work directory-driven instead of root-file-driven.
3. Separate source, config, specs, and generated artifacts.
4. Introduce a single top-level workflow entrypoint.
5. Preserve current recovery artifacts and legacy references until the migration is stable.

## Recommended canonical layout

```text
QDP/
  docs/
    repo/
    architecture/
  specs/
    core/
    intake/
    subsystem/
    research/
  config/
    schema/
    registries/
    manifests/
    contracts/
  modules/
    m03_reference_resolution/
      runner.py
      patch_notes.md
      fixtures/
    m04_branch_registration/
      runner.py
      patch_notes.md
      fixtures/
    m05_stage_machine/
      runner.py
      patch_notes.md
      fixtures/
    m06_bootstrap_harness/
      runner.py
      patch_notes.md
      fixtures/
    m07_family_triage/
      runner.py
      patch_notes.md
      fixtures/
    m08_baseline_fit/
      runner.py
      patch_notes.md
      fixtures/
    m09_mechanism_competition/
      runner.py
      patch_notes.md
      fixtures/
    m10_artifact_audit/
      runner.py
      patch_notes.md
      fixtures/
  tools/
    validators/
    workflow/
  artifacts/
    reports/
      m03/
      m05/
      m06/
      m07/
      m08/
      m09/
      m10/
      system/
    outputs/
      m05/
      m06/
      m07/
      m08/
      m09/
      m10/
  legacy/
    wrappers/
```

## Naming conventions

### Python source

- Use directory context plus simple names.
- Prefer:
  - `modules/m05_stage_machine/runner.py`
  - `modules/m06_bootstrap_harness/runner.py`
  - `tools/validators/candidate_validator.py`
- Avoid embedding full product/version/module context in every source filename.

### Specs and config

- Put human specs under `specs/`.
- Put machine-readable configuration under `config/`.
- Prefer descriptive lowercase snake_case names inside the correct directory.
- Examples:
  - `config/schema/candidate.schema.json`
  - `config/manifests/reference_manifest.json`
  - `config/registries/module_registry.json`

### Generated artifacts

- Generated reports belong under `artifacts/reports/`.
- Generated candidate outputs belong under `artifacts/outputs/`.
- Reports should be named by their function, not by the entire system lineage.
- Examples:
  - `artifacts/reports/m05/selftest_report.json`
  - `artifacts/reports/m06/bootstrap_report.json`
  - `artifacts/reports/system/module_closure_evaluation.json`
  - `artifacts/outputs/m09/selftests/...`

## Workflow conventions

### Desired workflow

The user should not need to remember exact filenames.

Preferred commands:

```text
python qdp.py module m05 selftest
python qdp.py module m10 selftest
python qdp.py bootstrap
python qdp.py validate candidate path/to/candidate.json --mode final
python qdp.py module m09 run --candidate path/to/input.json --output path/to/output.json
```

### Current problem

The current workflow is:

```text
python modules/m05_stage_machine/runner.py --selftest-cases ...
python modules/m06_bootstrap_harness/runner.py
python tools/validators/candidate_validator.py candidate.json --mode final
```

That is functional, but it is not intuitive for someone approaching the repo as code.

## Migration strategy

### Recommended: Compatibility-first migration

This is the recommended path.

- Create the canonical directory structure.
- Move or duplicate source into canonical module directories.
- Add a single top-level workflow CLI.
- Keep legacy root filenames as wrappers during the transition.
- Update the harness and module scripts to resolve canonical paths first.
- Continue exporting legacy artifact names until the rest of the repo stops depending on them.

Benefits:

- lowest breakage risk
- preserves current recovery state
- lets us improve the coding workflow immediately
- gives us a clean eventual path to remove legacy names

### Alternative: Hard rename / hard move

- Physically rename and relocate everything at once.
- Update all scripts, contracts, manifests, and reports in one pass.
- Remove root-level legacy names immediately.

Benefits:

- fastest path to a fully clean tree

Costs:

- much higher breakage risk
- harder to verify
- likely to invalidate current artifact references during the transition

## Recommended implementation phases

### Phase 1

- Add canonical repo conventions doc.
- Add a central workflow CLI.
- Add a path registry or module manifest so scripts stop hardcoding root filenames.
- Keep all legacy names working.

### Phase 2

- Move module source into `modules/`.
- Move validators into `tools/validators/`.
- Move self-test fixtures into module-local `fixtures/`.
- Move generated reports and outputs into `artifacts/`.
- Leave root wrappers behind.

### Phase 3

- Update closure contracts, registry references, and harness defaults to canonical paths.
- Make the CLI the primary documented workflow.
- Mark legacy root files as compatibility-only.

### Phase 4

- Remove legacy root wrappers only after the repo and reports no longer depend on them.

## Recommendation

Do not do a hard rename first.

Start with a compatibility-first overhaul:

1. canonical layout
2. central workflow CLI
3. root compatibility wrappers
4. progressive path migration

That gives a coding-friendly repo without destroying the current execution path.
