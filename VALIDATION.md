# Validation

## Primary check

```bash
python qdp_validation.py
```

## Additional review

- run `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml` when deterministic phase-1 validation/reporting surfaces change,
- run `tdgl-rf validate-seeded-vortices validation/seeded_vortex_phase2_2_manifest.yaml` when seeded-vortex initialization, placement semantics, rejection taxonomy, Tier-2 diagnostics, or the seeded experiment-pack contract changes,
- run `tdgl-rf run-experiment validation/seeded_vortex_phase2_3_experiment_pack.yaml` or the targeted experiment-sweep test slice when the deterministic seeded experiment harness, sweep expansion, repetition handling, aggregation surface, or experiment provenance contract changes,
- run the targeted Phase-2.4A experiment-sweep / CLI tests when the stochastic runtime contract, ensemble manifest dispatch, fail-closed staging/promotion/aggregation behavior, or replay/provenance contract changes,
- run `tdgl-rf evidence-bundle <validation_dir>` when proposal-facing evidence packaging changes or reviewer-facing bundle contents change,
- consult `docs/PHASE1_ACCEPTANCE.md`, `docs/PHASE1_VALIDATION_CAMPAIGN.md`, and `docs/PHASE1_VALIDATION_MEMO.md` before expanding the accepted deterministic scope,
- consult `docs/PHASE2_ENTRY_CRITERIA.md`, `docs/PHASE2_OPTIONS_MEMO.md`, and `docs/PHASE2_SEEDED_VORTICES.md` before widening the seeded-vortex surface or authorizing a different phase-2 feature class,
- treat `validation/thresholds.yaml` and `validation/reference_manifest.yaml` as the committed validation contract for the deterministic baseline,
- treat `validation/seeded_vortex_phase2_2_manifest.yaml` as the committed seeded experiment-pack contract for deterministic same-stack initialization-only, short-horizon, and rejection-taxonomy checks,
- treat Phase-2.3 experiment packs as deterministic same-stack sweep/repetition harnesses over committed Tier-2 observables, not as broader seeded-vortex validation artifacts,
- treat Phase-2.4A v4 manifests as runtime-capable but scientifically unvalidated; current enforcement covers explicit noise opt-in, sequential fail-fast execution, staged promotion, strict full-member aggregation, and replay/provenance integrity only,
- there are currently no grounded scientific guardrails for `noise.strength` beyond the explicit runtime config contract `noise.enabled=true`, `noise.seed`, and `noise.strength > 0`,
- treat `validation/seeded_vortex_reference_manifest.yaml` as the legacy Phase-2.1 compatibility manifest only,
- treat `configs/tdgl_run_provenance.schema.json` as the replay-metadata contract for seeded deterministic and Phase-2.4A ensemble-member runs,
- treat `configs/seeded_vortex_tier2.schema.json` and `configs/seeded_vortex_rejection.schema.json` as the Tier-2 and rejection-payload contracts for the seeded experiment pack,
- confirm `STATUS.md`, `PROMOTION_NOTES.md`, and `REPO_MAP.md` still match the repo layout,
- confirm new generated outputs do not become implicit source-of-truth documents,
- confirm any ALL-MIND integration note still points to a narrow interface, not whole-repo ingestion.
