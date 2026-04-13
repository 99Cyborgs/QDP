# qdp_io

Destination package for shared serialization, manifests, artifact metadata, and non-TDGL-specific provenance helpers.

This package should absorb reusable IO and artifact-contract logic without becoming a second runtime or a second domain model.

Current extraction status:

- active shared serialization surface under `src/qdp_io/serialization.py`
- active generic runtime metadata helpers under `src/qdp_io/runtime_metadata.py`
- active artifact hash and JSON artifact helper surface under `src/qdp_io/artifacts.py`
- active retained-reference manifest and provenance helper surface under `src/qdp_io/reference_manifest.py`
- active object-root JSON loader surface under `src/qdp_io/serialization.py`
- active module-registry payload and markdown builder surface under `src/qdp_io/module_registry.py`
- active shared report-header helper surface under `src/qdp_io/artifacts.py`
- active shared module selftest-report payload helper surface under `src/qdp_io/artifacts.py`
- active shared candidate result-summary report helper surface under `src/qdp_io/artifacts.py`
- active shared visible-source result-summary report helper surface under `src/qdp_io/artifacts.py`
- broader reusable manifest contracts, artifact ledgers, and provenance schemas are still deferred

Active ownership in this phase:

- JSON, YAML, text, and CSV serialization helpers
- object-root JSON loading helpers used by active runtime-shell compatibility surfaces
- generic runtime metadata snapshots for provenance payloads
- stable payload hashing and file SHA-256 helpers
- legacy-compatible JSON artifact writing used by extracted package and runtime compatibility surfaces
- shared timezone-aware UTC timestamp helper used by active control, subsystem, and migration surfaces
- shared report-header helpers for artifact-scoped and module-scoped reports on the active module, audit, and queue-report path
- shared module selftest-report payload helpers for canonical selftest summary counts, pass aggregation, and optional schema-visible metadata on the active module and subsystem path
- shared candidate-scoped result-summary report helpers for the canonical `candidate_id` plus `result_summary` envelope on the active module path
- shared visible-source result-summary report helpers for the canonical `visible_source_only` plus `result_summary` envelope, with optional metadata and diagnostics, on the active module path
- retained-reference lookup, surrogate provenance detection, and authoritative-binding interpretation for shared QDP runtime/provenance flows
- module-registry payload and markdown builders used by the bootstrap-facing module-registry emission path

Explicitly not owned here in this phase:

- TDGL-only replay or checkpoint provenance
- materials-domain models or registry semantics
- schema validation and frozen ALL-MIND readiness gates
- repo-root control-plane runtime logic

Compatibility note:

- `tools/workflow/qdp_runtime/qdp_artifact_contracts.py` now acts as a compatibility facade over `qdp_io` and `qdp_validation` rather than owning the generic file/hash helpers itself
- `tools/workflow/qdp_runtime/qdp_registry.py` now acts as a compatibility facade over `qdp_io.module_registry` rather than owning the module-registry payload and markdown builders itself
- the M06 bootstrap harness, M01 runtime assembly runner, and `qdp_control` run ledger now delegate retained-reference lookup or interpretation to `qdp_io` rather than keeping second rule copies
- `tools/workflow/qdp_runtime/qdp_module_sdk.py`, `tools/workflow/qdp_runtime/qdp_subsystem.py`, and `tools/workflow/qdp_runtime/qdp_cli.py` now delegate object-root JSON loading to `qdp_io` rather than keeping separate runtime-local root-shape checks
- migration/report tooling such as `tools/migration/repo_audit.py` and `tools/migration/write_migration_manifests.py` now delegate generic JSON artifact writing to `qdp_io`
- the active visible-source module runners `M02`, `M04`, `M05`, `M07`-`M15` now delegate generic JSON artifact writing to `qdp_io` rather than carrying per-runner writer copies
- `qdp_control`, `tools/workflow/qdp_runtime/qdp_subsystem.py`, and migration tooling now delegate shared UTC timestamp generation to `qdp_io` rather than keeping local `utc_now()` helpers
- the active module runner path `M01`-`M15`, including `M03` and `M06`, now delegates `timestamp_utc` generation to `qdp_io` rather than calling `datetime.now(timezone.utc).isoformat()` inline
- the active module runner path, `qdp_subsystem`, queue reporting, run-ledger reporting, and migration/audit reporting now delegate standard report-header construction to `qdp_io` rather than rebuilding the leading `artifact_id` and `timestamp_utc` or `module_id` fields inline
- the active selftest-producing runner path `M01`, `M02`, `M04`, `M05`, and `M07`-`M15`, plus `tools/workflow/qdp_runtime/qdp_subsystem.py`, now delegate canonical selftest summary payload construction to `qdp_io` rather than rebuilding `cases_total`, `cases_passed`, `all_passed`, and optional selftest metadata inline
- the active candidate-summary runner path `M11`-`M15` now delegates canonical `candidate_id` plus `result_summary` report-envelope construction to `qdp_io` rather than rebuilding that report shape inline
- the active visible-source report path `M07`-`M10` now delegates canonical `visible_source_only` plus `result_summary` report-envelope construction to `qdp_io` rather than rebuilding that report shape inline

Validation in this phase should target the package directly, for example:

```powershell
$env:PYTHONPATH = "packages/qdp_io/src"
python -m pytest tests/unit/test_qdp_io_smoke.py -q
```
