# Implementation backlog

## Milestone M0 — scaffold
- [ ] Create repository layout from `docs/04_software_architecture.md`
- [ ] Implement config schema validation
- [ ] Implement recursive base-config loading
- [ ] Implement matrix-row override expansion
- [ ] Implement run-directory creation and provenance writing
- [ ] Add CLI entry points
- [ ] Add smoke tests for config loading and CLI

## Milestone M1 — deterministic core
- [ ] Mesh object with masks and geometry helpers
- [ ] Prescribed forcing profiles
- [ ] Link-variable builder
- [ ] Covariant Laplacian operator
- [ ] Current calculators
- [ ] Scalar-potential solve
- [ ] IMEX stepper
- [ ] Deterministic observable extraction
- [ ] Unit tests for kernels
- [ ] D01 benchmark

## Milestone M2 — deterministic V&V
- [ ] Seeded-vortex generator
- [ ] Vortex map extraction
- [ ] Vortex trajectory tracker
- [ ] Convergence workflow
- [ ] D02 benchmark
- [ ] D03 benchmark
- [ ] D04 / D05 geometry mask benchmarks
- [ ] D06 trajectory figure case
- [ ] Generate figures 1 and 2
- [ ] Mark Gate G1 status

## Milestone M3 — stochastic layer
- [ ] Deterministic seed derivation utility
- [ ] Additive noise sampler
- [ ] Ensemble runner
- [ ] Event-table writer
- [ ] Noise moment tests
- [ ] S01 benchmark
- [ ] S02 benchmark
- [ ] S03–S08 matrix rows
- [ ] Generate figure 3
- [ ] Mark Gate G2 status

## Milestone M4 — inverse workflow
- [ ] Synthetic data generator
- [ ] Summary-statistic builder
- [ ] Prior objects
- [ ] Gaussian likelihood
- [ ] MAP estimation
- [ ] Local uncertainty approximation
- [ ] Posterior predictive workflow
- [ ] I01–I04 matrix rows
- [ ] Generate figure 4
- [ ] Mark Gate G3 status

## Milestone M5 — performance
- [ ] Timing/profiling hooks
- [ ] Strong-scaling workflow
- [ ] Weak-scaling workflow
- [ ] Ensemble-throughput workflow
- [ ] P01–P04 matrix rows
- [ ] Scaling plots
- [ ] Projected workload table

## Milestone M6 — packaging
- [ ] Summarize all gates
- [ ] Emit campaign summary report
- [ ] Ensure all figures exist
- [ ] Freeze final configs and manifest
- [ ] Write concise implementation report
