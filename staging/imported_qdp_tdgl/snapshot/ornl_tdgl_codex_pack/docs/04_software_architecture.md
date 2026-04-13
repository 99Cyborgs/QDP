# 04. Software architecture specification

## 4.1 Repository layout

```text
repo_root/
  pyproject.toml
  README.md
  src/
    tdgl_rf/
      __init__.py
      cli.py
      config/
        models.py
        loaders.py
        validators.py
      geometry/
        masks.py
        strip.py
        moat.py
        defects.py
      fields/
        forcing.py
        linkvars.py
        currents.py
        observables.py
        vortices.py
      solvers/
        state.py
        tdgl_stepper.py
        phi_solver.py
        linear_ops.py
        petsc_backend.py
        scipy_backend.py
      inference/
        priors.py
        likelihood.py
        summary_stats.py
        synthetic_data.py
        map_estimation.py
        laplace.py
      workflows/
        run_case.py
        run_ensemble.py
        run_inference.py
        postprocess.py
        convergence.py
      io/
        hdf5_writer.py
        metadata.py
        checkpoints.py
        reports.py
      utils/
        seeds.py
        timers.py
        logging.py
        units.py
  tests/
    unit/
    integration/
    regression/
  configs/
  matrices/
  scripts/
  runs/
```

## 4.2 Architectural principles
1. **Config-driven execution**. No science case should require code edits.
2. **Strict separation** of physics, numerics, workflows, and postprocessing.
3. **Deterministic reproducibility** for deterministic and stochastic modes.
4. **MPI-safe IO** with rank-aware writing or gathered reduced outputs.
5. **Backend abstraction** for solver implementations.

## 4.3 Core data structures

### Config models
Use `pydantic` models for:
- `MetadataConfig`
- `MeshConfig`
- `GeometryConfig`
- `PhysicsConfig`
- `ForcingConfig`
- `NoiseConfig`
- `TimeConfig`
- `SolverConfig`
- `OutputConfig`
- `InferenceConfig`

The source of truth is `configs/tdgl_case.schema.json`.

### State object
A `SimulationState` object must include:
- `t`
- `step`
- `psi`
- `phi`
- `A`
- `A_dot`
- `diagnostics`
- `rng_state`
- `checkpoint_id`

### Run result object
A `RunSummary` object must include:
- status (`success`, `failed`, `partial`)
- case ID
- start/stop timestamps
- wall clock
- seed information
- solver iteration stats
- convergence status
- observable file paths
- checkpoint file paths
- failure reason if any

## 4.4 CLI
Provide the following commands:

```text
tdgl-rf validate-config <config.yaml>
tdgl-rf run-case <config.yaml>
tdgl-rf run-matrix <matrix.csv> [--selector ...]
tdgl-rf run-ensemble <config.yaml>
tdgl-rf run-inference <config.yaml>
tdgl-rf verify <benchmark_id>
tdgl-rf convergence <config.yaml>
tdgl-rf summarize <run_dir>
```

### CLI requirements
- exit nonzero on failure,
- emit human-readable logs,
- write machine-readable metadata (`json` or `yaml`),
- support dry-run mode for matrix expansion.

## 4.5 Configuration semantics
Case configs must support:
- inheritance via a `base_config` field,
- overrides from matrix rows,
- explicit versioning.

Codex should implement a config loader that:
1. loads the base config recursively,
2. applies current file overrides,
3. validates against the schema,
4. freezes an expanded config snapshot into the run directory.

## 4.6 Output layout

```text
runs/<case_id>/<timestamp>/
  expanded_config.yaml
  provenance.json
  status.json
  logs/
    run.log
  observables/
    timeseries.csv
    events.csv
    summary.json
  fields/
    checkpoint_000100.h5
    checkpoint_000200.h5
  diagnostics/
    solver_iterations.csv
    convergence_report.json
    profiling.json
```

## 4.7 Provenance requirements
Every run must record:
- git revision if available,
- hostname / rank count,
- package versions,
- seeds,
- config hash,
- matrix row ID if applicable,
- wall clock and CPU time if available.

## 4.8 Observable API
The observable layer must be callable independently of the solver loop.

Required functions:
- `compute_vortex_map(state, config) -> ndarray[int]`
- `track_vortices(prev_map, curr_map, metadata) -> EventTable`
- `compute_frequency_shift_proxy(state, weights, params) -> float`
- `compute_qinv_proxy(state, weights, params) -> float`
- `compute_summary_stats(timeseries, events) -> dict`

## 4.9 Postprocessing
Postprocessing code must:
- operate on stored run outputs without rerunning the solver,
- compute campaign-level summaries,
- generate proposal-ready plots,
- support comparison across case IDs and refinement levels.

## 4.10 Error model
Each workflow must raise structured exceptions:
- `ConfigError`
- `GeometryError`
- `SolverDivergenceError`
- `OutputWriteError`
- `InferenceError`

A failure must be represented both in the Python exception and in `status.json`.

## 4.11 Testing requirements
- unit tests for math kernels and config handling,
- integration tests for end-to-end deterministic runs,
- regression tests for reference observables and vortex counts,
- smoke tests for matrix expansion and CLI.

## 4.12 Dependency rules
Allowed in v1:
- scientific Python stack,
- PETSc / MPI wrappers,
- HDF5.

Disallowed in v1 core:
- JAX
- PyTorch
- custom CUDA/HIP kernels
- plotting inside solver modules
- direct dependence on lab-specific internal toolchains

## 4.13 Suggested package boundaries
Keep the following boundaries hard:
- `fields/` does not call `io/`
- `solvers/` does not call `postprocess`
- `inference/` consumes forward outputs through a stable interface, not through ad hoc file parsing
- `cli.py` stays thin
