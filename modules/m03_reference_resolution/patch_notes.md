# QDP v10.6 M03 Reference-Resolution and Governance-Registry Patch Notes
Version: 1.0  
Date: 2026-03-13  
Status: Working patch, not the final authoritative retained registry object

## Scope

This patch addresses **M03 â€” Reference-resolution and governance-registry module**.

It adds a working reference manifest, a surrogate governance registry object, and a resolver that can:

- verify presence of critical reference artifacts in the current environment
- emit a machine-readable reference-resolution report
- patch candidate JSON objects with `reference_resolution_status`, `system_status`, and unresolved-reference flags
- perform basic duplicate checks against the working registry

## Inputs used

- `specs/core/build_spec.md`
- `specs/core/master_spec.md`
- `specs/core/falsifier_registry.md`
- `specs/core/model_spec.md`
- `specs/intake/fork_questions.md`
- `specs/core/validation_gate.md`
- `specs/core/bath_glossary.md`
- `specs/core/signature_to_bath_decision_chart.md`
- `specs/intake/fork_intake_form_one_page.pdf`
- `config/schema/candidate_template.json`
- `config/schema/candidate_schema.json`
- `tools/validators/candidate_validator.py`
- `config/registries/module_registry.json`

## What changed

### 1. Added a strict reference manifest

Artifact:
- `config/manifests/reference_manifest.json`

The manifest classifies each reference by:

- role
- criticality
- required or optional status
- ordinary vs subsystem mode relevance
- relative path under `/mnt/data`

It also encodes the strict rule inherited from the visible build spec:

- if all critical references resolve, `reference_resolution_status = PASSED`
- if any critical reference is missing, `reference_resolution_status = FAILED`, `system_status = REFERENCE_RESOLUTION_FAILURE`, `promotion_cap_governance = SANDBOX_ONLY`, and `REFERENCE_UNRESOLVED:<ref_id>` flags are emitted

### 2. Added a surrogate governance registry object

Artifact:
- `config/registries/governance_registry.json`

This object is a working registry snapshot for blocker tracking. It includes:

- canonical reference snapshot with hashes when available
- baseline model registry entry for `H0_BASELINE_LINDBLAD`
- falsifier registry snapshot for the baseline entry
- placeholder failure-mode library entries relevant to current surfaced artifacts
- duplicate detection rules
- placeholder aging and override policies

### 3. Added an executable resolver

Artifact:
- `modules/m03_reference_resolution/runner.py`

The resolver can emit:

- a machine-readable reference-resolution report
- an optionally patched candidate JSON object

Candidate patch behavior:

- sets `governance_self_check.reference_resolution_status`
- sets `system_status` to `REFERENCE_RESOLUTION_FAILURE` when critical references are missing
- appends unresolved-reference automatic flags
- applies `promotion_cap_governance = SANDBOX_ONLY` on failure
- performs exact duplicate checks against the working registry

### 4. Added a current-environment resolution report

Artifact:
- `artifacts/reports/m03/reference_resolution_ordinary.json`

This report shows the strict current state of the environment.

At present, strict reference resolution fails because the following retained objects are still not surfaced as files:

- `RETAINED_V10_1_OPERATIVE_BODY`
- `RETAINED_FEDERATED_GOVERNANCE_REGISTRY_OBJECT`

That result is expected and consistent with the current blocker map.

## What this patch does NOT solve

### 1. It does not recreate the retained v10.1 body

The build spec says the authoritative v10.6 runtime requires the full retained v10.1 operative body. That file is still absent.

### 2. It does not recreate the final retained federated governance registry object

The module registry explicitly marks that retained registry object as missing. The new M03 registry is a surrogate, not a substitute.

### 3. It does not clear testing

Because strict reference resolution still fails in the current environment, M03 does not clear the testing blocker stack.

## Recommended next move after M03

Proceed to **M04 â€” Fork intake and branch registration** for implementation work, while separately recovering the missing retained v10.1 operative body and the retained federated governance registry object needed for strict M03 success.

## Artifact list

- `config/manifests/reference_manifest.json`
- `config/registries/governance_registry.json`
- `modules/m03_reference_resolution/runner.py`
- `artifacts/reports/m03/reference_resolution_ordinary.json`
