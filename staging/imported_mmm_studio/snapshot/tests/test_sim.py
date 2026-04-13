from mmm_studio.config import default_seed_root
from mmm_studio.io import load_dataset
from mmm_studio.models import SweepSpecification
from mmm_studio.sim import LocalPlaceholderBackend, MeepScaffoldBackend


def test_local_placeholder_backend_returns_preflight_result():
    dataset = load_dataset(default_seed_root())
    backend = LocalPlaceholderBackend()
    bundle = backend.build_bundle(
        dataset,
        "GEN-001",
        SweepSpecification(
            sweep_id="demo",
            domain="electromagnetic",
            target_frequency_window_ghz=(4.0, 6.0),
        ),
    )
    result = backend.run(bundle)

    assert bundle.job.backend == "local_placeholder"
    assert result.status == "preflight_only"
    assert result.extracted_metrics == {}


def test_meep_scaffold_translation():
    dataset = load_dataset(default_seed_root())
    backend = MeepScaffoldBackend()
    scaffold = backend.translate_geometry(dataset, "GEN-003")

    assert scaffold.candidate_id == "GEN-003"
    assert scaffold.structure_id == "STR-EM-LID-HIS"
    assert "Geometry translation scaffold only." in scaffold.notes
