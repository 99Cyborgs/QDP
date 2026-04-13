# Promotion Notes

## Current class

`incubate`

## Suggested promotion mode

`incubation link`

## Why not core yet

- the repo now achieves authoritative readiness through explicit retained-source and module authoritative bindings, but that does not justify whole-repo promotion by itself,
- the monorepo boundary is clearer than before, but several extracted package authorities still depend on transitional runtime-shell and repo-root path surfaces, so the architecture is not yet promotion-clean,
- retained-source recovery still relies on governed authoritative bindings rather than independently recovered retained provenance,
- prepared campaign artifacts under `artifacts/reports/campaigns/` and prepared `M12` outputs remain repo-local operational artifacts and are not part of the frozen ALL-MIND control-plane contract,
- QDP should remain a narrow downstream integration surface rather than a whole-repo ALL-MIND runtime dependency.

## What would justify promotion

- stable repo map and navigation surface,
- explicit machine-readable interface into ALL-MIND, currently frozen as `artifacts/reports/system/all_mind_interface.json`,
- repeat operational dependence that is cheaper than keeping QDP fully separate,
- a decision record approving the class change.
