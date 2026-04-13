# Staging

This area holds imported donor repositories before reusable code is extracted into canonical package destinations.

Current state:

- `imported_qdp_mm/snapshot/`: working-tree snapshot of the sibling donor repo `QDP MM`
- `imported_mmm_studio/snapshot/`: working-tree snapshot of the sibling donor repo `MMM-Studio`
- `imported_qdp_tdgl/snapshot/`: working-tree snapshot of the sibling donor repo `QDP TDGL`
- `docs/migration/STAGING_IMPORT_HISTORY_COMMANDS.md`: deferred clean-branch history-preserving import commands

The `snapshot/` trees are traceable donor imports for this consolidation run. They are staged source material, not canonical package authority.

Rules:

- staged content preserves traceability
- staged content is not canonical package authority
- when uncertain about deletion, move content here and document the reason
- keep donor-specific docs, scripts, and legacy shells intact here until extraction decisions are recorded
- if a later `history/` tree is added, do not remove the matching `snapshot/` tree until extraction is complete and documented
