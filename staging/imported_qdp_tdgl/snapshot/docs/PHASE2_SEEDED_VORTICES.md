# Phase-2 Seeded Vortices

This note records the current seeded-vortex boundary after Phase-2.2 plus the committed Phase-2.4A runtime operator pack and fixed-seed same-stack validation surface. The scientifically validated seeded-vortex surface remains a deterministic same-stack experiment pack for seeded initialization, bounded short-horizon replay, and seeded-input rejection taxonomy checks. That validated surface is not a broad vortex-physics claim, and the committed Phase-2.4A runtime and validation artifacts do not widen it.

## Active Surface

- Scientifically validated only through `physics.initial_condition: seeded_vortices`
- Scientifically validated only for deterministic runs with `noise.enabled: false`
- Scientifically validated only as an initialization ansatz for `psi`
- Scientifically validated only when every configured seed lies inside one fully active plaquette
- Scientifically validated only through same-stack replay-oriented evidence
- Runtime-capable but scientifically unvalidated through `validation/seeded_vortex_phase2_4a_experiment_pack.yaml`, which exists to exercise the stochastic ensemble control plane with fixed sweep and ensemble settings
- Same-stack runtime/control-plane validated through `validation/seeded_vortex_phase2_4a_validation_manifest.yaml`, which freezes fixed-seed member identity, selected replay metadata, aggregate observables, and robustness summaries without adding scientific stochastic acceptance claims

## Validation Split

Phase-2.2 separates seeded success cases into two non-interchangeable classes:

- `initialization_only`: step-0 / initialization-surface evidence only
- `short_horizon`: bounded early-window evidence only

The committed suite is defined by:

- `validation/seeded_vortex_phase2_2_manifest.yaml`
- `configs/seeded_vortex_experiment_manifest.schema.json`
- `configs/seeded_vortex_tier2.schema.json`
- `configs/seeded_vortex_rejection.schema.json`
- `configs/tdgl_run_provenance.schema.json`

Detailed suite design and reporting rules live in [docs/PHASE2_2_SEEDED_EXPERIMENT_PACK.md](docs/PHASE2_2_SEEDED_EXPERIMENT_PACK.md).

## Runtime Artifacts

Successful seeded runs write:

- `provenance.json` with same-stack replay metadata, package capture, numeric dtype metadata, and configured/resolved seed order
- `diagnostics/seeded_vortex_tier2.json` with explicit horizon contracts plus `initialization_observables` and, when applicable, `early_window_observables`

The committed Phase-2.4A operator pack writes the same replay-oriented `provenance.json` and Tier-2 payload surface for each ensemble member plus aggregated `experiment_results.json|csv|md` with per-parameter-point robustness summaries over successful members, but those outputs remain runtime-only control-plane evidence rather than scientific validation artifacts.

The committed Phase-2.4A validation surface reruns that operator pack through `tdgl-rf validate-phase2-4a validation/seeded_vortex_phase2_4a_validation_manifest.yaml` and emits `phase2_4a_validation.json`, `phase2_4a_validation.md`, and `phase2_4a_validation_cases.csv`. That surface compares only the frozen semantic contract, excluding absolute paths, output directories, and other path-dependent replay metadata.

## Non-Claims

- This surface does not establish equilibrium preparation.
- This surface does not establish long-time seeded-vortex dynamics.
- This surface does not establish stochastic robustness.
- This surface does not establish backend or cross-stack portability.
- This surface does not establish generic seeded-vortex validation beyond the committed case classes and same software stack.
