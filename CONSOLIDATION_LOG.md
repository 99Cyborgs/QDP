# Consolidation Log

## 2026-04-10 - Phase 1 forensic audit

- Read the QDP authority files in the repo-defined order:
  - `AGENTS.md`
  - `README.md`
  - `SYSTEM_BOUNDARY.md`
  - `STATUS.md`
  - `REPO_MAP.md`
  - `VALIDATION.md`
  - `QDP_REPO_REFACTOR_PLAN.md`
- Confirmed the current QDP canonical validation entrypoint is `python scripts/run_repo_validation.py`.
- Inspected the four sibling repositories:
  - `QDP/`
  - `QDP MM/`
  - `MMM-Studio/`
  - `QDP TDGL/`
- Confirmed current repo roles from observed files:
  - `QDP` is already the destination governance and orchestration surface.
  - `MMM-Studio` is the strongest typed materials and metamaterials donor.
  - `QDP MM` is a semantic and branch-protocol donor, not a full reusable materials package.
  - `QDP TDGL` is the strongest TDGL runtime donor and already ships an active packaged runtime under `src/tdgl_rf/`.
- Confirmed no comparable packaged TDGL runtime authority is currently present in `QDP/`; current overlaps there are governance, candidate, and campaign surfaces rather than a solver package.
- Confirmed all three donor repos are standalone git repositories, so history-preserving staging should be feasible in a later phase.
- Wrote `CONSOLIDATION_PLAN.md` with:
  - the subsystem overlap matrix
  - winner selections
  - proposed landing targets
  - staging, archive, and supersession calls
- No large-scale moves, imports, deletions, or refactors were performed in this phase.
- No existing files were reverted.
- Worktree note: the QDP repo was already dirty before these Phase 1 additions; this phase intentionally avoided normalizing unrelated changes.

## Next planned phase

- Create the target monorepo skeleton inside `QDP/`.
- Stage sibling repos under `staging/` without losing traceability.
- Begin extraction only after the staging roots and package boundaries exist.

## 2026-04-10 - Phase 2 target skeleton

- Added the consolidation-era tracked skeleton inside `QDP/`:
  - `packages/`
  - `apps/`
  - `labs/`
  - `configs/`
  - `docs/adr/`
  - `docs/migration/`
  - `staging/`
  - `tests/unit/`
  - `tests/integration/`
  - `tests/scientific/`
- Added a minimal root `pyproject.toml` as the umbrella workspace manifest.
- Updated `REPO_MAP.md` to describe:
  - destination ownership zones
  - current active transitional implementation surfaces
  - donor winner notes
- Updated `AGENTS.md` to add:
  - consolidation-specific read order
  - package uniqueness rules
  - app-shell separation rules
  - canonical and donor-local validation commands
- No donor repo contents were imported in this phase.
- No active runtime code was moved in this phase.
- No files were deleted in this phase.

## 2026-04-10 - Phase 3 staged donor imports

- Imported donor working-tree snapshots under:
  - `staging/imported_qdp_mm/snapshot/`
  - `staging/imported_mmm_studio/snapshot/`
  - `staging/imported_qdp_tdgl/snapshot/`
- Recorded donor traceability metadata in each staging root:
  - source path
  - donor branch
  - donor HEAD
  - donor cleanliness at import time
  - approximate staged file count
  - snapshot exclusions
- Recorded the deferred clean-branch history-preserving subtree procedure in `docs/migration/STAGING_IMPORT_HISTORY_COMMANDS.md`.
- Important caveat recorded: `QDP TDGL` was dirty at import time, so the staged snapshot contains uncommitted donor changes that are not represented by the committed donor SHA alone.
- No extraction into canonical packages was performed in this phase.
- No staged donor content was deleted in this phase.

## 2026-04-10 - Phase 4 initial qdp_meta_materials extraction

- Extracted the reusable materials core from the staged `MMM-Studio` donor into `packages/qdp_meta_materials/`.
- Promoted the following donor surfaces into the canonical package source tree:
  - typed models
  - typed registry loading
  - registry validation
  - scoring and ranking
  - run and provenance helpers
  - sweep and tranche planning
  - RF and simulation adapter scaffolds
- Kept `MMM-Studio` shell-owned files out of the package:
  - `api.py`
  - `api_models.py`
  - `cli.py`
  - `__main__.py`
- Copied stable materials seed data into `packages/qdp_meta_materials/data/seed/stable/`.
- Added package-level subarea facades and landing zones:
  - `schemas/`
  - `planning/`
  - `provenance/`
  - `adapters/`
  - `stable/`
  - `experimental/`
- Preserved QDP MM semantics as lineage notes in `packages/qdp_meta_materials/data/seed/experimental/qdp_mm_e01_lineage/README.md`.
- Added package-level validation guidance and a central smoke test:
  - `packages/qdp_meta_materials/README.md`
  - `tests/unit/test_qdp_meta_materials_smoke.py`
- Validated the extracted package by:
  - importing it from `packages/qdp_meta_materials/src`
  - loading and validating the stable seed dataset
  - scoring the dataset
  - running `python -m pytest tests/unit/test_qdp_meta_materials_smoke.py -q` with `PYTHONPATH=packages/qdp_meta_materials/src`
- No donor staging content was deleted in this phase.
- No app shell extraction was performed in this phase.

## Next planned phase

- Begin Phase 5 by extracting and reconciling the canonical TDGL runtime into `packages/qdp_tdgl/`.
- Keep `packages/qdp_meta_materials/` as the only materials authority while `apps/mmm_studio/` is refactored into a thin shell in a later phase.
- Decide which generic provenance contracts from `qdp_meta_materials` should move further into `qdp_io/` once the TDGL runtime extraction is underway.

## 2026-04-10 - Phase 5 initial qdp_tdgl extraction

- Extracted the staged `QDP TDGL` runtime package into `packages/qdp_tdgl/src/qdp_tdgl/`.
- Promoted the following donor surfaces into the canonical runtime package:
  - solver entrypoints
  - runtime workflows
  - runtime config loaders and validators
  - TDGL-specific IO, diagnostics, geometry, and solver code
- Copied canonical TDGL config assets into:
  - `configs/tdgl/`
  - `configs/validation/tdgl/`
- Rewired the extracted runtime so package-local lookup resolves:
  - the QDP monorepo root
  - canonical TDGL schema paths under `configs/tdgl/`
  - canonical TDGL validation manifests under `configs/validation/tdgl/`
- Added package metadata and extraction guidance:
  - `packages/qdp_tdgl/pyproject.toml`
  - `packages/qdp_tdgl/README.md`
- Preserved the donor CLI name as a compatibility alias, but moved the canonical extracted command name to `qdp-tdgl`.
- Kept donor root wrappers and duplicate QDP-style control surfaces out of the active extraction:
  - root `qdp.py`
  - root `qdp_validation.py`
  - donor `modules/`
  - donor `tools/`
  - donor `artifacts/`
- Added copied unit test surfaces for the extracted runtime:
  - `tests/unit/test_qdp_tdgl_config.py`
  - `tests/unit/test_qdp_tdgl_cli.py`
- Updated imported TDGL validation manifests so they reference:
  - `configs/tdgl/`
  - `configs/validation/tdgl/`
  - `qdp-tdgl` as the canonical command string
- Validated the extracted runtime by:
  - importing it from `packages/qdp_tdgl/src`
  - loading `configs/tdgl/d01_smoke.yaml`
  - confirming canonical schema and validation roots resolve inside QDP
  - running `$env:PYTHONPATH = "packages/qdp_tdgl/src"; python -m pytest tests/unit/test_qdp_tdgl_config.py tests/unit/test_qdp_tdgl_cli.py -q`
  - running `python scripts/run_repo_validation.py`
- No donor staging content was deleted in this phase.
- No app-shell separation was performed in this phase.

## Next planned phase

- Begin Phase 6 by extracting `apps/mmm_studio/` as a thin shell that consumes `qdp_meta_materials` and the other QDP packages.
- Continue narrowing duplicate donor surfaces by keeping staged TDGL legacy wrappers quarantined until they can be explicitly classified as archived or superseded.
- Decide which TDGL provenance helpers remain runtime-local versus moving into a later `qdp_io/` extraction.

## 2026-04-10 - Phase 6 initial apps/mmm_studio shell extraction

- Extracted the staged `MMM-Studio` shell files into `apps/mmm_studio/src/mmm_studio/`.
- Promoted only shell-owned surfaces:
  - `cli.py`
  - `api.py`
  - `api_models.py`
  - `__main__.py`
  - package metadata and minimal compatibility shims
- Rewired the shell so it consumes reusable package logic from `packages/qdp_meta_materials/`:
  - dataset loading
  - registry validation
  - scoring and leaderboard generation
  - run-manifest handling
  - planning and sweep execution
  - reporting helpers
- Added thin shell compatibility modules:
  - `apps/mmm_studio/src/mmm_studio/config.py`
  - `apps/mmm_studio/src/mmm_studio/errors.py`
- Added app packaging and shell ownership documentation:
  - `apps/mmm_studio/pyproject.toml`
  - `apps/mmm_studio/README.md`
- Added shell smoke tests:
  - `tests/unit/test_mmm_studio_app_api.py`
  - `tests/unit/test_mmm_studio_app_cli.py`
- Validated the extracted shell by running:
  - `$env:PYTHONPATH = "apps/mmm_studio/src;packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_mmm_studio_app_api.py tests/unit/test_mmm_studio_app_cli.py -q`
- No materials domain logic was copied into the app shell in this phase.
- No staged donor content was deleted in this phase.

## Next planned phase

- Begin Phase 7 by wiring `qdp_tdgl` configs to resolve materials through `qdp_meta_materials` registry references instead of duplicated ad hoc parameter blobs where practical.
- Continue isolating future shared provenance and serialization extraction targets for `qdp_io/`.
- Keep donor staging roots intact until every remaining overlap is explicitly classified as archived, superseded, app-only, or staged for later review.

## 2026-04-10 - Phase 7 TDGL materials wiring

- Added the active TDGL adapter registry and resolver to `packages/qdp_meta_materials/`:
  - `src/qdp_meta_materials/adapters/tdgl/`
  - `data/seed/stable/mmm_tdgl_material_adapter_registry.yaml`
- Rewired `qdp_tdgl` config validation so a case can supply a `materials` block that resolves canonical TDGL runtime parameters through `qdp_meta_materials`.
- Preserved runtime-side type strength by resolving material references before parsing the final `TDGLRFCaseConfig`.
- Updated the committed TDGL baselines in `configs/tdgl/` so the canonical examples no longer keep a second copied source of truth for:
  - `physics.u`
  - `physics.sigma_n`
  - `physics.alpha_background`
- Updated TDGL expanded-config and provenance surfaces so they retain the material-registry identity alongside the runtime context.
- Fixed imported validation-config `base_config` paths under `configs/validation/tdgl/` so they resolve against the canonical `configs/tdgl/` surface inside QDP.
- Rebased the committed Phase-2.4A validation manifest `base_case_hash` to match the new material-reference contract.
- Rebased the full committed Phase-2.4A frozen expected surface from the observed same-stack validation run so:
  - `parent_manifest_hash`
  - ensemble identifiers
  - fixed noise seeds
  - aggregate expectations
  - member provenance projections
  now match the extracted umbrella runtime rather than the donor-era contract snapshot.
- Added tests covering:
  - TDGL adapter resolution in `qdp_meta_materials`
  - TDGL config resolution from a material reference
  - rejection of copied-parameter drift against the canonical adapter
  - TDGL provenance material-registry identity recording
- Confirmed the rebased same-stack Phase-2.4A validation surface passes with `mismatch_count=0`.
- No donor staging content was deleted in this phase.
- No second materials parameter authority was left active in the TDGL baselines.

## Next planned phase

- Begin Phase 8 by tightening cleanup, dead-wrapper classification, and broader integration/scientific validation around the extracted package surfaces.
- Continue isolating future shared provenance and serialization extraction targets for `qdp_io/`.
- Keep donor staging roots intact until every remaining overlap is explicitly classified as archived, superseded, app-only, or staged for later review.

## 2026-04-10 - Phase 8 cleanup and validation hardening

- Collapsed the active materials-loader surface so `qdp_meta_materials.registry.load_dataset` is the one canonical materials registry loader and `qdp_meta_materials.io` now contains serialization helpers only.
- Rewired repo-internal consumers in:
  - `packages/qdp_meta_materials/`
  - `apps/mmm_studio/`
  - `tests/unit/`
  so there is no second in-repo materials loader authority.
- Added `tests/integration/test_tdgl_material_registry_integration.py` to verify that the canonical TDGL baseline:
  - carries a `materials` block instead of copied material parameters
  - resolves TDGL runtime parameters through `qdp_meta_materials`
  - records the materials registry identity in runtime provenance
- Added `docs/migration/MONOREPO_CONSOLIDATION_STATUS.md` to classify the current umbrella state into:
  - migrated
  - staged for later review
  - superseded
  - app-only
  - generated evidence
  - manual review still required
- Updated guidance files so future sessions have an explicit canonical loader boundary and a concrete migration inventory:
  - `AGENTS.md`
  - `REPO_MAP.md`
  - `docs/migration/README.md`
- Extracted `packages/qdp_io/` as an active shared package-layer authority for:
  - JSON, YAML, text, and CSV serialization
  - generic runtime metadata snapshots used in provenance payloads
- Rewired active extracted package consumers in:
  - `packages/qdp_meta_materials/`
  - `packages/qdp_tdgl/`
  - `apps/mmm_studio/`
  so shared serialization no longer lives as a duplicated active implementation in each package.
- Left `qdp_meta_materials/io.py` and `qdp_tdgl/io/reports.py` as compatibility facades only.
- No donor staging content was deleted in this phase.
- No package source trees were used to store run outputs or bulky generated data.

## Next planned phase

- Extract non-runtime orchestration into `packages/qdp_control/` after the package boundary is explicit enough to avoid re-owning TDGL or materials logic.
- Continue the broader `qdp_io` extraction for manifest contracts, artifact ledgers, and reusable provenance schemas without duplicating runtime-local TDGL details.
- Continue classifying staged donor long-tail content into `archived`, `staged for later review`, `app-only`, or `non-reusable`.

## 2026-04-11 - Phase 8 qdp_validation extraction

- Extracted `packages/qdp_validation/` as the active umbrella validation authority for:
  - repo-consistency validation
  - frozen ALL-MIND interface validation
  - structural-consistency versus authoritative-readiness gate semantics
- Promoted the implementation previously living in `tools/workflow/qdp_runtime/qdp_validation.py` into:
  - `packages/qdp_validation/src/qdp_validation/repo_consistency.py`
  - `packages/qdp_validation/src/qdp_validation/artifact_contracts.py`
- Converted the following repo-root and runtime paths into compatibility facades over the package:
  - root `qdp_validation.py`
  - `tools/workflow/qdp_runtime/qdp_validation.py`
  - validation-facing portions of `tools/workflow/qdp_runtime/qdp_artifact_contracts.py`
- Rewired `scripts/run_repo_validation.py` so the canonical repo validator imports the extracted package directly rather than the runtime copy.
- Added direct package smoke coverage in `tests/unit/test_qdp_validation_smoke.py`.
- No materials-registry validation or TDGL runtime-config validation was moved into `qdp_validation`; those ownership boundaries remain with `qdp_meta_materials` and `qdp_tdgl`.
- No donor staging content was deleted in this phase.

## Next planned phase

- Continue the broader `qdp_io` extraction for manifest contracts, artifact ledgers, and reusable provenance schemas without duplicating runtime-local TDGL details.
- Continue classifying staged donor long-tail content into `archived`, `staged for later review`, `app-only`, or `non-reusable`.

## 2026-04-11 - Phase 8 qdp_control extraction

- Extracted `packages/qdp_control/` as the active umbrella control authority for:
  - queue/control-plane persistence
  - run-ledger state
  - campaign prepare/plan workflows
  - lab pack/ingest orchestration
- Promoted the implementation previously living in:
  - `tools/workflow/qdp_runtime/qdp_control_plane.py`
  - `tools/workflow/qdp_runtime/qdp_run_ledger.py`
  - `tools/workflow/qdp_runtime/qdp_campaign_planner.py`
  - `tools/workflow/qdp_runtime/qdp_queue.py`
  - `tools/workflow/qdp_runtime/qdp_lab_workflows.py`
  into `packages/qdp_control/src/qdp_control/`.
- Converted those runtime paths into compatibility facades over the package.
- Rewired `tools/workflow/qdp_runtime/qdp_cli.py` so the active command shell consumes `qdp_control` directly.
- Updated the queue and branch-sweep tests to target the extracted package boundary rather than the old runtime implementation paths.
- Added direct package smoke coverage in `tests/unit/test_qdp_control_smoke.py`.
- No TDGL runtime logic or materials logic was moved into `qdp_control` in this phase.
- No donor staging content was deleted in this phase.

## Next planned phase

- Continue the broader `qdp_io` extraction for manifest contracts, artifact ledgers, and reusable provenance schemas without duplicating runtime-local TDGL details.
- Continue later `qdp_core` cleanup for shared contracts and utilities that still sit in the transitional runtime layer.
- Continue classifying staged donor long-tail content into `archived`, `staged for later review`, `app-only`, or `non-reusable`.

## 2026-04-11 - Phase 8 qdp_io helper extraction hardening

- Broadened `packages/qdp_io/` beyond serialization and runtime metadata by adding:
  - stable payload hashing
  - file SHA-256 helpers
  - legacy-compatible JSON artifact writing
- Promoted the generic file/hash helper portions previously living in `tools/workflow/qdp_runtime/qdp_artifact_contracts.py` into `packages/qdp_io/src/qdp_io/artifacts.py`.
- Rewired active consumers to import generic helper surfaces directly from `qdp_io` and validation surfaces from `qdp_validation`:
  - `packages/qdp_control/`
  - `tools/workflow/qdp_runtime/qdp_cli.py`
  - `tools/workflow/qdp_runtime/qdp_subsystem.py`
  - queue/control tests
- Reduced `tools/workflow/qdp_runtime/qdp_artifact_contracts.py` to a compatibility facade over `qdp_io` and `qdp_validation`.
- Fixed the `qdp_control` runtime compatibility wrappers so they bootstrap:
  - `packages/qdp_control/src`
  - `packages/qdp_io/src`
  - `packages/qdp_validation/src`
  when imported through legacy runtime paths.
- Added direct `qdp_io` smoke coverage for artifact dump/hash helpers in `tests/unit/test_qdp_io_smoke.py`.
- No frozen ALL-MIND interface schema, readiness contract, or TDGL/materials authority boundary changed in this phase.

## Next planned phase

- Continue broader reusable provenance and manifest-schema extraction without mixing it into shell or runtime-entrypoint rewrites.
- Continue later `qdp_core` cleanup for shared contracts and utilities that still sit in the transitional runtime layer.
- Continue classifying staged donor long-tail content into `archived`, `staged for later review`, `app-only`, or `non-reusable`.

## 2026-04-11 - Phase 8 qdp_io retained-reference provenance extraction

- Added `packages/qdp_io/src/qdp_io/reference_manifest.py` as the shared authority for:
  - retained-reference lookup by `ref_id`
  - reconstructed-surrogate detection
  - authoritative-binding interpretation using the manifest plus governance registry
  - collapsed retained-reference provenance mode for the run-ledger contract
- Rewired `packages/qdp_control/src/qdp_control/run_ledger.py` to derive `provenance_mode` through `qdp_io` instead of keeping its own retained-reference rule.
- Rewired `modules/m06_bootstrap_harness/runner.py` so surrogate retained-reference limitations and authoritative-binding checks now delegate to `qdp_io`.
- Rewired `tools/workflow/qdp_runtime/qdp_module_sdk.py` and `tools/workflow/qdp_runtime/qdp_registry.py` to use `qdp_io` JSON artifact helpers instead of runtime-local dump helpers.
- Added direct `qdp_io` smoke coverage for retained-reference provenance helpers in `tests/unit/test_qdp_io_smoke.py`.
- No frozen ALL-MIND interface schema, callable surface, or readiness field changed in this phase.

## Next planned phase

- Continue broader reusable manifest and provenance-schema extraction without mixing it into shell or runtime-entrypoint rewrites.
- Continue later `qdp_core` cleanup for shared contracts and utilities that still sit in the transitional runtime layer.
- Continue classifying staged donor long-tail content into `archived`, `staged for later review`, `app-only`, or `non-reusable`.

## 2026-04-12 - Closure pass: qdp_io manifest/registry helper extraction and runtime/staging classification

- Added `packages/qdp_io/src/qdp_io/module_registry.py` as the active authority for:
  - module-registry JSON payload construction
  - module-registry markdown construction
  - shared derived-status and closure-limitation extraction helpers
- Added `load_json_object(...)` to `packages/qdp_io/src/qdp_io/serialization.py` as the shared object-root JSON loader for active runtime-shell compatibility surfaces.
- Rewired `tools/workflow/qdp_runtime/qdp_registry.py` into a compatibility facade over `qdp_io.module_registry` instead of leaving module-registry payload and markdown logic hidden in the transitional runtime layer.
- Rewired these runtime-shell surfaces to consume the shared object-root JSON loader from `qdp_io`:
  - `tools/workflow/qdp_runtime/qdp_module_sdk.py`
  - `tools/workflow/qdp_runtime/qdp_subsystem.py`
  - `tools/workflow/qdp_runtime/qdp_cli.py`
- Rewired `modules/m12_experiment_design/runner.py` to import `stable_hash` directly from `qdp_io.artifacts`, removing the last active non-wrapper consumer of `tools/workflow/qdp_runtime/qdp_artifact_contracts.py`.
- Added direct regression coverage in:
  - `tests/unit/test_qdp_io_smoke.py`
  - `tests/test_runtime_facade_surface.py`
- Updated `REPO_MAP.md` to classify retained runtime files explicitly as:
  - `shell`
  - `compatibility facade`
  - `still-authoritative and pending extraction`
- Updated `docs/migration/MONOREPO_CONSOLIDATION_STATUS.md` with final high-level donor subtree classifications and the active validation-scope decision:
  - promoted
  - intentionally left staged
  - out of scope for the default closure gate
- No public root command changed:
  - `python qdp.py`
  - `python qdp_validation.py`
  - `python scripts/run_repo_validation.py`
- No frozen ALL-MIND interface field, readiness rule, queue model, or domain package authority changed in this pass.

## 2026-04-13 - Closure pass: qdp_validation bootstrap-helper extraction

- Added `packages/qdp_validation/src/qdp_validation/module_workflows.py` as the active authority for:
  - module selftest-key discovery
  - module selftest execution fan-out
  - shared selftest report pass and validator-valid aggregation
- Added `packages/qdp_validation/src/qdp_validation/module_verification.py` as the active authority for:
  - bootstrap-facing module verification aggregation
  - compatibility alias construction for legacy `module_selftests`
  - bootstrap report extraction of the canonical `module_verification` surface
- Rewired these runtime-layer files into compatibility facades over `qdp_validation`:
  - `tools/workflow/qdp_runtime/qdp_module_workflows.py`
  - `tools/workflow/qdp_runtime/qdp_module_verification.py`
- Expanded `tests/unit/test_qdp_validation_smoke.py` and `tests/test_runtime_facade_surface.py` to cover the rehomed helpers and facade boundaries.
- Updated the runtime-surface classification and migration inventory so those two files are no longer described as pending extraction.
- No root command surface, frozen ALL-MIND contract field, readiness rule, or queue/control-plane model changed in this pass.

## 2026-04-12 - Phase 8 qdp_io shared UTC timestamp extraction

- Added `utc_now()` to `packages/qdp_io/src/qdp_io/artifacts.py` as the shared timezone-aware UTC timestamp helper.
- Rewired the following active control and audit surfaces to consume that helper instead of keeping local `utc_now()` implementations:
  - `packages/qdp_control/src/qdp_control/control_plane.py`
  - `packages/qdp_control/src/qdp_control/queue.py`
  - `packages/qdp_control/src/qdp_control/run_ledger.py`
  - `tools/workflow/qdp_runtime/qdp_subsystem.py`
  - `tools/migration/repo_audit.py`
  - `tools/migration/write_migration_manifests.py`
- Added direct regression coverage in `tests/test_shared_timestamp_surface.py`.
- No report schema, field names, queue state model, or frozen ALL-MIND interface surface changed in this phase.

## Next planned phase

- Continue broader reusable manifest and provenance-schema extraction without mixing it into shell or runtime-entrypoint rewrites.
- Continue later `qdp_core` cleanup for shared contracts and utilities that still sit in the transitional runtime layer.
- Continue classifying staged donor long-tail content into `archived`, `staged for later review`, `app-only`, or `non-reusable`.

## 2026-04-12 - Phase 8 qdp_io module-runner UTC timestamp extraction

- Rewired the active module runner path `M01`-`M15`, including `M03` and the canonical `M06` bootstrap harness, so `timestamp_utc` now comes from `qdp_io.artifacts.utc_now()` instead of inline `datetime.now(timezone.utc).isoformat()` calls.
- Brought `modules/m03_reference_resolution/runner.py` onto the shared `qdp_io` helper layer for:
  - JSON artifact writing
  - file SHA-256 hashing
  - shared `timestamp_utc` generation
- Added boundary regression coverage in `tests/test_module_runner_io_surface.py` so the active runner path keeps consuming `qdp_io` for both JSON artifact writing and `timestamp_utc` generation.
- Preserved report payload shapes, field names, and M03 `report_id` formatting; this pass only changed shared helper ownership on the module-report path.
- No frozen ALL-MIND interface field, callable surface, readiness flag, or module closure rule changed in this phase.

## 2026-04-12 - Phase 8 qdp_io shared report-header extraction

- Added shared report-header helpers to `packages/qdp_io/src/qdp_io/artifacts.py`:
  - `artifact_report_header(...)`
  - `module_report_header(...)`
- Rewired the active module runner path `M01`-`M15`, including `M03` and the canonical `M06` bootstrap harness, so standard module report headers now come from `qdp_io` instead of repeated inline `artifact_id` plus `module_id` plus `timestamp_utc` dict prefixes.
- Rewired additional active report surfaces so standard non-module report headers now come from `qdp_io`:
  - `tools/workflow/qdp_runtime/qdp_subsystem.py`
  - `packages/qdp_control/src/qdp_control/queue.py`
  - `packages/qdp_control/src/qdp_control/run_ledger.py`
  - `tools/migration/repo_audit.py`
  - `tools/migration/write_migration_manifests.py`
- Added regression coverage in:
  - `tests/unit/test_qdp_io_smoke.py`
  - `tests/test_module_runner_io_surface.py`
  - `tests/test_shared_report_header_surface.py`
- Preserved payload shapes and field order at the leading report-header boundary by expanding the shared helpers into the existing dict constructors.
- No frozen ALL-MIND interface field, callable surface, readiness flag, queue model, or module closure rule changed in this phase.

## 2026-04-12 - Phase 8 qdp_io shared selftest-payload extraction

- Added `module_selftest_report_payload(...)` to `packages/qdp_io/src/qdp_io/artifacts.py` as the shared authority for canonical selftest summary payload construction.
- Rewired the active selftest-producing runner path:
  - `modules/m01_runtime_assembly/runner.py`
  - `modules/m02_schema_validator/runner.py`
  - `modules/m04_branch_registration/runner.py`
  - `modules/m05_stage_machine/runner.py`
  - `modules/m07_family_triage/runner.py`
  - `modules/m08_baseline_fit/runner.py`
  - `modules/m09_mechanism_competition/runner.py`
  - `modules/m10_artifact_audit/runner.py`
  - `modules/m11_lindblad_equivalence/runner.py`
  - `modules/m12_experiment_design/runner.py`
  - `modules/m13_cross_device_gate/runner.py`
  - `modules/m14_promotion_caps/runner.py`
  - `modules/m15_governance_guardrails/runner.py`
  so `cases_total`, `cases_passed`, `all_passed`, and optional `schema_valid_all` plus visible-source metadata no longer live as duplicate inline payload assembly on the canonical selftest-report path.
- Rewired `tools/workflow/qdp_runtime/qdp_subsystem.py` to consume the same shared helper rather than rebuilding the selftest summary payload locally.
- Preserved module-local behavior where the selftest contract intentionally differs:
  - `M02` still carries `contract_checks`
  - `M05` and `qdp_subsystem` still use their pre-existing explicit `all_passed` semantics
- Added regression coverage in:
  - `tests/unit/test_qdp_io_smoke.py`
  - `tests/test_module_runner_io_surface.py`
- Validated the structural extraction with:
  - `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_validation/src;packages/qdp_control/src"; python -m pytest tests/unit/test_qdp_io_smoke.py tests/test_module_runner_io_surface.py tests/test_shared_report_header_surface.py tests/test_m01_runtime_assembly.py tests/test_authoritative_readiness.py tests/test_run_repo_validation.py -q`
  - `python scripts/run_repo_validation.py`
- No frozen ALL-MIND interface field, callable surface, readiness flag, queue model, or module closure rule changed in this phase.

## 2026-04-12 - Phase 8 qdp_io shared candidate-result summary extraction

- Added `candidate_result_summary_report(...)` to `packages/qdp_io/src/qdp_io/artifacts.py` as the shared authority for canonical module reports that expose:
  - `candidate_id`
  - `result_summary`
- Rewired the active candidate-summary report path:
  - `modules/m11_lindblad_equivalence/runner.py`
  - `modules/m12_experiment_design/runner.py`
  - `modules/m13_cross_device_gate/runner.py`
  - `modules/m14_promotion_caps/runner.py`
  - `modules/m15_governance_guardrails/runner.py`
  so that report-envelope shape no longer lives as duplicate inline payload assembly on the canonical module path.
- Added regression coverage in:
  - `tests/unit/test_qdp_io_smoke.py`
  - `tests/test_module_runner_io_surface.py`
- Fixed one stale boundary assertion during focused validation:
  - `tests/test_module_runner_io_surface.py` previously required `module_report_header` in every active module runner
  - the assertion was broadened so `M11`-`M15` may use the higher-level `candidate_result_summary_report` helper instead
- Validated the structural extraction with:
  - `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_validation/src;packages/qdp_control/src"; python -m pytest tests/unit/test_qdp_io_smoke.py tests/test_module_runner_io_surface.py tests/test_shared_report_header_surface.py tests/test_authoritative_readiness.py tests/test_run_repo_validation.py -q`
  - `python scripts/run_repo_validation.py`
- No frozen ALL-MIND interface field, callable surface, readiness flag, queue model, or module closure rule changed in this phase.

## 2026-04-12 - Phase 8 qdp_io shared visible-source result-summary extraction

- Added `visible_source_result_summary_report(...)` to `packages/qdp_io/src/qdp_io/artifacts.py` as the shared authority for canonical visible-source module reports that expose:
  - `visible_source_only`
  - `result_summary`
  - optional metadata
  - optional nested diagnostics
- Rewired the active visible-source report path:
  - `modules/m07_family_triage/runner.py`
  - `modules/m08_baseline_fit/runner.py`
  - `modules/m09_mechanism_competition/runner.py`
  - `modules/m10_artifact_audit/runner.py`
  so that visible-source report-envelope shape no longer lives as duplicate inline payload assembly on the canonical module path.
- Added regression coverage in:
  - `tests/unit/test_qdp_io_smoke.py`
  - `tests/test_module_runner_io_surface.py`
- Validated the structural extraction with:
  - `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_validation/src;packages/qdp_control/src"; python -m pytest tests/unit/test_qdp_io_smoke.py tests/test_module_runner_io_surface.py tests/test_shared_report_header_surface.py tests/test_authoritative_readiness.py tests/test_run_repo_validation.py -q`
  - `python scripts/run_repo_validation.py`
- No frozen ALL-MIND interface field, callable surface, readiness flag, queue model, or module closure rule changed in this phase.

## 2026-04-11 - Phase 8 qdp_io module-runner writer extraction

- Rewired the active visible-source module runners:
  - `M02`
  - `M04`
  - `M05`
  - `M07`
  - `M08`
  - `M09`
  - `M10`
  - `M11`
  - `M12`
  - `M13`
  - `M14`
  - `M15`
  so they now import `qdp_io.artifacts.dump_json` instead of carrying duplicated local JSON artifact writer helpers.
- Added a direct boundary regression test in `tests/test_module_runner_io_surface.py` to assert those runners import `qdp_io.artifacts.dump_json` and no longer define local `dump_json(...)`.
- Preserved module behavior and report payload shapes; this pass only changed helper ownership, not module closure semantics.
- No frozen ALL-MIND interface field, callable surface, or readiness flag changed in this phase.

## Next planned phase

- Continue broader reusable manifest and provenance-schema extraction without mixing it into shell or runtime-entrypoint rewrites.
- Continue later `qdp_core` cleanup for shared contracts and utilities that still sit in the transitional runtime layer.
- Continue classifying staged donor long-tail content into `archived`, `staged for later review`, `app-only`, or `non-reusable`.

## 2026-04-11 - Phase 8 qdp_io M01 and migration-writer extraction

- Rewired `modules/m01_runtime_assembly/runner.py` to consume:
  - `qdp_io.artifacts.dump_json`
  - `qdp_io.artifacts.sha256_file`
  - `qdp_io.reference_manifest.find_reference_entry`
  - `qdp_io.reference_manifest.reference_is_reconstructed_surrogate`
- Preserved the existing M01 closure semantics: a surrogate retained reference still keeps M01 in the recovery lane.
- Added direct focused coverage in `tests/test_m01_runtime_assembly.py` for:
  - surrogate-retained recovery behavior
  - original-retained authoritative-lane behavior
- Rewired `tools/migration/repo_audit.py` and `tools/migration/write_migration_manifests.py` to use `qdp_io` for generic JSON artifact writing instead of local duplicate writers.
- No frozen ALL-MIND interface field, callable surface, or readiness flag changed in this phase.

## Next planned phase

- Continue broader reusable manifest and provenance-schema extraction without mixing it into shell or runtime-entrypoint rewrites.
- Continue later `qdp_core` cleanup for shared contracts and utilities that still sit in the transitional runtime layer.
- Continue classifying staged donor long-tail content into `archived`, `staged for later review`, `app-only`, or `non-reusable`.

## 2026-04-13 - Phase 8 TDGL run_case workflow slice promotion

- Promoted a focused TDGL runtime-output regression slice from the staged donor suite into the active repo as:
  - `tests/unit/test_qdp_tdgl_run_case_outputs.py`
- The promoted active slice now verifies that the extracted `qdp_tdgl.workflows.run_case.run_simulation(...)` path:
  - appends the terminal observable sample even when `obs_stride` skips intermediate steps
  - preserves compact summary and diagnostics metadata when observables are computed but not written
  - emits replayable seeded-vortex provenance and Tier-2 diagnostics that validate against `configs/tdgl/tdgl_run_provenance.schema.json`
- Updated active package-level TDGL validation guidance in:
  - `AGENTS.md`
  - `packages/qdp_tdgl/README.md`
  - `VALIDATION.md`
- Validated the promoted slice with:
  - `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_tdgl/src;packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_qdp_tdgl_run_case_outputs.py -q`
- No TDGL runtime behavior, solver semantics, or frozen ALL-MIND interface fields changed in this phase; this pass promoted active workflow coverage only.
