"""Compatibility facade for report writers now owned by qdp_io."""

from qdp_io.serialization import write_csv, write_json

__all__ = ["write_csv", "write_json"]
