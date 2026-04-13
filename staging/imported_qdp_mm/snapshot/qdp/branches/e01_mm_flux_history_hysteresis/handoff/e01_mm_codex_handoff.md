# E01 MM Codex Handoff

## Current State

The branch pack is created under the fallback QDP layout.
Intake posture is `METASTABLE_C_STATE` only.
`VORTEX` remains a conditional promoted interpretation behind a same-chip matched-geometry gate.
The first-cooldown execution artifacts now support both `PRE_RUN_MINIMUM_ACQUISITION` and `AS_RUN_BINDING`.
The branch also includes a non-authoritative candidate packet generator for field and dwell sweeps only.
The branch now also includes a deterministic bridge from bound as-run evidence into normalized analysis input.

## Read Order

1. `specs/e01_mm_branch_spec.md`
2. `specs/e01_mm_exact_falsifier.md`
3. `protocols/e01_mm_measurement_protocol.md`
4. `protocols/e01_mm_first_cooldown_run_binding.json`
5. `protocols/e01_mm_first_cooldown_execution_sheet.md`
6. `execution_queue/e01_mm_execution_queue_spec.md`
7. `execution_queue/e01_mm_first_cooldown_queue_manifest.json`
8. `protocols/e01_mm_candidate_packet_sweep_generator.ps1`
9. `analysis/e01_mm_analysis_protocol.md`
10. `analysis/e01_mm_measurement_evidence_schema.md`
11. `analysis/e01_mm_analysis_input_schema.md`
12. `competition/e01_mm_mechanism_competition.md`
13. `failures/e01_mm_failure_mode_ledger.md`
14. `simulation/e01_mm_minimal_sim_plan.md`
15. `intake/e01_mm_fork_intake.json`
16. `intake/e01_mm_candidate_seed.json`

## Non-Negotiable Constraints

- Register as `METASTABLE_C_STATE` first.
- Keep phase 1 at fixed low temperature and fixed low drive.
- Do not add broad power or temperature sweeps.
- Do not discuss H2 before H0, H1, H3, and H4 are handled in the required order.
- Do not promote vortex interpretation without same-chip matched geometry and consistent ordering across the minimum three cooldowns.
- Do not ignore sham timing, dwell convergence, return-to-zero checkpoints, or package witness coverage.
- Do not mark `AS_RUN_BOUND` while witness binding, `P_read`, field units, or output-path existence checks remain unresolved.
- Do not treat an empty matched-geometry binding as H2-supporting evidence; it makes H2 ineligible for that run.
- Do not bind `P_read` from a room-temperature generator setpoint.
- Do not bind output paths until the as-run files or directories actually exist.
- Do not treat generator output as an authoritative run record before real hardware binding is merged.

## Open Conservative Fields

- `T_base`, `P_read`, `B_max`, field step list, and device identifiers are intentionally left for run-specific binding.
- The exact witness channel implementation is not bound because no hardware map exists in this repository.
- No cross-device status, proceed-level governance outcome, or microscopic closure claim has been set.
- `PRE_RUN_MINIMUM_ACQUISITION` may remain partially unbound on as-run-only fields; `AS_RUN_BINDING` may not.

## Next Worker Action

If the first cooldown has not happened yet, set `binding_context = PRE_RUN_MINIMUM_ACQUISITION` and bind the minimum ZFC, nonzero FC, symmetric `+/- B_max` loop, and zero/onset/high-field dwell plan.
If the field and dwell plan is not yet fixed, use `protocols/e01_mm_candidate_packet_sweep_generator.ps1` with an external sweep-spec JSON to enumerate candidate packets that remain `TEMPLATE_UNBOUND`.
Select one candidate outside the authoritative record, then merge real hardware bindings from the fridge log plus sample and channel maps before updating the authoritative JSON.
Promote only to `PRE_RUN_MINIMUM_READY` before hardware execution.
Create or refresh `execution_queue/e01_mm_first_cooldown_queue_manifest.json` from the authoritative run-binding JSON before handing the run to an unattended worker.
Let the queue advance automatically through `QUEUED`, `READY_FOR_PRECHECK`, and `READY_FOR_HARDWARE`, and use blocked or escalated reason codes instead of free-text worker status.
Use the reconciliation layer to populate source-owned run-binding fields from the declared logbook, fridge, map, DAQ, and calibration artifacts, and treat any source conflict as a structured stop rather than a silent overwrite.
Use the scheduler-facing `run-once` runner when the queue should be polled externally; it processes each manifest once, skips active leases, reclaims expired leases, and writes append-only audit snapshots without touching the execution sheet.
After the cooldown exists, switch to `AS_RUN_BINDING`, use `AS_RUN_PARTIAL` while provenance or output-path checks remain unresolved, and bind run identity from the as-run logbook and fridge log, hardware from the fridge log plus sample and channel maps, fixed settings from DAQ plus calibration, field history from the first actual loop, and output paths only after the files exist.
Promote to `AS_RUN_BOUND` only when all `binding_checks` are `true`.
Mirror the resolved JSON values into `protocols/e01_mm_first_cooldown_execution_sheet.md` without changing branch classification, falsifier logic, or the analysis gate order.
After `AS_RUN_BOUND`, point `data_capture.metadata_output_path` or `data_capture.raw_data_output_path` at a structured measurement evidence file conforming to `analysis/e01_mm_measurement_evidence_schema.md`.
Run `analysis/e01_mm_analysis_input_builder.py` against the authoritative run-binding JSON or queue manifest to emit normalized `analysis_input.json`.
Then run `analysis/e01_mm_analysis_runner.py` on that normalized input to produce the post-run summary artifact and optional Markdown report.
