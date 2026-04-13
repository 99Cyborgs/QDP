---
name: qdp-interface-and-readiness-guard
description: Use when changing QDP's frozen ALL-MIND interface, authoritative-readiness logic, queue surfaces, or campaign prepare/plan flow so structural consistency, readiness, and repo-local operator state do not get conflated. Do not use for isolated branch science work outside the repo control surface.
---

# QDP Interface And Readiness Guard

## Purpose
Keep the frozen `ALL-MIND` interface narrow and truthful. Preserve the distinction between structural consistency and authoritative readiness.

## When to use
Use this skill when touching:
- `config/schema/all_mind_interface_schema.json`
- `INTEGRATION_PLAN.md`
- `VALIDATION.md`
- `qdp_validation.py`
- queue logic or queue reports
- readiness tests
- campaign prepare / plan outputs

## Required inputs
- repo root
- changed paths

## Operating procedure
1. Read `README.md`, `REPO_MAP.md`, `VALIDATION.md`, and `INTEGRATION_PLAN.md`.
2. Run `scripts/check_qdp_interface.py --repo-root <repo-root> --changed <paths...>`.
3. If the frozen interface or readiness surface changed, run the canonical validation wrapper.
4. If the task needs a staging-grade claim, escalate to the authoritative-ready gate explicitly.
5. Keep queue state, queue logs, and campaign batch outputs repo-local unless the contract says otherwise.

## Output contract
Always return:
1. `Frozen Interface Impact`
2. `Readiness Claim Boundary`
3. `Repo-Local State Surfaces`
4. `Required Validation`

## Hard invariants
- `structural_consistency_passed` is not authoritative readiness.
- `artifacts/reports/system/all_mind_interface.json` is narrow interface output, not whole-repo truth.
- Queue state and queue logs remain repo-local operator state.
- Generated simulation and campaign outputs do not become governing inputs.

## Failure handling
If docs or tests blur structural consistency and readiness:
- treat that as a correctness issue
- point to the exact conflicting file
- avoid readiness claims until the wording and tests are aligned
