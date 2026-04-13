# MMM Analysis Pipeline Specification

## Pipeline stages
| Stage | Action | Output |
| --- | --- | --- |
| A0 | Ingest raw data, calibration data, metrology data, and package metadata. | versioned dataset manifest |
| A1 | Apply calibration and de-embedding. | calibrated observables and S-parameters |
| A2 | Extract primary observables with uncertainty models. | T1/T2/parity/recovery/witness metrics |
| A3 | Fit baseline null models and candidate mechanism models. | model posteriors / information criteria |
| A4 | Run scaling tests and geometry metrology alignment. | scaling residuals and pass/fail status |
| A5 | Run hierarchical replication model across cooldowns, devices, and batches. | replication effect estimate |
| A6 | Emit validation report and branch disposition. | promote / hold / reject recommendation |

## Statistical rules
- Use held-out likelihood or delta_BIC >= 10 as decisive model-separation threshold.
- Carry metrology uncertainty into model inputs for geometry-sensitive branches.
- Use random-effects hierarchical models for cooldown, batch, and device variability.
- Never claim structured-bath behavior from fit residuals alone; require explicit non-Markovian model advantage.

## Required outputs
- calibrated_observables.parquet or equivalent
- model_comparison_summary.yaml
- scaling_report.yaml
- replication_report.yaml
- validation_gate_report.md

## Validation rules
The authoritative rule set is `mmm_validation_rules.yaml`.
