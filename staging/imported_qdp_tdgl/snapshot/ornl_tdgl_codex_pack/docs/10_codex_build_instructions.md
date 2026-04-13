# 10. Codex build instructions

This file is written directly for Codex.

## 10.1 Mission
Build **v1** of the TDGL-RF experiment platform defined by this pack.

## 10.2 Hard constraints
You must obey all of the following:

1. Implement only the v1 scope defined in `docs/01_program_charter.md`.
2. Use the config schema in `configs/tdgl_case.schema.json` as the source of truth.
3. Start with deterministic forward solves.
4. Do not implement stochastic or inference features until deterministic acceptance gates pass.
5. Do not introduce new physics beyond the equations in `docs/02_physics_spec.md`.
6. Do not replace the discretization choice in `docs/03_numerics_spec.md`.
7. Do not add optional frameworks or dependencies not listed in `README.md` without an explicit ADR.
8. Do not optimize prematurely for GPUs.
9. Do not produce proposal prose until the required figures exist.
10. Keep all outputs reproducible and provenance-rich.

## 10.3 Required implementation order

### Phase 0 — scaffold
- create repository structure,
- implement config models and schema validation,
- implement logging and run-directory creation,
- implement matrix expansion.

### Phase 1 — deterministic solver core
- mesh and geometry masks,
- forcing field representation,
- link variables,
- covariant Laplacian,
- phi solve,
- IMEX stepper,
- unit tests for math kernels,
- benchmark D01.

### Phase 2 — deterministic V&V
- D02, D03, D04,
- convergence workflow,
- vortex detection,
- proposal figure 1 and figure 2.

Do not proceed until Gate G1 is green.

### Phase 3 — stochastic extension
- additive noise generation,
- seed management,
- ensemble runner,
- event tables,
- stochastic benchmarks S01 and S02,
- proposal figure 3.

Do not proceed until Gate G2 is green.

### Phase 4 — inverse workflow
- synthetic data generator,
- summary-statistic likelihood,
- MAP estimation,
- local uncertainty approximation,
- inference benchmark I01,
- proposal figure 4.

Do not proceed until Gate G3 is green.

### Phase 5 — performance instrumentation
- timers and profiling hooks,
- scaling workflows,
- P-phase matrix rows,
- performance plots and projected workload table.

## 10.4 Coding rules
- use type hints,
- write docstrings for public functions,
- keep functions small and testable,
- separate pure numerical kernels from orchestration logic,
- use `pytest`,
- prefer explicit over clever code,
- keep file IO out of numerical kernels.

## 10.5 Testing rules
At the end of each phase:
- run all relevant tests,
- write a short status memo,
- update the acceptance checklist,
- fail loudly if a gate is not green.

## 10.6 Deliverables expected from you
You should produce:
- the code repository,
- passing tests,
- run scripts,
- expanded configs,
- benchmark outputs,
- figures,
- a concise implementation report per phase.

## 10.7 How to handle ambiguity
If any requirement is ambiguous:
1. prefer the narrower interpretation,
2. document the assumption in an ADR or `assumptions.md`,
3. do not expand scientific scope,
4. do not silently change equations or acceptance thresholds.

## 10.8 Disallowed shortcuts
- hard-coding benchmark outputs,
- bypassing config validation,
- plotting from inside solver loops,
- writing dense fields every time step,
- using raw global variables for state,
- inventing undocumented observables.

## 10.9 Definition of done
The build is complete when:
- all three gates G1/G2/G3 pass,
- the matrix runner executes the full baseline campaign,
- the figure package exists,
- the acceptance checklist is green,
- the implementation backlog is substantially closed.
