# imported_qdp_mm

## Import Status

- Classification: `staged for later review`
- Snapshot status: imported on `2026-04-10`
- Snapshot root: `staging/imported_qdp_mm/snapshot/`
- Source repo: sibling donor checkout `QDP MM`
- Donor branch at import: `main`
- Donor HEAD at import: `7cded8feb7d57a07041e7c203e9aca7e4ef73c31`
- Donor worktree at import: `clean`
- Approximate staged file count: `40`

## Import Method Used In This Run

- Imported as a working-tree snapshot by filesystem copy into `snapshot/`.
- Excluded from the snapshot:
  - `.git/`
  - `__pycache__/`
  - `.pytest_cache/`
  - `*.pyc`
- Git history was not imported in this run. See `docs/migration/STAGING_IMPORT_HISTORY_COMMANDS.md` for the clean-branch subtree procedure that should be used later if maintainers want lineal history preserved inside `QDP/`.

## Expected Extraction Surface

- QDP MM is not the canonical reusable materials package.
- The expected donor value is semantic lineage and branch-pack protocol discipline:
  - conservative metastable-memory naming
  - explicit pre-run versus as-run binding states
  - branch-specific intake, analysis, and reconciliation patterns
- Expected landing zones later:
  - reusable semantics and protocol vocabulary into `packages/qdp_meta_materials/`
  - experimental branch assets into `labs/materials/`

## Later-Review Content

- `qdp/branches/e01_mm_flux_history_hysteresis/`: staged branch pack for selective extraction, not package authority
- `qdp/branches/e01_mm_flux_history_hysteresis.zip`: staged donor artifact retained for traceability; manual review still required before any archive or removal decision
