# MMM Studio Plan

This is the living implementation plan for evolving MMM Studio from a single-run surrogate-scoring slice into a reproducible sweep platform built around typed slices and tranches.

## Objective

Deliver a tranche and sweep orchestration layer that:

- preserves the current typed registry, validation, surrogate scoring, CLI, API, provenance, and artifact foundations
- executes declarative sweep specs through deterministic slice runs
- aggregates tranche and sweep comparisons into reproducible, employer-facing artifacts
- stays honest about scope: this is a surrogate-driven experiment orchestration system, not a physics solver

## Confirmed Reuse Surface

The current repo already has working components that should be generalized instead of replaced:

- `src/mmm_studio/registry.py`: typed seed-data loading
- `src/mmm_studio/validation.py`: repository validation
- `src/mmm_studio/scoring.py`: baseline surrogate profiles and ranking
- `src/mmm_studio/runs.py`: persisted run manifests, provenance, and artifact-writing conventions
- `src/mmm_studio/reporting.py`: CSV, Markdown, and plot generation
- `src/mmm_studio/cli.py`: existing single-run CLI surface
- `src/mmm_studio/api.py`: existing typed HTTP surface

## Generalization Boundary

What is being generalized now:

- the current scoring run path becomes the execution primitive for sweep slices
- current run artifacts and provenance patterns are reused for per-slice outputs
- current CLI and API architecture are extended so sweeps use the same business logic instead of parallel code paths

What is not being generalized now:

- simulation backends remain scaffolds and are not promoted into tranche execution engines
- RF parsing remains separate utility functionality unless explicitly invoked later
- the heuristic scorer remains the only real working engine underneath slice execution
- distributed or parallel execution is not implemented in this tranche

## Tranche Architecture Plan

### Domain models

Add typed Pydantic models for:

- `SweepSpec`: declarative sweep input contract
- `TrancheSpec`: managed collection of related slices
- `SliceSpec`: constrained candidate-ranking unit
- `ResolvedSweepPlan` / `ResolvedTranchePlan` / `ResolvedSlicePlan`: normalized executable forms
- `SweepManifest`: persisted execution and provenance state
- `SweepSummary`: persisted aggregate comparison output

### Execution layering

Add a dedicated `src/mmm_studio/sweeps/` package with:

- `models.py`: sweep, tranche, slice, manifest, and summary contracts
- `planner.py`: spec loading, normalization, input hashing, inheritance resolution, candidate scoping
- `executor.py`: deterministic sequential orchestration with per-slice failure isolation
- `aggregator.py`: tranche and sweep comparison logic
- `artifacts.py`: JSON, Markdown, CSV, and plot persistence plus summary loaders

### Working engine

The first real engine is strictly:

- candidate registry selection
- surrogate scoring by existing profiles
- per-slice persisted run artifacts
- cross-slice and cross-tranche comparison

No fake simulation claims, no empty orchestration shell, and no duplicated scoring logic.

## Execution Phases

### Phase 1: Sweep Modeling

Scope:

- define typed sweep, tranche, slice, manifest, and summary models
- define comparison-strategy and slice-filter contracts
- document candidate robustness as a software comparison metric

Validation checkpoints:

- model validation tests
- invalid-spec cases for duplicate IDs, unsupported modes, and bad profile references

### Phase 2: Planning and Normalization

Scope:

- load declarative YAML specs
- resolve shared profile / parameter inheritance
- resolve candidate scopes against the existing typed dataset
- compute stable input hashes
- persist a pre-execution `sweep_manifest.json`

Validation checkpoints:

- planner normalization tests
- deterministic candidate-count assertions for example specs

### Phase 3: Sequential Slice Execution

Scope:

- execute each slice through the existing surrogate scorer
- isolate each slice in its own artifact directory
- preserve partial progress when a slice fails
- keep the implementation structured so future parallel dispatch can slot in behind the same plan contract

Validation checkpoints:

- executor tests
- failure-isolation test
- full CLI sweep run against repo data

### Phase 4: Aggregation and Comparison

Scope:

- aggregate within-slice ranks into tranche and sweep views
- compute cross-slice overlap, divergence, and stability metrics
- produce tranche-level and sweep-level summaries, tables, CSVs, and plots

Validation checkpoints:

- aggregator tests
- artifact presence checks for summary JSON, Markdown, CSV, and plots

### Phase 5: Surfaces, Examples, and Docs

Scope:

- add sweep CLI commands and typed API endpoints
- add working example sweep specs
- update architecture, pipeline, roadmap, and README docs

Validation checkpoints:

- CLI integration tests
- API tests for sweep endpoints
- docs cross-check against actual commands and artifact names

## Explicit Non-Goals

The following are intentionally deferred unless required to support the tranche architecture itself:

- real Meep or solver execution
- inverse design loops
- learned surrogates
- distributed concurrency
- deep RF calibration workflows

## Final Validation Gate

Before considering the tranche platform complete, run:

- `ruff check .`
- `ruff format --check .`
- `mypy`
- `pytest`
- at least one full example sweep via CLI

Completion criteria:

- planned and executed sweep manifests are written successfully
- per-slice, per-tranche, and sweep-level artifacts exist and are coherent
- CLI and API surfaces use the same orchestration logic
- docs describe the implemented surrogate-backed scope accurately
