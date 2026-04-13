# MMM Device Integration Specification

## Integration doctrine
- Hold device Hamiltonian parameters fixed as much as possible while changing only the environment-engineering structure.
- Pair every candidate integration with a sham geometry preserving fill factor or package loading where possible.
- Include at least one witness structure whenever direct band verification is otherwise ambiguous.


## transmon

- **Integration modes:** on-chip perimeter EM bandgap ring, local phononic crystal under junction neck / capacitor edge, lid/interposer boundary structure, control-line bandstop interposer
- **Allowed structures:** STR-EM-CPW-EBG-RING, STR-EM-LID-HIS, STR-EM-HKI-FENCE, STR-PH-SOI-JJ-PHC, STR-PH-SOI-FULLCAP-PHC, STR-PH-GRADED-SINK, STR-PH-SAW-BRAGG, STR-QP-GAP-LATTICE, STR-CTRL-BANDSTOP-INTERPOSER, STR-HYB-BILAYER-INTERPOSER
- **Primary metrics:** OBS-T1-MEAN, OBS-T2STAR, OBS-QP-PARITY, OBS-T1-NMARK
- **Readout modes:** dispersive resonator, time-domain parity monitor, witness resonator
- **Preferred witnesses:** SAW lane, package through-line, adjacent resonator

**Keepout rules**
- No metamaterial metal within 3 um of junction electrodes unless explicitly modeled.
- No membrane release directly under large bond pads.
- Maintain readout resonator coupling geometry constant across sham and candidate variants.

**Packaging note**
Use same sample box for sham/candidate pairs whenever possible.

## fluxonium

- **Integration modes:** EM bandgap around antenna or readout interfaces, local phononic crystal near junction array anchor or antenna arm, control-line bandstop interposer, package lid HIS
- **Allowed structures:** STR-EM-CPW-EBG-RING, STR-EM-LID-HIS, STR-EM-HKI-FENCE, STR-PH-SOI-JJ-PHC, STR-PH-GRADED-SINK, STR-QP-GAP-LATTICE, STR-CTRL-BANDSTOP-INTERPOSER, STR-HYB-BILAYER-INTERPOSER, STR-3D-CAVITY-LINER
- **Primary metrics:** OBS-T1-MEAN, OBS-T1-NMARK, OBS-T2ECHO, OBS-QP-PARITY
- **Readout modes:** dispersive resonator, relaxometry, parity-sensitive spectroscopy
- **Preferred witnesses:** adjacent resonator, package through-line

**Keepout rules**
- Maintain array inductance and antenna geometry fixed across structure variants.
- Avoid phononic release beneath high-stress array crossovers without anchor simulation.

**Packaging note**
Flux-tunable devices require explicit field-history logs for every cooldown.

## planar_resonator

- **Integration modes:** witness resonator for EM and vortex screening, phononic witness resonator on SOI, SAW witness lane
- **Allowed structures:** STR-EM-CPW-EBG-RING, STR-EM-LID-HIS, STR-EM-HKI-FENCE, STR-PH-SOI-JJ-PHC, STR-PH-SOI-FULLCAP-PHC, STR-PH-SAW-BRAGG, STR-VX-ANTIDOT-LATTICE, STR-CTRL-BANDSTOP-INTERPOSER
- **Primary metrics:** OBS-WITNESS-QI, OBS-VORTEX-SLOPE, OBS-BG-SHIFT
- **Readout modes:** VNA, ringdown, power sweep
- **Preferred witnesses:** through line, field-cool series

**Keepout rules**
- Maintain resonator frequency crowding manageable for multiplexed readout.
- Antidot lattices must be placed away from maximum current density unless intentionally testing loss.

**Packaging note**
Preferred for fast screening before qubit deployment.

## 3d_cavity

- **Integration modes:** corrugated cavity wall, removable liner or insert, lid/interposer boundary structure for hybrid planar-in-cavity variants
- **Allowed structures:** STR-3D-CAVITY-LINER, STR-EM-LID-HIS, STR-HYB-BILAYER-INTERPOSER
- **Primary metrics:** OBS-T1-MEAN, OBS-WITNESS-QI, OBS-PKG-S21
- **Readout modes:** cavity spectroscopy, embedded qubit time-domain
- **Preferred witnesses:** bare cavity mode map, reassembly repeat

**Keepout rules**
- Maintain seam preparation and assembly torque identical across variants.
- Track cavity frequency shifts separately from coherence metrics.

**Packaging note**
Assembly reproducibility is part of validation, not a nuisance variable.

## kinetic_inductance_detector

- **Integration modes:** graded phonon sink, antidot lattice for magnetic robustness, SAW / phononic witness structures
- **Allowed structures:** STR-PH-GRADED-SINK, STR-PH-SAW-BRAGG, STR-VX-ANTIDOT-LATTICE, STR-CTRL-BANDSTOP-INTERPOSER
- **Primary metrics:** OBS-QP-RECOV, OBS-WITNESS-QI, OBS-VORTEX-SLOPE
- **Readout modes:** S21 resonance tracking, pulse injection / recovery
- **Preferred witnesses:** controlled injection coupon

**Keepout rules**
- Maintain absorber geometry constant when comparing phonon-routing structures.
- Field-cool series required for antidot variants.

**Packaging note**
Useful for high-throughput phonon and vortex screening.
