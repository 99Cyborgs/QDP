# imported_mmm_studio

## Import Status

- Classification: `staged for later review`
- Snapshot status: imported on `2026-04-10`
- Snapshot root: `staging/imported_mmm_studio/snapshot/`
- Source repo: sibling donor checkout `MMM-Studio`
- Donor branch at import: `main`
- Donor HEAD at import: `f9b55444a8175103c481c8095860a26ff814380d`
- Donor worktree at import: `clean`
- Approximate staged file count: `191`

## Import Method Used In This Run

- Imported as a working-tree snapshot by filesystem copy into `snapshot/`.
- Excluded from the snapshot:
  - `.git/`
  - `.hypothesis/`
  - `.mypy_cache/`
  - `.pytest_cache/`
  - `.ruff_cache/`
  - `__pycache__/`
  - `artifacts/`
  - `outputs/`
  - `*.pyc`
- Git history was not imported in this run. See `docs/migration/STAGING_IMPORT_HISTORY_COMMANDS.md` for the clean-branch subtree procedure that should be used later if maintainers want lineal history preserved inside `QDP/`.

## Expected Extraction Surface

- MMM-Studio is the selected donor for the canonical materials and metamaterials package.
- The strongest expected extraction surface is under `src/mmm_studio/`:
  - typed models
  - registry loading
  - registry validation
  - scoring
  - sweep and tranche planning
  - run metadata and IO helpers
  - TDGL-facing adapter contracts
- Stable seed data is expected to move from `data/mmm_seed/` into `packages/qdp_meta_materials/data/seed/stable/`.

## Later-Review Content

- `src/mmm_studio/api.py` and `src/mmm_studio/cli.py`: expected app-shell donors for `apps/mmm_studio/`, not future package authority
- `examples/` and `docs/`: staged reference material for `labs/materials/` and `docs/migration/`
- `tests/`: staged donor tests for selective reuse in `tests/unit/`, `tests/integration/`, and `tests/scientific/`
