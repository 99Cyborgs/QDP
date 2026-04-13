# MMM Detectability Tests

## Detectability gate
A candidate may proceed only if the predicted effect exceeds the measured uncertainty floor by a factor of at least 3.

## Generic test
```text
detectability_margin = predicted_effect_size / sigma_observable
pass if detectability_margin >= 3
```

## Observable-specific minimum claim margins
| Observable class | Minimum fractional or absolute shift for promotable claim |
| --- | --- |
| T1 / T2 | >= 15% |
| Parity rate / QP proxy | >= 20% |
| QP recovery time | >= 20% |
| Vortex loss slope | >= 25% |
| Witness band marker | >= 50 MHz |
| SAW notch depth | >= 3 dB |

## Acquisition planning rule
- Increase device count before shrinking uncertainty by aggressive fitting assumptions.
- If detectability margin remains below threshold after reasonable sample expansion, reject the branch or move it to sandbox.
- Instrument floors are defined in `mmm_instrument_constraints.yaml`.

## Immediate fail conditions
- Predicted band marker below witness spectroscopy resolution
- Predicted coherence change smaller than cooldown-to-cooldown drift
- Predicted parity or recovery shift below calibration repeatability
