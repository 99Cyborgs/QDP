from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

DEFAULT_SEED = 1729

FIELD_GRID_MT = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]


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


def baseline_inv_qi(field_mt: float) -> float:
    return 1.0e-6 * (1.0 + 0.08 * abs(field_mt) + 0.01 * field_mt * field_mt)


def baseline_delta_fr(field_mt: float) -> float:
    return -2.5e-7 * field_mt + 1.5e-8 * field_mt * field_mt


def exp_relax(previous: float, target: float, dwell_s: float, tau_s: float) -> float:
    return target + (previous - target) * math.exp(-dwell_s / tau_s)


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


def round_value(value: float, digits: int = 12) -> float:
    return round(value, digits)


def serialise_records(records: list[dict[str, float | str | None]]) -> list[dict[str, float | str | None]]:
    serialised: list[dict[str, float | str | None]] = []
    for record in records:
        serialised_record: dict[str, float | str | None] = {}
        for key, value in record.items():
            if isinstance(value, float):
                serialised_record[key] = round_value(value)
            else:
                serialised_record[key] = value
        serialised.append(serialised_record)
    return serialised


def simulate_memoryless_field_loss_with_drift(seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    dwell_s = 45.0
    drift_inv_qi_per_s = 1.6e-9
    drift_delta_fr_per_s = -4.0e-10
    noise_inv_qi = 8.0e-9
    noise_delta_fr = 5.0e-10

    records: list[dict[str, float | str | None]] = []
    sham_records: list[dict[str, float | str | None]] = []
    zero_checkpoints: list[dict[str, float | str | None]] = []

    up_branch: list[float] = []
    down_descending: list[float] = []
    time_s = 0.0

    for checkpoint_label in ["zero_pre", "zero_mid", "zero_post"]:
        value = baseline_inv_qi(0.0) + drift_inv_qi_per_s * time_s + rng.gauss(0.0, noise_inv_qi)
        zero_checkpoints.append(
            {
                "history_label": checkpoint_label,
                "time_s": time_s,
                "field_mT": 0.0,
                "inv_qi": value,
            }
        )
        time_s += dwell_s

    time_s = 0.0
    for field_mt in FIELD_GRID_MT:
        inv_qi = baseline_inv_qi(field_mt) + drift_inv_qi_per_s * time_s + rng.gauss(0.0, noise_inv_qi)
        delta_fr = baseline_delta_fr(field_mt) + drift_delta_fr_per_s * time_s + rng.gauss(0.0, noise_delta_fr)
        up_branch.append(inv_qi)
        records.append(
            {
                "branch": "up",
                "time_s": time_s,
                "field_mT": field_mt,
                "inv_qi": inv_qi,
                "delta_fr_over_fr": delta_fr,
            }
        )
        time_s += dwell_s

    time_s += dwell_s
    for field_mt in reversed(FIELD_GRID_MT):
        inv_qi = baseline_inv_qi(field_mt) + drift_inv_qi_per_s * time_s + rng.gauss(0.0, noise_inv_qi)
        delta_fr = baseline_delta_fr(field_mt) + drift_delta_fr_per_s * time_s + rng.gauss(0.0, noise_delta_fr)
        down_descending.append(inv_qi)
        records.append(
            {
                "branch": "down",
                "time_s": time_s,
                "field_mT": field_mt,
                "inv_qi": inv_qi,
                "delta_fr_over_fr": delta_fr,
            }
        )
        time_s += dwell_s

    sham_time_s = 0.0
    for sham_index in range(len(FIELD_GRID_MT) * 2):
        sham_inv_qi = baseline_inv_qi(0.0) + drift_inv_qi_per_s * sham_time_s + rng.gauss(0.0, noise_inv_qi)
        sham_delta_fr = baseline_delta_fr(0.0) + drift_delta_fr_per_s * sham_time_s + rng.gauss(0.0, noise_delta_fr)
        sham_records.append(
            {
                "branch": "sham",
                "time_s": sham_time_s,
                "field_mT": 0.0,
                "step_index": sham_index,
                "inv_qi": sham_inv_qi,
                "delta_fr_over_fr": sham_delta_fr,
            }
        )
        sham_time_s += dwell_s

    down_branch = list(reversed(down_descending))
    metrics = compute_loop_metrics(FIELD_GRID_MT, up_branch, down_branch)

    return {
        "case_name": "memoryless_field_loss_with_drift",
        "seed": seed,
        "purpose": "Stress H0 under allowable drift and sham cadence without retained memory.",
        "inputs": {
            "field_grid_mT": FIELD_GRID_MT,
            "dwell_s": dwell_s,
            "drift_inv_qi_per_s": drift_inv_qi_per_s,
            "drift_delta_fr_per_s": drift_delta_fr_per_s,
            "noise_inv_qi_sigma": noise_inv_qi,
            "noise_delta_fr_sigma": noise_delta_fr,
        },
        "loop_metrics": {key: round_value(value) for key, value in metrics.items()},
        "records": serialise_records(records),
        "sham_records": serialise_records(sham_records),
        "zero_field_checkpoints": serialise_records(zero_checkpoints),
    }


def simulate_generic_hidden_state_hysteresis(seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    dwell_s = 90.0
    base_tau_s = 180.0
    base_coupling = 1.8e-7
    cooldowns: list[dict[str, object]] = []

    for cooldown_index in range(3):
        tau_s = base_tau_s * (1.0 + rng.gauss(0.0, 0.04))
        coupling = base_coupling * (1.0 + rng.gauss(0.0, 0.05))
        occupancy = 0.0
        up_branch: list[float] = []
        down_descending: list[float] = []
        occupancy_trace_up: list[float] = []
        occupancy_trace_down_descending: list[float] = []

        for field_mt in FIELD_GRID_MT:
            target = field_mt / FIELD_GRID_MT[-1]
            occupancy = exp_relax(occupancy, target, dwell_s, tau_s)
            occupancy_trace_up.append(occupancy)
            up_branch.append(
                baseline_inv_qi(field_mt)
                + coupling * occupancy
                + rng.gauss(0.0, 6.0e-9)
            )

        for field_mt in reversed(FIELD_GRID_MT):
            target = field_mt / FIELD_GRID_MT[-1]
            occupancy = exp_relax(occupancy, target, dwell_s, tau_s)
            occupancy_trace_down_descending.append(occupancy)
            down_descending.append(
                baseline_inv_qi(field_mt)
                + coupling * occupancy
                + rng.gauss(0.0, 6.0e-9)
            )

        down_branch = list(reversed(down_descending))
        occupancy_trace_down = list(reversed(occupancy_trace_down_descending))
        metrics = compute_loop_metrics(FIELD_GRID_MT, up_branch, down_branch)
        cooldowns.append(
            {
                "cooldown_id": f"synthetic_cd_{cooldown_index + 1:02d}",
                "tau_s": round_value(tau_s),
                "coupling": round_value(coupling),
                "field_grid_mT": FIELD_GRID_MT,
                "up_branch_inv_qi": [round_value(value) for value in up_branch],
                "down_branch_inv_qi": [round_value(value) for value in down_branch],
                "up_branch_hidden_state": [round_value(value) for value in occupancy_trace_up],
                "down_branch_hidden_state": [round_value(value) for value in occupancy_trace_down],
                "loop_metrics": {key: round_value(value) for key, value in metrics.items()},
            }
        )

    mean_h_o = sum(cooldown["loop_metrics"]["H_O"] for cooldown in cooldowns) / len(cooldowns)
    mean_a_o = sum(cooldown["loop_metrics"]["A_O"] for cooldown in cooldowns) / len(cooldowns)

    return {
        "case_name": "generic_hidden_state_hysteresis",
        "seed": seed,
        "purpose": "Stress H1 with a minimal retained-state surrogate and cooldown replication.",
        "inputs": {
            "field_grid_mT": FIELD_GRID_MT,
            "dwell_s": dwell_s,
            "base_tau_s": base_tau_s,
            "base_coupling": base_coupling,
            "cooldown_count": 3,
        },
        "summary": {
            "mean_H_O": round_value(mean_h_o),
            "mean_A_O": round_value(mean_a_o),
            "cooldown_count": 3,
        },
        "cooldowns": cooldowns,
    }


def simulate_qp_lag_after_field_step(seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    field_schedule = [0.0, 1.0, 3.0, 1.0, 0.0]
    dwell_s = 40.0
    qp_tau_s = 95.0
    burst_gain_per_step = 0.45
    t1_base_us = 42.0
    t1_suppression_gain = 0.35
    loss_gain = 1.5e-7

    records: list[dict[str, float | str | None]] = []
    residual_qp = 0.0
    previous_field = 0.0
    time_s = 0.0

    for step_index, field_mt in enumerate(field_schedule):
        field_step = abs(field_mt - previous_field)
        residual_qp = (residual_qp + burst_gain_per_step * field_step) * math.exp(-dwell_s / qp_tau_s)
        inv_qi = baseline_inv_qi(field_mt) + loss_gain * residual_qp + rng.gauss(0.0, 7.0e-9)
        t1_us = t1_base_us / (1.0 + t1_suppression_gain * residual_qp) + rng.gauss(0.0, 0.08)
        records.append(
            {
                "step_index": step_index,
                "time_s": time_s,
                "field_mT": field_mt,
                "qp_residual": residual_qp,
                "inv_qi": inv_qi,
                "T1_us": t1_us,
            }
        )
        previous_field = field_mt
        time_s += dwell_s

    up_branch = [records[0]["inv_qi"], records[1]["inv_qi"], records[2]["inv_qi"]]
    down_branch = [records[4]["inv_qi"], records[3]["inv_qi"], records[2]["inv_qi"]]
    field_grid = [0.0, 1.0, 3.0]
    metrics = compute_loop_metrics(field_grid, up_branch, down_branch)

    return {
        "case_name": "qp_lag_after_field_step",
        "seed": seed,
        "purpose": "Stress H3 by showing how step-triggered lag can fake loop metrics at finite dwell.",
        "inputs": {
            "field_schedule_mT": field_schedule,
            "dwell_s": dwell_s,
            "qp_tau_s": qp_tau_s,
            "burst_gain_per_step": burst_gain_per_step,
            "t1_base_us": t1_base_us,
        },
        "apparent_loop_metrics": {key: round_value(value) for key, value in metrics.items()},
        "records": serialise_records(records),
    }


def is_monotonic(values: list[float]) -> bool:
    ascending = all(left <= right for left, right in zip(values, values[1:]))
    descending = all(left >= right for left, right in zip(values, values[1:]))
    return ascending or descending


def simulate_fabrication_noise_false_geometry_signal(seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    widths_um = [2.0, 4.0, 8.0, 16.0]
    fabrication_offsets = {width: rng.gauss(0.0, 0.06) for width in widths_um}
    cooldowns: list[dict[str, object]] = []
    monotonic_h_o_cooldowns = 0

    for cooldown_index in range(3):
        measurements: list[dict[str, float | str]] = []
        h_o_values: list[float] = []
        for width_um in widths_um:
            fabrication_offset = fabrication_offsets[width_um]
            h_o = 0.18 + fabrication_offset + rng.gauss(0.0, 0.03)
            delta_fr = 2.0e-7 + 4.5e-8 * fabrication_offset + rng.gauss(0.0, 1.2e-8)
            h_o_values.append(h_o)
            measurements.append(
                {
                    "device_id": f"geom_{int(width_um):02d}um",
                    "nominal_width_um": round_value(width_um),
                    "H_O": round_value(h_o),
                    "delta_fr_over_fr": round_value(delta_fr),
                }
            )

        if is_monotonic(h_o_values):
            monotonic_h_o_cooldowns += 1

        ranked_measurements = sorted(measurements, key=lambda item: item["H_O"], reverse=True)
        cooldowns.append(
            {
                "cooldown_id": f"synthetic_geom_cd_{cooldown_index + 1:02d}",
                "measurements": ranked_measurements,
                "rank_order_by_H_O": [measurement["device_id"] for measurement in ranked_measurements],
            }
        )

    return {
        "case_name": "fabrication_noise_false_geometry_signal",
        "seed": seed,
        "purpose": "Stress H2 by estimating false width ordering from fabrication scatter alone.",
        "inputs": {
            "nominal_widths_um": widths_um,
            "fabrication_offsets": {str(width): round_value(offset) for width, offset in fabrication_offsets.items()},
            "cooldown_count": 3,
        },
        "summary": {
            "monotonic_h_o_cooldowns": monotonic_h_o_cooldowns,
            "cooldown_count": 3,
            "spurious_monotonic_rate": round_value(monotonic_h_o_cooldowns / 3.0),
        },
        "cooldowns": cooldowns,
    }


def shared_drift(time_s: float) -> float:
    return 1.4e-7 * math.sin(time_s / 120.0) + 6.0e-10 * time_s


def simulate_package_common_mode_drift(seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    dwell_s = 45.0
    target_gain = 0.95
    witness_gain = 0.70
    records: list[dict[str, float | str | None]] = []
    target_up: list[float] = []
    target_down_descending: list[float] = []
    witness_trace: list[float] = []
    target_trace: list[float] = []
    time_s = 0.0

    for field_mt in FIELD_GRID_MT:
        drift = shared_drift(time_s)
        target = baseline_inv_qi(field_mt) + target_gain * drift + rng.gauss(0.0, 7.0e-9)
        witness = witness_gain * drift + rng.gauss(0.0, 5.0e-9)
        target_up.append(target)
        target_trace.append(target)
        witness_trace.append(witness)
        records.append(
            {
                "branch": "up",
                "time_s": time_s,
                "field_mT": field_mt,
                "target_inv_qi": target,
                "witness_response": witness,
            }
        )
        time_s += dwell_s

    time_s += dwell_s
    for field_mt in reversed(FIELD_GRID_MT):
        drift = shared_drift(time_s)
        target = baseline_inv_qi(field_mt) + target_gain * drift + rng.gauss(0.0, 7.0e-9)
        witness = witness_gain * drift + rng.gauss(0.0, 5.0e-9)
        target_down_descending.append(target)
        target_trace.append(target)
        witness_trace.append(witness)
        records.append(
            {
                "branch": "down",
                "time_s": time_s,
                "field_mT": field_mt,
                "target_inv_qi": target,
                "witness_response": witness,
            }
        )
        time_s += dwell_s

    target_down = list(reversed(target_down_descending))
    metrics = compute_loop_metrics(FIELD_GRID_MT, target_up, target_down)

    return {
        "case_name": "package_common_mode_drift",
        "seed": seed,
        "purpose": "Stress H4 by generating co-moving target and witness traces from a shared drift source.",
        "inputs": {
            "field_grid_mT": FIELD_GRID_MT,
            "dwell_s": dwell_s,
            "target_gain": target_gain,
            "witness_gain": witness_gain,
        },
        "loop_metrics": {key: round_value(value) for key, value in metrics.items()},
        "target_witness_correlation": round_value(safe_correlation(target_trace, witness_trace)),
        "records": serialise_records(records),
    }


def generate_suite(seed: int = DEFAULT_SEED) -> dict[str, object]:
    case_builders = [
        ("memoryless_field_loss_with_drift", simulate_memoryless_field_loss_with_drift),
        ("generic_hidden_state_hysteresis", simulate_generic_hidden_state_hysteresis),
        ("qp_lag_after_field_step", simulate_qp_lag_after_field_step),
        ("fabrication_noise_false_geometry_signal", simulate_fabrication_noise_false_geometry_signal),
        ("package_common_mode_drift", simulate_package_common_mode_drift),
    ]

    cases: dict[str, object] = {}
    for offset, (case_name, builder) in enumerate(case_builders):
        cases[case_name] = builder(seed + offset)

    summary = {
        "suite_name": "E01 MM Minimal Simulation Suite",
        "seed": seed,
        "case_count": len(cases),
        "case_names": list(cases.keys()),
        "proposal_scope": "Implements exactly the five phase-1 synthetic stress cases from e01_mm_minimal_sim_plan.md.",
    }
    return {"summary": summary, "cases": cases}


def render_proposal_appendix(suite: dict[str, object]) -> str:
    summary = suite["summary"]
    cases = suite["cases"]

    memoryless = cases["memoryless_field_loss_with_drift"]
    hidden = cases["generic_hidden_state_hysteresis"]
    qp_lag = cases["qp_lag_after_field_step"]
    fabrication = cases["fabrication_noise_false_geometry_signal"]
    package = cases["package_common_mode_drift"]

    lines = [
        "# E01 MM Simulation Appendix",
        "",
        "## Reproducibility",
        "",
        f"- suite: `{summary['suite_name']}`",
        f"- seed: `{summary['seed']}`",
        f"- case count: `{summary['case_count']}`",
        "",
        "## Synthetic Case Summary",
        "",
        "| Case | Proposal role | Primary quantitative output |",
        "| --- | --- | --- |",
        (
            f"| `memoryless_field_loss_with_drift` | H0 stress test | "
            f"`H_O = {memoryless['loop_metrics']['H_O']}`, `A_O = {memoryless['loop_metrics']['A_O']}` |"
        ),
        (
            f"| `generic_hidden_state_hysteresis` | H1 retained-memory surrogate | "
            f"`mean_H_O = {hidden['summary']['mean_H_O']}`, `mean_A_O = {hidden['summary']['mean_A_O']}` |"
        ),
        (
            f"| `qp_lag_after_field_step` | H3 lag challenge | "
            f"`H_O = {qp_lag['apparent_loop_metrics']['H_O']}`, `A_O = {qp_lag['apparent_loop_metrics']['A_O']}` |"
        ),
        (
            f"| `fabrication_noise_false_geometry_signal` | H2 false-ordering stress | "
            f"`spurious_monotonic_rate = {fabrication['summary']['spurious_monotonic_rate']}` |"
        ),
        (
            f"| `package_common_mode_drift` | H4 common-mode drift challenge | "
            f"`corr(target,witness) = {package['target_witness_correlation']}` |"
        ),
        "",
        "## Proposal Interpretation",
        "",
        "- The package now demonstrates that each authorized mechanism class can be stressed without access to cryogenic hardware.",
        "- The appendix metrics are deterministic for the declared seed and can be regenerated from the simulation suite.",
        "- These outputs are proposal evidence for computational readiness only; they are not claims about real-device calibration.",
        "",
        "## Regeneration Command",
        "",
        "```powershell",
        "python simulation\\e01_mm_simulation_suite.py --output-dir simulation_outputs --appendix-path simulation\\e01_mm_simulation_appendix.md",
        "```",
    ]
    return "\n".join(lines) + "\n"


def write_suite_outputs(output_dir: Path, suite: dict[str, object]) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(suite["summary"], indent=2) + "\n", encoding="ascii")
    written_paths.append(summary_path)

    cases = suite["cases"]
    if not isinstance(cases, dict):
        raise ValueError("Suite cases must be a mapping.")

    for case_name, payload in cases.items():
        case_path = output_dir / f"{case_name}.json"
        case_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")
        written_paths.append(case_path)

    return written_paths


def write_proposal_appendix(output_path: Path, suite: dict[str, object]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_proposal_appendix(suite), encoding="ascii")
    return output_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the E01 minimal synthetic simulation suite."
    )
    parser.add_argument(
        "--output-dir",
        default="simulation_outputs",
        help="Directory that will receive JSON outputs for every synthetic case.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Base seed used to derive deterministic per-case random streams.",
    )
    parser.add_argument(
        "--appendix-path",
        help="Optional Markdown appendix path summarising proposal-facing metrics from the generated suite.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    suite = generate_suite(seed=args.seed)
    output_dir = Path(args.output_dir)
    written_paths = write_suite_outputs(output_dir, suite)
    appendix_path = None
    if args.appendix_path:
        appendix_path = write_proposal_appendix(Path(args.appendix_path), suite)

    print(f"Wrote {len(written_paths)} files to {output_dir.resolve()}")
    if appendix_path is not None:
        print(f"Wrote proposal appendix to {appendix_path.resolve()}")
    print(json.dumps(suite["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
