# QDP

QDP is an active quantum domain-program repository on the ALL-MIND incubate path.

It stays outside the core operating surface by default, but it is strategically near-core and already referenced by ALL-MIND as a governed downstream program.

## Read order

1. `AGENTS.md`
2. `SYSTEM_BOUNDARY.md`
3. `STATUS.md`
4. `REPO_MAP.md`
5. `ARCHITECTURE_SUMMARY.md`
6. `VALIDATION.md`
7. `PROMOTION_NOTES.md`
8. `INTEGRATION_PLAN.md`

## Current posture

- class: `incubate`
- suggested promotion mode: `incubation link`
- integration rule: ALL-MIND consumes compact status and interface artifacts only

## Human review entrypoint

- `specs/research/vortex_flagship_internal_research_proposal.md`: governed internal research proposal for the flagship vortex branch. This is the source-truth human review layer above the current `M12` vortex synthesis candidate and the drafted vortex lab request pack.

## Canonical validation

Use the Windows-safe repo validation runner:

```bash
python scripts/run_repo_validation.py
```

Add `--require-authoritative-ready` only when the task requires a true staging gate rather than structural consistency.
The frozen first-corridor gate now expects that flag to pass.

## Frozen ALL-MIND interface

The first downstream control-plane contract is:

- `artifacts/reports/system/all_mind_interface.json`
- `config/schema/all_mind_interface_schema.json`

It is emitted by the canonical validation flow and described in `INTEGRATION_PLAN.md`.
`ALL-MIND` must not treat `structural_consistency_passed` as proof of authoritative readiness.
Validate the frozen contract with `python qdp.py validate artifacts/reports/system/all_mind_interface.json --kind all-mind-interface`.

## Main repo concern

The repo contains meaningful runtime and scientific content, but the source-versus-generated boundary is still too noisy for core promotion. Governance exists here to reduce that audit cost without absorbing the whole repo.

## Simulation partitioning

Partitioned simulation batches stay inside generated artifact space.

- Use `python qdp.py module run ... --batch <batch> --variant <variant>` to derive candidate/report output paths under `artifacts/outputs/simulations/` and `artifacts/reports/simulations/`.
- Use `python qdp.py check --batch <batch>`, then `python qdp.py campaign prepare --batch <batch>`, and then `python qdp.py campaign plan --batch <batch>` to validate, materialize prepared `M12` candidates, and rank only that batch.
- Prepared campaign-facing `M12` candidates live under `artifacts/outputs/simulations/<batch>/m12/`, with active campaign reports under `artifacts/reports/campaigns/` or the batch-scoped simulation report namespace.
- Keep `candidate_id` unique for materially different variants, use `branch_or_model_tag` for model labeling, and keep sweep knobs in `simulation_conditions` and `tested_parameter_ranges`.
- Treat batch names as operator-defined namespaces, not as readiness lanes or source-of-truth identifiers.

## Local execution queue

QDP now exposes a repo-local execution queue for low-touch workflow automation.

- Use `python qdp.py queue enqueue --manifest <path>` to validate and enqueue manifest-defined workflow jobs.
- Use `python qdp.py queue run --once` for one eligible job or `python qdp.py queue run --daemon` for a local worker loop.
- Use `python qdp.py queue list [--state ... --job-type ... --reason-code ...]` to filter queue state for triage.
- Use `python qdp.py queue show <queue_id>` to inspect payload, dependency, failure history, manual actions, lease state, and artifact verification.
- Use `python qdp.py queue log <queue_id>` to inspect the per-item chronological audit log before `retry`, `unblock --force`, or `cancel`.
- Queue state stays under `artifacts/state/` and `artifacts/reports/system/queue_report.json`; it is repo-local operator state, not part of the frozen ALL-MIND contract.
