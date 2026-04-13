from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from analysis.e01_mm_analysis_input_builder import build_analysis_input, main


BRANCH_ROOT = Path(__file__).resolve().parent.parent
BUILDER_SCRIPT_PATH = BRANCH_ROOT / "analysis" / "e01_mm_analysis_input_builder.py"
RUNNER_SCRIPT_PATH = BRANCH_ROOT / "analysis" / "e01_mm_analysis_runner.py"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")


def load_run_binding_template() -> dict[str, object]:
    template_path = BRANCH_ROOT / "protocols" / "e01_mm_first_cooldown_run_binding.json"
    return json.loads(template_path.read_text(encoding="ascii"))


def make_bound_run_binding(temp_root: Path, *, include_dwell: bool = True, metadata_filename: str = "measurement_evidence.json") -> Path:
    run_binding = load_run_binding_template()
    run_binding["binding_context"] = "AS_RUN_BINDING"
    run_binding["binding_status"] = "AS_RUN_BOUND"
    run_binding["cooldown_id"] = "CD-001"
    run_binding["hardware_binding"]["target_device_ids"] = ["device_a"]
    run_binding["hardware_binding"]["matched_geometry_device_ids"] = ["device_a", "device_b"]
    run_binding["fixed_settings"]["T_base"] = 0.02
    run_binding["fixed_settings"]["P_read"] = -100.0
    run_binding["field_program"]["production_dwell_t_conv"] = 30.0 if include_dwell else None
    run_binding["data_capture"]["metadata_output_path"] = str((temp_root / metadata_filename).resolve())
    run_binding["data_capture"]["raw_data_output_path"] = str((temp_root / "raw_capture").resolve())
    run_binding["data_capture"]["witness_trace_output_path"] = str((temp_root / "witness_capture").resolve())
    run_binding_path = temp_root / "run_binding.json"
    write_json(run_binding_path, run_binding)
    return run_binding_path


def make_measurement_evidence(temp_root: Path, *, include_dwell_metadata: bool = True) -> Path:
    records = []
    for history_label in ("ZFC", "FC"):
        for branch, values in (("up", [0.0, 0.5, 1.0]), ("down", [0.1, 0.3, 0.6])):
            fields = [0.0, 1.0, 2.0] if branch == "up" else [2.0, 1.0, 0.0]
            for index, (field, inv_qi) in enumerate(zip(fields, values)):
                records.append(
                    {
                        "cooldown_id": "CD-001",
                        "device_id": "device_a",
                        "geometry_id": "geom_a",
                        "history_label": history_label,
                        "branch": branch,
                        "commanded_field": field,
                        "calibrated_field": field,
                        "elapsed_time": float(index * 10),
                        "dwell_duration": 10.0,
                        "inv_qi": inv_qi,
                        "fr": 5.0,
                        "delta_fr_over_fr": -1.0e-7 * field,
                        "T1": None,
                        "witness_response": 0.01 * inv_qi,
                        "bath_temperature": 0.02,
                        "readout_power": -100.0,
                    }
                )
    for checkpoint_index in range(3):
        records.append(
            {
                "cooldown_id": "CD-001",
                "device_id": "device_a",
                "geometry_id": "geom_a",
                "history_label": "ZFC",
                "branch": "checkpoint",
                "commanded_field": 0.0,
                "calibrated_field": 0.0,
                "elapsed_time": 100.0 + checkpoint_index,
                "dwell_duration": 5.0,
                "inv_qi": 0.0,
                "fr": 5.0,
                "delta_fr_over_fr": 0.0,
                "T1": None,
                "witness_response": 0.0,
                "bath_temperature": 0.02,
                "readout_power": -100.0,
            }
        )
    for sham_index in range(4):
        records.append(
            {
                "cooldown_id": "CD-001",
                "device_id": "device_a",
                "geometry_id": "geom_a",
                "history_label": "SHAM",
                "branch": "sham",
                "commanded_field": 0.0,
                "calibrated_field": 0.0,
                "elapsed_time": 120.0 + sham_index,
                "dwell_duration": 5.0,
                "inv_qi": 0.0,
                "fr": 5.0,
                "delta_fr_over_fr": 0.0,
                "T1": None,
                "witness_response": 0.0,
                "bath_temperature": 0.02,
                "readout_power": -100.0,
            }
        )
    payload: dict[str, object] = {
        "measurement_evidence_schema_version": "1.0.0",
        "records": records,
    }
    if include_dwell_metadata:
        payload["dwell_metadata"] = [
            {
                "cooldown_id": "CD-001",
                "converged": True,
                "production_dwell_t_conv": 30.0,
                "doubled_loop_change_fraction": 0.02,
            }
        ]
    evidence_path = temp_root / "measurement_evidence.json"
    write_json(evidence_path, payload)
    return evidence_path


class AnalysisInputBuilderTests(unittest.TestCase):
    def test_builder_emits_valid_payload_from_bound_run_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            run_binding_path = make_bound_run_binding(temp_root)
            make_measurement_evidence(temp_root)

            output_path = temp_root / "analysis_input.json"
            exit_code = main(["--run-binding", str(run_binding_path), "--output-path", str(output_path)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="ascii"))
            self.assertEqual(payload["analysis_schema_version"], "1.0.0")
            self.assertEqual(payload["primary_device_id"], "device_a")
            self.assertEqual(payload["matched_geometry_device_ids"], ["device_a", "device_b"])
            self.assertTrue(payload["records"])
            self.assertTrue(payload["dwell_metadata"])

    def test_authoritative_bindings_win_for_primary_and_geometry(self) -> None:
        run_binding = load_run_binding_template()
        run_binding["cooldown_id"] = "CD-001"
        run_binding["hardware_binding"]["target_device_ids"] = ["device_authoritative"]
        run_binding["hardware_binding"]["matched_geometry_device_ids"] = ["geom_authoritative_a", "geom_authoritative_b"]
        run_binding["fixed_settings"]["T_base"] = 0.02
        run_binding["fixed_settings"]["P_read"] = -100.0
        measurement_evidence = {
            "measurement_evidence_schema_version": "1.0.0",
            "records": [
                {
                    "cooldown_id": "CD-001",
                    "device_id": "device_measurement",
                    "geometry_id": "geom_measurement",
                    "history_label": "ZFC",
                    "branch": "up",
                    "commanded_field": 0.0,
                    "calibrated_field": 0.0,
                    "elapsed_time": 0.0,
                    "dwell_duration": 10.0,
                    "inv_qi": 0.0,
                    "fr": 5.0,
                    "delta_fr_over_fr": 0.0,
                    "bath_temperature": 0.02,
                    "readout_power": -100.0,
                }
            ],
        }
        payload = build_analysis_input(run_binding, measurement_evidence)
        self.assertEqual(payload["primary_device_id"], "device_authoritative")
        self.assertEqual(payload["matched_geometry_device_ids"], ["geom_authoritative_a", "geom_authoritative_b"])

    def test_missing_or_unsupported_measurement_evidence_fails_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            run_binding_path = make_bound_run_binding(temp_root, metadata_filename="measurement_evidence.txt")
            (temp_root / "measurement_evidence.txt").write_text("not supported", encoding="ascii")
            output_path = temp_root / "analysis_input.json"

            result = subprocess.run(
                [sys.executable, str(BUILDER_SCRIPT_PATH), "--run-binding", str(run_binding_path), "--output-path", str(output_path)],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unsupported or invalid measurement evidence format", result.stderr)

    def test_absent_optional_dwell_metadata_emits_empty_or_derived_list(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            run_binding_path = make_bound_run_binding(temp_root, include_dwell=False)
            make_measurement_evidence(temp_root, include_dwell_metadata=False)

            output_path = temp_root / "analysis_input.json"
            main(["--run-binding", str(run_binding_path), "--output-path", str(output_path)])

            payload = json.loads(output_path.read_text(encoding="ascii"))
            self.assertEqual(payload["dwell_metadata"], [])

    def test_builder_output_is_accepted_by_analysis_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            run_binding_path = make_bound_run_binding(temp_root)
            make_measurement_evidence(temp_root)
            analysis_input_path = temp_root / "analysis_input.json"
            analysis_output_dir = temp_root / "analysis_output"

            subprocess.run(
                [sys.executable, str(BUILDER_SCRIPT_PATH), "--run-binding", str(run_binding_path), "--output-path", str(analysis_input_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                [sys.executable, str(RUNNER_SCRIPT_PATH), "--input", str(analysis_input_path), "--output-dir", str(analysis_output_dir)],
                capture_output=True,
                text=True,
                check=True,
            )

            summary = json.loads((analysis_output_dir / "summary.json").read_text(encoding="ascii"))
            self.assertIn("branch_disposition", summary)

    def test_queue_manifest_can_discover_run_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            run_binding_path = make_bound_run_binding(temp_root)
            make_measurement_evidence(temp_root)
            manifest_path = temp_root / "queue_manifest.json"
            write_json(
                manifest_path,
                {
                    "queue_schema_version": "1.1.0",
                    "queue_item_id": "queue_item_001",
                    "run_binding_path": str(run_binding_path),
                    "run_binding": json.loads(run_binding_path.read_text(encoding="ascii")),
                },
            )
            output_path = temp_root / "analysis_input.json"
            exit_code = main(["--queue-manifest", str(manifest_path), "--output-path", str(output_path)])
            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="ascii"))
            self.assertEqual(payload["primary_device_id"], "device_a")


if __name__ == "__main__":
    unittest.main()
