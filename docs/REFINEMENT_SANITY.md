# Refinement Sanity Harness

The phase-1 refinement sanity harness runs one canonical deterministic RF-driven case over:

- two mesh levels: the base mesh and a `1.5x` refinement with preserved aspect ratio
- two time steps: `dt` from the input config and `dt / 2`

The default committed input is `configs/phase1_refinement_sanity.yaml`.

## Invocation

```bash
tdgl-rf refinement-sanity configs/phase1_refinement_sanity.yaml
```

To choose a custom output directory:

```bash
tdgl-rf refinement-sanity configs/phase1_refinement_sanity.yaml --output-dir runs/refinement_sanity/manual_check
```

## Outputs

The workflow writes:

- `comparison_table.csv`
- `comparison_table.json`
- per-run expanded configs under `configs/`
- per-run case outputs under `case_runs/`

Each comparison row records the mesh, `dt`, final reduced observables, and absolute differences against the finest mesh / smallest-`dt` reference run. This is a sanity harness for controlled baseline checks, not a formal convergence proof.
