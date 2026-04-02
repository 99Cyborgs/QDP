"""Pydantic configuration models for TDGL-RF cases."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Base model with explicit schema enforcement."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class MetadataConfig(StrictModel):
    case_id: str
    phase: Literal["D", "S", "I", "P", "custom"]
    version: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class MeshConfig(StrictModel):
    nx: int
    ny: int
    lx: float
    ly: float
    periodic_x: bool = False
    periodic_y: bool = False

    @field_validator("nx", "ny")
    @classmethod
    def _validate_shape(cls, value: int) -> int:
        if value < 8:
            raise ValueError("mesh dimensions must be >= 8")
        return value

    @field_validator("lx", "ly")
    @classmethod
    def _validate_length(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("domain lengths must be positive")
        return value


class CircularFeatureConfig(StrictModel):
    x0: float
    y0: float
    radius: float

    @field_validator("radius")
    @classmethod
    def _validate_radius(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("radius must be positive")
        return value


class GeometryConfig(StrictModel):
    family: Literal["strip", "strip_with_moat", "strip_with_hole", "custom_mask"]
    moats: list[CircularFeatureConfig] = Field(default_factory=list)
    holes: list[CircularFeatureConfig] = Field(default_factory=list)
    mask_file: str | None = None


class DefectConfig(StrictModel):
    x0: float
    y0: float
    amplitude: float
    width: float

    @field_validator("width")
    @classmethod
    def _validate_width(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("defect width must be positive")
        return value


class PinningConfig(StrictModel):
    model: Literal["none", "gaussian_defects", "random_field"]
    seed: int | None = None
    mu: float = 0.0
    sigma: float = 0.0
    lcorr: float = 0.0
    defect_count: int = 0
    defects: list[DefectConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_consistency(self) -> "PinningConfig":
        if self.model == "gaussian_defects" and self.defect_count != len(self.defects):
            raise ValueError("defect_count must match the number of explicit defects")
        return self


class PhysicsConfig(StrictModel):
    u: float
    sigma_n: float
    alpha_background: float
    pinning: PinningConfig
    initial_condition: Literal["meissner", "seeded_vortices", "restart"]
    restart_file: str | None = None

    @field_validator("u")
    @classmethod
    def _validate_u(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("u must be positive")
        return value

    @field_validator("sigma_n")
    @classmethod
    def _validate_sigma(cls, value: float) -> float:
        if value < 0:
            raise ValueError("sigma_n must be non-negative")
        return value


class ForcingConfig(StrictModel):
    b_dc: float
    a_rf: float
    omega: float
    phase: float
    rf_profile: Literal["uniform_x", "uniform_y", "edge_crowding", "from_file"]
    rf_profile_file: str | None = None

    @field_validator("a_rf", "omega")
    @classmethod
    def _validate_nonnegative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("forcing amplitudes and frequencies must be non-negative")
        return value


class NoiseConfig(StrictModel):
    enabled: bool
    gamma_psi: float
    master_seed: int

    @field_validator("gamma_psi")
    @classmethod
    def _validate_gamma(cls, value: float) -> float:
        if value < 0:
            raise ValueError("gamma_psi must be non-negative")
        return value


class TimeConfig(StrictModel):
    dt: float
    n_steps: int
    obs_stride: int
    field_stride: int
    checkpoint_stride: int

    @field_validator("dt")
    @classmethod
    def _validate_dt(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("dt must be positive")
        return value

    @field_validator("n_steps", "obs_stride", "field_stride", "checkpoint_stride")
    @classmethod
    def _validate_positive_int(cls, value: int) -> int:
        if value < 1:
            raise ValueError("time counters and strides must be >= 1")
        return value


class SolverConfig(StrictModel):
    backend: Literal["scipy", "petsc"]
    scheme: Literal["imex_linearized"]
    psi_linear_solver: str
    phi_linear_solver: str
    rtol: float
    atol: float
    max_it: int = 1000

    @field_validator("rtol", "atol")
    @classmethod
    def _validate_tol(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("solver tolerances must be positive")
        return value

    @field_validator("max_it")
    @classmethod
    def _validate_max_it(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_it must be >= 1")
        return value


class ObservablesConfig(StrictModel):
    track_vortices: bool = True
    compute_frequency_shift_proxy: bool = True
    compute_qinv_proxy: bool = True
    weight_profile_f: Literal["uniform", "edge_crowding", "from_file"] = "uniform"
    weight_profile_q: Literal["uniform", "edge_crowding", "from_file"] = "uniform"
    c_f: float = 1.0
    c_q: float = 1.0
    qinv_bg: float = 0.0


class InferenceConfig(StrictModel):
    enabled: bool = False
    mode: Literal["none", "synthetic_map", "synthetic_laplace", "synthetic_mcmc"] = "none"
    infer_parameters: list[str] = Field(default_factory=list)
    dataset_path: str | None = None
    summary_statistics: list[str] = Field(default_factory=list)


class OutputConfig(StrictModel):
    root_dir: str
    write_fields: bool
    write_observables: bool
    compression: Literal["none", "gzip"]


class CampaignConfig(StrictModel):
    ensemble_size: int = 1
    matrix_row_id: str | None = None
    promotion_rule: str | None = None

    @field_validator("ensemble_size")
    @classmethod
    def _validate_ensemble_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("ensemble_size must be >= 1")
        return value


class TDGLRFCaseConfig(StrictModel):
    base_config: str | None = None
    metadata: MetadataConfig
    mesh: MeshConfig
    geometry: GeometryConfig
    physics: PhysicsConfig
    forcing: ForcingConfig
    noise: NoiseConfig
    time: TimeConfig
    solver: SolverConfig
    output: OutputConfig
    observables: ObservablesConfig = Field(default_factory=ObservablesConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    campaign: CampaignConfig = Field(default_factory=CampaignConfig)

