# QDP v10.6 M10 Patch Notes

## Scope

Visible-source working patch for M10 artifact-equivalence auditing.

## What this adds

- Adds `modules/m10_artifact_audit/runner.py` as a surfaced artifact-route scorer.
- Fills `artifact_tests` conservatively for:
  - `control_chain_distortion`
  - `readout_alias`
  - `calibration_drift`
  - `refrigerator_cycle_alias`
  - `power_calibration_alias`
- Sets `artifact_tests.route_explains_data` and `artifact_tests.explains_data` for M05 Stage 9 consumption.
- Emits `strongest_artifact_route_initial`, `strongest_artifact_route`, and parsimonious-combination fields inside `artifact_tests`.
- Adds a self-test pack and schema-valid emitted outputs.

## Visible-Source Limitation

This is a visible-source partial implementation. It uses surfaced artifact-elimination logic from `specs/research/deep_research_report.md` plus already-present candidate nuisance-control fields. It does not claim no-loss parity with unsurfaced retained runtime behavior, and it does not implement a structured intake adapter over `specs/intake/fork_intake_form_one_page.pdf`.

## Working-Patch Status

This patch should be treated as a working patch only, not as resume-authoritative or authoritative closure.
