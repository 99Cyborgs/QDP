from __future__ import annotations

from typing import Any, Mapping


RETAINED_RUNTIME_REF_ID = "RETAINED_V10_1_OPERATIVE_BODY"
RETAINED_GOVERNANCE_REGISTRY_REF_ID = "RETAINED_FEDERATED_GOVERNANCE_REGISTRY_OBJECT"


def find_reference_entry(manifest: Mapping[str, Any], ref_id: str) -> dict[str, Any]:
    """Return one reference entry by ref_id or an empty object when absent."""

    for entry in manifest.get("reference_entries", []):
        if isinstance(entry, dict) and entry.get("ref_id") == ref_id:
            return dict(entry)
    return {}


def reference_is_reconstructed_surrogate(entry: Mapping[str, Any]) -> bool:
    """Return True when one reference entry is a reconstructed surrogate."""

    return str(entry.get("provenance", "") or "") == "reconstructed_surrogate"


def reference_has_authoritative_binding(
    ref_id: str,
    manifest: Mapping[str, Any],
    governance_registry: Mapping[str, Any] | None = None,
) -> bool:
    """Return True when a manifest entry or registry binding marks a reference authoritative."""

    manifest_entry = find_reference_entry(manifest, ref_id)
    if manifest_entry.get("authoritative_binding_status") == "BOUND":
        return True
    registry = governance_registry or {}
    bindings = registry.get("authoritative_reference_bindings", {})
    binding = bindings.get(ref_id, {}) if isinstance(bindings, Mapping) else {}
    return isinstance(binding, Mapping) and binding.get("status") == "BOUND"


def retained_reference_provenance_mode(manifest: Mapping[str, Any]) -> str:
    """Collapse retained reference provenance to the QDP run-ledger mode contract."""

    retained_runtime = find_reference_entry(manifest, RETAINED_RUNTIME_REF_ID)
    retained_registry = find_reference_entry(manifest, RETAINED_GOVERNANCE_REGISTRY_REF_ID)
    provenances = {
        str(retained_runtime.get("provenance", "") or ""),
        str(retained_registry.get("provenance", "") or ""),
    }
    return "surrogate" if "reconstructed_surrogate" in provenances else "original"
