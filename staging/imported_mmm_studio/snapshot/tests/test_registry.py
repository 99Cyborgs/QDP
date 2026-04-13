from mmm_studio.config import default_seed_root
from mmm_studio.io import load_dataset


def test_typed_registry_summary():
    dataset = load_dataset(default_seed_root())
    summary = dataset.to_summary()

    assert summary.mechanisms == 11
    assert summary.material_systems == 9
    assert summary.environment_models == 12
    assert dataset.mechanism_index["MECH-EM-001"].priority_tier == "A"
    assert dataset.structure_index["STR-EM-LID-HIS"].structure_family == "high_impedance_surface"
