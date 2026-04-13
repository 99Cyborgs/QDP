# Phase-2.4A Same-Stack Validation

This report validates the committed fixed-seed Phase-2.4A ensemble pack as a same-stack runtime/control-plane surface only.
It freezes member identity, selected replay metadata, aggregate observables, and robustness summaries.

- Validation manifest: `G:\GitHub\incubate\QDP\configs\validation\tdgl\seeded_vortex_phase2_4a_validation_manifest.yaml`
- Experiment pack: `G:\GitHub\incubate\QDP\configs\validation\tdgl\seeded_vortex_phase2_4a_experiment_pack.yaml`
- Overall status: `success`
- Parameter points: `2`
- Members: `6`
- Mismatch count: `0`

## Boundary

- Claim scope: Same-stack fixed-seed runtime/control-plane validation of the committed Phase-2.4A seeded-vortex ensemble pack only.
- scientific robustness: not established by this validation surface
- long time dynamics: not established by this validation surface
- cross stack portability: not established by this validation surface

## Cases

| surface | subject_id | pass | mismatch_count | notes |
| --- | --- | --- | ---: | --- |
| top_level | overall | yes | 0 | matched frozen top-level aggregate surface |
| parameter_point | 22c77fcc8895b7c6 | yes | 0 | matched frozen parameter-point surface |
| parameter_point | 7e25b35f64dc7088 | yes | 0 | matched frozen parameter-point surface |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m0 | yes | 0 | matched frozen member surface |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m1 | yes | 0 | matched frozen member surface |
| member | seeded_vortex_phase2_4a_experiment_pack__22c77fcc8895b7c6__m2 | yes | 0 | matched frozen member surface |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m0 | yes | 0 | matched frozen member surface |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m1 | yes | 0 | matched frozen member surface |
| member | seeded_vortex_phase2_4a_experiment_pack__7e25b35f64dc7088__m2 | yes | 0 | matched frozen member surface |
