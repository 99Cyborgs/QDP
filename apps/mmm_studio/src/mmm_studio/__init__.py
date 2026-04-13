"""MMM Studio app shell for the QDP monorepo."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


for _distribution_name in ("qdp-mmm-studio", "mmm-studio"):
    try:
        __version__ = version(_distribution_name)
        break
    except PackageNotFoundError:  # pragma: no cover
        continue
else:  # pragma: no cover
    __version__ = "0.1.0"

__all__ = ["__version__"]
