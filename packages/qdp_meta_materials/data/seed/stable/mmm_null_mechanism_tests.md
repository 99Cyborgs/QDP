# MMM Null Mechanism Tests

## Rule
Every candidate branch is attacked by baseline null models before any positive interpretation is allowed.

| Null ID | Null model | What it can mimic | Decisive observables |
| --- | --- | --- | --- |
| NULL-EM-PURCELL | Ordinary Purcell / impedance engineering null | T1 improvement due to altered impedance environment without requiring a true metamaterial mechanism. | OBS-T1-MEAN, OBS-PKG-S21, OBS-BG-SHIFT |
| NULL-PKG-MODE | Package-mode shift null | Apparent coherence gain arises from modified package resonances, seams, or lid spacing. | OBS-PKG-S21, OBS-T1-MEAN |
| NULL-QP-TRAP | Ordinary quasiparticle trap null | T1 or parity improvement arises from conventional gap engineering or normal-metal traps, not metamaterial environment shaping. | OBS-QP-PARITY, OBS-QP-RECOV, OBS-T1-MEAN |
| NULL-SHIELDING | Improved magnetic / infrared shielding null | Observed gains come from better shielding, light-tightness, or flux hygiene introduced with the new assembly. | OBS-VORTEX-SLOPE, OBS-QP-PARITY, OBS-T1-MEAN |
| NULL-THERMAL | Thermal gradient / hidden heating null | Coherence changes arise from altered thermalization or local heating rather than structured environment coupling. | OBS-TEMP-SLOPE, OBS-QP-PARITY, OBS-T1-MEAN |
| NULL-FAB-VAR | Fabrication variation null | Observed gain is due to uncontrolled changes in junction resistance, film quality, or etch bias. | OBS-T1-MEAN, OBS-WITNESS-QI, OBS-BG-SHIFT |
| NULL-VORTEX | Vortex-entry / mobility null | Periodic superconducting features act mainly by changing vortex pinning or flux entry. | OBS-VORTEX-SLOPE, OBS-WITNESS-QI, OBS-T1-MEAN |
| NULL-CTRL-DISTORT | Control electronics / line distortion null | Changed attenuation, reflections, or pulse distortions alter observed T2/T1 without a new materials mechanism. | OBS-CTRL-PSD, OBS-T2STAR, OBS-T2ECHO |
| NULL-SAW-CROSSTALK | SAW witness cross-talk null | Witness acoustic stopband is an RF crosstalk artifact or packaging resonance, not true acoustic isolation. | OBS-SAW-S21, OBS-BG-SHIFT |

## Mandatory test sequence
1. Run same-wafer sham control.
2. Run same-package or same-lid control.
3. Measure package/control transfer functions.
4. Measure field sensitivity if superconducting perforation or periodic ground engineering is present.
5. Measure temperature scaling.
6. Measure fabrication monitors and as-built geometry.
7. Compare candidate model against all admissible null models.

## Branch-specific kill criteria
- EM branches die if package or Purcell null explains the full effect.
- Phononic branches die if memory-kernel evidence is absent and thermal/TLS nulls dominate.
- QP branches die if parity or injection recovery does not change consistently.
- Periodic superconducting-film branches die if field-cool dependence dominates the signal.
