# MMM Fabrication Methods

## Program-wide fabrication rules
- Every fabrication lot must include sham controls, monitor structures, and witness structures.
- As-built metrology is part of the scientific claim, not only process QA.
- Exotic processes are allowed only when flagged and isolated from lead-branch dependency.


## STR-EM-CPW-EBG-RING — CPW electromagnetic bandgap ring

- **Cleanroom level:** standard
- **Exotic flag:** False
- **Process flow:** superconducting film deposition, optical_or_e-beam patterning, dry etch or lift-off

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-EM-LID-HIS — High-impedance metasurface lid or interposer

- **Cleanroom level:** standard
- **Exotic flag:** False
- **Process flow:** lid machining or wafer interposer, metal patterning, optional bump/spacer assembly

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-EM-HKI-FENCE — High-kinetic-inductance fence / slotline suppressor

- **Cleanroom level:** advanced_standard
- **Exotic flag:** False
- **Process flow:** multilayer or single-layer HKI deposition, fine-line lithography, bridge/crossover integration if needed

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-PH-SOI-JJ-PHC — Junction-local SOI phononic crystal

- **Cleanroom level:** advanced_standard
- **Exotic flag:** False
- **Process flow:** junction patterning, front-side phononic lattice lithography, selective release / undercut, critical point dry optional

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-PH-SOI-FULLCAP-PHC — Full-capacitor SOI phononic crystal

- **Cleanroom level:** advanced_standard
- **Exotic flag:** False
- **Process flow:** large-area phononic lithography, release/etch, stress control metrology

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-PH-GRADED-SINK — Graded phonon sink / acoustic black-hole ring

- **Cleanroom level:** standard
- **Exotic flag:** False
- **Process flow:** multi-depth etch or graded patterning, optional backside thinning, no mandatory membrane release for baseline design

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-PH-SAW-BRAGG — Surface-acoustic-wave Bragg lattice

- **Cleanroom level:** advanced_standard
- **Exotic flag:** True
- **Process flow:** piezo deposition optional, IDT lithography, Bragg etch or metal patterning

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-QP-GAP-LATTICE — Gap-contrast quasiparticle trap lattice

- **Cleanroom level:** standard
- **Exotic flag:** False
- **Process flow:** multimetal deposition, trap alignment lithography, surface-clean requirement

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-VX-ANTIDOT-LATTICE — Antidot vortex-pinning lattice

- **Cleanroom level:** standard
- **Exotic flag:** False
- **Process flow:** single-layer lithography or etch, CD metrology, field-cool witness design

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-3D-CAVITY-LINER — 3D cavity corrugated liner / insert

- **Cleanroom level:** machine_shop_plus_clean_assembly
- **Exotic flag:** False
- **Process flow:** precision machining, surface polish, optional insert fabrication, assembly metrology

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-HYB-BILAYER-INTERPOSER — Hybrid EM-phononic bilayer interposer

- **Cleanroom level:** advanced_exotic
- **Exotic flag:** True
- **Process flow:** multilayer patterning, possibly bonded interposer, alignment assembly

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level

## STR-CTRL-BANDSTOP-INTERPOSER — Control-line bandstop interposer

- **Cleanroom level:** standard
- **Exotic flag:** False
- **Process flow:** interposer lithography, through-substrate vias optional, wirebond or flip-chip attach

**Metrology checkpoints**
- SEM/CD monitor for critical dimensions
- Film thickness and sheet resistance check
- As-built geometry export to simulator
- Witness coupon retained for each mask level


## Release-risk controls
- Membrane releases require anchor-stress simulations and handling fixtures.
- Interposer alignment processes require spacer metrology and removable calibration coupons.
- 3D cavity branches require assembly torque and seam-prep logs.
