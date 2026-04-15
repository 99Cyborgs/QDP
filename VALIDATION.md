# Validation

## Control Planes

- Legacy QDP governance / module surface:

```bash
python qdp.py check
```

- TDGL-RF surface:
  run the smallest matching `tdgl-rf` workflow below for the surface you changed.
  There is no single repo-wide TDGL validation command in the current checkout.
  Before live CLI validation, refresh the editable install from this checkout with `python -m pip install -e .[dev]` so `tdgl-rf` resolves to the current repo rather than a stale sibling install.

## Additional review

- run `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml` when the accepted short-horizon deterministic validation/reporting surface changes,
- run `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v2_long_horizon.csv validation/thresholds_long_horizon.yaml validation/reference_manifest_long_horizon.yaml configs/phase1_refinement_sanity_long_horizon.yaml` when the committed `n_steps=8` longer-horizon deterministic tranche changes,
- run `tdgl-rf validate-seeded-vortices validation/seeded_vortex_phase2_2_manifest.yaml` when seeded-vortex initialization, placement semantics, rejection taxonomy, Tier-2 diagnostics, or the seeded experiment-pack contract changes,
- run `tdgl-rf run-experiment validation/seeded_vortex_phase2_3_experiment_pack.yaml` or the targeted experiment-sweep test slice when the deterministic seeded experiment harness, sweep expansion, repetition handling, aggregation surface, or experiment provenance contract changes,
- run `tdgl-rf run-experiment validation/seeded_vortex_phase2_4a_runtime_smoke.yaml` plus the targeted Phase-2.4A experiment-sweep / CLI tests when the stochastic runtime contract, committed smoke manifest, ensemble manifest dispatch, fail-closed staging/promotion/aggregation behavior, or replay/provenance contract changes,
- run `tdgl-rf evidence-bundle <validation_dir>` when proposal-facing evidence packaging changes or reviewer-facing bundle contents change,
- consult `docs/PHASE1_ACCEPTANCE.md`, `docs/PHASE1_VALIDATION_CAMPAIGN.md`, and `docs/PHASE1_VALIDATION_MEMO.md` before expanding the accepted deterministic scope,
- consult `docs/PHASE2_ENTRY_CRITERIA.md`, `docs/PHASE2_OPTIONS_MEMO.md`, and `docs/PHASE2_SEEDED_VORTICES.md` before widening the seeded-vortex surface or authorizing a different phase-2 feature class,
- treat `validation/thresholds.yaml` and `validation/reference_manifest.yaml` as the accepted short-horizon deterministic validation contract,
- treat `validation/thresholds_long_horizon.yaml` and `validation/reference_manifest_long_horizon.yaml` as the committed `n_steps=8` longer-horizon deterministic tranche contract; as of `2026-04-13` it remains flagged at refinement `2/4`, so it does not widen the accepted baseline yet,
- treat `validation/seeded_vortex_phase2_2_manifest.yaml` as the committed seeded experiment-pack contract for deterministic same-stack initialization-only, short-horizon, and rejection-taxonomy checks,
- treat Phase-2.3 experiment packs as deterministic same-stack sweep/repetition harnesses over committed Tier-2 observables, not as broader seeded-vortex validation artifacts,
- treat Phase-2.4A v4 manifests as runtime-capable but scientifically unvalidated; current enforcement covers explicit noise opt-in, sequential fail-fast execution, staged promotion, strict full-member aggregation, and replay/provenance integrity only,
- there are currently no grounded scientific guardrails for `noise.strength` beyond the explicit runtime config contract `noise.enabled=true`, `noise.seed`, and `noise.strength > 0`,
- treat `validation/seeded_vortex_reference_manifest.yaml` as the legacy Phase-2.1 compatibility manifest only,
- treat `validation/seeded_vortex_phase2_4a_runtime_smoke.yaml` as the committed small Phase-2.4A runtime smoke manifest; it is a control-plane and provenance check, not a scientific validation artifact,
- treat `qdp_validation.py` as a legacy helper library in this checkout, not as the primary validation CLI,
- treat `configs/tdgl_run_provenance.schema.json` as the replay-metadata contract for seeded deterministic and Phase-2.4A ensemble-member runs,
- treat `configs/seeded_vortex_tier2.schema.json` and `configs/seeded_vortex_rejection.schema.json` as the Tier-2 and rejection-payload contracts for the seeded experiment pack,
- confirm `STATUS.md`, `PROMOTION_NOTES.md`, and `REPO_MAP.md` still match the repo layout,
- confirm new generated outputs do not become implicit source-of-truth documents,
- confirm any ALL-MIND integration note still points to a narrow interface, not whole-repo ingestion.
