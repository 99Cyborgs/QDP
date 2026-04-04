---
name: qdp-seeded-vortex-suite
description: Run the committed Phase-2.2 seeded-vortex validation suite through tdgl-rf validate-seeded-vortices and keep its initialization-only, short-horizon, and rejection-taxonomy claim boundaries explicit. Use when working with validation/seeded_vortex_phase2_2_manifest.yaml and its committed schemas, provenance contract, Tier-2 payload contract, or rejection taxonomy. Do not use for Phase-2.3 experiment packs, ad hoc single-case seeded runs, or stochastic ensemble work.
---

# Purpose

Execute and inspect the bounded deterministic same-stack seeded-vortex suite defined for Phase-2.2 without widening what the suite claims.

# Use when

- The task is to rerun `validation/seeded_vortex_phase2_2_manifest.yaml`.
- The task is to inspect seeded suite mismatch records, rejection taxonomy drift, or Tier-2/provenance drift.
- The task is to verify that seeded initialization-only and short-horizon cases still match the committed contract.

# Do not use when

- The task is a Phase-2.3 deterministic experiment pack. Use `qdp-seeded-vortex-experiment-pack`.
- The task is one seeded config without suite interpretation. Use `qdp-run-case`.
- The task is a 4.x stochastic ensemble. Leave that explicit and unencoded unless the repo promotes a committed operator surface.
- The task changes schemas, manifest dispatch, or rejection contract fields. Use `qdp-contract-sync`.

# Inputs required

- Seeded-vortex suite manifest path.
- Optional output directory.

# Files and directories to inspect first

- `docs/PHASE2_SEEDED_VORTICES.md`
- `docs/PHASE2_2_SEEDED_EXPERIMENT_PACK.md`
- `validation/seeded_vortex_phase2_2_manifest.yaml`
- `configs/seeded_vortex_experiment_manifest.schema.json`
- `configs/seeded_vortex_tier2.schema.json`
- `configs/seeded_vortex_rejection.schema.json`
- `configs/tdgl_run_provenance.schema.json`
- `src/tdgl_rf/workflows/seeded_vortex_suite.py`
- `tests/unit/test_seeded_vortex_suite.py`
- `tests/acceptance/test_seeded_vortex_acceptance.py`

# Step-by-step procedure

1. Read the phase-2 seeded docs first to restate the active surface and non-claims.
2. Run the committed suite manifest with `validate-seeded-vortices`.
3. Inspect the generated JSON before the Markdown report so mismatch records and case counts are explicit.
4. Verify the case split remains non-interchangeable:
   `initialization_only` stays step-0 only, and `short_horizon` stays bounded early-window only.
5. Confirm provenance, Tier-2 payloads, and rejection payloads still validate against their committed schemas.
6. Restate the interpretation boundary from the generated report whenever you summarize the run.

# Exact commands

```bash
tdgl-rf validate-seeded-vortices validation/seeded_vortex_phase2_2_manifest.yaml
```

# Validation / definition of done

- The command exits successfully and writes:
  `seeded_vortex_validation.json`, `seeded_vortex_validation.md`, and `seeded_vortex_validation_cases.csv`.
- The JSON restates `suite_id`, `claim_scope`, `validated_surfaces`, and `non_claims`.
- Canonical cases, exercise cases, and rejection cases all match their expected contract surfaces.
- The Markdown report contains an `Interpretation Boundary` section.

# Failure modes / escalation

- Manifest schema failure or unknown key:
  Fix the manifest or switch to `qdp-contract-sync` if the schema must change.
- Horizon contract mismatch:
  Treat it as real drift between config, Tier-2 payload, and manifest defaults.
- Rejection taxonomy mismatch:
  Report the exact `code`, `field_path`, or `seed_index` drift.
- Provenance or Tier-2 mismatch:
  Inspect the schema-backed payloads first, then the generating workflow.

# Output artifacts

- `runs/seeded_vortex_validation/.../seeded_vortex_validation.json`
- `runs/seeded_vortex_validation/.../seeded_vortex_validation.md`
- `runs/seeded_vortex_validation/.../seeded_vortex_validation_cases.csv`

# Example prompts that SHOULD trigger the skill

- "Re-run the Phase-2.2 seeded-vortex suite and show me any mismatch records."
- "Check whether the seeded rejection taxonomy still matches the committed manifest."
- "Validate the bounded short-horizon seeded surface after my change."

# Example prompts that should NOT trigger the skill

- "Run the deterministic seeded-vortex experiment pack sweep."
- "Execute one seeded config and inspect its output."
- "Add a new field to the seeded-vortex Tier-2 schema."
