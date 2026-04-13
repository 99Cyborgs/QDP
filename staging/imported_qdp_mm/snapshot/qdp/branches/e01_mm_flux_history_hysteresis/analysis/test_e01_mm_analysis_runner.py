from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from analysis.e01_mm_analysis_runner import (
    DEFAULT_ANALYSIS_SCHEMA_VERSION,
    build_common_field_grid,
    compute_loop_metrics,
    generate_analysis_summary,
    main,
)


BRANCH_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_SCRIPT_PATH = BRANCH_ROOT / "analysis" / "e01_mm_analysis_runner.py"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")


def make_loop_records(
    cooldown_id: str,
    device_id: str,
    geometry_id: str,
    history_label: str,
    up_values: list[float],
    down_values: list[float],
    *,
    witness_scale: float = 0.1,
    field_grid: list[float] | None = None,
) -> list[dict[str, object]]:
    grid = field_grid or [0.0, 1.0, 2.0]
    records: list[dict[str, object]] = []
    time_s = 0.0
    for field, inv_qi in zip(grid, up_values):
        records.append(
            {
                "cooldown_id": cooldown_id,
                "device_id": device_id,
                "geometry_id": geometry_id,
                "history_label": history_label,
                "branch": "up",
                "commanded_field": field,
                "calibrated_field": field,
                "elapsed_time": time_s,
                "dwell_duration": 10.0,
                "inv_qi": inv_qi,
                "fr": 5.0,
                "delta_fr_over_fr": -1.0e-7 * field,
                "T1": None,
                "witness_response": inv_qi * witness_scale,
                "bath_temperature": 0.02,
                "readout_power": -100.0,
            }
        )
        time_s += 10.0
    for field, inv_qi in zip(reversed(grid), reversed(down_values)):
        records.append(
            {
                "cooldown_id": cooldown_id,
                "device_id": device_id,
                "geometry_id": geometry_id,
                "history_label": history_label,
                "branch": "down",
                "commanded_field": field,
                "calibrated_field": field,
                "elapsed_time": time_s,
                "dwell_duration": 10.0,
                "inv_qi": inv_qi,
                "fr": 5.0,
                "delta_fr_over_fr": -1.0e-7 * field,
                "T1": None,
                "witness_response": inv_qi * witness_scale,
                "bath_temperature": 0.02,
                "readout_power": -100.0,
            }
        )
        time_s += 10.0
    for checkpoint_index in range(3):
        records.append(
            {
                "cooldown_id": cooldown_id,
                "device_id": device_id,
                "geometry_id": geometry_id,
                "history_label": history_label,
                "branch": "checkpoint",
                "commanded_field": 0.0,
                "calibrated_field": 0.0,
                "elapsed_time": time_s + checkpoint_index * 5.0,
                "dwell_duration": 5.0,
                "inv_qi": up_values[0] + checkpoint_index * 1.0e-8,
                "fr": 5.0,
                "delta_fr_over_fr": 0.0,
                "T1": None,
                "witness_response": up_values[0] * witness_scale,
                "bath_temperature": 0.02,
                "readout_power": -100.0,
            }
        )
    for sham_index in range(4):
        records.append(
            {
                "cooldown_id": cooldown_id,
                "device_id": device_id,
                "geometry_id": geometry_id,
                "history_label": "SHAM",
                "branch": "sham",
                "commanded_field": 0.0,
                "calibrated_field": 0.0,
                "elapsed_time": time_s + 20.0 + sham_index * 5.0,
                "dwell_duration": 5.0,
                "inv_qi": up_values[0] + sham_index * 1.0e-8,
                "fr": 5.0,
                "delta_fr_over_fr": 0.0,
                "T1": None,
                "witness_response": up_values[0] * witness_scale,
                "bath_temperature": 0.02,
                "readout_power": -100.0,
            }
        )
    return records


def build_payload(records: list[dict[str, object]], **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "analysis_schema_version": DEFAULT_ANALYSIS_SCHEMA_VERSION,
        "branch_slug": "e01_mm_flux_history_hysteresis",
        "primary_device_id": "device_a",
        "matched_geometry_device_ids": ["device_a", "device_b"],
        "records": records,
        "dwell_metadata": [
            {"cooldown_id": "CD-001", "converged": True, "production_dwell_t_conv": 20.0, "doubled_loop_change_fraction": 0.01},
            {"cooldown_id": "CD-002", "converged": True, "production_dwell_t_conv": 20.0, "doubled_loop_change_fraction": 0.02},
            {"cooldown_id": "CD-003", "converged": True, "production_dwell_t_conv": 20.0, "doubled_loop_change_fraction": 0.03},
        ],
    }
    payload.update(overrides)
    return payload


class AnalysisRunnerTests(unittest.TestCase):
    def test_common_field_grid_and_loop_metrics_known_case(self) -> None:
        up_records = [{"calibrated_field": 0.0}, {"calibrated_field": 2.0}, {"calibrated_field": 4.0}]
        down_records = [{"calibrated_field": 1.0}, {"calibrated_field": 2.0}, {"calibrated_field": 4.0}]
        grid = build_common_field_grid(up_records, down_records)
        self.assertEqual(grid, [1.0, 2.0, 4.0])

        metrics = compute_loop_metrics([0.0, 1.0, 2.0], [0.0, 1.0, 2.0], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(metrics["H_O"], 2.0)
        self.assertAlmostEqual(metrics["A_O"], 2.0)

    def test_sham_falsifier_kills_branch(self) -> None:
        records: list[dict[str, object]] = []
        for cooldown_id in ("CD-001", "CD-002", "CD-003"):
            records.extend(make_loop_records(cooldown_id, "device_a", "geom_a", "ZFC", [0.0, 1.0, 2.0], [2.0, 1.0, 0.0], witness_scale=0.0))
        payload = build_payload(records, matched_geometry_device_ids=[])
        summary = generate_analysis_summary(payload, BRANCH_ROOT / "analysis_outputs")
        self.assertEqual(summary["branch_disposition"], "KILL_ENTIRE_BRANCH")
        self.assertIn("SHAM_TIMING_REPRODUCES_LOOP_AREA", summary["falsifier_hits"])

    def test_witness_falsifier_kills_branch(self) -> None:
        records: list[dict[str, object]] = []
        for cooldown_id in ("CD-001", "CD-002", "CD-003"):
            records.extend(make_loop_records(cooldown_id, "device_a", "geom_a", "ZFC", [1.0, 2.0, 3.0], [0.5, 1.0, 1.5], witness_scale=1.0))
        payload = build_payload(records, matched_geometry_device_ids=[])
        summary = generate_analysis_summary(payload, BRANCH_ROOT / "analysis_outputs")
        self.assertEqual(summary["branch_disposition"], "KILL_ENTIRE_BRANCH")
        self.assertIn("PACKAGE_WITNESS_COMOVES_WITH_TARGET", summary["falsifier_hits"])

    def test_geometry_gate_failure_preserves_generic_branch(self) -> None:
        records: list[dict[str, object]] = []
        geometry_patterns = {
            "CD-001": ([0.0, 0.2, 0.4], [0.0, 0.0, 0.0], [0.0, 0.6, 1.2], [0.0, 0.0, 0.0]),
            "CD-002": ([0.0, 0.7, 1.4], [0.0, 0.0, 0.0], [0.0, 0.2, 0.4], [0.0, 0.0, 0.0]),
            "CD-003": ([0.0, 0.2, 0.4], [0.0, 0.0, 0.0], [0.0, 0.6, 1.2], [0.0, 0.0, 0.0]),
        }
        for cooldown_id, (a_up, a_down, b_up, b_down) in geometry_patterns.items():
            records.extend(make_loop_records(cooldown_id, "device_a", "geom_a", "ZFC", a_up, a_down, witness_scale=0.0))
            records.extend(make_loop_records(cooldown_id, "device_b", "geom_b", "ZFC", b_up, b_down, witness_scale=0.0))
        payload = build_payload(records)
        summary = generate_analysis_summary(payload, BRANCH_ROOT / "analysis_outputs")
        self.assertEqual(summary["branch_disposition"], "PRESERVE_GENERIC_MM_BRANCH")
        self.assertEqual(summary["vortex_status"], "DOWNGRADE_VORTEX_ONLY")
        self.assertEqual(summary["geometry_gate"]["status"], "inconsistent")

    def test_cooldown_reproducibility_failure_blocks_upgrade(self) -> None:
        records: list[dict[str, object]] = []
        records.extend(make_loop_records("CD-001", "device_a", "geom_a", "ZFC", [0.0, 0.9, 1.8], [0.3, 0.2, 0.1], witness_scale=0.0))
        records.extend(make_loop_records("CD-001", "device_a", "geom_a", "FC", [0.0, 0.4, 0.8], [0.15, 0.1, 0.05], witness_scale=0.0))
        records.extend(make_loop_records("CD-002", "device_a", "geom_a", "ZFC", [0.0, 0.3, 0.6], [0.18, 0.12, 0.06], witness_scale=0.0))
        records.extend(make_loop_records("CD-002", "device_a", "geom_a", "FC", [0.0, 1.0, 2.0], [0.35, 0.25, 0.15], witness_scale=0.0))
        records.extend(make_loop_records("CD-003", "device_a", "geom_a", "ZFC", [0.0, 0.8, 1.6], [0.25, 0.16, 0.09], witness_scale=0.0))
        records.extend(make_loop_records("CD-003", "device_a", "geom_a", "FC", [0.0, 0.5, 1.0], [0.18, 0.11, 0.06], witness_scale=0.0))
        payload = build_payload(records, matched_geometry_device_ids=[])
        summary = generate_analysis_summary(payload, BRANCH_ROOT / "analysis_outputs")
        self.assertFalse(summary["cooldown_reproducibility"]["passed"])
        self.assertEqual(summary["branch_disposition"], "PRESERVE_GENERIC_MM_BRANCH")

    def test_incomplete_inputs_fail_gate_explicitly(self) -> None:
        records = make_loop_records("CD-001", "device_a", "geom_a", "ZFC", [0.0, 0.4, 0.8], [0.0, 0.0, 0.0], witness_scale=0.0)
        records = [record for record in records if record["branch"] not in {"sham", "checkpoint"}]
        payload = build_payload(records, matched_geometry_device_ids=[], dwell_metadata=[])
        summary = generate_analysis_summary(payload, BRANCH_ROOT / "analysis_outputs")
        self.assertFalse(summary["gate_results"]["data_completeness"]["passed"])
        self.assertFalse(summary["gate_results"]["dwell_validity"]["passed"])
        self.assertIn("Sham timing control", " ".join(summary["gate_results"]["data_completeness"]["reasons"]))

    def test_cli_smoke_writes_summary_and_report(self) -> None:
        records: list[dict[str, object]] = []
        for cooldown_id in ("CD-001", "CD-002", "CD-003"):
            records.extend(make_loop_records(cooldown_id, "device_a", "geom_a", "ZFC", [0.0, 0.4, 0.8], [0.0, 0.0, 0.0], witness_scale=0.0))
        payload = build_payload(records, matched_geometry_device_ids=[])
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            input_path = temp_root / "analysis_input.json"
            output_dir = temp_root / "analysis_output"
            report_path = temp_root / "report.md"
            write_json(input_path, payload)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ANALYSIS_SCRIPT_PATH),
                    "--input",
                    str(input_path),
                    "--output-dir",
                    str(output_dir),
                    "--report-path",
                    str(report_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertIn("Wrote summary", result.stdout)
            summary = json.loads((output_dir / "summary.json").read_text(encoding="ascii"))
            self.assertIn("branch_disposition", summary)
            self.assertTrue(report_path.exists())

    def test_main_returns_zero(self) -> None:
        records: list[dict[str, object]] = []
        for cooldown_id in ("CD-001", "CD-002", "CD-003"):
            records.extend(make_loop_records(cooldown_id, "device_a", "geom_a", "ZFC", [0.0, 0.4, 0.8], [0.0, 0.0, 0.0], witness_scale=0.0))
        payload = build_payload(records, matched_geometry_device_ids=[])
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            input_path = temp_root / "analysis_input.json"
            output_dir = temp_root / "analysis_output"
            write_json(input_path, payload)
            exit_code = main(["--input", str(input_path), "--output-dir", str(output_dir)])
            self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
