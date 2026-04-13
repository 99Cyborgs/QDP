from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
QDP_CONTROL_SRC = ROOT / "packages" / "qdp_control" / "src"
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_VALIDATION_SRC = ROOT / "packages" / "qdp_validation" / "src"

for path in (QDP_CONTROL_SRC, QDP_IO_SRC, QDP_VALIDATION_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_m12():
    return load_module("qdp_m12_branch_sweep_test", ROOT / "modules" / "m12_experiment_design" / "runner.py")


def load_lab_workflows():
    return importlib.reload(importlib.import_module("qdp_control.lab_workflows"))


def load_campaign_planner():
    return importlib.reload(importlib.import_module("qdp_control.campaign_planner"))


def make_candidate(m12, overrides: dict) -> dict:
    base_template = m12.load_json(m12.DEFAULT_BASE_TEMPLATE)
    candidate = m12.make_minimal_final_candidate(base_template)
    return m12.deep_merge(candidate, overrides)


def patch_planner_paths(planner, monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    outputs_root = tmp_path / "outputs"
    reports_root = tmp_path / "reports"
    monkeypatch.setattr(planner, "ROOT", tmp_path)
    monkeypatch.setattr(planner, "OUTPUTS_DIR", outputs_root)
    monkeypatch.setattr(planner, "REPORTS_DIR", reports_root)
    monkeypatch.setattr(planner, "CAMPAIGN_PREPARE_REPORT", reports_root / "campaigns" / "latest_prepare.json")
    monkeypatch.setattr(planner, "CAMPAIGN_PLAN_REPORT", reports_root / "campaigns" / "latest_plan.json")
    return outputs_root, reports_root


def copy_candidate_to_tmp(relative_source: str, destination: Path) -> Path:
    source_path = ROOT / relative_source
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def test_m12_generates_branch_specific_vortex_sweep() -> None:
    m12 = load_m12()
    candidate = make_candidate(
        m12,
        {
            "candidate_id": "m09-case-vortex",
            "branch_or_model_tag": "M09_CASE_VORTEX",
            "assigned_family_class": "METASTABLE_CONFIGURATION_MEMORY",
            "strongest_competing_mechanism": "VORTEX",
            "signature_matches": ["HYSTERESIS", "CONSISTENT_IMPEDANCE_RATIO"],
            "evaluation_notes": [
                "Bcool history, ZFC versus FC, and repeated field loop hysteresis index all track the loss shift."
            ],
        },
    )

    candidate, _ = m12.run_experiment_design(candidate)

    assert candidate["experiment_schedule"]["priority_experiments"][0].startswith("Vortex discriminant sweep")
    assert candidate["experiment_schedule"]["sweep_route_group"] == "VORTEX"
    assert candidate["experiment_schedule"]["branch_partition"] == "mechanism_discrimination"
    assert candidate["tested_parameter_ranges"]["field_history_tag"] == ["ZFC", "FC", "UP_LOOP", "DOWN_LOOP"]
    assert candidate["simulation_conditions"]["owner_route"] == "VORTEX"
    assert candidate["exact_falsifier"].startswith("If the vortex branch is real")


def test_m12_backfills_cross_device_priority_and_devices() -> None:
    m12 = load_m12()
    candidate_path = (
        ROOT
        / "artifacts"
        / "outputs"
        / "m06"
        / "bootstrap"
        / "run_1"
        / "CASE_7_CONFIRMED_READY_BRANCH"
        / "CASE_7_CONFIRMED_READY_BRANCH_candidate.json"
    )
    candidate = m12.load_json(candidate_path)

    candidate, _ = m12.run_experiment_design(candidate)

    assert candidate["experiment_schedule"]["priority_experiments"] == ["Cross-device matched-fabrication sweep"]
    assert candidate["experiment_schedule"]["sweep_route_group"] == "CROSS_DEVICE_CONFIRMATION"
    assert candidate["experiment_schedule"]["branch_partition"] == "cross_device_confirmation"
    assert candidate["candidate_target_devices"] == ["DEV_A", "DEV_B"]
    assert candidate["exact_falsifier"] == "Confirmed matched-fabrication sweeps must preserve the discriminant ordering."


def test_lab_pack_preserves_non_empty_priority_experiment(tmp_path: Path, monkeypatch) -> None:
    m12 = load_m12()
    lab = load_lab_workflows()
    candidate_path = (
        ROOT
        / "artifacts"
        / "outputs"
        / "m06"
        / "bootstrap"
        / "run_1"
        / "CASE_7_CONFIRMED_READY_BRANCH"
        / "CASE_7_CONFIRMED_READY_BRANCH_candidate.json"
    )
    candidate = m12.load_json(candidate_path)
    candidate, _ = m12.run_experiment_design(candidate)

    updated_candidate_path = tmp_path / "m06_case_7_candidate.json"
    updated_candidate_path.write_text(json.dumps(candidate, indent=2), encoding="utf-8")

    monkeypatch.setattr(lab, "LAB_REQUEST_REPORT", tmp_path / "lab_request_report.json")
    monkeypatch.setattr(lab, "upsert_lab_request", lambda payload: None)
    monkeypatch.setattr(lab, "record_run", lambda **kwargs: None)

    instrument_profile = lab.default_instrument_profile(candidate)
    packed = lab.pack_lab_request(
        candidate_path=updated_candidate_path,
        candidate=candidate,
        lane="recovery",
        instrument_profile=instrument_profile,
        output_dir=tmp_path / "lab_requests",
    )

    request_pack = packed["request_pack"]
    assert instrument_profile["device_ids"] == ["DEV_A", "DEV_B"]
    assert request_pack["priority_experiments"] == ["Cross-device matched-fabrication sweep"]
    assert request_pack["candidate_target_devices"] == ["DEV_A", "DEV_B"]


def test_discover_source_candidates_excludes_prepared_and_bootstrap_but_keeps_explicit_bootstrap_paths(
    tmp_path: Path, monkeypatch
) -> None:
    planner = load_campaign_planner()
    outputs_root, _reports_root = patch_planner_paths(planner, monkeypatch, tmp_path)
    bootstrap_path = (
        outputs_root
        / "m06"
        / "bootstrap"
        / "run_1"
        / "CASE_7_CONFIRMED_READY_BRANCH"
        / "CASE_7_CONFIRMED_READY_BRANCH_candidate.json"
    )
    selftest_path = outputs_root / "m12" / "selftests" / "CASE_SELFTEST" / "CASE_SELFTEST_candidate.json"
    prepared_path = outputs_root / "m12" / "prepared" / "m05" / "run_1" / "prepared_candidate.json"
    operational_path = outputs_root / "m05" / "run_1" / "OPERATIONAL_BRANCH_candidate.json"
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    selftest_path.parent.mkdir(parents=True, exist_ok=True)
    prepared_path.parent.mkdir(parents=True, exist_ok=True)
    operational_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text(json.dumps({"candidate_id": "bootstrap-case"}), encoding="utf-8")
    selftest_path.write_text(json.dumps({"candidate_id": "selftest-case"}), encoding="utf-8")
    prepared_path.write_text(json.dumps({"candidate_id": "prepared-case"}), encoding="utf-8")
    operational_path.write_text(json.dumps({"candidate_id": "operational-case"}), encoding="utf-8")

    discovered = planner.discover_source_candidates([], outputs_root)
    explicit = planner.discover_source_candidates([bootstrap_path], outputs_root)

    assert bootstrap_path.resolve() not in discovered
    assert selftest_path.resolve() not in discovered
    assert prepared_path.resolve() not in discovered
    assert operational_path.resolve() in discovered
    assert explicit == [bootstrap_path.resolve()]


def test_prepare_campaign_materializes_simulation_candidates_and_report(tmp_path: Path, monkeypatch) -> None:
    planner = load_campaign_planner()
    outputs_root, reports_root = patch_planner_paths(planner, monkeypatch, tmp_path)
    batch = "sim_smoke_20260317"
    source_path = copy_candidate_to_tmp(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/confirmed_ready_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "confirmed_ready_candidate.json",
    )

    report = planner.prepare_campaign([], outputs_root, batch=batch)

    prepared_candidate_path = outputs_root / "simulations" / batch / "m12" / "confirmed_ready_candidate.json"
    prepared_report_path = reports_root / "simulations" / batch / "m12" / "confirmed_ready_report.json"
    prepared_candidate = planner.load_json(prepared_candidate_path)
    prepared_report = planner.load_json(prepared_report_path)

    assert report["prepared_candidate_count"] == 1
    assert prepared_candidate_path.exists()
    assert prepared_report_path.exists()
    assert prepared_report["source_candidate_path"] == str(source_path.resolve())
    assert prepared_report["source_candidate_hash"] == planner.candidate_hash(planner.load_json(source_path))
    assert prepared_report["output_candidate_path"] == str(prepared_candidate_path.resolve())
    assert prepared_report["output_candidate_hash"] == planner.candidate_hash(prepared_candidate)


def test_campaign_plan_consumes_prepared_candidates_with_source_lineage(tmp_path: Path, monkeypatch) -> None:
    planner = load_campaign_planner()
    outputs_root, _reports_root = patch_planner_paths(planner, monkeypatch, tmp_path)
    batch = "sim_smoke_20260317"
    confirmed_ready_source = copy_candidate_to_tmp(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/confirmed_ready_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "confirmed_ready_candidate.json",
    )
    copy_candidate_to_tmp(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/scheduled_cross_device_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "scheduled_cross_device_candidate.json",
    )
    copy_candidate_to_tmp(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/baseline_reject_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "baseline_reject_candidate.json",
    )

    planner.prepare_campaign([], outputs_root, batch=batch)
    monkeypatch.setattr(planner, "load_latest_campaign", lambda: {})

    report = planner.plan_campaign([], outputs_root, budget=5, batch=batch)
    ranked_by_id = {item["candidate_id"]: item for item in report["ranked_candidates"]}
    confirmed_ready = ranked_by_id["m06-case-7"]
    prepared_candidate_path = outputs_root / "simulations" / batch / "m12" / "confirmed_ready_candidate.json"
    prepared_candidate = planner.load_json(prepared_candidate_path)

    assert confirmed_ready["candidate_origin"] == "operational"
    assert confirmed_ready["candidate_path"] == str(prepared_candidate_path.resolve())
    assert confirmed_ready["source_candidate_path"] == str(confirmed_ready_source.resolve())
    assert confirmed_ready["source_candidate_hash"] == planner.candidate_hash(planner.load_json(confirmed_ready_source))
    assert confirmed_ready["candidate_hash"] == planner.candidate_hash(prepared_candidate)
    assert confirmed_ready["candidate_key"].endswith("simulations/sim_smoke_20260317/m05/confirmed_ready_candidate")
    assert confirmed_ready["branch_partition"] == "cross_device_confirmation"
    assert confirmed_ready["sweep_route_group"] == "CROSS_DEVICE_CONFIRMATION"
    assert confirmed_ready["best_next_experiment"] == "Cross-device matched-fabrication sweep"


def test_campaign_plan_fails_on_missing_prepared_report(tmp_path: Path, monkeypatch) -> None:
    planner = load_campaign_planner()
    outputs_root, reports_root = patch_planner_paths(planner, monkeypatch, tmp_path)
    batch = "sim_smoke_20260317"
    copy_candidate_to_tmp(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/confirmed_ready_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "confirmed_ready_candidate.json",
    )

    planner.prepare_campaign([], outputs_root, batch=batch)
    prepared_report_path = reports_root / "simulations" / batch / "m12" / "confirmed_ready_report.json"
    prepared_report_path.unlink()

    with pytest.raises(ValueError, match="Prepared M12 report is missing"):
        planner.plan_campaign([], outputs_root, batch=batch)


def test_campaign_plan_fails_on_stale_source_materialization(tmp_path: Path, monkeypatch) -> None:
    planner = load_campaign_planner()
    outputs_root, _reports_root = patch_planner_paths(planner, monkeypatch, tmp_path)
    batch = "sim_smoke_20260317"
    source_path = copy_candidate_to_tmp(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/confirmed_ready_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "confirmed_ready_candidate.json",
    )

    planner.prepare_campaign([], outputs_root, batch=batch)
    stale_candidate = planner.load_json(source_path)
    stale_candidate["campaign_stale_marker"] = True
    source_path.write_text(json.dumps(stale_candidate, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="stale relative to its source candidate"):
        planner.plan_campaign([], outputs_root, batch=batch)


def test_campaign_plan_rejects_explicit_raw_source_candidates(tmp_path: Path, monkeypatch) -> None:
    planner = load_campaign_planner()
    outputs_root, _reports_root = patch_planner_paths(planner, monkeypatch, tmp_path)
    batch = "sim_smoke_20260317"
    source_path = copy_candidate_to_tmp(
        "artifacts/outputs/simulations/sim_smoke_20260317/m05/confirmed_ready_candidate.json",
        outputs_root / "simulations" / batch / "m05" / "confirmed_ready_candidate.json",
    )

    with pytest.raises(ValueError, match="campaign plan requires prepared M12 candidates"):
        planner.plan_campaign([source_path], outputs_root, batch=batch)
