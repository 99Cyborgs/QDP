# QDP v10.6 M07 Patch Notes

## Scope

This patch adds a visible-source executable subset for M07: family-class triage
and signature-to-bath scoring.

## Added artifacts

- `modules/m07_family_triage/runner.py`
- `modules/m07_family_triage/selftest_cases.json`
- `artifacts/reports/m07/selftest_report.json`
- `QDP_v10_6_M07_SELFTEST_OUTPUTS/`

## Implementation notes

- The scorer uses only surfaced mappings from `specs/core/bath_glossary.md` and
  `specs/core/signature_to_bath_decision_chart.md`.
- It fills the existing schema fields:
  `assigned_family_class`, `family_class_mismatch`,
  `inferred_bath_rank_order`, `signature_matches`,
  `minimal_discriminant_measurement`, and
  `mechanism_scores_after_signature`.
- It defaults conservatively to `scientific_decision=NOT_EVALUATED` and
  `governance_outcome=DEFER`. M07 is triage only; it does not decide later
  validation gates.
- When no surfaced signature is present, the scorer falls back to the declared
  family or bath class instead of inventing stronger evidence.

## Limitations

- This is a working-patch visible-source implementation, not a no-loss proof of
  parity with any unsurfaced retained runtime behavior.
- Signature matching is keyword-based and intentionally conservative.
- A passing M07 self-test report should not be treated as permission to resume
  ordinary or subsystem testing.
