# Data Model

MMM Studio has two kinds of data contracts:

1. **seed registry documents** loaded from `data/mmm_seed/`
2. **generated operational artifacts** written during scoring and demo runs

## Seed Registry Documents

The loader validates these primary files into typed Pydantic models:

- `mmm_material_genome_database.yaml`
- `mmm_candidate_ranking_model.yaml`
- `mmm_mechanism_registry.yaml`
- `mmm_structure_library.yaml`
- `mmm_experiment_registry.yaml`
- `mmm_validation_rules.yaml`
- `mmm_benchmark_models.yaml`
- `mmm_scaling_discrimination_models.yaml`
- `mmm_device_architecture_registry.yaml`
- `mmm_tolerance_models.yaml`
- `mmm_geometry_scaling_models.yaml`
- `mmm_material_system_registry.yaml`
- `mmm_environment_model_registry.yaml`
- `mmm_instrument_constraints.yaml`
- `mmm_cross_device_registry.yaml`

The assembled `MMMDataset` exposes typed lists plus indexes for genomes, mechanisms, structures, observables, and protocols.

## Core Domain Models

### Candidate Geometry Metadata

`CandidateGeometryMetadata` is the normalized, versioned geometry surface used by the simulation layer. It captures:

- candidate ID
- parent structure ID
- lattice topology
- parameter map

### Material Parameter Set

`MaterialParameterSet` describes the material system and any backend-facing material hints. It is used for job definitions and future solver adapters.

### Sweep Specification

`SweepSpecification` defines:

- target domain
- frequency window
- sample count
- optional temperature points
- requested observables

This is the common contract between CLI/API orchestration and future simulation backends.

### Simulation Job Definition

`SimulationJobDefinition` packages:

- backend ID
- candidate geometry metadata
- material parameters
- sweep spec
- requested outputs

Current repository behavior is preflight only. The job contract exists so future solver integrations can reuse the same orchestration surface.

### Score Result

`ScoreResult` preserves:

- total score
- decision band
- backend/profile labels
- reject reason
- full component trace with per-feature value and weight

This is the primary scoring output contract for the CLI, API, and reports.

### Provenance and Run Manifest

Generated runs persist:

- `ProvenanceMetadata`
- `RunManifest`
- `metrics.json`
- `params.yaml`

These contracts make runs reproducible and comparable.

## Validation Philosophy

Validation is strict at the document boundary and mechanism-aware at the repository level:

- missing files are errors
- duplicate identifiers are errors
- unresolved references between mechanisms, structures, observables, protocols, nulls, and replication paths are errors
- missing tolerance or geometry-scaling coverage for lead structures is a warning
- ranking-model formulas are checked against declared features and normalized weights

## Schema Versioning

Seed documents use the artifact version already present in the source library. Generated operational artifacts additionally carry explicit `schema_name` and `schema_version` fields so future non-breaking evolution is manageable without rewriting the seed library itself.
