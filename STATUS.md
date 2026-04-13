# Status

- class: `incubate`
- activity: `active`
- last reviewed: `2026-04-12`
- owner: `forre`
- suggested promotion mode: `incubation link`

## Summary

QDP remains the closest downstream program to the ALL-MIND core, but it stays incubate. The repository surface is now cleaner, its ALL-MIND interface is narrower, and the frozen downstream contract now derives authoritative readiness from explicit retained-source bindings and module-level authoritative bindings rather than working-patch placeholders. Campaign planning is now artifact-stable through prepared `M12` materialization, with freshness enforced against raw source candidates before ranking. The consolidation boundary is now explicit: reusable materials, TDGL runtime, IO, validation, and control logic live under `packages/`, while the root command entrypoints remain shell surfaces and the remaining `tools/workflow/qdp_runtime/` files are now explicitly classified as shell, compatibility facade, or still-authoritative pending extraction in `REPO_MAP.md`.

## Current risks

- promotion remains broader than the compact control-plane interface even though the frozen downstream contract is now authoritatively ready,
- retained-source recovery still depends on explicit authoritative bindings and must not be misrepresented as independently recovered retained provenance,
- campaign planning now depends on prepared `M12` materialization discipline, so stale preparation must be treated as an operational failure rather than silently recomputed planner state,
- the consolidation still relies on a narrowed set of explicitly labeled runtime-shell compatibility facades and repo-root path helpers while broader manifest/provenance cleanup continues,
- the ALL-MIND boundary must stay limited to compact status and interface artifacts rather than whole-repo ingestion.
