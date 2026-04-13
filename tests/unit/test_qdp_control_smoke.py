from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QDP_CONTROL_SRC = ROOT / "packages" / "qdp_control" / "src"
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_VALIDATION_SRC = ROOT / "packages" / "qdp_validation" / "src"

for path in (QDP_CONTROL_SRC, QDP_IO_SRC, QDP_VALIDATION_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qdp_control import campaign_planner, control_plane, lab_workflows, queue


def test_make_queue_id_is_stable() -> None:
    payload = {"lane": "recovery", "outputs_root": "artifacts/outputs"}

    first = queue.make_queue_id(manifest_id="manifest-a", job_id="job-1", job_type="check", payload=payload)
    second = queue.make_queue_id(manifest_id="manifest-a", job_id="job-1", job_type="check", payload=payload)

    assert first == second
    assert first.startswith("QDPQUE-")


def test_control_plane_round_trip_queue_item(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "control_plane.sqlite3"
    control_plane.insert_queue_item(
        {
            "queue_id": "QDPQUE-SMOKE00000001",
            "job_type": "check",
            "job_payload": {"lane": "recovery"},
            "state": "QUEUED",
            "priority": 100,
            "attempt_count": 0,
            "max_attempts": 3,
        },
        db_path=db_path,
    )

    item = control_plane.get_queue_item("QDPQUE-SMOKE00000001", db_path=db_path)

    assert item["queue_id"] == "QDPQUE-SMOKE00000001"
    assert item["state"] == "QUEUED"
    assert item["job_type"] == "check"


def test_control_helpers_cover_campaign_and_lab_defaults() -> None:
    assert campaign_planner.report_name_for_candidate_name("example_candidate.json") == "example_report.json"

    profile = lab_workflows.default_instrument_profile(
        {
            "candidate_id": "case-1",
            "cross_device_validation": {"devices_tested": ["DEV_A", "DEV_B"]},
            "experiment_schedule": {"priority_experiments": ["Cross-device matched-fabrication sweep"]},
        }
    )

    assert profile["device_ids"] == ["DEV_A", "DEV_B"]
    assert profile["supported_measurements"] == ["Cross-device matched-fabrication sweep"]
