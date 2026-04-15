# Gap Log

## Intentionally Unencoded

### Reserved `run-inference`, `convergence`, and `verify`
- Evidence: `src/tdgl_rf/cli.py`
- Reason left unencoded:
  These commands are reserved or explicitly non-active surfaces, so a skill would only restate unsupported behavior.

### Legacy repo restructuring / wrapper migration
- Evidence: `QDP_REPO_REFACTOR_PLAN.md`, `REPO_MAP.md`, `ARCHITECTURE_SUMMARY.md`
- Reason left unencoded:
  This is milestone-specific migration work, not a stable recurring operator workflow. It belongs in the refactor plan, not in reusable skills.

## Repo Gaps Found During Audit

### No `.github/workflows/` CI surface
- Result:
  No CI-specific skill was created because the repository does not currently expose a committed GitHub Actions workflow surface to mirror.

### Mixed repo map versus active runtime surface
- Evidence:
  `REPO_MAP.md` and `ARCHITECTURE_SUMMARY.md` still describe broader `modules/`, `runtime/`, `config/`, and `specs/` surfaces, but the actively documented recurring workflows live in the packaged `tdgl-rf` CLI under `src/tdgl_rf/`.
- Impact:
  The skills target the active `tdgl-rf` surface. Broader repo-structure cleanup remains plan work.

### Generated run artifacts under `configs/runs`
- Evidence:
  `configs/runs/` exists alongside source configs even though root guidance says generated outputs should not become source-of-truth surfaces.
- Impact:
  Workflow indexing and human review can confuse retained execution artifacts with governing config inputs.

### No nested `AGENTS.md` or subtree-local workflow splits
- Result:
  No subtree-specific skills were created. The audit did not find any local subtree with its own authority chain or materially different recurring procedure.

## Unverified Until Explicitly Run

- `python -m pip install -e .[dev]` was treated as the documented bootstrap command, but the environment may already have the editable install and dependencies satisfied.
