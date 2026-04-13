# qdp_control

Destination package for umbrella orchestration and non-runtime pipeline control logic.

Current extraction status:

- active control-plane persistence surface under `src/qdp_control/control_plane.py`
- active run-ledger surface under `src/qdp_control/run_ledger.py`
- active campaign prepare/plan surface under `src/qdp_control/campaign_planner.py`
- active queue-manifest and queue-state orchestration surface under `src/qdp_control/queue.py`
- active lab pack/ingest orchestration surface under `src/qdp_control/lab_workflows.py`
- `qdp.py` and `tools/workflow/qdp_runtime/qdp_cli.py` remain the command shell and consume this package

Active ownership in this phase:

- campaign execution
- queue and control-plane orchestration
- lab request and ingest orchestration
- run-ledger persistence for repo-local operations
- non-runtime workflow coordination

Explicitly not owned here in this phase:

- TDGL runtime execution logic in `packages/qdp_tdgl/`
- materials domain logic in `packages/qdp_meta_materials/`
- frozen ALL-MIND interface validation and repo-consistency gates in `packages/qdp_validation/`
- root command wrappers and the transitional CLI shell itself

This package should orchestrate package APIs instead of re-owning materials logic or TDGL runtime internals.

Validation in this phase should target both the package and the queue/campaign surfaces, for example:

```powershell
$env:PYTHONPATH = "packages/qdp_control/src"
python -m pytest tests/unit/test_qdp_control_smoke.py tests/test_branch_sweep_traversal.py tests/test_execution_queue.py -q
```
