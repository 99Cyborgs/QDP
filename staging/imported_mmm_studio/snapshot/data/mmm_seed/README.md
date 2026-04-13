# MMM — Meta Material Module

Research-grade artifact repository for the QDP Meta Material Module.

## Program objective
Determine whether engineered metamaterial environments measurably alter decoherence mechanisms in quantum hardware while explicitly closing baseline explanations first.

## Baseline-first doctrine
- Vortex loss
- Quasiparticle poisoning
- Two-level systems
- Phonon coupling
- Control electronics noise

## Lead branches
- MECH-EM-001 — photonic-bandgap / electromagnetic-LDOS suppression
- MECH-PH-001 — phononic-bandgap engineering of TLS relaxation
- MECH-PH-002 — phonon escape routing and down-conversion
- MECH-VX-001 — vortex-pinning lattice and parked-vortex control (mandatory null-closure branch)

## Repository doctrine
- Every mechanism links to observable IDs, protocol IDs, and validation rule IDs.
- No effect is promotable without matched sham controls and same-package closure.
- Structures requiring exotic fabrication are flagged and cannot be lead-branch candidates without mitigation.
- Replication across cooldowns is mandatory. Cross-device or cross-batch replication is required for promotion.
- Negative results are first-class outputs.

## Core artifact map
| Path | Purpose |
| --- | --- |
| mmm_mechanism_registry.yaml | Canonical metamaterial mechanism registry |
| mmm_structure_library.yaml | Library of realizable structures and integration interfaces |
| mmm_material_genome_database.yaml | Candidate geometry genome database |
| mmm_discovery_engine_spec.md | Discovery workflow and optimization pipeline |
| mmm_environment_simulator_spec.md | Cryogenic environment simulator architecture |
| mmm_null_mechanism_tests.md | Baseline-null attack plan |
| mmm_scaling_tests.md | Scaling-law discrimination plan |
| mmm_device_integration_spec.md | Device integration architecture |
| mmm_fabrication_methods.md | Fabrication workflows and checkpoints |
| mmm_experiment_protocols.md | Discriminating experiment library |
| mmm_detectability_tests.md | Instrument detectability gate |
| mmm_analysis_pipeline_spec.md | Analysis and validation framework |
| mmm_replication_protocols.md | Multi-device replication framework |
| mmm_geometry_scaling_tests.md | Geometry scaling engine |
| mmm_fabrication_variability_tests.md | Fabrication variability engine |
| ARTIFACT_MANIFEST.md | Full artifact inventory |
| REPOSITORY_TREE.txt | Filesystem view of repository |

## Required subrepository
The `/mmm` foundry layout requested by the program is implemented directly in this repository under:
`registry/`, `genome/`, `discovery/`, `simulation/`, `benchmark/`, `scaling/`, `integration/`, `fabrication/`, `experiments/`, `replication/`, `analysis/`, `publications/`.

## Version
- Program: QDP_MMM
- Version: 1.0.0
- Generated: 2026-03-14
