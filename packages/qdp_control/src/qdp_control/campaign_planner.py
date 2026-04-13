from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from qdp_io.artifacts import dump_json, stable_hash
from .control_plane import load_latest_campaign, upsert_campaign
from tools.workflow.qdp_runtime.qdp_paths import (
    CAMPAIGN_PLAN_REPORT,
    CAMPAIGN_PREPARE_REPORT,
    MODULES,
    OUTPUTS_DIR,
    REPORTS_DIR,
    ROOT,
)
from .run_ledger import record_run


def load_json(path: Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def normalize_repo_path(path: Path | str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def output_relative_path(candidate_path: Path) -> Path | None:
    path = normalize_repo_path(candidate_path)
    try:
        return path.relative_to(OUTPUTS_DIR.resolve())
    except ValueError:
        return None


def report_name_for_candidate_name(filename: str) -> str:
    if not filename.endswith("_candidate.json"):
        raise ValueError(f"Expected candidate filename ending with '_candidate.json': {filename}")
    return filename[: -len("_candidate.json")] + "_report.json"


def candidate_is_selftest_output(candidate_path: Path) -> bool:
    relative = output_relative_path(candidate_path)
    if relative is None:
        return False
    parts = relative.parts
    return len(parts) >= 4 and parts[1] == "selftests"


def candidate_is_bootstrap_output(candidate_path: Path) -> bool:
    relative = output_relative_path(candidate_path)
    if relative is None:
        return False
    parts = relative.parts
    return len(parts) >= 4 and parts[0] == "m06" and parts[1] == "bootstrap"


def candidate_is_prepared_m12_output(candidate_path: Path) -> bool:
    relative = output_relative_path(candidate_path)
    if relative is None:
        return False
    parts = relative.parts
    return (
        len(parts) >= 4
        and parts[0] == "simulations"
        and parts[2] == "m12"
        and parts[-1].endswith("_candidate.json")
    ) or (
        len(parts) >= 3
        and parts[0] == "m12"
        and parts[1] == "prepared"
        and parts[-1].endswith("_candidate.json")
    )


def explicit_candidate_paths(candidate_paths: Iterable[Path]) -> List[Path]:
    explicit = [normalize_repo_path(path) for path in candidate_paths]
    missing = [str(path) for path in explicit if not path.exists()]
    if missing:
        detail = ", ".join(missing[:3])
        suffix = " ..." if len(missing) > 3 else ""
        raise ValueError(f"Candidate path(s) do not exist: {detail}{suffix}")
    return explicit


def candidate_is_expected_invalid_selftest(candidate_path: Path) -> bool:
    path = normalize_repo_path(candidate_path)
    relative = output_relative_path(path)
    if relative is None:
        return False
    parts = relative.parts
    if len(parts) < 4 or parts[1] != "selftests":
        return False
    module = MODULES.get(parts[0])
    if not module:
        return False
    report_path = module.get("selftest_report")
    if not isinstance(report_path, Path) or not report_path.exists():
        return False
    report = load_json(report_path)
    case_id = parts[2]
    for case in report.get("cases", []):
        if isinstance(case, dict) and case.get("case_id") == case_id and case.get("expected_valid") is False and case.get("passed", False):
            return True
    return False


def discover_source_candidates(candidate_paths: Iterable[Path], input_root: Path | None = None) -> List[Path]:
    explicit = explicit_candidate_paths(candidate_paths)
    if explicit:
        prepared = [str(path) for path in explicit if candidate_is_prepared_m12_output(path)]
        if prepared:
            detail = ", ".join(prepared[:3])
            suffix = " ..." if len(prepared) > 3 else ""
            raise ValueError(f"campaign prepare expects raw source candidates, not prepared M12 candidates: {detail}{suffix}")
        return explicit
    root = normalize_repo_path(input_root or OUTPUTS_DIR)
    if not root.exists():
        return []
    return sorted(
        path.resolve()
        for path in root.rglob("*_candidate.json")
        if path.is_file()
        and not candidate_is_expected_invalid_selftest(path)
        and not candidate_is_bootstrap_output(path)
        and not candidate_is_selftest_output(path)
        and not candidate_is_prepared_m12_output(path)
    )


def discover_prepared_candidates(candidate_paths: Iterable[Path], input_root: Path | None = None) -> List[Path]:
    explicit = explicit_candidate_paths(candidate_paths)
    if explicit:
        raw = [str(path) for path in explicit if not candidate_is_prepared_m12_output(path)]
        if raw:
            detail = ", ".join(raw[:3])
            suffix = " ..." if len(raw) > 3 else ""
            raise ValueError(
                "campaign plan requires prepared M12 candidates. "
                f"Run 'python qdp.py campaign prepare --candidate <raw-source>' first. Invalid path(s): {detail}{suffix}"
            )
        return explicit
    root = normalize_repo_path(input_root or OUTPUTS_DIR)
    if not root.exists():
        return []
    return sorted(
        path.resolve()
        for path in root.rglob("*_candidate.json")
        if path.is_file() and candidate_is_prepared_m12_output(path)
    )


def candidate_hash(candidate: Dict[str, Any]) -> str:
    return stable_hash(candidate)


def prepared_candidate_path_for_source(source_candidate_path: Path) -> Path:
    path = normalize_repo_path(source_candidate_path)
    relative = output_relative_path(path)
    if relative is None:
        raise ValueError(f"campaign prepare expects candidates under {OUTPUTS_DIR}: {path}")
    parts = relative.parts
    if len(parts) >= 4 and parts[0] == "simulations" and parts[2] != "m12":
        return OUTPUTS_DIR / "simulations" / parts[1] / "m12" / path.name
    return OUTPUTS_DIR / "m12" / "prepared" / relative


def prepared_report_path_for_source(source_candidate_path: Path) -> Path:
    path = normalize_repo_path(source_candidate_path)
    relative = output_relative_path(path)
    if relative is None:
        raise ValueError(f"campaign prepare expects candidates under {OUTPUTS_DIR}: {path}")
    parts = relative.parts
    report_name = report_name_for_candidate_name(path.name)
    if len(parts) >= 4 and parts[0] == "simulations" and parts[2] != "m12":
        return REPORTS_DIR / "simulations" / parts[1] / "m12" / report_name
    return REPORTS_DIR / "m12" / "prepared" / relative.with_name(report_name)


def prepared_report_path_for_candidate(prepared_candidate_path: Path) -> Path:
    path = normalize_repo_path(prepared_candidate_path)
    relative = output_relative_path(path)
    if relative is None:
        raise ValueError(f"Prepared candidate must live under {OUTPUTS_DIR}: {path}")
    parts = relative.parts
    report_name = report_name_for_candidate_name(path.name)
    if len(parts) >= 4 and parts[0] == "simulations" and parts[2] == "m12":
        return REPORTS_DIR / "simulations" / parts[1] / "m12" / report_name
    if len(parts) >= 3 and parts[0] == "m12" and parts[1] == "prepared":
        tail = Path(*parts[2:])
        return REPORTS_DIR / "m12" / "prepared" / tail.with_name(report_name)
    raise ValueError(f"Prepared candidate is not in a recognized M12 location: {path}")


def prepare_campaign_candidates(candidate_files: Iterable[Path], *, batch: str | None = None) -> Dict[str, Any]:
    from modules.m12_experiment_design.runner import attach_materialization_provenance, run_experiment_design

    prepared_candidates: List[Dict[str, Any]] = []
    for path in candidate_files:
        source_path = normalize_repo_path(path)
        source_candidate = load_json(source_path)
        output_candidate, report = run_experiment_design(source_candidate)
        output_path = prepared_candidate_path_for_source(source_path)
        report_path = prepared_report_path_for_source(source_path)
        report = attach_materialization_provenance(
            report,
            source_candidate_path=source_path,
            source_candidate=source_candidate,
            output_candidate_path=output_path,
            output_candidate=output_candidate,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        dump_json(output_path, output_candidate)
        dump_json(report_path, report)

        prepared_candidates.append(
            {
                "candidate_id": str(output_candidate.get("candidate_id", "") or output_path.stem),
                "source_candidate_path": str(source_path),
                "source_candidate_hash": report["source_candidate_hash"],
                "output_candidate_path": str(output_path),
                "output_candidate_hash": report["output_candidate_hash"],
                "report_path": str(report_path),
            }
        )

    summary = {
        "artifact_id": "QDP_V10_6_CAMPAIGN_PREPARE_REPORT",
        "source_candidate_count": len(prepared_candidates),
        "prepared_candidate_count": len(prepared_candidates),
        "prepared_candidates": prepared_candidates,
    }
    if batch:
        summary["batch"] = batch
    return summary


def write_prepare_report(report: Dict[str, Any], report_path: Path = CAMPAIGN_PREPARE_REPORT) -> Dict[str, Any]:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    dump_json(report_path, report)
    batch = str(report.get("batch", "") or "").strip()
    record_run(
        operation="campaign_prepare",
        lane="recovery",
        status="READY",
        summary={
            "source_candidate_count": report.get("source_candidate_count", 0),
            "prepared_candidate_count": report.get("prepared_candidate_count", 0),
            **({"batch": batch} if batch else {}),
        },
        artifacts=[report_path],
    )
    return report


def best_next_experiment(candidate: Dict[str, Any]) -> str:
    experiments = candidate.get("experiment_schedule", {}).get("priority_experiments", [])
    if isinstance(experiments, list) and experiments:
        return str(experiments[0])
    falsifier = str(candidate.get("exact_falsifier", "") or "").strip()
    if falsifier:
        return falsifier
    return "No surfaced experiment path"


def candidate_partition(candidate: Dict[str, Any]) -> str:
    schedule = candidate.get("experiment_schedule", {})
    if isinstance(schedule, dict):
        return str(schedule.get("branch_partition", "") or "")
    return ""


def candidate_route_group(candidate: Dict[str, Any]) -> str:
    schedule = candidate.get("experiment_schedule", {})
    if isinstance(schedule, dict):
        return str(schedule.get("sweep_route_group", "") or "")
    return ""


def candidate_origin(candidate_path: Path) -> str:
    if candidate_is_selftest_output(candidate_path):
        return "selftest"
    if candidate_is_bootstrap_output(candidate_path):
        return "bootstrap"
    return "operational"


def why_blocked(candidate: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if candidate.get("promotion_cap_governance"):
        reasons.append(f"promotion_cap_governance={candidate['promotion_cap_governance']}")
    if candidate.get("cross_device_status") not in {"", "CONFIRMED"}:
        reasons.append(f"cross_device_status={candidate.get('cross_device_status', '')}")
    calibration = candidate.get("calibration_status", {})
    if calibration.get("status") in {"INVALID", "PENDING_REVIEW", "UNKNOWN"}:
        reasons.append(f"calibration_status={calibration.get('status', '')}")
    dataset = candidate.get("dataset_governance", {})
    if dataset.get("status") not in {"", "COMPLETE"}:
        reasons.append(f"dataset_governance={dataset.get('status', '')}")
    return reasons or ["No surfaced blocker"]


def why_promoted(candidate: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if candidate.get("governance_outcome") == "PROCEED":
        reasons.append("governance_outcome=PROCEED")
    if candidate.get("scientific_decision") == "CROSS_DEVICE_CONFIRMED_IDENTIFIABLE":
        reasons.append("cross-device confirmation complete")
    if candidate.get("cross_device_status") == "CONFIRMED":
        reasons.append("cross_device_status=CONFIRMED")
    return reasons or ["Promotion criteria not fully met"]


def priority_score(candidate: Dict[str, Any]) -> int:
    outcome = str(candidate.get("governance_outcome", "") or "")
    science = str(candidate.get("scientific_decision", "") or "")
    cross = str(candidate.get("cross_device_status", "") or "")
    score = 0
    if outcome == "PROCEED":
        score += 100
    elif outcome == "SANDBOX_ONLY":
        score += 70
    elif outcome == "DEFER":
        score += 50
    if science == "CROSS_DEVICE_CONFIRMED_IDENTIFIABLE":
        score += 25
    elif science == "PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST":
        score += 20
    if cross in {"SCHEDULED", "DEVICE_SPECIFIC", "INCONSISTENT"}:
        score += 10
    if candidate.get("exact_falsifier"):
        score += 5
    return score


def candidate_key(candidate_path: Path, candidate: Dict[str, Any]) -> str:
    cid = str(candidate.get("candidate_id", "") or candidate_path.stem)
    try:
        relative = normalize_repo_path(candidate_path).relative_to(ROOT.resolve())
        suffix = str(relative.with_suffix("")).replace("\\", "/")
    except ValueError:
        suffix = candidate_path.stem
    return f"{cid}@{suffix}"


def required_report_value(report: Dict[str, Any], field: str, *, report_path: Path) -> str:
    value = str(report.get(field, "") or "").strip()
    if not value:
        raise ValueError(f"Prepared M12 report is missing '{field}': {report_path}")
    return value


def load_prepared_candidate_bundle(candidate_path: Path) -> Dict[str, Any]:
    prepared_path = normalize_repo_path(candidate_path)
    if not candidate_is_prepared_m12_output(prepared_path):
        raise ValueError(
            "campaign plan requires prepared M12 candidates. "
            f"Run 'python qdp.py campaign prepare --candidate {prepared_path}' first."
        )

    candidate = load_json(prepared_path)
    report_path = prepared_report_path_for_candidate(prepared_path)
    if not report_path.exists():
        raise ValueError(
            "Prepared M12 report is missing for campaign planning input. "
            f"Rerun 'python qdp.py campaign prepare --candidate {prepared_path}'."
        )
    report = load_json(report_path)
    source_path = normalize_repo_path(required_report_value(report, "source_candidate_path", report_path=report_path))
    if not source_path.exists():
        raise ValueError(
            "Prepared M12 report points to a missing source candidate. "
            f"Rerun 'python qdp.py campaign prepare --candidate {source_path}'."
        )
    source_candidate = load_json(source_path)
    source_digest = candidate_hash(source_candidate)
    expected_source_digest = required_report_value(report, "source_candidate_hash", report_path=report_path)
    if source_digest != expected_source_digest:
        raise ValueError(
            "Prepared M12 candidate is stale relative to its source candidate. "
            f"Rerun 'python qdp.py campaign prepare --candidate {source_path}'."
        )

    expected_output_path = normalize_repo_path(required_report_value(report, "output_candidate_path", report_path=report_path))
    if expected_output_path != prepared_path:
        raise ValueError(
            "Prepared M12 report output path does not match the planning input. "
            f"Expected {expected_output_path}, found {prepared_path}."
        )

    output_digest = candidate_hash(candidate)
    expected_output_digest = required_report_value(report, "output_candidate_hash", report_path=report_path)
    if output_digest != expected_output_digest:
        raise ValueError(
            "Prepared M12 candidate hash does not match its report provenance. "
            f"Rerun 'python qdp.py campaign prepare --candidate {source_path}'."
        )

    return {
        "candidate": candidate,
        "candidate_path": prepared_path,
        "candidate_hash": output_digest,
        "report_path": report_path,
        "source_candidate_path": source_path,
        "source_candidate_hash": source_digest,
    }


def validate_prepared_scan_coverage(prepared_candidate_files: Iterable[Path], input_root: Path | None = None) -> None:
    source_candidates = discover_source_candidates([], input_root)
    if not source_candidates:
        return
    prepared_source_paths = {
        load_prepared_candidate_bundle(path)["source_candidate_path"] for path in prepared_candidate_files
    }
    missing = [str(path) for path in source_candidates if normalize_repo_path(path) not in prepared_source_paths]
    if missing:
        root = normalize_repo_path(input_root or OUTPUTS_DIR)
        detail = ", ".join(missing[:3])
        suffix = " ..." if len(missing) > 3 else ""
        raise ValueError(
            "Missing prepared M12 candidates for one or more campaign source candidates. "
            f"Run 'python qdp.py campaign prepare --input-root {root}'. Missing: {detail}{suffix}"
        )


def build_campaign_plan(candidate_files: Iterable[Path], *, budget: int = 5, batch: str | None = None) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    previous = load_latest_campaign()
    previous_summary = previous.get("summary", {})
    previous_hashes_by_key = previous_summary.get("candidate_hashes_by_key", {})
    if not isinstance(previous_hashes_by_key, dict):
        previous_hashes_by_key = {}
    previous_hashes_by_id = previous_summary.get("candidate_hashes", {})
    if not isinstance(previous_hashes_by_id, dict):
        previous_hashes_by_id = {}
    seen_variants: set[tuple[str, str]] = set()
    for path in candidate_files:
        bundle = load_prepared_candidate_bundle(path)
        prepared_candidate_path = bundle["candidate_path"]
        source_candidate_path = bundle["source_candidate_path"]
        candidate = bundle["candidate"]
        cid = str(candidate.get("candidate_id", "") or prepared_candidate_path.stem)
        digest = str(bundle["candidate_hash"])
        variant_key = (cid, digest)
        if variant_key in seen_variants:
            continue
        seen_variants.add(variant_key)
        key = candidate_key(source_candidate_path, candidate)
        previous_digest = previous_hashes_by_key.get(key, previous_hashes_by_id.get(cid))
        candidates.append(
            {
                "candidate_key": key,
                "candidate_id": cid,
                "branch_or_model_tag": candidate.get("branch_or_model_tag", ""),
                "candidate_path": str(prepared_candidate_path),
                "source_candidate_path": str(source_candidate_path),
                "source_candidate_hash": str(bundle["source_candidate_hash"]),
                "candidate_origin": candidate_origin(source_candidate_path),
                "candidate_hash": digest,
                "governance_outcome": candidate.get("governance_outcome", ""),
                "scientific_decision": candidate.get("scientific_decision", ""),
                "cross_device_status": candidate.get("cross_device_status", ""),
                "branch_partition": candidate_partition(candidate),
                "sweep_route_group": candidate_route_group(candidate),
                "best_next_experiment": best_next_experiment(candidate),
                "why_blocked": why_blocked(candidate),
                "why_promoted": why_promoted(candidate),
                "priority_score": priority_score(candidate),
                "what_changed_since_last_run": "new_candidate"
                if previous_digest is None
                else ("artifact_hash_changed" if previous_digest != digest else "unchanged"),
            }
        )
    ranked = sorted(candidates, key=lambda item: (-item["priority_score"], item["candidate_key"]))
    input_hash = stable_hash({item["candidate_key"]: item["candidate_hash"] for item in ranked})
    candidate_hashes: Dict[str, str] = {}
    candidate_variants_by_id: Dict[str, List[str]] = {}
    blocked_candidates: Dict[str, List[str]] = {}
    promotion_ready_candidates: List[str] = []
    for item in ranked:
        candidate_hashes.setdefault(item["candidate_id"], item["candidate_hash"])
        candidate_variants_by_id.setdefault(item["candidate_id"], []).append(item["candidate_key"])
        if item["governance_outcome"] == "PROCEED":
            if item["candidate_id"] not in promotion_ready_candidates:
                promotion_ready_candidates.append(item["candidate_id"])
        else:
            blocked_candidates.setdefault(item["candidate_id"], item["why_blocked"])
    report = {
        "artifact_id": "QDP_V10_6_CAMPAIGN_PLAN",
        "campaign_id": f"QDPCAM-{input_hash[:16].upper()}",
        "budgeted_slots": budget,
        "candidate_count": len(ranked),
        "candidate_hashes": candidate_hashes,
        "candidate_hashes_by_key": {item["candidate_key"]: item["candidate_hash"] for item in ranked},
        "ranked_candidates": ranked,
        "selected_candidates": ranked[: max(0, budget)],
        "summary": {
            "best_next_experiment": ranked[0]["best_next_experiment"] if ranked else "",
            "promotion_ready_candidates": promotion_ready_candidates,
            "promotion_ready_candidate_keys": [item["candidate_key"] for item in ranked if item["governance_outcome"] == "PROCEED"],
            "blocked_candidates": blocked_candidates,
            "blocked_candidates_by_key": {item["candidate_key"]: item["why_blocked"] for item in ranked if item["governance_outcome"] != "PROCEED"},
            "candidate_variants_by_id": candidate_variants_by_id,
            "variant_count_by_candidate_id": {candidate_id: len(keys) for candidate_id, keys in candidate_variants_by_id.items()},
            "candidate_ids_with_multiple_variants": sorted(
                candidate_id for candidate_id, keys in candidate_variants_by_id.items() if len(keys) > 1
            ),
        },
    }
    if batch:
        report["batch"] = batch
    return report


def prepare_campaign(candidate_paths: Iterable[Path], input_root: Path | None = None, *, batch: str | None = None) -> Dict[str, Any]:
    explicit = list(candidate_paths)
    candidates = discover_source_candidates(explicit, input_root)
    return prepare_campaign_candidates(candidates, batch=batch)


def plan_campaign(
    candidate_paths: Iterable[Path],
    input_root: Path | None = None,
    *,
    budget: int = 5,
    batch: str | None = None,
) -> Dict[str, Any]:
    explicit = list(candidate_paths)
    candidates = discover_prepared_candidates(explicit, input_root)
    if not explicit:
        validate_prepared_scan_coverage(candidates, input_root)
    return build_campaign_plan(candidates, budget=budget, batch=batch)


def write_campaign_plan(report: Dict[str, Any], report_path: Path = CAMPAIGN_PLAN_REPORT) -> Dict[str, Any]:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    dump_json(report_path, report)
    batch = str(report.get("batch", "") or "").strip()
    upsert_campaign(
        {
            "campaign_id": report["campaign_id"],
            "status": "READY",
            "input_hash": stable_hash(report.get("candidate_hashes_by_key", {})),
            "report_path": str(report_path),
            "summary": report,
        }
    )
    record_run(
        operation="campaign_plan",
        lane="recovery",
        status="READY",
        summary={
            "campaign_id": report["campaign_id"],
            "candidate_count": report["candidate_count"],
            "selected_count": len(report.get("selected_candidates", [])),
            **({"batch": batch} if batch else {}),
        },
        artifacts=[report_path],
    )
    return report
