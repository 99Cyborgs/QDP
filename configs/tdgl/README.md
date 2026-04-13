# tdgl configs

Destination for source TDGL configuration bundles that belong to the canonical `qdp_tdgl` runtime.

Current status: active canonical TDGL config and schema surface.

Phase 7 note:

- committed TDGL baselines now resolve `physics.u`, `physics.sigma_n`, and `physics.alpha_background` through the canonical `qdp_meta_materials` TDGL adapter registry via a `materials` block
- expanded configs remain the runtime snapshot, but the material identity now originates in `packages/qdp_meta_materials/`
