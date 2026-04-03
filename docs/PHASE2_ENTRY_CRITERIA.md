# Phase-2 Entry Criteria

This document defines what must be true before phase-2 feature work is allowed to proceed. Phase-2 means new capability beyond the current deterministic phase-1 surface. Evidence packaging alone does not satisfy this gate.

## Gate Intent

- The deterministic phase-1 baseline remains the control surface for all near-term roadmap decisions.
- No phase-2 feature branch should merge unless the required deterministic baseline evidence exists on the current solver commit.
- If the solver core changes after the last successful validation run, the phase-2 gate automatically reopens until the required evidence is regenerated.

## Required Deterministic Baseline Evidence

The deterministic baseline is considered sufficient for phase-2 planning only when all of the following are true on the current branch:

- `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml` completes with overall status `success`.
- The generated validation artifacts from that run are internally consistent:
  - `validation_summary.csv`
  - `validation_summary.json`
  - `validation_report.md`
  - `campaign_summary/proposal_summary.csv`
  - `campaign_summary/proposal_summary.json`
  - `campaign_summary/proposal_summary.md`
  - `reference_checks/reference_check.json`
  - `reference_checks/reference_check.md`
  - `refinement_sanity/comparison_table.csv`
  - `refinement_sanity/comparison_table.json`
  - reproducibility outputs under `reproducibility/`
- The validation result still satisfies the current deterministic acceptance thresholds:
  - campaign acceptable rows: `16/16`
  - refinement sanity rows within bounds: `4/4`
  - frozen references matched: `4/4`
  - deterministic reproducibility: `pass`
- A reviewer-facing bundle can be regenerated from that same validation run with `tdgl-rf evidence-bundle <validation_dir>`.
- `docs/PHASE1_ACCEPTANCE.md`, `docs/PHASE1_VALIDATION_MEMO.md`, `VALIDATION.md`, `STATUS.md`, and this document all describe the same accepted baseline without contradiction.

## Residual Risks Tolerated At The Gate

The following limitations remain tolerated when entering phase-2. They must remain explicit and must not be reworded as solved problems:

- The current evidence is short-horizon and deterministic only.
- Same-stack reproducibility has been checked; cross-stack or cross-backend reproducibility has not.
- The refinement harness is a bounded drift check, not an asymptotic convergence proof.
- PETSc parity, larger-scale runs, seeded-vortex initial conditions, and stochastic workflows remain unvalidated.
- The proposal-usable deterministic surface is limited to the documented strip and simple masked-strip conditions in the current validation matrix and memo.

## Additional Evidence Required Before Specific Phase-2 Directions

### Stochastic Noise

Before stochastic noise work is allowed to proceed beyond prototype status:

- The deterministic phase-1 baseline must be rerun and pass on the target branch immediately before stochastic development begins.
- The RNG and seeding contract must be documented, including what is required to reproduce one seeded realization.
- A small stochastic smoke matrix with fixed seeds must exist, with explicit thresholds for acceptance and explicit limits on what can be claimed from it.
- The reproducibility statement must be widened from exact equality to an explicitly documented bounded stochastic policy before any claim is made.

### Ensembles

Before ensemble workflows are allowed to proceed:

- Single-realization stochastic runs must already satisfy their own documented smoke criteria.
- The ensemble summary schema, aggregation metrics, and minimum ensemble size for any reported statistic must be documented.
- A small ensemble validation surface must exist with fixed seed lists and stable aggregation outputs.
- Proposal-facing outputs must clearly separate deterministic baseline evidence from ensemble-derived statistics.

### Seeded Vortex Initialization

Before seeded-vortex initialization is allowed to proceed:

- Deterministic reference cases must exist with explicit expected initial vortex count and placement semantics.
- The initialization path must be shown not to inject unintended vortices or immediate setup artifacts on the accepted short-horizon surface.
- New frozen references and validation thresholds must be added for the seeded-vortex cases before broader interpretation is allowed.
- The operating-conditions and limitations surfaces must be updated to show the exact supported seeded-vortex regime.

### PETSc Parity / Larger-Scale Runs

Before PETSc parity or larger-scale claims are allowed to proceed:

- Overlapping deterministic parity cases must run on both SciPy and PETSc with explicit tolerances on final observables and trajectory drift.
- Solver iteration and failure-mode reporting must be captured for both backends on the overlapping cases.
- Larger mesh or longer-horizon cases may be used only after overlapping small-case parity passes; larger scale cannot be used as a substitute for parity.
- The hardware and software environment for the PETSc evidence must be recorded alongside the parity outputs.

## Required Reruns When The Solver Core Changes

If any solver-core behavior changes, the following must be rerun and regenerated on the new commit before the phase-2 gate can be considered closed again:

- The solver-touching baseline tests listed in `docs/PHASE1_ACCEPTANCE.md`
- `tdgl-rf refinement-sanity configs/phase1_refinement_sanity.yaml`
- `tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml`
- `tdgl-rf evidence-bundle <validation_dir>` for the refreshed validation run

Solver-core changes include, at minimum:

- updates under `src/tdgl_rf/solvers/`
- changes to link-variable, current, observable, or geometry-mask semantics
- changes to deterministic config defaults that alter numerical execution
- changes to workflow logic that change the contents or interpretation of validation metrics

## Gate Decision Rule

Phase-2 work may start only when the deterministic baseline evidence above exists on the current branch and the chosen phase-2 direction has an agreed additional-evidence plan from the relevant subsection above. If either condition is false, the work is still pre-gate.
