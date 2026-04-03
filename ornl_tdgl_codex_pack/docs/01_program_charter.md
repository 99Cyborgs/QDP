# 01. Program charter

## Project name
**Exascale-ready stochastic TDGL-RF experiment platform for vortex-mediated rare-event inference**

## Core scientific question
Can a vortex-resolved, stochastic thin-film TDGL model driven by a device-specific RF mode explain observed jump/loss phenomenology in superconducting structures, and can Bayesian inversion recover the hidden pinning and noise parameters that control those events?

## Working hypothesis
Rare dissipative events are set by the interaction of:
1. RF current concentration,
2. static trapped-flux or bias-field conditions,
3. heterogeneous pinning landscapes,
4. stochastic forcing.

If this is correct, then a calibrated stochastic TDGL model should reproduce:
- abrupt changes in reduced observables,
- nontrivial event waiting-time distributions,
- strong sensitivity to geometry and pinning hyperparameters,
- posterior concentration over a low-dimensional latent parameter vector.

## Baseline/null models to test against
The proposal must not be framed as "vortices must be the answer." v1 should preserve explicit nulls:

### Null A: smooth non-vortex dissipation
A phenomenological loss model with continuous parameter drift and no topological events explains the data as well as the vortex model.

### Null B: deterministic-only vortex dynamics
A purely deterministic vortex model reproduces the target observables without stochastic forcing.

### Null C: non-identifiable latent structure
Multiple pinning/noise settings reproduce the same observables, preventing meaningful inversion.

## v1 scope
This pack defines **v1 only**.

### In scope
- 2D thin-film TDGL in nondimensional form
- prescribed static and RF vector-potential fields
- insulating boundaries and optional lead segments
- parametric or random-field pinning landscapes
- additive complex Gaussian forcing in the TDGL equation
- reduced observable extraction:
  - vortex count / trajectories / crossings
  - frequency-shift proxy
  - dissipation proxy
  - jump and waiting-time statistics
- synthetic data generation
- low-dimensional Bayesian inversion over hyperparameters
- structured Cartesian grids
- gauge-invariant link-variable finite differences
- IMEX time stepping
- HDF5-based outputs
- campaign orchestration from CSV/YAML

### Out of scope
- full 3D electromagnetics
- self-consistent Maxwell coupling
- full-chip or package-level co-simulation
- microscopic superconductivity models beyond TDGL
- laboratory DAQ integration
- experimental metadata ingestion
- neural surrogates
- topology optimization
- AMR beyond simple block-refinement placeholders
- MFEM / finite-element implementation in v1

## Primary deliverables
1. Deterministic forward solver for 2D TDGL with prescribed RF mode.
2. Stochastic extension and rare-event statistics.
3. Observation operator from fields to reduced measurable proxies.
4. Synthetic inverse workflow over low-dimensional parameters.
5. Experiment runner using matrix-defined campaigns.
6. Proposal-grade figures and summary tables.
7. Performance and scaling evidence sufficient for a DD-style readiness narrative.

## Success criteria

### Scientific success
- At least one regime shows eventful, geometry-sensitive vortex dynamics.
- At least one reduced observable exhibits clearly resolvable jump-like or bursty behavior.
- Low-dimensional inference on synthetic data is nondegenerate.

### Numerical success
- Deterministic V&V gates pass.
- Convergence under mesh/time-step refinement is demonstrated for reference cases.
- Vortex detection is stable under refinement.
- Noise discretization passes moment checks.

### Proposal success
- The code and campaign produce a 4-figure package:
  1. geometry + pinning field,
  2. vortex trajectories,
  3. observable traces with events,
  4. synthetic posterior recovery.
- A credible compute-need narrative exists based on ensemble + inverse workload, not only on a single large solve.
- The proposal can explicitly state what exascale resources buy beyond workstation or cluster scale.

## Risks and mitigations

### Risk 1: TDGL effective-model limitations
Mitigation:
- frame TDGL as a mesoscopic effective model,
- focus on mechanistic discrimination and data-constrained parameter recovery,
- avoid claims of microscopic completeness.

### Risk 2: inverse non-identifiability
Mitigation:
- infer hyperparameters, not full spatial fields, in v1,
- use multiple observables and posterior predictive checks,
- include null-model comparisons.

### Risk 3: solver instability under strong forcing or noise
Mitigation:
- start with deterministic clean-strip cases,
- use IMEX first and fully implicit only when needed,
- gate stochastic work behind deterministic acceptance tests.

### Risk 4: uncontrolled scope growth
Mitigation:
- use this charter as a hard boundary,
- require Architectural Decision Records for any scope change.

## Decision log for v1
- **Geometry**: thin-film 2D patches only.
- **Discretization**: structured Cartesian, gauge-invariant link variables.
- **Forward EM**: prescribed `A_dc + a_rf(t) A_rf(x)` only.
- **Inference target**: low-dimensional hyperparameters only.
- **Output policy**: reduced observables by default, sparse full-field checkpoints.
- **Performance goal**: MPI-first, PETSc-friendly architecture with later GPU path; no bespoke GPU kernels in v1.

## Exit conditions for v1
v1 is complete when:
- deterministic, stochastic, and inverse baselines all run from configs,
- the acceptance checklist is green,
- the figure package exists,
- the experiment matrix has been executed for at least one full campaign phase.
