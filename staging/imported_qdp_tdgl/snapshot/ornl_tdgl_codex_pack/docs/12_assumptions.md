# Assumptions

These assumptions are intentionally frozen for v1 unless changed by an explicit ADR.

1. The first implementation target is a structured-grid Python codebase.
2. PETSc is the preferred scalable backend; SciPy fallback is acceptable for local debugging.
3. The RF field is prescribed, not solved self-consistently.
4. Inference is summary-statistic based in v1.
5. Synthetic data only; no laboratory data ingestion in v1.
6. The experiment matrix is the authoritative run campaign for the first build.
