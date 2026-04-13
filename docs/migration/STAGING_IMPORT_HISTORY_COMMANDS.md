# Staging Import History Commands

This document records the deferred clean-branch commands maintainers should use if they want to preserve donor git history inside `QDP/` after the working-tree snapshots have already been staged.

## Current State

- `staging/imported_qdp_mm/snapshot/` records the donor working tree from the sibling repo `QDP MM` at `7cded8feb7d57a07041e7c203e9aca7e4ef73c31`
- `staging/imported_mmm_studio/snapshot/` records the donor working tree from the sibling repo `MMM-Studio` at `f9b55444a8175103c481c8095860a26ff814380d`
- `staging/imported_qdp_tdgl/snapshot/` records the donor working tree from the sibling repo `QDP TDGL` at `889621025893ef1064de6818d281097686cb7a12`
- `QDP TDGL` was dirty at snapshot time, so the committed SHA above does not fully represent the imported snapshot tree

## Why History Preservation Was Deferred In This Run

- The destination `QDP/` worktree was already dirty.
- Phase 3 prioritized stable, traceable donor snapshots over disruptive history surgery inside an already-active umbrella repo.
- `QDP TDGL` also had uncommitted donor changes, which makes exact history-preserving replay impossible without an extra donor-side commit.

## Clean-Branch History Import Procedure

Run the following from a clean `QDP/` working tree if the goal is to preserve donor history alongside the already-staged `snapshot/` trees. Replace the placeholder checkout paths with the local paths for your sibling donor clones:

```powershell
Set-Location "<path-to-QDP>"
git switch -c codex/consolidation-history-imports
git status --short

git remote add donor-qdp-mm "<path-to-QDP-MM>"
git remote add donor-mmm-studio "<path-to-MMM-Studio>"
git remote add donor-qdp-tdgl "<path-to-QDP-TDGL>"

git fetch donor-qdp-mm main
git fetch donor-mmm-studio main
git fetch donor-qdp-tdgl codex/tdgl-g2-seeded-vortex-init

git subtree add --prefix=staging/imported_qdp_mm/history donor-qdp-mm 7cded8feb7d57a07041e7c203e9aca7e4ef73c31
git subtree add --prefix=staging/imported_mmm_studio/history donor-mmm-studio f9b55444a8175103c481c8095860a26ff814380d
git subtree add --prefix=staging/imported_qdp_tdgl/history donor-qdp-tdgl 889621025893ef1064de6818d281097686cb7a12

git remote remove donor-qdp-mm
git remote remove donor-mmm-studio
git remote remove donor-qdp-tdgl
```

Notes:

- These commands preserve committed donor history only.
- The `history/` trees should remain staged reference material; they are not package authority.
- Do not remove the corresponding `snapshot/` trees until extraction is complete and the remaining differences are documented.

## Preserving The Dirty `QDP TDGL` Snapshot Exactly

If maintainers want the later history-preserving import to match the already-staged `QDP TDGL` snapshot exactly, they first need a temporary donor commit that captures the uncommitted changes which were present on `2026-04-10`.

One safe approach is:

```powershell
git -C "<path-to-QDP-TDGL>" switch -c codex/consolidation-stage-2026-04-10
git -C "<path-to-QDP-TDGL>" add -A
git -C "<path-to-QDP-TDGL>" commit -m "Capture working tree for QDP umbrella staging import"

git -C "<path-to-QDP>" remote add donor-qdp-tdgl "<path-to-QDP-TDGL>"
git -C "<path-to-QDP>" fetch donor-qdp-tdgl codex/consolidation-stage-2026-04-10
git -C "<path-to-QDP>" subtree add --prefix=staging/imported_qdp_tdgl/history donor-qdp-tdgl codex/consolidation-stage-2026-04-10
git -C "<path-to-QDP>" remote remove donor-qdp-tdgl
```

This procedure was not executed in the current run.
