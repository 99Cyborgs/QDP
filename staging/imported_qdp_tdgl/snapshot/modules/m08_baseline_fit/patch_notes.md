# QDP v10.6 M08 Patch Notes

## Scope

This patch adds a visible-source executable subset for M08: baseline GKSL fit
and drift-aware residual diagnostics.

## Added artifacts

- `modules/m08_baseline_fit/runner.py`
- `modules/m08_baseline_fit/selftest_cases.json`
- `artifacts/reports/m08/selftest_report.json`
- `QDP_v10_6_M08_SELFTEST_OUTPUTS/`

## Implementation notes

- The runner uses only surfaced guidance from `specs/core/model_spec.md` and
  `specs/research/deep_research_report.md`.
- It populates `baseline_model.*` and `residual_analysis.*` in the existing
  schema and aligns those fields with the inputs already consumed by M05.
- It records joint-fit use, hierarchical drift handling, and conservative
  residual adequacy signals such as whiteness, stationarity, and structured
  residual features.

## Limitations

- This is a visible-source working patch, not authoritative runtime closure.
- The baseline-fit logic is a conservative diagnostic mapper, not a full
  quantitative Lindblad solver or inference engine.
- A passing M08 self-test report should not be treated as authorization to
  resume ordinary or subsystem testing.
