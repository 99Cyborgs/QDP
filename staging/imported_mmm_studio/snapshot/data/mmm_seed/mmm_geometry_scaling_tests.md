# MMM Geometry Scaling Tests

## Geometry-series doctrine
Every active mechanism must have at least one mask series in which the dominant effect is predicted to move with an explicit geometry knob.

| Model | Structure | Geometry variables | Required series size | Acceptance criterion |
| --- | --- | --- | --- | --- |
| GEO-001 | STR-EM-CPW-EBG-RING | lattice_constant_um, cell_count, impedance_contrast | 5 | Monotonic band-center shift and saturating T1 trend recovered after as-built metrology correction. |
| GEO-002 | STR-EM-LID-HIS | patch_pitch_um, patch_size_um, lid_spacing_um | 4 | Removable-lid geometry trend exceeds package-only control trend. |
| GEO-003 | STR-PH-SOI-JJ-PHC | lattice_constant_nm, neck_width_nm, cell_count, membrane_thickness_nm | 5 | Gap shift and memory-score alignment both observed. |
| GEO-004 | STR-PH-SOI-FULLCAP-PHC | fill_factor, lattice_constant_nm, membrane_thickness_nm | 4 | Trend survives after correcting for membrane stress variation. |
| GEO-005 | STR-PH-GRADED-SINK | sink_radius_um, taper_angle_deg, stage_count | 4 | Recovery improvement tracks sink geometry more strongly than trap area or temperature drift. |
| GEO-006 | STR-VX-ANTIDOT-LATTICE | antidot_radius_um, pitch_um, edge_offset_um | 5 | Distinct optimum in field dependence reproduced across cooldowns. |
| GEO-007 | STR-PH-SAW-BRAGG | period_nm, pair_count, piezo_thickness_nm | 4 | Acoustic witness shift matches geometry trend and correlates with any device response. |
| GEO-008 | STR-3D-CAVITY-LINER | corrugation_period_mm, corrugation_depth_mm, insert_distance_mm | 4 | Mode map shift follows machining series and repeats after reassembly. |

## Mask design rules
- All geometry-series masks must include same-density sham structures where feasible.
- Include CD monitors adjacent to each geometry family.
- Export as-built geometry values into the analysis pipeline before model comparison.
