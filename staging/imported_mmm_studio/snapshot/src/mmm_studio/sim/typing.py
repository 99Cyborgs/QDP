from __future__ import annotations

from dataclasses import dataclass

from ..models import SimulationJobDefinition, SimulationJobResult


@dataclass(slots=True)
class SimulationBundle:
    """Simple transport object for backend preflight state."""

    job: SimulationJobDefinition
    result: SimulationJobResult | None = None
