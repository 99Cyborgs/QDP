# Validation

## Primary check

```bash
python qdp_validation.py
```

## Additional review

- run `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml` when deterministic phase-1 validation/reporting surfaces change,
- consult `docs/PHASE1_ACCEPTANCE.md`, `docs/PHASE1_VALIDATION_CAMPAIGN.md`, and `docs/PHASE1_VALIDATION_MEMO.md` before expanding the accepted deterministic scope,
- treat `validation/thresholds.yaml` and `validation/reference_manifest.yaml` as the committed validation contract for the deterministic baseline,
- confirm `STATUS.md`, `PROMOTION_NOTES.md`, and `REPO_MAP.md` still match the repo layout,
- confirm new generated outputs do not become implicit source-of-truth documents,
- confirm any ALL-MIND integration note still points to a narrow interface, not whole-repo ingestion.
