# Signature → Likely Bath Class → Minimal Measurement Needed

**Goal:** map observed signatures to the smallest measurement that breaks degeneracy.

| Signature in data | Likely bath / channel class | Minimal measurement to confirm / discriminate |
|---|---|---|
| **Hysteresis** in 1/Qi or Δfr/fr vs Bcool or sweep direction | **Metastable configuration memory** (vortex pinning/traps, slow defect sector) | Repeat **ZFC vs FC** and **up/down field loops**; compute hysteresis index; replicate across cooldowns |
| **Bimodal** Qi/T1 distributions at fixed external settings | **Hidden discrete state C** (pinned vortex occupancy; strong fluctuator) | Long time traces + histogram; fit **2-state HMM** vs single drift; verify protocol dependence |
| **Telegraph switching** in Qi/T1 time traces | **Metastable switching** (C(t) jumps) | Time-resolved monitoring at fixed conditions; estimate dwell times; test dependence on Bcool, drive, T |
| Smooth **power dependence** consistent with saturation | **TLS ensemble** (dielectric/interface loss) | Qi vs readout power sweep; fit TLS saturation form; repeat at 2–3 temperatures |
| Strong **temperature scaling** of loss without hysteresis | TLS or quasiparticles (depends on scaling law) | Temperature sweep (small set of points); check whether scaling matches TLS tanh-law vs qp activation-like behavior |
| **Non-exponential** decay (T1/Ramsey) with stable preparation | **Kernel memory** (structured phonon/EM bath) | Acquire decay curves with high SNR; compare exponential vs stretched / multi-exponential; then do filter-function (CPMG) if needed |
| **Revivals / backflow** signatures (partial recovery) | **Finite-size / bandgap** structured bath | Time-domain sequences designed to reveal revivals; compare with/without phononic structures or packaging changes |
| **Avoided crossing** in spectroscopy | **Coherent parasitic mode** (spurious resonator/defect mode) | High-resolution spectroscopy vs flux/bias; verify anticrossing gap 2g and mode tracking |
| **Narrowband peak** in noise PSD inferred from Ramsey/echo | **Structured bath mode** or coherent fluctuator | Filter-function noise spectroscopy (vary pulse spacing); identify peak frequency & linewidth |
| **Sudden T1 collapses** or bursty relaxation | **Quasiparticle / phonon burst** events | Fast repeated T1 sampling; cross-device correlation; vary shielding / biasing / thermalization; if available check parity switching |
| **Correlated events across devices** on same chip | **Global bath** (qp/phonon/radiation) | Simultaneous monitoring; correlation analysis; modify shielding/absorbers/packaging to test suppression |
| Drive causes **crossover to higher loss** correlated with Bcool/history | **Depinning / flux-flow onset** (vortex dynamics) vs heating | Drive sweep at fixed prepared state; check whether crossover shifts with Bcool; verify Δfr/fr vs Δ(1/Qi) ratio change |
| Δfr/fr and Δ(1/Qi) move with **consistent ratio** across histories | **Pinned vortex impedance** organized by a single \(\omega_p\) | Joint extraction of Qi and fr; apply ratio test for inferred \(\omega_p\); check consistency across Bcool |
| No geometry dependence; loss stable across field protocols | Likely **not vortex-dominated**; proceed to TLS / Purcell / conductor loss | Swap geometry / participation; power and temperature sweeps; package/line attenuation checks |

---

## QDP Usage
- Treat this table as a **fork protocol**: choose the smallest discriminant measurement before adding model parameters. fileciteturn1file0
