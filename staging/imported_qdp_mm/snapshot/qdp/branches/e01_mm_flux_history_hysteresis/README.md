# E01 Flux History Hysteresis Discriminator

## What E01 Is

E01 is the branch pack for testing whether field-history dependence in `1/Qi` should be registered first as a conservative metastable memory effect under fixed low temperature and fixed low drive.

The branch is organized to support registration, minimal lab execution, mechanism competition, simulation planning, and worker handoff without requiring a wider theory claim.

## What E01 Is Not

- Not a vortex proof branch.
- Not a cross-device confirmation branch.
- Not a broad power-sweep study.
- Not a broad temperature-sweep study.
- Not a claim that a microscopic mechanism has already been identified.

## Why This Is Metastable Memory First

The intake label is `METASTABLE_C_STATE` because the primary observable is hysteresis in `1/Qi` versus magnetic field history.
That observable can exist without establishing a vortex-specific origin.
The pack therefore preserves the standard memoryless baseline, requires dwell and sham controls, rejects H0 first, then compares H1 against H3 and H4, and only then allows any geometry-specific H2 promotion discussion.

## How It Could Later Be Promoted To A Vortex Candidate

Promotion is conditional, not automatic.
The later H2 path requires same-chip matched geometry, consistent susceptibility ordering across the minimum three cooldowns, negative sham and witness controls, and failure of H0, H3, and H4 to explain the primary observable.
Even then, the posture remains conservative and candidate-level.

## Authoritative Artifacts

- `specs/e01_mm_branch_spec.md`
- `specs/e01_mm_exact_falsifier.md`
- `protocols/e01_mm_measurement_protocol.md`
- `analysis/e01_mm_analysis_protocol.md`
- `competition/e01_mm_mechanism_competition.md`
- `failures/e01_mm_failure_mode_ledger.md`
- `simulation/e01_mm_minimal_sim_plan.md`
- `intake/e01_mm_fork_intake.json`
- `intake/e01_mm_candidate_seed.json`
- `handoff/e01_mm_codex_handoff.md`

If any later worker output conflicts with the branch spec or exact falsifier, those two artifacts control.

## Operational Artifacts

- `analysis/e01_mm_analysis_input_builder.py`
- `analysis/e01_mm_analysis_input_schema.md`
- `analysis/e01_mm_measurement_evidence_schema.md`
- `protocols/e01_mm_first_cooldown_execution_sheet.md`
- `protocols/e01_mm_first_cooldown_run_binding.json`
- `protocols/e01_mm_candidate_packet_sweep_generator.ps1`
- `protocols/e01_mm_first_cooldown_candidate_sweep_spec.json`
- `protocols/e01_mm_first_cooldown_candidate_packets.generated.json`
- `execution_queue/e01_mm_execution_queue_spec.md`
- `execution_queue/e01_mm_first_cooldown_queue_manifest.json`
- `execution_queue/e01_mm_execution_queue.py`
- `execution_queue/e01_mm_reconciliation.py`
- `execution_queue/test_e01_mm_execution_queue.py`
- `simulation/__init__.py`
- `simulation/e01_mm_simulation_suite.py`
- `simulation/test_e01_mm_simulation_suite.py`
- `simulation/e01_mm_simulation_proposal.md`
- `simulation/e01_mm_simulation_appendix.md`

Use `PRE_RUN_MINIMUM_ACQUISITION` to define the smallest defensible first cooldown before any as-run files exist.
Use `AS_RUN_BINDING` only after a completed cooldown and bind run identity from the as-run logbook and fridge log, hardware from the fridge log plus sample and channel maps, thermal and readout state from the DAQ plus calibration record, field history from the first actual loop, and output paths only after the files or directories exist.
Use `PRE_RUN_MINIMUM_READY` only for a complete pre-run discriminator plan, `AS_RUN_PARTIAL` for a completed cooldown with unresolved provenance or output checks, and `AS_RUN_BOUND` only when all binding checks are true.
Mirror the resolved JSON values into the execution sheet after checking the binding rules.
Use `execution_queue/e01_mm_first_cooldown_queue_manifest.json` as the file-backed queue record for unattended state progression around the same authoritative run-binding payload.
Use `execution_queue/e01_mm_execution_queue.py` to create queue manifests, claim worker leases, validate staged bindings, and advance queue state without changing the scientific meaning of the branch artifacts.
Use `execution_queue/e01_mm_reconciliation.py` to load declared provenance files, reconcile source-owned fields into the authoritative run-binding JSON, compute binding checks, and report conflicts or parse failures structurally.
Use `execution_queue/e01_mm_execution_queue_spec.md` to interpret queue states, reason codes, and worker triggers before extending the queue behavior.
Use `run-once` when the queue should be advanced by an external scheduler; it discovers queue manifests, skips actively leased items, persists reconciled run-binding updates, and writes append-only audit snapshots under the queue audit directory.
Use the generator only to enumerate non-authoritative candidate field and dwell packets from a sweep-spec JSON.
Use `protocols/e01_mm_first_cooldown_candidate_sweep_spec.json` as the default single-candidate seed for the smallest phase 1 discriminator packet unless lab-specific hardware provenance requires a different field plan.
Treat `protocols/e01_mm_first_cooldown_candidate_packets.generated.json` as generated output only.
Use `simulation/e01_mm_simulation_suite.py` to execute the five authorized synthetic cases without hardware and emit deterministic JSON outputs suitable for proposal review.
Use `simulation/e01_mm_simulation_appendix.md` as the generated proposal appendix tied to the declared simulation seed.
Use `simulation/test_e01_mm_simulation_suite.py` to smoke-test the simulation package before proposing any branch expansion.
Use `analysis/e01_mm_measurement_evidence_schema.md` as the contract for the structured measurement evidence file referenced by the authoritative run-binding payload.
Use `analysis/e01_mm_analysis_input_builder.py` to turn a bound run-binding record and declared measurement evidence into `analysis_input.json` for post-run scoring.
Use `analysis/e01_mm_analysis_runner.py` only on normalized analysis input produced by the builder or an equivalent schema-conforming export.
Do not treat generated packets as hardware-bound records and do not overwrite the authoritative run-binding JSON with an unselected candidate.
These files do not change branch classification, falsifier logic, or analysis order.
