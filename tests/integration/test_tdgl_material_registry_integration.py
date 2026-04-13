from __future__ import annotations

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
TDGL_PACKAGE_SRC = ROOT / "packages" / "qdp_tdgl" / "src"
MATERIALS_PACKAGE_SRC = ROOT / "packages" / "qdp_meta_materials" / "src"
if str(QDP_IO_SRC) not in sys.path:
    sys.path.insert(0, str(QDP_IO_SRC))
if str(TDGL_PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(TDGL_PACKAGE_SRC))
if str(MATERIALS_PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(MATERIALS_PACKAGE_SRC))

from qdp_tdgl.config.loaders import load_case_config
from qdp_tdgl.io.metadata import build_provenance


def test_canonical_tdgl_baseline_resolves_materials_through_registry() -> None:
    case_path = ROOT / "configs" / "tdgl" / "phase1_matrix_base.yaml"
    raw_payload = yaml.safe_load(case_path.read_text(encoding="utf-8"))

    assert "materials" in raw_payload
    assert "u" not in raw_payload["physics"]
    assert "sigma_n" not in raw_payload["physics"]
    assert "alpha_background" not in raw_payload["physics"]

    config = load_case_config(case_path)
    assert config.materials is not None
    assert config.materials.adapter_id == "TDGL-MAT-001-BASELINE-V1"
    assert config.materials.material_system_id == "MAT-001"
    assert config.physics.u == 5.79
    assert config.physics.sigma_n == 1.0
    assert config.physics.alpha_background == 1.0

    provenance = build_provenance(config, ROOT, source_config_path=case_path)
    assert provenance["materials"]["adapter_id"] == "TDGL-MAT-001-BASELINE-V1"
    assert provenance["materials"]["material_system_id"] == "MAT-001"
    assert provenance["materials"]["registry_root"] == str(
        ROOT / "packages" / "qdp_meta_materials" / "data" / "seed" / "stable"
    )
