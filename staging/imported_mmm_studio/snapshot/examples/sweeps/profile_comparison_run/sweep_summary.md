# Sweep Summary: profile-comparison

## Status

- Sweep ID: `profile_comparison_run`
- Successful slices: `3`
- Failed slices: `0`

## Highlights

- GEN-003 achieved the highest robustness score across 3 successful slices.
- GEN-002 had the tightest rank spread (0) among compared slices.
- GEN-003 showed the strongest profile sensitivity signal with score 0.656.

## Aggregate Leaderboard

| Rank | Genome | Structure | Robustness | Mean Rank | Sensitivity |
| --- | --- | --- | --- | --- | --- |
| 1 | GEN-003 | STR-EM-LID-HIS | 0.989 | 1.33 | 0.656 |
| 2 | GEN-001 | STR-EM-CPW-EBG-RING | 0.978 | 1.67 | 0.651 |
| 3 | GEN-002 | STR-EM-CPW-EBG-RING | 0.935 | 3.00 | 0.001 |
| 4 | GEN-005 | STR-PH-SOI-JJ-PHC | 0.881 | 4.67 | 0.179 |
| 5 | GEN-018 | STR-EM-LID-HIS | 0.831 | 4.67 | 0.267 |
| 6 | GEN-007 | STR-PH-SOI-FULLCAP-PHC | 0.738 | 6.00 | 0.243 |
| 7 | GEN-006 | STR-PH-SOI-JJ-PHC | 0.667 | 6.67 | 0.119 |
| 8 | GEN-009 | STR-PH-GRADED-SINK | 0.624 | 8.00 | 0.011 |
| 9 | GEN-010 | STR-PH-GRADED-SINK | 0.580 | 9.33 | 0.079 |
| 10 | GEN-016 | STR-HYB-BILAYER-INTERPOSER | 0.548 | 10.33 | 0.202 |

## Slice Winners

| Tranche | Slice | Profile | Winner | Score | Status |
| --- | --- | --- | --- | --- | --- |
| profile_comparison | broadband | broadband | GEN-003 | 0.783 | completed |
| profile_comparison | resonance_targeted | resonance_targeted | GEN-003 | 0.787 | completed |
| profile_comparison | manufacturability_aware | manufacturability_aware | GEN-001 | 0.779 | completed |

## Cross-Slice Comparisons

| Left Slice | Right Slice | Top-K Overlap | Jaccard | Same Winner |
| --- | --- | --- | --- | --- |
| broadband | manufacturability_aware | 5 | 1.000 | no |
| broadband | resonance_targeted | 4 | 0.667 | yes |
| manufacturability_aware | resonance_targeted | 4 | 0.667 | no |

## Metric Notes

- `robustness_score` is a software comparison metric that rewards repeatably strong rank positions across successful slices.
- `profile_sensitivity_score` is a software comparison metric that surfaces candidates whose relative standing changes sharply across slices.
- These metrics summarize surrogate-ranking behavior only and are not physics claims.
