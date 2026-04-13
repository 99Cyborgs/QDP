# QDP Consolidation Plan

## Status

- Phase: `8 - closure cleanup in progress after qdp_io, qdp_validation, and qdp_control extraction`
- Date: `2026-04-12`
- Scope of this file: overlap audit, winner selection, landing map, staging decisions, and target-skeleton guidance
- Explicitly deferred in the current phase: broader reusable provenance and manifest schema extraction beyond the newly moved object-root and module-registry helpers, destructive cleanup, and full donor-wide scientific/integration suite migration beyond the copied high-value surfaces

## QDP Authority Context

- Authority order used for this audit: `AGENTS.md` -> `README.md` -> `SYSTEM_BOUNDARY.md` -> `STATUS.md` -> `REPO_MAP.md` -> `VALIDATION.md` -> `QDP_REPO_REFACTOR_PLAN.md`
- Canonical QDP validation entrypoint: `python scripts/run_repo_validation.py`
- QDP source surfaces today: `tools/workflow/qdp_runtime/`, `modules/`, `config/`, `specs/`, `docs/`
- QDP generated or retained surfaces today: `artifacts/`, `runtime/current/`, `runtime/retained/`, `runtime/missing/`, `legacy/imported_artifacts/`
- Boundary rule carried into consolidation: QDP remains the master repo, generated outputs stay out of source authority, and the ALL-MIND interface must stay narrow

## Repo Roles

| Repo | Observed role | Key evidence | Consolidation role |
| --- | --- | --- | --- |
| `QDP/` | Current umbrella governance, orchestration, campaign planning, queue, and repo validation surface | `README.md`, `REPO_MAP.md`, `qdp.py`, `tools/workflow/qdp_runtime/`, `tests/` | Destination system of record and umbrella monorepo root |
| `QDP MM/` | Branch-pack donor with conservative metastable-memory semantics, run-binding states, protocol schemas, analysis gates, and branch-specific synthetic tests | `README.md`, `qdp/branches/e01_mm_flux_history_hysteresis/specs/e01_mm_branch_spec.md`, `analysis/e01_mm_analysis_protocol.md`, `execution_queue/e01_mm_execution_queue.py` | Semantic lineage donor and experimental branch-pack donor, not the canonical reusable materials package |
| `MMM-Studio/` | Strongest typed reusable metamaterials package and app shell | `README.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `src/mmm_studio/models.py`, `registry.py`, `scoring.py`, `sweeps/`, `tests/` | Canonical donor for `qdp_meta_materials` and the `apps/mmm_studio` shell |
| `QDP TDGL/` | Strongest packaged TDGL runtime, solver, config, provenance, validation, and runtime tests; also contains duplicate legacy QDP-style control surfaces | `README.md`, `REPO_MAP.md`, `src/tdgl_rf/`, `configs/`, `validation/`, `tests/` | Canonical donor for `qdp_tdgl`; legacy duplicate control surfaces must not survive as authorities |

## Subsystem Overlap Matrix

| Subsystem | Current locations | Reusable | Winner | Land in QDP | Stage / archive / supersede call |
| --- | --- | --- | --- | --- | --- |
| material schemas | `MMM-Studio/src/mmm_studio/models.py`; `MMM-Studio/docs/DATA_MODEL.md`<br>`QDP MM/.../analysis/e01_mm_analysis_input_schema.md`; `.../analysis/e01_mm_measurement_evidence_schema.md`; `.../protocols/e01_mm_first_cooldown_run_binding.json` (branch protocol schemas, not general materials schemas)<br>`QDP TDGL/src/tdgl_rf/config/models.py`; `QDP TDGL/configs/tdgl_case.schema.json` (runtime schemas)<br>`QDP/config/schema/*.json` (QDP candidate/governance schemas) | Yes, but only one repo already exposes a reusable typed materials schema surface | `MMM-Studio` | `packages/qdp_meta_materials/schemas/` and exported typed models | Stage QDP MM schemas as branch-protocol assets under experimental or lab surfaces; keep QDP and QDP TDGL schemas in their own domains; do not let them co-own the materials domain model |
| stack definitions | `MMM-Studio/data/mmm_seed/mmm_structure_library.yaml`; `mmm_material_system_registry.yaml`; `mmm_device_architecture_registry.yaml`; typed counterparts in `src/mmm_studio/models.py`<br>`QDP MM` uses geometry labels and matched-geometry rules but not a reusable stack library<br>`QDP TDGL/src/tdgl_rf/config/models.py` defines runtime geometry and physics inputs, not a materials stack registry | Yes | `MMM-Studio` | `packages/qdp_meta_materials/registry/` plus `packages/qdp_meta_materials/data/seed/stable/` | Preserve QDP MM geometry semantics as lineage notes and experimental rules; do not duplicate TDGL runtime geometry config as the canonical materials stack model |
| registry data / seed data | `MMM-Studio/data/mmm_seed/*`<br>`QDP MM/.../intake/e01_mm_candidate_seed.json`; `.../intake/e01_mm_fork_intake.json`<br>`QDP/config/registries/*.json` (governance registries, not materials seed data)<br>`QDP TDGL/validation/*`; `configs/validation/*` (runtime validation packs) | Yes | `MMM-Studio` for stable materials seed data; `QDP MM` only as experimental lineage seed | Stable seed data in `packages/qdp_meta_materials/data/seed/stable/`; branch or hypothesis seeds in `packages/qdp_meta_materials/data/seed/experimental/` or `labs/materials/` | Stage QDP MM intake seeds as experimental lineage artifacts; keep QDP governance registries and TDGL validation packs domain-local and out of the materials registry authority |
| registry loading | `MMM-Studio/src/mmm_studio/registry.py`; `src/mmm_studio/io.py`<br>`QDP/tools/workflow/qdp_runtime/qdp_registry.py` (module and governance registry)<br>`QDP TDGL/src/tdgl_rf/config/loaders.py` (runtime case loading) | Yes, but only MMM-Studio loads a typed materials registry | `MMM-Studio` | `packages/qdp_meta_materials/registry/` | Retire app-local duplicate materials loaders after extraction; rename or keep other registry systems strictly domain-qualified (`governance`, `runtime-config`) so there is exactly one materials registry loader |
| registry validation | `MMM-Studio/src/mmm_studio/validation.py`; `tests/test_registry.py`; `tests/test_validation.py`<br>`QDP/tools/validators/*.py` (QDP candidate and intake validators)<br>`QDP TDGL/src/tdgl_rf/config/validators.py` (runtime config validators)<br>`QDP MM/execution_queue/*` and analysis gates validate branch packets, not a general materials registry | Yes | `MMM-Studio` | `packages/qdp_meta_materials/validation/` with package-owned registry checks | Keep TDGL config validation in `qdp_tdgl` and repo/promotion validation in `qdp_validation`; do not let branch-pack validators or app shell validation become second materials registry authorities |
| provenance / artifact models | `MMM-Studio/src/mmm_studio/models.py`; `src/mmm_studio/runs.py`<br>`QDP TDGL/src/tdgl_rf/io/metadata.py`; `QDP TDGL/configs/tdgl_run_provenance.schema.json`<br>`QDP MM/.../protocols/e01_mm_first_cooldown_run_binding.json`; `execution_queue/e01_mm_reconciliation.py`; analysis input schemas<br>`QDP/tools/workflow/qdp_runtime/qdp_artifact_contracts.py`; `qdp_run_ledger.py` | Yes, but duplicated and currently inconsistent | `MMM-Studio` for generic typed artifact contracts, with `QDP TDGL` retaining TDGL-only replay extensions | Generic contracts and helpers in `packages/qdp_io/`; TDGL-only provenance extensions stay in `packages/qdp_tdgl/` | Stage QDP MM run-binding as branch protocol state, not global provenance authority; fold reusable QDP JSON validation and ledger helpers into `qdp_io`; remove duplicate package-local provenance writers once consumers move to shared contracts |
| scoring / ranking | `MMM-Studio/src/mmm_studio/scoring.py`; `tests/test_scoring.py`<br>`QDP MM/.../analysis/e01_mm_analysis_runner.py`; `competition/e01_mm_mechanism_competition.md`<br>`QDP/modules/m07_family_triage/runner.py`; `m09_mechanism_competition/runner.py`; `m12_experiment_design/runner.py` | Partially; only MMM-Studio is already a reusable typed materials ranking system | `MMM-Studio`, with QDP MM naming and decision semantics informing lineage notes | `packages/qdp_meta_materials/scoring/` | Stage QDP MM branch analysis as experimental branch evaluation; keep QDP branch-mechanism scoring under `qdp_control` with explicit scope; do not allow app-local or branch-pack-local materials ranking to remain authoritative |
| planning / sweep / tranche logic | `MMM-Studio/src/mmm_studio/sweeps/*`; `examples/sweeps/*`; `tests/test_sweeps.py`<br>`QDP MM/.../protocols/e01_mm_candidate_packet_sweep_generator.ps1`; `execution_queue/*`<br>`QDP/tools/workflow/qdp_runtime/qdp_campaign_planner.py`; `modules/m12_experiment_design/runner.py`<br>`QDP TDGL/src/tdgl_rf/workflows/experiment_sweep.py` | Yes, but the layers must be separated | `MMM-Studio` for generic material tranche planning; `QDP` for umbrella orchestration; `QDP TDGL` for runtime execution only | Generic planning in `packages/qdp_meta_materials/planning/`; orchestration in `packages/qdp_control/`; runtime execution in `packages/qdp_tdgl/` | Stage QDP MM packet generation as experimental lab tooling; refactor QDP campaign planning into orchestration only; keep `tdgl_rf` experiment packs runtime-specific and do not let them become a second generic sweep planner |
| TDGL runtime / solver | `QDP TDGL/src/tdgl_rf/solvers/*`; `workflows/run_case.py`; `workflows/run_ensemble.py`; `cli.py`; `tests/unit|integration|acceptance/*`; `configs/*`; `validation/*`<br>`QDP` currently contains mechanism docs and sweep synthesis but no comparable packaged TDGL runtime authority<br>`QDP MM/simulation/e01_mm_simulation_suite.py` is synthetic branch stress testing, not a TDGL runtime | Yes | `QDP TDGL` | `packages/qdp_tdgl/` | Stage the entire donor repo under `staging/imported_qdp_tdgl/`; keep only one runtime authority after extraction; quarantine `QDP TDGL` legacy `qdp.py`, `modules/`, `tools/`, and `artifacts/` as imported legacy, not active authority |
| RF or simulation adapters | `MMM-Studio/src/mmm_studio/rf/*`; `src/mmm_studio/sim/*`; adapter contracts documented in `docs/DATA_MODEL.md`<br>`QDP TDGL/src/tdgl_rf/config/*`; `workflows/*` implement runtime execution, not generic adapter contracts<br>`QDP MM/simulation/*` provides branch-specific synthetic scenarios | Partially | `MMM-Studio` for reusable adapter contracts; `QDP TDGL` for TDGL backend implementation | Adapter contracts in `packages/qdp_meta_materials/adapters/tdgl/`; backend implementation in `packages/qdp_tdgl/` | Move QDP MM synthetic simulation into `labs/materials/` or experimental surfaces; do not leave placeholder backends in the app shell or a second simulation runtime beside `qdp_tdgl` |
| CLI | `QDP/qdp.py` and `tools/workflow/qdp_runtime/qdp_cli.py`<br>`MMM-Studio/src/mmm_studio/cli.py`<br>`QDP TDGL/src/tdgl_rf/cli.py`<br>`QDP MM` branch scripts with local argparse entrypoints | No, shell layer only | `QDP` for the umbrella CLI; `MMM-Studio` keeps an app shell only | Master orchestration remains at repo root and later `packages/qdp_control/`; app shell stays in `apps/mmm_studio/` | Refactor `MMM-Studio` CLI into a thin app shell consuming packages; convert `tdgl-rf` into a package-local compatibility surface or QDP subcommand; stage QDP MM script CLIs as experimental tools |
| API | `MMM-Studio/src/mmm_studio/api.py`; `api_models.py`; `tests/test_api.py` | No, shell layer only | `MMM-Studio` | `apps/mmm_studio/` | Keep API logic out of package ownership; the app must consume `qdp_meta_materials`, `qdp_io`, `qdp_validation`, and `qdp_tdgl` rather than re-owning domain logic |
| examples | `MMM-Studio/examples/*`<br>`QDP TDGL/configs/*`; `validation/*`; phase docs<br>`QDP MM/protocols/*`; `simulation/*`; proposal docs<br>`QDP/artifacts/outputs/simulations/*` and other generated outputs already exist but are not governing source | Partially | Composite by domain; no single repo should own all examples | Hand-curated source examples in `labs/materials/` and `labs/tdgl/`; migration docs in `docs/migration/` | Keep only curated source examples; quarantine generated outputs and bulky run directories outside package trees; do not promote generated artifacts to source examples |
| tests | `MMM-Studio/tests/*`<br>`QDP TDGL/tests/unit/*`; `tests/integration/*`; `tests/acceptance/*`<br>`QDP/tests/*`<br>`QDP MM/.../test_*.py` | Yes | Composite by package | `tests/unit/`, `tests/integration/`, `tests/scientific/`, with package-owned fixtures and lab-specific tests under `labs/` | Preserve the strongest package-local tests from MMM-Studio, QDP TDGL, and QDP; stage QDP MM tests with their experimental branch assets until the related code is extracted |

## Winner Summary

- Canonical materials and metamaterials package winner: `MMM-Studio`
- Canonical TDGL runtime winner: `QDP TDGL`
- Umbrella orchestration and destination authority: `QDP`
- Semantic lineage donor: `QDP MM`

## Proposed Landing Map

### `packages/qdp_meta_materials/`

- Start from `MMM-Studio/src/mmm_studio/` for typed models, registry loading, validation, scoring, runs, and tranche planning.
- Pull stable seed data from `MMM-Studio/data/mmm_seed/`.
- Preserve QDP MM lineage by carrying forward branch vocabulary and conservative semantics where they clarify domain intent:
  - `METASTABLE_C_STATE`
  - geometry-gate discipline
  - explicit pre-run versus as-run provenance states
  - conservative branch disposition labels
- Do not import the entire `MMM-Studio` app as the package. Extract reusable library code only.
- Do not import `QDP MM` branch-pack code wholesale as the canonical library. Selectively absorb reusable semantics and protocol patterns.

### `packages/qdp_tdgl/`

- Start from `QDP TDGL/src/tdgl_rf/`, `configs/`, `validation/`, and the strongest unit/integration/acceptance tests.
- Treat `QDP TDGL/REPO_MAP.md` as authoritative for what is already active versus legacy inside the donor repo.
- Keep solver entrypoints, runtime workflows, and TDGL-specific execution logic here.
- The initial extracted runtime now lives under `packages/qdp_tdgl/src/qdp_tdgl/`.
- Canonical TDGL schemas and case configs now resolve from `configs/tdgl/`.
- Canonical TDGL validation manifests and thresholds now resolve from `configs/validation/tdgl/`.
- The compatibility CLI alias `tdgl-rf` is preserved temporarily, but `qdp-tdgl` is the canonical extracted command name.
- Legacy donor root control shells remain staged-only under `staging/imported_qdp_tdgl/`; they are not part of the active runtime authority.
- TDGL configs now carry an explicit `materials` block that resolves runtime material parameters through `qdp_meta_materials/adapters/tdgl/`.

### `packages/qdp_io/`

- The initial extracted authority now covers shared package-layer serialization and generic runtime metadata helpers.
- Active extracted sources in this phase:
  - `MMM-Studio/src/mmm_studio/io.py`
  - generic runtime metadata portions of `QDP TDGL/src/tdgl_rf/io/metadata.py`
  - generic file-hash and JSON artifact helper portions of `QDP/tools/workflow/qdp_runtime/qdp_artifact_contracts.py`
  - retained-reference provenance helper portions of `QDP/modules/m06_bootstrap_harness/runner.py`
  - retained-reference provenance mode logic from `QDP/packages/qdp_control/src/qdp_control/run_ledger.py`
- Deferred candidate sources for later extraction:
  - remaining reusable manifest and provenance schema portions of `QDP/tools/workflow/qdp_runtime/qdp_artifact_contracts.py`
  - remaining generic portions of `QDP TDGL/src/tdgl_rf/io/*`
- Keep TDGL-only replay or checkpoint details out of `qdp_io`.

### `packages/qdp_validation/`

- The initial extracted authority now covers:
  - repo-consistency validation
  - frozen ALL-MIND interface validation
  - structural-versus-authoritative readiness gate semantics
- Active extracted sources in this phase:
  - `QDP/scripts/run_repo_validation.py` compatibility import surface
  - `QDP/tools/workflow/qdp_runtime/qdp_validation.py`
  - validation-facing portions of `QDP/tools/workflow/qdp_runtime/qdp_artifact_contracts.py`
- Deferred candidate sources for later extraction:
  - scientific-threshold and donor validation-pack harmonization from `QDP TDGL/validation/*`
- Keep materials-registry validation delegated to `qdp_meta_materials` and TDGL runtime-config validation delegated to `qdp_tdgl`.

### `packages/qdp_control/`

- The initial extracted authority now covers:
  - control-plane persistence
  - queue-manifest validation and queue-state orchestration
  - campaign prepare/plan logic
  - lab pack/ingest orchestration
  - run-ledger state
- Active extracted sources in this phase:
  - `QDP/tools/workflow/qdp_runtime/qdp_control_plane.py`
  - `QDP/tools/workflow/qdp_runtime/qdp_run_ledger.py`
  - `QDP/tools/workflow/qdp_runtime/qdp_campaign_planner.py`
  - `QDP/tools/workflow/qdp_runtime/qdp_queue.py`
  - `QDP/tools/workflow/qdp_runtime/qdp_lab_workflows.py`
- Deferred candidate sources for later extraction:
  - the transitional command shell in `QDP/tools/workflow/qdp_runtime/qdp_cli.py`
- This layer should orchestrate package calls rather than re-own materials or TDGL logic.

### `apps/mmm_studio/`

- Keep only CLI, API, and app-shell concerns from `MMM-Studio`.
- Remove domain ownership from the app shell after extraction.
- The app must consume package-layer APIs from `qdp_meta_materials`, `qdp_io`, `qdp_validation`, and `qdp_tdgl`.
- The initial extracted shell now lives under `apps/mmm_studio/src/mmm_studio/`.
- Active shell-owned files are limited to:
  - `cli.py`
  - `api.py`
  - `api_models.py`
  - compatibility shims for `config.py` and `errors.py`
  - package metadata and entrypoint files
- The shell must not copy registry, scoring, planning, provenance, or typed domain-model implementations out of `qdp_meta_materials`.

### `staging/`

- `staging/imported_qdp_mm/`
- `staging/imported_mmm_studio/`
- `staging/imported_qdp_tdgl/`

Each staging import should preserve traceability back to the donor repo.

Current Phase 3 state:

- `staging/imported_qdp_mm/snapshot/` contains a working-tree snapshot from the sibling donor repo `QDP MM`
- `staging/imported_mmm_studio/snapshot/` contains a working-tree snapshot from the sibling donor repo `MMM-Studio`
- `staging/imported_qdp_tdgl/snapshot/` contains a working-tree snapshot from the sibling donor repo `QDP TDGL`
- Deferred clean-branch history-preserving subtree commands are recorded in `docs/migration/STAGING_IMPORT_HISTORY_COMMANDS.md`
- `QDP TDGL` was dirty at import time, so exact lineage preservation for that snapshot requires an extra donor-side commit if maintainers want the later history import to match the staged tree byte-for-byte

### `labs/`

- `labs/materials/` should hold curated experimental branch packs, branch-specific synthetic studies, and non-authoritative protocol assets that should not live inside the canonical package.
- `labs/tdgl/` should hold curated example cases, validation packs, and exploratory runtime studies that are source inputs rather than package internals.

## What Should Not Survive As Duplicate Authorities

- A second materials or metamaterials domain model inside `apps/mmm_studio`
- A second TDGL runtime outside `packages/qdp_tdgl`
- A second materials registry loader outside `packages/qdp_meta_materials`
- A second generic provenance system outside `packages/qdp_io`
- A second generic materials scoring or tranche-planning stack outside `packages/qdp_meta_materials`
- The legacy QDP-style control surfaces embedded inside `QDP TDGL` once the runtime code has been extracted

## Manual Review Queue

- Decide which `MMM-Studio/src/mmm_studio/sim/*` pieces are worth keeping as adapter contracts versus being dropped as placeholders.
- Decide whether any `QDP MM` execution-queue mechanics should become reusable `qdp_control` patterns or remain branch-specific lab tooling.
- Define the exact split between generic provenance contracts in `qdp_io` and TDGL replay-specific provenance in `qdp_tdgl`.
- Rename or scope any surviving QDP mechanism-ranking surfaces so they cannot be mistaken for the canonical materials ranking system.
- Choose the exact history-preserving import method in Phase 3 and document the executed commands after the staging skeleton exists.

## Phase 2 Entry Criteria

- Create the target monorepo skeleton inside `QDP/` without moving donor code yet.
- Add package, app, docs, labs, configs, tools, and staging directories explicitly.
- Do not edit donor code in place inside sibling repos.
- Do not start extracting code until the staging import roots exist and the landing map above has been accepted as the current working plan.

## Phase 2 Completion Notes

- The target skeleton now exists inside `QDP/` through tracked placeholder files under:
  - `packages/`
  - `apps/`
  - `labs/`
  - `configs/`
  - `docs/adr/`
  - `docs/migration/`
  - `staging/`
  - `tests/unit/`, `tests/integration/`, `tests/scientific/`
- `REPO_MAP.md` now describes both the destination ownership zones and the still-active transitional implementation surfaces.
- `AGENTS.md` now includes consolidation rules, uniqueness constraints for `qdp_meta_materials` and `qdp_tdgl`, and the validation commands discovered during Phase 1.

## Phase 3 Completion Notes

- The three donor repos are now staged inside `QDP/` as working-tree snapshots under `staging/imported_*/snapshot/`.
- Each staging root now records:
  - the source repo path
  - the donor branch and HEAD observed at import time
  - donor cleanliness at import time
  - the snapshot exclusion set used in this run
  - the expected extraction surface and later-review content
- `docs/migration/STAGING_IMPORT_HISTORY_COMMANDS.md` now records the exact clean-branch subtree commands maintainers should use later if they want committed donor history preserved inside `QDP/`.

## Phase 4 Completion Notes

- `packages/qdp_meta_materials/` is no longer skeleton-only.
- The extracted canonical materials package now contains:
  - donor-derived typed models
  - canonical materials registry loading
  - canonical materials registry validation
  - canonical scoring and ranking logic
  - run and provenance helpers
  - sweep and tranche planning logic
  - retained RF and simulation adapter scaffolds
  - stable seed data under `data/seed/stable/`
- The package deliberately excludes the former MMM-Studio CLI and API shell, which remain staged donor material for later extraction into `apps/mmm_studio/`.
- QDP MM lineage is currently preserved through package-owned experimental lineage notes rather than a second runtime implementation.
- A minimum active validation surface now exists for the extracted package:
  - `$env:PYTHONPATH = "packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_qdp_meta_materials_smoke.py -q`

## Phase 5 Completion Notes

- `packages/qdp_tdgl/` is no longer skeleton-only.
- The extracted canonical TDGL runtime now contains:
  - donor-derived runtime package code under `src/qdp_tdgl/`
  - canonical TDGL package metadata and README guidance
  - canonical TDGL case configs and schemas under `configs/tdgl/`
  - canonical TDGL validation manifests and thresholds under `configs/validation/tdgl/`
  - copied unit test surfaces under `tests/unit/test_qdp_tdgl_config.py` and `tests/unit/test_qdp_tdgl_cli.py`
- Runtime config and validation-manifest lookup now resolve through the QDP monorepo layout instead of the donor repo root.
- Donor-era root wrappers, duplicate control surfaces, and other legacy runtime-adjacent files remain quarantined under `staging/imported_qdp_tdgl/`.
- Minimum active validation surfaces now exist for the extracted runtime:
  - `$env:PYTHONPATH = "packages/qdp_tdgl/src"; python -m pytest tests/unit/test_qdp_tdgl_config.py tests/unit/test_qdp_tdgl_cli.py -q`
  - `python scripts/run_repo_validation.py`

## Phase 6 Completion Notes

- `apps/mmm_studio/` is no longer skeleton-only.
- The extracted app shell now contains:
  - a CLI shell under `apps/mmm_studio/src/mmm_studio/cli.py`
  - a FastAPI shell under `apps/mmm_studio/src/mmm_studio/api.py`
  - API request and response models under `apps/mmm_studio/src/mmm_studio/api_models.py`
  - thin compatibility shims for `config.py` and `errors.py`
  - app-local packaging metadata under `apps/mmm_studio/pyproject.toml`
- The shell imports registry, scoring, run, validation, reporting, and sweep logic from `packages/qdp_meta_materials/` rather than re-owning those subsystems.
- Minimum active validation surfaces now exist for the extracted shell:
  - `$env:PYTHONPATH = "apps/mmm_studio/src;packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_mmm_studio_app_api.py tests/unit/test_mmm_studio_app_cli.py -q`
  - `python scripts/run_repo_validation.py`

## Phase 7 Completion Notes

- `packages/qdp_meta_materials/` now contains the active TDGL adapter registry and resolver under:
  - `src/qdp_meta_materials/adapters/tdgl/`
  - `data/seed/stable/mmm_tdgl_material_adapter_registry.yaml`
- `qdp_tdgl` now consumes that package-owned adapter surface during config validation.
- Canonical TDGL baselines now use a `materials` block to resolve:
  - `physics.u`
  - `physics.sigma_n`
  - `physics.alpha_background`
- Expanded TDGL configs now retain the material-registry identity, and TDGL provenance now records both runtime context and material-registry identity.
- Imported validation configs under `configs/validation/tdgl/` were path-rebased to the canonical `configs/tdgl/phase1_matrix_base.yaml` location.
- The committed Phase-2.4A validation manifest had its frozen `base_case_hash` rebased to the new material-reference contract.
- Minimum active validation surfaces now exist for the TDGL/material-reference wiring:
  - `$env:PYTHONPATH = "packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_qdp_meta_materials_smoke.py -q`
  - `$env:PYTHONPATH = "packages/qdp_tdgl/src;packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_qdp_tdgl_config.py tests/unit/test_qdp_tdgl_cli.py -q`
  - same-stack Phase-2.4A validation rerun through `qdp_tdgl.workflows.phase2_4a_validation.run_phase2_4a_validation(...)` after manifest rebasing
  - `python scripts/run_repo_validation.py`

## Phase 8 Progress Notes

- Collapsed the active materials registry loader surface so `qdp_meta_materials.registry.load_dataset` is the only canonical loader and `qdp_meta_materials.io` now owns serialization helpers only.
- Added a package-boundary integration test at `tests/integration/test_tdgl_material_registry_integration.py` to assert that canonical TDGL baselines resolve materials through `qdp_meta_materials` and record the registry identity in provenance.
- Added `docs/migration/MONOREPO_CONSOLIDATION_STATUS.md` as the active moved versus staged versus superseded versus manual-review inventory.
- Updated `AGENTS.md` and `REPO_MAP.md` so future work no longer treats the duplicate loader surface as active authority.
- Extracted `packages/qdp_io/` as the active shared package-layer serialization and generic runtime metadata authority.
- Rewired active package and shell code so:
  - `qdp_meta_materials`
  - `qdp_tdgl`
  - `apps/mmm_studio`
  now import shared serialization from `qdp_io` instead of re-owning package-local implementations.
- Converted `qdp_meta_materials/io.py` and `qdp_tdgl/io/reports.py` into compatibility facades so the active authority is `qdp_io`, not duplicate per-package writers.
- Broadened `packages/qdp_io/` so it now also owns:
  - stable payload hashing
  - file SHA-256 helpers
  - legacy-compatible JSON artifact writing
- Broadened `packages/qdp_io/` again so it now also owns:
  - retained-reference lookup by `ref_id`
  - surrogate provenance detection for retained references
  - authoritative-binding interpretation for retained references
  - collapsed retained-reference provenance mode used by the run ledger
- Broadened `packages/qdp_io/` again so it now also owns:
  - the shared timezone-aware UTC timestamp helper used by control, subsystem, and migration surfaces
- Broadened `packages/qdp_io/` again so it now also owns:
  - shared `timestamp_utc` generation across the active module runner path `M01`-`M15`, including `M03` and the canonical `M06` bootstrap harness
- Broadened `packages/qdp_io/` again so it now also owns:
  - shared artifact-report and module-report header construction for the active module runner path, subsystem tooling, queue reporting, run-ledger reporting, and migration/audit reporting
- Broadened `packages/qdp_io/` again so it now also owns:
  - shared module selftest-report payload construction for the active selftest-producing runner path and `tools/workflow/qdp_runtime/qdp_subsystem.py`
- Broadened `packages/qdp_io/` again so it now also owns:
  - shared `candidate_id` plus `result_summary` report-envelope construction for the active module path `M11`-`M15`
- Broadened `packages/qdp_io/` again so it now also owns:
  - shared `visible_source_only` plus `result_summary` report-envelope construction, with optional metadata and diagnostics, for the active visible-source module path `M07`-`M10`
- Rewired active consumers in:
  - `packages/qdp_control/`
  - `tools/workflow/qdp_runtime/qdp_cli.py`
  - `tools/workflow/qdp_runtime/qdp_subsystem.py`
  - `tests/`
  so they no longer import generic file/hash helpers from `qdp_artifact_contracts`.
- Rewired additional active consumers in:
  - `modules/m06_bootstrap_harness/runner.py`
  - `modules/m01_runtime_assembly/runner.py`
  - active visible-source module runners `M02`, `M04`, `M05`, `M07`-`M15`
  - `packages/qdp_control/`
  - `tools/workflow/qdp_runtime/qdp_subsystem.py`
  - `tools/workflow/qdp_runtime/qdp_module_sdk.py`
  - `tools/workflow/qdp_runtime/qdp_registry.py`
  - `tools/migration/repo_audit.py`
  - `tools/migration/write_migration_manifests.py`
  so retained-reference provenance logic and JSON artifact helpers no longer live as duplicate runtime-local implementations.
- Rewired the active module runner path:
  - `modules/m01_runtime_assembly/runner.py`
  - `modules/m02_schema_validator/runner.py`
  - `modules/m03_reference_resolution/runner.py`
  - `modules/m04_branch_registration/runner.py`
  - `modules/m05_stage_machine/runner.py`
  - `modules/m06_bootstrap_harness/runner.py`
  - `modules/m07_family_triage/runner.py`
  - `modules/m08_baseline_fit/runner.py`
  - `modules/m09_mechanism_competition/runner.py`
  - `modules/m10_artifact_audit/runner.py`
  - `modules/m11_lindblad_equivalence/runner.py`
  - `modules/m12_experiment_design/runner.py`
  - `modules/m13_cross_device_gate/runner.py`
  - `modules/m14_promotion_caps/runner.py`
  - `modules/m15_governance_guardrails/runner.py`
  so shared `timestamp_utc` generation no longer lives as duplicate inline wall-clock calls across the canonical module-report path.
- Rewired additional active report surfaces:
  - `tools/workflow/qdp_runtime/qdp_subsystem.py`
  - `packages/qdp_control/src/qdp_control/queue.py`
  - `packages/qdp_control/src/qdp_control/run_ledger.py`
  - `tools/migration/repo_audit.py`
  - `tools/migration/write_migration_manifests.py`
  so shared artifact-report and module-report header construction no longer lives as duplicate inline dict prefixes across the canonical report path.
- Rewired active selftest-producing report surfaces:
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
  - `tools/workflow/qdp_runtime/qdp_subsystem.py`
  so shared selftest summary payload construction no longer lives as duplicate inline `cases_total`, `cases_passed`, `all_passed`, and optional schema-visible metadata assembly across the canonical selftest-report path.
- Rewired active candidate-summary report surfaces:
  - `modules/m11_lindblad_equivalence/runner.py`
  - `modules/m12_experiment_design/runner.py`
  - `modules/m13_cross_device_gate/runner.py`
  - `modules/m14_promotion_caps/runner.py`
  - `modules/m15_governance_guardrails/runner.py`
  so shared `candidate_id` plus `result_summary` report-envelope construction no longer lives as duplicate inline payload assembly across the canonical candidate-summary report path.
- Rewired active visible-source report surfaces:
  - `modules/m07_family_triage/runner.py`
  - `modules/m08_baseline_fit/runner.py`
  - `modules/m09_mechanism_competition/runner.py`
  - `modules/m10_artifact_audit/runner.py`
  so shared `visible_source_only` plus `result_summary` report-envelope construction no longer lives as duplicate inline payload assembly across the canonical visible-source report path.
- Reduced `tools/workflow/qdp_runtime/qdp_artifact_contracts.py` to a compatibility facade over `qdp_io` and `qdp_validation`.
- Extracted `packages/qdp_validation/` as the active umbrella validation authority for repo-consistency and frozen ALL-MIND interface validation.
- Converted:
  - root `qdp_validation.py`
  - `tools/workflow/qdp_runtime/qdp_validation.py`
  - validation-facing portions of `tools/workflow/qdp_runtime/qdp_artifact_contracts.py`
  into compatibility facades so the implementation authority lives in `packages/qdp_validation/`.
- Minimum active validation surfaces for the extracted `qdp_validation` boundary now include:
  - `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_validation/src"; python -m pytest tests/unit/test_qdp_validation_smoke.py -q`
  - `python -m pytest tests/test_authoritative_readiness.py tests/test_run_repo_validation.py tests/test_all_mind_interface_validation.py -q`
  - `python scripts/run_repo_validation.py`
- Extracted `packages/qdp_control/` as the active umbrella control authority for queue/control-plane persistence, campaign prepare/plan logic, lab pack/ingest orchestration, and run-ledger state.
- Converted:
  - `tools/workflow/qdp_runtime/qdp_control_plane.py`
  - `tools/workflow/qdp_runtime/qdp_run_ledger.py`
  - `tools/workflow/qdp_runtime/qdp_campaign_planner.py`
  - `tools/workflow/qdp_runtime/qdp_queue.py`
  - `tools/workflow/qdp_runtime/qdp_lab_workflows.py`
  into compatibility facades so the implementation authority lives in `packages/qdp_control/`.
- Rewired the active CLI shell in `tools/workflow/qdp_runtime/qdp_cli.py` to consume `qdp_control` directly instead of the old runtime-local implementations.
- Minimum active validation surfaces for the extracted `qdp_control` boundary now include:
  - `$env:PYTHONPATH = "packages/qdp_control/src"; python -m pytest tests/unit/test_qdp_control_smoke.py tests/test_branch_sweep_traversal.py tests/test_execution_queue.py -q`
  - `python scripts/run_repo_validation.py`
- Minimum active validation surfaces for the extracted `qdp_io` boundary now include:
  - `$env:PYTHONPATH = "packages/qdp_io/src"; python -m pytest tests/unit/test_qdp_io_smoke.py -q`
  - `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_qdp_meta_materials_smoke.py -q`
  - `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_tdgl/src;packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_qdp_tdgl_config.py tests/unit/test_qdp_tdgl_cli.py tests/unit/test_qdp_tdgl_run_case_outputs.py tests/integration/test_tdgl_material_registry_integration.py -q`
