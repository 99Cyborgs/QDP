from __future__ import annotations

from importlib import metadata
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Iterable


def package_version(name: str) -> str | None:
    """Return an installed package version or None when unavailable."""

    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def git_revision(repo_root: str | Path) -> str | None:
    """Return the current git revision for a repo root when available."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def build_runtime_snapshot(
    repo_root: str | Path,
    *,
    package_names: Iterable[str] = (),
) -> dict[str, Any]:
    """Collect generic runtime metadata for provenance payloads."""

    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "git_revision": git_revision(repo_root),
        "packages": {name: package_version(name) for name in package_names},
    }
