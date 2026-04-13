# E01 MM Exact Falsifier

## Disposition Codes

- `KILL_ENTIRE_BRANCH`: the metastable memory registration fails and the branch should not proceed under this tag.
- `DOWNGRADE_VORTEX_ONLY`: the generic metastable memory branch may remain open, but vortex-specific interpretation is blocked.
- `PRESERVE_GENERIC_MM_BRANCH`: retain the branch only as a conservative metastable memory candidate.
- `PRESERVE_VORTEX_CANDIDATE_UPGRADE_PATH`: keep the option to test H2 later, but do not promote yet.

## Exact Outcome Matrix

| Condition | Exact decision rule | Branch disposition | Vortex status |
| --- | --- | --- | --- |
| `1. hysteresis disappears when dwell increases` | If doubling dwell to the convergence criterion drives both `H_O` and `A_O` into the zero-field plus sham envelope, the observed loop is equilibration lag rather than retained history. | `KILL_ENTIRE_BRANCH` | `blocked` |
| `2. sham timing reproduces loop area` | If a sham run with matched timing and readout cadence reproduces `A_O` within the measurement confidence interval, the loop is timing-induced and not field-history-induced. | `KILL_ENTIRE_BRANCH` | `blocked` |
| `3. memoryless field model explains data` | If H0 with allowed drift correction explains the looped data, the zero-field checkpoints, and held-out cooldowns without branch-ordered residual structure, no retained state is needed. | `KILL_ENTIRE_BRANCH` | `blocked` |
| `4. geometry ordering absent` | If same-chip matched widths do not show the required susceptibility ordering under the same protocol, H2 loses its geometry support. | `PRESERVE_GENERIC_MM_BRANCH` | `DOWNGRADE_VORTEX_ONLY` |
| `5. geometry ordering inconsistent across cooldowns` | If the ordering changes sign, rank, or vanishes across the minimum three cooldowns, H2 is not stable enough for promotion. | `PRESERVE_GENERIC_MM_BRANCH` | `DOWNGRADE_VORTEX_ONLY` |
| `6. package witness co-moves with target signal` | If the witness channel co-moves with comparable timing and sufficient amplitude to account for `H_O` or `A_O` under a fixed gain mapping derived from control segments, package or EM drift wins. | `KILL_ENTIRE_BRANCH` | `blocked` |
| `7. QP lag dominates selected field time traces` | Immediately remove `T1` as supporting evidence. If the H3 lag model also reconstructs the primary `1/Qi` loop within held-out error, kill the branch. If H3 only explains the selected-field time traces and not the primary hysteresis metrics, retain the generic branch but block vortex promotion. | `KILL_ENTIRE_BRANCH` or `PRESERVE_GENERIC_MM_BRANCH` by the stated rule | `DOWNGRADE_VORTEX_ONLY` unless H3 also explains the primary observable |

## Upgrade Path Preservation Rule

Only preserve the vortex candidate upgrade path when all of the following remain true:

- Dwell-converged hysteresis survives the sham timing control.
- H0 does not explain the primary observable.
- H3 does not explain the primary observable.
- H4 does not explain the primary observable.
- Same-chip matched geometry shows consistent susceptibility ordering across the minimum three cooldowns.
- Package witness remains non-coincident with the target signal under the fixed analysis protocol.

If any item above fails, retain at most the conservative metastable memory branch.
