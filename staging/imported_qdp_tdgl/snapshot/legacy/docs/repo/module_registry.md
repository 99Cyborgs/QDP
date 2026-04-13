# QDP v10.6 Module Registry
Version 1.0
Status: Pre-testing blocker map
Date: 2026-03-13

## Purpose

Define the full module stack that must exist before resuming testing under QDP v10.6.

This registry separates:

- core blockers required before ordinary candidate testing
- subsystem blockers required before any GKSL subsystem-emergence testing
- deferred non-blockers that matter later but do not block bootstrap or ordinary testing

## Resume-testing policy

### Ordinary QDP v10.6 candidate testing
Do not resume ordinary candidate testing until all core blocker modules M01-M15 exist and pass their acceptance gates.

### QDP v10.6 with subsystem-emergence claims enabled
Do not allow subsystem language, subsystem verdicts, or subsystem paper-facing outputs until all core blockers M01-M15 and all subsystem blockers S16-S19 exist and pass.

## Blocking classes

- CORE_BLOCKER: required before ordinary candidate testing
- SUBSYSTEM_BLOCKER: required before subsystem-emergence testing
- DEFERRED_NON_BLOCKER: useful later, but not required to restart testing

## Core blocker modules

| ID | Module | Blocker for | Primary purpose | Primary owner artifacts | Required status / output fields | Current artifact status |
|---|---|---|---|---|---|---|
| M01 | Runtime assembly and freeze | ordinary + subsystem | Compile executable `QDP_v10_6_RUNTIME_PROMPT` from retained v10.1 body plus v10.6 patches; forbid running build spec as live runtime | `specs/core/build_spec.md`; **missing** retained v10.1 operative body | `QDP_v10_6_RUNTIME_PROMPT` artifact; frozen build hash/version stamp | recovery artifact emitted; runtime intentionally not assembled; retained v10.1 body still missing |
| M02 | Schema extension and post-run validator | ordinary + subsystem | Patch candidate schema to v10.6 and fail closed on malformed output | `specs/core/build_spec.md`; `config/schema/candidate_template.json` | `system_status`; `governance_self_check.*`; enum validation; JSON presence validation; alias or explicit field for `cross_device_status` | schema template present but still v8.2-shaped |
| M03 | Reference-resolution and governance-registry module | ordinary + subsystem | Resolve critical references, register failures, and cap governance on unresolved dependencies | `specs/core/build_spec.md`; `specs/core/master_spec.md`; `specs/core/falsifier_registry.md`; **missing** retained federated governance registry object from v10.1 body | `reference_resolution_status`; `automatic_flags_triggered`; governance registry object; duplicate and reference tracking | working patch hardened; ordinary/subsystem summaries now explicit; strict failure remains on retained critical references |
| M04 | Fork intake and branch registration | ordinary + subsystem | Enforce pre-compute registration of branch identity, bath class, observables, constraints, and falsifier | `specs/intake/fork_intake_form_one_page.pdf`; `specs/intake/fork_questions.md`; `specs/core/master_spec.md` | branch metadata; bath class fields; observable fields; `exact_falsifier`; `relevant_nuisance_controls_list`; fork outcome label | source materials present; intake-to-runtime adapter missing |
| M05 | Gate-trace and validation-ladder state machine | ordinary + subsystem | Record machine-readable stage trace and explicit ladder assignments L0-L4 | `specs/core/build_spec.md`; `specs/core/validation_gate.md`; `config/schema/candidate_template.json` | `gate_trace[]`; `validation_ladder.*`; stage-by-stage cap changes; stage notes | working executable subset present with self-tests; authoritative no-loss closure still blocked by missing retained full stage body |
| M06 | Bootstrap harness runner and fixture loader | ordinary + subsystem | Execute five canonical harness cases and set deterministic readiness state | `specs/core/build_spec.md` | `validation_harness_status`; `determinism_status`; `system_status`; fixture manifests; expected-outcome matcher | harness runner, canonical fixtures, deterministic bootstrap report, and divergence report now exist; module closed, but environment still blocked by M01/M03/M07-M15 |
| M07 | Family-class triage and signature-to-bath scorer | ordinary + subsystem | Rank likely mechanism classes and choose minimal discriminant measurement before parameter expansion | `specs/core/bath_glossary.md`; `specs/core/signature_to_bath_decision_chart.md`; `config/schema/candidate_template.json` | `declared_family_class`; `assigned_family_class`; `family_class_mismatch`; `inferred_bath_rank_order`; `signature_matches`; `minimal_discriminant_measurement` | visible-source scorer, self-test pack, and schema-valid outputs now exist; working patch only and not resume-authoritative |
| M08 | Baseline GKSL fit and drift-aware residual diagnostics | ordinary + subsystem | Fit baseline Lindblad/GKSL null model jointly and test residual structure on time-series observables | `specs/core/model_spec.md`; `specs/research/deep_research_report.md`; `config/schema/candidate_template.json` | `baseline_model.*`; `residual_analysis.*`; drift-aware fit outputs; whiteness/stationarity diagnostics | visible-source baseline-fit runner, self-test pack, and schema-valid outputs now exist; working patch only and not resume-authoritative |
| M09 | Known-mechanism competition suite | ordinary + subsystem | Evaluate parsimonious physical mechanisms before Hamiltonian escalation | `specs/core/signature_to_bath_decision_chart.md`; `QDP_Vortex_Pinning_Microwave_Loss_Module.md`; `vortex_entry_barrier.md`; `vortex_entry_calculator.md`; `vortex_microwave_dissipation.md`; `residual_field_estimation_dilution_fridge.md`; `config/schema/candidate_template.json` | `mechanism_tests.*`; `strongest_competing_mechanism`; mechanism score updates; rejection mapping if explained | visible-source partial mechanism suite, self-test pack, and schema-valid outputs now exist; working patch only and not resume-authoritative |
| M10 | Artifact-equivalence audit | ordinary + subsystem | Eliminate classical/systematic explanations distinct from physical mechanisms | `specs/research/deep_research_report.md`; `specs/intake/fork_intake_form_one_page.pdf`; `config/schema/candidate_template.json` | `artifact_tests`; artifact alias summary; rejection mapping if artifact route explains data | visible-source artifact-audit runner, self-test pack, and schema-valid outputs now exist; working patch only and not resume-authoritative |
| M11 | Lindblad-equivalence gate | ordinary + subsystem | Reject branches equivalent to Lindblad dynamics within measurement resolution | `specs/core/build_spec.md`; `config/schema/candidate_template.json` | `lindblad_equivalence.equivalent_within_resolution`; `best_equivalent_model`; rejection state mapping | schema fields present; decision engine missing |
| M12 | Executable falsifier and experiment-design module | ordinary + subsystem | Emit experiment package that satisfies Experimental Design Law and instrument-facing falsifier requirement | `specs/core/falsifier_registry.md`; `specs/intake/fork_intake_form_one_page.pdf`; `specs/core/validation_gate.md`; `specs/research/deep_research_report.md` | `exact_falsifier`; `hamiltonian_test.*`; `experiment_schedule.*`; `requested_output_artifacts`; executable measurement plan | registry and intake sources present; executable planner missing |
| M13 | Cross-device evidence gate | ordinary + subsystem | Prevent `PROCEED` without matched cross-device confirmation | `specs/core/build_spec.md`; `config/schema/candidate_template.json`; `specs/research/deep_research_report.md` | explicit `cross_device_status` or exact alias; `cross_device_validation.*`; geometry-fabrication confound checks | build logic present; schema alias unresolved; implementation missing |
| M14 | Promotion-cap clipping and fallback completion | ordinary + subsystem | Enforce irreversible cap lowering and deterministic final completion | `specs/core/build_spec.md`; `config/schema/candidate_template.json` | `promotion_cap_governance`; `promotion_cap_scientific`; clipped `governance_outcome`; fallback-completed `scientific_decision` | logic present in spec; executable cap manager missing |
| M15 | Calibration, drift, identifiability, and dataset-governance guardrails | ordinary + subsystem | Enforce calibration integrity, drift ledger, parameter identifiability, and dataset governance before interpretation | `specs/core/build_spec.md`; `specs/research/deep_research_report.md`; **missing** retained v10.1 body sections named in build spec | calibration validity outputs; identifiability status; drift ledger; failure-mode hits; dataset governance checks | declared as mandatory retained body; concrete module not surfaced |

## Subsystem blocker modules

| ID | Module | Blocker for | Primary purpose | Primary owner artifacts | Required status / output fields | Current artifact status |
|---|---|---|---|---|---|---|
| S16 | GKSL subsystem audit core | subsystem only | Evaluate whether a slow GKSL sector justifies subsystem-emergence language | **missing** `gksl_subsystem_audit_v1.md`; `specs/subsystem/gksl_subsystem_case_matrix.json` | `theorem_status`; `corollary_status`; `simulation_validation_status`; `null_audit_status`; `real_data_verdict` | case matrix exists; core runtime prompt missing |
| S17 | Subsystem stability / closure / finite-horizon control | subsystem only | Veto subsystem claims unless projector stability, finite-horizon control, and observable closure are acceptable | **missing** `gksl_subsystem_decision_patch.md`; `specs/subsystem/gksl_subsystem_case_matrix.json` | `projector_stability_status`; `finite_horizon_control_status`; `observable_closure_status`; `symmetry_alias_status`; `artifact_alias_status`; `identifiability_status` | design exists in prose only; no frozen artifact file uploaded |
| S18 | Subsystem adversarial/null harness | subsystem only | Stress-test subsystem detector against false positives and require one true-positive control | `specs/subsystem/gksl_subsystem_case_matrix.json`; **missing** `gksl_subsystem_harness_spec.md` | adversarial acceptance summary; case-level verdict matrix; pass/fail harness status | case matrix present; fixture pack and runner missing |
| S19 | Subsystem intake and schema adapter | subsystem only | Bind subsystem branch outputs back into ordinary QDP candidate governance | **missing** `gksl_subsystem_branch_intake.json`; `config/schema/candidate_template.json`; `specs/intake/fork_intake_form_one_page.pdf` | subsystem branch metadata; bath ranking; closure targets; publication claim cap; adapter to core QDP fields | missing |

## Deferred non-blockers

| ID | Module | Why deferred | Owner artifacts |
|---|---|---|---|
| D20 | Subsystem publication gate | matters only after theorem/simulation/real-data outputs exist; not required to restart testing | **missing** `gksl_subsystem_publication_gate.md` |
| D21 | Module registry machine-readable export maintenance | useful for automation and CI but not required for first resumed test cycle | this registry JSON export |

## Hard stop conditions before testing resumes

1. If M01 is incomplete, there is no executable runtime.
2. If M02 is incomplete, schema drift can silently invalidate runs.
3. If M06 is incomplete or failing, ordinary testing remains capped because `system_status` stays `HARNESS_REQUIRED` or becomes `GOVERNANCE_LOGIC_FAILURE`.
4. If M13 is incomplete, nothing may clear into true cross-device proceed status.
5. If subsystem language is allowed while S16-S19 are incomplete, false-positive risk is structurally high.

## Schema drift already visible from current artifacts

The current template already exposes several useful fields, including `validation_ladder`, `baseline_model`, `residual_analysis`, `mechanism_tests`, `artifact_tests`, `lindblad_equivalence`, `cross_device_validation`, and `gate_trace`.

But the v10.6 build spec requires additional fields or stricter mappings that are not visible in the current v8.2 template, including:

- `system_status`
- `governance_self_check`
- typed self-check enums
- an explicit or exact-aliased `cross_device_status`
- any additional fields needed to represent retained v10.1 governance sections now required by the build spec

This drift must be patched before ordinary testing resumes.

## Recommended implementation order

1. M01 Runtime assembly and freeze
2. M02 Schema extension and validator
3. M03 Reference-resolution and governance registry
4. M04 Fork intake and branch registration
5. M05 Gate-trace and ladder state machine
6. M06 Bootstrap harness runner and fixtures
7. M07 Family-class triage
8. M08 Baseline GKSL fit and residual diagnostics
9. M09 Mechanism competition suite
10. M10 Artifact-equivalence audit
11. M11 Lindblad-equivalence gate
12. M12 Executable falsifier and experiment-design module
13. M13 Cross-device evidence gate
14. M14 Promotion-cap clipping and fallback completion
15. M15 Calibration / drift / identifiability / dataset-governance guardrails
16. S16-S19 only if subsystem testing is in scope

## Resume authorization rule

Resume ordinary candidate testing only when:

- all M01-M15 exist
- bootstrap harness passes exactly
- schema patch is applied and validated
- cross-device gate is represented unambiguously in schema and runtime

Resume subsystem testing only when:

- all M01-M15 exist and pass
- all S16-S19 exist and pass
- adversarial subsystem harness never returns `supported` on adversarial cases
- true-positive subsystem control returns `supported`
