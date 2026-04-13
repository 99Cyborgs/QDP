# E01 MM First Cooldown Execution Sheet

## Control References

- Governing laboratory procedure: `protocols/e01_mm_measurement_protocol.md`
- Governing analysis gates: `analysis/e01_mm_analysis_protocol.md`
- Governing classification limits: `specs/e01_mm_branch_spec.md`

This sheet instantiates the first cooldown only.
Do not reinterpret the branch from this sheet.
If this sheet conflicts with the governing artifacts above, the governing artifacts control.

## Binding Modes

| Key | Allowed values | Meaning |
| --- | --- | --- |
| `binding_context` | `PRE_RUN_MINIMUM_ACQUISITION`; `AS_RUN_BINDING` | Minimum acquisition planning before cooldown, or binding a completed cooldown from as-run records |
| `binding_status` | `TEMPLATE_UNBOUND`; `PRE_RUN_MINIMUM_READY`; `AS_RUN_PARTIAL`; `AS_RUN_BOUND` | Template only, minimum acquisition plan complete, partial as-run binding, or full as-run binding |

## Binding Source Hierarchy

| Field group | Source of truth | Binding rule |
| --- | --- | --- |
| run identity | `as-run logbook`; `fridge log` | Bind `cooldown_id`, `operator`, `run_date`, and `lab_location` only from these records |
| hardware binding | `fridge log`; `sample map`; `channel map` | Bind `target_device_ids`, `witness_channel_id`, and `matched_geometry_device_ids` only from these records |
| thermal and readout state | `DAQ record`; `calibration record` | Bind `T_base` at stabilized measurement start and bind `P_read` only when device-calibrated |
| field-history program | `first actual loop` | Bind `B_max`, `fc_field`, `field_steps`, `selected_fields`, and dwell probe fields from the first loop actually run |
| output paths | existing as-run files or directories only | Do not bind output paths until the files or directories exist |

## Run Header

| Field | Value |
| --- | --- |
| `branch_tag` | `E01_MM_FLUX_HISTORY_HYSTERESIS` |
| `branch_slug` | `e01_mm_flux_history_hysteresis` |
| `binding_context` | `PRE_RUN_MINIMUM_ACQUISITION` |
| `binding_status` | `TEMPLATE_UNBOUND` |
| `cooldown_id` | `UNBOUND` |
| `operator` | `TBD` |
| `run_date` | `TBD` |
| `lab_location` | `TBD` |
| `run_readiness` | `NOT_READY` |

## Staged Workflow

1. `PRE_RUN_MINIMUM_ACQUISITION`
   Bind the smallest defensible first acquisition and verify the pre-run checks.
   Promote only to `PRE_RUN_MINIMUM_READY`.
2. cooldown execution
   Run strictly under `protocols/e01_mm_measurement_protocol.md`.
   Capture as-run identity, stabilized fixed settings, actual first-loop field history, and real output paths as they become available.
3. `AS_RUN_BINDING`
   Switch the same record to `AS_RUN_BINDING`.
   Use `AS_RUN_PARTIAL` until all as-run provenance and binding checks are complete.
   Promote to `AS_RUN_BOUND` only when all required checks are `true`.

## Context-Specific Completion Rules

### PRE_RUN_MINIMUM_ACQUISITION

Mark `binding_status = PRE_RUN_MINIMUM_READY` only when all of the following are true:

- `target_device_ids` is not empty.
- `witness_channel_id` is identified.
- `matched_geometry_device_ids` is either explicitly bound or explicitly set to `[]`.
- A true `ZFC` condition is retained.
- At least one nonzero `FC` condition is defined.
- A symmetric up/down loop to `+/- B_max` is specified.
- `field_steps` is defined.
- `selected_fields` is a subset of `field_steps`.
- The selected fields include zero field, a suspected onset region, and one high-field point.
- `probe_fields` and `dwell_times` have equal length.
- The dwell probe fields include zero field, a suspected onset region, and one high-field point.

In this mode, as-run output paths may remain unbound.
Do not claim `AS_RUN_PARTIAL` or `AS_RUN_BOUND` from planned values alone.
Set the binding checks as follows:

- `selected_fields_subset_of_field_steps = true` only after the subset relation is verified.
- `probe_schedule_lengths_match = true` only after equal probe and dwell lengths are verified.
- `field_unit_consistent = true` only after every field quantity uses the same unit.
- `p_read_device_calibrated = false` until a device-calibrated `P_read` exists from the run.
- `output_paths_exist = false` until real as-run files or directories exist.

### cooldown execution

During the first actual cooldown:

- capture run identity from the as-run logbook and fridge log,
- capture stabilized `T_base` and device-calibrated `P_read` from DAQ plus calibration,
- capture actual `B_max`, `fc_field`, `field_steps`, `selected_fields`, and dwell probe schedule from the first actual loop,
- do not bind output paths until the files or directories exist.

### AS_RUN_BINDING

Use `binding_status = AS_RUN_PARTIAL` when run identity, hardware, fixed settings, and field program are bound from the correct sources but one or more of the following remain unresolved:

- output paths do not yet exist,
- `p_read_device_calibrated = false`,
- `field_unit_consistent = false`,
- `selected_fields_subset_of_field_steps = false`,
- `probe_schedule_lengths_match = false`.

Mark `binding_status = AS_RUN_BOUND` only when all of the following are true:

- Run identity is bound from the as-run logbook and fridge log.
- Hardware identifiers are bound from the fridge log, sample map, and channel map.
- `T_base` is the stabilized base temperature at measurement start.
- `P_read` is the calibrated at-device readout power and `p_read_device_calibrated = true`.
- `readout_tone_id`, `attenuation_state`, and `readout_chain_config` are the exact identifiers used in the acquisition block.
- `B_max`, `fc_field`, `field_steps`, `selected_fields`, and dwell probe fields are bound from the first actual loop.
- `field_unit` is explicit and consistent across all field values.
- Output paths point to real as-run files or directories and `output_paths_exist = true`.
- All binding checks in the JSON are `true`.

## Hard Binding Rules

- Set `matched_geometry_device_ids = []` when no same-chip matched-geometry comparison devices exist.
- Do not bind `P_read` unless it is device-calibrated.
- Do not bind output paths until the files or directories actually exist.
- Require `selected_fields` to satisfy `selected_fields subset of field_steps`.
- Require `len(probe_fields) == len(dwell_times)`.
- Use one field unit consistently for `B_max`, `fc_field`, `field_steps`, and `probe_fields`.
- Keep H2 ineligible for this run whenever `matched_geometry_device_ids = []`.

## Hardware Binding

| Binding item | Value |
| --- | --- |
| `target_device_ids` | `UNBOUND` |
| `witness_channel_id` | `UNBOUND` |
| `matched_geometry_device_ids` | `UNBOUND OR []` |
| `H2 run eligibility` | INELIGIBLE UNTIL SAME-CHIP MATCHED GEOMETRY IS BOUND |

Operator action:
Fill the JSON template first.
Mirror the resolved hardware identifiers here without changing names or device count.

## Fixed Settings

| Setting | Value |
| --- | --- |
| `T_base` | `UNBOUND` |
| `P_read` | `UNBOUND` |
| `readout_tone_id` | `UNBOUND` |
| `attenuation_state` | `UNBOUND` |
| `readout_chain_config` | `UNBOUND` |

Binding rule:
`P_read` must be the calibrated at-device readout power, not the room-temperature generator setpoint.

## Field-History Program

| Item | Value |
| --- | --- |
| `field_unit` | `UNBOUND` |
| `B_max` | `UNBOUND` |
| `fc_field` | `UNBOUND` |
| `field_steps` | `UNBOUND` |
| `selected_fields` | `UNBOUND` |

Binding rule:
`fc_field` records the field present during cooldown for the FC leg.
Use `0` only for a true ZFC-only run.
Keep the required true ZFC condition as a separate leg of the discriminator plan.

## Dwell Probe Schedule

| Item | Value |
| --- | --- |
| `probe_fields` | `UNBOUND` |
| `dwell_times` | `UNBOUND` |
| `dwell_time_unit` | `UNBOUND` |
| convergence criterion source | `protocols/e01_mm_measurement_protocol.md step 5` |
| production dwell `t_conv` | `TBD AFTER CALIBRATION` |

Binding rule:
`probe_fields` and `dwell_times` must have equal length.
Use explicit time units.

## Dual-Mode Minimum Acquisition Requirements

For `PRE_RUN_MINIMUM_ACQUISITION`, the smallest defensible first acquisition is:

- one true `ZFC` condition,
- at least one nonzero `FC` condition,
- a symmetric up/down loop to `+/- B_max`,
- dwell traces at zero field,
- dwell traces in a suspected onset region,
- dwell traces at one high-field point.

This minimum plan matches the branch discriminator logic.

## Sham Timing And Return-To-Zero

| Item | Value |
| --- | --- |
| sham required | `YES` |
| sham command mode | `UNBOUND` |
| cadence match | `MUST MATCH REAL LOOP` |
| sequence length | `MUST MATCH REAL LOOP` |
| return-to-zero checkpoints | `REQUIRED AFTER HALF-LOOP AND FULL LOOP` |

Gate:
If sham timing is omitted, the run is non-discriminating.

## Witness Acquisition

| Item | Value |
| --- | --- |
| witness channel bound | `UNBOUND` |
| simultaneous multiplexing | `TBD` |
| interleaved fallback allowed | `YES, WITH TIMESTAMP ALIGNMENT` |

Gate:
If witness binding is missing, stop before acquisition and log the run as non-discriminating.

## Selected-Field T1

| Item | Value |
| --- | --- |
| zero-field `T1` | `REQUIRED` |
| selected field just above `B_on` | `UNBOUND UNTIL B_on IS DETERMINED` |
| higher selected field | `UNBOUND` |

Operator action:
`T1` remains secondary.
Do not let selected-field `T1` override the primary `1/Qi` history observable.

## Dataset Capture

Record the dataset fields required by `protocols/e01_mm_measurement_protocol.md` step 13.

| Capture item | Value |
| --- | --- |
| raw data output path | `TBD` |
| metadata output path | `TBD` |
| witness trace path | `TBD` |
| operator notes path | `TBD` |

Binding rule:
Use real as-run directories or files only.
Do not bind the three output paths above until they exist.

## Stop Conditions

- Dwell convergence fails.
- Sham timing control is missing.
- Witness channel is missing.
- `T_base` or `P_read` drifts outside tolerance.
- Field calibration or zero-return checkpoints cannot be trusted.

If any stop condition triggers, annotate the run as `NON_DISCRIMINATING` and do not escalate interpretation.

## Completion Order

1. Set the `binding_context`.
2. Fill the machine-readable JSON template for `PRE_RUN_MINIMUM_ACQUISITION`.
3. Verify the pre-run `binding_checks` and promote to `PRE_RUN_MINIMUM_READY` only when the minimum acquisition is complete.
4. Execute the cooldown under `protocols/e01_mm_measurement_protocol.md`.
5. Switch the same record to `AS_RUN_BINDING` and use `AS_RUN_PARTIAL` until all as-run provenance and checks are complete.
6. Promote to `AS_RUN_BOUND` only when all required binding checks are `true`.
7. Mirror the resolved values into this sheet.
8. Do not change branch classification, falsifier logic, or analysis order while binding the run.
