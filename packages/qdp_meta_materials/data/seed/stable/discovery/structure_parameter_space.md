# MMM Structure Parameter Space

## Search-space policy
- Each structure family exposes a bounded parameter space that is wide enough to move target band positions but narrow enough to remain fabricable.
- Discovery engine D2 performs broad space-filling sweeps inside these bounds.
- Discovery engine D5 robustness analysis perturbs each critical dimension according to `mmm_tolerance_models.yaml`.
- Candidates are promoted only if geometry scaling remains interpretable after as-built metrology.

| Structure ID | Family | Primary knobs | Fabrication level | Exotic |
| --- | --- | --- | --- | --- |
| STR-EM-CPW-EBG-RING | planar_photonic_crystal | lattice_constant_um, cell_count, line_width_um, gap_width_um... | standard | no |
| STR-EM-LID-HIS | high_impedance_surface | patch_pitch_um, patch_size_um, gap_um, lid_spacing_um... | standard | no |
| STR-EM-HKI-FENCE | periodic_ground_engineering | fence_pitch_um, bridge_length_um, strip_width_um, gap_to_ground_um... | advanced_standard | no |
| STR-PH-SOI-JJ-PHC | local_phononic_crystal | lattice_constant_nm, neck_width_nm, slot_or_hole_size_nm, membrane_thickness_nm... | advanced_standard | no |
| STR-PH-SOI-FULLCAP-PHC | extended_phononic_crystal | lattice_constant_nm, neck_width_nm, hole_or_cross_size_nm, membrane_thickness_nm... | advanced_standard | no |
| STR-PH-GRADED-SINK | phonon_escape_router | sink_radius_um, taper_angle_deg, stage_count, gradient_strength... | standard | no |
| STR-PH-SAW-BRAGG | saw_bandstop | period_nm, duty_cycle, aperture_um, pair_count... | advanced_standard | yes |
| STR-QP-GAP-LATTICE | gap_engineered_trap_network | trap_pitch_um, trap_size_um, distance_to_junction_um, coverage_fraction... | standard | no |
| STR-VX-ANTIDOT-LATTICE | vortex_pinning_lattice | antidot_radius_um, pitch_um, edge_offset_um, grading_factor... | standard | no |
| STR-3D-CAVITY-LINER | three_dimensional_metamaterial_boundary | corrugation_period_mm, corrugation_depth_mm, fill_fraction, insert_distance_mm... | machine_shop_plus_clean_assembly | no |
| STR-HYB-BILAYER-INTERPOSER | hybrid_interposer | em_pitch_um, phononic_pitch_nm, spacer_um, alignment_tolerance_um... | advanced_exotic | yes |
| STR-CTRL-BANDSTOP-INTERPOSER | metamaterial_filter_section | cell_pitch_um, cell_count, line_impedance_ohm, via_inductance_pH... | standard | no |

## Down-select gates
- Gate P0 — design-rule compliance and mK/package compatibility
- Gate P1 — predicted observable above detectability floor
- Gate P2 — best baseline null cannot explain >80% of predicted effect
- Gate P3 — geometry series exists with at least one internal falsification ladder
- Gate P4 — fabrication robustness passes yield floor
