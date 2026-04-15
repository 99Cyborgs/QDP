# QDP Skills

This directory holds the minimal repo-local Codex skills for recurring work in the active `tdgl-rf` surface.

Scope decisions from the repository audit:

- All approved skills live at the repo root because the recurring workflows are exposed through one shared CLI, one shared validation surface, and repo-wide docs/contracts.
- No subtree-local `.agents/skills/` directories were created because no inspected subtree had a meaningfully different local procedure or trigger boundary.
- Always-on repo rules stay in `AGENTS.md`; long refactor or migration work stays in `QDP_REPO_REFACTOR_PLAN.md`.

Approved skills:

1. `qdp-run-case`
   Validate one config, execute one case, and inspect one run directory.
2. `qdp-phase1-campaign`
   Dry-run, execute, resume, and summarize deterministic phase-1 matrix campaigns.
3. `qdp-phase1-validation`
   Run the committed deterministic validation tranche and its component checks.
4. `qdp-seeded-vortex-suite`
   Run the committed Phase-2.2 seeded-vortex validation suite without widening the claim boundary.
5. `qdp-seeded-vortex-experiment-pack`
   Run an explicit Phase-2.3 deterministic seeded-vortex experiment pack and inspect its artifacts.
6. `qdp-phase2-4a-runtime-smoke`
   Run the committed Phase-2.4A stochastic seeded-vortex runtime smoke manifest without widening the scientific claim boundary.
7. `qdp-evidence-bundle`
   Package one completed deterministic phase-1 validation run into the reviewer-facing evidence bundle.
8. `qdp-contract-sync`
   Change schema or manifest contracts and keep validators, docs, CLI dispatch, and tests synchronized.
9. `qdp-governance-check`
   Run the legacy QDP bootstrap harness and candidate-validation sweep under `artifacts/`.
10. `qdp-module-ops`
   List, self-test, and directly run legacy QDP modules `m03` through `m10`.

See `COVERAGE_MATRIX.md` for the full workflow map and `GAPS.md` for intentionally unencoded or still-unverified areas.
