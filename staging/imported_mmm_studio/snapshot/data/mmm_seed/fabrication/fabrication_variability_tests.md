# MMM Fabrication Variability Tests

## Objective
Quantify whether candidate effects survive realistic process drift and whether any apparent mechanism can be reproduced by ordinary fabrication variation alone.

## Test plan
1. Split-lot same-wafer fabrication for sham and candidate.
2. Intentional mask-bias DOE on critical dimensions.
3. Full metrology capture: SEM/CD, thickness, sheet resistance, junction monitors.
4. As-built simulation update.
5. Correlate performance metrics with measured dimensions.
6. Reject mechanism if fabrication-only model explains the trend.

## Tolerance focus
| Structure | Critical dimensions | Yield floor | Intentional bias DOE |
| --- | --- | --- | --- |
| STR-EM-CPW-EBG-RING | lattice_constant_um, gap_width_um, line_width_um | 0.8 | -2sigma, nominal, +2sigma |
| STR-EM-LID-HIS | patch_size_um, lid_spacing_um, gap_um | 0.85 | spacer_low, spacer_nominal, spacer_high |
| STR-PH-SOI-JJ-PHC | neck_width_nm, membrane_thickness_nm, lattice_constant_nm | 0.55 | neck_minus10nm, nominal, neck_plus10nm |
| STR-PH-SOI-FULLCAP-PHC | fill_factor, membrane_thickness_nm, lattice_constant_nm | 0.45 | sparse, nominal, dense |
| STR-PH-GRADED-SINK | taper_angle_deg, sink_radius_um, escape_channel_width_um | 0.85 | shallow, nominal, steep |
| STR-VX-ANTIDOT-LATTICE | antidot_radius_um, pitch_um, edge_offset_um | 0.9 | radius_low, nominal, radius_high |
| STR-CTRL-BANDSTOP-INTERPOSER | cell_pitch_um, via_inductance_pH, line_impedance_ohm | 0.75 | low_viaL, nominal, high_viaL |
| STR-3D-CAVITY-LINER | corrugation_depth_mm, corrugation_period_mm, insert_distance_mm | 0.9 | depth_low, nominal, depth_high |

## Pass rule
A candidate passes only if the sign of the effect survives tolerance Monte Carlo and measured as-built bias does not collapse the predicted operating point.
