from mmm_studio.config import default_seed_root
from mmm_studio.io import load_dataset


def test_load_dataset():
    dataset = load_dataset(default_seed_root())
    assert dataset.genomes
    assert dataset.structures
    assert dataset.mechanisms
    assert dataset.ranking_model.model_id == "RANK-001"
