# E01 MM Measurement Evidence Schema

## Purpose

This schema defines the structured measurement-evidence file consumed by
`analysis/e01_mm_analysis_input_builder.py`.
It is the authoritative bridge format between bound as-run outputs and the
normalized analysis input accepted by `analysis/e01_mm_analysis_runner.py`.

## Format

- Preferred format: `.json`
- Also accepted: markdown frontmatter using the same parser conventions already
  used in the execution queue and reconciliation layer
- Raw DAQ exports, CSV files, and opaque binary dumps are out of scope for this
  slice and must be normalized before ingestion

## Top-Level Object

```json
{
  "measurement_evidence_schema_version": "1.0.0",
  "records": [],
  "dwell_metadata": []
}
```

## Required Fields

- `records`: array of measurement point records

## Optional Fields

- `measurement_evidence_schema_version`: if present, must be `1.0.0`
- `dwell_metadata`: cooldown-level dwell convergence metadata

## Record Contract

Each record must include:

- `device_id`
- `geometry_id`
- `history_label`
- `branch`
- `commanded_field`
- `calibrated_field`
- `elapsed_time`
- `dwell_duration`
- `inv_qi`
- `fr`
- `delta_fr_over_fr`

The builder will also require `cooldown_id`, `bath_temperature`, and
`readout_power`, but may fill those from the authoritative run-binding when they
are uniquely bound there.

Optional record fields:

- `T1`
- `witness_response`

## Dwell Metadata Contract

Each dwell metadata entry may contain:

- `cooldown_id`
- `converged`
- `production_dwell_t_conv`
- `doubled_loop_change_fraction`
- `notes`

If `dwell_metadata` is absent, the builder emits an empty array unless
`production_dwell_t_conv` is bound in the run-binding, in which case it emits a
single conservative cooldown-level entry with that value.
