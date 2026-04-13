# MMM Geometry Specifications

## Common geometry rules
- Keep Josephson junction and immediate electrodes outside unintended high-field metamaterial unit cells unless explicitly co-designed.
- Hold package, launch, and readout couplings fixed between candidate and sham variants.
- Treat membrane release, lid spacing, and interposer spacing as explicit design variables rather than uncontrolled assembly outcomes.
- All geometry-series masks must include SEM / profilometry monitors and sham controls.

## Structure parameter dictionary

## STR-EM-CPW-EBG-RING — CPW electromagnetic bandgap ring

- **Family:** planar_photonic_crystal
- **Topology:** Concentric or surround ring of periodic CPW unit cells around the qubit island and readout neck
- **Implements:** MECH-EM-001
- **Integration interface:** top metal layer around qubit / resonator perimeter / galvanically isolated or weakly coupled boundary structure
- **Materials:** superconducting Al or NbTiN trace, high-resistivity Si or sapphire substrate
- **Fabrication level:** standard
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| lattice_constant_um | [180, 520] |
| cell_count | [6, 32] |
| line_width_um | [8, 24] |
| gap_width_um | [6, 18] |
| impedance_contrast | [1.5, 4.0] |
| target_stopband_GHz | [4.0, 8.5] |

**Notes**
Primary EM stopband candidate for planar devices.

## STR-EM-LID-HIS — High-impedance metasurface lid or interposer

- **Family:** high_impedance_surface
- **Topology:** Periodic patch or mushroom surface on lid / interposer above device
- **Implements:** MECH-EM-001, MECH-EM-002
- **Integration interface:** device lid or removable interposer / floating boundary surface
- **Materials:** Cu/Au plated lid with superconducting coating optional, silicon or sapphire interposer optional, indium or spacer stand-off
- **Fabrication level:** standard
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| patch_pitch_um | [200, 1500] |
| patch_size_um | [120, 1200] |
| gap_um | [10, 100] |
| lid_spacing_um | [50, 1000] |
| target_stopband_GHz | [4.0, 12.0] |

**Notes**
Low-risk packaging branch with direct package-mode metrology.

## STR-EM-HKI-FENCE — High-kinetic-inductance fence / slotline suppressor

- **Family:** periodic_ground_engineering
- **Topology:** Perimeter fence or inductive bridge lattice using high-kinetic-inductance segments
- **Implements:** MECH-EM-001, MECH-EM-002, MECH-EM-003
- **Integration interface:** ground-plane gaps, package interface perimeter, control-line transitions / galvanic ground engineering
- **Materials:** NbTiN, TiN, or granular Al HKI film, baseline Al/Nb ground plane, Si or sapphire substrate
- **Fabrication level:** advanced_standard
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| fence_pitch_um | [40, 300] |
| bridge_length_um | [10, 100] |
| strip_width_um | [0.1, 2.0] |
| gap_to_ground_um | [2, 20] |
| target_common_mode_band_GHz | [2.0, 20.0] |

**Notes**
Supports slotline suppression and boundary engineering; must be compared to ordinary bridge fixes.

## STR-PH-SOI-JJ-PHC — Junction-local SOI phononic crystal

- **Family:** local_phononic_crystal
- **Topology:** Released membrane or localized suspended region with periodic holes / necks beneath and around the Josephson junction region
- **Implements:** MECH-PH-001
- **Integration interface:** local to junction capacitor neck or island edge / mechanically structured substrate under active device
- **Materials:** SOI device layer Si, Al or Ta junction stack, optional SiNx hard mask
- **Fabrication level:** advanced_standard
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| lattice_constant_nm | [250, 700] |
| neck_width_nm | [40, 180] |
| slot_or_hole_size_nm | [120, 500] |
| membrane_thickness_nm | [150, 400] |
| cell_count | [5, 20] |
| target_gap_GHz | [3.0, 10.0] |

**Notes**
Lead phononic branch. Release window kept local to preserve yield.

## STR-PH-SOI-FULLCAP-PHC — Full-capacitor SOI phononic crystal

- **Family:** extended_phononic_crystal
- **Topology:** Phononic lattice spanning most of capacitor footprint or qubit body on suspended/structured substrate
- **Implements:** MECH-PH-001
- **Integration interface:** below full capacitor or resonator section / structured support under high-participation region
- **Materials:** SOI or membrane Si, Al, Ta, or Nb device metal
- **Fabrication level:** advanced_standard
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| lattice_constant_nm | [300, 900] |
| neck_width_nm | [50, 220] |
| hole_or_cross_size_nm | [150, 650] |
| membrane_thickness_nm | [150, 500] |
| fill_factor | [0.2, 0.7] |
| target_gap_GHz | [2.5, 8.0] |

**Notes**
Higher signal potential, lower fabrication robustness than local PHC.

## STR-PH-GRADED-SINK — Graded phonon sink / acoustic black-hole ring

- **Family:** phonon_escape_router
- **Topology:** Radially graded acoustic impedance or tapered trench network guiding phonons away from active region
- **Implements:** MECH-PH-002
- **Integration interface:** annular region around qubit / resonator / injector / acoustic only
- **Materials:** Si or sapphire substrate, etched trenches / variable-thickness regions, optional metal sink pad
- **Fabrication level:** standard
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| sink_radius_um | [20, 400] |
| taper_angle_deg | [2, 30] |
| stage_count | [2, 8] |
| gradient_strength | [0.2, 2.0] |
| escape_channel_width_um | [1, 20] |

**Notes**
Best branch for explicit phonon-routing tests with QP injection.

## STR-PH-SAW-BRAGG — Surface-acoustic-wave Bragg lattice

- **Family:** saw_bandstop
- **Topology:** Periodic etched or piezoelectric SAW reflector with witness IDTs
- **Implements:** MECH-PH-003
- **Integration interface:** witness lane adjacent to device or dedicated test die / IDT transducers
- **Materials:** Al on Si with interface piezoelectricity, optional AlN or LiNbO3 piezo layer, IDT witness metal
- **Fabrication level:** advanced_standard
- **Exotic flag:** True

| Parameter | Range / value |
| --- | --- |
| period_nm | [200, 2000] |
| duty_cycle | [0.2, 0.8] |
| aperture_um | [20, 400] |
| pair_count | [10, 200] |
| piezo_thickness_nm | [50, 1000] |

**Notes**
Explicitly exotic because piezo integration is not baseline qubit process.

## STR-QP-GAP-LATTICE — Gap-contrast quasiparticle trap lattice

- **Family:** gap_engineered_trap_network
- **Topology:** Periodic lower-gap islands or normal-metal traps surrounding active region
- **Implements:** MECH-QP-001
- **Integration interface:** qubit perimeter and leads / diffusion-path engineering
- **Materials:** Al base layer, Cu/Au/Pd normal metal or lower-gap superconducting trap metal, optional oxide barrier
- **Fabrication level:** standard
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| trap_pitch_um | [2, 50] |
| trap_size_um | [0.5, 20] |
| distance_to_junction_um | [5, 200] |
| coverage_fraction | [0.01, 0.25] |
| gap_contrast_meV | [0.01, 0.3] |

**Notes**
High confound risk; must be benchmarked against non-periodic trap controls.

## STR-VX-ANTIDOT-LATTICE — Antidot vortex-pinning lattice

- **Family:** vortex_pinning_lattice
- **Topology:** Periodic or graded hole array placed in low-field-participation regions and feedline grounds
- **Implements:** MECH-VX-001
- **Integration interface:** ground planes, feedline edges, cavity current nodes / superconducting film perforation
- **Materials:** Al, Nb, Ta, or NbTiN film on Si or sapphire
- **Fabrication level:** standard
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| antidot_radius_um | [0.2, 5.0] |
| pitch_um | [0.5, 20.0] |
| edge_offset_um | [2, 100] |
| grading_factor | [0.5, 2.0] |
| coverage_fraction | [0.01, 0.4] |

**Notes**
Primarily baseline-null architecture; included because periodic structures can masquerade as metamaterial effects.

## STR-3D-CAVITY-LINER — 3D cavity corrugated liner / insert

- **Family:** three_dimensional_metamaterial_boundary
- **Topology:** Machined corrugation or inserted periodic liner inside cavity wall
- **Implements:** MECH-3D-001
- **Integration interface:** inside 3D cavity wall or as removable insert / cavity boundary condition
- **Materials:** bulk Nb, Al, OFHC Cu with superconducting coating, sapphire or Si insert optional
- **Fabrication level:** machine_shop_plus_clean_assembly
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| corrugation_period_mm | [0.2, 5.0] |
| corrugation_depth_mm | [0.1, 3.0] |
| fill_fraction | [0.1, 0.9] |
| insert_distance_mm | [0.1, 10.0] |
| target_mode_GHz | [3.0, 12.0] |

**Notes**
3D screening branch with straightforward assembly replication.

## STR-HYB-BILAYER-INTERPOSER — Hybrid EM-phononic bilayer interposer

- **Family:** hybrid_interposer
- **Topology:** Two-layer interposer with microwave stopband pattern and acoustic membrane or graded sink features
- **Implements:** MECH-PH-002, MECH-HYB-001
- **Integration interface:** between device chip and lid or as bonded substrate / near-field EM boundary + acoustic environment
- **Materials:** patterned Si or sapphire interposer, superconducting top metal, released or etched acoustic layer
- **Fabrication level:** advanced_exotic
- **Exotic flag:** True

| Parameter | Range / value |
| --- | --- |
| em_pitch_um | [100, 1000] |
| phononic_pitch_nm | [250, 800] |
| spacer_um | [5, 200] |
| alignment_tolerance_um | [0.2, 5.0] |
| active_area_mm | [0.5, 10.0] |

**Notes**
Sandbox-only until single-domain branches mature.

## STR-CTRL-BANDSTOP-INTERPOSER — Control-line bandstop interposer

- **Family:** metamaterial_filter_section
- **Topology:** Periodic resonant section or interposer inserted in control/readout path near device package
- **Implements:** MECH-EM-003, MECH-EM-004
- **Integration interface:** control/readout line segment proximal to sample box or on-chip launch region / series inline filter / shunt-resonant network
- **Materials:** Si interposer or PCB-like cryogenic laminate, superconducting NbTiN/Al or normal-metal reference
- **Fabrication level:** standard
- **Exotic flag:** False

| Parameter | Range / value |
| --- | --- |
| cell_pitch_um | [50, 1000] |
| cell_count | [2, 40] |
| line_impedance_ohm | [30, 80] |
| via_inductance_pH | [1, 500] |
| target_stopband_GHz | [6.0, 100.0] |

**Notes**
Designed to explicitly challenge control-noise and pair-breaking leakage hypotheses.
