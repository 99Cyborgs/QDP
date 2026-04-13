# imported_qdp_tdgl

## Import Status

- Classification: `staged for later review`
- Snapshot status: imported on `2026-04-10`
- Snapshot root: `staging/imported_qdp_tdgl/snapshot/`
- Source repo: sibling donor checkout `QDP TDGL`
- Donor branch at import: `codex/tdgl-g2-seeded-vortex-init`
- Donor HEAD at import: `889621025893ef1064de6818d281097686cb7a12`
- Donor worktree at import: `dirty`
- Approximate staged file count: `274`

## Import Method Used In This Run

- Imported as a working-tree snapshot by filesystem copy into `snapshot/`.
- Excluded from the snapshot:
  - `.git/`
  - `.pytest_cache/`
  - `__pycache__/`
  - `artifacts/`
  - `runs/`
  - `*.pyc`
- Git history was not imported in this run. See `docs/migration/STAGING_IMPORT_HISTORY_COMMANDS.md` for the clean-branch subtree procedure that should be used later if maintainers want lineal history preserved inside `QDP/`.
- Important limitation: the staged snapshot includes uncommitted donor changes. Any later history-preserving import can only match this snapshot exactly if maintainers first commit those donor-side changes on a temporary branch or otherwise formalize that donor state.

## Expected Extraction Surface

- QDP TDGL is the selected donor for the canonical TDGL runtime.
- The strongest expected extraction surface is:
  - `src/tdgl_rf/`
  - runtime configs under `configs/`
  - TDGL validation assets under `validation/`
  - the strongest runtime-focused tests under `tests/`
- Expected landing zone later: `packages/qdp_tdgl/`

## Later-Review Content

- Root `qdp.py`, `qdp_validation.py`, `modules/`, `tools/`, and related governance docs are duplicate QDP-style control surfaces staged for later review, not future runtime authority
- `.agents/` is donor-local agent guidance and remains staged reference material only
- `ornl_tdgl_codex_pack.zip` and `RL framework/qdp_agentic_framework_reference.zip` are retained for traceability; manual review is still required before any archive or removal decision
