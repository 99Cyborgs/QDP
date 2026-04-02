# 03. Numerics specification

## 3.1 Discretization choice
v1 uses a **gauge-invariant link-variable finite-difference scheme** on a structured Cartesian mesh.

Reasons:
- preserves gauge structure,
- handles vortices robustly,
- straightforward MPI domain decomposition,
- simple output format,
- lower implementation burden than finite elements for the first milestone.

## 3.2 Mesh and storage layout
Use a rectangular grid with:
- cell centers for \(\psi\) and \(\phi\),
- edge-centered storage for \(A_x\) and \(A_y\),
- optional ghost cells for MPI exchange.

### Required mesh metadata
- `nx`, `ny`
- `lx`, `ly`
- `hx = lx / nx`, `hy = ly / ny`
- boundary masks
- optional hole/moat masks

## 3.3 Link variables
Define edge link variables
\[
U^x_{i+\frac{1}{2},j}=e^{-i h_x A^x_{i+\frac{1}{2},j}},
\qquad
U^y_{i,j+\frac{1}{2}}=e^{-i h_y A^y_{i,j+\frac{1}{2}}}.
\tag{1}
\]

These are required; do not implement the covariant Laplacian by expanding the gauge terms directly in v1.

## 3.4 Covariant Laplacian
Use

\[
(\Delta_A \psi)_{ij} =
\frac{
U^x_{i+\frac{1}{2},j}\psi_{i+1,j}
- 2\psi_{ij}
+ (U^x_{i-\frac{1}{2},j})^*\psi_{i-1,j}
}{h_x^2}
+
\frac{
U^y_{i,j+\frac{1}{2}}\psi_{i,j+1}
- 2\psi_{ij}
+ (U^y_{i,j-\frac{1}{2}})^*\psi_{i,j-1}
}{h_y^2}.
\tag{2}
\]

## 3.5 Discrete currents
Required edge currents:

\[
(J_s)_x{}_{i+\frac{1}{2},j}
=
\frac{1}{h_x}
\Im\left(
\psi_{ij}^* U^x_{i+\frac{1}{2},j}\psi_{i+1,j}
\right),
\tag{3}
\]

\[
(J_s)_y{}_{i,j+\frac{1}{2}}
=
\frac{1}{h_y}
\Im\left(
\psi_{ij}^* U^y_{i,j+\frac{1}{2}}\psi_{i,j+1}
\right),
\tag{4}
\]

\[
(J_n)_x{}_{i+\frac{1}{2},j}
=
-\sigma_n
\left(
\frac{\phi_{i+1,j}-\phi_{ij}}{h_x}
+
\dot{A}^x_{i+\frac{1}{2},j}
\right),
\tag{5}
\]

with the analogous expression in \(y\).

## 3.6 Boundary treatment
For insulating boundaries, impose discrete zero-normal-current conditions by:
- mirror or ghost-cell treatment consistent with the link-variable stencil,
- excluding invalid neighbors at masked cells,
- zeroing current components normal to masked edges.

Moats/holes are represented by masks and boundary stencils, not by separate meshes.

## 3.7 Time integration strategy

### Phase 1 default: IMEX linearized scheme
At step \(n\rightarrow n+1\):

1. Evaluate \(\mathbf{A}^n\) and \(\dot{\mathbf{A}}^n\).
2. Build link variables from \(\mathbf{A}^n\).
3. Sample \(\eta^n\) if stochastic mode is active.
4. Compute \(\mathbf{J}_s(\psi^n)\).
5. Solve the discrete elliptic equation for \(\phi^n\).
6. Advance \(\psi\) using

\[
\frac{u}{\Delta t}(\psi^{n+1}-\psi^n)
-
\Delta_{A^n}\psi^{n+1}
=
(\alpha-|\psi^n|^2)\psi^n
-
iu\phi^n\psi^n
+
\eta^n.
\tag{6}
\]

This yields a linear complex solve for \(\psi^{n+1}\).

### Phase 2 optional upgrade: fully implicit Newton solve
Only add this after deterministic/stochastic baselines pass. It is not required for v1 delivery.

## 3.8 Linear algebra requirements
Use PETSc-backed operators for:
- the scalar-potential elliptic solve,
- the complex \(\psi\) update solve,
- optional Jacobian-free Newton-Krylov later.

### Required abstractions
Implement a solver interface with pluggable backends:
- `scipy` fallback for local development,
- PETSc backend for production and MPI runs.

## 3.9 Solver tolerances
Default targets:
- linear solve relative tolerance: `1e-8`
- linear solve absolute tolerance: `1e-12`
- nonlinear residual tolerance (if used later): `1e-8`
- charge-conservation residual target: `L_inf < 1e-8`

These are defaults; case configs may override them.

## 3.10 Random-number handling
All stochastic runs must:
- accept a master seed,
- derive per-rank and per-realization seeds deterministically,
- write the derived seeds to provenance metadata,
- support exact reruns.

Use `numpy.random.Generator` with a documented seed-derivation rule.

## 3.11 Output cadence
Provide separate cadences for:
- observables,
- vortex maps,
- full-field checkpoints.

Default:
- observables every `obs_stride`,
- vortex map every `vortex_stride`,
- full fields every `field_stride`,
- checkpoint every `checkpoint_stride`.

The experiment runner should bias toward sparse field dumps and dense reduced-observable output.

## 3.12 Failure handling
The solver must detect and report:
- NaNs or infs in \(\psi\), \(\phi\), or observables,
- divergence of linear or nonlinear solves,
- physically absurd values such as negative waiting times or invalid vortex labels,
- violation of masked geometry rules.

On failure:
- write a compact crash report,
- persist the last valid checkpoint if available,
- mark the run status as failed in metadata,
- return a nonzero exit code.

## 3.13 Convergence studies
Every reference benchmark must support mesh and time-step refinement runs.

### Minimum convergence ladder
- mesh: coarse / medium / fine
- time step: base / half / quarter

The code should emit a standard convergence report:
- key observable values,
- percent differences,
- estimated empirical order where meaningful,
- pass/fail against acceptance thresholds.

## 3.14 Pseudocode for one time step

```text
given psi_n, config, time t_n
A_n      <- A_dc + a_rf(t_n) * A_rf
A_dot_n  <- d/dt[a_rf(t_n)] * A_rf
U_n      <- link_variables(A_n)

if stochastic:
    eta_n <- sample_noise(seed, dt, hx, hy, Gamma)
else:
    eta_n <- 0

J_s_n    <- supercurrent(psi_n, U_n)
phi_n    <- solve_phi(div(J_s_n), A_dot_n, sigma_n, bc, gauge_fix)

rhs      <- (u/dt) * psi_n
rhs      += (alpha - |psi_n|^2) * psi_n
rhs      += -1j * u * phi_n * psi_n
rhs      += eta_n

solve:
    [(u/dt) I - Delta_A(U_n)] psi_{n+1} = rhs

obs_n1   <- observables(psi_{n+1}, phi_n, A_n, A_dot_n)
events   <- detect_events(obs_n1, vortex_map(psi_{n+1}, A_n))
write outputs according to stride policy
```

## 3.15 Non-negotiable design constraints
- Keep gauge-invariant building blocks isolated and unit-tested.
- Do not entangle solver code with plotting code.
- Do not hard-code experiment-specific observables in the core PDE update.
- Do not store dense field output at every time step.
- Do not add GPU-specific branches in v1 core logic.
