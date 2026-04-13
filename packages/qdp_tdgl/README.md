# qdp_tdgl

Canonical QDP TDGL runtime package.

Active ownership:

- solver entrypoints
- TDGL workflows
- TDGL-specific execution logic
- TDGL runtime validation harnesses
- TDGL-only replay and runtime provenance details
- TDGL config-time consumption of canonical materials adapters from `qdp_meta_materials`
- consumption of shared serialization and generic runtime metadata from `qdp_io`

Package layout:

- `src/qdp_tdgl/`: canonical runtime, solver, workflow, and CLI implementation
- `../../configs/tdgl/`: canonical TDGL case configs and JSON schemas
- `../../configs/validation/tdgl/`: committed validation manifests and thresholds

Consolidation notes:

- this package is the extracted authority from the staged `QDP TDGL` donor
- donor-era root control shells and duplicate wrappers remain quarantined under `staging/imported_qdp_tdgl/`
- the compatibility CLI alias `tdgl-rf` is preserved temporarily, but `qdp-tdgl` is the canonical command name inside QDP
- TDGL cases can now carry a `materials` block that resolves runtime parameters through `packages/qdp_meta_materials/` instead of maintaining a second copied material-parameter authority in the case file
- shared JSON and CSV report writing plus generic runtime metadata now come from `packages/qdp_io/`; `src/qdp_tdgl/io/reports.py` is a compatibility facade only

Validation in this phase should target the package directly, for example:

```powershell
$env:PYTHONPATH = "packages/qdp_io/src;packages/qdp_tdgl/src;packages/qdp_meta_materials/src"
python -m pytest tests/unit/test_qdp_tdgl_config.py tests/unit/test_qdp_tdgl_cli.py tests/unit/test_qdp_tdgl_run_case_outputs.py -q
```
