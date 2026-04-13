# MMM Experimental Protocol Library

## Protocol doctrine
- Every protocol must discriminate a metamaterial claim from at least one baseline null.
- Matched sham and package controls are default, not optional.
- Raw data, calibration data, and metadata are versioned with cooldown and batch identifiers.


## EXP-T1-FSWEEP-01 — Frequency-resolved T1 sweep across target band edges

- **Purpose:** Measure whether T1 changes track the designed electromagnetic or phononic spectral features rather than generic package shifts
- **Primary observables:** OBS-T1-MEAN
- **Secondary observables:** OBS-BG-SHIFT, OBS-PKG-S21, OBS-T1-NMARK
- **Device classes:** transmon, fluxonium, planar_resonator, 3d_cavity
- **Nulls addressed:** NULL-EM-PURCELL, NULL-PKG-MODE, NULL-FAB-VAR
- **Minimum repeats:** devices/condition=3, cooldowns=2

**Required controls**
- same-wafer sham geometry
- same-package control device
- matched readout chain
- package transfer-function calibration

**Analysis route**
T1 extraction -> band-edge alignment -> null-model comparison -> replication gate

## EXP-HOLEBURN-THERM-01 — TLS hole-burning and thermalization dynamics

- **Purpose:** Probe whether phononic structuring modifies TLS relaxation or thermalization pathways
- **Primary observables:** OBS-T1-NMARK, OBS-SDIFF-PSD
- **Secondary observables:** OBS-T1-MEAN, OBS-TEMP-SLOPE
- **Device classes:** transmon, planar_resonator
- **Nulls addressed:** NULL-THERMAL, NULL-FAB-VAR, NULL-CTRL-DISTORT
- **Minimum repeats:** devices/condition=3, cooldowns=2

**Required controls**
- same wafer without phononic lattice
- identical junction design
- temperature-calibrated sequence

**Analysis route**
Pump-probe response -> memory-kernel model fit -> temperature scaling discrimination

## EXP-RAMSEY-PSD-01 — Long-duration Ramsey / echo spectral-diffusion assay

- **Purpose:** Measure low-frequency noise and dephasing changes under metamaterial integration
- **Primary observables:** OBS-T2STAR, OBS-T2ECHO, OBS-SDIFF-PSD
- **Secondary observables:** OBS-CTRL-PSD
- **Device classes:** transmon, fluxonium
- **Nulls addressed:** NULL-CTRL-DISTORT, NULL-SHIELDING, NULL-FAB-VAR
- **Minimum repeats:** devices/condition=3, cooldowns=2

**Required controls**
- shared source electronics
- line-swapped confirmation
- same package or dummy package insert

**Analysis route**
Frequency-noise trace -> PSD estimation -> control-noise closure -> hierarchical comparison

## EXP-QP-PARITY-01 — Steady-state quasiparticle and charge-parity monitor

- **Purpose:** Test whether metamaterial modifications change nonequilibrium quasiparticle population or parity switching
- **Primary observables:** OBS-QP-PARITY
- **Secondary observables:** OBS-T1-MEAN, OBS-QP-RECOV
- **Device classes:** transmon, fluxonium
- **Nulls addressed:** NULL-QP-TRAP, NULL-SHIELDING, NULL-THERMAL
- **Minimum repeats:** devices/condition=3, cooldowns=3

**Required controls**
- identical readout thresholding
- same shielding condition
- same wafer control

**Analysis route**
Parity-event extraction -> stationarity checks -> link to T1 and thermal load

## EXP-QP-INJECT-01 — Controlled phonon / quasiparticle injection and recovery

- **Purpose:** Measure recovery dynamics after pair breaking or local heating to isolate phonon escape engineering
- **Primary observables:** OBS-QP-RECOV
- **Secondary observables:** OBS-QP-PARITY, OBS-T1-MEAN
- **Device classes:** transmon, fluxonium, kinetic_inductance_detector
- **Nulls addressed:** NULL-QP-TRAP, NULL-THERMAL, NULL-FAB-VAR
- **Minimum repeats:** devices/condition=3, cooldowns=2

**Required controls**
- identical injector geometry
- equal injected energy calibration
- same ambient temperature

**Analysis route**
Injection calibration -> recovery-curve fit -> diffusion-reaction inversion

## EXP-BFIELD-VORTEX-01 — Field-cool / field-sweep vortex assay

- **Purpose:** Determine whether periodic structures are acting through vortex pinning or entry suppression
- **Primary observables:** OBS-VORTEX-SLOPE
- **Secondary observables:** OBS-WITNESS-QI, OBS-T1-MEAN
- **Device classes:** planar_resonator, transmon, kinetic_inductance_detector
- **Nulls addressed:** NULL-VORTEX, NULL-SHIELDING, NULL-FAB-VAR
- **Minimum repeats:** devices/condition=4, cooldowns=2

**Required controls**
- zero-field cooldown reference
- field polarity reversal
- antidot-free control

**Analysis route**
Loss-vs-field fit -> vortex model comparison -> pinning-threshold extraction

## EXP-PKG-MODE-01 — Package-mode and transfer-function closure

- **Purpose:** Measure full electromagnetic transfer function to ensure apparent improvements are not simple packaging or filtering changes
- **Primary observables:** OBS-PKG-S21
- **Secondary observables:** OBS-BG-SHIFT, OBS-WITNESS-QI
- **Device classes:** transmon, fluxonium, planar_resonator, 3d_cavity, kinetic_inductance_detector
- **Nulls addressed:** NULL-PKG-MODE, NULL-EM-PURCELL, NULL-CTRL-DISTORT
- **Minimum repeats:** devices/condition=2, cooldowns=2

**Required controls**
- through-line package coupon
- open/short/load calibration structure
- same launch geometry

**Analysis route**
De-embed launches -> mode map -> compare to sham and EM solver

## EXP-TEMP-SCAN-01 — Controlled temperature scaling scan

- **Purpose:** Discriminate TLS, quasiparticle, phonon, and radiative mechanisms through temperature response
- **Primary observables:** OBS-TEMP-SLOPE
- **Secondary observables:** OBS-T1-MEAN, OBS-T2STAR, OBS-QP-PARITY
- **Device classes:** transmon, fluxonium, planar_resonator, kinetic_inductance_detector
- **Nulls addressed:** NULL-THERMAL, NULL-QP-TRAP, NULL-EM-PURCELL
- **Minimum repeats:** devices/condition=3, cooldowns=2

**Required controls**
- verified fridge temperature calibration
- thermal equilibration dwell
- fixed readout power

**Analysis route**
Fit mechanism-specific temperature forms -> Bayes factor / information criteria ranking

## EXP-DRIVE-AMP-01 — Drive-amplitude and photon-number scaling

- **Purpose:** Distinguish saturation-sensitive TLS or control-path effects from genuine environment-engineering signatures
- **Primary observables:** OBS-T2STAR, OBS-CTRL-PSD
- **Secondary observables:** OBS-WITNESS-QI, OBS-T1-MEAN
- **Device classes:** transmon, fluxonium, planar_resonator
- **Nulls addressed:** NULL-CTRL-DISTORT, NULL-THERMAL, NULL-FAB-VAR
- **Minimum repeats:** devices/condition=3, cooldowns=2

**Required controls**
- source-noise calibration
- attenuation chain consistency
- same package

**Analysis route**
Power sweep -> saturation / dephasing model fit -> null discrimination

## EXP-GEO-SERIES-01 — Geometry-series wafer study

- **Purpose:** Verify that effects scale with metamaterial pitch, fill factor, or number of cells as predicted
- **Primary observables:** OBS-T1-MEAN, OBS-BG-SHIFT
- **Secondary observables:** OBS-T2STAR, OBS-VORTEX-SLOPE, OBS-QP-PARITY
- **Device classes:** transmon, fluxonium, planar_resonator, 3d_cavity, kinetic_inductance_detector
- **Nulls addressed:** NULL-FAB-VAR, NULL-PKG-MODE, NULL-THERMAL
- **Minimum repeats:** devices/condition=4, cooldowns=2

**Required controls**
- split-lot DOE
- same process lot
- mask bias monitor structures

**Analysis route**
SEM metrology -> inferred geometry -> response-surface comparison to scaling models

## EXP-SAW-WITNESS-01 — Surface-acoustic-wave / piezoelectric witness assay

- **Purpose:** Confirm acoustic bandstops or piezoelectric pathway modifications with a dedicated witness structure
- **Primary observables:** OBS-SAW-S21
- **Secondary observables:** OBS-BG-SHIFT, OBS-T1-MEAN
- **Device classes:** transmon, planar_resonator, kinetic_inductance_detector
- **Nulls addressed:** NULL-SAW-CROSSTALK, NULL-THERMAL, NULL-FAB-VAR
- **Minimum repeats:** devices/condition=2, cooldowns=2

**Required controls**
- IDT-to-IDT control path
- same piezoelectric stack without stopband
- temperature sweep

**Analysis route**
S21 extraction -> stopband alignment -> link to qubit or resonator response

## EXP-REPL-01 — Cross-device and cross-batch replication

- **Purpose:** Establish that candidate effects persist across device classes, substrates, and fabrication batches
- **Primary observables:** OBS-T1-MEAN, OBS-T2STAR, OBS-QP-PARITY, OBS-WITNESS-QI
- **Secondary observables:** OBS-BG-SHIFT, OBS-TEMP-SLOPE
- **Device classes:** transmon, fluxonium, planar_resonator, 3d_cavity, kinetic_inductance_detector
- **Nulls addressed:** NULL-FAB-VAR, NULL-THERMAL, NULL-PKG-MODE, NULL-CTRL-DISTORT
- **Minimum repeats:** devices/condition=6, cooldowns=4

**Required controls**
- minimum two fabrication batches
- minimum two cooldowns per batch
- same data reduction code path

**Analysis route**
Hierarchical effect estimation -> batch random-effects model -> claim maturity gate
