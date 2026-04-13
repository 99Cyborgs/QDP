# Change Hygiene Workflow

This workflow keeps active runtime edits, staged donor imports, and generated evidence in separate commits so GitNexus risk reads stay reviewable instead of collapsing into one broad aggregate warning.

## Buckets

- `active_runtime`: `qdp.py`, `qdp_validation.py`, `modules/`, `packages/`, `apps/`, `tools/workflow/qdp_runtime/`, `tools/validators/`, `config/`, `configs/`, `scripts/`, and `tests/`
- `staged_donor`: `staging/imported_*/` and `legacy/imported_artifacts/`
- `generated_artifacts`: `artifacts/outputs/`, `artifacts/reports/`, `artifacts/lab/`, and `runs/`
- `docs_metadata`: root markdown guidance files and `docs/`

`docs_metadata` may accompany one primary bucket. `tests/` are active-runtime support files and are not a standalone commit bucket.

## Scope Check Commands

Inspect the paths you are about to commit:

```bash
git diff --name-only --cached
python scripts/check_change_scope.py --staged
```

Inspect an existing diff span:

```bash
git diff --name-only main..HEAD
python scripts/check_change_scope.py --ref main..HEAD
```

If you intentionally need a mixed primary-bucket diff, require an explicit override and capture the reason in the review notes:

```bash
python scripts/check_change_scope.py --staged --allow-mixed-scope
```

The checker prints JSON with:

- `primary_bucket`
- `mixed_scope_violations`
- `accepted_mixed_scope`
- `policy_violations`
- exact `bucket_files`

## Runtime Review Workflow

For every GitNexus-named changed symbol in an active-runtime path:

1. Disambiguate the symbol with a file-qualified lookup:

```text
gitnexus_context({name: "symbolName", file_path: "packages/qdp_tdgl/src/qdp_tdgl/example.py"})
```

2. Run upstream blast-radius review on the file-qualified symbol:

```text
gitnexus_impact({target: "symbolName", direction: "upstream"})
```

3. Confirm the returned impact result matches the file-qualified context before treating it as authoritative.
4. Review all `d=1` callers first.
5. Record one disposition per `d=1` caller:
   - `updated`
   - `validated unaffected`
   - `deferred with risk note`

Ignore GitNexus hits that only land in `staging/imported_*/`, generated artifact paths, or docs unless the work is explicitly a staging-only review.

## Commit Sequence

1. `runtime commit`
   - source, tests, and minimal docs only
   - no `staging/`
   - no generated artifact refresh
   - GitNexus runtime review completed before commit
2. `artifact refresh commit`
   - generated outputs and reports only
   - no active source edits
   - no `staging/`
3. `staging/import commit`
   - staged donor content, migration notes, or consolidation bookkeeping only
   - no active runtime edits
   - no generated runtime evidence refresh

Use the same sequence for consolidation work: extract or refactor active code first, update donor snapshots second, and refresh generated evidence separately.

## Review Checklist

- [ ] changed paths land in one primary bucket
- [ ] `python scripts/check_change_scope.py --staged` was run before commit preparation
- [ ] every changed active-runtime symbol was reviewed with file-qualified GitNexus `context` and `impact`
- [ ] every `d=1` caller has a disposition: `updated`, `validated unaffected`, or `deferred with risk note`
- [ ] runtime validation passed before any artifact-refresh follow-up commit
- [ ] artifact-refresh commits contain no active runtime source edits
- [ ] staging/import commits contain no active runtime edits
