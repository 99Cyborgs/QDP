# QDP Vortex Pinning Reference

### Practical Device Guidance for Superconducting Thin Films and Resonators

---

# 1. Purpose

This document summarizes experimentally relevant mechanisms for **vortex pinning and vortex driven microwave loss** in superconducting thin films used in qubits and resonators.

The goal is operational: provide **design rules, diagnostics, and modeling hooks** that allow discrimination between vortex driven dissipation and other decoherence channels such as TLS, quasiparticles, or phonon coupling.

This reference is structured to plug directly into the **Quantum Decoherence Program (QDP)** modeling and experimental workflow.

---

# 2. Basic Vortex Physics in Thin Films

When a magnetic field penetrates a type II superconductor above the lower critical field (H_{c1}), flux enters in quantized vortices.

Each vortex carries a single flux quantum:

[
\Phi_0 = \frac{h}{2e}
]

A vortex consists of

• a **normal core**
• circulating supercurrents
• a magnetic flux line through the film

In thin films the electromagnetic field spreads laterally across the film thickness scale, creating **Pearl vortices** rather than bulk Abrikosov vortices.

The characteristic scale is the **Pearl length**

[
\Lambda = \frac{2\lambda^2}{d}
]

where

• ( \lambda ) = London penetration depth
• ( d ) = film thickness

Typical values

| Material | Film thickness | Pearl length |
| -------- | -------------- | ------------ |
| Nb       | 100 nm         | 20 to 100 µm |
| Ta       | 50 to 150 nm   | 30 to 150 µm |

Because Pearl lengths are large, vortices interact strongly with **device edges and patterned defects**.

---

# 3. Why Vortices Cause Microwave Loss

In resonators or qubits, microwave currents exert a Lorentz force on vortices:

[
F_L = J \times \Phi_0
]

If vortices move, energy is dissipated via normal core motion.

Microwave loss arises through **vortex oscillation around pinning sites**.

Two regimes occur.

### 3.1 Strong pinning regime

Vortices remain trapped.

Motion amplitude is small.

Loss contribution is weak.

### 3.2 Weak pinning regime

Vortices oscillate over larger distances.

Dissipation becomes significant.

Loss increases rapidly with field.

---

# 4. Depinning Frequency

The central parameter is the **vortex depinning frequency**

[
\omega_p = \frac{k_p}{\eta}
]

Where

• (k_p) = pinning spring constant
• ( \eta ) = vortex viscous drag

Interpretation:

| Frequency regime         | Behavior                 |
| ------------------------ | ------------------------ |
| ( \omega \ll \omega_p )  | vortex pinned            |
| ( \omega \sim \omega_p ) | partial motion           |
| ( \omega \gg \omega_p )  | vortex freely oscillates |

Typical values

| Material      | Depinning frequency |
| ------------- | ------------------- |
| Nb thin films | 1 to 10 GHz         |
| Ta thin films | 0.5 to 5 GHz        |

Because qubit frequencies fall in the **3 to 8 GHz range**, vortex depinning often occurs **directly inside the operating band**.

This is why even a small number of vortices can reduce resonator Q.

---

# 5. Sources of Vortex Entry

Vortices enter devices through several mechanisms.

### 5.1 Ambient magnetic field during cooldown

Even the Earth field (~50 µT) can trap vortices.

### 5.2 Edge barrier breakdown

Thin film edges reduce vortex entry energy.

### 5.3 Local field concentration

Ground plane gaps and CPW edges amplify magnetic fields.

---

# 6. Flux Trapping Patterns

Magneto optical imaging and scanning SQUID studies show three major penetration patterns.

### 6.1 Bean critical state

Flux gradually penetrates from edges.

This is stable and predictable.

### 6.2 Dendritic avalanches

Thermomagnetic instability produces branching flux fingers.

These appear abruptly and trap large vortex densities.

### 6.3 Channel guided flux

Vortices follow grain boundaries or film defects.

These produce highly localized loss hotspots.

---

# 7. Artificial Pinning Strategies

Engineering strong pinning sites dramatically reduces microwave loss.

Three strategies are currently effective.

---

## 7.1 Antidot Arrays

Antidots are lithographically patterned holes.

They act as vortex traps.

Typical parameters

| Parameter     | Value          |
| ------------- | -------------- |
| Hole diameter | 100 nm to 1 µm |
| Spacing       | 1 to 10 µm     |

Advantages

• strong pinning potential
• deterministic vortex placement

Tradeoff

• excessive holes increase surface loss.

---

## 7.2 Quasiperiodic Pinning Lattices

Pinning sites arranged in **Penrose or quasicrystal patterns**.

Advantages

• suppress vortex channeling
• reduce collective vortex motion

These structures outperform periodic arrays in several experiments.

---

## 7.3 Micro engineered defect lines

Examples

• ion irradiated tracks
• controlled grain boundaries
• nanoparticle inclusions

These increase the pinning constant (k_p).

---

# 8. Material Specific Observations

## Niobium Films

Recent magneto optical imaging studies show:

• sputtering parameters strongly affect pinning landscapes
• smooth films exhibit dendritic avalanches
• controlled disorder stabilizes flux penetration

Films with moderate defect density show

• higher critical current
• reduced microwave vortex loss.

---

## Tantalum Resonators

Recent resonator measurements indicate:

• ultra clean Ta films contain few natural pinning sites
• vortices move thermally even at millikelvin temperatures

Artificial pinning structures such as **micron scale holes** significantly reduce anomalous loss.

---

# 9. Minimal Experimental Protocol

### Vortex Mechanism Identification

Before expanding modeling, determine whether vortex loss is present.

Recommended protocol.

---

## Step 1: Field dependent Q measurement

Procedure

1. Cool device in zero field
2. Apply small perpendicular field
3. Measure resonator Q vs field

Signature

```
Q^{-1} increases approximately linearly with field
```

This strongly indicates vortex loss.

---

## Step 2: Field sweep hysteresis test

Procedure

1. ramp magnetic field up
2. ramp field down

Signature

```
Q does not return to original value
```

This indicates trapped vortices.

---

## Step 3: Warm up above Tc and re cool

If loss disappears after warm up, vortex trapping is confirmed.

---

# 10. Modeling Hooks for QDP

Vortex motion can be incorporated into decoherence modeling through an additional loss term.

Example resonator dissipation model.

[
\frac{1}{Q} =
\frac{1}{Q_{TLS}}
+
\frac{1}{Q_{qp}}
+
\frac{1}{Q_{vortex}}
]

The vortex term follows

[
Q_{vortex}^{-1} \propto
\frac{B}{1 + (\omega / \omega_p)^2}
]

Observable predictions

| Parameter sweep | Expected scaling            |
| --------------- | --------------------------- |
| magnetic field  | linear                      |
| frequency       | Lorentzian around depinning |
| temperature     | weak dependence             |

These scaling relations allow mechanism discrimination.

---

# 11. Engineering Design Rules

Condensed operational guidance.

### Fabrication

• maintain moderate defect density
• avoid ultra perfect films without pinning

### Geometry

• minimize ground plane gaps
• avoid large current crowding at edges

### Magnetic hygiene

• μ metal shielding
• zero field cooldown

### Intentional pinning

• sparse antidot lattices near resonator current nodes.

---

# 12. Key Experimental Diagnostics

High value measurement tools.

Magneto optical imaging
Scanning SQUID microscopy
Cryogenic Hall probe mapping
Microwave loss vs field sweeps

These techniques directly visualize vortex configurations.

---

# 13. Strategic Relevance for QDP

Vortex driven dissipation satisfies several QDP constraints.

Identifiable scaling:

• magnetic field dependence
• hysteresis behavior
• geometry dependence

This makes vortex mechanisms **ideal first stage discrimination targets** before introducing Hamiltonian level nonlinear modifications.

---

# 14. Immediate Next Steps for Simulation

Recommended modules.

1. CPW vortex current density solver
2. vortex depinning response model
3. geometry dependent pinning simulation

These allow direct comparison between

• device geometry
• pinning landscape
• measured resonator Q.

---

# End
