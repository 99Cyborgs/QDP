# QDP v10.6 M04 Fork Intake and Branch Registration Patch Notes
Version: 1.0  
Date: 2026-03-13  
Status: Working patch for branch-intake normalization and candidate pre-registration

## Scope

This patch addresses **M04 â€” Fork intake and branch registration**.

It converts the one-page fork intake requirements into a machine-readable intake object, validates that object, and maps it onto the working M02 candidate template while preserving the governance logic already surfaced in the QDP materials.

## Inputs used

- `specs/intake/fork_intake_form_one_page.pdf`
- `specs/intake/fork_questions.md`
- `specs/core/master_spec.md`
- `specs/core/validation_gate.md`
- `specs/core/bath_glossary.md`
- `config/schema/candidate_template.json`
- `config/registries/governance_registry.json`

## What changed

### 1. Added a machine-readable intake template

Artifact:
- `QDP_v10_6_FORK_INTAKE_TEMPLATE_M04.json`

This template preserves the mandatory fork-registration surface from the one-page intake form:

- branch identification
- change type
- classification
- likely bath class
- primary and secondary observables
- minimal discriminant measurement
- invariant
- reduction limit
- free-parameter count and constraint sources
- exact falsifier
- nuisance controls
- validation-ladder planning fields

It also adds optional Hamiltonian-specific fields already present in the candidate template:

- `candidate_H_mod_symbolic`
- `candidate_H_mod_physical_interpretation`
- `claimed_effect`

### 2. Added a fork-intake schema

Artifact:
- `QDP_v10_6_FORK_INTAKE_SCHEMA_M04.schema.json`

The schema enforces structure, enum normalization targets, and presence of all intake fields.

Strings may remain blank in template mode.
Stricter non-empty checks are handled by the validator script.

### 3. Added an intake validator

Artifact:
- `tools/validators/fork_intake_validator.py`

Validator modes:

- `template` for structure-only validation of blank templates
- `final` for pre-registration intake validation

The validator checks:

- change-type and bath-class enum validity
- `count_new_free_parameters == len(new_free_parameters)`
- duplicate parameter names
- `cross_scale_claim_present => effective_mapping_attached`
- `declared_likely_bath_class_raw = OTHER => declared_likely_bath_class_other_text non-empty`

It emits warnings, not hard failure, for cases that are allowed but governance-relevant, such as unconstrained parameters or empty nuisance-control lists.

### 4. Added an executable branch-registration mapper

Artifact:
- `modules/m04_branch_registration/runner.py`

This script takes:

- an M04 intake JSON
- the working M02 candidate template
- the M03 governance registry

and produces:

- a candidate JSON pre-populated from the intake
- a machine-readable branch-registration report

### 5. Explicit conservative mapping for the L3 ladder field

The one-page intake form asks whether the **L3 stability criterion is defined**.

The working candidate template field is **`validation_ladder.L3_numerical_stability_passed`**.

These are not the same thing.

This patch therefore preserves semantics conservatively:

- intake `L3_stability_criterion_defined` is recorded in notes / gate trace
- it does **not** set `L3_numerical_stability_passed = true`

That pass state remains reserved for later execution logic.

### 6. Automatic flag and preliminary outcome logic

The registration script emits preliminary governance flags from the surfaced rules:

- `MISSING_BRANCH_TAG`
- `MISSING_CHANGE_TYPE`
- `MISSING_MODEL_CLASSIFICATION`
- `MISSING_PRIMARY_OBSERVABLE`
- `MISSING_SECONDARY_OBSERVABLE`
- `MISSING_PRIMARY_OBSERVABLE_AND_SECONDARY_OBSERVABLE`
- `MISSING_EXACT_FALSIFIER`
- `MISSING_REDUCTION_LIMIT`
- `SCALE_CLAIM_WITHOUT_EFFECTIVE_MAPPING`
- `BATH_CLASSIFICATION_INCONSISTENT`
- `MORE_THAN_TWO_UNCONSTRAINED_NEW_PARAMETERS`
- duplicate flags from the M03 registry

These flags are converted into a **preliminary intake outcome**:

- `REJECT` for hard scope violations
- `DEFER` for missing mandatory registration material
- `SANDBOX_ONLY` for parameter-overextension
- `PROCEED` only if the intake clears the surfaced fork rules

This preliminary intake outcome is reported in the registration report.
The working candidate JSON is not falsely marked as final scientific success.

### 7. Gate-trace insertion

The mapper appends an M04 machine-readable `gate_trace` entry with:

- stage id
- stage name
- inputs checked
- decision or cap change
- evidence ids
- status
- notes

This prepares the branch object for M05 rather than leaving intake logic outside traceability.

## What this patch does NOT solve

### 1. It does not clear M01 or M03 blockers

The build spec still requires the retained v10.1 operative body for the executable runtime, and the current M03 report still fails because critical retained references are missing.

### 2. It does not implement M05 execution logic

This patch inserts a single intake-stage trace entry, but it does not implement the full stage machine, cap clipping, or ladder transitions.

### 3. It does not perform mechanism triage

Bath-class normalization is limited to intake consistency.
Mechanism scoring, signature matching, and minimal-measurement ranking remain M07 work.

## Recommended next move after M04

Proceed to **M05 â€” Gate-trace and validation-ladder state machine**.

M04 now creates a machine-readable registered branch object.
The next blocker is the execution logic that must consume it.

## Artifact list

- `QDP_v10_6_FORK_INTAKE_TEMPLATE_M04.json`
- `QDP_v10_6_FORK_INTAKE_SCHEMA_M04.schema.json`
- `tools/validators/fork_intake_validator.py`
- `modules/m04_branch_registration/runner.py`
