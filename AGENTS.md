# AGENTS.md

QDP is an incubate repo: strategically important, but not part of the default core operating surface.

## Read first

1. `README.md`
2. `SYSTEM_BOUNDARY.md`
3. `STATUS.md`
4. `REPO_MAP.md`
5. `VALIDATION.md`
6. `QDP_REPO_REFACTOR_PLAN.md`
7. `CONSOLIDATION_PLAN.md` for monorepo consolidation, package-boundary, app-shell, staging, or donor-import work
8. `CONSOLIDATION_LOG.md` for the current consolidation phase state and prior migration decisions

## Working rules

- Keep source materials, runtime code, specs, and generated artifacts conceptually separate.
- Do not treat generated outputs under `artifacts/outputs/` as the governing source of truth.
- Separate commit scopes into one primary bucket at a time: `active_runtime`, `staged_donor`, or `generated_artifacts`. `docs_metadata` may accompany one primary bucket, but mixed primary-bucket commits require explicit override and justification.
- Use `python scripts/check_change_scope.py --staged` before commit preparation for local bucket classification. Use `python scripts/check_change_scope.py --ref <base>..<head>` when reviewing an existing diff span.
- `active_runtime` includes `qdp.py`, `qdp_validation.py`, `modules/`, `packages/`, `apps/`, `tools/workflow/qdp_runtime/`, `tools/validators/`, `config/`, `configs/`, `scripts/`, and `tests/`.
- `staged_donor` includes `staging/imported_*/` and `legacy/imported_artifacts/`.
- `generated_artifacts` includes `artifacts/outputs/`, `artifacts/reports/`, `artifacts/lab/`, and `runs/`.
- `docs_metadata` includes root markdown guidance files, `.github/`, and `docs/`.
- Treat `tests/` as active-runtime support files, not a standalone commit bucket. Test-only diffs must ride with the runtime source change they validate.
- Default commit sequence for behavior-changing work is: runtime commit first, artifact-refresh commit second if generated evidence changed, and staging/import commit separately when donor snapshots or migration bookkeeping move.
- Keep ALL-MIND integration narrow: status, interfaces, and promotion artifacts, not whole-repo ingestion.
- Update `STATUS.md` and `PROMOTION_NOTES.md` when the class, boundary, or promotion posture changes.
- Preserve QDP as the umbrella destination repo.
- Treat `packages/`, `apps/`, `labs/`, `configs/`, and `staging/` as destination ownership zones during consolidation.
- There must be exactly one canonical materials package: `packages/qdp_meta_materials/`.
- There must be exactly one canonical TDGL runtime: `packages/qdp_tdgl/`.
- Keep UI, API, and CLI shells in `apps/`; reusable domain logic belongs in `packages/`.
- Preserve QDP MM lineage in adopted naming, migration notes, and conservative branch semantics when that lineage is the clearest semantic source.
- If uncertain about deletion, move content into `staging/` or another clearly marked non-authoritative area and document the reason in `CONSOLIDATION_LOG.md`.
- Update `REPO_MAP.md`, `CONSOLIDATION_PLAN.md`, and `CONSOLIDATION_LOG.md` when package ownership, staging status, or winner decisions change.

## Validation

- Canonical QDP repo validation remains:
  - `python scripts/run_repo_validation.py`
- Add `--require-authoritative-ready` only when the task is making a real readiness or staging claim rather than a structural one.
- For active-runtime changes, review changed runtime symbols with file-qualified GitNexus analysis before commit:
  1. `gitnexus_context({name: "symbolName", file_path: "path/to/file.py"})` or `gitnexus_context({uid: "..."})`
  2. `gitnexus_impact({target: "symbolName", direction: "upstream"})`
  3. confirm the impact result matches the disambiguated context before treating it as authoritative
  4. review every `d=1` caller first and record one disposition per caller: `updated`, `validated unaffected`, or `deferred with risk note`
  5. ignore GitNexus hits for `staging/imported_*/`, generated artifacts, and docs unless the commit is explicitly a staging-only review
- For consolidation changes that only add skeleton structure, docs, or destination-boundary guidance and do not change the active runtime or control plane, use the smallest sufficient validation first:
  - read back changed files
  - verify the changed paths explicitly with scoped `git diff` or `git status`
- Donor-local validation commands discovered during the forensic audit:
  - `QDP MM`: `python -m unittest discover -s qdp/branches/e01_mm_flux_history_hysteresis -p "test_*.py"`
  - `MMM-Studio`: `pytest -q`
  - `QDP TDGL`: `pytest`
- Donor-local validation does not replace QDP's canonical repo validation once active QDP runtime, validation, or control surfaces are modified.
- Extracted package-level validation currently available:
  - `QDP qdp_io`: `$env:PYTHONPATH = "packages/qdp_io/src"; python -m pytest tests/unit/test_qdp_io_smoke.py -q`
  - `QDP qdp_validation`: `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_validation/src"; python -m pytest tests/unit/test_qdp_validation_smoke.py -q`
  - `QDP qdp_control`: `$env:PYTHONPATH = "packages/qdp_control/src"; python -m pytest tests/unit/test_qdp_control_smoke.py tests/test_branch_sweep_traversal.py tests/test_execution_queue.py -q`
  - `QDP qdp_meta_materials`: `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_qdp_meta_materials_smoke.py -q`
  - `QDP qdp_tdgl`: `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_tdgl/src;packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_qdp_tdgl_config.py tests/unit/test_qdp_tdgl_cli.py tests/unit/test_qdp_tdgl_run_case_outputs.py -q`
  - `QDP apps/mmm_studio`: `$env:PYTHONPATH = "packages/qdp_io/src;apps/mmm_studio/src;packages/qdp_meta_materials/src"; python -m pytest tests/unit/test_mmm_studio_app_api.py tests/unit/test_mmm_studio_app_cli.py -q`
  - `QDP materials-to-TDGL integration`: `$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_tdgl/src;packages/qdp_meta_materials/src"; python -m pytest tests/integration/test_tdgl_material_registry_integration.py -q`
- Consolidation-closure validation scope:
  - promoted into the active umbrella gate: canonical repo validation, the package smoke tests above, and `tests/integration/test_tdgl_material_registry_integration.py`
  - intentionally left staged: donor-wide `MMM-Studio` tests, donor-wide `QDP TDGL` suites beyond the promoted slices, and branch-pack `QDP MM` tests
  - out of scope for the default closure gate: staged donor acceptance and regression packs plus any high-cost scientific suites not called by `python scripts/run_repo_validation.py`

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **QDP** (11727 symbols, 27694 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST disambiguate active-runtime symbols with `file_path` or `uid` before relying on GitNexus impact results.** Use file-qualified review for runtime changes so staged donor copies and generated artifacts do not pollute the blast-radius read.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/QDP/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/QDP/context` | Codebase overview, check index freshness |
| `gitnexus://repo/QDP/clusters` | All functional areas |
| `gitnexus://repo/QDP/processes` | All execution flows |
| `gitnexus://repo/QDP/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. active-runtime symbol review used `file_path` or `uid` disambiguation and every `d=1` caller has a recorded disposition
3. No HIGH/CRITICAL risk warnings were ignored
4. `gitnexus_detect_changes()` confirms changes match expected scope
5. `python scripts/check_change_scope.py --staged` reports one primary bucket unless an explicit mixed-scope override is being used

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
