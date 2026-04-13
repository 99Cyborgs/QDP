# Validation

## Primary check

```bash
python scripts/run_repo_validation.py
```

Canonical behavior:

- runs the authoritative-readiness regression test `tests/test_authoritative_readiness.py`,
- runs the repo-consistency sweep through `python qdp_validation.py`,
- requires emission of `artifacts/reports/system/repo_validation_report.json`,
- requires emission of `artifacts/reports/system/all_mind_interface.json`, and
- requires `artifacts/reports/system/all_mind_interface.json` to validate against `config/schema/all_mind_interface_schema.json`, and
- reports structural consistency separately from authoritative readiness.

Use `--require-authoritative-ready` when the task is a true staging gate or portfolio drill.

## Underlying validator

```bash
python qdp_validation.py
```

This is the repo-level consistency sweep. It:

- reruns the post-overhaul audit,
- validates generated candidate artifacts under `artifacts/outputs/`,
- emits `artifacts/reports/system/repo_validation_report.json`,
- can emit `artifacts/reports/system/all_mind_interface.json`, and
- exits `0` when the repository is structurally consistent even if the authoritative-readiness gates are still unmet.

Authoritative blockers stay visible in the report and do not count as a false pass for testing readiness. The canonical runner can now fail directly on authoritative-readiness regressions by adding `--require-authoritative-ready`.

Module verification evidence is module-specific. Selftest-backed modules report through selftest artifacts, while `M01` is verified through assembly and closure reports, `M03` through strict reference-resolution reports, and `M06` through bootstrap-harness evidence.

`module_verification` is the governing summary for those module-level checks. Any emitted `module_selftests` field is a deprecated compatibility alias and must not be treated as proof that every module is selftest-backed.

## Active consolidation validation surface

Promoted into the active umbrella validation surface:

- `python scripts/run_repo_validation.py`
- package smoke tests listed in `AGENTS.md`
- `tests/integration/test_tdgl_material_registry_integration.py`

Intentionally left staged for selective later promotion:

- donor-wide `MMM-Studio` tests under `staging/imported_mmm_studio/snapshot/tests/`
- donor-wide `QDP TDGL` unit, integration, acceptance, and regression suites beyond the already-promoted config, CLI, run-case-output, and material-registry slices
- donor-local `QDP MM` branch-pack tests retained with branch lineage material

High-cost scientific evidence that remains outside the default closure gate:

- donor acceptance and regression packs under `staging/imported_qdp_tdgl/snapshot/tests/acceptance/` and `staging/imported_qdp_tdgl/snapshot/tests/regression/`
- rebased same-stack Phase-2.4A evidence under `runs/phase2_4a_validation/` remains valid evidence, but it is not rerun by the canonical repo validator

## Operational checks

```bash
python qdp.py module list
python qdp.py readiness
python qdp.py module selftest all
python qdp.py bootstrap
python qdp.py module run m05 --candidate path/to/input.json --stage-inputs path/to/stage_inputs.json --batch batch_a --variant variant_1
python qdp.py check --batch batch_a --skip-bootstrap
python qdp.py campaign prepare --batch batch_a
python qdp.py campaign plan --batch batch_a
python qdp.py queue enqueue --manifest artifacts/state/queue_manifests/example.json
python qdp.py queue run --once
python qdp.py queue list
python qdp.py queue show <queue_id>
python qdp.py queue log <queue_id>
python qdp.py validate artifacts/reports/system/all_mind_interface.json --kind all-mind-interface
```

Partitioned simulation batches default to generated artifact namespaces under `artifacts/outputs/simulations/`, `artifacts/reports/simulations/`, `artifacts/lab/requests/`, and `artifacts/lab/ingestions/`.
Campaign planning now consumes prepared `M12` candidates rather than raw source candidates. If a source candidate changes, rerun `python qdp.py campaign prepare ...` before rerunning `python qdp.py campaign plan ...`.
Queue triage is operator-local: `queue list` to find candidates, `queue show` to inspect current state and failure history, `queue log` to inspect transitions and manual interventions, then `queue retry`, `queue unblock --force`, or `queue cancel` as needed.

## Generated validation artifacts

- `artifacts/reports/system/pre_overhaul_blocker_ledger.json`
- `artifacts/reports/system/post_overhaul_blocker_ledger.json`
- `artifacts/reports/system/path_migration_report.json`
- `artifacts/reports/system/repo_validation_report.json`
- `artifacts/reports/system/all_mind_interface.json`
- `artifacts/reports/system/queue_report.json`

## Additional review

- confirm `STATUS.md`, `PROMOTION_NOTES.md`, and `REPO_MAP.md` still match the repo layout,
- confirm `module_verification` and any propagated `closure_limitations` remain truthful to the current generated reports,
- confirm `artifacts/reports/system/all_mind_interface.json` still matches the frozen contract in `INTEGRATION_PLAN.md`,
- confirm `structural_consistency_passed` is not described as authoritative readiness anywhere in the control-plane-facing docs,
- confirm new generated outputs do not become implicit source-of-truth documents,
- confirm queue manifests, queue logs, and `artifacts/reports/system/queue_report.json` remain repo-local operator state rather than ALL-MIND contract surfaces,
- confirm partitioned simulation batches remain under generated artifact paths and do not become governing inputs,
- confirm `artifacts/reports/campaigns/latest_prepare.json` and `artifacts/reports/campaigns/latest_plan.json` remain the active campaign report outputs rather than any legacy system-level campaign snapshot,
- confirm `legacy/docs/archive/` remains archival history and is not reintroduced as an active truth surface,
- confirm any ALL-MIND integration note still points to a narrow interface, not whole-repo ingestion.
