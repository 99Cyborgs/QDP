"""TDGL-facing material adapter registry and resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from pathlib import Path

from pydantic import Field, ValidationError

from ...config import default_seed_root
from ...errors import DatasetLoadError
from ...io import load_yaml_model
from ...models import ArtifactDocument, MMMBaseModel
from ...registry import load_dataset

ADAPTER_REGISTRY_FILENAME = "mmm_tdgl_material_adapter_registry.yaml"


class TDGLResolvedParameterSet(MMMBaseModel):
    u: float
    sigma_n: float
    alpha_background: float


class TDGLMaterialAdapterSpec(MMMBaseModel):
    adapter_id: str
    adapter_version: str = "1.0"
    material_system_id: str
    runtime_family: str
    supported_geometry_families: list[str] = Field(default_factory=list)
    tdgl_parameters: TDGLResolvedParameterSet
    notes: str = ""


class TDGLMaterialAdapterRegistryFile(ArtifactDocument):
    adapters: list[TDGLMaterialAdapterSpec]


@dataclass(frozen=True, slots=True)
class ResolvedTDGLMaterialReference:
    registry_root: Path
    artifact_id: str
    source_artifacts: list[str]
    adapter_id: str
    adapter_version: str
    material_system_id: str
    material_system_name: str
    genome_id: str | None
    runtime_family: str
    supported_geometry_families: list[str]
    tdgl_parameters: TDGLResolvedParameterSet
    notes: str


def _resolve_seed_root(registry_root: str | Path | None) -> Path:
    if registry_root is None:
        return default_seed_root()
    return Path(registry_root).expanduser().resolve()


def adapter_registry_path(registry_root: str | Path | None = None) -> Path:
    """Return the canonical TDGL adapter-registry path inside the seed dataset."""

    seed_root = _resolve_seed_root(registry_root)
    candidates = [
        seed_root / ADAPTER_REGISTRY_FILENAME,
        seed_root / "registry" / ADAPTER_REGISTRY_FILENAME,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        f"could not locate TDGL adapter registry under {seed_root}; checked {[str(path) for path in candidates]}"
    )


def load_tdgl_adapter_registry(
    registry_root: str | Path | None = None,
) -> TDGLMaterialAdapterRegistryFile:
    """Load the canonical TDGL adapter registry from qdp_meta_materials seed data."""

    path = adapter_registry_path(registry_root)
    try:
        return load_yaml_model(path, TDGLMaterialAdapterRegistryFile)
    except ValidationError as exc:
        raise DatasetLoadError(path, exc.errors(include_url=False).__repr__()) from exc


def resolve_tdgl_material_reference(
    adapter_id: str,
    *,
    registry_root: str | Path | None = None,
    material_system_id: str | None = None,
    genome_id: str | None = None,
    geometry_family: str | None = None,
) -> ResolvedTDGLMaterialReference:
    """Resolve one TDGL material reference against the canonical materials seed registry."""

    seed_root = _resolve_seed_root(registry_root)
    dataset = load_dataset(seed_root)
    adapter_registry = load_tdgl_adapter_registry(seed_root)
    adapter_map = {adapter.adapter_id: adapter for adapter in adapter_registry.adapters}
    if adapter_id not in adapter_map:
        raise DatasetLoadError(
            adapter_registry_path(seed_root),
            f"unknown TDGL material adapter_id '{adapter_id}'",
        )
    adapter = adapter_map[adapter_id]
    if material_system_id is not None and material_system_id != adapter.material_system_id:
        raise DatasetLoadError(
            adapter_registry_path(seed_root),
            "TDGL material reference mismatch: "
            f"adapter '{adapter_id}' resolves to material_system_id '{adapter.material_system_id}', "
            f"not '{material_system_id}'",
        )

    material_by_id = {
        material.material_system_id: material for material in dataset.material_systems
    }
    if adapter.material_system_id not in material_by_id:
        raise DatasetLoadError(
            adapter_registry_path(seed_root),
            f"TDGL adapter '{adapter_id}' references unknown material_system_id '{adapter.material_system_id}'",
        )
    material = material_by_id[adapter.material_system_id]
    if geometry_family is not None and adapter.supported_geometry_families:
        if geometry_family not in adapter.supported_geometry_families:
            raise DatasetLoadError(
                adapter_registry_path(seed_root),
                "TDGL adapter geometry mismatch: "
                f"adapter '{adapter_id}' does not support geometry family '{geometry_family}'",
            )

    source_artifacts = [
        adapter_registry.artifact.artifact_id,
        dataset.material_system_doc.artifact.artifact_id,
    ]
    if genome_id is not None:
        genome = dataset.genome_index.get(genome_id)
        if genome is None:
            raise DatasetLoadError(
                adapter_registry_path(seed_root),
                f"TDGL material reference cites unknown genome_id '{genome_id}'",
            )
        if genome.material_system != material.name:
            raise DatasetLoadError(
                adapter_registry_path(seed_root),
                "TDGL material reference mismatch: "
                f"genome '{genome_id}' uses material system '{genome.material_system}', "
                f"not '{material.name}'",
            )
        source_artifacts.append(dataset.genome_doc.artifact.artifact_id)

    return ResolvedTDGLMaterialReference(
        registry_root=seed_root,
        artifact_id=adapter_registry.artifact.artifact_id,
        source_artifacts=source_artifacts,
        adapter_id=adapter.adapter_id,
        adapter_version=adapter.adapter_version,
        material_system_id=material.material_system_id,
        material_system_name=material.name,
        genome_id=genome_id,
        runtime_family=adapter.runtime_family,
        supported_geometry_families=list(adapter.supported_geometry_families),
        tdgl_parameters=adapter.tdgl_parameters,
        notes=adapter.notes,
    )


def tdgl_parameters_match(
    *,
    observed_u: float,
    observed_sigma_n: float,
    observed_alpha_background: float,
    resolved: ResolvedTDGLMaterialReference,
) -> bool:
    """Return True when explicit TDGL parameters match the resolved adapter values."""

    return (
        isclose(float(observed_u), float(resolved.tdgl_parameters.u), rel_tol=1.0e-12, abs_tol=1.0e-12)
        and isclose(
            float(observed_sigma_n),
            float(resolved.tdgl_parameters.sigma_n),
            rel_tol=1.0e-12,
            abs_tol=1.0e-12,
        )
        and isclose(
            float(observed_alpha_background),
            float(resolved.tdgl_parameters.alpha_background),
            rel_tol=1.0e-12,
            abs_tol=1.0e-12,
        )
    )


__all__ = [
    "ADAPTER_REGISTRY_FILENAME",
    "ResolvedTDGLMaterialReference",
    "TDGLMaterialAdapterRegistryFile",
    "TDGLMaterialAdapterSpec",
    "TDGLResolvedParameterSet",
    "adapter_registry_path",
    "load_tdgl_adapter_registry",
    "resolve_tdgl_material_reference",
    "tdgl_parameters_match",
]
