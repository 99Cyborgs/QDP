# E01 MM Analysis Input Schema

## Purpose

This schema defines the normalized JSON input accepted by `analysis/e01_mm_analysis_runner.py`.
It is analysis-ready input only.
It does not accept raw DAQ exports or arbitrary lab-native files.

## Top-Level Object

```json
{
  "analysis_schema_version": "1.0.0",
  "branch_slug": "e01_mm_flux_history_hysteresis",
  "primary_device_id": "device_a",
  "matched_geometry_device_ids": ["device_a", "device_b"],
  "records": [],
  "dwell_metadata": []
}
```

## Required Fields

- `analysis_schema_version`: string, currently `1.0.0`
- `records`: array of normalized point records

## Optional Fields

- `branch_slug`: string
- `primary_device_id`: string
- `matched_geometry_device_ids`: array of device ids used for the H2 geometry gate
- `dwell_metadata`: array of cooldown-level dwell checks used by the rule-based H3 screen

## Record Schema

Each record must be a JSON object with:

- `cooldown_id`
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
- `bath_temperature`
- `readout_power`

The following fields are optional:

- `T1`
- `witness_response`

## Branch Semantics

- `up`: production up-branch data
- `down`: production down-branch data
- `sham`: sham timing control data
- `checkpoint`: return-to-zero checkpoint data
- any other branch label is accepted but will only be used when the runner has an explicit rule for it

## Dwell Metadata Schema

Each dwell metadata item may contain:

- `cooldown_id`
- `converged`
- `production_dwell_t_conv`
- `doubled_loop_change_fraction`
- `notes`

`doubled_loop_change_fraction > 0.05` is treated as non-converged for the v1 rule-based H3 screen.
