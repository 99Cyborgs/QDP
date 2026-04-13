# Mechanism Identifiability and Falsification Framework for Superconducting-Qubit Decoherence

## Why identifiability is the bottleneck

Superconducting-qubit decoherence is not one problem; it is a superposition of problems whose observable consequences are often statistically indistinguishable unless you force them apart with **orthogonal perturbations**. Reviews that catalog “known mechanisms” are useful as background, but they typically stop short of the harder question: **given realistic measurement constraints, what can be uniquely identified?** citeturn6search4turn8view2turn5search7

A practical identifiability analysis therefore has to be framed as an **input–output system identification** problem: choose a candidate model class (or several), apply structured perturbations (temperature, drive amplitude, magnetic history, geometry), and test whether models remain distinguishable **after** marginalizing over nuisance parameters (SPAM errors, drift, pulse distortion, readout nonlinearity). citeturn11search0turn11search2turn9search5turn9search4

Two sobering facts from long-duration qubit metrology matter here:

- **Coherence parameters fluctuate** in time, often with colored correlations; naive “single-number” T1/T2 summaries can be mismeasuring the process you think you’re probing. citeturn5search15turn1search18turn1search6  
- Environmental couplings can be **non-Markovian** on experimentally relevant timescales; forcing them into a time-independent Lindblad fit can produce deceptively “good-looking” averages while leaving structured residuals. citeturn6search26turn11search7turn4search33turn12search3

You asked for a mechanism discrimination matrix spanning five mechanisms and five families of observables. The correct way to read such a matrix is: “what combination of probes is necessary to break degeneracy under realistic bandwidth/precision limits,” not “which single knob settles it.”

## Mechanism discrimination matrix

The table below encodes **identifiability leverage**. “Primary” means the observable can (with proper controls) isolate the mechanism from the others; “supporting” means it helps but usually remains degenerate; “weak” means rarely diagnostic without extra context. “Instrument caveat” flags where limited bandwidth/SNR routinely causes false positives.

| Mechanism | T1 vs temperature | Ramsey envelope / T2* structure | Drive-amplitude dependence | Magnetic hysteresis / history | Geometry scaling | What actually isolates it |
|---|---|---|---|---|---|---|
| Vortex motion / trapped flux | Supporting | Supporting | Supporting | **Primary** | **Primary** | Hysteresis + cooldown field dependence + width/thickness thresholds |
| Quasiparticle tunneling | **Primary** (when thermal-QP dominated) / Supporting (when non-eq dominated) | Supporting | **Primary** (under strong drive / pair-breaking regimes) | Weak (except via vortex-assisted trapping) | Supporting | Parity switching correlations + controlled QP injection/suppression + drive-induced QP signatures |
| TLS in dielectrics | Supporting | Supporting (often via T1 fluctuations / spectral diffusion) | **Primary** (TLS saturation) | Weak | **Primary** (participation ratios) | Power dependence + participation scaling + TLS-induced T1 dispersion/frequency dependence |
| Phonon coupling to substrate | Supporting | Supporting / sometimes Primary (if synchronized to mechanical cycle) | Supporting | Weak | Supporting | Synchronization to mechanical/vibrational environment + phononic engineering response |
| Control-line / wiring noise (incl. flux-line noise) | Supporting | **Primary** (filter-function signatures, Gaussian/nonexp decay from 1/f) | Supporting (AM/PM noise converts under drive) | Weak (except for flux noise with field dependence) | Supporting (coupling/mutual inductance scaling) | Noise spectroscopy via dynamical decoupling + line-attenuation/frequency-dependent filtering tests |

Key point: **no single column isolates all mechanisms**. The most discriminating axes are (i) magnetic history (vortices), (ii) power dependence + participation scaling (TLS), and (iii) filter-function-based noise spectroscopy (control-line/flux noise). citeturn7search2turn7search1turn5search21turn5search9turn1search5turn10search0

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["transmon superconducting qubit chip microscope","Abrikosov vortex in superconducting thin film illustration","dilution refrigerator superconducting qubit wiring attenuation filtering diagram","two level systems dielectric loss schematic superconducting resonator"],"num_per_query":1}

### Vortex motion and trapped flux

**Observable signatures that actually discriminate:**

Magnetic hysteresis and field history are the hard discriminators. Coplanar resonators (and by extension planar qubit wiring and capacitor structures) display hysteretic dependence of resonator loss and frequency on applied field because the vortex distribution depends on the field sweep trajectory and pinning landscape. citeturn7search2turn7search5

Field-cool experiments show that insufficient shielding or pulsed fields can trap vortices that degrade microwave Q, and that engineered pinning/geometry can mitigate the added loss. citeturn7search30turn0search29turn7search23

Geometry scaling is not “nice to have”; it is diagnostic. Vortex trapping/expulsion thresholds in thin films depend on strip width and on the Pearl length (set by penetration depth and film thickness), and the trapping process occurs near Tc where these length scales matter. citeturn2search1turn2search5

**How the five requested observables behave:**

- **T1(T):** vortex-induced microwave loss can be relatively weakly temperature-dependent deep in the superconducting state (compared to, say, thermal QPs), which makes T sweeps alone poor discriminators. You need the field-history axis. citeturn0search9turn7search2  
- **Ramsey/T2 structure:** vortices can introduce frequency noise and loss; however, these signatures overlap with flux noise and TLS-induced frequency noise unless you tag them by magnetic history. citeturn7search2turn10search0  
- **Drive amplitude dependence:** vortex oscillation-driven loss can be nonlinear in current density, but practical identification is messy because microwave chain distortions mimic nonlinearity. Expect “supporting,” not “primary.” citeturn0search1turn7search11  
- **Magnetic hysteresis:** this is where vortices are uniquely loud. citeturn7search2turn7search5  
- **Geometry scaling:** vortex entry/trapping thresholds vary strongly with width and defect landscape; this is a discriminating axis when paired with controlled cooldown. citeturn2search1turn2search12turn2search9  

**Counterpoint that matters:** vortex-related observables are extraordinarily sensitive to microstructure and edge defects; ideal edge-barrier models routinely overpredict entry thresholds if the edges are damaged or granular. citeturn2search12turn2search0

### Quasiparticle tunneling and nonequilibrium quasiparticles

Quasiparticles are “solved” only in talks. In data, they are one of the few mechanisms that can produce **both** relaxation and excitation dynamics (effective heating) in ways that are directly measurable. citeturn0search2turn4search5turn8view6

**Discriminating signatures:**

- **Parity switching correlations:** In offset-charge-sensitive transmons, relaxation/excitation events correlate with charge-parity switches, providing a relatively direct fingerprint for quasiparticle tunneling. citeturn0search2  
- **Magnetic-field-assisted trapping:** controlled vortex trapping can reduce quasiparticle density by acting as a sink (suppressed gap in the vortex core), and this can improve coherence in some regimes; this is a genuine (and often misunderstood) coupling between “vortex physics” and “QP physics.” citeturn8view6turn7search0  
- **Drive-induced quasiparticles:** sufficiently strong microwave driving can activate pair-breaking (multi-photon or mixed absorption processes), reintroducing QP-induced decoherence even when static QP populations are managed. citeturn1search15turn1search19turn1search7  
- **Engineering suppression:** device-level interventions (geometry, shielding above the gap, traps) can reduce QP generation/poisoning, and their success/failure is informative about whether QPs are dominant. citeturn0search8turn4search8turn4search20  

**How the five requested observables behave:**

- **T1(T):** if thermal QPs dominate, T1 should show strong activated temperature dependence consistent with superconducting gap physics. In practice, many devices are limited by **nonequilibrium** QPs whose density is far above thermal expectation, weakening pure T-based discrimination. citeturn0search10turn4search5turn0search14  
- **Ramsey/T2 structure:** QPs can contribute to dephasing and to non-stationary behavior via random telegraph processes, but TLS and flux noise can do this too; make it supporting unless you have parity-tagging. citeturn0search2turn1search2  
- **Drive amplitude dependence:** one of the best discriminators if you can reach the regime where drive-induced QP generation is active, but you must rule out classical distortions first. citeturn1search15turn9search5  
- **Magnetic hysteresis:** weak on its own, except indirectly because vortices can trap QPs. citeturn8view6turn7search0  
- **Geometry scaling:** supportive; QP tunneling rates depend on device specifics (junction, environment, above-gap spectral density). Use it as part of a designed perturbation set, not as a unique signature. citeturn0search14turn0search8  

**Counterpoint:** quasiparticle and TLS narratives are entangled more than most groups admit; there is evidence of TLS-like decoherence channels arising from trapped QPs. citeturn0search4turn0search20

### TLS in dielectrics and surfaces

TLS loss is the default explanation whenever the investigator runs out of imagination. Unfortunately, it is also often correct at millikelvin temperatures and single-photon regimes, especially when participation ratios are high. citeturn5search6turn5search21turn6search13

**Discriminating signatures:**

- **Power dependence via TLS saturation:** resonator loss and frequency shifts show characteristic low-power excess loss from TLS that diminishes as drive power increases and TLS saturate. This is one of the cleanest operational discriminators available. citeturn5search10turn5search6turn5search29  
- **Geometry/participation scaling:** surface participation ratio frameworks connect T1 to the fraction of electric-field energy stored in lossy surface layers, and experiments show relaxation rates scaling roughly with participation under controlled conditions. citeturn8view5turn5search9turn5search21  
- **T1 fluctuations and spectral diffusion:** individual TLS can couple resonantly to qubits, producing large fluctuations in T1 and frequency over time; this is experimentally resolved and attributed to TLS plus spectral diffusion dynamics. citeturn1search6turn1search18turn1search28  

**Fabrication/process dependence (your prompt 5):**

Recent material-platform advances—tantalum-based devices, surface/interface engineering, annealed substrates—are explicitly motivated by reducing dielectric/surface loss and have produced large, reproducible coherence improvements. citeturn8view1turn0search19turn8view0turn0search7

The participation-ratio viewpoint is heavily used to predict and explain these improvements, including explicit decomposition of loss budgets into surface, bulk dielectric, seam/contact, and packaging. citeturn8view0turn5search21turn0search19

**How the five requested observables behave:**

- **T1(T):** TLS loss has temperature dependence, but it is rarely unique once QPs and phonons are in play; treat as supporting unless combined with power dependence. citeturn5search6turn5search26  
- **Ramsey/T2 structure:** TLS-driven noise can generate non-Gaussian features and time-dependent variations; however, so can 1/f flux noise and measurement drift. citeturn1search28turn10search0turn5search15  
- **Drive amplitude dependence:** primary (TLS saturation). citeturn5search10turn5search6  
- **Magnetic hysteresis:** typically weak unless you are actually probing magnetic TLS/spins (then you are drifting into flux-noise territory). citeturn10search2turn10search6  
- **Geometry scaling:** primary via participation. citeturn8view5turn5search9turn5search28  

**Counterpoint:** once coherence reaches the few-hundred-microsecond to millisecond regime, bulk substrate loss, seams, and other “previously negligible” channels emerge; assuming “TLS dominates” becomes lazy. citeturn8view0turn5search6

### Phonon coupling to substrate

If your experimental cadence ever shows periodicity, blame your pulse tube before you write a theory paper.

There is direct evidence that mechanical vibrations from a pulse-tube cooler can induce nonequilibrium dynamics and correlated bit-flip errors in high-coherence qubits, making this a real decoherence axis—not a speculative one. citeturn4search3

More broadly, non-equilibrium phonons in substrates are implicated in quasiparticle generation and correlated error events; mitigation strategies include phonon traps and phonon downconversion layers. citeturn4search20turn4search14turn4search27

Phononic engineering (bandgaps/metamaterials) is being used not only to suppress phonon-mediated decay but also to engineer TLS–phonon interactions, with reports of emergent non-Markovian behavior when phonon emission pathways are suppressed. citeturn4search7turn4search33turn4search4

**How the five requested observables behave:**

- **T1(T):** phonon effects can be strongly temperature-dependent in engineered circuit-phonon platforms, but in conventional transmons at ~5 GHz and ~10 mK, *thermal* phonon occupation is negligible; the “phonon problem” is usually non-equilibrium. citeturn4search1turn4search16turn4search20  
- **Ramsey/T2 structure:** can show up as bursts, correlated errors, or synchronization signatures rather than simple stationary decay; this is why residual analysis needs time correlation tests. citeturn4search3turn5search15turn1search18  
- **Drive amplitude dependence:** strong drives can heat substrates or populate phonon modes indirectly; but distinguishing intrinsic phonon coupling from classical dissipation is nontrivial. citeturn1search15turn4search3  
- **Magnetic hysteresis:** not a primary discriminator.  
- **Geometry scaling:** supportive; phononic bandgaps and substrate stack-ups create engineered geometric dependence. citeturn4search7turn4search26  

**Counterpoint:** in most “standard” planar processor experiments, phonon coupling is not uniquely inferable without time synchronization or engineered phononic structures because its observable footprint overlaps with QP bursts and classical heating. citeturn4search16turn4search29turn9search5

### Control-line noise and wiring-induced decoherence

If you are not doing noise spectroscopy, you are guessing.

Control lines couple the qubit to external noise across a wide frequency range; cryogenic line design must trade coupling strength for control/readout against isolation from thermal and technical noise. citeturn9search5turn9search4turn9search2

Low-frequency dephasing in flux-sensitive devices is often dominated by 1/f-type noise; classic experiments show Gaussian echo decay consistent with 1/f flux noise, and dynamical decoupling can be used both to suppress dephasing and to *reconstruct the noise spectrum*. citeturn1search0turn1search5turn1search1

Flux noise is widely attributed to surface spins, and ESR work has directly identified dilute surface spins consistent with being a flux-noise source. citeturn10search2turn10search6turn10search0

**How the five requested observables behave:**

- **T1(T):** usually not diagnostic because line noise is often technical and depends on filtering/attenuation rather than intrinsic thermal activation at the chip. citeturn9search5turn9search6  
- **Ramsey/T2 structure:** primary; 1/f noise yields non-exponential envelopes (often Gaussian in appropriate limits) and characteristic improvements under echo/CPMG whose scaling reveals spectral content. citeturn1search0turn1search1turn10search0  
- **Drive amplitude dependence:** supporting; AM/PM noise can convert into effective dephasing under driven evolution, but chain distortions must be excluded. citeturn9search5turn6search4  
- **Magnetic hysteresis:** usually weak, except that applying weak fields can shift the spin environment and flux noise trends in some regimes. citeturn1search8turn10search10  
- **Geometry scaling:** supporting; mutual inductance/coupling changes sensitivity to flux-line noise and technical noise, but this is rarely unique without dedicated noise injections. citeturn9search5turn6search4  

**Counterpoint:** “flux noise” and “control-line noise” are routinely conflated. Flux noise can be intrinsic (surface spins) rather than imported through wiring, and wiring improvements alone do not fix it. citeturn10search2turn10search15

## Lindblad baseline models and residual-structure analysis

Your prompt explicitly targets a minimal Lindblad model, then asks whether residuals contain structured deviations that would invalidate “Lindblad-suffices” narratives.

### Minimal model class

A workhorse baseline for a single qubit is a GKSL/Lindblad master equation with:

- amplitude damping (|1⟩→|0⟩)  
- thermal excitation (|0⟩→|1⟩) parameterized by an effective bath occupation  
- pure dephasing (σz channel)  
- optional additional jump operators capturing quasiparticle-induced transitions or parity-conditioned rates (depending on device). citeturn6search1turn0search14turn0search2turn6search10

This baseline is the operationalization of the Bloch-Redfield picture widely used for superconducting qubits under weak-coupling/Markov approximations; it is not “fundamental truth,” merely a tractable model class that often fits first-order decay curves. citeturn6search1turn6search10turn6search4

If your goal is identifiability (not just curve-fitting), you should treat the baseline as a **null hypothesis** to be falsified, not as an article of faith.

### What qualifies as “structured residuals”

Residual analysis should be done on the *time series of measured observables*, not on reduced coherence-time numbers. Coherence benchmarking work shows that T1 and T2* drift and fluctuate with long correlation times; without modeling this, residual tests are meaningless. citeturn5search15turn1search18turn1search6

The residuals that actually matter:

- **Correlated residuals:** non-white residual autocorrelation suggests missing dynamics (non-Markovianity, parameter drift, spectral diffusion), or unmodeled experimental systematics. citeturn1search18turn6search26turn1search14  
- **Non-Gaussian residual distributions:** heavy tails and burstiness are consistent with telegraph fluctuators, QP bursts, radiation events, or mechanical-vibration coupling. citeturn4search16turn4search3turn1search28  
- **Drive-conditional residual shifts:** if fitted decay parameters depend on drive amplitude or pulse type beyond what your model encodes, you may be seeing TLS saturation, drive-induced QPs, or classical chain distortions. citeturn5search10turn1search15turn9search5  
- **Ramsey-envelope mismatches:** 1/f noise and related slow processes produce non-exponential envelopes and can generate asymmetries/beatings inconsistent with Markovian Lindblad dynamics. citeturn1search0turn6search3turn10search0  

### How to fit without fooling yourself

A sane workflow:

1. Fit the Lindblad baseline to **multiple experiments jointly** (T1, Ramsey, echo/CPMG, and—if available—parity-tagged data), not to each curve independently; otherwise you introduce artificial agreement. citeturn1search5turn0search2turn6search10  
2. Include a simple **hierarchical drift model** (slowly varying rates) because T1 fluctuations are empirically large and correlated; treating rates as constant is often wrong. citeturn1search18turn5search15turn1search6  
3. Evaluate model adequacy with residual whiteness tests and with cross-validation across days rather than within a single run (because nonstationarity dominates). citeturn5search15turn1search22  

If you want a more direct route to the generator, Lindblad tomography frameworks exist and have been demonstrated on superconducting processors; these can help separate Hamiltonian and dissipator parameters while exposing non-Markovian features. citeturn11search2turn11search7turn6search2

**Counterpoint:** residual structure is not automatically “new physics.” Pulse distortions, calibration drift, and readout nonlinearities can generate the same pathologies. Cryogenic wiring/control reviews emphasize exactly how many ways classical infrastructure contaminates your inferred noise model. citeturn9search5turn9search4turn9search2

## Vortex entry thresholds and refrigerator magnetic environment

Your prompts 3 and 4 are coupled: predicting vortex entry fields is useless unless you know (or can bound) the magnetic field environment near the chip during cooldown and operation.

### Vortex entry and trapping thresholds

For thin-film strips, vortex trapping/expulsion is governed by geometry and by thin-film electrodynamics; key scale is the **Pearl length** Λ = 2λ²/d, which becomes large in thin films and alters screening and vortex energetics near Tc. citeturn2search1turn2search5

Models and experiments on thin-film strips show that trapping occurs above a critical field that depends on strip width and energetics of vortex–antivortex formation and pinning. citeturn2search1turn2search5turn2search13

Edge barriers (Bean–Livingston-type and geometric barriers) are sensitive to corner geometry and defects; controlled defect modulation near edges can measurably suppress or alter entry barriers. citeturn2search0turn2search12turn2search32

The upshot for identifiability: geometry changes (width, thickness, edge condition) are not merely engineering tweaks—they produce **order-of-magnitude changes** in vortex susceptibility, which is exactly what you need to separate vortex loss from TLS/QP loss.

### Magnetic environment reconstruction inside a dilution refrigerator

Two points are robust even when the details are not:

- Ambient fields during cooldown trap flux as vortices, creating additional loss; controlling the magnetic environment is a standard requirement for high-Q superconducting devices. citeturn7search30turn3search12turn3search15  
- Achieving milligauss-level fields requires deliberate multi-layer shielding and careful ferromagnetic hygiene (fasteners, connectors, cable materials), not wishful thinking. citeturn3search15turn2search26turn9search2  

Cooldown protocol matters. Work in SRF contexts (which is not qubit-identical but is physically relevant) shows trapped flux and residual resistance scaling with ambient field and with temperature gradients during cooldown, providing a framework for why “how you cool” changes vortex trapping outcomes. citeturn2search3turn2search7

For superconducting quantum circuits specifically, there is experimental evidence that trapped flux and applied static fields can, within limits, suppress temporal T1 fluctuations without strongly degrading average T1—again illustrating that vortices can act not only as a loss channel but also as a quasiparticle sink depending on where they sit relative to current antinodes/nodes. citeturn3search5turn7search0turn8view6

**Counterpoint:** direct field mapping at millikelvin temperatures is hard; any “magnetic environment reconstruction” will be model-dominated unless you validate it with in-situ magnetometry or with qubit/resonator-based proxy measurements. This is why hysteresis tests and cooldown-field sweeps are more actionable than elaborate finite-element magnetostatics alone. citeturn7search2turn3search15turn2search9

## Materials and geometry scaling for TLS-dominant regimes

Your prompts 5 and 7 ask for a comparative analysis across fabrication and across device geometries. The experimentally validated lens is: **participation ratios + materials-specific loss tangents + process-dependent surface quality**. citeturn8view5turn5search28turn5search6

### Fabrication-to-loss mapping that is already defensible

- Tantalum-based transmons fabricated with stable processes have achieved large T1 improvements (hundreds of microseconds) compared to niobium/aluminum under similar design constraints. citeturn8view1turn0search19  
- Loss budgeting work explicitly ties improved coherence to reduced surface and bulk dielectric losses, annealed substrates, and geometry that reduces lossy participation. citeturn8view0turn9search3turn5search21  
- Recent results report millisecond-class lifetimes and coherence in 2D transmons via materials platforms and process control, emphasizing that materials improvements translate to scalable processors. citeturn12search2turn12search27  
- Nb-based approaches can also yield systematic improvements when the lossy oxide formation is mitigated (e.g., encapsulation strategies), reinforcing that “material platform” is broader than a single metal choice. citeturn0search7  

These provide an empirical backbone for your proposed “material property matrix,” even though batch-to-batch variability remains a real confound.

### Geometry scaling across architectures

The canonical demonstration that “geometry matters” is the progression from planar transmons to 3D cQED architectures yielding large coherence gains, followed by quantitative participation-ratio studies showing relaxation scaling with surface participation when QPs are suppressed and the electromagnetic environment is clean. citeturn5search0turn8view5turn5search21

On-chip coaxial and quasi-coaxial architectures are a more recent evolution: they deliberately reshape field distributions to suppress participation in lossy interfaces and packaging modes, yielding millisecond-scale single-photon Ramsey times in on-chip quantum memories. citeturn8view0turn9search15

**Counterpoint:** “geometry scaling” is only interpretable if you hold fabrication fixed; otherwise you end up attributing process variation to geometry. This is exactly why careful participation-ratio modeling paired with controlled fabrication comparisons is the only respectable path. citeturn8view0turn5search21turn5search28

## Minimal discriminator experiments and a Hamiltonian-modification falsification protocol

Your prompts 6, 8, 9, and 10 converge to one operational objective: don’t hypothesize Hamiltonian corrections until classical mechanisms are exhausted under controlled perturbations.

### Noise spectral density reconstruction as an identifiability engine

Dynamical decoupling is not just “error mitigation”; it is **spectroscopy**. Experiments demonstrate reconstruction of environmental noise spectra using the filter-function properties of sequences like CPMG, with strong improvements in T2 when low-frequency noise dominates. citeturn1search1turn1search5

For flux noise, Gaussian Ramsey/echo envelopes and their bias dependence provide direct evidence of 1/f spectra and allow extraction of noise magnitudes. citeturn1search0turn1search24turn10search0

This directly answers your prompt 8: the only honest claim you can make about S(ω) is over the frequency band your control sequences probe; outside that band, it is underdetermined unless you add additional probes. citeturn1search1turn11search7

### Drive-amplitude nonlinearity mapping with meaningful controls

To decide whether “nonlinear Hamiltonian corrections” are needed, you must first separate three effects:

- TLS saturation (decoherence *decreases* with power in the TLS-limited regime) citeturn5search10turn5search6  
- drive-induced quasiparticles (decoherence *increases* when pair-breaking channels activate) citeturn1search15turn1search19  
- classical distortions/heating in the microwave chain (which masquerade as intrinsic amplitude dependence) citeturn9search5turn9search4  

The correct experimental design uses (i) calibrated in-situ power at the device (not room-temperature generator settings), (ii) repetition across different attenuation/filter configurations, and (iii) cross-checks with parity/QP indicators where possible.

### Smallest experiment to separate vortex loss from TLS loss

A minimal discriminator protocol that is actually executable in a standard dilution refrigerator:

1. Use two otherwise identical chips (or two regions on one chip) differing only in **vortex susceptibility geometry** (strip widths/thicknesses expected to alter vortex trapping thresholds). citeturn2search1turn2search17  
2. For each geometry, run a **cooldown field sweep** (including both positive and negative fields) with controlled magnetic history and measure T1 plus resonator Q if available; look for hysteresis and sharp threshold behavior. citeturn7search2turn7search30  
3. At a fixed low field (Meissner-favored), run a **power dependence scan** at the relevant frequencies to test TLS saturation signatures. citeturn5search10turn5search6  
4. If coherence improves under controlled vortex trapping while hysteresis signatures appear, you are seeing vortex/QP interplay rather than pure TLS. If coherence degrades with clear hysteresis and geometry thresholding, vortex loss is dominant. If power dependence dominates while field history does little, TLS is the likely ceiling.

This is minimal because it uses only field coil control + standard coherence measurements, yet it gives you orthogonal discriminators.

**Counterpoint:** multiple mechanisms can contribute simultaneously; the aim is not to crown a single winner but to bound contributions with perturbations strong enough to change one mechanism at a time. citeturn8view2turn0search20turn0search10

### Hamiltonian modification falsification protocol

A disciplined falsification workflow consistent with your prompt 10:

- **Stage A: Lindblad null model.** Fit a baseline GKSL/Lindblad model to a multi-experiment dataset, incorporating rate drift as needed. citeturn6search10turn1search18  
- **Stage B: Residual diagnostics.** Demand whiteness and stationarity; if residuals show correlations, treat “Markovian Lindblad” as falsified. citeturn6search26turn1search18  
- **Stage C: Mechanism-specific noise channels.** Before touching the Hamiltonian, test whether added dissipators/noise spectra (1/f dephasing, TLS spectral diffusion, QP-driven transitions) eliminate residual structure. citeturn10search0turn1search6turn0search2turn0search14  
- **Stage D: Experimental artifact elimination.** Swap line filtering/attenuation, vary pulse shapes, measure distortion, synchronize to pulse-tube cycle; eliminate classical explanations. citeturn9search5turn4search3turn9search2  
- **Stage E: Only then consider Hamiltonian corrections.** If residual structure survives A–D and is reproducible across calibrations and setups, then (and only then) introduce Hamiltonian-level modifications and demand that they predict new, orthogonal observables—not just improve fit by adding degrees of freedom. The bar should be higher than “better least squares.”

This is not philosophical; it is how you avoid mistaking “unmodeled wiring noise” for “new coherent dynamics.” citeturn9search5turn11search7turn6search10