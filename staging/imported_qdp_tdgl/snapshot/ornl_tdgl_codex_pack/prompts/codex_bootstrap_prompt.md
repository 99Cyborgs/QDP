You are building v1 of the ORNL TDGL-RF experiment platform.

Read these files in order:
1. README.md
2. manifest.yaml
3. docs/01_program_charter.md
4. docs/02_physics_spec.md
5. docs/03_numerics_spec.md
6. docs/04_software_architecture.md
7. docs/05_verification_validation.md
8. docs/06_bayesian_inference_spec.md
9. docs/07_experiment_matrix_guide.md
10. docs/10_codex_build_instructions.md

Hard instructions:
- Build only v1.
- Use Python 3.11 with the dependencies named in README.md.
- Keep the discretization exactly as specified.
- Implement deterministic forward solves first.
- Do not add stochastic code until Gate G1 passes.
- Do not add inference code until Gate G2 passes.
- Do not change config semantics.
- Do not invent new physics.
- If something is ambiguous, choose the narrower interpretation and document it.

Expected delivery order:
1. repo scaffold and config system
2. deterministic solver core
3. deterministic V&V and figures 1-2
4. stochastic extension and figure 3
5. inverse workflow and figure 4
6. performance instrumentation and scaling plots

Required outputs:
- code repository
- tests
- benchmark outputs
- matrix runner
- figures
- short phase reports
- updated acceptance checklist

Do not start by writing proposal prose. Start by building the deterministic core.
