# MMM Discovery Engine Specification

## Objective
Generate, score, and down-select metamaterial candidates that can modify environmental coupling while remaining falsifiable against baseline mechanisms.

## Pipeline
| Stage | Name | Action | Hard gate |
| --- | --- | --- | --- |
| D0 | Problem framing | Select target device class, target decoherence channel, and allowed fabrication stack. | Baseline-null plan defined before search |
| D1 | Topology seeding | Use topology grammars and template libraries to generate candidate families. | Feature sizes and keepouts valid |
| D2 | Broad scan | Run Latin-hypercube / Sobol sweeps for coarse objective maps. | At least one observable exceeds detectability floor |
| D3 | Local optimization | Use surrogate-guided optimization and package co-simulation. | Package sensitivity bounded |
| D4 | Pareto ranking | Select candidates by multiobjective frontier. | Null-risk and feasibility constraints met |
| D5 | Robustness | Apply tolerance Monte Carlo and assembly perturbations. | Yield floor preserved |
| D6 | Null attack | Adversarially search baseline explanations. | No null reproduces >=80% of effect |
| D7 | Campaign update | Update ranks after fabrication/measurement. | Validation status machine-checkable |

## Objective vector
- Coherence uplift in target observable
- Null separation margin
- Detectability margin
- Geometry-scaling clarity
- Fabrication robustness
- Replication portability
- Simulation confidence
- Standard-lab feasibility

## Hard constraints
- No candidate without explicit observable / protocol / validation mapping
- No lead candidate with unmitigated exotic fabrication
- No candidate whose only predicted signal is below instrument floor
- No promotion without matched sham and same-package controls

## Algorithms
| Algorithm | Purpose | Stage |
| --- | --- | --- |
| ALG-001 | Generate planar microwave stopband structures from a constrained grammar of CPW corrugations, patch arrays, and inductive fences. | D1_seed |
| ALG-002 | Generate suspended or non-suspended phononic crystals, graded sinks, and Bragg structures. | D1_seed |
| ALG-003 | Explore continuous parameter spaces for each topology family with broad coverage before local optimization. | D2_broad_scan |
| ALG-004 | Optimize stopband placement, LDOS suppression, or phononic isolation under expensive simulation cost. | D3_local_opt |
| ALG-005 | Identify Pareto-optimal tradeoffs between coherence benefit, fabrication complexity, and null-risk exposure. | D4_pareto |
| ALG-006 | Estimate candidate survival under fabrication tolerances and package assembly variation. | D5_robustness |
| ALG-007 | Search for ordinary explanations that can reproduce the predicted signal without invoking metamaterial mechanisms. | D6_null_attack |
| ALG-008 | Co-optimize chip pattern and package/lid environment to prevent false-positive packaging improvements. | D3_local_opt |
| ALG-009 | Update candidate ranking after each fabrication and measurement batch using measured observables and falsification outcomes. | D7_campaign_update |

## Candidate ranking
The authoritative scoring model is `mmm_candidate_ranking_model.yaml`.

## Reference pseudo-code
```python
for target in program_targets:
    seeds = topology_grammar(target)
    broad_pool = space_filling_scan(seeds)
    optimized = constrained_surrogate_optimize(broad_pool)
    robust = tolerance_monte_carlo(optimized)
    attacked = null_adversary_search(robust)
    ranked = rank_candidates(attacked)
    promote(ranked, rules=["detectability", "null_closure", "geometry_scaling", "lab_feasibility"])
```

## Outputs
- Candidate geometries
- Parameter bounds
- Pareto fronts
- Null-risk updates
- Ranked mask recommendations
