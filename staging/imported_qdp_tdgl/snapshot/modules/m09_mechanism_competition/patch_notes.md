# QDP v10.6 M09 Patch Notes

## Scope

This patch adds a visible-source executable subset for M09: known-mechanism
competition before Hamiltonian escalation.

## Added artifacts

- `modules/m09_mechanism_competition/runner.py`
- `modules/m09_mechanism_competition/selftest_cases.json`
- `artifacts/reports/m09/selftest_report.json`
- `QDP_v10_6_M09_SELFTEST_OUTPUTS/`

## Implementation notes

- The runner uses only the surfaced mechanism references currently available in
  this workspace:
  `specs/core/signature_to_bath_decision_chart.md`,
  `specs/research/vortex_pinning_methods.md`, and
  `specs/research/deep_research_report.md`.
- It fills `mechanism_tests.*`,
  `strongest_competing_mechanism_initial`, and
  `strongest_competing_mechanism`.
- It can positively explain data for strong surfaced signatures such as TLS
  saturation, vortex hysteresis / depinning, quasiparticle parity-style
  evidence, control-noise spectroscopy, and coherent parasitic mode evidence.
- Missing listed owner artifacts are recorded explicitly under
  `mechanism_tests.missing_owner_artifacts`.

## Limitations

- This is a visible-source working patch, not authoritative closure.
- Several M09 owner artifacts named in the module registry are still absent, so
  the suite is intentionally partial.
- Ambiguous phonon or global-bath style evidence is kept in supporting-only mode
  unless a surfaced discriminator is explicitly present.
