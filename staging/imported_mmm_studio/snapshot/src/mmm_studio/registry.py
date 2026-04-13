from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ValidationError

from .errors import DatasetLoadError
from .io import load_yaml_model
from .models import (
    BenchmarkModelFile,
    CrossDeviceRegistryFile,
    DeviceArchitectureFile,
    EnvironmentModelRegistryFile,
    ExperimentRegistryFile,
    GenomeFile,
    GeometryScalingModelFile,
    InstrumentConstraintFile,
    MaterialSystemRegistryFile,
    MechanismRegistryFile,
    MMMDataset,
    RankingModelFile,
    ScalingModelFile,
    StructureLibraryFile,
    ToleranceModelFile,
    ValidationRulesFile,
)


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    filename: str
    model: type[BaseModel]


DOCUMENT_SPECS: dict[str, DocumentSpec] = {
    "genome_doc": DocumentSpec("mmm_material_genome_database.yaml", GenomeFile),
    "ranking_model_doc": DocumentSpec("mmm_candidate_ranking_model.yaml", RankingModelFile),
    "mechanism_doc": DocumentSpec("mmm_mechanism_registry.yaml", MechanismRegistryFile),
    "structure_doc": DocumentSpec("mmm_structure_library.yaml", StructureLibraryFile),
    "experiment_doc": DocumentSpec("mmm_experiment_registry.yaml", ExperimentRegistryFile),
    "validation_doc": DocumentSpec("mmm_validation_rules.yaml", ValidationRulesFile),
    "benchmark_doc": DocumentSpec("mmm_benchmark_models.yaml", BenchmarkModelFile),
    "scaling_doc": DocumentSpec("mmm_scaling_discrimination_models.yaml", ScalingModelFile),
    "device_doc": DocumentSpec("mmm_device_architecture_registry.yaml", DeviceArchitectureFile),
    "tolerance_doc": DocumentSpec("mmm_tolerance_models.yaml", ToleranceModelFile),
    "geometry_doc": DocumentSpec("mmm_geometry_scaling_models.yaml", GeometryScalingModelFile),
    "material_system_doc": DocumentSpec(
        "mmm_material_system_registry.yaml", MaterialSystemRegistryFile
    ),
    "environment_model_doc": DocumentSpec(
        "mmm_environment_model_registry.yaml", EnvironmentModelRegistryFile
    ),
    "instrument_constraint_doc": DocumentSpec(
        "mmm_instrument_constraints.yaml", InstrumentConstraintFile
    ),
    "cross_device_doc": DocumentSpec("mmm_cross_device_registry.yaml", CrossDeviceRegistryFile),
}


def load_dataset(root: str | Path) -> MMMDataset:
    """Load and validate the typed MMM seed registry."""

    root_path = Path(root).resolve()
    loaded: dict[str, BaseModel] = {}

    for field_name, spec in DOCUMENT_SPECS.items():
        path = root_path / spec.filename
        try:
            loaded[field_name] = load_yaml_model(path, spec.model)
        except FileNotFoundError as exc:
            raise DatasetLoadError(path, "missing required document") from exc
        except ValidationError as exc:
            raise DatasetLoadError(path, exc.errors(include_url=False).__repr__()) from exc

    return MMMDataset(
        root=root_path,
        genome_doc=cast(GenomeFile, loaded["genome_doc"]),
        ranking_model_doc=cast(RankingModelFile, loaded["ranking_model_doc"]),
        mechanism_doc=cast(MechanismRegistryFile, loaded["mechanism_doc"]),
        structure_doc=cast(StructureLibraryFile, loaded["structure_doc"]),
        experiment_doc=cast(ExperimentRegistryFile, loaded["experiment_doc"]),
        validation_doc=cast(ValidationRulesFile, loaded["validation_doc"]),
        benchmark_doc=cast(BenchmarkModelFile, loaded["benchmark_doc"]),
        scaling_doc=cast(ScalingModelFile, loaded["scaling_doc"]),
        device_doc=cast(DeviceArchitectureFile, loaded["device_doc"]),
        tolerance_doc=cast(ToleranceModelFile, loaded["tolerance_doc"]),
        geometry_doc=cast(GeometryScalingModelFile, loaded["geometry_doc"]),
        material_system_doc=cast(MaterialSystemRegistryFile, loaded["material_system_doc"]),
        environment_model_doc=cast(EnvironmentModelRegistryFile, loaded["environment_model_doc"]),
        instrument_constraint_doc=cast(
            InstrumentConstraintFile, loaded["instrument_constraint_doc"]
        ),
        cross_device_doc=cast(CrossDeviceRegistryFile, loaded["cross_device_doc"]),
    )
