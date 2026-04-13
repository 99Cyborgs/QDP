# Monorepo Consolidation Status

This document is the current migration inventory for the QDP umbrella consolidation. It classifies active destination surfaces and any donor-era content that remains staged, superseded, app-only, or still under manual review.

## Migrated Into Active QDP Authority

- `packages/qdp_meta_materials/`
  - canonical materials and metamaterials package
  - active authority for typed material schemas, registry loading, registry validation, scoring, planning, provenance relevant to the materials system, and TDGL-facing material adapters
  - primary code donor: `staging/imported_mmm_studio/snapshot/src/mmm_studio/`
  - semantic lineage donor: `staging/imported_qdp_mm/snapshot/`
- `packages/qdp_tdgl/`
  - canonical TDGL runtime, workflow, solver, and runtime provenance authority
  - active code donor: `staging/imported_qdp_tdgl/snapshot/src/tdgl_rf/`
- `packages/qdp_io/`
  - canonical shared package-layer serialization and generic runtime metadata helper package
  - active authority for JSON, YAML, text, and CSV writing, object-root JSON loading, stable payload hashing, file SHA-256 helpers, legacy-compatible JSON artifact writing, shared artifact and module report-header helpers, shared module selftest-payload helpers, shared candidate result-summary report helpers, shared visible-source result-summary report helpers, the shared UTC timestamp helper, generic runtime snapshots, module-registry payload and markdown builders, and retained-reference provenance interpretation used by extracted packages, `M01`, qdp_control, subsystem tooling, migration tooling, and active runtime compatibility surfaces
- `packages/qdp_validation/`
  - canonical umbrella validation and interface-contract package
  - active authority for repo-consistency validation, frozen ALL-MIND interface validation, structural-versus-authoritative readiness gate semantics, bootstrap-facing module selftest orchestration, and module verification aggregation
- `packages/qdp_control/`
  - canonical umbrella control and orchestration package
  - active authority for queue/control-plane persistence, run-ledger state, campaign prepare/plan logic, and lab pack/ingest workflows
- `apps/mmm_studio/`
  - canonical CLI and API shell only
  - consumes `qdp_meta_materials`; it is not an authority for materials models, registry loading, scoring, or provenance
- `configs/tdgl/`
  - canonical TDGL config and schema surface
  - committed baselines now resolve materials through `qdp_meta_materials` via the `materials` block
- `configs/validation/tdgl/`
  - canonical TDGL validation manifests and thresholds
  - includes the rebased `seeded_vortex_phase2_4a_validation_manifest.yaml` for the extracted umbrella runtime
- `tests/unit/` and `tests/integration/`
  - active package and shell smoke coverage for the extracted materials package, TDGL runtime, MMM Studio shell, and the materials-to-TDGL boundary

## Staged For Later Review

- `staging/imported_qdp_mm/`
  - preserved for semantic lineage, branch-protocol reference material, and later selective extraction into `labs/materials/` or future package surfaces
- `staging/imported_mmm_studio/`
  - preserved as the traceable donor snapshot after extracting reusable package code and the shell surface
- `staging/imported_qdp_tdgl/`
  - preserved as the traceable donor snapshot after extracting the active `qdp_tdgl` runtime
  - donor-root wrappers and legacy control shells remain staged only and are not active authorities

## Final Staging Classification

### `staging/imported_qdp_mm/`

- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/analysis/`
  - `staged for later review`
  - branch-specific analysis protocol and lineage material for possible `labs/materials/` extraction
- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/competition/`
  - `staged for later review`
  - branch-specific mechanism-competition notes; not canonical materials scoring authority
- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/execution_queue/`
  - `non-reusable`
  - donor-local queue mechanics superseded by `packages/qdp_control/`
- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/failures/`
  - `archived`
  - donor forensic notes retained for chronology only
- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/handoff/`
  - `archived`
  - donor handoff notes retained for chronology only
- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/intake/`
  - `staged for later review`
  - lineage and branch-protocol inputs; not active materials registry seed authority
- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/protocols/`
  - `staged for later review`
  - semantic lineage and conservative branch-state vocabulary donor
- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/simulation/`
  - `staged for later review`
  - branch-specific synthetic studies; possible future `labs/materials/` content
- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/specs/`
  - `archived`
  - donor narrative/spec material retained for chronology and semantic traceability
- `snapshot/qdp/branches/e01_mm_flux_history_hysteresis/manifest.json`
  - `archived`
  - donor manifest retained for traceability only

### `staging/imported_mmm_studio/`

- `snapshot/src/mmm_studio/api.py`, `snapshot/src/mmm_studio/cli.py`, `snapshot/src/mmm_studio/api_models.py`, `snapshot/src/mmm_studio/__main__.py`
  - `app-only`
  - donor shell reference superseded by `apps/mmm_studio/`
- remaining reusable library code under `snapshot/src/mmm_studio/`
  - `superseded`
  - canonical authority now lives in `packages/qdp_meta_materials/`
- `snapshot/data/mmm_seed/`
  - `superseded`
  - stable and experimental seed authority now lives under `packages/qdp_meta_materials/data/seed/`
- `snapshot/examples/rf/` and `snapshot/examples/sweeps/`
  - `staged for later review`
  - candidate source examples for `labs/materials/`
- `snapshot/examples/demo_run/`
  - `archived`
  - donor run output and generated evidence retained for traceability only
- `snapshot/docs/`
  - `archived`
  - donor design narrative retained as migration reference, not active authority
- `snapshot/tests/`
  - `staged for later review`
  - donor test bank for selective future promotion into active unit/integration/scientific layers
- `.github/`, packaging files, contribution files, and repo-local policy files
  - `non-reusable`
  - donor repo administration retained for provenance only

### `staging/imported_qdp_tdgl/`

- `snapshot/src/tdgl_rf/`
  - `superseded`
  - canonical runtime authority now lives in `packages/qdp_tdgl/`
- `snapshot/configs/` and `snapshot/validation/`
  - `superseded`
  - canonical config and validation authority now lives in `configs/tdgl/` and `configs/validation/tdgl/`
- `snapshot/tests/unit/`
  - `staged for later review`
  - donor unit-bank beyond the promoted CLI/config/runtime slices
- `snapshot/tests/integration/`
  - `staged for later review`
  - donor integration-bank beyond the promoted materials-to-TDGL and rebased workflow slices
- `snapshot/tests/acceptance/` and `snapshot/tests/regression/`
  - `staged for later review`
  - high-cost scientific and acceptance suites not yet promoted into the active umbrella gate
- donor-root `qdp.py`, `qdp_validation.py`, `modules/`, `tools/`, `config/`, `runtime/`, and duplicate governance docs
  - `superseded`
  - donor-local duplicate QDP control surfaces; not active runtime authority
- `snapshot/specs/`, `snapshot/docs/`, `snapshot/ornl_tdgl_codex_pack/`, `snapshot/matrices/`
  - `archived`
  - donor research and planning references retained for chronology and traceability
- `.agents/`, `.gitattributes`, `.gitignore`, repo-local packaging notes, and donor-local patches
  - `non-reusable`
  - donor repo administration or local scaffolding retained for provenance only
- `snapshot/RL framework/` and `snapshot/ornl_tdgl_codex_pack.zip`
  - `archived`
  - retained traceability bundles; not part of active authority

## Superseded Active Surfaces

- `qdp_meta_materials.io.load_dataset`
  - superseded by `qdp_meta_materials.registry.load_dataset`
  - `io.py` is now serialization-only so there is one canonical materials registry loader surface
- copied TDGL material parameters in committed baseline configs
  - superseded by `configs/tdgl/*.yaml` `materials` blocks resolved through `qdp_meta_materials.adapters.tdgl`
  - the active TDGL baselines no longer keep a second copied authority for `physics.u`, `physics.sigma_n`, or `physics.alpha_background`
- generic file/hash helpers in `tools/workflow/qdp_runtime/qdp_artifact_contracts.py`
  - superseded by `packages/qdp_io/src/qdp_io/artifacts.py`
  - `qdp_artifact_contracts.py` now remains only as a compatibility facade over `qdp_io` and `qdp_validation`
- module-registry payload and markdown builders in `tools/workflow/qdp_runtime/qdp_registry.py`
  - superseded by `packages/qdp_io/src/qdp_io/module_registry.py`
  - `qdp_registry.py` now remains only as a compatibility facade that adapts `qdp_paths.py` constants into the shared builder surface
- bootstrap-facing module selftest orchestration in `tools/workflow/qdp_runtime/qdp_module_workflows.py`
  - superseded by `packages/qdp_validation/src/qdp_validation/module_workflows.py`
  - `qdp_module_workflows.py` now remains only as a compatibility facade over `qdp_validation`
- module verification aggregation in `tools/workflow/qdp_runtime/qdp_module_verification.py`
  - superseded by `packages/qdp_validation/src/qdp_validation/module_verification.py`
  - `qdp_module_verification.py` now remains only as a compatibility facade over `qdp_validation`
- object-root JSON loading in `tools/workflow/qdp_runtime/qdp_module_sdk.py`, `tools/workflow/qdp_runtime/qdp_subsystem.py`, and `tools/workflow/qdp_runtime/qdp_cli.py`
  - superseded by `packages/qdp_io/src/qdp_io/serialization.py`
  - those runtime-shell surfaces now delegate shared object-root JSON loading to `qdp_io`
- retained-reference provenance lookup and authoritative-binding logic in `modules/m06_bootstrap_harness/runner.py` and `packages/qdp_control/src/qdp_control/run_ledger.py`
  - superseded by `packages/qdp_io/src/qdp_io/reference_manifest.py`
  - the bootstrap harness and run ledger now delegate to the shared helper instead of keeping a second retained-reference interpretation rule
- local JSON artifact writers in `modules/m01_runtime_assembly/runner.py`, `tools/migration/repo_audit.py`, and `tools/migration/write_migration_manifests.py`
  - superseded by `packages/qdp_io/src/qdp_io/artifacts.py`
  - those active paths now delegate generic artifact writing to the shared package helper
- local JSON artifact writers in the active visible-source module runners `M02`, `M04`, `M05`, and `M07`-`M15`
  - superseded by `packages/qdp_io/src/qdp_io/artifacts.py`
  - those module runners now delegate generic artifact writing to the shared package helper instead of keeping per-runner copies
- local `utc_now()` helpers in `packages/qdp_control/`, `tools/workflow/qdp_runtime/qdp_subsystem.py`, `tools/migration/repo_audit.py`, and `tools/migration/write_migration_manifests.py`
  - superseded by `packages/qdp_io/src/qdp_io/artifacts.py`
  - those active control and audit surfaces now delegate shared UTC timestamp generation to `qdp_io`
- inline `datetime.now(timezone.utc).isoformat()` timestamp generation in the active module runner path `M01`-`M15`, including `M03` and `M06`
  - superseded by `packages/qdp_io/src/qdp_io/artifacts.py`
  - those active module/report surfaces now delegate shared `timestamp_utc` generation to `qdp_io`
- inline artifact-report and module-report header construction on the active module runner path, `qdp_subsystem`, queue reporting, run-ledger reporting, and migration/audit reporting
  - superseded by `packages/qdp_io/src/qdp_io/artifacts.py`
  - those active report surfaces now delegate shared leading-header construction to `qdp_io`
- inline module selftest summary payload construction on `M01`, `M02`, `M04`, `M05`, `M07`-`M15`, and `tools/workflow/qdp_runtime/qdp_subsystem.py`
  - superseded by `packages/qdp_io/src/qdp_io/artifacts.py`
  - those active selftest surfaces now delegate shared `cases_total`, `cases_passed`, `all_passed`, and optional metadata payload construction to `qdp_io`
- inline `candidate_id` plus `result_summary` report-envelope construction on `M11`-`M15`
  - superseded by `packages/qdp_io/src/qdp_io/artifacts.py`
  - those active module report surfaces now delegate the shared candidate-summary envelope to `qdp_io`
- inline `visible_source_only` plus `result_summary` report-envelope construction on `M07`-`M10`
  - superseded by `packages/qdp_io/src/qdp_io/artifacts.py`
  - those active visible-source module report surfaces now delegate the shared visible-source envelope to `qdp_io`

## App-Only Surfaces

- `apps/mmm_studio/src/mmm_studio/cli.py`
- `apps/mmm_studio/src/mmm_studio/api.py`
- `apps/mmm_studio/src/mmm_studio/api_models.py`
- `apps/mmm_studio/src/mmm_studio/__main__.py`

These files are shell-only entrypoints. They must continue consuming package APIs rather than re-owning domain logic.

## Generated Or Operational Evidence, Not Source Authority

- `artifacts/reports/`
  - generated validation, module, and system reports
- `runs/phase2_4a_validation/`
  - generated runtime-validation outputs from the rebased same-stack Phase-2.4A validation runs
- any future experiment or run directories under `runs/`

These outputs are valid evidence surfaces, but they are not governing source code or schema authority and must stay out of package source trees.

## Manual Review Still Required

- broader `packages/qdp_io/` scope
  - shared manifest contracts, artifact ledgers, and reusable provenance schemas are not fully extracted yet
- broader imported scientific and integration suites
  - the highest-value unit surfaces and the Phase-2.4A same-stack validation were migrated and rebased, but the full donor-wide scientific suite has not been exhaustively ported

## Active Validation Scope

### Promoted Into The Canonical Umbrella Gate

- `python scripts/run_repo_validation.py`
  - canonical umbrella validation runner
- package-level smoke surfaces listed in `AGENTS.md`
  - `qdp_io`
  - `qdp_validation`
  - `qdp_control`
  - `qdp_meta_materials`
  - `qdp_tdgl`
  - `apps/mmm_studio`
- `tests/integration/test_tdgl_material_registry_integration.py`
  - active package-boundary integration proof for materials-to-TDGL resolution
- rebased same-stack Phase-2.4A evidence surface under `runs/phase2_4a_validation/`
  - retained as active scientific evidence, but not rerun by the default umbrella gate

### Intentionally Left Staged

- `staging/imported_mmm_studio/snapshot/tests/`
  - donor materials test bank beyond the promoted smoke slices
- `staging/imported_qdp_tdgl/snapshot/tests/unit/`
  - donor TDGL unit-bank beyond the promoted config and CLI/runtime slices
- `staging/imported_qdp_tdgl/snapshot/tests/integration/`
  - donor TDGL workflow integration bank beyond the promoted rebased umbrella slices
- `staging/imported_qdp_mm/snapshot/qdp/branches/e01_mm_flux_history_hysteresis/**/test_*.py`
  - branch-pack tests retained with lineage material rather than promoted into active umbrella authority

### Out Of Scope For The Default Closure Gate

- donor-wide acceptance and regression packs under `staging/imported_qdp_tdgl/snapshot/tests/acceptance/` and `staging/imported_qdp_tdgl/snapshot/tests/regression/`
  - high-cost scientific suites not required for structural consolidation closure
- donor-local repo CI, admin, and packaging checks under staged `.github/` and donor root repo scaffolds
  - not part of the active umbrella validation contract
