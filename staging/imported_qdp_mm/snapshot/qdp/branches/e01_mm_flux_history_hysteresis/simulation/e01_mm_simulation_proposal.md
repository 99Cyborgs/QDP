# E01 MM Simulation-First Research Proposal

## Abstract

This proposal translates the E01 branch into a simulation-first research package that can be executed before cryogenic or field-bias hardware exists.
The package preserves the branch's mechanism order, implements exactly the five authorized synthetic cases, and produces deterministic outputs that demonstrate computational readiness for a later experimental campaign.

## Problem Statement

The current branch logic is scientifically conservative but operationally blocked by unavailable hardware.
Without a simulation package, proposal review would depend on narrative claims rather than executable evidence that the mechanism gates, summary metrics, and failure-mode challenges are already formalized.

## Specific Aims

- Implement H0, H1, H3, H2-gate, and H4 stress cases as deterministic executable code.
- Produce structured outputs that a reviewer can inspect without requiring plotting or third-party software.
- Demonstrate that branch metrics such as `H_O` and `A_O` are computable and reproducible before any hardware acquisition.
- Preserve the branch's conservative posture by refusing to add cases beyond the five already authorized by `simulation/e01_mm_minimal_sim_plan.md`.

## Innovation

- The proposal converts a branch specification into an executable simulation package without broadening scientific scope.
- The package keeps all runtime dependencies inside the Python standard library.
- The suite emits a proposal appendix directly from generated outputs, so the narrative and the computational artifacts stay synchronized.

## Technical Approach

The implementation consists of:

- `simulation/e01_mm_simulation_suite.py` for deterministic synthetic-case generation
- `simulation/test_e01_mm_simulation_suite.py` for metric and output-structure validation
- `simulation/e01_mm_simulation_appendix.md` as a generated proposal appendix tied to a declared seed

The suite covers:

- memoryless field loss with drift for H0 stress,
- generic hidden-state hysteresis for H1 stress,
- QP lag after field step for H3 stress,
- fabrication-noise false geometry ordering for H2-gate stress,
- package common-mode drift for H4 stress.

## Milestones And Go/No-Go Criteria

- Milestone 1: all five synthetic cases execute from a clean checkout.
- Milestone 2: JSON outputs are deterministic for a declared seed.
- Milestone 3: tests confirm core metric logic and output structure.
- Go condition: the suite and tests run without external dependencies or hardware.
- No-go condition: any branch case requires manual intervention, untracked assumptions, or unavailable instrumentation to execute.

## Deliverables

- executable simulation suite
- unit and smoke tests
- deterministic JSON outputs
- generated Markdown appendix for proposal inclusion

## Execution

```powershell
python simulation\e01_mm_simulation_suite.py --output-dir simulation_outputs --appendix-path simulation\e01_mm_simulation_appendix.md
python -m unittest simulation.test_e01_mm_simulation_suite
```

## Validation And Reproducibility

- The suite declares a base seed and derives deterministic per-case seeds.
- The appendix is generated from the same run that produces the JSON outputs.
- The tests validate both numerical metric behavior and artifact generation.

## Boundaries

- This package does not claim real-device realism.
- It does not replace the laboratory protocol.
- It does not promote H2 or any microscopic mechanism.
- It does not add phase 1 cases beyond the authorized five.

## Proposal Use

This package is suitable for a serious pre-hardware proposal because it provides executable evidence of computational readiness, an auditable appendix, explicit milestones, and a controlled boundary between synthetic validation and later experimental validation.
