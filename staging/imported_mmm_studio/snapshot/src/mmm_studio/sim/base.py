from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import MMMDataset, SimulationJobResult, SweepSpecification
from .typing import SimulationBundle


class SimulationBackend(ABC):
    """Abstract simulation backend for future solver integrations."""

    backend_id: str
    description: str

    @abstractmethod
    def build_bundle(
        self,
        dataset: MMMDataset,
        genome_id: str,
        sweep: SweepSpecification,
    ) -> SimulationBundle:
        """Build a simulation job bundle for a dataset candidate."""

    @abstractmethod
    def run(self, bundle: SimulationBundle) -> SimulationJobResult:
        """Execute or preflight the backend for the provided bundle."""
