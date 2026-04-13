# qdp_validation

Destination package for umbrella validation and promotion gates.

Current extraction status:

- active repo-consistency validation surface under `src/qdp_validation/repo_consistency.py`
- active artifact and interface-contract validation surface under `src/qdp_validation/artifact_contracts.py`
- active bootstrap-facing module selftest-orchestration surface under `src/qdp_validation/module_workflows.py`
- active bootstrap-facing module verification-aggregation surface under `src/qdp_validation/module_verification.py`
- root `qdp_validation.py` and `tools/workflow/qdp_runtime/qdp_validation.py` are now compatibility facades over the package
- broader scientific-threshold extraction from donor validation packs remains deferred

Active ownership in this phase:

- acceptance checks
- repo-consistency validation
- frozen ALL-MIND interface validation
- regression gates around structural consistency versus authoritative readiness
- promotion and readiness guardrails at the umbrella-repo level
- bootstrap-facing module selftest summary evaluation and module verification aggregation

Explicitly not owned here in this phase:

- materials-registry validation that belongs in `packages/qdp_meta_materials/`
- TDGL runtime config validation that belongs in `packages/qdp_tdgl/`
- repo-root orchestration and queue/control-plane execution logic

Package-local domain validation should stay with its owning package where appropriate.

Validation in this phase should target the package directly, for example:

```powershell
$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_validation/src"
python -m pytest tests/unit/test_qdp_validation_smoke.py -q
```
