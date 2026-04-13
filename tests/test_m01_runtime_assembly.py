from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_runner_module():
    runner_path = ROOT / "modules" / "m01_runtime_assembly" / "runner.py"
    spec = importlib.util.spec_from_file_location("qdp_m01_runner_test", runner_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_surrogate_retained_source_keeps_m01_in_recovery_lane() -> None:
    runner = load_runner_module()
    state = runner.derive_runtime_state(
        {
            "reference_entries": [
                {
                    "ref_id": "RETAINED_V10_1_OPERATIVE_BODY",
                    "provenance": "reconstructed_surrogate",
                }
            ]
        },
        ROOT / "runtime" / "current" / "runtime_prompt.md",
        ROOT / "runtime" / "retained" / "operative_body_v10_1.md",
        ROOT / "runtime" / "missing" / "operative_body_v10_1_surrogate.md",
        runtime_prompt_exists_override=True,
        retained_runtime_exists_override=True,
        surrogate_runtime_exists_override=False,
    )

    assert state["retained_runtime_source_authoritative"] is False
    assert state["lane"] == "RECOVERY_LANE"
    assert state["derived_status"] == "RECOVERY_INTERIM"


def test_original_retained_source_allows_m01_authoritative_lane() -> None:
    runner = load_runner_module()
    state = runner.derive_runtime_state(
        {
            "reference_entries": [
                {
                    "ref_id": "RETAINED_V10_1_OPERATIVE_BODY",
                    "provenance": "original",
                }
            ]
        },
        ROOT / "runtime" / "current" / "runtime_prompt.md",
        ROOT / "runtime" / "retained" / "operative_body_v10_1.md",
        ROOT / "runtime" / "missing" / "operative_body_v10_1_surrogate.md",
        runtime_prompt_exists_override=True,
        retained_runtime_exists_override=True,
        surrogate_runtime_exists_override=False,
    )

    assert state["retained_runtime_source_authoritative"] is True
    assert state["lane"] == "AUTHORITATIVE_LANE"
    assert state["derived_status"] == "AUTHORITATIVE_CLOSURE"
