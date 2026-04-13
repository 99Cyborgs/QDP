# MMM Repository Architecture

## Root contract
The repository root is the authoritative `/mmm` module.

## Canonical root artifacts
- Top-level engine outputs are named `mmm_*` and remain canonical.
- Mirror copies are placed in the required foundry subdirectories using generic filenames such as `registry/mechanisms.yaml`.
- Validation scripts live under `tools/`.

## Foundry directory structure
| Directory | Canonical contents |
| --- | --- |
| registry/ | mechanisms.yaml, structures.yaml |
| genome/ | material_genome_database.yaml |
| discovery/ | generation_algorithms.yaml |
| simulation/ | environment_models.yaml |
| benchmark/ | null_mechanism_models.yaml |
| scaling/ | scaling_models.yaml |
| integration/ | device_architecture.yaml |
| fabrication/ | fabrication_methods.md |
| experiments/ | protocols.md |
| replication/ | replication_protocols.md |
| analysis/ | analysis_pipeline.md |
| publications/ | mmm_overview.tex |
| tools/ | validation and repository utilities |

## Artifact naming rule
- Canonical root artifact: `mmm_<engine_or_scope>.<ext>`
- Mirror artifact: shortened path-specific filename inside required subdirectory
- IDs inside YAML are immutable and machine-checkable

## Governance rule enforcement
1. Mechanism entries must contain at least one predicted observable ID.
2. Mechanism entries must contain at least one experimental protocol ID.
3. Mechanism entries must contain at least one validation rule ID.
4. All references must resolve.
5. Exotic structures must be flagged.
6. Lead-branch promotion requires standard-lab feasibility.

## Reproducibility rule
- All analysis and validation results must be reproducible from versioned YAML + markdown specs + Python validation utilities.
