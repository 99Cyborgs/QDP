# Roadmap

## Current Baseline

Implemented now:

- typed seed registry loading
- repository validation
- surrogate scoring with multiple profiles
- reproducible single-run artifacts
- tranche and sweep orchestration
- typed CLI and API surfaces
- simulation and RF scaffolds

## Near-Term

- plug solver-backed simulation outputs into the existing slice artifact contract without overstating fidelity
- add RF-oriented tranche execution over validated Touchstone subsets
- add richer sweep-level provenance for environment and external file snapshots
- harden comparison reports with more tranche-level diagnostic views

## Mid-Term

- add safe parallel slice execution behind the current planner / manifest model
- integrate measured experiment outputs into the same provenance and comparison layer
- add DVC or experiment-catalog hooks around persisted sweep artifacts

## Long-Term

- add solver-backed ranking inputs only after forward contracts are mature
- add calibration-aware surrogate updates informed by measured data
- add inverse-design loops only after solver and evidence surfaces are reliable

## Guardrails

- no fake solver outputs
- no physics claims from robustness or sensitivity metrics
- no replacement of typed boundaries with loose orchestration scripts
- no distributed concurrency before deterministic single-process execution remains stable
