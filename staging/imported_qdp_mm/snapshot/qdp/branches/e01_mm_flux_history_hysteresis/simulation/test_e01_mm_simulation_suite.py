from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from simulation.e01_mm_simulation_suite import (
    DEFAULT_SEED,
    compute_loop_metrics,
    generate_suite,
    write_proposal_appendix,
    write_suite_outputs,
)


class SimulationSuiteTests(unittest.TestCase):
    def test_compute_loop_metrics_known_case(self) -> None:
        metrics = compute_loop_metrics([0.0, 1.0, 2.0], [0.0, 1.0, 2.0], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(metrics["H_O"], 2.0)
        self.assertAlmostEqual(metrics["A_O"], 2.0)

    def test_generate_suite_has_all_cases(self) -> None:
        suite = generate_suite(DEFAULT_SEED)
        self.assertEqual(
            set(suite["cases"].keys()),
            {
                "memoryless_field_loss_with_drift",
                "generic_hidden_state_hysteresis",
                "qp_lag_after_field_step",
                "fabrication_noise_false_geometry_signal",
                "package_common_mode_drift",
            },
        )

    def test_hidden_state_case_has_three_cooldowns(self) -> None:
        suite = generate_suite(DEFAULT_SEED)
        case = suite["cases"]["generic_hidden_state_hysteresis"]
        self.assertEqual(len(case["cooldowns"]), 3)
        self.assertGreater(case["summary"]["mean_H_O"], 0.0)

    def test_write_suite_outputs_emits_summary_and_case_files(self) -> None:
        suite = generate_suite(DEFAULT_SEED)
        with tempfile.TemporaryDirectory() as temporary_directory:
            written_paths = write_suite_outputs(Path(temporary_directory), suite)
            self.assertEqual(len(written_paths), 6)

            summary_path = Path(temporary_directory) / "summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="ascii"))
            self.assertEqual(summary["case_count"], 5)

            case_path = Path(temporary_directory) / "package_common_mode_drift.json"
            self.assertTrue(case_path.exists())
            payload = json.loads(case_path.read_text(encoding="ascii"))
            self.assertIn("target_witness_correlation", payload)

    def test_write_proposal_appendix_emits_markdown_summary(self) -> None:
        suite = generate_suite(DEFAULT_SEED)
        with tempfile.TemporaryDirectory() as temporary_directory:
            appendix_path = Path(temporary_directory) / "appendix.md"
            write_proposal_appendix(appendix_path, suite)
            self.assertTrue(appendix_path.exists())
            appendix_text = appendix_path.read_text(encoding="ascii")
            self.assertIn("# E01 MM Simulation Appendix", appendix_text)
            self.assertIn("memoryless_field_loss_with_drift", appendix_text)
            self.assertIn("package_common_mode_drift", appendix_text)


if __name__ == "__main__":
    unittest.main()
