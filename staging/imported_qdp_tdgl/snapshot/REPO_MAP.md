# Repo Map

## Active Control Surfaces

- `src/tdgl_rf/`: active packaged TDGL-RF control plane, including CLI entrypoints, workflows, analysis, config validation, and run orchestration
- `validation/`: committed validation and experiment manifests for deterministic phase-1, seeded-vortex Phase-2.2, deterministic Phase-2.3, and stochastic Phase-2.4A runtime/validation surfaces
- `configs/`: authoritative config inputs plus JSON schemas for case configs, manifests, provenance, Tier-2 payloads, and rejection payloads
- `docs/`: phase-boundary, acceptance, validation, and decision-support documents
- `tests/`: unit, integration, and acceptance coverage for the active `tdgl-rf` surface

## Legacy Control Surfaces

- `qdp.py`: legacy repo-level entrypoint for bootstrap, candidate checks, and module operations
- `qdp_validation.py`: legacy candidate-validation entrypoint and shared sweep helpers
- `modules/`: legacy domain modules and runnable program pieces behind `qdp.py module ...`
- `tools/`: legacy and supporting utilities
- `artifacts/`: generated legacy outputs and reports; not an authority source

## Supporting / Transitional Areas

- `runtime/`: legacy runtime support code outside the packaged `tdgl-rf` surface
- `config/`: legacy repo-local configuration inputs
- `specs/`: legacy scientific and operating specs
- `QDP_REPO_REFACTOR_PLAN.md`: structure and cleanup direction

## Key Committed Validation Entrypoints

- `tdgl-rf validate-phase1 ...`: deterministic phase-1 baseline validation tranche
- `tdgl-rf validate-seeded-vortices validation/seeded_vortex_phase2_2_manifest.yaml`: bounded deterministic seeded-vortex suite
- `tdgl-rf run-experiment validation/seeded_vortex_phase2_3_experiment_pack.yaml`: deterministic seeded-vortex experiment harness
- `tdgl-rf run-experiment validation/seeded_vortex_phase2_4a_experiment_pack.yaml`: committed stochastic Phase-2.4A operator pack
- `tdgl-rf validate-phase2-4a validation/seeded_vortex_phase2_4a_validation_manifest.yaml`: committed same-stack Phase-2.4A validation surface
- `python qdp_validation.py`: legacy candidate sweep over emitted `*_candidate.json` artifacts
