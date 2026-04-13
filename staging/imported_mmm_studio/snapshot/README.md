# MMM Studio

## Current State

- `mmm-studio` is a Python 3.11 package (`pyproject.toml`, version `0.2.0`) for typed metamaterial discovery and analysis workflows.
- The implemented core is the typed registry and scoring pipeline:
  - seed registry loading from `data/mmm_seed/`
  - repository validation
  - surrogate scoring with multiple profiles
  - reproducible run artifacts, reports, and provenance
- The implemented orchestration layer supports:
  - declarative sweep specs
  - tranche and slice planning
  - deterministic sweep execution with failure isolation
  - cross-slice aggregation and summary artifacts
- The current user-facing surfaces are:
  - a Typer CLI in `src/mmm_studio/cli.py`
  - a FastAPI app in `src/mmm_studio/api.py`
- Simulation and RF modules exist under `src/mmm_studio/sim/` and `src/mmm_studio/rf/`, but they are still scaffolds and utility layers rather than full production execution paths.
- The project does not yet implement solver-backed simulation runs, measured RF tranche execution, inverse design loops, learned surrogate training, or distributed execution.

## Goal

MMM Studio's goal is to be a reproducible, typed workbench for metamaterials R&D: load a structured registry, validate it, run comparable ranking experiments, and preserve the artifacts needed to inspect, compare, and extend those experiments without overstating what the software has actually proven.

## Next Steps

- Connect real solver-backed simulation outputs to the existing typed run and slice artifact contracts.
- Add RF-oriented tranche execution over validated measurement datasets.
- Improve sweep provenance so environment details and external inputs are captured more completely.
- Expand tranche and sweep diagnostics to make comparison outputs more decision-useful.
- Add safe parallel slice execution only after deterministic single-process behavior remains stable.
