# Sweeps

This document describes MMM Studio's tranche and sweep system.

## Concepts

- **slice**: one bounded candidate-ranking pass
- **tranche**: a managed collection of related slices executed together
- **sweep**: the top-level plan that owns tranches, manifests, summaries, and shared provenance

Current slices execute through the existing surrogate scorer only.

## Spec Model

The sweep input contract is `SweepSpec`.

Top-level fields:

- `name`
- `description`
- `version`
- `default_output_root`
- `global_filters`
- `shared_parameters`
- `adaptive`
- `tranches`

Tranche fields:

- `tranche_id`
- `objective`
- `execution_mode`
- `shared_profile`
- `slices`
- `comparison_strategy`

Slice fields:

- `slice_id`
- `input_registry_scope`
- `candidate_filters`
- `profile_override`
- `parameter_overrides`
- `output_requirements`
- `tags`

Adaptive fields:

- `enabled`
- `seed`
- `utility_weights`
- `null_model`
- `robustness`
- `refinement`
- `redundancy`
- `cross_tranche`

Important adaptive controls:

- `refinement.candidate_count_floor`: skip generated child slices that become too small
- `refinement.minimum_pending_per_phase`: preserve at least this many pending slices in each adaptive phase so pruning cannot silently collapse the entire frontier
- `refinement.categorical_top_values`: cap categorical branch fanout deterministically
- `refinement.utility_prune_threshold`: utility floor applied before executing pending adaptive slices
- `redundancy.*_similarity_threshold`: explicit similarity gates used for redundancy pruning
- `cross_tranche.max_interaction_slices`: hard cap on generated interaction slices

## Example

```yaml
schema_name: mmm_studio.sweep_spec
schema_version: "1.0"
name: profile-comparison
description: Compare the built-in scoring profiles on the shared registry.
version: "1.0.0"
default_output_root: artifacts/runs/sweeps
shared_parameters:
  default_profile: broadband
  top_n: 8
tranches:
  - tranche_id: profile_comparison
    objective: Compare profile sensitivity on the same candidate pool.
    shared_profile: broadband
    slices:
      - slice_id: broadband
        profile_override: broadband
      - slice_id: resonance_targeted
        profile_override: resonance_targeted
      - slice_id: manufacturability_aware
        profile_override: manufacturability_aware
```

Runnable examples live under `examples/sweeps/`.

The adaptive example lives at `examples/sweeps/adaptive_hypothesis_search.yaml`.

## Comparison Metrics

### Robustness score

`robustness_score` is a **software comparison metric**. It summarizes how consistently strong a candidate remains across successful slices.

Current implementation:

```text
robustness_score =
    0.55 * mean_normalized_rank
  + 0.30 * appearance_rate
  + 0.15 * top_k_rate
```

Where:

- `mean_normalized_rank` rewards high placement within each slice
- `appearance_rate` rewards showing up across more successful slices
- `top_k_rate` rewards repeated top-k appearances

This metric is bounded to `[0, 1]` and is **not a physics claim**.

### Profile sensitivity score

`profile_sensitivity_score` is another software comparison metric. It highlights candidates whose relative standing moves sharply across slices.

Current implementation combines:

- normalized rank span
- score standard deviation

Again, this is about sweep behavior under the surrogate pipeline, not physical instability.

## Supported Working Patterns

Implemented now:

- profile comparison tranches
- geometry-family or mechanism-subset tranches
- threshold sensitivity tranches over fabrication complexity and related filters

Structured for later:

- RF subset tranches
- simulation-backed slice executors
- parallel slice dispatch

## Commands

```bash
mmm-studio sweep-validate examples/sweeps/profile_comparison.yaml
mmm-studio sweep-plan examples/sweeps/profile_comparison.yaml --output artifacts/runs/sweeps/profile_plan
mmm-studio sweep-run examples/sweeps/profile_comparison.yaml --output-dir artifacts/runs/sweeps/profile_run
mmm-studio sweep-summary artifacts/runs/sweeps/profile_run
mmm-studio tranche-summary artifacts/runs/sweeps/profile_run --tranche profile_comparison
mmm-studio compare-slices artifacts/runs/sweeps/profile_run --tranche profile_comparison
```

## API Endpoints

- `POST /sweeps/validate`
- `POST /sweeps/plan`
- `POST /sweeps/run`
- `GET /sweeps/{sweep_id}/summary`
- `GET /sweeps/{sweep_id}/tranches/{tranche_id}`

## Failure Model

The executor is sequential and deterministic.

- one slice failure does not discard the rest of the sweep
- the parent `sweep_manifest.json` records per-slice status and error text
- failed slices still get local error artifacts so the sweep remains inspectable

## Adaptive Audit Surface

Adaptive sweeps now persist their decision policy more explicitly:

- `sweep_manifest.json`
  - `execution_order` records queue order, utility, source, and tie-break serial
  - `decision_log` records generated, skipped, pruned, and retained adaptive decisions
- `sweep_summary.json` and `tranche_summary.json`
  - `adaptive_audit` rolls up refinement, pruning, and cross-tranche activity
  - `null_model_summary` reports requested-vs-available baseline coverage and delta rollups
- `sweep_summary.md`
  - includes an execution ledger table for post hoc review
- `tranche_summary.md`
  - includes per-slice utility basis, warning codes, prune reason, and null-model delta columns
