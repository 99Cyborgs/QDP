from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator

from ..errors import DatasetLoadError
from ..models import MMMBaseModel

FREQUENCY_SCALE = {
    "hz": 1.0,
    "khz": 1.0e3,
    "mhz": 1.0e6,
    "ghz": 1.0e9,
}


class TouchstoneHeader(MMMBaseModel):
    frequency_unit: str = "ghz"
    parameter: str = "s"
    format: str = "ma"
    reference_resistance_ohm: float = 50.0


class TouchstonePoint(MMMBaseModel):
    frequency_hz: float
    values: list[float]


class TouchstoneDataset(MMMBaseModel):
    path: str
    ports: int
    header: TouchstoneHeader
    points: list[TouchstonePoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_shape(self) -> TouchstoneDataset:
        expected_values = 2 * self.ports * self.ports
        for point in self.points:
            if len(point.values) != expected_values:
                raise ValueError(
                    f"Expected {expected_values} scalar values per point for "
                    f"{self.ports}-port data, got {len(point.values)}."
                )
        return self


def _infer_port_count(path: Path) -> int:
    suffix = path.suffix.lower()
    if len(suffix) < 4 or not suffix.endswith("p") or not suffix[2:-1].isdigit():
        raise DatasetLoadError(path, "expected a Touchstone suffix like .s2p")
    return int(suffix[2:-1])


def _parse_header(line: str) -> TouchstoneHeader:
    tokens = line[1:].strip().split()
    if len(tokens) < 5:
        raise ValueError(
            "Touchstone option line must contain frequency unit, parameter, "
            "format, R, and resistance."
        )
    frequency_unit = tokens[0].lower()
    parameter = tokens[1].lower()
    data_format = tokens[2].lower()
    if tokens[3].lower() != "r":
        raise ValueError("Touchstone option line must include reference resistance marker 'R'.")
    if frequency_unit not in FREQUENCY_SCALE:
        raise ValueError(f"Unsupported Touchstone frequency unit: {tokens[0]}")
    return TouchstoneHeader(
        frequency_unit=frequency_unit,
        parameter=parameter,
        format=data_format,
        reference_resistance_ohm=float(tokens[4]),
    )


def parse_touchstone(path: str | Path) -> TouchstoneDataset:
    """Parse a Touchstone file into a typed dataset."""

    touchstone_path = Path(path)
    ports = _infer_port_count(touchstone_path)
    header: TouchstoneHeader | None = None
    points: list[TouchstonePoint] = []

    for raw_line in touchstone_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("#"):
            header = _parse_header(line)
            continue
        if header is None:
            raise DatasetLoadError(touchstone_path, "missing Touchstone header line")
        numbers = [float(token) for token in line.split()]
        if len(numbers) != 1 + (2 * ports * ports):
            raise DatasetLoadError(
                touchstone_path,
                f"expected {1 + (2 * ports * ports)} numeric columns, got {len(numbers)}",
            )
        scale = FREQUENCY_SCALE[header.frequency_unit]
        points.append(
            TouchstonePoint(
                frequency_hz=numbers[0] * scale,
                values=numbers[1:],
            )
        )

    if header is None:
        raise DatasetLoadError(touchstone_path, "no Touchstone header found")

    return TouchstoneDataset(
        path=str(touchstone_path.resolve()),
        ports=ports,
        header=header,
        points=points,
    )
