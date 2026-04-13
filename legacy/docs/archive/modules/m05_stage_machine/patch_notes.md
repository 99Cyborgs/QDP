# QDP v10.6 M05 Patch Notes
Version: 1.0  
Date: 2026-03-14  
Status: WORKING_PATCH

## Scope

This patch implements the scoped **M05 gate-trace and validation-ladder state machine** only.
It is a working executable subset for the visible v10.6 rules and does **not** claim authoritative closure.

## Artifacts created

- `modules/m05_stage_machine/runner.py`
- `modules/m05_stage_machine/selftest_cases.json`
- `artifacts/reports/m05/selftest_report.json`
- `QDP_v10_6_M05_PATCH_NOTES.md`
- `QDP_v10_6_M05_SELFTEST_OUTPUTS/`

## Interim trigger mapping used for the executable subset

The retained full runtime body is still missing, so M05 uses a small conservative trigger table based only on surfaced fields plus helper flags under existing permissive objects.

- Baseline pipeline executed:
  `baseline_model.status` in `EXECUTED_SUCCESSFULLY | BASELINE_PIPELINE_EXECUTED | PASSED | REPRODUCED`, or `baseline_model.pipeline_executed = true`
- Baseline sufficiency:
  `validation_ladder.L0_baseline_pipeline_reproduced = true` plus `residual_analysis.white_residuals = true`, `residual_analysis.stationary_residuals = true`, `residual_analysis.structured_residuals = false`, `residual_analysis.cross_observable_correlations_vanish = true`, and `residual_analysis.drift_aware_fit_applied = true`
- Classical mechanism explains data:
  `mechanism_tests.explains_data = true`, `mechanism_tests.parsimonious_combination_explains = true`, or any nested `mechanism_tests.<name>.explains_data = true`
- Artifact route explains data:
  `artifact_tests.route_explains_data = true` or `artifact_tests.explains_data = true`
- Convergence plan declared:
  `hamiltonian_test.convergence_plan_declared = true` or `hamiltonian_test.plan_declared_before_nonlinear_sweeps = true`
- Reduction limit verified:
  non-empty `reduction_limit` plus `baseline_model.reduction_limit_verified = true` or `baseline_model.reduction_limit_test_passed = true`
- Lindblad equivalence within measurement resolution:
  `lindblad_equivalence.equivalent_within_resolution = true`
- Numerical stability passed:
  `numerical_stability.stable = true` and `numerical_stability.failed_checks` empty
- Instrument-facing path defined:
  non-empty `exact_falsifier`, an emitted falsifier package via `experiment_schedule.executable_falsifier_package_emitted = true` or `requested_output_artifacts` containing `EXECUTABLE_FALSIFIER_PACKAGE`, and an instrument-facing experiment via non-empty `experiment_schedule.priority_experiments` plus `instrument_capabilities.instrument_facing_requirement_satisfied = true`
- Cross-device mapping:
  `multi_device_data_available = false` -> `SCHEDULED`
  geometry-claimed discriminator with `fabrication_matched_for_geometry_claim = false` -> `CONFUNDED`
  otherwise `cross_device_validation.status` or `cross_device_validation.consistency_class` maps to `DEVICE_SPECIFIC | INCONSISTENT | CONFIRMED`

For deterministic harnessing, `modules/m05_stage_machine/runner.py` also accepts explicit `stage_inputs` overrides. Those overrides do not replace the documented candidate-field trigger table; they only expose surfaced stage findings directly for harness use.

## Visible rules implemented verbatim

Implemented exactly as surfaced in the M05 implementation pack and local M05 contracts:

- Governance pre-check cap forcing and conservative termination for `GOVERNANCE_LOGIC_FAILURE` and `REFERENCE_RESOLUTION_FAILURE`
- Stage 5 -> L0 assignment
- Stage 6 -> baseline sufficiency rejection mapping
- Stage 8 -> classical mechanism rejection mapping
- Stage 9 -> artifact equivalence rejection mapping
- Stage 10 -> convergence-plan gate, reduction-limit gate, and conservative termination behavior
- Stage 11 -> Lindblad-equivalence rejection mapping
- Stage 13 -> numerical-stability gate and `NUMERICALLY_UNSTABLE` termination behavior
- Stage 14 -> provisional identifiability assignment
- Stage 15 visible L4 rule only
- Stage 16 cross-device status mapping and sandbox cap forcing for scheduled/confounded cases
- Stage 17 raw proceed gate
- Final clipping rule
- Fallback completion rule
- Post-run final-mode schema validation

Every visible stage appends a machine-readable `gate_trace` entry with the schema-required fields, including explicit `SKIPPED` entries after termination.

## What remains blocked

- The retained v10.1 operative body is still missing, so the visible stage machine cannot claim no-loss parity with the authoritative runtime.
- The retained federated governance registry object is still missing, so authoritative governance binding remains blocked.
- `specs/core/build_spec.md`, `specs/core/master_spec.md`, `specs/core/validation_gate.md`, `specs/intake/fork_questions.md`, and `specs/core/falsifier_registry.md` were referenced by prior M03 artifacts but are not surfaced in this workspace snapshot; this patch therefore implements only the visible rules restated in the current pack, schema, validator, closure contracts, and rule-binding registry.
- M05 therefore qualifies as `WORKING_PATCH`, not `AUTHORITATIVE_CLOSURE`.

## Commands run

Because `python` was not on `PATH` in this PowerShell session, the local interpreter was invoked explicitly.

```powershell
& 'C:\Users\Forre\AppData\Local\Python\pythoncore-3.14-64\python.exe' modules/m05_stage_machine/runner.py --selftest --write-report artifacts/reports/m05/selftest_report.json
```

```powershell
$files = Get-ChildItem 'QDP_v10_6_M05_SELFTEST_OUTPUTS' -Recurse -Filter '*_candidate.json' | Sort-Object FullName
foreach ($file in $files) {
  & 'C:\Users\Forre\AppData\Local\Python\pythoncore-3.14-64\python.exe' tools/validators/candidate_validator.py $file.FullName --mode final
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

## Results

- Self-test cases: 6
- Self-test cases passed: 6
- `all_passed`: true
- Standalone final-mode schema validation over every emitted candidate output: passed for all 6 cases
- Resulting M05 status: `WORKING_PATCH`

## Notes

- Planning fields are intentionally not conflated with passed states. In particular, Stage 13 only sets `validation_ladder.L3_numerical_stability_passed = true` from an explicit surfaced pass condition, not from planning text.
- The stage machine remains compatible with the existing M06 harness hooks by exposing `make_minimal_final_candidate`, `deep_merge`, `run_state_machine`, `validate_candidate_with_existing_validator`, and `compare_expected`.
