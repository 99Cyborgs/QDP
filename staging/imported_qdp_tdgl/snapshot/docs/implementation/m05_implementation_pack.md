# QDP Codex Task Pack â€” M05 Stage Machine Closure

## Scope lock
You are working inside the QDP v10.6 repository.

Implement **M05 only**: the executable gate-trace and validation-ladder state machine.

This run is for **working-patch closure**, not authoritative closure.

Do **not**:
- fabricate the missing retained v10.1 operative body
- claim authoritative runtime closure
- resume ordinary candidate testing
- resume subsystem testing
- expand into M06, M07, M08, M09, M10, M11, M12, M13, or subsystem modules except where a minimal interface stub is required for M05 to run

## Ground truth you must honor
1. `specs/core/build_spec.md` is authoritative for the visible v10.6 stage logic, but it is **not** the live runtime.
2. `config/registries/module_registry.json` and `.md` define M05 as a core blocker.
3. `config/contracts/module_closure_contracts.json` defines the required predicates for M05 closure.
4. `config/registries/rule_binding_registry.json` defines which rules are already bound and which remain blocked by missing retained sources.
5. Missing retained sources still block authoritative binding. Your implementation must preserve that fact.

## Read first, in this order
1. `specs/core/build_spec.md`
2. `config/registries/module_registry.json`
3. `docs/repo/module_registry.md`
4. `config/schema/candidate_template.json`
5. `config/schema/candidate_schema.json`
6. `tools/validators/candidate_validator.py`
7. `config/manifests/reference_manifest.json`
8. `config/registries/governance_registry.json`
9. `artifacts/reports/m03/reference_resolution_ordinary.json`
10. `modules/m03_reference_resolution/runner.py`
11. `QDP_v10_6_FORK_INTAKE_TEMPLATE_M04.json`
12. `QDP_v10_6_FORK_INTAKE_SCHEMA_M04.schema.json`
13. `tools/validators/fork_intake_validator.py`
14. `modules/m04_branch_registration/runner.py`
15. `specs/core/master_spec.md`
16. `specs/core/validation_gate.md`
17. `specs/intake/fork_questions.md`
18. `specs/core/falsifier_registry.md`
19. `config/contracts/module_closure_contracts.json`
20. `config/registries/rule_binding_registry.json`
21. `config/policies/mode_divergence_policy.json`

## Objective
Create an executable **M05 stage machine** that consumes a QDP candidate JSON object, applies the visible v10.6 stage logic conservatively, emits machine-readable `gate_trace` entries, updates `validation_ladder`, applies cap clipping and fallback completion, and writes outputs that validate against `config/schema/candidate_schema.json` in final mode.

## Deliverables
Create these files:
1. `modules/m05_stage_machine/runner.py`
2. `modules/m05_stage_machine/selftest_cases.json`
3. `artifacts/reports/m05/selftest_report.json`
4. `QDP_v10_6_M05_PATCH_NOTES.md`

Optional minimal truthful updates are allowed only if necessary:
- `config/registries/rule_binding_registry.json`
- `config/contracts/module_closure_contracts.json`

If you touch those optional files, keep changes minimal and factual.

## Non-negotiable implementation rules

### 1. No invention beyond surfaced rules
Use only the visible rules from the uploaded artifacts.
If a stage depends on retained v10.1 logic that is not surfaced, implement only the visible subset and document the limitation explicitly.

### 2. Preserve governance truthfulness
Do not mark M05 as `AUTHORITATIVE_CLOSURE`.
At best, this run may justify `WORKING_PATCH` if the executable subset, self-tests, and schema validation all pass.

### 3. Use the existing candidate schema
Do not add new **required top-level fields**.
If you need helper flags for the interim executable subset, place them under existing permissive objects such as:
- `baseline_model`
- `residual_analysis`
- `mechanism_tests`
- `artifact_tests`
- `hamiltonian_test`
- `cross_device_validation`
- `evaluation_notes`

### 4. Final outputs must validate
All self-test emitted candidate outputs must pass:
```bash
python tools/validators/candidate_validator.py <candidate_output.json> --mode final
```

### 5. Deterministic behavior
The stage machine and self-tests must be deterministic.
No randomness.
No time-dependent pass/fail behavior except timestamps in report metadata.

## Required stage-machine behavior

Implement an explicit stage runner for the **visible** stages only.
At minimum, support:
- pre-check governance self-diagnostic handling
- Stage 5
- Stage 6
- Stage 8
- Stage 9
- Stage 10
- Stage 11
- Stage 13
- Stage 14
- Stage 16
- Stage 17
- final clipping rule
- fallback completion rule
- post-run schema validation

### Governance pre-check behavior
Before running stage logic:
- if `governance_self_check.validation_harness_status == "UNKNOWN"`, force `promotion_cap_governance = "SANDBOX_ONLY"`
- if `governance_self_check.reference_resolution_status == "FAILED"`, force `promotion_cap_governance = "SANDBOX_ONLY"`
- if `system_status` is `GOVERNANCE_LOGIC_FAILURE` or `REFERENCE_RESOLUTION_FAILURE`, terminate conservatively and emit a gate-trace entry explaining why
- preserve mirror consistency between top-level `system_status` and `governance_self_check.system_status`

### Stage 5
If the baseline pipeline executed successfully, set:
- `validation_ladder.L0_baseline_pipeline_reproduced = true`

Use a documented, explicit trigger based on fields already present in the candidate object.
Document the trigger in patch notes and self-test cases.

### Stage 6
If residuals are white, stationary, structurally absent, and cross-observable correlations vanish after drift-aware fitting, terminate with:
- `scientific_decision = "REJECTED_BY_BASELINE_SUFFICIENCY"`
- `governance_outcome = "REJECT"`
- `cross_device_status = "NOT_REQUIRED"`

### Stage 8
If any known mechanism or parsimonious combination explains the data, terminate with:
- `scientific_decision = "REJECTED_BY_CLASSICAL_MECHANISM_EQUIVALENCE"`
- `governance_outcome = "REJECT"`
- `cross_device_status = "NOT_REQUIRED"`

### Stage 9
If artifact route explains the data, terminate with:
- `scientific_decision = "REJECTED_BY_ARTIFACT_EQUIVALENCE"`
- `governance_outcome = "REJECT"`
- `cross_device_status = "NOT_REQUIRED"`

### Stage 10
If convergence plan is declared before nonlinear sweeps, set:
- `validation_ladder.L2_convergence_plan_defined = true`

If convergence plan is missing, terminate conservatively with:
- `scientific_decision = "NOT_EVALUATED"`
- `governance_outcome = "DEFER"`
- `cross_device_status = "NOT_REQUIRED"`

Then verify reduction limit.
If verified, set:
- `validation_ladder.L1_reduction_limit_verified = true`

If reduction limit fails, terminate conservatively with:
- `scientific_decision = "NOT_EVALUATED"`
- `governance_outcome = "REJECT"`
- `cross_device_status = "NOT_REQUIRED"`

### Stage 11
If equivalent within measurement resolution, terminate with:
- `scientific_decision = "REJECTED_BY_LINDBLAD_EQUIVALENCE"`
- `governance_outcome = "REJECT"`
- `cross_device_status = "NOT_REQUIRED"`

### Stage 13
If numerical stability checks pass, set:
- `validation_ladder.L3_numerical_stability_passed = true`

Else terminate with:
- `scientific_decision = "NUMERICALLY_UNSTABLE"`
- `governance_outcome = "DEFER"`
- `cross_device_status = "NOT_REQUIRED"`

### Stage 14
If Stages 5 through 13 survive and `scientific_decision` is still unset or `NOT_EVALUATED`, set:
- `scientific_decision = "PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST"`

### Stage 15 / L4 rule
Even if you do not implement a full Stage 15 runner, you must enforce the visible L4 rule:
Set `validation_ladder.L4_instrument_facing_comparison_path_defined = true` **only if**:
- an executable falsifier package is emitted or explicitly represented by current fields, and
- at least one experiment satisfies the visible instrument-facing requirement

Do not set L4 true from planning text alone.

### Stage 16 cross-device gate
Implement the visible cross-device logic:
- if already in an explicit rejection state, set `cross_device_status = "NOT_REQUIRED"`
- if `multi_device_data_available == false`, set `cross_device_status = "SCHEDULED"` and force `promotion_cap_governance = "SANDBOX_ONLY"`
- if geometry is a claimed discriminator and fabrication match is false, set `cross_device_status = "CONFUNDED"` and force `promotion_cap_governance = "SANDBOX_ONLY"`
- if multi-device data exist, map to one of:
  - `DEVICE_SPECIFIC`
  - `INCONSISTENT`
  - `CONFIRMED`
- `PROCEED` must be impossible without `cross_device_status = "CONFIRMED"`
- mirror `cross_device_status` with `cross_device_validation.status`

### Stage 17
If raw proceed conditions pass and clipping permits, allow:
- `scientific_decision = "CROSS_DEVICE_CONFIRMED_IDENTIFIABLE"`
- `governance_outcome = "PROCEED"`

### Final clipping rule
Implement the visible clipping rules exactly:
- `PROCEED` + `promotion_cap_governance = "SANDBOX_ONLY"` => `governance_outcome = "SANDBOX_ONLY"`
- `CROSS_DEVICE_CONFIRMED_IDENTIFIABLE` + `promotion_cap_scientific = "SANDBOX_ONLY"` =>
  - `scientific_decision = "SANDBOX_ONLY"`
  - `governance_outcome = "SANDBOX_ONLY"`

### Fallback completion rule
If `governance_outcome` is still unset at the end:
- if `scientific_decision` is `PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST` or `SANDBOX_ONLY` => `governance_outcome = "SANDBOX_ONLY"`
- if `scientific_decision` is `NOT_EVALUATED` => `governance_outcome = "DEFER"`
- else => `governance_outcome = "REJECT"`

## Gate trace requirements
Every stage run must append a machine-readable `gate_trace` entry with exactly these fields:
- `stage_id`
- `stage_name`
- `inputs_checked`
- `decision_or_cap_change`
- `key_evidence_ids`
- `status`
- `notes`

Use the schema-defined shape.
Do not omit gate-trace entries for skipped or terminating stages; mark them explicitly.

## Required trigger mapping for the interim executable subset
Because the full retained runtime is missing, define a **small, documented trigger table** for the M05 working patch.
Use only existing fields.

At minimum, document and implement explicit triggers for:
- baseline pipeline executed
- residual whiteness / stationarity / no structured residuals
- classical mechanism explains data
- artifact route explains data
- convergence plan declared
- reduction limit verified
- numerical stability passed
- Lindblad equivalence within measurement resolution
- instrument-facing path defined
- cross-device confirmed vs scheduled/confounded/device-specific/inconsistent

Use helper functions. Keep them deterministic and conservative.

## Mandatory self-tests
Create `modules/m05_stage_machine/selftest_cases.json` with at least these six cases.
Each case must include:
- `case_id`
- input candidate object or input candidate path
- expected top-level result fields
- expected terminating stage or final stage summary

### Required case 1
`CASE_M05_BASELINE_SUFFICIENCY`
Expected:
- `scientific_decision = REJECTED_BY_BASELINE_SUFFICIENCY`
- `governance_outcome = REJECT`
- `cross_device_status = NOT_REQUIRED`

### Required case 2
`CASE_M05_CLASSICAL_MECHANISM_EQUIVALENCE`
Expected:
- `scientific_decision = REJECTED_BY_CLASSICAL_MECHANISM_EQUIVALENCE`
- `governance_outcome = REJECT`
- `cross_device_status = NOT_REQUIRED`

### Required case 3
`CASE_M05_ARTIFACT_EQUIVALENCE`
Expected:
- `scientific_decision = REJECTED_BY_ARTIFACT_EQUIVALENCE`
- `governance_outcome = REJECT`
- `cross_device_status = NOT_REQUIRED`

### Required case 4
`CASE_M05_LINDBLAD_EQUIVALENCE`
Expected:
- `scientific_decision = REJECTED_BY_LINDBLAD_EQUIVALENCE`
- `governance_outcome = REJECT`
- `cross_device_status = NOT_REQUIRED`

### Required case 5
`CASE_M05_PROVISIONAL_SURVIVAL_NO_CROSS_DEVICE`
Expected:
- `scientific_decision = PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST`
- `cross_device_status = SCHEDULED`
- final `governance_outcome = SANDBOX_ONLY`

### Required case 6
`CASE_M05_PLANNING_FIELD_DOES_NOT_EQUAL_PASS`
Purpose:
prove that planning fields are not conflated with passed states.
Expected behavior:
- `validation_ladder.L2_convergence_plan_defined = true` may be set if justified
- `validation_ladder.L3_numerical_stability_passed` must remain false if numerical stability did not actually pass
- output must terminate conservatively with `scientific_decision = NUMERICALLY_UNSTABLE` and `governance_outcome = DEFER`

## Self-test runner requirements
Your Python entrypoint must support running the self-tests and emitting `artifacts/reports/m05/selftest_report.json`.
The report must include, at minimum:
- artifact id
- module id
- timestamp
- total cases
- passed cases
- `all_passed`
- per-case expected vs actual summary
- per-case schema validation result
- overall `schema_valid_all`

## Validation commands you must run
Run and report these commands:
```bash
python modules/m05_stage_machine/runner.py --selftest --write-report artifacts/reports/m05/selftest_report.json
python tools/validators/candidate_validator.py <each_emitted_case_output.json> --mode final
```

If your CLI differs, keep it minimal and document the exact commands in patch notes.

## Patch-note requirements
`QDP_v10_6_M05_PATCH_NOTES.md` must state:
1. what was created
2. exact trigger mapping used for the interim executable subset
3. which build-spec rules were implemented verbatim
4. what remains blocked by missing retained v10.1 sources
5. the resulting M05 status (`WORKING_PATCH` vs blocked)
6. exact commands run and whether all self-tests passed

## Success criteria
This run is successful only if all of the following are true:
- `modules/m05_stage_machine/runner.py` exists
- self-test cases exist
- self-test report exists
- all self-tests pass
- all emitted candidate outputs validate in final mode
- gate trace entries are emitted with the correct shape
- planning fields are not conflated with passed states
- no claim of authoritative closure is made

## Failure behavior
If you cannot satisfy the above without inventing missing retained logic:
- leave M05 as `BLOCKED` or `WORKING_PATCH`, whichever is truthful
- emit patch notes explaining the exact blocker
- do not fabricate retained content

## Final response format for this Codex run
Return:
1. touched files
2. commands run
3. self-test summary
4. whether schema validation passed for all cases
5. whether M05 now qualifies as `WORKING_PATCH`
6. what still blocks `AUTHORITATIVE_CLOSURE`
