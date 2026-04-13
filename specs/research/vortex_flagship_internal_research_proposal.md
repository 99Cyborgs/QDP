# Vortex Flagship Internal Research Proposal

## Abstract

This document is the governed human-review proposal for the QDP vortex branch. It packages the current vortex mechanism evidence, the current `M12` experiment-design output, and the drafted lab request pack into one internal review surface for lab and operator use.

This proposal is source truth for human review only. Generated artifacts under `artifacts/` remain execution evidence and handoff attachments, not governing source documents. This proposal is recovery-lane only. It does not claim authoritative readiness, repo promotion readiness, or any widened ALL-MIND control-plane surface.

The canonical machine-facing anchor for this proposal is `artifacts/outputs/m12/selftests/CASE_M12_VORTEX_SWEEP_SYNTHESIS/CASE_M12_VORTEX_SWEEP_SYNTHESIS_candidate.json`. The upstream mechanism evidence remains `artifacts/outputs/m09/selftests/CASE_M09_VORTEX_EXPLAINS/CASE_M09_VORTEX_EXPLAINS_candidate.json`. The current downstream execution handoff remains `artifacts/lab/requests/m09-case-vortex/QDPLAB-48A24B1CAD3FC365_request_pack.json`.

## Research Question and Hypothesis

**Research question**

Can the currently surfaced loss signature be explained by vortex pinning or trapped-flux dynamics rather than by TLS saturation, quasiparticle activity, or classical control-chain and readout artifacts?

**Working hypothesis**

If the vortex branch is the governing explanation, then zero-field-cooled versus field-cooled preparation and up-loop versus down-loop magnetic history will produce reproducible hysteresis and a stable `delta fr / delta (1/Qi)` ordering, and that ordering will persist under matched width or thickness changes without being absorbed by the minimum competing-mechanism control set.

## Current Evidence Baseline

### Source evidence

- `specs/core/signature_to_bath_decision_chart.md` maps hysteresis in `1/Qi` or frequency shift versus `Bcool` or sweep direction to metastable configuration memory and specifies the minimum discriminant measurement as `ZFC` versus `FC` plus up-loop and down-loop field history.
- `specs/research/vortex_pinning_methods.md` states that vortex loss is operationally identified by field-dependent microwave loss, field-sweep hysteresis, and geometry-sensitive trapping behavior in superconducting thin films and resonators.
- `specs/research/deep_research_report.md` argues that magnetic history and geometry scaling are the main discriminants for vortex routes and that no single observable is sufficient without orthogonal perturbations.

### Generated evidence and handoff surfaces

- `artifacts/outputs/m09/selftests/CASE_M09_VORTEX_EXPLAINS/CASE_M09_VORTEX_EXPLAINS_candidate.json` records the current mechanism-level evidence: signature matches `HYSTERESIS` and `CONSISTENT_IMPEDANCE_RATIO`, strongest competing mechanism `VORTEX`, and the note that `Bcool` history plus repeated field loops track the loss shift.
- `artifacts/outputs/m12/selftests/CASE_M12_VORTEX_SWEEP_SYNTHESIS/CASE_M12_VORTEX_SWEEP_SYNTHESIS_candidate.json` records the current experiment-design surface: exact falsifier, primary vortex discriminant sweep, `VORTEX` route ownership, lab and simulation sweep requirements, and the active tested parameter ranges.
- `artifacts/lab/requests/m09-case-vortex/QDPLAB-48A24B1CAD3FC365_request_pack.json` carries the drafted recovery-lane request pack with the same exact falsifier and the same primary experiment string as the `M12` candidate.

### Current execution limitations

- `candidate_target_devices` is still empty in the current `M12` candidate and in the drafted request pack.
- `calibration_status`, `dataset_governance`, and `identifiability_status` remain `PENDING_REVIEW`.
- `cross_device_status` is only `SCHEDULED`.
- `promotion_cap_governance` remains `SANDBOX_ONLY`.

These are execution prerequisites, not evidence of branch failure. They are surfaced here so the proposal does not overstate readiness.

## Exact Falsifier

The governing falsifier for this proposal is copied directly from the current `M12` vortex sweep synthesis candidate and the drafted vortex request pack:

> If the vortex branch is real, ZFC vs FC, field-loop history, and matched width or thickness sweeps must preserve the delta fr over delta 1/Qi ordering across cooldowns.

This proposal introduces no alternate falsifier and does not widen the current machine-facing contract.

## Specific Aims

### Aim 1: Reproduce magnetic-history hysteresis across cooldowns

Reproduce the surfaced vortex signature by running the current `ZFC` versus `FC` preparation and up-loop versus down-loop field-history sweep and verifying that hysteresis remains visible across repeated cooldowns.

### Aim 2: Test whether geometry preserves the impedance-ordering signal

Run matched width or thickness comparisons and verify that the observed `delta fr / delta (1/Qi)` ordering remains stable under the geometry labels already present in the `M12` sweep definition.

### Aim 3: Refuse escalation unless competing routes fail

Before any branch survival beyond this proposal, require the minimum control set already implied by QDP source materials:

- TLS route: check whether power and temperature behavior absorbs the observed signal.
- Quasiparticle route: check whether parity or shielding dependence absorbs the observed signal.
- Artifact route: check whether control-chain, readout, or calibration alias behavior absorbs the observed signal.

If any of those routes explains the data more parsimoniously than the vortex branch, the branch is demoted to that follow-up path and does not escalate to Hamiltonian modification.

## Experiment Matrix

The primary experiment for this proposal is the current request-pack priority experiment:

`Vortex discriminant sweep: ZFC vs FC, field loops, cooldown field, matched width or thickness, delta fr over delta 1/Qi`

The governing sweep axes are copied directly from `artifacts/outputs/m12/selftests/CASE_M12_VORTEX_SWEEP_SYNTHESIS/CASE_M12_VORTEX_SWEEP_SYNTHESIS_candidate.json`.

| Sweep axis | Levels | Proposal use |
|---|---|---|
| `field_history_tag` | `ZFC`, `FC`, `UP_LOOP`, `DOWN_LOOP` | Establish magnetic-history dependence and hysteresis reproducibility |
| `field_magnitude` | `LOW`, `MID`, `HIGH` | Check whether the vortex signature survives controlled cooldown-field changes |
| `geometry` | `MATCHED_WIDTH_A`, `MATCHED_WIDTH_B` | Test matched width or thickness dependence without changing proposal scope |
| `drive_amplitude` | `LOW`, `MID`, `HIGH` | Check whether the signal is stable across the current drive envelope |
| `temperature` | `BASE`, `MID`, `HIGH` | Provide the minimum thermal axis needed to separate vortex behavior from TLS-like alternatives |

Execution rules for this matrix:

- Keep the route classification as `VORTEX`.
- Keep `branch_partition=mechanism_discrimination`.
- Preserve the current `simulation_sweep_required=true` and `lab_sweep_required=true` settings.
- Do not add proposal-only sweep axes beyond the current `M12` set.

## Competing-Mechanism Controls

The proposal does not assume that the vortex branch wins by default. It requires the minimum competing-route checks already implied by the source evidence set.

### TLS control

Use the power and temperature behavior around the active sweep to test whether a TLS saturation explanation is more parsimonious than magnetic-history-driven vortex behavior.

### Quasiparticle control

Use the minimum available shielding or parity-sensitive check to test whether quasiparticle activity absorbs the observed signal more cleanly than the vortex branch.

### Artifact controls

Require the execution review to record whether control-chain distortion, readout alias, or calibration drift can explain the observed behavior before branch survival is declared.

These controls are gating checks for branch survival. They do not replace the primary vortex discriminant sweep and they do not supersede the current request-pack experiment.

## Instrument and Data Preconditions

The current proposal is not ready for blind lab execution. The following preconditions must be closed before the drafted request pack is treated as executable:

- Assign real target-device identifiers in place of the current empty `candidate_target_devices` field.
- Bind `MATCHED_WIDTH_A` and `MATCHED_WIDTH_B` to real matched geometry selections before running the geometry comparison.
- Confirm or regenerate the instrument profile at `artifacts/lab/requests/m09-case-vortex/QDPLAB-48A24B1CAD3FC365_instrument_profile.json` after device assignment.
- Capture a calibration snapshot and a lineage record before any result is treated as branch-evidence.
- Preserve recovery-lane labeling unless those prerequisites are closed by standard QDP governance.

These are required because the current branch still shows pending calibration and dataset-governance status, plus scheduled rather than confirmed cross-device status.

## Analysis and Decision Gates

### Success criteria

The proposal succeeds only if all of the following hold:

1. Hysteresis is reproduced across `ZFC` versus `FC` and up-loop versus down-loop histories over repeated cooldowns.
2. The `delta fr / delta (1/Qi)` ordering remains preserved when the matched geometry labels are exercised.
3. The minimum TLS, quasiparticle, and artifact control checks fail to absorb the signal more parsimoniously than the vortex branch.

### Branch survival rule

If the success criteria are met, the branch may advance to the next governed confirmation stage as a vortex-first mechanism branch. This proposal itself does not authorize promotion, authoritative readiness claims, or ALL-MIND-facing interface changes.

### Failure rule

If hysteresis is not reproducible, if the ordering collapses under matched geometry, or if a competing route explains the signal more parsimoniously, the branch is demoted to TLS, quasiparticle, or control-noise follow-up. It does not escalate to Hamiltonian modification on ambiguous evidence.

## Risks and Fallback Paths

- The current branch has no assigned device identifiers. That blocks direct execution and creates an avoidable mismatch between the proposal and the drafted request pack.
- The current branch has pending calibration and dataset-governance status. That blocks any claim of independent evidence.
- The current branch is still recovery-lane and `SANDBOX_ONLY`. This proposal must not be misread as a promotion artifact.
- The source research notes are useful evidence but not clean enough to copy directly into an operator proposal. This document is therefore a paraphrased control surface rather than a narrative duplicate.

Fallback handling is fixed:

- If the vortex discriminant sweep fails, move to the most parsimonious competing route.
- If the sweep is directionally suggestive but governance prerequisites are incomplete, hold the branch in recovery-lane status rather than widening claims.

## Appendices

### Appendix A: Traceability map

| Proposal element | Governing source |
|---|---|
| Branch mechanism claim | `artifacts/outputs/m09/selftests/CASE_M09_VORTEX_EXPLAINS/CASE_M09_VORTEX_EXPLAINS_candidate.json` |
| Exact falsifier | `artifacts/outputs/m12/selftests/CASE_M12_VORTEX_SWEEP_SYNTHESIS/CASE_M12_VORTEX_SWEEP_SYNTHESIS_candidate.json` |
| Primary experiment string | `artifacts/lab/requests/m09-case-vortex/QDPLAB-48A24B1CAD3FC365_request_pack.json` |
| Sweep axes and levels | `artifacts/outputs/m12/selftests/CASE_M12_VORTEX_SWEEP_SYNTHESIS/CASE_M12_VORTEX_SWEEP_SYNTHESIS_candidate.json` |
| Hysteresis interpretation rule | `specs/core/signature_to_bath_decision_chart.md` |
| Vortex operational mechanism framing | `specs/research/vortex_pinning_methods.md` |
| Orthogonal-discriminant rationale | `specs/research/deep_research_report.md` |

### Appendix B: Governed evidence versus handoff attachments

Source-truth human review document:

- `specs/research/vortex_flagship_internal_research_proposal.md`

Generated evidence and handoff attachments:

- `artifacts/outputs/m09/selftests/CASE_M09_VORTEX_EXPLAINS/CASE_M09_VORTEX_EXPLAINS_candidate.json`
- `artifacts/outputs/m12/selftests/CASE_M12_VORTEX_SWEEP_SYNTHESIS/CASE_M12_VORTEX_SWEEP_SYNTHESIS_candidate.json`
- `artifacts/lab/requests/m09-case-vortex/QDPLAB-48A24B1CAD3FC365_request_pack.json`
- `artifacts/lab/requests/m09-case-vortex/QDPLAB-48A24B1CAD3FC365_candidate_manifest.json`
- `artifacts/lab/requests/m09-case-vortex/QDPLAB-48A24B1CAD3FC365_instrument_profile.json`

### Appendix C: Scope lock

- This proposal does not add a schema, CLI command, control-plane contract, or promotion artifact.
- This proposal does not supersede `STATUS.md`, `PROMOTION_NOTES.md`, or `INTEGRATION_PLAN.md`.
- This proposal exists to turn the current vortex branch into one governed internal review surface without widening the repo boundary.
