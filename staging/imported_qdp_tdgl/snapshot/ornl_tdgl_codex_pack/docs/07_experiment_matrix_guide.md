# 07. Experiment matrix guide

## 7.1 Purpose
`matrices/experiment_matrix.csv` defines the first campaign. It is the control surface for:
- verification,
- rare-event discovery,
- synthetic inverse studies,
- early scaling runs.

The matrix is deliberately explicit so Codex does not need to infer campaign structure.

## 7.2 Phases
The matrix is divided into four phases.

### Phase D — deterministic verification
Goal:
- establish solver correctness and convergence.

### Phase S — stochastic rare-event discovery
Goal:
- identify regimes where event statistics are informative.

### Phase I — inference
Goal:
- generate synthetic datasets and recover low-dimensional truth.

### Phase P — performance / scaling
Goal:
- test ensemble orchestration and decomposition strategy.

## 7.3 Required matrix columns
- `case_id`
- `phase`
- `base_config`
- `geometry_family`
- `nx`
- `ny`
- `pinning_model`
- `pinning_mu`
- `pinning_sigma`
- `pinning_lcorr`
- `defect_count`
- `b_dc`
- `a_rf`
- `omega`
- `gamma_noise`
- `dt`
- `n_steps`
- `ensemble_size`
- `obs_stride`
- `field_stride`
- `goal`
- `success_metric`
- `promotion_rule`
- `notes`

## 7.4 Matrix semantics
A matrix row is not a full config. It is a set of overrides applied to `base_config`.

Codex must implement:
1. base-config load,
2. row override application,
3. config validation,
4. run-directory expansion.

## 7.5 Promotion rules
Every row includes a `promotion_rule`, for example:
- `gate:G1`
- `gate:G2`
- `proposal:figure2`
- `scale:pilot`

Codex should preserve this metadata in run summaries so campaign progress can be tracked automatically.

## 7.6 Campaign usage
Suggested execution order:
1. run all phase D rows,
2. only after G1 passes, run phase S,
3. only after G2 passes, run phase I,
4. run phase P in parallel as infrastructure allows.

## 7.7 Notes on ensemble sizes
Early stochastic rows use small ensembles (`16`–`64`) to discover regimes.
Proposal-facing rows should increase to `128`–`512` where feasible.

## 7.8 Data reduction policy
For large campaigns:
- store full fields sparsely,
- store reduced observables densely,
- aggregate campaign summaries at the end of each phase.

## 7.9 Human review points
Review manually after:
- D04,
- S04,
- I02,
- P02.

Those are the intended checkpoints for deciding whether the physics, inverse problem, and performance story are on track.
