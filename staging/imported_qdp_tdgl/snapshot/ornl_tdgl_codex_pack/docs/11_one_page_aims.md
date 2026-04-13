# 11. One-page aims draft

## Title
Exascale-ready stochastic TDGL-RF digital twin for vortex-mediated rare events in superconducting devices

## Objective
We will build and validate a vortex-resolved, uncertainty-aware PDE framework to determine whether rare vortex events under RF drive explain jump and loss phenomenology in superconducting thin-film devices, and to recover the hidden pinning and noise parameters that control those events.

## Rationale
Observed dissipation and instability signatures are often modeled phenomenologically. That limits mechanistic discrimination and device-design guidance. A stochastic, vortex-resolved thin-film TDGL model provides an effective mesoscale route to simulate rare nucleation, pinning, depinning, and crossing events in realistic geometries. Coupling this forward model to reduced observation operators and Bayesian inversion creates a practical digital-twin workflow for mechanism testing and parameter recovery.

## Aim 1
Develop a deterministic and stochastic 2D thin-film TDGL solver with prescribed RF forcing and explicit pinning landscapes.

### Deliverables
- gauge-invariant forward solver,
- vortex detection and trajectory extraction,
- reduced observables for frequency-shift and dissipation proxies,
- convergence and verification results on reference geometries.

## Aim 2
Construct an event-aware observation layer and identify regimes in which reduced observables are informative about hidden pinning and noise structure.

### Deliverables
- event tables,
- jump and waiting-time statistics,
- synthetic data products,
- campaign results across geometry, forcing, and pinning regimes.

## Aim 3
Perform low-dimensional Bayesian inversion over pinning and noise hyperparameters and quantify posterior predictive agreement.

### Deliverables
- MAP and local uncertainty estimates,
- synthetic-truth recovery baselines,
- posterior predictive checks,
- proposal-grade figures and tables.

## Computational significance
The principal computational cost is not a single forward solve. It is the large ensemble of long-horizon stochastic realizations required for rare-event statistics and posterior exploration over latent parameters. This makes the project naturally aligned with leadership-scale campaigns in which domain decomposition and ensemble parallelism are both required.

## Outcome
The result will be an implementation-ready, uncertainty-aware simulation and inference platform that can support a proposal centered on mechanistic discrimination of vortex-mediated rare events and the computational need for large stochastic PDE campaigns.
