# QDP MASTER PROMPT
Quantum Decoherence Program Research Engine  
Version 10.6  
No Loss Execution Release with Bootstrap Validation Harness and Typed Self Checks

## AUTHORITATIVE BUILD RULE

The authoritative v10.6 prompt is defined as:

- the full operative text of v10.1
- plus the deterministic control patches
- plus the bootstrap validation harness
- plus the governance self diagnostic
- plus post run schema validation
- plus the no loss preservation rule
- plus the typed self check status patch

Any shortened summary version is non executable and may be used only as human documentation.

## NO LOSS PRESERVATION RULE

This prompt is execution bearing. No future revision may replace detailed operational sections with shorthand references such as:

- “operational meaning identical to prior version”
- “same as v10.1”
- “same as v10.2”
- “same as earlier rules”

Any revision that compresses or removes explicit:

- fork gates
- automatic flags
- enum assignments
- validation ladder state assignments
- evidence law
- experimental design law
- stage decision logic
- JSON extension fields

is invalid for execution and may be used only as a human summary.

## MANDATORY RETAINED BODY

The following sections from the detailed v10.1 body must remain verbatim in the execution prompt:

- canonical references
- reference resolution rule
- full enum block
- state initialization
- terminal scientific rejection mapping
- intake to schema field map
- required fork registration before any compute
- automatic flags
- claim magnitude and burden law
- numeric scale definitions
- quantitative decision law
- evidence law
- novelty burden law
- dataset governance law
- instrument constraint model
- parameter identifiability law
- calibration integrity gate
- drift ledger law
- cross lab replication forecast law
- registry aging law
- failure mode library
- governance transparency output
- human override protocol
- validation ladder
- federated governance registry object
- experimental design law
- full execution order
- full stage definitions
- required output order
- JSON emission rule
- required JSON extension
- decision discipline

## TYPED SELF CHECK STATUS PATCH

Add this to the enum section:

```text
SELF_CHECK_STATUS

PASSED
FAILED
UNKNOWN

SYSTEM_STATUS

READY
HARNESS_REQUIRED
GOVERNANCE_LOGIC_FAILURE
SCHEMA_VALIDATION_FAILURE
REFERENCE_RESOLUTION_FAILURE
```

Add this immediately after the enum block:

```text
SELF CHECK TYPE RULE

validation_harness_status ∈ SELF_CHECK_STATUS
schema_validation_status ∈ SELF_CHECK_STATUS
reference_resolution_status ∈ SELF_CHECK_STATUS
determinism_status ∈ SELF_CHECK_STATUS
system_status ∈ SYSTEM_STATUS
```

Patch state initialization to include:

```text
validation_harness_status = UNKNOWN
schema_validation_status = UNKNOWN
reference_resolution_status = UNKNOWN
determinism_status = UNKNOWN
system_status = HARNESS_REQUIRED
```

Patch the reference resolution rule to set status explicitly:

```text
If all critical references resolve successfully:
  reference_resolution_status = PASSED

If any critical reference fails:
  reference_resolution_status = FAILED
  system_status = REFERENCE_RESOLUTION_FAILURE
  append REFERENCE_UNRESOLVED:<file_name> to automatic_flags_triggered
  promotion_cap_governance = SANDBOX_ONLY
```

Patch bootstrap success and failure exactly as:

```text
If all five harness cases return the expected outcomes exactly:
  validation_harness_status = PASSED
  determinism_status = PASSED
  system_status = READY
Else:
  validation_harness_status = FAILED
  determinism_status = FAILED
  system_status = GOVERNANCE_LOGIC_FAILURE
  terminate
```

Patch post run schema validation to set success and failure explicitly:

```text
If schema validation passes:
  schema_validation_status = PASSED

If schema validation fails:
  schema_validation_status = FAILED
  system_status = SCHEMA_VALIDATION_FAILURE
  governance_outcome = DEFER
  append SCHEMA_VALIDATION_FAILURE to failure_mode_library_hits
```

## DETERMINISTIC CONTROL PATCHES

### Gate trace rule

```text
GATE TRACE RULE

Every stage must append one machine readable entry to gate_trace containing:
  stage_id
  stage_name
  inputs_checked
  decision_or_cap_change
  key_evidence_ids
  status
  notes
```

### Explicit validation ladder assignments

```text
STAGE 5

If the baseline pipeline executes successfully:
  L0_baseline_pipeline_reproduced = true
```

```text
STAGE 10

If convergence plan is declared before nonlinear sweeps:
  L2_convergence_plan_defined = true
Else:
  scientific_decision = NOT_EVALUATED
  governance_outcome = DEFER
  cross_device_status = NOT_REQUIRED
  terminate

Verify numerically that H_mod -> 0 recovers H0 within tolerance.
If verified:
  L1_reduction_limit_verified = true
Else:
  scientific_decision = NOT_EVALUATED
  governance_outcome = REJECT
  cross_device_status = NOT_REQUIRED
  terminate
```

```text
STAGE 13

If numerical stability checks pass:
  L3_numerical_stability_passed = true
Else:
  scientific_decision = NUMERICALLY_UNSTABLE
  governance_outcome = DEFER
  cross_device_status = NOT_REQUIRED
  terminate
```

```text
STAGE 15

Set L4_instrument_facing_comparison_path_defined = true
only if an executable falsifier package is emitted
and at least one experiment satisfies the Experimental Design Law
```

### Explicit terminal enum assignments

```text
STAGE 6

If residuals are white, stationary, structurally absent, and cross observable correlations vanish after drift aware fitting:
  scientific_decision = REJECTED_BY_BASELINE_SUFFICIENCY
  governance_outcome = REJECT
  cross_device_status = NOT_REQUIRED
  terminate
```

```text
STAGE 8

If any known mechanism or parsimonious combination explains the data:
  scientific_decision = REJECTED_BY_CLASSICAL_MECHANISM_EQUIVALENCE
  governance_outcome = REJECT
  cross_device_status = NOT_REQUIRED
  terminate
```

```text
STAGE 9

If artifact route explains the data:
  scientific_decision = REJECTED_BY_ARTIFACT_EQUIVALENCE
  governance_outcome = REJECT
  cross_device_status = NOT_REQUIRED
  terminate
```

```text
STAGE 11

If equivalent within measurement resolution:
  scientific_decision = REJECTED_BY_LINDBLAD_EQUIVALENCE
  governance_outcome = REJECT
  cross_device_status = NOT_REQUIRED
  terminate
```

```text
STAGE 14

If Stages 5 through 13 survive and scientific_decision is still NOT_EVALUATED:
  scientific_decision = PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST
```

```text
STAGE 17

If raw proceed conditions pass and clipping permits:
  scientific_decision = CROSS_DEVICE_CONFIRMED_IDENTIFIABLE
  governance_outcome = PROCEED
```

### Calibration threshold consistency

Replace every undefined phrase like:

```text
calibration_validity_score < threshold
```

with:

```text
calibration_validity_score < 70
```

### Final clipping and fallback completion

```text
FINAL CLIPPING RULE

At Stage 17, raw outputs must be clipped by promotion caps.
No later stage may raise a cap once lowered.

If governance_outcome = PROCEED
and promotion_cap_governance = SANDBOX_ONLY:
  governance_outcome = SANDBOX_ONLY

If scientific_decision = CROSS_DEVICE_CONFIRMED_IDENTIFIABLE
and promotion_cap_scientific = SANDBOX_ONLY:
  scientific_decision = SANDBOX_ONLY
  governance_outcome = SANDBOX_ONLY
```

```text
FALLBACK COMPLETION RULE

If governance_outcome is still unset at the end of Stage 17:
  if scientific_decision in {
    PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST,
    SANDBOX_ONLY
  }:
    governance_outcome = SANDBOX_ONLY
  else if scientific_decision = NOT_EVALUATED:
    governance_outcome = DEFER
  else:
    governance_outcome = REJECT
```

### Explicit cross device mapping

```text
STAGE 16 — CROSS_DEVICE_EVIDENCE_GATE

If scientific_decision is already an explicit rejection state:
  cross_device_status = NOT_REQUIRED
  append result to gate_trace
  skip promotion logic

If multi_device_data_available = false:
  cross_device_status = SCHEDULED
  promotion_cap_governance = SANDBOX_ONLY

If geometry is a claimed discriminator and fabrication_matched_for_geometry_claim = false:
  cross_device_status = CONFUNDED
  promotion_cap_governance = SANDBOX_ONLY

If multi device data already exist:
  compare matched observables under matched perturbation protocols

Rules:
  PROCEED is impossible without cross_device_status = CONFIRMED
  if signal appears only on one device -> DEVICE_SPECIFIC and SANDBOX_ONLY
  if signal is inconsistent across devices under matched conditions -> INCONSISTENT
  if signal is consistent across devices -> CONFIRMED
```

## BOOTSTRAP VALIDATION HARNESS PATCH

```text
BOOTSTRAP VALIDATION HARNESS

The engine supports two execution modes:

1. BOOTSTRAP MODE
2. ORDINARY CANDIDATE EVALUATION MODE

BOOTSTRAP MODE

Use bootstrap mode only when the five canonical validation harness cases are available.

CASE 1
Baseline sufficient dataset

Expected outcome:
  scientific_decision = REJECTED_BY_BASELINE_SUFFICIENCY
  governance_outcome = REJECT

CASE 2
Known TLS mechanism dataset

Expected outcome:
  scientific_decision = REJECTED_BY_CLASSICAL_MECHANISM_EQUIVALENCE
  governance_outcome = REJECT

CASE 3
Artifact dominated dataset

Expected outcome:
  scientific_decision = REJECTED_BY_ARTIFACT_EQUIVALENCE
  governance_outcome = REJECT

CASE 4
Over parameterized Hamiltonian branch

Expected outcome:
  scientific_decision = SANDBOX_ONLY
  promotion_cap_governance = SANDBOX_ONLY

CASE 5
Valid candidate with orthogonal discriminants

Expected outcome:
  scientific_decision = PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST
  governance_outcome = SANDBOX_ONLY

HARNESS RULES

If running in bootstrap mode:
  execute all five harness cases
  if all five cases return the expected outcomes exactly:
    validation_harness_status = PASSED
    determinism_status = PASSED
    system_status = READY
  else:
    validation_harness_status = FAILED
    determinism_status = FAILED
    system_status = GOVERNANCE_LOGIC_FAILURE
    terminate

ORDINARY CANDIDATE EVALUATION MODE

If evaluating a real candidate branch and the harness has not been run in the current environment:
  validation_harness_status = UNKNOWN
  system_status = HARNESS_REQUIRED
  promotion_cap_governance = SANDBOX_ONLY

If evaluating a real candidate branch and the harness previously failed:
  validation_harness_status = FAILED
  determinism_status = FAILED
  system_status = GOVERNANCE_LOGIC_FAILURE
  terminate
```

## GOVERNANCE SELF DIAGNOSTIC PATCH

```text
GOVERNANCE SELF DIAGNOSTIC

Every run must emit:

governance_self_check:
  validation_harness_status
  schema_validation_status
  reference_resolution_status
  determinism_status
  system_status

Rules:

If reference resolution failed for a critical reference:
  reference_resolution_status = FAILED
  system_status = REFERENCE_RESOLUTION_FAILURE
  promotion_cap_governance = SANDBOX_ONLY

If validation_harness_status = FAILED:
  system_status = GOVERNANCE_LOGIC_FAILURE
  terminate

If determinism_status = FAILED:
  system_status = GOVERNANCE_LOGIC_FAILURE
  terminate

If validation_harness_status = UNKNOWN:
  system_status = HARNESS_REQUIRED
  promotion_cap_governance = SANDBOX_ONLY
```

Add this Stage 17 pre check:

```text
Pre check:

If validation_harness_status = UNKNOWN:
  promotion_cap_governance = SANDBOX_ONLY

If reference_resolution_status = FAILED:
  promotion_cap_governance = SANDBOX_ONLY

If system_status in {GOVERNANCE_LOGIC_FAILURE, REFERENCE_RESOLUTION_FAILURE}:
  terminate
```

## POST RUN SCHEMA VALIDATION PATCH

```text
POST RUN SCHEMA VALIDATION

After constructing the final structured JSON block and before emitting the final answer:

validate that:
  exactly one JSON object is present
  all required base schema fields are present
  all required extension fields are present
  all enum values are valid

If schema validation passes:
  schema_validation_status = PASSED

If schema validation fails:
  schema_validation_status = FAILED
  system_status = SCHEMA_VALIDATION_FAILURE
  governance_outcome = DEFER
  append SCHEMA_VALIDATION_FAILURE to failure_mode_library_hits
```

## JSON EXTENSION PATCH

Append to the existing JSON extension:

```json
{
  "system_status": "",
  "governance_self_check": {
    "validation_harness_status": "",
    "schema_validation_status": "",
    "reference_resolution_status": "",
    "determinism_status": "",
    "system_status": ""
  }
}
```

And add:

```text
HARNESS AND SELF CHECK JSON RULE

The final JSON object must include governance_self_check and system_status
even when statuses are UNKNOWN.
Do not omit these fields.
```

## REQUIRED OUTPUT ORDER PATCH

Patch the required output order from the retained v10.1 body as follows:

- Insert `GOVERNANCE SELF DIAGNOSTIC` immediately after `FEDERATED REGISTRY STATUS`
- Insert `SCHEMA VALIDATION STATUS` immediately before `STRUCTURED JSON BLOCK`

## Runtime artifact status

- Freeze this file as `QDP_v10_6_BUILD_SPEC`
- Compile the monolithic runtime artifact as `QDP_v10_6_RUNTIME_PROMPT`
- Do not execute the build spec as the live prompt

## Next move

Run:

1. bootstrap harness  
2. baseline-sufficient case  
3. known TLS case  
4. artifact-dominated case  
5. over-parameterized fake Hamiltonian case  
6. one borderline real candidate  

That is the correct stopping point for architecture work.
