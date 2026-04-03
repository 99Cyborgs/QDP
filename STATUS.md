# Status

- class: `incubate`
- activity: `active`
- last reviewed: `2026-04-03`
- owner: `forre`
- suggested promotion mode: `incubation link`

## Summary

QDP now has a validated deterministic phase-1 baseline with explicit thresholds, frozen references, same-stack reproducibility checks, and a compact evidence-bundle workflow for proposal and internal review use. The immediate next decision is a phase-2 gate decision, not broader phase-1 feature expansion.

## Current risks

- generated artifacts and source materials are still too interleaved,
- short-horizon deterministic evidence could be overread as broader solver validity if the scope limits are not kept explicit,
- phase-2 direction could be chosen before the deterministic control surface is extended or backend parity is clarified,
- core/candidate boundary could blur if ALL-MIND starts loading QDP wholesale.

## Next Decision Point

- Phase-2 gate definition: `docs/PHASE2_ENTRY_CRITERIA.md`
- Phase-2 option ranking: `docs/PHASE2_OPTIONS_MEMO.md`
- Reviewer-facing evidence packaging: `tdgl-rf evidence-bundle <validation_dir>`
