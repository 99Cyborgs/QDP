# Integration Plan

## Portfolio posture

QDP remains an `incubate` repo. It is the first downstream staging consumer, but it is not part of the `ALL-MIND` core surface.

## Allowed ALL-MIND consumption

`ALL-MIND` may consume only:

- `artifacts/reports/system/all_mind_interface.json`
- compact status language in `STATUS.md`
- promotion posture in `PROMOTION_NOTES.md`

`ALL-MIND` must not consume raw module outputs, bootstrap fixtures, or generated scientific artifacts as control-plane inputs.

## Frozen first-corridor contract

The first downstream contract is `artifacts/reports/system/all_mind_interface.json`.

Schema contract:

- `config/schema/all_mind_interface_schema.json`

Current producer:

- `python qdp_validation.py`

Current validator:

- `python qdp.py validate artifacts/reports/system/all_mind_interface.json --kind all-mind-interface`

Current consumer expectations:

- `repo_class`, `activity`, and `promotion_mode` describe repo posture
- `readiness` distinguishes recovery readiness from authoritative readiness
- `blockers` names the module sets still blocking each readiness lane
- `module_readiness_summary` and `module_closure_limitations` provide bounded operator context
- `promotion_posture` and `callable_surfaces` provide the only allowed control-plane affordances

## Explicit non-contract surfaces

The following remain repo-local only:

- `artifacts/outputs/**`
- `artifacts/reports/m*/**`
- `artifacts/reports/s*/**`
- retained runtime and scientific source materials under `runtime/**`
- raw selftest and bootstrap corpora

## Readiness rule

`structural_consistency_passed` is not equivalent to authoritative readiness.

The control plane must treat:

- `ordinary_authoritative_ready`
- `subsystem_authoritative_ready`

as the only authoritative staging gates.
