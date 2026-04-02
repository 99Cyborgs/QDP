# 02. Physics specification

## 2.1 Modeling regime
Use a 2D thin-film effective model on a planar domain

\[
\Omega \subset \mathbb{R}^2
\]

with film thickness absorbed into effective parameters. The domain may contain:
- outer insulating boundaries,
- optional holes / moats,
- optional current-lead segments in later v1.1 work.

v1 should start with strip geometries and moat-free or simple-moat variants.

## 2.2 State variables
- Complex order parameter: \(\psi(x,t) \in \mathbb{C}\)
- Scalar potential: \(\phi(x,t) \in \mathbb{R}\)
- Prescribed vector potential: \(\mathbf{A}(x,t) \in \mathbb{R}^2\)

## 2.3 Prescribed forcing
Represent the electromagnetic drive by

\[
\mathbf{A}(x,t) = \mathbf{A}_{dc}(x) + a_{rf}(t)\,\mathbf{A}_{rf}(x)
\]

where initially

\[
a_{rf}(t) = A_{rf}\cos(\omega t + \varphi_0).
\]

v1 does not solve Maxwell self-consistently.

## 2.4 Nondimensionalization
Use the following scales:
- length: coherence length \(\xi\),
- time: TDGL relaxation time \(\tau_{GL}\),
- vector potential: \(A_0 = \Phi_0/(2\pi \xi)\),
- scalar potential: \(\phi_0 = \hbar/(2e\tau_{GL})\),
- order parameter: equilibrium amplitude \(\psi_0\).

All equations below are written in nondimensional variables.

## 2.5 Forward model
The forward stochastic TDGL system is

\[
u(\partial_t + i\phi)\psi
=
(\nabla - i\mathbf{A})^2\psi
+
(\alpha(x) - |\psi|^2)\psi
+
\eta_\psi(x,t).
\tag{1}
\]

The supercurrent is

\[
\mathbf{J}_s =
\Im\left( \psi^*(\nabla - i\mathbf{A})\psi \right),
\tag{2}
\]

and the normal current is

\[
\mathbf{J}_n =
-\sigma_n(\nabla\phi + \partial_t \mathbf{A}).
\tag{3}
\]

Enforce charge conservation:

\[
\nabla \cdot (\mathbf{J}_s + \mathbf{J}_n)=0.
\tag{4}
\]

This yields the elliptic equation for \(\phi\):

\[
-\sigma_n \Delta \phi =
\nabla\cdot\mathbf{J}_s -
\sigma_n \nabla\cdot(\partial_t \mathbf{A}).
\tag{5}
\]

If \(\nabla\cdot \mathbf{A}=0\), the last term is absent.

## 2.6 Pinning / defect field
Write

\[
\alpha(x)=1-\chi(x),
\tag{6}
\]

where \(\chi(x)\) is the pinning landscape.

### Supported pinning models in v1

#### Model P0: none
\[
\chi(x) = 0.
\]

#### Model P1: parametric Gaussian defects
\[
\chi(x;\theta)=\sum_{m=1}^{M} a_m
\exp\left(-\frac{|x-c_m|^2}{2\ell_m^2}\right).
\tag{7}
\]

#### Model P2: random-field hypermodel
\[
\chi \sim \text{Gaussian random field with hyperparameters }
\theta_\chi=(\mu_\chi,\sigma_\chi,\ell_\chi,s),
\tag{8}
\]

where \(s\) denotes the random seed. A log-Gaussian transform is permitted if strict positivity is desired.

v1 inference should target hyperparameters of P2, not full field values.

## 2.7 Boundary conditions

### Superconducting boundary
For insulating edges and moat boundaries,

\[
\mathbf{n}\cdot(\nabla - i\mathbf{A})\psi = 0.
\tag{9}
\]

### Current conservation boundary
Impose

\[
\mathbf{n}\cdot(\mathbf{J}_s + \mathbf{J}_n)=0
\tag{10}
\]

on insulating boundaries.

### Gauge fixing for \(\phi\)
Impose one of:
- zero spatial mean: \(\int_\Omega \phi\,dx = 0\), or
- a pinned reference node in the discrete solve.

v1 should use zero-mean gauge fixing.

## 2.8 Noise model
v1 uses additive complex Gaussian white noise in the TDGL equation:

\[
\mathbb{E}[\eta_\psi(x,t)] = 0,
\tag{11}
\]

\[
\mathbb{E}[\eta_\psi(x,t)\eta_\psi^*(x',t')]
=
2\Gamma_\psi \delta(x-x')\delta(t-t').
\tag{12}
\]

Discrete realization on a grid cell of area \(h_x h_y\) and time step \(\Delta t\):

\[
\eta_{ij}^n
=
\sqrt{\frac{2\Gamma_\psi}{h_x h_y \Delta t}}
\frac{\xi^n_{1,ij} + i\xi^n_{2,ij}}{\sqrt{2}},
\qquad
\xi^n_{1,ij},\xi^n_{2,ij}\sim\mathcal{N}(0,1).
\tag{13}
\]

### Noise exclusions
Do not add:
- multiplicative noise,
- colored noise,
- technical frequency jitter,
- \(1/f\) noise

until the additive-noise workflow is validated.

## 2.9 Initial conditions
Supported initial conditions:
- `meissner`: \(\psi \approx 1\) everywhere, no vortices
- `seeded_vortices`: one or more imposed phase windings
- `restart`: read from checkpoint

Default for reference campaigns: `meissner`.

## 2.10 Derived field quantities
Compute at each output step:
- \(|\psi|^2\),
- phase of \(\psi\) with wrapped and unwrapped variants as needed,
- \(\mathbf{J}_s\),
- \(\mathbf{J}_n\),
- total current,
- vortex plaquette winding map,
- event flags.

## 2.11 Gauge-invariant vortex detection
Define plaquette winding number

\[
q_p=
\frac{1}{2\pi}\operatorname{wrap}\left(
\sum_{\partial p}\Delta\arg \psi
-
\oint_{\partial p}\mathbf{A}\cdot d\ell
\right).
\tag{14}
\]

Interpretation:
- \(q_p=+1\): vortex
- \(q_p=-1\): antivortex
- \(q_p=0\): no topological defect

v1 should store the vortex map per sampled frame and emit trajectory tracks.

## 2.12 Observation model
The reduced observable layer maps field trajectories to experiment-like proxies.

### Frequency-shift proxy
\[
\frac{\Delta f(t)}{f_0}
=
-c_f \int_\Omega w_f(x)\left(1-|\psi(x,t)|^2\right)\,dx
+ \varepsilon_f(t).
\tag{15}
\]

### Dissipation proxy
\[
Q^{-1}(t)
=
Q^{-1}_{bg}
+
c_Q \int_\Omega w_Q(x)|\mathbf{J}_n(x,t)|^2\,dx
+ \varepsilon_Q(t).
\tag{16}
\]

### Event observables
Also compute:
- total vortex count \(N_v(t)\),
- boundary crossing count,
- jump amplitude distribution in \(\Delta f/f_0\),
- jump amplitude distribution in \(Q^{-1}\),
- inter-event waiting-time distribution,
- burst size and burst duration.

### Default observation noise
Use additive Gaussian observation noise for synthetic data:
- \(\varepsilon_f \sim \mathcal{N}(0,\sigma_f^2)\)
- \(\varepsilon_Q \sim \mathcal{N}(0,\sigma_Q^2)\)

## 2.13 Parameter vector for inverse studies
v1 inference should target the low-dimensional vector

\[
\theta = (
\mu_\chi,\sigma_\chi,\ell_\chi,
\Gamma_\psi,
A_{rf},
B_{dc},
c_f,
c_Q,
Q^{-1}_{bg},
\sigma_f,\sigma_Q
).
\tag{17}
\]

Not every study must infer every component. Early studies should start with
\[
\theta_{small} = (\sigma_\chi,\ell_\chi,\Gamma_\psi,A_{rf}).
\]

## 2.14 Data products
Every run must produce:
- configuration snapshot,
- scalar metadata,
- time-series observables,
- event table,
- optional field checkpoints,
- provenance file with random seeds and code revision,
- summary statistics file.

## 2.15 Explicit exclusions and assumptions
- The model is effective and mesoscopic.
- Quantitative agreement with low-temperature experiments is not assumed a priori.
- v1 is aimed at mechanism discrimination and inverse-workflow demonstration, not final device prediction.
