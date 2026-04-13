from __future__ import annotations

import argparse
import json
import math
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_ANALYSIS_SCHEMA_VERSION = "1.0.0"
PLOT_FILENAMES = {
    "raw_inv_qi_by_history": "plot_01_raw_inv_qi_by_history.png",
    "drift_corrected_inv_qi": "plot_02_drift_corrected_inv_qi.png",
    "delta_fr_over_fr": "plot_03_delta_fr_over_fr.png",
    "selected_field_t1": "plot_04_selected_field_t1.png",
    "loop_metrics": "plot_05_loop_metrics.png",
    "target_vs_witness": "plot_06_target_vs_witness.png",
    "geometry_summary": "plot_07_geometry_summary.png",
    "held_out_residuals": "plot_08_held_out_residuals.png",
}
RECORD_REQUIRED_FIELDS = (
    "cooldown_id",
    "device_id",
    "geometry_id",
    "history_label",
    "branch",
    "commanded_field",
    "calibrated_field",
    "elapsed_time",
    "dwell_duration",
    "inv_qi",
    "fr",
    "delta_fr_over_fr",
    "bath_temperature",
    "readout_power",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="ascii"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")


def round_value(value: float, digits: int = 12) -> float:
    return round(float(value), digits)


def trapz(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys):
        raise ValueError("trapz requires equal-length inputs.")
    if len(xs) < 2:
        raise ValueError("trapz requires at least two samples.")
    total = 0.0
    for index in range(1, len(xs)):
        total += 0.5 * (ys[index - 1] + ys[index]) * (xs[index] - xs[index - 1])
    return total


def compute_loop_metrics(field_grid: list[float], up_branch: list[float], down_branch: list[float]) -> dict[str, float]:
    if len(field_grid) != len(up_branch) or len(field_grid) != len(down_branch):
        raise ValueError("Loop metrics require equal-length field and branch arrays.")
    signed_difference = [up_value - down_value for up_value, down_value in zip(up_branch, down_branch)]
    absolute_difference = [abs(value) for value in signed_difference]
    return {
        "H_O": trapz(field_grid, absolute_difference),
        "A_O": trapz(field_grid, signed_difference),
    }


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def ensure_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_correlation(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys):
        raise ValueError("Correlation requires equal-length inputs.")
    if len(xs) < 2:
        return 0.0
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    covariance = sum((x_value - x_mean) * (y_value - y_mean) for x_value, y_value in zip(xs, ys))
    x_variance = sum((x_value - x_mean) ** 2 for x_value in xs)
    y_variance = sum((y_value - y_mean) ** 2 for y_value in ys)
    if x_variance <= 0.0 or y_variance <= 0.0:
        return 0.0
    return covariance / math.sqrt(x_variance * y_variance)


def linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    if len(xs) != len(ys):
        raise ValueError("linear_fit requires equal-length inputs.")
    if len(xs) < 2:
        return 0.0, ys[0] if ys else 0.0, 0.0
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((x_value - x_mean) ** 2 for x_value in xs)
    if denominator <= 0.0:
        return 0.0, y_mean, 0.0
    slope = sum((x_value - x_mean) * (y_value - y_mean) for x_value, y_value in zip(xs, ys)) / denominator
    intercept = y_mean - slope * x_mean
    predictions = [slope * value + intercept for value in xs]
    residuals = [actual - predicted for actual, predicted in zip(ys, predictions)]
    residual_scale = math.sqrt(sum(value * value for value in residuals) / len(residuals))
    return slope, intercept, residual_scale


def interpolate_series(xs: list[float], ys: list[float], grid: list[float]) -> list[float]:
    if len(xs) != len(ys):
        raise ValueError("Interpolation requires equal-length inputs.")
    if len(xs) < 2:
        raise ValueError("Interpolation requires at least two source points.")
    interpolated: list[float] = []
    for field in grid:
        index = bisect_left(xs, field)
        if index < len(xs) and xs[index] == field:
            interpolated.append(ys[index])
            continue
        if index == 0 or index >= len(xs):
            raise ValueError("Interpolation grid extends outside the source domain.")
        left_x = xs[index - 1]
        right_x = xs[index]
        left_y = ys[index - 1]
        right_y = ys[index]
        weight = (field - left_x) / (right_x - left_x)
        interpolated.append(left_y + weight * (right_y - left_y))
    return interpolated


def serialise_float_list(values: list[float]) -> list[float]:
    return [round_value(value) for value in values]


def normalise_record(record: dict[str, Any], index: int) -> dict[str, Any]:
    missing_fields = [field_name for field_name in RECORD_REQUIRED_FIELDS if field_name not in record]
    if missing_fields:
        raise ValueError(f"Record {index} is missing required fields: {', '.join(missing_fields)}")
    return {
        "cooldown_id": str(record["cooldown_id"]),
        "device_id": str(record["device_id"]),
        "geometry_id": str(record["geometry_id"]),
        "history_label": str(record["history_label"]),
        "branch": str(record["branch"]).lower(),
        "commanded_field": float(record["commanded_field"]),
        "calibrated_field": float(record["calibrated_field"]),
        "elapsed_time": float(record["elapsed_time"]),
        "dwell_duration": float(record["dwell_duration"]),
        "inv_qi": float(record["inv_qi"]),
        "fr": float(record["fr"]),
        "delta_fr_over_fr": float(record["delta_fr_over_fr"]),
        "T1": None if record.get("T1") is None else float(record["T1"]),
        "witness_response": None if record.get("witness_response") is None else float(record["witness_response"]),
        "bath_temperature": float(record["bath_temperature"]),
        "readout_power": float(record["readout_power"]),
    }


def select_primary_device(records: list[dict[str, Any]], preferred_device_id: str | None) -> str | None:
    device_counts: dict[str, int] = defaultdict(int)
    for record in records:
        if record["branch"] in {"up", "down"}:
            device_counts[record["device_id"]] += 1
    if preferred_device_id and preferred_device_id in device_counts:
        return preferred_device_id
    if not device_counts:
        return preferred_device_id
    return sorted(device_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def build_common_field_grid(up_records: list[dict[str, Any]], down_records: list[dict[str, Any]]) -> list[float]:
    up_fields = sorted({record["calibrated_field"] for record in up_records})
    down_fields = sorted({record["calibrated_field"] for record in down_records})
    if len(up_fields) < 2 or len(down_fields) < 2:
        raise ValueError("Both branches need at least two field points.")
    minimum = max(min(up_fields), min(down_fields))
    maximum = min(max(up_fields), max(down_fields))
    if minimum >= maximum:
        raise ValueError("Branch field domains do not overlap.")
    grid = sorted({field for field in up_fields + down_fields if minimum <= field <= maximum})
    if len(grid) < 2:
        raise ValueError("The common field grid must contain at least two points.")
    return grid


def fit_checkpoint_drift(checkpoint_records: list[dict[str, Any]]) -> dict[str, Any] | None:
    usable = [record for record in checkpoint_records if record["calibrated_field"] == 0.0]
    if len(usable) < 2:
        return None
    usable = sorted(usable, key=lambda record: record["elapsed_time"])
    times = [record["elapsed_time"] for record in usable]
    values = [record["inv_qi"] for record in usable]
    slope, intercept, residual_scale = linear_fit(times, values)
    baseline = slope * times[0] + intercept
    return {
        "slope": slope,
        "intercept": intercept,
        "baseline_at_first_checkpoint": baseline,
        "residual_scale": residual_scale,
        "checkpoint_count": len(usable),
    }


def apply_drift_correction(records: list[dict[str, Any]], drift_model: dict[str, Any] | None) -> list[float]:
    corrected: list[float] = []
    for record in records:
        if drift_model is None:
            corrected.append(record["inv_qi"])
            continue
        drift = drift_model["slope"] * record["elapsed_time"] + drift_model["intercept"]
        corrected.append(record["inv_qi"] - (drift - drift_model["baseline_at_first_checkpoint"]))
    return corrected


def compute_loop_payload(
    records: list[dict[str, Any]],
    cooldown_id: str,
    device_id: str,
    history_label: str,
    checkpoint_records: list[dict[str, Any]],
) -> dict[str, Any] | None:
    loop_records = [
        record
        for record in records
        if record["cooldown_id"] == cooldown_id
        and record["device_id"] == device_id
        and record["history_label"] == history_label
    ]
    up_records = sorted((record for record in loop_records if record["branch"] == "up"), key=lambda record: record["calibrated_field"])
    down_records = sorted((record for record in loop_records if record["branch"] == "down"), key=lambda record: record["calibrated_field"])
    if len(up_records) < 2 or len(down_records) < 2:
        return None

    field_grid = build_common_field_grid(up_records, down_records)
    up_inv_qi = interpolate_series(
        [record["calibrated_field"] for record in up_records],
        [record["inv_qi"] for record in up_records],
        field_grid,
    )
    down_inv_qi = interpolate_series(
        [record["calibrated_field"] for record in down_records],
        [record["inv_qi"] for record in down_records],
        field_grid,
    )
    up_delta_fr = interpolate_series(
        [record["calibrated_field"] for record in up_records],
        [record["delta_fr_over_fr"] for record in up_records],
        field_grid,
    )
    down_delta_fr = interpolate_series(
        [record["calibrated_field"] for record in down_records],
        [record["delta_fr_over_fr"] for record in down_records],
        field_grid,
    )
    drift_model = fit_checkpoint_drift(
        [
            record
            for record in checkpoint_records
            if record["cooldown_id"] == cooldown_id and record["device_id"] == device_id
        ]
    )
    corrected_up = interpolate_series(
        [record["calibrated_field"] for record in up_records],
        apply_drift_correction(up_records, drift_model),
        field_grid,
    )
    corrected_down = interpolate_series(
        [record["calibrated_field"] for record in down_records],
        apply_drift_correction(down_records, drift_model),
        field_grid,
    )
    raw_metrics = compute_loop_metrics(field_grid, up_inv_qi, down_inv_qi)
    corrected_metrics = compute_loop_metrics(field_grid, corrected_up, corrected_down)
    return {
        "cooldown_id": cooldown_id,
        "device_id": device_id,
        "history_label": history_label,
        "field_grid": serialise_float_list(field_grid),
        "raw_metrics": {key: round_value(value) for key, value in raw_metrics.items()},
        "drift_corrected_metrics": {key: round_value(value) for key, value in corrected_metrics.items()},
        "delta_fr_over_fr_metrics": {
            key: round_value(value)
            for key, value in compute_loop_metrics(field_grid, up_delta_fr, down_delta_fr).items()
        },
        "drift_model": None
        if drift_model is None
        else {
            "slope": round_value(drift_model["slope"]),
            "intercept": round_value(drift_model["intercept"]),
            "residual_scale": round_value(drift_model["residual_scale"]),
            "checkpoint_count": drift_model["checkpoint_count"],
        },
    }


def summarise_sham(records: list[dict[str, Any]], cooldown_id: str, device_id: str, field_span: float) -> dict[str, Any]:
    sham_records = [
        record
        for record in records
        if record["cooldown_id"] == cooldown_id and record["device_id"] == device_id and record["branch"] == "sham"
    ]
    if not sham_records:
        return {
            "present": False,
            "sample_count": 0,
            "inv_qi_span": None,
            "equivalent_area_envelope": None,
        }
    inv_qi_values = [record["inv_qi"] for record in sham_records]
    span = max(inv_qi_values) - min(inv_qi_values)
    return {
        "present": True,
        "sample_count": len(sham_records),
        "inv_qi_span": round_value(span),
        "equivalent_area_envelope": round_value(span * field_span),
    }


def summarise_witness(records: list[dict[str, Any]], cooldown_id: str, device_id: str, history_label: str) -> dict[str, Any]:
    usable = [
        record
        for record in records
        if record["cooldown_id"] == cooldown_id
        and record["device_id"] == device_id
        and record["history_label"] == history_label
        and record["branch"] in {"up", "down"}
        and record["witness_response"] is not None
    ]
    if len(usable) < 2:
        return {
            "present": False,
            "sample_count": len(usable),
            "correlation": None,
            "explained_variance": None,
            "gain": None,
        }
    target_values = [record["inv_qi"] for record in usable]
    witness_values = [float(record["witness_response"]) for record in usable]
    correlation = safe_correlation(target_values, witness_values)
    witness_mean = sum(witness_values) / len(witness_values)
    target_mean = sum(target_values) / len(target_values)
    denominator = sum((value - witness_mean) ** 2 for value in witness_values)
    if denominator <= 0.0:
        gain = 0.0
        explained_variance = 0.0
    else:
        gain = sum((witness - witness_mean) * (target - target_mean) for witness, target in zip(witness_values, target_values)) / denominator
        intercept = target_mean - gain * witness_mean
        residuals = [target - (gain * witness + intercept) for witness, target in zip(witness_values, target_values)]
        total_variance = sum((target - target_mean) ** 2 for target in target_values)
        explained_variance = 0.0 if total_variance <= 0.0 else max(0.0, 1.0 - sum(value * value for value in residuals) / total_variance)
    return {
        "present": True,
        "sample_count": len(usable),
        "correlation": round_value(correlation),
        "explained_variance": round_value(explained_variance),
        "gain": round_value(gain),
    }


def evaluate_data_completeness(
    records: list[dict[str, Any]],
    primary_device_id: str | None,
    checkpoint_records: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    primary_records = [record for record in records if primary_device_id is None or record["device_id"] == primary_device_id]
    cooldown_ids = sorted({record["cooldown_id"] for record in primary_records if record["branch"] in {"up", "down"}})
    if len(cooldown_ids) < 3:
        reasons.append("Requires three cooldowns with primary loop data.")
    sham_cooldowns = {record["cooldown_id"] for record in primary_records if record["branch"] == "sham"}
    if len(sham_cooldowns) < 3:
        reasons.append("Sham timing control is missing for at least one required cooldown.")
    witness_coverage = all(
        record["witness_response"] is not None for record in primary_records if record["branch"] in {"up", "down", "sham"}
    )
    if not witness_coverage:
        reasons.append("Witness coverage is incomplete in the primary dataset.")
    checkpoint_cooldowns = {record["cooldown_id"] for record in checkpoint_records if primary_device_id is None or record["device_id"] == primary_device_id}
    if len(checkpoint_cooldowns) < 3:
        reasons.append("Return-to-zero checkpoints are incomplete.")
    fixed_settings_logged = all(
        record["bath_temperature"] is not None and record["readout_power"] is not None
        for record in primary_records
        if record["branch"] in {"up", "down"}
    )
    if not fixed_settings_logged:
        reasons.append("Bath temperature and readout power must be logged for all primary loop points.")
    return {"passed": not reasons, "reasons": reasons}


def evaluate_dwell_validity(dwell_metadata: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: list[str] = []
    problematic: list[str] = []
    if not dwell_metadata:
        reasons.append("No dwell metadata was provided; dwell validity cannot be confirmed.")
        return {"passed": False, "reasons": reasons, "problematic_cooldowns": problematic}
    for entry in dwell_metadata:
        cooldown_id = str(entry.get("cooldown_id", "UNKNOWN"))
        converged = entry.get("converged")
        doubled_change = entry.get("doubled_loop_change_fraction")
        if converged is False or (doubled_change is not None and float(doubled_change) > 0.05):
            problematic.append(cooldown_id)
    if problematic:
        reasons.append("One or more cooldowns failed the dwell convergence rule.")
    return {"passed": not reasons, "reasons": reasons, "problematic_cooldowns": sorted(set(problematic))}


def evaluate_cooldown_reproducibility(primary_loop_payloads: list[dict[str, Any]], sham_map: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    reasons: list[str] = []
    by_cooldown: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payload in primary_loop_payloads:
        by_cooldown[payload["cooldown_id"]].append(payload)

    cooldown_ids = sorted(by_cooldown.keys())
    if len(cooldown_ids) < 3:
        reasons.append("At least three cooldowns are required for reproducibility.")
    ordered_payloads = []
    for cooldown_id in cooldown_ids:
        candidates = sorted(by_cooldown[cooldown_id], key=lambda payload: (payload["history_label"] != "ZFC", payload["history_label"]))
        ordered_payloads.append(candidates[0])
    a_o_signs = [1 if payload["raw_metrics"]["A_O"] > 0 else -1 for payload in ordered_payloads if payload["raw_metrics"]["A_O"] != 0]
    dominant_sign_count = max((a_o_signs.count(sign) for sign in {-1, 1}), default=0)
    if dominant_sign_count < 2:
        reasons.append("A_O sign is not stable across cooldowns.")
    stable_payload_count = 0
    for payload in ordered_payloads:
        sham_summary = sham_map.get((payload["cooldown_id"], payload["device_id"]), {})
        sham_envelope = sham_summary.get("equivalent_area_envelope")
        if sham_envelope is not None and abs(payload["raw_metrics"]["H_O"]) > sham_envelope:
            stable_payload_count += 1
    if stable_payload_count < 2:
        reasons.append("H_O does not clear the sham envelope in at least two cooldowns.")

    ranking_patterns: list[str] = []
    for cooldown_id in cooldown_ids:
        history_payloads = {payload["history_label"]: payload for payload in by_cooldown[cooldown_id]}
        if "ZFC" in history_payloads and "FC" in history_payloads:
            zfc_h_o = history_payloads["ZFC"]["raw_metrics"]["H_O"]
            fc_h_o = history_payloads["FC"]["raw_metrics"]["H_O"]
            if fc_h_o > zfc_h_o:
                ranking_patterns.append("FC_GT_ZFC")
            elif zfc_h_o > fc_h_o:
                ranking_patterns.append("ZFC_GT_FC")
            else:
                ranking_patterns.append("TIE")
    ranking_consistent = len(set(ranking_patterns)) <= 1 and len(ranking_patterns) >= 2
    if len(ranking_patterns) >= 2 and not ranking_consistent:
        reasons.append("ZFC versus FC branch ranking is inconsistent across cooldowns.")
    return {
        "passed": not reasons,
        "reasons": reasons,
        "cooldown_count": len(cooldown_ids),
        "dominant_a_o_sign_count": dominant_sign_count,
        "stable_payload_count": stable_payload_count,
        "history_ranking_patterns": ranking_patterns,
    }


def evaluate_geometry_gate(
    all_loop_payloads: list[dict[str, Any]],
    matched_geometry_device_ids: list[str],
) -> dict[str, Any]:
    if len(matched_geometry_device_ids) < 2:
        return {
            "passed": False,
            "status": "absent",
            "reasons": ["No same-chip matched geometry device set was declared."],
            "cooldown_rankings": {},
        }
    by_cooldown_device: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for payload in all_loop_payloads:
        if payload["device_id"] not in matched_geometry_device_ids:
            continue
        slot = by_cooldown_device[payload["cooldown_id"]]
        current = slot.get(payload["device_id"])
        if current is None or (current["history_label"] != "ZFC" and payload["history_label"] == "ZFC"):
            slot[payload["device_id"]] = payload
    if len(by_cooldown_device) < 3:
        return {
            "passed": False,
            "status": "absent",
            "reasons": ["Matched geometry ordering is not available across the minimum three cooldowns."],
            "cooldown_rankings": {},
        }
    rankings: dict[str, list[str]] = {}
    for cooldown_id, device_map in sorted(by_cooldown_device.items()):
        if any(device_id not in device_map for device_id in matched_geometry_device_ids):
            return {
                "passed": False,
                "status": "absent",
                "reasons": ["At least one cooldown is missing one or more matched-geometry devices."],
                "cooldown_rankings": rankings,
            }
        ranked = sorted(device_map.values(), key=lambda payload: (-payload["raw_metrics"]["H_O"], payload["device_id"]))
        rankings[cooldown_id] = [payload["device_id"] for payload in ranked]
    unique_rankings = {tuple(ranking) for ranking in rankings.values()}
    if len(unique_rankings) > 1:
        return {
            "passed": False,
            "status": "inconsistent",
            "reasons": ["Matched geometry ordering changes across cooldowns."],
            "cooldown_rankings": rankings,
        }
    return {
        "passed": True,
        "status": "passed",
        "reasons": [],
        "cooldown_rankings": rankings,
    }


def evaluate_h0(primary_loop_payloads: list[dict[str, Any]], sham_map: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    collapses = []
    for payload in primary_loop_payloads:
        sham_summary = sham_map.get((payload["cooldown_id"], payload["device_id"]))
        if not sham_summary or sham_summary.get("equivalent_area_envelope") is None:
            continue
        envelope = float(sham_summary["equivalent_area_envelope"])
        corrected_h_o = abs(float(payload["drift_corrected_metrics"]["H_O"]))
        corrected_a_o = abs(float(payload["drift_corrected_metrics"]["A_O"]))
        if corrected_h_o <= envelope and corrected_a_o <= envelope:
            collapses.append(payload["cooldown_id"])
    if collapses:
        return {
            "status": "explained_by_simple_drift_screen",
            "passed_h0_rejection": False,
            "reasons": ["Drift-corrected loop metrics collapse into the sham envelope."],
            "cooldown_hits": sorted(set(collapses)),
        }
    return {
        "status": "not_tested_by_model_fit",
        "passed_h0_rejection": True,
        "reasons": ["No parametric H0 fit is implemented in v1; simple drift screening did not collapse the loop."],
        "cooldown_hits": [],
    }


def evaluate_h3(
    records: list[dict[str, Any]],
    primary_device_id: str | None,
    dwell_result: dict[str, Any],
) -> dict[str, Any]:
    t1_records = [
        record
        for record in records
        if (primary_device_id is None or record["device_id"] == primary_device_id) and record["T1"] is not None
    ]
    strong_lag_signal = len(t1_records) > 0 and bool(dwell_result["problematic_cooldowns"])
    return {
        "status": "lag_risk_detected" if strong_lag_signal else "no_primary_h3_signal",
        "selected_field_t1_count": len(t1_records),
        "dwell_problem_cooldowns": dwell_result["problematic_cooldowns"],
        "primary_observable_explained": False,
        "reasons": (
            ["Selected-field T1 data exists and dwell convergence metadata indicates lag risk."]
            if strong_lag_signal
            else ["No rule-based H3 signal strong enough to explain the primary observable in v1."]
        ),
    }


def evaluate_h4(witness_map: dict[tuple[str, str, str], dict[str, Any]], primary_loop_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    strong_hits: list[str] = []
    details: list[dict[str, Any]] = []
    for payload in primary_loop_payloads:
        key = (payload["cooldown_id"], payload["device_id"], payload["history_label"])
        witness = witness_map.get(key, {})
        details.append(
            {
                "cooldown_id": payload["cooldown_id"],
                "history_label": payload["history_label"],
                "correlation": witness.get("correlation"),
                "explained_variance": witness.get("explained_variance"),
                "gain": witness.get("gain"),
            }
        )
        if witness.get("present") and float(witness.get("correlation") or 0.0) >= 0.95 and float(witness.get("explained_variance") or 0.0) >= 0.9:
            strong_hits.append(payload["cooldown_id"])
    return {
        "status": "witness_comoves_with_target" if strong_hits else "no_primary_h4_signal",
        "primary_observable_explained": bool(strong_hits),
        "cooldown_hits": sorted(set(strong_hits)),
        "details": details,
        "reasons": (
            ["Target and witness strongly co-move under a fixed gain mapping."]
            if strong_hits
            else ["No witness co-movement strong enough to explain the primary observable in v1."]
        ),
    }


def build_required_plots_manifest(output_dir: Path) -> dict[str, str]:
    return {name: str((output_dir / filename).resolve()) for name, filename in PLOT_FILENAMES.items()}


def render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# E01 MM Analysis Report",
        "",
        "## Outcome",
        "",
        f"- branch disposition: `{summary['branch_disposition']}`",
        f"- vortex status: `{summary['vortex_status']}`",
        f"- falsifier hits: `{', '.join(summary['falsifier_hits']) if summary['falsifier_hits'] else 'none'}`",
        "",
        "## Gates",
        "",
    ]
    for gate_name, gate_payload in summary["gate_results"].items():
        lines.append(f"- `{gate_name}`: `{'pass' if gate_payload['passed'] else 'fail'}`")
        for reason in gate_payload["reasons"]:
            lines.append(f"  reason: {reason}")
    lines.extend(
        [
            "",
            "## Rule-Based Screens",
            "",
            f"- `H0`: `{summary['h0_result']['status']}`",
            f"- `H3`: `{summary['h3_screen']['status']}`",
            f"- `H4`: `{summary['h4_screen']['status']}`",
            "",
            "## Input Summary",
            "",
            f"- cooldown count: `{summary['input_summary']['cooldown_count']}`",
            f"- device count: `{summary['input_summary']['device_count']}`",
            f"- record count: `{summary['input_summary']['record_count']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_analysis_summary(payload: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    schema_version = payload.get("analysis_schema_version")
    if schema_version != DEFAULT_ANALYSIS_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported analysis_schema_version: {schema_version}. Expected {DEFAULT_ANALYSIS_SCHEMA_VERSION}."
        )
    records = [normalise_record(record, index) for index, record in enumerate(ensure_list(payload.get("records")))]
    if not records:
        raise ValueError("Analysis input must contain at least one record.")

    primary_device_id = select_primary_device(records, payload.get("primary_device_id"))
    matched_geometry_device_ids = [str(value) for value in ensure_list(payload.get("matched_geometry_device_ids"))]
    checkpoint_records = [record for record in records if record["branch"] == "checkpoint"]
    cooldown_ids = sorted({record["cooldown_id"] for record in records})
    device_ids = sorted({record["device_id"] for record in records})
    history_labels = sorted({record["history_label"] for record in records if record["branch"] in {"up", "down"}})

    loop_payloads: list[dict[str, Any]] = []
    sham_map: dict[tuple[str, str], dict[str, Any]] = {}
    witness_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    primary_loop_payloads: list[dict[str, Any]] = []

    for cooldown_id in cooldown_ids:
        for device_id in device_ids:
            candidate_histories = sorted(
                {
                    record["history_label"]
                    for record in records
                    if record["cooldown_id"] == cooldown_id and record["device_id"] == device_id and record["branch"] in {"up", "down"}
                }
            )
            for history_label in candidate_histories:
                payload_item = compute_loop_payload(records, cooldown_id, device_id, history_label, checkpoint_records)
                if payload_item is None:
                    continue
                loop_payloads.append(payload_item)
                field_span = payload_item["field_grid"][-1] - payload_item["field_grid"][0]
                sham_map[(cooldown_id, device_id)] = summarise_sham(records, cooldown_id, device_id, field_span)
                witness_map[(cooldown_id, device_id, history_label)] = summarise_witness(records, cooldown_id, device_id, history_label)
                if device_id == primary_device_id:
                    primary_loop_payloads.append(payload_item)

    data_completeness = evaluate_data_completeness(records, primary_device_id, checkpoint_records)
    dwell_result = evaluate_dwell_validity(ensure_list(payload.get("dwell_metadata")))
    cooldown_reproducibility = evaluate_cooldown_reproducibility(primary_loop_payloads, sham_map)
    geometry_gate = evaluate_geometry_gate(loop_payloads, matched_geometry_device_ids)
    h0_result = evaluate_h0(primary_loop_payloads, sham_map)
    h3_screen = evaluate_h3(records, primary_device_id, dwell_result)
    h4_screen = evaluate_h4(witness_map, primary_loop_payloads)

    falsifier_hits: list[str] = []
    sham_reproduces_loop = any(
        sham_summary.get("present")
        and sham_summary.get("equivalent_area_envelope") is not None
        and any(
            abs(payload_item["raw_metrics"]["A_O"]) <= float(sham_summary["equivalent_area_envelope"])
            for payload_item in primary_loop_payloads
            if payload_item["cooldown_id"] == cooldown_id
        )
        for (cooldown_id, device_id), sham_summary in sham_map.items()
        if device_id == primary_device_id
    )
    if sham_reproduces_loop:
        falsifier_hits.append("SHAM_TIMING_REPRODUCES_LOOP_AREA")
    if h0_result["status"] == "explained_by_simple_drift_screen":
        falsifier_hits.append("H0_SIMPLE_DRIFT_SCREEN_EXPLAINS_DATA")
    if h4_screen["primary_observable_explained"]:
        falsifier_hits.append("PACKAGE_WITNESS_COMOVES_WITH_TARGET")
    if geometry_gate["status"] == "absent":
        falsifier_hits.append("GEOMETRY_ORDERING_ABSENT")
    if geometry_gate["status"] == "inconsistent":
        falsifier_hits.append("GEOMETRY_ORDERING_INCONSISTENT")
    if h3_screen["status"] == "lag_risk_detected":
        falsifier_hits.append("QP_LAG_RISK_IN_SELECTED_FIELD_TRACES")

    if (
        "SHAM_TIMING_REPRODUCES_LOOP_AREA" in falsifier_hits
        or "H0_SIMPLE_DRIFT_SCREEN_EXPLAINS_DATA" in falsifier_hits
        or "PACKAGE_WITNESS_COMOVES_WITH_TARGET" in falsifier_hits
    ):
        branch_disposition = "KILL_ENTIRE_BRANCH"
        vortex_status = "blocked"
    elif (
        geometry_gate["status"] in {"absent", "inconsistent"}
        or h3_screen["status"] == "lag_risk_detected"
        or not cooldown_reproducibility["passed"]
        or not data_completeness["passed"]
        or not dwell_result["passed"]
    ):
        branch_disposition = "PRESERVE_GENERIC_MM_BRANCH"
        vortex_status = "DOWNGRADE_VORTEX_ONLY"
    else:
        branch_disposition = "PRESERVE_VORTEX_CANDIDATE_UPGRADE_PATH"
        vortex_status = "upgrade_path_preserved"

    gate_results = {
        "data_completeness": data_completeness,
        "dwell_validity": dwell_result,
        "h0_rejection": {
            "passed": h0_result["passed_h0_rejection"],
            "reasons": h0_result["reasons"],
        },
        "mechanism_competition": {
            "passed": not h4_screen["primary_observable_explained"] and not h3_screen["primary_observable_explained"],
            "reasons": h4_screen["reasons"] + h3_screen["reasons"],
        },
        "geometry_gate": {
            "passed": geometry_gate["passed"],
            "reasons": geometry_gate["reasons"],
        },
        "governance": {
            "passed": branch_disposition != "KILL_ENTIRE_BRANCH",
            "reasons": []
            if branch_disposition != "KILL_ENTIRE_BRANCH"
            else ["A falsifier hit killed the branch before any upgrade path can be retained."],
        },
    }

    sham_comparison = {
        f"{cooldown_id}:{device_id}": summary for (cooldown_id, device_id), summary in sorted(sham_map.items())
    }
    witness_comparison = {
        f"{cooldown_id}:{device_id}:{history_label}": summary
        for (cooldown_id, device_id, history_label), summary in sorted(witness_map.items())
    }
    return {
        "analysis_schema_version": DEFAULT_ANALYSIS_SCHEMA_VERSION,
        "branch_slug": payload.get("branch_slug", "e01_mm_flux_history_hysteresis"),
        "input_summary": {
            "record_count": len(records),
            "cooldown_count": len(cooldown_ids),
            "device_count": len(device_ids),
            "history_labels": history_labels,
            "primary_device_id": primary_device_id,
            "matched_geometry_device_ids": matched_geometry_device_ids,
        },
        "gate_results": gate_results,
        "loop_metrics": loop_payloads,
        "sham_comparison": sham_comparison,
        "witness_comparison": witness_comparison,
        "cooldown_reproducibility": cooldown_reproducibility,
        "geometry_gate": geometry_gate,
        "h0_result": h0_result,
        "h3_screen": h3_screen,
        "h4_screen": h4_screen,
        "branch_disposition": branch_disposition,
        "vortex_status": vortex_status,
        "falsifier_hits": falsifier_hits,
        "required_plots_manifest": build_required_plots_manifest(output_dir),
    }


def write_markdown_report(output_path: Path, summary: dict[str, Any]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown_report(summary), encoding="ascii")
    return output_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic post-run analysis for the E01 branch.")
    parser.add_argument("--input", required=True, help="Path to the normalized analysis input JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory that will receive summary.json.")
    parser.add_argument("--report-path", help="Optional Markdown report path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    payload = read_json(input_path)
    summary = generate_analysis_summary(payload, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    write_json(summary_path, summary)
    print(f"Wrote summary to {summary_path}")
    if args.report_path:
        report_path = write_markdown_report(Path(args.report_path).resolve(), summary)
        print(f"Wrote report to {report_path}")
    print(json.dumps(summary["input_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
