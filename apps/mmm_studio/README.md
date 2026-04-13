# mmm_studio

Active MMM Studio app shell for the QDP monorepo.

This app owns only:

- CLI shell
- API shell
- app-specific request and response wiring

This app does not own:

- materials schemas
- registry loading
- registry validation
- scoring and ranking
- planning or sweep logic
- run or provenance logic

Those reusable surfaces now live in `packages/qdp_meta_materials/` and `packages/qdp_io/` and must remain authoritative there.
