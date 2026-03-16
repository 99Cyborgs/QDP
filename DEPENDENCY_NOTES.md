# Dependency Notes

## Internal dependencies

- `qdp.py` and `qdp_validation.py` depend on the repo-level directory layout
- module execution depends on `config/`, `modules/`, and `tools/`
- local review depends on generated outputs under `artifacts/`

## Portfolio dependency posture

- ALL-MIND depends on QDP only as a governed downstream program, not as an imported runtime package
- promotion should be driven by a narrow interface contract, not by loading QDP internals into the core repo
