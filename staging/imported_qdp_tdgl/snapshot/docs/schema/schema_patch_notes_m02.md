# QDP v10.6 M02 Schema Patch Notes
Version: 1.0  
Date: 2026-03-13  
Status: Working patch, not the final authoritative no-loss schema

## Scope

This patch addresses module **M02 â€” Schema extension and post-run validator**.

It patches the surfaced `config/schema/candidate_template.json` into a working v10.6-compatible template and adds a validator oriented around the v10.6 build-spec requirements that are already visible.

## Inputs used

- `specs/core/build_spec.md`
- `config/schema/candidate_template.json`
- `docs/repo/module_registry.md` / `.json`

## What changed

### 1. Added the v10.6 self-check extension

Added:
- `system_status`
- `governance_self_check.validation_harness_status`
- `governance_self_check.schema_validation_status`
- `governance_self_check.reference_resolution_status`
- `governance_self_check.determinism_status`
- `governance_self_check.system_status`

Default template values follow the visible v10.6 state initialization:
- self-check statuses default to `UNKNOWN`
- `system_status` defaults to `HARNESS_REQUIRED`
- `promotion_cap_governance` defaults to `SANDBOX_ONLY` for the surfaced template because harness status is initialized as `UNKNOWN`

### 2. Added explicit cross-device status

Added:
- top-level `cross_device_status`

Reason:
the current v8.2 template only exposed `cross_device_validation.status`, while the v10.6 build spec uses an explicit `cross_device_status` decision variable.

### 3. Added schema-level and validator-level mirror rule

The validator enforces:
- `system_status == governance_self_check.system_status`
- `cross_device_status == cross_device_validation.status` when both are populated

This resolves the alias ambiguity enough to keep M13 from remaining structurally undefined at the schema layer.

### 4. Added `failure_mode_library_hits`

Reason:
the v10.6 build spec explicitly appends `SCHEMA_VALIDATION_FAILURE` to `failure_mode_library_hits` on validation failure.

### 5. Added `calibration_validity_score`

Reason:
the v10.6 build spec replaces an undefined threshold with the explicit rule:
`calibration_validity_score < 70`

The retained v10.1 body that uses this score is not yet surfaced, so the field is included as a placeholder to prevent silent schema drift.

### 6. Added gate-trace item contract

The JSON Schema now specifies the machine-readable `gate_trace[]` entry shape expected by the visible v10.6 patch:
- `stage_id`
- `stage_name`
- `inputs_checked`
- `decision_or_cap_change`
- `key_evidence_ids`
- `status`
- `notes`

### 7. Added a post-run validator script

Artifacts:
- `config/schema/candidate_schema.json`
- `tools/validators/candidate_validator.py`

Validator modes:
- `template`: structural/schema validation for partially filled templates
- `final`: stricter post-run validation for final candidate outputs

The validator checks:
- required field presence
- self-check enum validity
- cross-device enum validity
- governance outcome enum validity
- top-level/nested status mirroring
- key build-spec consistency constraints

## What this patch does NOT solve

### 1. Full v10.1 enum closure is still missing

The v10.6 build spec says the authoritative runtime must retain the full v10.1 enum block. That body has not been surfaced as a file here.

Consequence:
- `scientific_decision` is only partially constrained
- root `additionalProperties` remains enabled for compatibility
- this patch is a **working guardrail**, not the final authoritative no-loss schema

### 2. Full M15 guardrail representation is not settled

The build spec references:
- calibration integrity gate
- drift ledger law
- parameter identifiability law
- dataset governance law
- failure mode library

Only part of that surface is visible in the currently uploaded artifacts.
This patch adds enough structure to avoid obvious drift, but it does not claim complete M15 closure.

### 3. Runtime semantics are still not implemented

This patch provides:
- data template updates
- schema validation
- post-run consistency checks

It does **not** provide:
- runtime execution
- harness runner
- stage logic
- mechanism tests
- artifact audit
- cross-device comparison engine

## Recommended next move after M02

Proceed to **M03 â€” Reference-resolution and governance-registry module**.

The reason is simple:
- M02 now reduces silent schema drift
- M03 is the next blocker in the registered implementation order
- the harness should not be trusted until reference resolution and registry state are explicit

## Artifact list

- `config/schema/candidate_template.json`
- `config/schema/candidate_schema.json`
- `tools/validators/candidate_validator.py`
