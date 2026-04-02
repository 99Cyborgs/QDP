# 09. Proposal translation brief

This document maps technical outputs from the experiment platform to proposal sections.

## 9.1 Significance
Use outputs from:
- deterministic and stochastic field simulations,
- reduced-observable traces,
- null-model comparisons.

Narrative:
- the platform tests whether vortex-mediated rare events can explain observed jump/loss phenomenology,
- the work is scientifically significant because it moves from descriptive loss models to mechanism-resolving, uncertainty-aware inference.

## 9.2 Innovation
Use outputs from:
- gauge-invariant vortex-resolved TDGL under prescribed RF drive,
- event-aware observation operators,
- low-dimensional Bayesian inversion.

Narrative:
- the innovation is not just a solver; it is the coupling of rare-event PDE simulation to inverse inference over hidden pinning/noise structure.

## 9.3 Computational need
Use outputs from:
- ensemble rare-event campaigns,
- inference workloads,
- scaling tables.

Narrative:
- capability computing is required because the scientific quantity of interest is a posterior over rare-event behavior, not a single forward trajectory.

## 9.4 Readiness
Use outputs from:
- V&V suite,
- pilot scaling runs,
- reproducibility metadata,
- synthetic inverse recovery.

Narrative:
- the team already possesses a validated prototype and a campaign definition, reducing technical risk.

## 9.5 Deliverables
Proposal deliverables can be tied directly to pack outputs.

### Deliverable D1
Validated stochastic TDGL-RF solver.

Evidence:
- D and S phase benchmarks.

### Deliverable D2
Observation-operator and event-statistics package.

Evidence:
- proposal figure 3,
- timeseries and event summary outputs.

### Deliverable D3
Synthetic inverse capability.

Evidence:
- proposal figure 4,
- posterior recovery tables.

### Deliverable D4
Leadership-scale campaign and compute justification.

Evidence:
- P-phase scaling outputs,
- projected workload table.

## 9.6 Figure plan
The following figure names should be preserved by the codebase:

1. `fig_geometry_pinning.png`
2. `fig_vortex_trajectories.png`
3. `fig_observable_traces_events.png`
4. `fig_synthetic_posterior_recovery.png`
5. `fig_scaling_strong.png`
6. `fig_scaling_ensemble.png`

## 9.7 Proposal paragraph fragments

### Scientific objective fragment
We will determine whether rare, geometry- and defect-mediated vortex events under RF drive can explain observed loss and jump phenomenology, and whether hidden pinning/noise parameters can be recovered through Bayesian inversion of reduced observables.

### Computational objective fragment
We will build an uncertainty-aware, ensemble-based TDGL campaign in which the dominant cost arises from long-horizon stochastic trajectories and inverse exploration over latent parameters.

### Readiness fragment
The project begins from a validated structured-grid prototype with explicit verification gates, synthetic inverse baselines, and an execution matrix that maps directly to early leadership-scale pilot runs.

## 9.8 Proposal failure modes to avoid
Do not write:
- "one large PDE solve requires exascale" without evidence,
- "TDGL is a complete microscopic description",
- "Bayesian inference will be straightforward",
- "the software will scale" without pilot results.
