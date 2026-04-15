# Autonomous Execution Roadmap

Date: `2026-04-15`

## Objective

Complete and validate the active TDGL-RF hardening slice visible in the current repo state:

- make deterministic phase-1 validation outputs self-describing through explicit surface metadata carried by the threshold contracts,
- keep evidence-bundle outputs aligned with those surface boundaries so short-horizon versus longer-horizon deterministic claims stay explicit,
- land and validate the committed `n_steps=8` longer-horizon deterministic tranche as an informative but non-baseline surface,
- land and validate the committed Phase-2.4A stochastic runtime smoke manifest as a runtime/provenance control-plane surface only.

## Authority Order

1. `AGENTS.md`
2. `README.md`
3. `SYSTEM_BOUNDARY.md`
4. `STATUS.md`
5. `REPO_MAP.md`
6. `VALIDATION.md`
7. `QDP_REPO_REFACTOR_PLAN.md`

## Current State Assessment

Confirmed from the current checkout:

- `src/tdgl_rf/workflows/validation.py` already parses an optional `surface` section from threshold specs and threads it into `validation_summary.json` and `validation_report.md`.
- `src/tdgl_rf/workflows/evidence.py` already consumes surface metadata, with a fallback for legacy validation payloads that do not carry it.
- `validation/thresholds.yaml` now defines the accepted short-horizon deterministic surface explicitly.
- Untracked assets define a committed longer-horizon deterministic tranche:
  `validation/thresholds_long_horizon.yaml`,
  `validation/reference_manifest_long_horizon.yaml`,
  `matrices/phase1_validation_matrix_v2_long_horizon.csv`,
  `configs/phase1_refinement_sanity_long_horizon.yaml`,
  and companion long-horizon reference configs.
- Untracked assets also define a committed Phase-2.4A runtime-smoke surface:
  `validation/seeded_vortex_phase2_4a_runtime_smoke.yaml`,
  `configs/validation/seeded_vortex/short_horizon/stochastic_single_positive.yaml`,
  and `.agents/skills/qdp-phase2-4a-runtime-smoke/`.
- Focused contract tests already pass for the touched surfaces.

## Target State

- The short-horizon phase-1 validation surface remains the accepted deterministic baseline.
- The longer-horizon `n_steps=8` tranche is committed, reproducible, and explicitly documented as informative only while refinement remains flagged.
- Evidence bundles generated from either validation tranche reproduce the correct claim scope, accepted use, and non-claim limits.
- The committed Phase-2.4A runtime-smoke manifest executes end to end, writes expected aggregate and per-member artifacts, and remains explicitly non-scientific.
- Docs, status, promotion notes, skills, tests, and live commands all agree on those boundaries.

## Constraints And Assumptions

- Do not widen public claim boundaries beyond what existing docs and thresholds justify.
- Do not treat generated run outputs as governing truth.
- Prefer the smallest sufficient validation first, then live workflow confirmation.
- Preserve existing CLI surfaces; modify semantics only where the current diff already establishes the intended contract.
- Treat the current dirty worktree as in-flight repo state to complete carefully, not to overwrite.

## Workstreams

1. Contract synchronization
   Update or confirm threshold/manifest semantics, workflow behavior, tests, and boundary docs for phase-surface metadata.
2. Longer-horizon deterministic tranche
   Validate the new assets and make sure their interpretation stays explicitly informative rather than accepted.
3. Evidence-bundle hardening
   Prove that evidence outputs preserve the surface-specific claim language.
4. Phase-2.4A runtime-smoke hardening
   Execute the committed smoke manifest and confirm fail-closed aggregate/provenance artifacts.
5. Final consistency pass
   Re-run the focused pytest slice, reconcile docs, and summarize residual risks.

## Dependency Order

1. Confirm doc and contract coherence.
2. Run focused pytest slice for validation/evidence/experiment-sweep surfaces.
3. Run live longer-horizon `validate-phase1`.
4. Run `tdgl-rf evidence-bundle` against that live validation directory.
5. Run live Phase-2.4A runtime smoke.
6. Patch any discovered inconsistencies.
7. Re-run targeted validation.

## Risk Register

| Risk | Impact | Containment |
| --- | --- | --- |
| Longer-horizon tranche is misread as accepted baseline | Overstated deterministic claims | Keep `STATUS.md`, `VALIDATION.md`, thresholds metadata, and evidence output aligned on informative-only posture |
| Evidence bundle falls back to legacy wording | Review artifacts blur claim scope | Exercise `tdgl-rf evidence-bundle` on a live validation run and inspect generated markdown |
| Runtime-smoke execution is mistaken for stochastic validation | Invalid scientific interpretation | Keep runtime-only language explicit in docs, skill, and final summary |
| Dirty worktree contains overlapping in-flight changes | Accidental overwrite or regression | Avoid reverting unrelated edits; patch only when a concrete gap is observed |

## Validation Strategy

Smallest sufficient checks first:

1. `python -m pytest tests/unit/test_validation.py tests/unit/test_evidence.py tests/integration/test_validation_workflows.py tests/integration/test_experiment_sweep_workflows.py`
2. `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v2_long_horizon.csv validation/thresholds_long_horizon.yaml validation/reference_manifest_long_horizon.yaml configs/phase1_refinement_sanity_long_horizon.yaml`
3. `tdgl-rf evidence-bundle <validation_dir>`
4. `tdgl-rf run-experiment validation/seeded_vortex_phase2_4a_runtime_smoke.yaml`

## Rollback / Containment

- Keep contract changes narrow and local to existing phase-1 validation/evidence and runtime-smoke surfaces.
- If live validation exposes a regression, revert or narrow only the specific touched contract/doc surface rather than broad refactors.
- If runtime smoke fails, leave the deterministic validation/evidence work intact and document the stochastic runtime residual separately.

## Done Criteria

- Roadmap captured in repo.
- Focused tests pass.
- Live longer-horizon validation completes and its status is inspected.
- Live evidence bundle is generated from that validation output.
- Live Phase-2.4A runtime smoke completes and expected artifacts are inspected.
- Any discovered gaps are fixed and revalidated.
- Final docs/status summary remains internally consistent and explicit about residual limits.
