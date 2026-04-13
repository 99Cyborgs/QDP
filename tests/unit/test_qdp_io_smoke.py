from __future__ import annotations

from pathlib import Path
import sys
from datetime import datetime

from pydantic import BaseModel


ROOT = Path(__file__).resolve().parents[2]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
if str(QDP_IO_SRC) not in sys.path:
    sys.path.insert(0, str(QDP_IO_SRC))

from qdp_io.artifacts import (
    artifact_report_header,
    candidate_result_summary_report,
    dump_json,
    module_report_header,
    module_selftest_report_payload,
    sha256_file,
    stable_hash,
    utc_now,
    visible_source_result_summary_report,
)
from qdp_io.module_registry import build_module_registry_json, build_module_registry_md
from qdp_io.reference_manifest import (
    RETAINED_GOVERNANCE_REGISTRY_REF_ID,
    RETAINED_RUNTIME_REF_ID,
    find_reference_entry,
    reference_has_authoritative_binding,
    reference_is_reconstructed_surrogate,
    retained_reference_provenance_mode,
)
from qdp_io.runtime_metadata import build_runtime_snapshot, package_version
from qdp_io.serialization import load_json, load_json_object, load_yaml_model, write_csv, write_json, write_yaml


class ExampleModel(BaseModel):
    name: str
    count: int


def test_round_trip_json_and_csv(tmp_path: Path) -> None:
    json_path = write_json(tmp_path / "payload.json", {"alpha": 1, "beta": 2})
    csv_path = write_csv(tmp_path / "payload.csv", [{"alpha": 1, "beta": 2}])

    assert load_json(json_path) == {"alpha": 1, "beta": 2}
    assert csv_path.read_text(encoding="utf-8").startswith("alpha,beta")


def test_load_json_object_requires_mapping_root(tmp_path: Path) -> None:
    object_path = write_json(tmp_path / "payload.json", {"alpha": 1})
    list_path = write_json(tmp_path / "payload-list.json", ["alpha"])

    assert load_json_object(object_path) == {"alpha": 1}
    try:
        load_json_object(list_path)
    except TypeError as exc:
        assert "Expected a mapping" in str(exc)
    else:
        raise AssertionError("load_json_object should reject non-object JSON roots")


def test_load_yaml_model_validates_typed_payload(tmp_path: Path) -> None:
    yaml_path = write_yaml(tmp_path / "payload.yaml", {"name": "demo", "count": 3})
    payload = load_yaml_model(yaml_path, ExampleModel)

    assert payload.name == "demo"
    assert payload.count == 3


def test_runtime_snapshot_collects_generic_metadata() -> None:
    snapshot = build_runtime_snapshot(ROOT, package_names=["pydantic", "__not_a_real_package__"])

    assert snapshot["hostname"]
    assert snapshot["platform"]
    assert snapshot["python_version"]
    assert snapshot["packages"]["pydantic"] == package_version("pydantic")
    assert snapshot["packages"]["__not_a_real_package__"] is None


def test_artifact_dump_and_hash_helpers_are_stable(tmp_path: Path) -> None:
    artifact_path = dump_json(tmp_path / "artifact.json", {"beta": 2, "alpha": 1})

    assert load_json(artifact_path) == {"beta": 2, "alpha": 1}
    assert stable_hash({"alpha": 1, "beta": 2}) == stable_hash({"beta": 2, "alpha": 1})
    assert sha256_file(artifact_path)


def test_utc_now_is_timezone_aware_utc_timestamp() -> None:
    timestamp = utc_now()
    parsed = datetime.fromisoformat(timestamp)

    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_shared_report_header_helpers_emit_expected_fields() -> None:
    artifact_header = artifact_report_header("QDP_SAMPLE_REPORT")
    module_header = module_report_header("QDP_SAMPLE_MODULE_REPORT", "M99")

    assert list(artifact_header.keys()) == ["artifact_id", "timestamp_utc"]
    assert artifact_header["artifact_id"] == "QDP_SAMPLE_REPORT"
    assert datetime.fromisoformat(artifact_header["timestamp_utc"]).utcoffset().total_seconds() == 0

    assert list(module_header.keys()) == ["artifact_id", "module_id", "timestamp_utc"]
    assert module_header["artifact_id"] == "QDP_SAMPLE_MODULE_REPORT"
    assert module_header["module_id"] == "M99"
    assert datetime.fromisoformat(module_header["timestamp_utc"]).utcoffset().total_seconds() == 0


def test_module_selftest_report_payload_emits_expected_shape() -> None:
    payload = module_selftest_report_payload(
        "QDP_SAMPLE_SELFTEST_REPORT",
        "M99",
        [{"case_id": "a", "passed": True}, {"case_id": "b", "passed": False}],
        visible_source_only=True,
        metadata={"contract_checks": {"ok": True}},
        schema_valid_all=False,
    )

    assert list(payload.keys()) == [
        "artifact_id",
        "module_id",
        "timestamp_utc",
        "visible_source_only",
        "contract_checks",
        "cases_total",
        "cases_passed",
        "all_passed",
        "schema_valid_all",
        "cases",
    ]
    assert payload["cases_total"] == 2
    assert payload["cases_passed"] == 1
    assert payload["all_passed"] is False
    assert payload["schema_valid_all"] is False


def test_candidate_result_summary_report_emits_expected_shape() -> None:
    payload = candidate_result_summary_report(
        "QDP_SAMPLE_RESULT_REPORT",
        "M99",
        "candidate-001",
        {"status": "READY"},
        metadata={"visible_source_only": True},
    )

    assert list(payload.keys()) == [
        "artifact_id",
        "module_id",
        "timestamp_utc",
        "candidate_id",
        "visible_source_only",
        "result_summary",
    ]
    assert payload["candidate_id"] == "candidate-001"
    assert payload["visible_source_only"] is True
    assert payload["result_summary"] == {"status": "READY"}


def test_visible_source_result_summary_report_emits_expected_shape() -> None:
    payload = visible_source_result_summary_report(
        "QDP_SAMPLE_VISIBLE_SOURCE_REPORT",
        "M98",
        {"status": "READY"},
        metadata={"evidence_text_sample": "sample"},
        diagnostics={"flag": True},
    )

    assert list(payload.keys()) == [
        "artifact_id",
        "module_id",
        "timestamp_utc",
        "visible_source_only",
        "evidence_text_sample",
        "result_summary",
        "diagnostics",
    ]
    assert payload["visible_source_only"] is True
    assert payload["result_summary"] == {"status": "READY"}
    assert payload["diagnostics"] == {"flag": True}


def test_reference_manifest_helpers_cover_surrogate_and_binding_logic() -> None:
    manifest = {
        "reference_entries": [
            {"ref_id": RETAINED_RUNTIME_REF_ID, "provenance": "reconstructed_surrogate"},
            {
                "ref_id": RETAINED_GOVERNANCE_REGISTRY_REF_ID,
                "provenance": "original",
                "authoritative_binding_status": "BOUND",
            },
        ]
    }
    governance_registry = {
        "authoritative_reference_bindings": {
            RETAINED_RUNTIME_REF_ID: {"status": "BOUND"},
        }
    }

    assert find_reference_entry(manifest, RETAINED_RUNTIME_REF_ID)["provenance"] == "reconstructed_surrogate"
    assert reference_is_reconstructed_surrogate(find_reference_entry(manifest, RETAINED_RUNTIME_REF_ID)) is True
    assert reference_has_authoritative_binding(RETAINED_RUNTIME_REF_ID, manifest, governance_registry) is True
    assert reference_has_authoritative_binding(RETAINED_GOVERNANCE_REGISTRY_REF_ID, manifest, {}) is True
    assert retained_reference_provenance_mode(manifest) == "surrogate"


def test_module_registry_helpers_emit_expected_payloads() -> None:
    blueprints = {
        "M01": {
            "name": "runtime_assembly",
            "purpose": "Assemble runtime provenance",
            "blocker_class": "core",
            "owner_artifacts": ["assembly_report"],
            "required_outputs": ["closure_report"],
        }
    }
    closure_by_module = {
        "M01": {
            "derived_status": "RECOVERY_READY",
            "closure_limitations": ["retained-authority-pending"],
        }
    }
    readiness = {
        "ordinary_recovery_ready": True,
        "ordinary_authoritative_ready": False,
        "ordinary_testing_ready": True,
        "subsystem_recovery_ready": True,
        "subsystem_authoritative_ready": False,
        "subsystem_testing_ready": False,
    }

    payload = build_module_registry_json(
        blueprints,
        resume_policy={"ordinary": "gated"},
        closure_by_module=closure_by_module,
        readiness=readiness,
    )
    markdown = build_module_registry_md(
        blueprints,
        closure_by_module=closure_by_module,
        readiness=readiness,
    )

    assert payload["artifact_id"] == "QDP_V10_6_MODULE_REGISTRY_V2"
    assert payload["modules"][0]["derived_closure_status"] == "RECOVERY_READY"
    assert payload["modules"][0]["closure_limitations"] == ["retained-authority-pending"]
    assert "ordinary_authoritative_ready: false" in markdown
    assert "| M01 | runtime_assembly | Assemble runtime provenance | closure_report | RECOVERY_READY |" in markdown
