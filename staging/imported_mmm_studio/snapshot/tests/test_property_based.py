from hypothesis import given
from hypothesis import strategies as st

from mmm_studio.models import Genome
from mmm_studio.scoring import fabrication_robustness_score, null_separation_score


def _make_genome(fabrication_complexity_score: int, null_risk_score: int) -> Genome:
    return Genome(
        genome_id="GEN-PROP",
        parent_structure_id="STR-EM-CPW-EBG-RING",
        lattice_topology="property-test",
        material_system="Al on Si",
        geometric_parameters={},
        predicted_electromagnetic_properties={},
        predicted_phononic_band_structure={},
        fabrication_complexity_score=fabrication_complexity_score,
        null_risk_score=null_risk_score,
        screening_status="screening",
        notes="",
    )


@given(
    fabrication_complexity_score=st.integers(min_value=1, max_value=10),
    null_risk_score=st.integers(min_value=1, max_value=10),
)
def test_score_invariants_are_bounded(
    fabrication_complexity_score: int,
    null_risk_score: int,
):
    genome = _make_genome(fabrication_complexity_score, null_risk_score)

    assert 0.0 <= fabrication_robustness_score(genome) <= 1.0
    assert 0.0 <= null_separation_score(genome) <= 1.0
