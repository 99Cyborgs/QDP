# Candidate Report: GEN-001

## Positioning

- Structure: `STR-EM-CPW-EBG-RING` (CPW electromagnetic bandgap ring)
- Screening status: `prioritized`
- Scoring profile: `manufacturability_aware`
- Score backend: `baseline_surrogate_v1`
- Total surrogate score: `0.779`
- Decision band: `lead_branch`
- Reject reason: `none`

## Candidate Metadata

- Topology: 1D CPW corrugation ring
- Material system: Al on high-resistivity Si
- Fabrication complexity: 3/10
- Null risk: 4/10
- Notes: Baseline planar EM candidate centered on fixed-frequency transmon band.

## Score Components

| Feature | Value | Weight | Weighted |
| --- | --- | --- | --- |
| coherence_uplift | 0.730 | 0.205 | 0.149 |
| null_separation | 0.667 | 0.171 | 0.114 |
| detectability_margin | 0.911 | 0.142 | 0.130 |
| geometry_scaling_clarity | 0.883 | 0.139 | 0.123 |
| fabrication_robustness | 0.778 | 0.154 | 0.119 |
| replication_portability | 0.650 | 0.091 | 0.059 |
| simulation_confidence | 0.750 | 0.047 | 0.036 |
| standard_lab_feasibility | 0.950 | 0.051 | 0.049 |

## Interpretation

- This report is generated from the baseline surrogate scoring pipeline.
- No full-wave electromagnetic, phononic, or measured RF result is implied by this ranking.
