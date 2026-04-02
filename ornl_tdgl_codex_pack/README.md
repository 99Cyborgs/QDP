# ORNL TDGL-RF Codex Artifact Pack

This pack is an implementation-grade specification for building the **experiment platform** behind a proposal centered on **vortex-resolved stochastic TDGL + RF coupling + Bayesian inference**.

The pack is optimized for a coding agent. It converts the research concept into:
- a hard scientific charter,
- exact forward and inverse model requirements,
- numerical and software specifications,
- verification gates,
- a run matrix for the first experiment campaign,
- proposal-facing translation notes.

## Intended use

Feed this pack to Codex and instruct it to implement **v1 only**.

v1 scope is deliberately narrow:
- 2D thin-film TDGL
- prescribed RF mode profile
- low-dimensional pinning/noise inference
- synthetic data only
- structured Cartesian mesh
- gauge-invariant link-variable finite differences
- IMEX time stepping first, fully implicit later

## Non-goals for v1

Do **not** let Codex expand scope into:
- full 3D electromagnetics
- microscopic nonequilibrium superconductivity
- full-chip package co-simulation
- neural operators / surrogates
- self-consistent Maxwell solves
- MFEM integration
- laboratory instrumentation code

## Recommended implementation stack

- Python 3.11
- `numpy`
- `scipy`
- `petsc4py`
- `mpi4py`
- `h5py`
- `pydantic>=2`
- `pyyaml`
- `pandas`
- `pytest`
- `typer`

The intent is:
- high-level orchestration in Python,
- linear algebra / time stepping through PETSc where appropriate,
- HDF5 for field and summary outputs,
- MPI-first architecture,
- later GPU portability through PETSc rather than bespoke kernels in v1.

## Read order for Codex

1. `manifest.yaml`
2. `docs/01_program_charter.md`
3. `docs/02_physics_spec.md`
4. `docs/03_numerics_spec.md`
5. `docs/04_software_architecture.md`
6. `docs/05_verification_validation.md`
7. `docs/06_bayesian_inference_spec.md`
8. `docs/07_experiment_matrix_guide.md`
9. `docs/10_codex_build_instructions.md`
10. sample configs and experiment matrix

## Minimum deliverable

Codex should produce a repository that can:
- run deterministic TDGL test cases,
- add stochastic forcing,
- detect vortices,
- compute reduced observables (`Δf/f0`, `Q^-1`, event statistics),
- execute small synthetic inverse studies,
- orchestrate campaign runs from a CSV matrix,
- pass the acceptance tests in `docs/05_verification_validation.md`.

## File map

- `docs/` — scientific, numerical, software, and proposal docs
- `configs/` — schema and baseline YAML configurations
- `matrices/` — first campaign definition
- `prompts/` — ready-to-use Codex prompt
- `tasks/` — build backlog and acceptance checklist

## Suggested human workflow

1. Hand the pack to Codex.
2. Require phase-gated delivery.
3. Do not approve stochastic/inference work until deterministic V&V passes.
4. Do not approve proposal prose until the figure set in `docs/09_proposal_translation_brief.md` exists.
