"""Compatibility facade for serialization helpers now owned by qdp_io."""

from qdp_io.serialization import load_yaml, load_yaml_model, write_json, write_text, write_yaml

__all__ = ["load_yaml", "load_yaml_model", "write_json", "write_text", "write_yaml"]
