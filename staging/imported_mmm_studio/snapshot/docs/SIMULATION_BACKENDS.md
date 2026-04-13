# Simulation Backends

MMM Studio is designed to evolve toward real solver-backed workflows, but this repository version is careful not to overclaim.

## Current Backends

### Local Placeholder Backend

Module: `src/mmm_studio/sim/local.py`

Behavior:

- builds a typed simulation job bundle
- serializes candidate geometry, material hints, and sweep definition
- returns `preflight_only`
- emits no fabricated field, S-parameter, or band-structure results

Use case:

- validating orchestration
- persisting reproducible run metadata
- keeping the CLI/API/demo pipeline honest before solver integration lands

### Meep Scaffold Backend

Module: `src/mmm_studio/sim/meep.py`

Behavior:

- translates a candidate into a `MeepGeometryScaffold`
- records material hints and geometry parameters
- reports whether the `meep` import is available
- returns `unsupported` for execution in this repository version

Not implemented yet:

- dielectric / dispersive material assignment
- source placement
- PML and boundary conditions
- field extraction
- S-parameter post-processing
- convergence studies

## Interface Contract

All simulation work is routed through:

- `SimulationJobDefinition`
- `SimulationJobResult`
- `SweepSpecification`

That separation is deliberate:

- geometry translation can evolve independently from run execution
- run execution can evolve independently from result extraction
- future backends can share one CLI/API surface

## Future Directions

### Meep Execution Path

- derive actual cell sizes and resolutions from structure families
- generate geometry primitives per candidate family
- add source and monitor placement
- extract spectra and band-edge proxies into typed result artifacts

### Multiphysics Expansion

- link EM and phononic geometries under one manifest
- add reduced-order open-system models as post-processors, not replacements for field solves
- connect experimental artifacts back into the same provenance path

## Honesty Rule

If a backend has not solved fields or consumed measured RF data, it should return a preflight or unsupported status and nothing stronger. MMM Studio follows that rule throughout the repository.
