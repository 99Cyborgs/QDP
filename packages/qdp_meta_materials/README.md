# qdp_meta_materials

Canonical destination for the single authoritative materials and metamaterials package.

Owned surfaces:

- material schemas
- stack definitions
- registry loading
- registry validation
- provenance metadata relevant to the materials system
- scoring and ranking
- planning, sweep, and tranche logic
- TDGL-facing material adapters
- stable and experimental seed data

Primary donor: `MMM-Studio`

Semantic lineage donor: `QDP MM`

Current extraction status:

- extracted reusable core from `staging/imported_mmm_studio/snapshot/src/mmm_studio/`
- kept the MMM-Studio app shell out of this package:
  - `api.py`
  - `api_models.py`
  - `cli.py`
  - `__main__.py`
- staged stable seed data from `staging/imported_mmm_studio/snapshot/data/mmm_seed/` into `data/seed/stable/`
- preserved QDP MM lineage notes under `data/seed/experimental/qdp_mm_e01_lineage/`

Current internal layout:

- `src/qdp_meta_materials/models.py`: typed donor model surface
- `src/qdp_meta_materials/registry/`: canonical typed registry loader surface
- `src/qdp_meta_materials/io.py`: compatibility facade over `packages/qdp_io/serialization.py`; dataset loading now belongs only to `registry/`
- `src/qdp_meta_materials/validation/`: canonical materials registry validation surface
- `src/qdp_meta_materials/scoring/`: canonical scoring and ranking surface
- `src/qdp_meta_materials/sweeps/`: donor tranche and sweep implementation retained during the transition
- `src/qdp_meta_materials/planning/`: planning facade over the sweep subsystem
- `src/qdp_meta_materials/provenance/`: provenance and run-manifest facade
- `src/qdp_meta_materials/adapters/`: RF, simulation, and TDGL adapter entrypoints
- `data/seed/stable/`: canonical stable seed dataset
- `data/seed/experimental/`: lineage and experimental seed staging

Active TDGL adapter surface:

- `src/qdp_meta_materials/adapters/tdgl/`: canonical TDGL material-reference resolver
- `data/seed/stable/mmm_tdgl_material_adapter_registry.yaml`: stable TDGL adapter registry keyed by `adapter_id`

Important constraints:

- `apps/mmm_studio/` will own the future app shell. This package must remain reusable library code.
- QDP MM semantics are preserved as lineage notes and later-review inputs, not as a second implementation authority.
- `sweeps/`, `rf/`, and `sim/` are transitional donor carry-forwards and should be refactored into clearer subarea-native modules in later phases rather than duplicated elsewhere.

Validation in this phase should target the package directly, for example:

```powershell
$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_meta_materials/src"
pytest tests/unit/test_qdp_meta_materials_smoke.py -q
```
