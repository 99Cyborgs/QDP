# E01 MM Measurement Protocol

## Purpose

Acquire the minimum laboratory dataset needed to register and test a conservative metastable memory branch using field-history-dependent loss at fixed low temperature and fixed low drive.

## Numbered Procedure

1. **Select the device set.**
   Use one target device plus at least one package witness or reference channel measured in the same cooldown.
   If the chip contains matched widths or matched geometries, include them in the same run plan.
   If no same-chip matched geometry exists, proceed with metastable memory intake only and mark H2 as ineligible.

2. **Lock the phase 1 operating point.**
   Choose one fixed low temperature `T_base` and one fixed low drive `P_read` from prior linear-response calibration.
   Do not perform broad power sweeps or broad temperature sweeps in this phase.
   Record `T_base`, `P_read`, attenuation state, and the device readout configuration before any field history run begins.

3. **Plan the cooldown set.**
   Run a minimum of `3` independent cooldowns.
   At least one cooldown must start with `ZFC`.
   At least one cooldown must include `FC`.
   Use the same nominal `T_base`, `P_read`, field step list, and witness strategy in every cooldown unless a documented equipment issue forces abort.

4. **Establish the zero-field baseline.**
   Set commanded field to zero and verify the coil-current readback.
   Measure repeated zero-field traces until the baseline estimates for `1/Qi`, `fr`, and the witness channel are stable enough to define the noise floor.
   Use these repeats to estimate `sigma_0` for the target and witness channels.

5. **Calibrate dwell convergence before production loops.**
   At one low field near the expected onset and one higher field with clear signal, repeat the same field step with dwell times `t`, `2t`, and `4t`.
   Define the production dwell `t_conv` as the smallest dwell for which:
   `1.` the final-window slopes of `1/Qi` and `delta fr over fr` are consistent with zero within measurement uncertainty, and
   `2.` doubling dwell changes the recomputed `H_O` by less than `5%`.
   If no such dwell is found before drift dominates the trace, stop and classify the run as non-converged.

6. **Run the ZFC field-history sequence.**
   Prepare a zero-field-cooled state using the lab-standard zero-field cooldown procedure.
   At fixed `T_base` and `P_read`, execute the field sequence:
   `0 -> +B_max -> 0 -> -B_max -> 0`.
   Use the same step size and dwell `t_conv` at every field point.
   Record full up-field and down-field branches.

7. **Run the FC field-history sequence.**
   Prepare a field-cooled state using the same absolute field setpoint intended for the FC condition.
   Repeat the identical loop structure and dwell settings used in the `ZFC` run.
   Keep all non-field settings unchanged.

8. **Apply the `B_on` threshold rule.**
   Define `B_on` as the smallest absolute field at which the dwell-converged branch difference in `1/Qi` exceeds `max(3 sigma_0, 3 sigma_witness_equivalent)` at two consecutive field points.
   Use the same interpolation rule in every cooldown.
   Select one field just above `B_on` as the primary selected-field point for secondary observable acquisition.

9. **Acquire the secondary observables at selected fields.**
   At minimum, acquire:
   `1.` `T1` at zero field,
   `2.` `T1` just above `B_on`, and
   `3.` `T1` at one higher field after the same history preparation.
   Record `delta fr over fr` at every field step, not only at selected fields.

10. **Run the sham timing control.**
    Execute the identical timing, dwell, and readout cadence with the applied field held at zero or with a validated null command that produces no net field change at the sample.
    The sham run must match the sequence length and checkpoint timing of the real field loop.

11. **Insert return-to-zero checkpoints.**
    After each half-loop and each full loop, return to zero applied field and reacquire the baseline.
    Use the same number of repeated reads at each checkpoint.
    These checkpoints are part of the dataset, not optional diagnostics.

12. **Measure the package witness or reference channel.**
    Acquire the witness channel at every field point and every sham checkpoint.
    If the hardware cannot multiplex the witness simultaneously, interleave witness reads at the same cadence as the target and preserve timestamp alignment.

13. **Record the required observables and metadata.**
    For every point, record:
    `1.` cooldown identifier,
    `2.` device identifier,
    `3.` geometry identifier,
    `4.` history label (`ZFC`, `FC`, `up`, `down`, `sham`),
    `5.` commanded field,
    `6.` calibrated field estimate,
    `7.` elapsed time,
    `8.` dwell duration,
    `9.` `1/Qi`,
    `10.` `fr`,
    `11.` `delta fr over fr`,
    `12.` selected-field `T1` when applicable,
    `13.` witness response,
    `14.` bath temperature,
    `15.` readout power.

14. **Compute and archive the loop metrics without changing the raw data.**
    Use `y(B) = 1/Qi(B)`.
    Define `H_O` as the integrated absolute branch difference:
    `H_O = integral |y_up(B) - y_down(B)| dB`.
    Define `A_O` as the signed loop area:
    `A_O = integral (y_up(B) - y_down(B)) dB`.
    Preserve the raw branch traces and the interpolation grid used for integration.

15. **Stop conditions.**
    Stop the run and mark it non-discriminating if any of the following occurs:
    `1.` dwell convergence cannot be reached,
    `2.` the sham timing control is missing,
    `3.` the witness channel is missing,
    `4.` the fixed `T_base` or `P_read` drifts outside the logged tolerance,
    `5.` the field calibration or zero return checkpoint cannot be trusted.
