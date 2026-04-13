from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
PACKAGE_SRC = ROOT / "packages" / "qdp_meta_materials" / "src"
for path in [QDP_IO_SRC, PACKAGE_SRC]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from qdp_meta_materials.config import default_seed_root
from qdp_meta_materials.adapters.tdgl import resolve_tdgl_material_reference
from qdp_meta_materials.registry import load_dataset
from qdp_meta_materials.scoring import rank_dataset
from qdp_meta_materials.validation import validate_repository


def test_seed_registry_loads():
    dataset = load_dataset(default_seed_root())
    summary = dataset.to_summary()

    assert summary
    assert summary.mechanisms == 11
    assert summary.material_systems == 9
    assert summary.environment_models == 12


def test_seed_repository_validates():
    report = validate_repository(default_seed_root())

    assert report.ok, report.errors
    assert report.stats["material_systems"] == 9


def test_ranking_surface_returns_traceable_results():
    dataset = load_dataset(default_seed_root())
    results = rank_dataset(dataset, profile="broadband")

    assert results
    assert results[0].score_backend == "baseline_surrogate_v1"
    assert results[0].decision_band in {"lead_branch", "primary_screen", "sandbox_only", "reject"}


def test_tdgl_material_adapter_registry_resolves_baseline_identity():
    resolved = resolve_tdgl_material_reference(
        "TDGL-MAT-001-BASELINE-V1",
        material_system_id="MAT-001",
        geometry_family="strip",
    )

    assert resolved.material_system_name == "Al on high-resistivity silicon"
    assert resolved.tdgl_parameters.u == 5.79
    assert resolved.tdgl_parameters.sigma_n == 1.0
