from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from execution_queue.e01_mm_execution_queue import (
    advance_queue_manifest,
    create_queue_manifest,
    load_queue_manifest,
    main,
    process_queue_directory,
    process_queue_manifest,
    write_queue_manifest,
)
from execution_queue.e01_mm_execution_sheet_sync import (
    preview_execution_sheet_sync,
    sync_execution_sheet,
)
from execution_queue.e01_mm_reconciliation import reconcile_queue_manifest


BRANCH_ROOT = Path(__file__).resolve().parent.parent
RUN_BINDING_TEMPLATE_PATH = BRANCH_ROOT / "protocols" / "e01_mm_first_cooldown_run_binding.json"
EXECUTION_SHEET_PATH = BRANCH_ROOT / "protocols" / "e01_mm_first_cooldown_execution_sheet.md"
QUEUE_SCRIPT_PATH = BRANCH_ROOT / "execution_queue" / "e01_mm_execution_queue.py"


def load_template() -> dict[str, object]:
    return json.loads(RUN_BINDING_TEMPLATE_PATH.read_text(encoding="ascii"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")


def write_markdown_frontmatter(path: Path, fields: dict[str, object]) -> None:
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, (list, dict)):
            rendered = json.dumps(value)
        elif value is True:
            rendered = "true"
        elif value is False:
            rendered = "false"
        elif value is None:
            rendered = "null"
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    lines.append("---")
    lines.append("evidence")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def build_evidence_paths(temp_root: Path, markdown_logbook: bool = False) -> dict[str, str]:
    as_run_filename = "as_run_logbook.md" if markdown_logbook else "as_run_logbook.json"
    return {
        "as_run_logbook_path": str((temp_root / as_run_filename).resolve()),
        "fridge_log_path": str((temp_root / "fridge_log.json").resolve()),
        "sample_map_path": str((temp_root / "sample_map.json").resolve()),
        "channel_map_path": str((temp_root / "channel_map.json").resolve()),
        "daq_record_path": str((temp_root / "daq_record.json").resolve()),
        "calibration_record_path": str((temp_root / "calibration_record.json").resolve()),
        "raw_data_output_path": str((temp_root / "raw").resolve()),
        "metadata_output_path": str((temp_root / "metadata.json").resolve()),
        "witness_trace_output_path": str((temp_root / "witness").resolve()),
    }


def create_complete_evidence(temp_root: Path, markdown_logbook: bool = False) -> dict[str, str]:
    evidence_paths = build_evidence_paths(temp_root, markdown_logbook=markdown_logbook)

    as_run_payload = {
        "cooldown_id": "CD-001",
        "operator": "operator_1",
        "run_date": "2026-03-27",
        "lab_location": "fridge_bay_2",
        "field_unit": "mT",
        "B_max": 5.0,
        "fc_field": 2.0,
        "field_steps": [0.0, 1.0, 3.0, 5.0, 0.0, -1.0, -3.0, -5.0, 0.0],
        "selected_fields": [0.0, 1.0, 5.0],
        "probe_fields": [0.0, 1.0, 5.0],
        "dwell_times": [30.0, 60.0, 90.0],
        "dwell_time_unit": "s",
    }
    if markdown_logbook:
        write_markdown_frontmatter(Path(evidence_paths["as_run_logbook_path"]), as_run_payload)
    else:
        write_json(Path(evidence_paths["as_run_logbook_path"]), as_run_payload)

    write_json(
        Path(evidence_paths["fridge_log_path"]),
        {
            "cooldown_id": "CD-001",
            "operator": "operator_1",
            "run_date": "2026-03-27",
            "lab_location": "fridge_bay_2",
            "target_device_ids": ["device_a"],
            "witness_channel_id": "witness_mux_1",
            "matched_geometry_device_ids": [],
        },
    )
    write_json(Path(evidence_paths["sample_map_path"]), {"target_device_ids": ["device_a"], "matched_geometry_device_ids": []})
    write_json(Path(evidence_paths["channel_map_path"]), {"witness_channel_id": "witness_mux_1"})
    write_json(
        Path(evidence_paths["daq_record_path"]),
        {
            "T_base": 0.018,
            "P_read": -103.5,
            "readout_tone_id": "tone_01",
            "attenuation_state": "atten_60dB",
            "readout_chain_config": "chain_alpha",
            "field_unit": "mT",
            "B_max": 5.0,
            "fc_field": 2.0,
            "field_steps": [0.0, 1.0, 3.0, 5.0, 0.0, -1.0, -3.0, -5.0, 0.0],
            "selected_fields": [0.0, 1.0, 5.0],
            "probe_fields": [0.0, 1.0, 5.0],
            "dwell_times": [30.0, 60.0, 90.0],
            "dwell_time_unit": "s",
        },
    )
    write_json(Path(evidence_paths["calibration_record_path"]), {"P_read": -103.5, "p_read_device_calibrated": True})

    (temp_root / "raw").mkdir()
    (temp_root / "witness").mkdir()
    (temp_root / "metadata.json").write_text("{}", encoding="ascii")
    return evidence_paths


def build_manifest(
    temp_root: Path,
    binding: dict[str, object],
    evidence_paths: dict[str, str] | None = None,
    execution_sheet_path: Path | None = None,
    manifest_filename: str = "queue_manifest.json",
) -> tuple[Path, dict[str, object]]:
    run_binding_path = temp_root / "run_binding.json"
    write_json(run_binding_path, binding)
    resolved_execution_sheet_path = execution_sheet_path or copy_execution_sheet(temp_root)
    manifest = create_queue_manifest(
        queue_item_id="queue_item_001",
        branch_slug="e01_mm_flux_history_hysteresis",
        run_binding_path=str(run_binding_path),
        execution_sheet_path=str(resolved_execution_sheet_path.resolve()),
        run_binding=binding,
        required_evidence_paths=evidence_paths or build_evidence_paths(temp_root),
    )
    manifest_path = temp_root / manifest_filename
    write_queue_manifest(manifest_path, manifest)
    return manifest_path, manifest


def copy_execution_sheet(temp_root: Path) -> Path:
    execution_sheet_copy = temp_root / "execution_sheet.md"
    execution_sheet_copy.write_text(EXECUTION_SHEET_PATH.read_text(encoding="ascii"), encoding="ascii")
    return execution_sheet_copy


class ExecutionQueueTests(unittest.TestCase):
    def test_happy_path_reconciles_sources_and_completes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            manifest["queue_state"] = "IN_PROGRESS"

            updated = advance_queue_manifest(manifest_path, manifest, worker_id="worker_a")
            self.assertEqual(updated["queue_state"], "READY_FOR_AS_RUN_BINDING")
            self.assertEqual(updated["run_binding"]["binding_context"], "AS_RUN_BINDING")
            self.assertEqual(updated["run_binding"]["cooldown_id"], "CD-001")
            self.assertEqual(updated["run_binding"]["binding_status"], "AS_RUN_BOUND")

            updated = advance_queue_manifest(manifest_path, updated, worker_id="worker_a")
            self.assertEqual(updated["queue_state"], "COMPLETE")
            self.assertEqual(updated["reconciliation"]["status"], "clean")

    def test_missing_source_families_block_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            required_sources = [
                "as_run_logbook_path",
                "fridge_log_path",
                "sample_map_path",
                "channel_map_path",
                "daq_record_path",
                "calibration_record_path",
            ]
            for missing_source in required_sources:
                with self.subTest(missing_source=missing_source):
                    temp_root = Path(temporary_directory) / missing_source
                    temp_root.mkdir()
                    evidence_paths = create_complete_evidence(temp_root)
                    Path(evidence_paths[missing_source]).unlink()
                    binding = load_template()
                    manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
                    manifest["queue_state"] = "READY_FOR_AS_RUN_BINDING"

                    updated = advance_queue_manifest(manifest_path, manifest, worker_id="worker_a")
                    self.assertEqual(updated["queue_state"], "BLOCKED_VALIDATION")
                    self.assertIn(updated["reconciliation"]["status"], {"blocked"})
                    self.assertTrue(
                        any(
                            code in updated["last_validator_result"]["reason_codes"]
                            for code in ("PROVENANCE_PATH_NOT_FOUND", "MISSING_REQUIRED_SOURCE_FIELD")
                        )
                    )

    def test_source_conflicts_fail_critical_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            conflict_cases = {
                "cooldown_id": ("fridge_log_path", {"cooldown_id": "CD-999"}),
                "hardware_binding.target_device_ids": ("sample_map_path", {"target_device_ids": ["device_b"], "matched_geometry_device_ids": []}),
                "fixed_settings.P_read": ("calibration_record_path", {"P_read": -100.0, "p_read_device_calibrated": True}),
            }
            for conflict_field, (source_key, override_payload) in conflict_cases.items():
                with self.subTest(conflict_field=conflict_field):
                    temp_root = Path(temporary_directory) / conflict_field.replace(".", "_")
                    temp_root.mkdir()
                    evidence_paths = create_complete_evidence(temp_root)
                    source_path = Path(evidence_paths[source_key])
                    base_payload = json.loads(source_path.read_text(encoding="ascii"))
                    base_payload.update(override_payload)
                    write_json(source_path, base_payload)
                    binding = load_template()
                    manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
                    manifest["queue_state"] = "READY_FOR_AS_RUN_BINDING"

                    updated = advance_queue_manifest(manifest_path, manifest, worker_id="worker_a")
                    self.assertEqual(updated["queue_state"], "FAILED")
                    self.assertEqual(updated["reconciliation"]["status"], "failed")
                    self.assertEqual(updated["reconciliation"]["source_conflicts"][0]["field"], conflict_field)

    def test_parse_failures_fail_reconciliation_for_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cases = {
                "json": ("daq_record_path", "{bad json"),
                "markdown": ("as_run_logbook_path", "---\nnot-valid\n"),
            }
            for label, (source_key, payload_text) in cases.items():
                with self.subTest(label=label):
                    temp_root = Path(temporary_directory) / label
                    temp_root.mkdir()
                    evidence_paths = create_complete_evidence(temp_root, markdown_logbook=(label == "markdown"))
                    Path(evidence_paths[source_key]).write_text(payload_text, encoding="ascii")
                    binding = load_template()
                    manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
                    manifest["queue_state"] = "READY_FOR_AS_RUN_BINDING"

                    updated = advance_queue_manifest(manifest_path, manifest, worker_id="worker_a")
                    self.assertEqual(updated["queue_state"], "FAILED")
                    self.assertIn("SOURCE_PARSE_FAILED", updated["reconciliation"]["reason_codes"])

    def test_output_paths_remain_unbound_until_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            evidence_paths = build_evidence_paths(temp_root)
            write_json(Path(evidence_paths["as_run_logbook_path"]), {"cooldown_id": "CD-001"})
            write_json(Path(evidence_paths["fridge_log_path"]), {"target_device_ids": ["device_a"], "witness_channel_id": "witness_mux_1", "matched_geometry_device_ids": []})
            write_json(Path(evidence_paths["sample_map_path"]), {"target_device_ids": ["device_a"], "matched_geometry_device_ids": []})
            write_json(Path(evidence_paths["channel_map_path"]), {"witness_channel_id": "witness_mux_1"})
            write_json(Path(evidence_paths["daq_record_path"]), {"T_base": 0.018, "P_read": -103.5})
            write_json(Path(evidence_paths["calibration_record_path"]), {"P_read": -103.5, "p_read_device_calibrated": True})
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)

            reconciled = reconcile_queue_manifest(manifest_path, manifest)
            self.assertFalse(reconciled["run_binding"]["binding_checks"]["output_paths_exist"])
            self.assertIsNone(reconciled["run_binding"]["data_capture"]["raw_data_output_path"])

    def test_stop_condition_escalates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            manifest["queue_state"] = "READY_FOR_AS_RUN_BINDING"
            manifest["stop_condition_reasons"] = ["SHAM_CONTROL_MISSING"]

            updated = advance_queue_manifest(manifest_path, manifest, worker_id="worker_a")
            self.assertEqual(updated["queue_state"], "ESCALATED")
            self.assertEqual(updated["escalation_reason"], "SHAM_CONTROL_MISSING")

    def test_lease_conflict_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            manifest["lease_owner"] = "worker_a"
            manifest["lease_acquired_at"] = "2026-03-27T12:00:00Z"
            manifest["lease_expires_at"] = "2999-03-27T12:05:00Z"

            with self.assertRaises(RuntimeError):
                advance_queue_manifest(manifest_path, manifest, worker_id="worker_b")

    def test_terminal_malformed_binding_fails_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            manifest["queue_state"] = "READY_FOR_AS_RUN_BINDING"
            manifest["run_binding"] = None

            updated = advance_queue_manifest(manifest_path, manifest, worker_id="worker_a")
            self.assertEqual(updated["queue_state"], "FAILED")
            self.assertEqual(updated["escalation_reason"], "MALFORMED_RUN_BINDING")

    def test_dry_run_cli_does_not_mutate_run_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            evidence_paths = create_complete_evidence(temp_root, markdown_logbook=True)
            binding = load_template()
            manifest_path, _ = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            run_binding_path = temp_root / "run_binding.json"
            before_text = run_binding_path.read_text(encoding="ascii")

            result = subprocess.run(
                [sys.executable, str(QUEUE_SCRIPT_PATH), "reconcile-dry-run", "--manifest-path", str(manifest_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            after_text = run_binding_path.read_text(encoding="ascii")
            self.assertEqual(before_text, after_text)
            self.assertIn('"reconciliation"', result.stdout)
            self.assertIn('"proposed_run_binding"', result.stdout)

    def test_tick_command_persists_reconciled_run_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, _ = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            run_binding_path = temp_root / "run_binding.json"

            main(["tick", "--manifest-path", str(manifest_path), "--worker-id", "worker_a"])
            main(["tick", "--manifest-path", str(manifest_path), "--worker-id", "worker_a"])
            main(["tick", "--manifest-path", str(manifest_path), "--worker-id", "worker_a"])
            main(["tick", "--manifest-path", str(manifest_path), "--worker-id", "worker_a"])

            persisted = json.loads(run_binding_path.read_text(encoding="ascii"))
            self.assertEqual(persisted["binding_context"], "AS_RUN_BINDING")
            self.assertEqual(persisted["binding_status"], "AS_RUN_BOUND")

    def test_process_queue_manifest_writes_audit_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            audit_dir = temp_root / "audit"
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            manifest["queue_state"] = "IN_PROGRESS"
            write_queue_manifest(manifest_path, manifest)

            result = process_queue_manifest(manifest_path, worker_id="worker_a", audit_dir=audit_dir)
            self.assertEqual(result["queue_state_after"], "READY_FOR_AS_RUN_BINDING")
            self.assertIsNotNone(result["audit_snapshot_path"])

            snapshot_files = sorted(audit_dir.glob("*.json"))
            self.assertEqual(len(snapshot_files), 1)
            snapshot = json.loads(snapshot_files[0].read_text(encoding="ascii"))
            self.assertEqual(snapshot["snapshot_version"], "1.0.0")
            self.assertEqual(snapshot["queue_state_before"], "IN_PROGRESS")
            self.assertEqual(snapshot["queue_state_after"], "READY_FOR_AS_RUN_BINDING")
            self.assertEqual(snapshot["outcome"], "advanced")

    def test_run_once_mixed_directory_summary_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            queue_dir = Path(temporary_directory)
            audit_dir = queue_dir / "audit"

            complete_root = queue_dir / "complete_item"
            complete_root.mkdir()
            complete_evidence = create_complete_evidence(complete_root)
            complete_binding = load_template()
            complete_manifest_path, complete_manifest = build_manifest(
                complete_root,
                complete_binding,
                evidence_paths=complete_evidence,
                manifest_filename="complete_item_manifest.json",
            )
            complete_manifest["queue_item_id"] = "complete_item"
            complete_manifest["queue_state"] = "IN_PROGRESS"
            write_queue_manifest(queue_dir / "complete_item_manifest.json", complete_manifest)

            blocked_root = queue_dir / "blocked_item"
            blocked_root.mkdir()
            blocked_evidence = create_complete_evidence(blocked_root)
            Path(blocked_evidence["daq_record_path"]).unlink()
            blocked_binding = load_template()
            blocked_manifest_path, blocked_manifest = build_manifest(
                blocked_root,
                blocked_binding,
                evidence_paths=blocked_evidence,
                manifest_filename="blocked_item_manifest.json",
            )
            blocked_manifest["queue_item_id"] = "blocked_item"
            blocked_manifest["queue_state"] = "READY_FOR_AS_RUN_BINDING"
            write_queue_manifest(queue_dir / "blocked_item_manifest.json", blocked_manifest)

            summary = process_queue_directory(queue_dir, worker_id="worker_a", audit_dir=audit_dir)
            self.assertEqual(summary["processed_count"], 2)
            self.assertEqual(summary["completed_count"], 0)
            self.assertEqual(summary["blocked_count"], 1)
            self.assertEqual(summary["advanced_count"], 1)
            self.assertEqual(summary["failed_count"], 0)
            self.assertEqual(len(summary["items"]), 2)

    def test_active_lease_is_skipped_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            audit_dir = temp_root / "audit"
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            manifest["lease_owner"] = "worker_a"
            manifest["lease_acquired_at"] = "2026-03-27T12:00:00Z"
            manifest["lease_expires_at"] = "2999-03-27T12:05:00Z"
            write_queue_manifest(manifest_path, manifest)
            before_text = manifest_path.read_text(encoding="ascii")

            result = process_queue_manifest(manifest_path, worker_id="worker_b", audit_dir=audit_dir)
            after_text = manifest_path.read_text(encoding="ascii")
            self.assertEqual(result["outcome"], "skipped_leased")
            self.assertEqual(before_text, after_text)
            self.assertEqual(len(list(audit_dir.glob("*.json"))), 1)

    def test_expired_lease_is_reclaimed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            manifest["queue_state"] = "IN_PROGRESS"
            manifest["lease_owner"] = "worker_a"
            manifest["lease_acquired_at"] = "2026-03-27T12:00:00Z"
            manifest["lease_expires_at"] = "2000-03-27T12:05:00Z"
            write_queue_manifest(manifest_path, manifest)

            result = process_queue_manifest(manifest_path, worker_id="worker_b")
            self.assertEqual(result["outcome"], "advanced")
            reloaded = load_queue_manifest(manifest_path)
            self.assertEqual(reloaded["queue_state"], "READY_FOR_AS_RUN_BINDING")
            self.assertIsNone(reloaded["lease_owner"])

    def test_audit_snapshots_are_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            audit_dir = temp_root / "audit"
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            manifest["queue_state"] = "IN_PROGRESS"
            write_queue_manifest(manifest_path, manifest)

            first_result = process_queue_manifest(manifest_path, worker_id="worker_a", audit_dir=audit_dir)
            second_result = process_queue_manifest(manifest_path, worker_id="worker_a", audit_dir=audit_dir)
            self.assertNotEqual(first_result["audit_snapshot_path"], second_result["audit_snapshot_path"])
            self.assertEqual(len(list(audit_dir.glob("*.json"))), 2)

    def test_run_once_returns_zero_for_item_level_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            evidence_paths = create_complete_evidence(temp_root)
            Path(evidence_paths["daq_record_path"]).write_text("{bad json", encoding="ascii")
            binding = load_template()
            manifest_path, manifest = build_manifest(temp_root, binding, evidence_paths=evidence_paths)
            manifest["queue_state"] = "READY_FOR_AS_RUN_BINDING"
            write_queue_manifest(manifest_path, manifest)

            exit_code = main(["run-once", "--queue-dir", str(temp_root), "--worker-id", "worker_a"])
            self.assertEqual(exit_code, 0)
            reloaded = load_queue_manifest(manifest_path)
            self.assertEqual(reloaded["queue_state"], "FAILED")

    def test_execution_sheet_is_not_written_by_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            execution_sheet_path = temp_root / "execution_sheet.md"
            execution_sheet_path.write_text("original execution sheet\n", encoding="ascii")
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(
                temp_root,
                binding,
                evidence_paths=evidence_paths,
                execution_sheet_path=execution_sheet_path,
            )
            manifest["queue_state"] = "IN_PROGRESS"
            write_queue_manifest(manifest_path, manifest)
            before_text = execution_sheet_path.read_text(encoding="ascii")

            process_queue_manifest(manifest_path, worker_id="worker_a", audit_dir=temp_root / "audit")

            after_text = execution_sheet_path.read_text(encoding="ascii")
            self.assertEqual(before_text, after_text)

    def test_happy_path_syncs_execution_sheet_from_run_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            execution_sheet_copy = copy_execution_sheet(temp_root)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(
                temp_root,
                binding,
                evidence_paths=evidence_paths,
                execution_sheet_path=execution_sheet_copy,
            )
            manifest["queue_state"] = "IN_PROGRESS"
            write_queue_manifest(manifest_path, manifest)

            process_queue_manifest(manifest_path, worker_id="worker_a", audit_dir=temp_root / "audit")

            synced_text = execution_sheet_copy.read_text(encoding="ascii")
            self.assertIn("| `binding_context` | `AS_RUN_BINDING` |", synced_text)
            self.assertIn("| `binding_status` | `AS_RUN_BOUND` |", synced_text)
            self.assertIn("| `cooldown_id` | `CD-001` |", synced_text)
            self.assertIn("| `target_device_ids` | `[\"device_a\"]` |", synced_text)
            self.assertIn("| raw data output path |", synced_text)

            reloaded = load_queue_manifest(manifest_path)
            self.assertEqual(reloaded["sheet_sync"]["status"], "synced")
            self.assertIn("binding_context", reloaded["sheet_sync"]["updated_fields"])

    def test_partial_sync_leaves_unresolved_placeholders_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            execution_sheet_copy = copy_execution_sheet(temp_root)
            binding = load_template()
            binding["binding_context"] = "PRE_RUN_MINIMUM_ACQUISITION"
            binding["binding_status"] = "TEMPLATE_UNBOUND"
            binding["cooldown_id"] = "CD-001"
            manifest_path, manifest = build_manifest(
                temp_root,
                binding,
                execution_sheet_path=execution_sheet_copy,
            )
            manifest["queue_state"] = "READY_FOR_PRECHECK"
            manifest["reconciliation"]["status"] = "clean"

            sync_execution_sheet(manifest_path, manifest, write_changes=True)

            synced_text = execution_sheet_copy.read_text(encoding="ascii")
            self.assertIn("| `cooldown_id` | `CD-001` |", synced_text)
            self.assertIn("| `operator` | `TBD` |", synced_text)
            self.assertIn("| `T_base` | `UNBOUND` |", synced_text)

    def test_sheet_sync_is_skipped_on_conflict_or_stop_condition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            for mode in ("conflict", "stop"):
                with self.subTest(mode=mode):
                    temp_root = Path(temporary_directory) / mode
                    temp_root.mkdir()
                    execution_sheet_copy = copy_execution_sheet(temp_root)
                    evidence_paths = create_complete_evidence(temp_root)
                    binding = load_template()
                    manifest_path, manifest = build_manifest(
                        temp_root,
                        binding,
                        evidence_paths=evidence_paths,
                        execution_sheet_path=execution_sheet_copy,
                    )
                    manifest["queue_state"] = "READY_FOR_AS_RUN_BINDING"
                    if mode == "conflict":
                        manifest["reconciliation"]["status"] = "blocked"
                        manifest["reconciliation"]["source_conflicts"] = [{"field": "cooldown_id"}]
                    else:
                        manifest["reconciliation"]["status"] = "clean"
                        manifest["stop_condition_reasons"] = ["SHAM_CONTROL_MISSING"]
                    before_text = execution_sheet_copy.read_text(encoding="ascii")

                    sync_execution_sheet(manifest_path, manifest, write_changes=True)

                    after_text = execution_sheet_copy.read_text(encoding="ascii")
                    self.assertEqual(before_text, after_text)
                    self.assertEqual(manifest["sheet_sync"]["status"], "skipped")
                    self.assertTrue(manifest["sheet_sync"]["reason_codes"])

    def test_execution_sheet_sync_does_not_mutate_run_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            execution_sheet_copy = copy_execution_sheet(temp_root)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(
                temp_root,
                binding,
                evidence_paths=evidence_paths,
                execution_sheet_path=execution_sheet_copy,
            )
            manifest["queue_state"] = "IN_PROGRESS"
            reconciled = reconcile_queue_manifest(manifest_path, manifest)
            before_binding = json.dumps(reconciled["run_binding"], sort_keys=True)

            sync_execution_sheet(manifest_path, reconciled, write_changes=True)

            after_binding = json.dumps(reconciled["run_binding"], sort_keys=True)
            self.assertEqual(before_binding, after_binding)

    def test_sheet_sync_preview_shows_proposed_updates_without_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            execution_sheet_copy = copy_execution_sheet(temp_root)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(
                temp_root,
                binding,
                evidence_paths=evidence_paths,
                execution_sheet_path=execution_sheet_copy,
            )
            manifest["queue_state"] = "IN_PROGRESS"
            reconciled = reconcile_queue_manifest(manifest_path, manifest)
            before_text = execution_sheet_copy.read_text(encoding="ascii")

            preview = preview_execution_sheet_sync(manifest_path, reconciled)

            after_text = execution_sheet_copy.read_text(encoding="ascii")
            self.assertEqual(before_text, after_text)
            self.assertEqual(preview["status"], "ready")
            self.assertIn("binding_context", preview["updated_fields"])
            self.assertIn("| `binding_context` | `AS_RUN_BINDING` |", preview["proposed_text"])

    def test_sheet_sync_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            execution_sheet_copy = copy_execution_sheet(temp_root)
            evidence_paths = create_complete_evidence(temp_root)
            binding = load_template()
            manifest_path, manifest = build_manifest(
                temp_root,
                binding,
                evidence_paths=evidence_paths,
                execution_sheet_path=execution_sheet_copy,
            )
            manifest["queue_state"] = "IN_PROGRESS"
            write_queue_manifest(manifest_path, manifest)

            process_queue_manifest(manifest_path, worker_id="worker_a", audit_dir=temp_root / "audit")
            first_text = execution_sheet_copy.read_text(encoding="ascii")
            process_queue_manifest(manifest_path, worker_id="worker_a", audit_dir=temp_root / "audit")
            second_text = execution_sheet_copy.read_text(encoding="ascii")

            self.assertEqual(first_text, second_text)
            reloaded = load_queue_manifest(manifest_path)
            self.assertIn(reloaded["sheet_sync"]["status"], {"unchanged", "synced"})


if __name__ == "__main__":
    unittest.main()
