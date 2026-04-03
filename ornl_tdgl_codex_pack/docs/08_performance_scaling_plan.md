# 08. Performance and scaling plan

## 8.1 Performance objective
The performance objective for v1 is not full production optimization. It is to show that the code architecture supports:

- domain decomposition within a realization,
- ensemble parallelism across realizations,
- reduced-output workflows,
- deterministic reproducibility,
- credible scaling to leadership-class campaigns.

## 8.2 Performance hierarchy

### Level L0 — workstation
Purpose:
- correctness development,
- unit and integration tests,
- small deterministic cases.

### Level L1 — single-node CPU
Purpose:
- medium deterministic runs,
- short stochastic ensembles,
- profiling of IO and solver iterations.

### Level L2 — single-node accelerator or strong CPU node
Purpose:
- throughput characterization for ensemble workloads,
- early memory-pressure and output-pressure studies.

### Level L3 — multi-node pilot
Purpose:
- MPI decomposition,
- weak and strong scaling,
- campaign orchestration.

## 8.3 Metrics to record
Every performance run must record:
- wall clock,
- solver iteration counts,
- time in:
  - forcing setup,
  - phi solve,
  - psi solve,
  - observable extraction,
  - IO,
- peak memory estimate,
- output volume,
- rank count,
- ensemble count.

## 8.4 Scaling experiments

### Strong scaling
Fix:
- one realization,
- one mesh,
- one time horizon.

Vary:
- rank count.

Track:
- wall clock,
- efficiency,
- communication fraction if measurable.

### Weak scaling
Fix:
- local cells per rank.

Vary:
- total ranks and global problem size.

Track:
- time per step,
- efficiency,
- IO growth.

### Ensemble scaling
Fix:
- realization size.

Vary:
- number of simultaneous realizations.

Track:
- throughput in realizations/hour,
- scheduling overhead,
- aggregate output bandwidth.

## 8.5 Minimum targets
These are proposal-readiness targets, not hard physical truths.

- deterministic reference case on a development machine should complete within a practical interactive window,
- weak scaling efficiency target: `>= 70%` across the pilot range,
- strong scaling efficiency target: `>= 60%` across the pilot range,
- ensemble throughput should scale near-linearly until IO becomes the bottleneck.

Codex should report measured values even if the targets are missed.

## 8.6 Output strategy
Performance runs must use reduced output by default:
- dense time-series output,
- sparse field checkpoints,
- compressed HDF5 where possible.

This is mandatory. Full-field-every-step runs are disallowed except for very short debugging cases.

## 8.7 Performance risk register

### Risk: solver dominated by scalar-potential solve
Mitigation:
- profile separately,
- test preconditioners,
- cache geometry structures.

### Risk: IO dominates ensemble runs
Mitigation:
- lower field cadence,
- aggregate summary writes,
- separate debug and production output modes.

### Risk: Python orchestration overhead becomes visible
Mitigation:
- keep per-step kernels vectorized,
- avoid Python loops over cells,
- move only proven hotspots behind optimized wrappers if needed.

## 8.8 Deliverables for proposal readiness
The code should generate:
- a scaling table,
- one strong-scaling plot,
- one ensemble-throughput plot,
- a projected workload table for the proposed campaign.
