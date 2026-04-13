# QDP v10.6 Module Registry
Version 2.0
Date: 2026-04-13

## Purpose

Generated core-module registry for M01-M15 from canonical repo metadata and live closure evaluation.
Verification evidence is module-specific: selftest-backed modules publish selftest reports, M01 publishes assembly plus closure reports, M03 publishes strict reference-resolution reports, and M06 publishes bootstrap-harness evidence.

## Readiness

- ordinary_recovery_ready: true
- ordinary_authoritative_ready: true
- ordinary_testing_ready: true
- subsystem_recovery_ready: true
- subsystem_authoritative_ready: true
- subsystem_testing_ready: true

## Resume-testing policy

### Ordinary candidate testing
Do not resume ordinary candidate testing until the required core modules are closure-complete under the active policy.

### Authoritative lane
Do not claim authoritative readiness until retained-source-dependent modules clear without unresolved surrogate provenance and visible-source modules have explicit authoritative bindings.

### Subsystem lane
Subsystem readiness is reported independently from the ordinary lane and only aliases subsystem_testing_ready when authoritative requirements are met.

## Modules

| ID | Module | Purpose | Required outputs | Current derived status |
|---|---|---|---|---|
| M01 | Runtime assembly and freeze | Assemble the execution-bearing runtime and capture retained-source provenance. | runtime_prompt; closure_report; provenance_metadata | AUTHORITATIVE_CLOSURE |
| M02 | Schema extension and post-run validator | Own the v10.6 candidate contract and final-mode validator semantics. | schema; template; typed_governance_fields; validator_semantics | AUTHORITATIVE_CLOSURE |
| M03 | Reference-resolution and governance-registry module | Resolve critical references and federate reference state into governance artifacts. | reference_resolution_status; governance_registry; mode_reports | AUTHORITATIVE_CLOSURE |
| M04 | Fork intake and branch registration | Map intake artifacts into canonical candidate objects before compute stages. | branch_registration; candidate_from_intake; precompute_flags | AUTHORITATIVE_CLOSURE |
| M05 | Gate-trace and validation-ladder state machine | Orchestrate gate stages and emit deterministic gate_trace and validation_ladder outputs. | gate_trace; validation_ladder; governance_outcome; scientific_decision | AUTHORITATIVE_CLOSURE |
| M06 | Bootstrap harness runner and fixture loader | Refresh core reports, selftests, bootstrap fixtures, and readiness evaluation. | bootstrap_report; closure_evaluation; readiness_flags; run_ledger | AUTHORITATIVE_CLOSURE |
| M07 | Family-class triage and signature-to-bath scorer | Assign family class, bath ranking, and minimal discriminant measurement. | assigned_family_class; inferred_bath_rank_order; signature_matches | AUTHORITATIVE_CLOSURE |
| M08 | Baseline GKSL fit and drift-aware residual diagnostics | Populate baseline_model and residual_analysis from the visible-source baseline contract. | baseline_model; residual_analysis | AUTHORITATIVE_CLOSURE |
| M09 | Known-mechanism competition suite | Score known mechanisms before Hamiltonian escalation. | mechanism_tests; strongest_competing_mechanism | AUTHORITATIVE_CLOSURE |
| M10 | Artifact-equivalence audit | Eliminate classical and systematic artifact routes before promotion. | artifact_tests | AUTHORITATIVE_CLOSURE |
| M11 | Lindblad-equivalence gate | Evaluate whether the candidate remains equivalent within measurement resolution. | lindblad_equivalence | AUTHORITATIVE_CLOSURE |
| M12 | Executable falsifier and experiment-design module | Build executable falsifier packs and instrument-facing experiment schedules. | exact_falsifier; hamiltonian_test; experiment_schedule | AUTHORITATIVE_CLOSURE |
| M13 | Cross-device evidence gate | Normalize cross-device status and enforce matched-fabrication confirmation rules. | cross_device_status; cross_device_validation | AUTHORITATIVE_CLOSURE |
| M14 | Promotion-cap clipping and fallback completion | Apply irreversible governance and scientific caps plus deterministic fallback completion. | promotion_cap_governance; promotion_cap_scientific; governance_outcome | AUTHORITATIVE_CLOSURE |
| M15 | Calibration, drift, identifiability, and dataset-governance guardrails | Populate typed governance guardrails and block promotion on calibration or provenance failures. | calibration_status; drift_ledger; identifiability_status; dataset_governance | AUTHORITATIVE_CLOSURE |
| S16 | Subsystem slow-sector detection | Detect candidate slow sectors and projector stability from the surfaced GKSL subsystem case matrix. | slow_sector_detected; projector_stability; diagnostic_report | AUTHORITATIVE_CLOSURE |
| S17 | Subsystem alias and null-baseline audit | Evaluate symmetry, artifact, TLS, and null-baseline alias routes for subsystem claims. | symmetry_alias_rejection; artifact_alias_rejection; null_baseline_rejection | AUTHORITATIVE_CLOSURE |
| S18 | Subsystem finite-horizon and closure gate | Check finite-horizon control and observable closure requirements before subsystem promotion. | finite_horizon_control; observable_closure; closure_metrics | AUTHORITATIVE_CLOSURE |
| S19 | Subsystem verdict gate | Aggregate surfaced subsystem gates into supported, inconclusive, or not_supported verdicts. | subsystem_verdict; verdict_report | AUTHORITATIVE_CLOSURE |

## Next phase

Subsystem modules S16-S19 remain governed by the live readiness predicates in this registry; surfaced-source origin alone does not decide authoritative status once explicit bindings are recorded.
