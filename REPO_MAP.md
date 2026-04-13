# Repo Map

## Consolidation Status

- `CONSOLIDATION_PLAN.md`: overlap matrix, winner selections, landing map, staging decisions, and phase entry criteria
- `CONSOLIDATION_LOG.md`: executed consolidation phases and no-silent-discard migration notes
- `pyproject.toml`: umbrella workspace manifest for the consolidation-era repo skeleton

## Destination Ownership Zones

- `packages/qdp_core/`: future destination for reusable core contracts and utilities that do not belong to another package
- `packages/qdp_tdgl/`: active canonical TDGL runtime extracted from the staged `QDP TDGL` donor
- `packages/qdp_meta_materials/`: current canonical materials and metamaterials package extracted from the staged `MMM-Studio` donor; `apps/mmm_studio/` now consumes it as a thin shell
- `packages/qdp_io/`: active extracted shared serialization, object-root JSON loading, module-registry payload/markdown builder, artifact-hash, JSON artifact-helper, generic runtime-metadata, retained-reference provenance-helper, shared UTC timestamp, shared report-header, shared module selftest-payload, shared candidate result-summary report, and shared visible-source result-summary report package; M01, the active visible-source module runners, qdp_control, subsystem tooling, migration/audit tooling, and runtime compatibility surfaces now consume it directly, while broader reusable manifest and provenance contract extraction remains deferred
- `packages/qdp_validation/`: active extracted umbrella validation, interface-contract, and promotion-gate package
- `packages/qdp_control/`: active extracted orchestration, queue, campaign, lab, and non-runtime pipeline control package
- `apps/mmm_studio/`: active app-shell-only surface for the migrated MMM Studio CLI and API
- `labs/materials/`: future source home for experimental materials packs and branch-specific non-authoritative assets
- `labs/tdgl/`: future source home for curated TDGL examples and exploratory runtime studies
- `configs/tdgl/`: active canonical TDGL case-config and schema surface
- `configs/validation/tdgl/`: active canonical TDGL validation-manifest and threshold surface
- `configs/materials/`, `configs/validation/`: future package-scoped config destinations outside the extracted TDGL surface; `config/` remains the current active governance config surface until migrated
- `staging/imported_qdp_mm/`, `staging/imported_mmm_studio/`, `staging/imported_qdp_tdgl/`: active donor staging roots with working-tree `snapshot/` imports and per-donor traceability manifests before extraction
- `tests/unit/`, `tests/integration/`, `tests/scientific/`: destination test layers for the reorganized suite; current active tests still live in the root `tests/` directory

## Current Active Implementation Surfaces

- `qdp.py`: main orchestration entrypoint
- `tools/workflow/qdp_runtime/qdp_cli.py`: active transitional CLI shell that now consumes `packages/qdp_control/`
- `qdp_validation.py`: repo-consistency validation entrypoint and compatibility wrapper over `packages/qdp_validation/`
- `scripts/run_repo_validation.py`: canonical Windows-safe validation wrapper for repo consistency plus the frozen ALL-MIND interface artifact
- `INTEGRATION_PLAN.md`: contract describing the only QDP surface the ALL-MIND control plane may consume
- `artifacts/state/`: governed local state, including the control-plane database, queue manifests, and queue logs
- `artifacts/reports/system/queue_report.json`: generated snapshot of the repo-local execution queue state
- `modules/`: directory-driven module runners, patch notes, fixtures, and selftests for `M01`-`M15` and `S16`-`S19`
- `tools/workflow/qdp_runtime/`: canonical internal transitional Python runtime package for shared QDP implementation; remaining major extraction targets are now narrowed to the explicitly labeled `still-authoritative and pending extraction` files below
- `packages/qdp_meta_materials/`: active extracted materials package containing the canonical typed registry, validation, scoring, planning, adapter scaffolds, and stable seed dataset from the selected `MMM-Studio` donor
- `packages/qdp_tdgl/`: active extracted TDGL runtime package containing the canonical runtime, solver, workflow, and CLI authority selected from `QDP TDGL`
- `packages/qdp_io/`: active extracted shared IO package containing serialization, object-root JSON loading, module-registry payload and markdown builders, artifact hash helpers, legacy-compatible JSON artifact writing, shared report-header, module selftest-payload, candidate result-summary, and visible-source result-summary helpers, a shared UTC timestamp helper, generic runtime metadata, and retained-reference provenance helpers used by extracted packages, `modules/m01_runtime_assembly/`, the active visible-source module runners, and runtime compatibility facades
- `packages/qdp_validation/`: active extracted umbrella validation package containing the canonical repo-consistency and frozen ALL-MIND interface validation logic
- `packages/qdp_control/`: active extracted control package containing the canonical queue, campaign, lab, control-plane persistence, and run-ledger logic used by the CLI shell
- `apps/mmm_studio/`: active extracted MMM Studio shell that consumes `qdp_meta_materials` rather than owning materials logic
- `configs/tdgl/`: active extracted TDGL schemas and committed case-config inputs
- `configs/validation/tdgl/`: active extracted TDGL validation manifests, reference packs, and thresholds
- `tools/validators/`: candidate and subsystem validation surfaces
- `tools/migration/`: overhaul audit and migration-report tooling
- `specs/core/`, `specs/intake/`, `specs/subsystem/`, `specs/research/`: governing scientific and intake specifications
- `config/schema/`, `config/registries/`, `config/manifests/`, `config/contracts/`, `config/policies/`: machine-readable governance inputs, including `config/schema/all_mind_interface_schema.json`
- `runtime/current/`, `runtime/retained/`, `runtime/missing/`: active runtime prompt, retained sources, and missing-source recovery tracking
- `artifacts/reports/`: generated module, subsystem, system, and campaign reports, including partitioned simulation reports under `artifacts/reports/simulations/` and active campaign reports under `artifacts/reports/campaigns/`
- `artifacts/outputs/`: generated candidate, bootstrap, selftest, prepared `M12`, and optional partitioned simulation outputs under `artifacts/outputs/simulations/`; these generated artifacts are operational evidence, not governing source truth
- `docs/repo/`: repo navigation and operational guidance
- `docs/architecture/`: implementation and architecture notes
- `docs/decisions/`: existing design decisions and source-side narrative records
- `docs/adr/`: destination for new consolidation-era architecture decision records
- `docs/migration/`: destination for donor import procedures, migration notes, and manual follow-up instructions
- `legacy/docs/archive/`: superseded historical narrative docs that are preserved for chronology but are not part of the active truth surface
- `legacy/imported_artifacts/`: quarantined reference material that is not part of the active governing surface
- Root guidance files: `README.md`, `AGENTS.md`, `SYSTEM_BOUNDARY.md`, `STATUS.md`, `VALIDATION.md`, `PROMOTION_NOTES.md`, `INTEGRATION_PLAN.md`, `QDP_REPO_REFACTOR_PLAN.md`, `CONSOLIDATION_PLAN.md`, `CONSOLIDATION_LOG.md`

## Ownership Notes

- `QDP` remains the umbrella repo and long-term system of record.
- `MMM-Studio` is the selected donor for the canonical materials package.
- `QDP TDGL` is the selected donor for the canonical TDGL runtime.
- `QDP MM` is a lineage and branch-protocol donor, not the future canonical reusable materials package.
- `packages/qdp_io/` is now the active authority for shared package-layer serialization, stable payload hashing, JSON artifact writing, generic runtime metadata, and retained-reference provenance interpretation.
- `packages/qdp_io/` is now also the active authority for object-root JSON loading on the active runtime-shell compatibility path and for module-registry payload and markdown builders used by the bootstrap-facing module-registry emission path.
- `packages/qdp_io/` is now also the active authority for the shared timezone-aware UTC timestamp helper used by control, subsystem, and migration surfaces.
- `packages/qdp_io/` is now also the active authority for `timestamp_utc` generation across the active module runner path `M01`-`M15`, including `M03` and the canonical `M06` bootstrap harness.
- `packages/qdp_io/` is now also the active authority for shared artifact-report and module-report header construction on the active module runner, subsystem, queue-report, run-ledger, and migration/audit surfaces.
- `packages/qdp_io/` is now also the active authority for canonical module selftest summary payload construction on the active selftest-producing runner path and `tools/workflow/qdp_runtime/qdp_subsystem.py`.
- `packages/qdp_io/` is now also the active authority for canonical `candidate_id` plus `result_summary` report-envelope construction on the active module path `M11`-`M15`.
- `packages/qdp_io/` is now also the active authority for canonical `visible_source_only` plus `result_summary` report-envelope construction on the active module path `M07`-`M10`.
- `tools/workflow/qdp_runtime/qdp_artifact_contracts.py` is now a compatibility facade over `packages/qdp_io/` and `packages/qdp_validation/`, not the active authority for generic file/hash helpers.
- `tools/workflow/qdp_runtime/qdp_registry.py` is now a compatibility facade over `packages/qdp_io/module_registry.py`, not the active authority for module-registry payload or markdown generation.
- `modules/m01_runtime_assembly/runner.py`, `tools/migration/repo_audit.py`, and `tools/migration/write_migration_manifests.py` now consume shared `qdp_io` helpers instead of owning local JSON artifact writer copies.
- The active visible-source module runners `M02`, `M04`, `M05`, `M07`-`M15` now consume `qdp_io.artifacts.dump_json` instead of owning duplicated local JSON artifact writer implementations.
- `packages/qdp_validation/` is now the active authority for umbrella repo-consistency validation and frozen ALL-MIND interface validation.
- `packages/qdp_control/` is now the active authority for queue/control-plane persistence, campaign prepare/plan logic, lab pack/ingest orchestration, and run-ledger helpers.
- `packages/qdp_meta_materials/` is now the active materials authority.
- `packages/qdp_meta_materials/registry/` is now the one canonical materials registry loader surface; `qdp_meta_materials/io.py` is serialization-only.
- `packages/qdp_tdgl/` is now the active TDGL runtime authority.
- `apps/mmm_studio/` is now the active shell authority only and must not re-own materials logic.
- `configs/tdgl/` now resolves canonical TDGL material references through `packages/qdp_meta_materials/adapters/tdgl/` instead of keeping a second copied material-parameter authority in the TDGL baselines.
- `docs/migration/MONOREPO_CONSOLIDATION_STATUS.md` is the active inventory for what is migrated, staged, superseded, app-only, and still under manual review.
- The remaining major extraction work after the current Phase 8 work is broader reusable provenance/manifest extraction, later `qdp_core` cleanup, and long-tail donor classification work.

## Runtime Surface Classification

| Path | Classification | Notes |
| --- | --- | --- |
| `qdp.py` | shell | stable root command entrypoint; delegates to `tools/workflow/qdp_runtime/qdp_cli.py` |
| `qdp_validation.py` | shell | stable root validation entrypoint; delegates to `packages/qdp_validation/` |
| `tools/workflow/qdp_runtime/qdp_cli.py` | shell | active command-dispatch shell; consumes `qdp_control`, `qdp_io`, `qdp_validation`, and runtime-pending helpers |
| `tools/workflow/qdp_runtime/qdp_artifact_contracts.py` | compatibility facade | forwards shared artifact/helper and validation surfaces to `qdp_io` and `qdp_validation` |
| `tools/workflow/qdp_runtime/qdp_validation.py` | compatibility facade | forwards runtime validation imports to `packages/qdp_validation/` |
| `tools/workflow/qdp_runtime/qdp_control_plane.py` | compatibility facade | forwards control-plane persistence imports to `packages/qdp_control/` |
| `tools/workflow/qdp_runtime/qdp_campaign_planner.py` | compatibility facade | forwards campaign prepare/plan imports to `packages/qdp_control/` |
| `tools/workflow/qdp_runtime/qdp_queue.py` | compatibility facade | forwards queue imports to `packages/qdp_control/` |
| `tools/workflow/qdp_runtime/qdp_lab_workflows.py` | compatibility facade | forwards lab request and ingest imports to `packages/qdp_control/` |
| `tools/workflow/qdp_runtime/qdp_run_ledger.py` | compatibility facade | forwards run-ledger imports to `packages/qdp_control/` |
| `tools/workflow/qdp_runtime/qdp_registry.py` | compatibility facade | adapts runtime constants from `qdp_paths.py` into `qdp_io.module_registry` builders |
| `tools/workflow/qdp_runtime/qdp_paths.py` | still-authoritative and pending extraction | owns repo-root path constants, module blueprints, and generated-vs-source path policy |
| `tools/workflow/qdp_runtime/qdp_governance.py` | still-authoritative and pending extraction | owns candidate governance normalization, cap clipping, gate tracing, and fallback semantics |
| `tools/workflow/qdp_runtime/qdp_module_sdk.py` | still-authoritative and pending extraction | owns module loading and runner dispatch conventions for the root shell |
| `tools/workflow/qdp_runtime/qdp_module_workflows.py` | compatibility facade | forwards bootstrap-facing module selftest orchestration helpers to `packages/qdp_validation/` |
| `tools/workflow/qdp_runtime/qdp_module_verification.py` | compatibility facade | forwards module-verification aggregation helpers to `packages/qdp_validation/` |
| `tools/workflow/qdp_runtime/qdp_subsystem.py` | still-authoritative and pending extraction | owns subsystem-runner payload semantics and subsystem selftest orchestration |
