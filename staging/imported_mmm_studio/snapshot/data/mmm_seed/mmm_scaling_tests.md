# MMM Scaling Tests

## Scaling-law doctrine
A metamaterial claim is stronger when it produces a geometry-linked or spectral scaling law that baseline nulls do not naturally reproduce.

| Scaling model | Mechanism | Independent variables | Distinctive signature |
| --- | --- | --- | --- |
| SCALE-001 | MECH-EM-001 | frequency, geometry | Spectral alignment to stopband marker with weak temperature dependence. |
| SCALE-002 | MECH-PH-001 | frequency, temperature, geometry | Memory-kernel evidence plus geometry-shifted phononic band marker. |
| SCALE-003 | MECH-PH-002 | geometry, temperature, injection_energy | Injection-recovery scaling tracks sink geometry rather than trap area. |
| SCALE-004 | MECH-VX-001 | magnetic_field, geometry, temperature | Strong field scaling dominates if vortex mechanism is active. |
| SCALE-005 | MECH-EM-002 | frequency, geometry, lid_spacing | Removable-lid geometry dependence with preserved same-package wiring. |
| SCALE-006 | MECH-EM-003 | drive_amplitude, geometry, frequency | Broadband reduction in control PSD without strong temperature signature. |
| SCALE-007 | MECH-PH-003 | frequency, geometry, temperature | Dedicated SAW witness tracks qubit response. |
| SCALE-008 | MECH-QP-001 | geometry, temperature, injection_energy | Broadband particle-management trend only. |
| SCALE-009 | MECH-HYB-001 | frequency, geometry, temperature | Correlated EM and phononic witness markers plus elevated non-Markovian evidence. |
| SCALE-010 | MECH-3D-001 | frequency, geometry, assembly_repeat | 3D-specific cavity-mode map changes with reassembly robustness. |
| SCALE-011 | MECH-EM-004 | frequency, drive_amplitude, geometry | Matched conventional attenuation cannot reproduce same T2 + parity combination. |

## Mandatory scaling scans
| Scan | Independent variable | Minimum points | Pass logic |
| --- | --- | --- | --- |
| Temperature | 10-200 mK or safe device range | 5 | Candidate model beats TLS/QP/thermal nulls |
| Magnetic field | field-cool or sweep | >=7 | Vortex slope bounded or explicitly assigned to null branch |
| Drive amplitude | power or photon number | >=6 | Candidate effect survives matched control fidelity |
| Geometry | mask series | >=4 structures | Effect follows predicted geometry trend |
| Frequency | tunable device or family sweep | >=4 points | Effect aligns with band feature not arbitrary drift |

## Promotion rule
No mechanism is promotable without at least one successful geometry or frequency scaling result plus cooldown replication.
