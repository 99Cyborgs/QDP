# Phase-2 Seeded Vortices

This note records the current seeded-vortex boundary after Phase-2.2. The active surface is a deterministic same-stack experiment pack for seeded initialization, bounded short-horizon replay, and seeded-input rejection taxonomy checks. It is not a broad vortex-physics validation claim.

## Active Surface

- Supported only through `physics.initial_condition: seeded_vortices`
- Supported only for deterministic runs with `noise.enabled: false`
- Supported only as an initialization ansatz for `psi`
- Supported only when every configured seed lies inside one fully active plaquette
- Supported only through same-stack replay-oriented evidence

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

The separate committed Phase-2.4A runtime smoke manifest `validation/seeded_vortex_phase2_4a_runtime_smoke.yaml` may execute seeded short-horizon cases with `noise.enabled: true` for control-plane and provenance checks, but it is not part of this deterministic validation boundary and does not widen the seeded-vortex claim surface.

## Runtime Artifacts

Successful seeded runs write:

- `provenance.json` with same-stack replay metadata, package capture, numeric dtype metadata, and configured/resolved seed order
- `diagnostics/seeded_vortex_tier2.json` with explicit horizon contracts plus `initialization_observables` and, when applicable, `early_window_observables`

## Non-Claims

- This surface does not establish equilibrium preparation.
- This surface does not establish long-time seeded-vortex dynamics.
- This surface does not establish stochastic robustness.
- This surface does not establish backend or cross-stack portability.
- This surface does not establish generic seeded-vortex validation beyond the committed case classes and same software stack.
