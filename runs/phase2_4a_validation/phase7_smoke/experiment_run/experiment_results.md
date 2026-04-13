# Seeded-Vortex Experiment Harness

- Pack name: `seeded_vortex_phase2_4a_experiment_pack`
- Mode: `stochastic_ensemble`
- Manifest: `G:\GitHub\incubate\QDP\configs\validation\tdgl\seeded_vortex_phase2_4a_experiment_pack.yaml`
- Base case: `G:\GitHub\incubate\QDP\configs\validation\tdgl\seeded_vortex\short_horizon\canonical_single_positive_stochastic.yaml`
- Overall status: `success`
- Ensemble members per parameter point: `3`
- Parameter points: `2`

## Interpretation Boundary

Stochastic same-stack ensemble aggregation of committed seeded initialization / short-horizon Tier-2 observables only.

- `equilibrium_preparation`: not established by this ensemble harness
- `long_time_dynamics`: not established by this ensemble harness
- `cross_stack_portability`: not established by this ensemble harness

## Parameter Points

| param_set_hash | case_class | status | successful runs | parameters | notes |
| --- | --- | --- | ---: | --- | --- |
| 22c77fcc8895b7c6 | short_horizon | success | 3/3 | forcing.a_rf=0.0 | aggregated stochastic same-stack Tier-2 observables |
| 7e25b35f64dc7088 | short_horizon | success | 3/3 | forcing.a_rf=0.05 | aggregated stochastic same-stack Tier-2 observables |

## Aggregated Observables

| param_set_hash | observable | classification | aggregates |
| --- | --- | --- | --- |
| 22c77fcc8895b7c6 | early_window.mean_abs2_final | early_window_observable | mean=0.9877432798444367, std=0.005803130880937511, min=0.9809600057230531, max=0.9951355276307005 |
| 7e25b35f64dc7088 | early_window.mean_abs2_final | early_window_observable | mean=0.9934805444797786, std=0.0037935897738098747, min=0.989072861339504, max=0.998333203155557 |

## Ensemble Robustness Summary

| param_set_hash | failure_rate | observable | coefficient_of_variation | cv_defined | sign_consistency |
| --- | ---: | --- | ---: | --- | ---: |
| 22c77fcc8895b7c6 | 0.0 | early_window.mean_abs2_final | 0.005875140838064186 | True | 1.0 |
| 7e25b35f64dc7088 | 0.0 | early_window.mean_abs2_final | 0.0038184842117832633 | True | 1.0 |
