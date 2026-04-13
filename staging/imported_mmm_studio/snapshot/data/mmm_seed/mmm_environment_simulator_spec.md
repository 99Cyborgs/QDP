# MMM Environment Simulator Specification

## Simulator mission
Model the full cryogenic environment surrounding a device so that metamaterial claims are evaluated in the presence of realistic packaging, phonon transport, quasiparticle dynamics, and control-noise pathways.

## Simulator stack
| Model ID | Domain | Role |
| --- | --- | --- |
| ENV-EM-FEM | electromagnetic | mode_frequencies |
| ENV-EM-RLGC | electromagnetic | fast_S_parameters |
| ENV-PKG-MODE | packaging | package_mode_map |
| ENV-PH-BAND | phononic | phononic_gap_map |
| ENV-PH-TD | phononic | escape_time_distribution |
| ENV-QP-RD | quasiparticle | parity_switch_proxy |
| ENV-VX-DYN | vortex | loss_vs_field_prediction |
| ENV-CTRL-NOISE | control_noise | device_noise_psd |
| ENV-THERMAL | thermal | local_temperature_estimate |
| ENV-OPEN-MARKOV | open_quantum_system | T1_prediction |
| ENV-OPEN-PSEUDOMODE | open_quantum_system | non_markovian_relaxation_curve |
| ENV-SYNTHETIC-DATA | validation | synthetic_raw_data |

## Coupling graph
1. Geometry and material stacks feed `ENV-EM-FEM`, `ENV-EM-RLGC`, and `ENV-PH-BAND`.
2. Packaging and launch geometry feed `ENV-PKG-MODE`.
3. Phonon transport outputs feed `ENV-QP-RD`.
4. Control-path S-parameters feed `ENV-CTRL-NOISE`.
5. EM / phononic bath summaries feed `ENV-OPEN-MARKOV` or `ENV-OPEN-PSEUDOMODE`.
6. Synthetic-data generator emits end-to-end mock datasets for analysis validation.

## Required input contracts
- Geometry: GDS-derived dimensions plus as-built metrology corrections
- Materials: film thickness, resistivity, elastic constants, gap contrast, surface loss priors
- Package: sample-box CAD, lid spacing, wirebond map, launch topology
- Cryostat: temperature, field history, filter stack, source-noise measurements
- Experimental metadata: drive amplitudes, injection energies, cooldown identifiers

## Output contracts
- Band-edge / stopband markers
- Package-mode maps
- Predicted T1/T2 / memory-kernel signatures
- Quasiparticle recovery trajectories
- Field-dependent vortex loss curves
- Detectability estimates under instrument constraints

## Fidelity policy
- High-fidelity FEM or eigensolver models calibrate reduced-order surrogates.
- Reduced-order network and PDE models drive optimization and uncertainty propagation.
- Open-system models must be run in both Markov and structured-bath modes for any phononic claim.

## Validation policy
- No simulator module is accepted without a corresponding observable in the experiment registry.
- Model discrepancy is explicit and carried into ranking and validation decisions.
- Simulation alone cannot promote a mechanism; measured scaling and null closure remain decisive.
