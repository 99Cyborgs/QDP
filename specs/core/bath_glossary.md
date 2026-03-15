# Bath Glossary (One Page)

**Purpose:** define bath / environment terminology in QDP in a mechanically precise way.

---

## Core Objects

### System (S)
The degrees of freedom you **explicitly** model and control (qubit, resonator mode, selected collective coordinate).

### Bath / Environment (B)
All degrees of freedom you **do not** keep explicitly, but which couple to S and influence its dynamics.

### Reservoir
A bath large enough that energy/information flow from S does not noticeably change the bath state (often assumed stationary).

### Thermal bath (T)
A reservoir in equilibrium at temperature **T**, imposing **detailed balance** constraints on noise and transition rates.

---

## Mathematical Backbone

### Total Hamiltonian
\[
H = H_S + H_B + H_{SB}
\]
Reduced state:
\[
\rho_S(t)=\mathrm{Tr}_B\,\rho_{SB}(t)
\]

### Bath operator
The operator in B that couples to S (often denoted **B** in formulas). Typical coupling:
\[
H_{SB}= A_S \otimes B
\]

### Bath correlation function
\[
C(t)=\langle B(t)B(0)\rangle
\]
Encodes the bath memory in time.

### Bath correlation time (\(\tau_B\))
Timescale over which **C(t)** decays. If \(\tau_B\ll\tau_S\) (system timescale), Markov approximations are often valid.

### Noise power spectral density (PSD) \(S(\omega)\)
Fourier transform of correlations (convention-dependent):
\[
S(\omega)=\int_{-\infty}^{\infty} e^{i\omega t} C(t)\,dt
\]
What filter-function measurements effectively probe.

### Spectral density \(J(\omega)\)
Mode-density-weighted coupling strength for oscillator-bath models:
\[
J(\omega)=\sum_k |g_k|^2\,\delta(\omega-\omega_k)
\]
Structured \(J(\omega)\) (peaks/gaps) is a primary source of kernel memory.

---

## Markovian vs Non‑Markovian (Operational)

### Markovian (time-local, memoryless)
\[
\dot\rho_S(t)=\mathcal{L}\,\rho_S(t)
\]
with \(\mathcal{L}\) a GKSL/Lindblad generator (CPTP-safe).
Interpretation: environment correlations are effectively instantaneous at the system’s resolution.

### Non‑Markovian (memoryful)
Two practically distinct sources:

**(A) Kernel memory (dynamical bath correlations)**
\[
\dot\rho_S(t)=\int_0^t K(t-\tau)\,\rho_S(\tau)\,d\tau
\]
Memory lives in the **kernel** \(K\) built from bath correlations / structured \(J(\omega)\).

**(B) Metastable memory (hidden slow configuration)**
Hybrid model:
\[
\dot\rho_S(t)=\mathcal{L}_{C(t)}[\rho_S(t)]
\]
Memory lives in a slow state variable **C(t)** (e.g., pinned vortex configuration, trap occupancy, slow fluctuator state).

---

## Circuit / Microwave Translation

### Surface impedance \(Z_s(\omega)=R_s+iX_s\)
Effective boundary condition for superconducting films; vortices, quasiparticles, and TLS can modify \(R_s\) and \(X_s\).

### Participation ratio
Geometry factor mapping local dissipation or reactance into a mode-level observable (\(1/Q_i\), \(\Delta f/f\)).

### Purcell / radiative loss (EM bath)
Loss via coupling to EM modes of lines/package. Often expressible via effective impedance seen by the qubit/resonator.

---

## Common Physical Baths in Superconducting Devices

### TLS ensemble (dielectrics/interfaces)
A broad distribution of two-level defects producing loss and 1/f-type noise; shows power-dependent saturation and temperature dependence.

### Phonon bath (substrate)
Vibrational modes; can be engineered (phononic bandgaps) to create kernel memory (non-exponential decay, revivals).

### Quasiparticles (pair-breaking excitations)
Non-equilibrium density can cause relaxation bursts and correlated events across devices.

### Vortices (trapped flux lines)
Either:
- **metastable configuration bath** (C-state memory; hysteresis/switching), or
- an **effective impedance contribution** (complex response via pinning frequency \(\omega_p\)).

---

## QDP Discipline Reminder
Escalate from Markovian to non‑Markovian only when required by a **specific signature** (hysteresis/switching for metastable memory; non-exponential/revivals/structured spectra for kernel memory). fileciteturn1file0
