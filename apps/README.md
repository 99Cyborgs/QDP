# Apps

Application and service shells live here.

Rule:

- app code may expose CLI, API, or UI shells
- reusable domain logic belongs in `packages/`
- app shells must consume package-layer APIs rather than re-owning schemas, scoring, or runtimes

