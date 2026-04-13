from __future__ import annotations

from ..models import (
    CandidateGeometryMetadata,
    MaterialParameterSet,
    MMMDataset,
    SimulationJobDefinition,
    SimulationJobResult,
    SweepSpecification,
)
from .base import SimulationBackend
from .typing import SimulationBundle


class LocalPlaceholderBackend(SimulationBackend):
    """Backend that builds honest local preflight jobs without solver claims."""

    backend_id = "local_placeholder"
    description = "Generates preflight simulation jobs only; no physical solver is executed."

    def build_bundle(
        self,
        dataset: MMMDataset,
        genome_id: str,
        sweep: SweepSpecification,
    ) -> SimulationBundle:
        genome = dataset.genome_index[genome_id]
        structure = dataset.structure_index[genome.parent_structure_id]

        job = SimulationJobDefinition(
            job_id=f"{genome_id}-{self.backend_id}",
            backend=self.backend_id,
            candidate=CandidateGeometryMetadata(
                candidate_id=genome.genome_id,
                parent_structure_id=genome.parent_structure_id,
                topology=structure.geometry.topology,
                parameters=genome.geometric_parameters,
            ),
            materials=MaterialParameterSet(
                material_system=genome.material_system,
                parameters={
                    "notes": genome.notes,
                    "structure_family": structure.structure_family,
                },
            ),
            sweep=sweep,
            requested_outputs=["geometry_preflight", "parameter_manifest"],
            notes=(
                "Local placeholder backend. This bundle is suitable for manifesting "
                "geometry, material, and sweep intent, but it does not execute field solves."
            ),
        )
        return SimulationBundle(job=job)

    def run(self, bundle: SimulationBundle) -> SimulationJobResult:
        job = bundle.job
        bundle.result = SimulationJobResult(
            job_id=job.job_id,
            backend=self.backend_id,
            status="preflight_only",
            summary=(
                "Preflight-only local backend. Geometry and sweep metadata were serialized, "
                "but no electromagnetic or phononic solver was run."
            ),
            extracted_metrics={},
            artifact_paths=[],
        )
        return bundle.result
