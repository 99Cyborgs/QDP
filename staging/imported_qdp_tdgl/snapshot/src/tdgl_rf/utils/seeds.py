"""Deterministic seed derivation utilities."""

from __future__ import annotations

import hashlib


def derive_seed(master_seed: int, *components: int | str) -> int:
    """Derive a deterministic integer seed from a master seed and labels."""

    digest = hashlib.sha256(f"{master_seed}:{':'.join(map(str, components))}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little", signed=False)

