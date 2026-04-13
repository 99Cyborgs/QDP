# E01 MM Simulation Appendix

## Reproducibility

- suite: `E01 MM Minimal Simulation Suite`
- seed: `1729`
- case count: `5`

## Synthetic Case Summary

| Case | Proposal role | Primary quantitative output |
| --- | --- | --- |
| `memoryless_field_loss_with_drift` | H0 stress test | `H_O = 2.518495e-06`, `A_O = -2.518495e-06` |
| `generic_hidden_state_hysteresis` | H1 retained-memory surrogate | `mean_H_O = 3.1985e-07`, `mean_A_O = -3.1985e-07` |
| `qp_lag_after_field_step` | H3 lag challenge | `H_O = 2.68264e-07`, `A_O = -2.68264e-07` |
| `fabrication_noise_false_geometry_signal` | H2 false-ordering stress | `spurious_monotonic_rate = 0.0` |
| `package_common_mode_drift` | H4 common-mode drift challenge | `corr(target,witness) = 0.887162427199` |

## Proposal Interpretation

- The package now demonstrates that each authorized mechanism class can be stressed without access to cryogenic hardware.
- The appendix metrics are deterministic for the declared seed and can be regenerated from the simulation suite.
- These outputs are proposal evidence for computational readiness only; they are not claims about real-device calibration.

## Regeneration Command

```powershell
python simulation\e01_mm_simulation_suite.py --output-dir simulation_outputs --appendix-path simulation\e01_mm_simulation_appendix.md
```
