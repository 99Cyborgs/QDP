from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from ..errors import OptionalDependencyUnavailable
from .touchstone import parse_touchstone


class ScikitRFAdapter:
    """Thin optional adapter around scikit-rf."""

    package_name = "skrf"

    @classmethod
    def is_available(cls) -> bool:
        try:
            import_module(cls.package_name)
        except ImportError:
            return False
        return True

    @classmethod
    def load_network(cls, path: str | Path) -> Any:
        if not cls.is_available():
            raise OptionalDependencyUnavailable(
                "scikit-rf is not installed. Install the rf extra to enable this adapter."
            )
        skrf = import_module(cls.package_name)
        return skrf.Network(str(path))

    @classmethod
    def load_or_parse(cls, path: str | Path) -> Any:
        if cls.is_available():
            return cls.load_network(path)
        return parse_touchstone(path)
