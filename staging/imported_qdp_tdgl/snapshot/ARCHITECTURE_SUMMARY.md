# Architecture Summary

QDP combines:

- domain modules under `modules/`,
- runtime helpers under `runtime/`,
- configuration and spec inputs under `config/` and `specs/`,
- validation and orchestration entrypoints at the repo root,
- generated outputs under `artifacts/`.

The repo is operational enough to matter, but it still carries refactor debt. The right near-term posture is to keep it governed as an incubate repo while lowering audit cost and making the interface to ALL-MIND explicit.
