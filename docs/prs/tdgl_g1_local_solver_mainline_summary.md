# TDGL G1 Local Solver Mainline Summary

This branch promotes the local deterministic phase-1 solver to a merge-ready baseline after the correctness pass in `3ea2a19` and the forcing-alignment follow-up in `9c2287e`.

## Previously fixed solver defects

1. The Meissner initial state ignored configured forcing at `t=0`, so `state.A` and `state.A_dot` did not match the case forcing definition.
2. The IMEX advance path assembled the solve context at the old state time instead of `t + dt`, so RF-driven steps used stale forcing.
3. The stepper returned `phi`, `A`, and `A_dot` that were not recomputed after the `psi` update, leaving the stored state internally inconsistent at the end of each step.
4. Observable weight profiles were normalized over inactive cells in masked geometries, biasing reduced observables such as `delta_f_over_f0` and `qinv`.
5. Vortex plaquette winding used one late phase wrap instead of edge-wise wrapped increments, allowing cancellation and missed unit-charge vortices.
6. The scalar-potential solve accepted disconnected active masks, which produced an ill-posed gauge problem instead of failing fast with a structured solver error.

## Main regression tests added on this branch

- `tests/unit/test_state_stepper.py`
  Verifies forcing alignment at initialization and after one RF-driven step.
- `tests/unit/test_observables.py`
  Verifies masked-cell exclusion in observable weight normalization.
- `tests/unit/test_vortices.py`
  Verifies unit-charge vortex detection on an analytic field.
- `tests/unit/test_phi_solver.py`
  Verifies zero-mean gauge fixing, sparse reduction on masked domains, and disconnected-mask rejection.
- `tests/unit/test_scipy_backend.py`
  Verifies non-finite RHS rejection, direct-solve residual checking, and iterative-to-direct fallback reuse.
- `tests/integration/test_run_case_outputs.py`
  Verifies terminal observable sampling and `write_observables` gating.
- `tests/integration/test_d01_clean_strip.py`
  Verifies the deterministic clean-strip smoke path and persisted profiling/status outputs.

## Residual caveats

- Phase-1 remains deterministic-only. `noise.enabled=true`, ensemble workflows, and inference workflows are still intentionally rejected by semantic validation.
- This branch establishes solver correctness and run-artifact discipline; it is not a full physics-validation claim outside the documented phase-1 acceptance surface.
- Acceptance thresholds should stay conservative and observable-based. They are intended to catch regressions in controlled campaign runs, not certify asymptotic convergence or publication-grade validation.
