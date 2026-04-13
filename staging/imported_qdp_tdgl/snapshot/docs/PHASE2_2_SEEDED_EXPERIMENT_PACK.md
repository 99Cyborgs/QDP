# Phase-2.2 Seeded Experiment Pack

Phase-2.2 extends the seeded-vortex Phase-2.1 hook into a schema-validated experiment pack without widening the scientific claim surface.

## Scope

Success in this tranche means only:

deterministic same-stack seeded initialization / short-horizon expectations were reproduced on the committed software stack.

It does not mean:

- equilibrium preparation validated
- long-time seeded-vortex dynamics validated
- stochastic robustness validated
- backend or cross-stack portability validated

## Manifest Contract

The committed suite manifest is `validation/seeded_vortex_phase2_2_manifest.yaml`.

Required top-level fields:

- `schema_version`
- `suite_id`
- `claim_scope`
- `defaults`
- `canonical_cases`
- `exercise_cases`
- `rejection_cases`

Unknown keys are rejected by `configs/seeded_vortex_experiment_manifest.schema.json`.

## Case Classes

- `initialization_only`
  Evidence is limited to the initialization surface and requires `n_steps: 0` with `sampling_policy: initialization_surface`.
- `short_horizon`
  Evidence is limited to the fixed early window and requires the declared short-horizon `n_steps` plus `sampling_policy: all_observable_samples_through_n_steps`.

The validator does not infer `short_horizon` coverage from an `initialization_only` pass.

## Canonical, Exercise, Rejection

- Canonical cases are frozen deterministic references with summary/final observable checks plus payload-hash checks.
- Exercise cases are invariant-only seeded checks. They do not freeze complete payloads.
- Rejection cases are first-class validation cases and must reproduce the expected seeded rejection taxonomy subset.

## Reporting

`tdgl-rf validate-seeded-vortices validation/seeded_vortex_phase2_2_manifest.yaml` writes:

- `seeded_vortex_validation.json`
- `seeded_vortex_validation.md`
- `seeded_vortex_validation_cases.csv`

Each output restates:

- `suite_id`
- `claim_scope`
- `validated_surfaces`
- `non_claims`
- explicit case-class counts
- explicit mismatch records

The Markdown report includes an `Interpretation Boundary` section.

## Provenance And Tier-2 Boundaries

- `provenance.json` is validated against `configs/tdgl_run_provenance.schema.json`.
- `diagnostics/seeded_vortex_tier2.json` is validated against `configs/seeded_vortex_tier2.schema.json`.
- rejection payloads are validated against `configs/seeded_vortex_rejection.schema.json`.

The Tier-2 payload is restricted to:

- `initialization_observables`
- `early_window_observables`

No Tier-2 field in this tranche is intended to imply equilibrium, relaxation quality, long-time persistence, or generic dynamics validation.
