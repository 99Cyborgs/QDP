# QDP MM

Canonical Git source tree for the E01 metastable-memory branch pack.

## Layout

- `qdp/branches/e01_mm_flux_history_hysteresis/` is the authoritative branch pack.
- `qdp/branches/e01_mm_flux_history_hysteresis/manifest.json` inventories the published artifacts.
- `qdp/branches/e01_mm_flux_history_hysteresis/README.md` is the branch-level overview and usage guide.

## Validation

Run the published test surface from the repository root:

```powershell
python -m unittest discover -s qdp/branches/e01_mm_flux_history_hysteresis -p "test_*.py"
```
