# AGENTS.md

QDP is an incubate repo: strategically important, but not part of the default core operating surface.

## Read first

1. `README.md`
2. `SYSTEM_BOUNDARY.md`
3. `STATUS.md`
4. `REPO_MAP.md`
5. `VALIDATION.md`
6. `QDP_REPO_REFACTOR_PLAN.md`

## Working rules

- Keep source materials, runtime code, specs, and generated artifacts conceptually separate.
- Do not treat generated outputs under `artifacts/outputs/` as the governing source of truth.
- Keep ALL-MIND integration narrow: status, interfaces, and promotion artifacts, not whole-repo ingestion.
- Update `STATUS.md` and `PROMOTION_NOTES.md` when the class, boundary, or promotion posture changes.

## Skills

- Repo-local recurring workflows live under `.agents/skills/`.
- Start with `.agents/skills/README.md` and `.agents/skills/COVERAGE_MATRIX.md` to choose the right skill.
- Treat `tdgl-rf` and `qdp.py` as separate control planes; choose the matching skill instead of mixing their procedures.
- Keep always-on conventions here in `AGENTS.md`; keep long refactor or milestone work in `QDP_REPO_REFACTOR_PLAN.md`, not in skills.
