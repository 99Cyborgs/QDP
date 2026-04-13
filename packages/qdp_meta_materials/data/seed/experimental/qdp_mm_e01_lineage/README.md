# QDP MM E01 Lineage

This directory preserves the semantic lineage imported from the `QDP MM` donor while the canonical implementation lives in `qdp_meta_materials`.

Lineage facts carried forward from `staging/imported_qdp_mm/snapshot/qdp/branches/e01_mm_flux_history_hysteresis/`:

- conservative intake posture starts at `METASTABLE_C_STATE`
- `VORTEX` remains a conditional promoted interpretation, not an intake default
- the geometry gate requires same-chip matched geometry with consistent ordering across cooldowns
- run provenance distinguishes pre-run planning from bound as-run evidence:
  - `PRE_RUN_MINIMUM_ACQUISITION`
  - `PRE_RUN_MINIMUM_READY`
  - `AS_RUN_BINDING`
  - `AS_RUN_PARTIAL`
  - `AS_RUN_BOUND`

Current status:

- these semantics are preserved here as migration and lineage guidance
- branch-specific execution queue mechanics and analysis packs remain staged for later review or future `labs/materials/` extraction
