from __future__ import annotations

from importlib.util import find_spec

from pydantic import Field

from ..models import (
    MMMBaseModel,
    MMMDataset,
    SimulationJobResult,
    SweepSpecification,
)
from .base import SimulationBackend
from .local import LocalPlaceholderBackend
from .typing import SimulationBundle


class MeepGeometryScaffold(MMMBaseModel):
    """Serializable translation artifact for future Meep geometry generation."""

    candidate_id: str
    structure_id: str
    lattice_topology: str
    resolution_pixels_per_um: int = 20
    cell_size_um: tuple[float, float, float] = (50.0, 50.0, 10.0)
    parameter_map: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    material_hints: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class MeepScaffoldBackend(SimulationBackend):
    """Partial Meep integration scaffold with translation but no fake results."""

    backend_id = "meep_scaffold"
    description = "Translates MMM candidates into a Meep-oriented geometry scaffold."

    def build_bundle(
        self,
        dataset: MMMDataset,
        genome_id: str,
        sweep: SweepSpecification,
    ) -> SimulationBundle:
        placeholder = LocalPlaceholderBackend().build_bundle(dataset, genome_id, sweep)
        placeholder.job.backend = self.backend_id
        placeholder.job.notes = (
            "Meep scaffold job. Geometry translation is available, but a production FDTD "
            "execution path is intentionally not implemented yet."
        )
        return placeholder

    def translate_geometry(self, dataset: MMMDataset, genome_id: str) -> MeepGeometryScaffold:
        genome = dataset.genome_index[genome_id]
        structure = dataset.structure_index[genome.parent_structure_id]
        return MeepGeometryScaffold(
            candidate_id=genome.genome_id,
            structure_id=genome.parent_structure_id,
            lattice_topology=genome.lattice_topology,
            parameter_map=genome.geometric_parameters,
            material_hints={
                "material_system": genome.material_system,
                "structure_family": structure.structure_family,
            },
            notes=[
                "Geometry translation scaffold only.",
                "Boundary conditions, dispersive media, and source definitions remain future work.",
                f"Meep import available: {self.is_available()}",
            ],
        )

    def is_available(self) -> bool:
        return find_spec("meep") is not None

    def run(self, bundle: SimulationBundle) -> SimulationJobResult:
        bundle.result = SimulationJobResult(
            job_id=bundle.job.job_id,
            backend=self.backend_id,
            status="unsupported",
            summary=(
                "Meep scaffold only. Translation artifacts are available, but solver execution "
                "is intentionally not implemented in this repository version."
            ),
            extracted_metrics={},
            artifact_paths=[],
        )
        return bundle.result
