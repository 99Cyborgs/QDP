from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from ..io import write_json, write_text
from ..models import ScoreResult
from ..reporting import markdown_table
from .contracts import load_sweep_summary_payload, load_tranche_summary_payload
from .models import SweepManifest, SweepSummary, TrancheIndexEntry, TrancheSummary


def default_sweep_directory(base_dir: str | Path | None = None) -> Path:
    """Return the default root for persisted sweep runs."""

    base = Path(base_dir) if base_dir is not None else Path("artifacts") / "runs" / "sweeps"
    return base.resolve()


def write_sweep_outputs(
    manifest: SweepManifest,
    summary: SweepSummary,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
) -> None:
    """Persist sweep-level and tranche-level summary artifacts."""

    output_root = Path(manifest.output_root)
    write_json(output_root / "sweep_manifest.json", manifest.model_dump(mode="json"))
    write_json(output_root / "sweep_summary.json", summary.model_dump(mode="json"))
    write_text(output_root / "sweep_summary.md", render_sweep_summary_markdown(summary, manifest))
    write_json(
        output_root / "tranche_index.json",
        [
            entry.model_dump(mode="json")
            for entry in build_tranche_index_entries(summary, output_root=output_root)
        ],
    )

    leaderboard_frame = aggregate_leaderboard_dataframe(summary)
    leaderboard_path = output_root / "aggregate_leaderboard.csv"
    leaderboard_frame.to_csv(leaderboard_path, index=False)

    plots_dir = output_root / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    _plot_cross_slice_score_matrix(
        summary, slice_results, plots_dir / "cross_slice_score_comparison.png"
    )
    _plot_robustness_overview(summary, plots_dir / "robustness_overview.png")

    for tranche_summary in summary.tranches:
        tranche_dir = output_root / "tranches" / tranche_summary.tranche_id
        write_json(tranche_dir / "tranche_summary.json", tranche_summary.model_dump(mode="json"))
        write_text(
            tranche_dir / "tranche_summary.md", render_tranche_summary_markdown(tranche_summary)
        )


def build_tranche_index_entries(
    summary: SweepSummary,
    *,
    output_root: Path,
) -> list[TrancheIndexEntry]:
    return [
        TrancheIndexEntry(
            tranche_id=tranche.tranche_id,
            status=tranche.status,
            output_dir=str(output_root / "tranches" / tranche.tranche_id),
            summary_path=str(
                output_root / "tranches" / tranche.tranche_id / "tranche_summary.json"
            ),
            slice_ids=[record.slice_id for record in tranche.slice_records],
        )
        for tranche in summary.tranches
    ]


def aggregate_leaderboard_dataframe(summary: SweepSummary) -> pd.DataFrame:
    rows = [
        {
            "rank": index + 1,
            "genome_id": aggregate.genome_id,
            "parent_structure_id": aggregate.parent_structure_id,
            "robustness_score": aggregate.robustness_score,
            "profile_sensitivity_score": aggregate.profile_sensitivity_score,
            "mean_rank": aggregate.mean_rank,
            "best_rank": aggregate.best_rank,
            "worst_rank": aggregate.worst_rank,
            "top_k_appearances": aggregate.top_k_appearances,
            "win_count": aggregate.win_count,
            "mean_score": aggregate.mean_score,
            "score_stddev": aggregate.score_stddev,
            "slice_count": aggregate.successful_slice_count,
        }
        for index, aggregate in enumerate(summary.aggregate_rankings)
    ]
    return pd.DataFrame(rows)


def render_sweep_summary_markdown(
    summary: SweepSummary,
    manifest: SweepManifest | None = None,
) -> str:
    governance_rows = [
        ["recommendation", summary.adjudication.recommendation.value],
        ["promotion_blocked", "yes" if summary.adjudication.promotion_blocked else "no"],
        ["promotion_block_reason", summary.adjudication.promotion_block_reason or "n/a"],
        [
            "discriminator_stop_reason",
            (
                summary.adjudication.discriminator_stop_reason.value
                if summary.adjudication.discriminator_stop_reason is not None
                else "n/a"
            ),
        ],
        ["equivalence_clusters", f"{len(summary.equivalence_clusters)}"],
        ["unresolved_fronts", f"{len(summary.adjudication.weakest_unresolved_edges)}"],
    ]
    weakest_edge_rows = [
        [
            edge.left_tranche_id,
            edge.left_slice_id,
            edge.right_tranche_id,
            edge.right_slice_id,
            f"{edge.equivalence_margin:.3f}",
            ",".join(edge.tested_axes) if edge.tested_axes else "n/a",
        ]
        for edge in summary.adjudication.weakest_unresolved_edges[:10]
    ]
    discriminator_rows = [
        [
            entry.tranche_id,
            f"{entry.generation}",
            "/".join(entry.target_hypothesis_pair),
            entry.discriminator_axis,
            f"{entry.discriminator_gain:.3f}",
            ",".join(entry.tested_axes) if entry.tested_axes else entry.discriminator_axis,
            (
                "; ".join(
                    f"{item.axis_key}:{item.reason}"
                    for item in entry.rejected_axes
                )
                if entry.rejected_axes
                else "none"
            ),
            entry.stop_reason.value if entry.stop_reason is not None else "n/a",
        ]
        for entry in summary.discriminator_history[:10]
    ]
    winners_rows = [
        [
            winner.tranche_id,
            winner.slice_id,
            winner.scoring_profile,
            winner.candidate_id or "n/a",
            f"{winner.score:.3f}" if winner.score is not None else "n/a",
            winner.status.value,
        ]
        for winner in summary.per_slice_winners
    ]
    leaderboard_rows = [
        [
            f"{index + 1}",
            aggregate.genome_id,
            aggregate.parent_structure_id,
            f"{aggregate.robustness_score:.3f}",
            f"{aggregate.mean_rank:.2f}",
            f"{aggregate.profile_sensitivity_score:.3f}",
        ]
        for index, aggregate in enumerate(summary.aggregate_rankings[:10])
    ]
    comparison_rows = [
        [
            comparison.left_slice_id,
            comparison.right_slice_id,
            f"{comparison.overlap_count}",
            f"{comparison.jaccard_index:.3f}",
            "yes" if comparison.same_winner else "no",
        ]
        for comparison in summary.cross_slice_comparisons[:12]
    ]
    adaptive_rows = [
        ["initial_utility_seeds", f"{summary.adaptive_audit.initial_utility_seeds}"],
        ["utility_updates", f"{summary.adaptive_audit.utility_updates}"],
        ["refinements_generated", f"{summary.adaptive_audit.refinements_generated}"],
        ["refinements_skipped", f"{summary.adaptive_audit.refinements_skipped}"],
        ["slices_pruned", f"{summary.adaptive_audit.slices_pruned}"],
        ["pruning_retained", f"{summary.adaptive_audit.pruning_retained}"],
        ["cross_tranche_generated", f"{summary.adaptive_audit.cross_tranche_generated}"],
        ["cross_tranche_skipped", f"{summary.adaptive_audit.cross_tranche_skipped}"],
        ["utility_warning_slices", f"{summary.adaptive_audit.utility_warning_slices}"],
    ]
    null_model_rows = [
        ["requested_slices", f"{summary.null_model_summary.requested_slices}"],
        ["available_slices", f"{summary.null_model_summary.available_slices}"],
        ["winner_changed_slices", f"{summary.null_model_summary.winner_changed_slices}"],
        [
            "mean_top_candidate_delta",
            (
                f"{summary.null_model_summary.mean_top_candidate_delta:.3f}"
                if summary.null_model_summary.mean_top_candidate_delta is not None
                else "n/a"
            ),
        ],
        [
            "mean_score_delta",
            (
                f"{summary.null_model_summary.mean_score_delta:.3f}"
                if summary.null_model_summary.mean_score_delta is not None
                else "n/a"
            ),
        ],
        [
            "positive_delta_rate",
            (
                f"{summary.null_model_summary.positive_delta_rate:.3f}"
                if summary.null_model_summary.positive_delta_rate is not None
                else "n/a"
            ),
        ],
    ]
    execution_rows = (
        [
            [
                f"{entry.priority_order}",
                entry.tranche_id,
                entry.slice_id,
                f"{entry.phase}",
                entry.source,
                f"{entry.utility_score:.3f}",
                f"{entry.queue_serial if entry.queue_serial is not None else 'n/a'}",
            ]
            for entry in (manifest.execution_order[:15] if manifest is not None else [])
        ]
        if manifest is not None
        else []
    )

    lines = [
        f"# Sweep Summary: {summary.sweep_name}",
        "",
        "## Status",
        "",
        f"- Sweep ID: `{summary.sweep_id}`",
        f"- Successful slices: `{summary.successful_slices}`",
        f"- Failed slices: `{summary.failed_slices}`",
        f"- Pruned slices: `{summary.pruned_slices}`",
        (
            f"- Legacy contract downgrade: `{'; '.join(summary.legacy_contract_notes)}`"
            if summary.legacy_contract_downgrade
            else "- Legacy contract downgrade: `none`"
        ),
        "",
        "## Highlights",
        "",
    ]
    lines.extend(f"- {highlight}" for highlight in summary.summary_highlights)
    lines.extend(
        [
            "",
            "## Adaptive Audit",
            "",
            markdown_table(["Metric", "Value"], adaptive_rows),
            "",
            "## Null-Model Rollup",
            "",
            markdown_table(["Metric", "Value"], null_model_rows),
            "",
            "## Governance",
            "",
            markdown_table(["Metric", "Value"], governance_rows),
            "",
            "## Aggregate Leaderboard",
            "",
            markdown_table(
                ["Rank", "Genome", "Structure", "Robustness", "Mean Rank", "Sensitivity"],
                leaderboard_rows or [["n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Slice Winners",
            "",
            markdown_table(
                ["Tranche", "Slice", "Profile", "Winner", "Score", "Status"],
                winners_rows or [["n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Cross-Slice Comparisons",
            "",
            markdown_table(
                ["Left Slice", "Right Slice", "Top-K Overlap", "Jaccard", "Same Winner"],
                comparison_rows or [["n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Weakest Unresolved Edges",
            "",
            markdown_table(
                ["Left Tranche", "Left Slice", "Right Tranche", "Right Slice", "Margin", "Tested Axes"],
                weakest_edge_rows or [["n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Discriminator History",
            "",
            markdown_table(
                ["Tranche", "Generation", "Pair", "Axis", "Gain", "Tested", "Rejected", "Stop Reason"],
                discriminator_rows or [["n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Execution Ledger",
            "",
            markdown_table(
                ["Order", "Tranche", "Slice", "Phase", "Source", "Utility", "Queue Serial"],
                execution_rows or [["n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Metric Notes",
            "",
            (
                "- `robustness_score` is a software comparison metric that rewards "
                "repeatably strong rank positions across successful slices."
            ),
            (
                "- `profile_sensitivity_score` is a software comparison metric that "
                "surfaces candidates whose relative standing changes sharply across slices."
            ),
            "- These metrics summarize surrogate-ranking behavior only and are not physics claims.",
            "",
        ]
    )
    return "\n".join(lines)


def render_tranche_summary_markdown(summary: TrancheSummary) -> str:
    governance_rows = [
        [
            "recommendation",
            summary.adjudication.recommendation.value if summary.adjudication is not None else "n/a",
        ],
        [
            "promotion_blocked",
            (
                "yes"
                if summary.adjudication is not None and summary.adjudication.promotion_blocked
                else "no"
            ),
        ],
        [
            "promotion_block_reason",
            (
                summary.adjudication.promotion_block_reason
                if summary.adjudication is not None
                else "n/a"
            )
            or "n/a",
        ],
        [
            "discriminator_stop_reason",
            (
                summary.adjudication.discriminator_stop_reason.value
                if summary.adjudication is not None
                and summary.adjudication.discriminator_stop_reason is not None
                else "n/a"
            ),
        ],
    ]
    weakest_edge_rows = [
        [
            edge.left_slice_id,
            edge.right_slice_id,
            f"{edge.equivalence_margin:.3f}",
            ",".join(edge.tested_axes) if edge.tested_axes else "n/a",
        ]
        for edge in (
            summary.adjudication.weakest_unresolved_edges[:10]
            if summary.adjudication is not None
            else []
        )
    ]
    discriminator_rows = [
        [
            entry.tranche_id,
            f"{entry.generation}",
            entry.discriminator_axis,
            f"{entry.discriminator_gain:.3f}",
            ",".join(entry.tested_axes) if entry.tested_axes else entry.discriminator_axis,
            (
                "; ".join(
                    f"{item.axis_key}:{item.reason}"
                    for item in entry.rejected_axes
                )
                if entry.rejected_axes
                else "none"
            ),
        ]
        for entry in (
            summary.adjudication.discriminator_history[:10]
            if summary.adjudication is not None
            else []
        )
    ]
    winner_rows = [
        [
            winner.slice_id,
            winner.scoring_profile,
            winner.candidate_id or "n/a",
            f"{winner.score:.3f}" if winner.score is not None else "n/a",
            winner.status.value,
        ]
        for winner in summary.slice_winners
    ]
    leaderboard_rows = [
        [
            f"{index + 1}",
            aggregate.genome_id,
            f"{aggregate.robustness_score:.3f}",
            f"{aggregate.mean_rank:.2f}",
            f"{aggregate.profile_sensitivity_score:.3f}",
        ]
        for index, aggregate in enumerate(summary.candidate_leaderboard[:10])
    ]
    overlap_rows = [
        [
            comparison.left_slice_id,
            comparison.right_slice_id,
            f"{comparison.overlap_count}",
            f"{comparison.jaccard_index:.3f}",
        ]
        for comparison in summary.overlap_matrix
    ]
    adaptive_rows = [
        ["initial_utility_seeds", f"{summary.adaptive_audit.initial_utility_seeds}"],
        ["utility_updates", f"{summary.adaptive_audit.utility_updates}"],
        ["refinements_generated", f"{summary.adaptive_audit.refinements_generated}"],
        ["refinements_skipped", f"{summary.adaptive_audit.refinements_skipped}"],
        ["slices_pruned", f"{summary.adaptive_audit.slices_pruned}"],
        ["pruning_retained", f"{summary.adaptive_audit.pruning_retained}"],
        ["utility_warning_slices", f"{summary.adaptive_audit.utility_warning_slices}"],
    ]
    null_model_rows = [
        ["requested_slices", f"{summary.null_model_summary.requested_slices}"],
        ["available_slices", f"{summary.null_model_summary.available_slices}"],
        ["winner_changed_slices", f"{summary.null_model_summary.winner_changed_slices}"],
        [
            "mean_top_candidate_delta",
            (
                f"{summary.null_model_summary.mean_top_candidate_delta:.3f}"
                if summary.null_model_summary.mean_top_candidate_delta is not None
                else "n/a"
            ),
        ],
        [
            "mean_score_delta",
            (
                f"{summary.null_model_summary.mean_score_delta:.3f}"
                if summary.null_model_summary.mean_score_delta is not None
                else "n/a"
            ),
        ],
        [
            "positive_delta_rate",
            (
                f"{summary.null_model_summary.positive_delta_rate:.3f}"
                if summary.null_model_summary.positive_delta_rate is not None
                else "n/a"
            ),
        ],
    ]
    slice_audit_rows = [
        [
            record.slice_id,
            f"{record.phase}",
            record.status.value,
            f"{record.utility.utility_score:.3f}",
            record.utility.utility_basis,
            (
                ", ".join(code.value for code in record.utility.trace.warning_codes)
                if record.utility.trace.warning_codes
                else "none"
            ),
            (
                record.pruning_decision.reason_code.value
                if record.pruning_decision is not None
                and record.pruning_decision.reason_code is not None
                else "n/a"
            ),
            (
                f"{record.null_model_comparison.mean_score_delta:.3f}"
                if record.null_model_comparison.available
                and record.null_model_comparison.mean_score_delta is not None
                else "n/a"
            ),
        ]
        for record in summary.slice_records
    ]

    return "\n".join(
        [
            f"# Tranche Summary: {summary.tranche_id}",
            "",
            f"- Objective: {summary.objective}",
            f"- Status: `{summary.status.value}`",
            f"- Successful slices: `{summary.successful_slices}`",
            f"- Failed slices: `{summary.failed_slices}`",
            f"- Pruned slices: `{summary.pruned_slices}`",
            "",
            "## Winner Consistency",
            "",
            f"- Dominant winner: `{summary.winner_consistency.dominant_candidate_id or 'n/a'}`",
            f"- Dominant win count: `{summary.winner_consistency.dominant_win_count}`",
            (
                "- Winner consistency ratio: "
                f"`{summary.winner_consistency.winner_consistency_ratio:.3f}`"
            ),
            "",
            "## Adaptive Audit",
            "",
            markdown_table(["Metric", "Value"], adaptive_rows),
            "",
            "## Null-Model Rollup",
            "",
            markdown_table(["Metric", "Value"], null_model_rows),
            "",
            "## Governance",
            "",
            markdown_table(["Metric", "Value"], governance_rows),
            "",
            "## Slice Winners",
            "",
            markdown_table(
                ["Slice", "Profile", "Winner", "Score", "Status"],
                winner_rows or [["n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Candidate Leaderboard",
            "",
            markdown_table(
                ["Rank", "Genome", "Robustness", "Mean Rank", "Sensitivity"],
                leaderboard_rows or [["n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Slice Audit",
            "",
            markdown_table(
                [
                    "Slice",
                    "Phase",
                    "Status",
                    "Utility",
                    "Basis",
                    "Warnings",
                    "Prune Reason",
                    "Mean Delta",
                ],
                slice_audit_rows or [["n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Slice Overlap",
            "",
            markdown_table(
                ["Left Slice", "Right Slice", "Top-K Overlap", "Jaccard"],
                overlap_rows or [["n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Weakest Unresolved Edges",
            "",
            markdown_table(
                ["Left Slice", "Right Slice", "Margin", "Tested Axes"],
                weakest_edge_rows or [["n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
            "## Discriminator History",
            "",
            markdown_table(
                ["Tranche", "Generation", "Axis", "Gain", "Tested", "Rejected"],
                discriminator_rows or [["n/a", "n/a", "n/a", "n/a", "n/a", "n/a"]],
            ),
            "",
        ]
    )


def load_sweep_manifest(path: str | Path) -> SweepManifest:
    manifest_path = Path(path)
    if manifest_path.is_dir():
        manifest_path = manifest_path / "sweep_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return SweepManifest.model_validate(payload)


def load_sweep_summary(path: str | Path) -> SweepSummary:
    summary_path = Path(path)
    if summary_path.is_dir():
        summary_path = summary_path / "sweep_summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return load_sweep_summary_payload(payload)


def load_tranche_summary(path: str | Path, tranche_id: str) -> TrancheSummary:
    root = Path(path)
    if not root.is_dir():
        root = root.parent
    summary_path = root / "tranches" / tranche_id / "tranche_summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return load_tranche_summary_payload(payload)


def _plot_cross_slice_score_matrix(
    summary: SweepSummary,
    slice_results: dict[tuple[str, str], list[ScoreResult]],
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not summary.aggregate_rankings:
        return

    top_candidates = [aggregate.genome_id for aggregate in summary.aggregate_rankings[:10]]
    slice_keys = sorted(slice_results)
    matrix: list[list[float]] = []
    for candidate_id in top_candidates:
        row: list[float] = []
        for key in slice_keys:
            results = slice_results[key]
            result = next((item for item in results if item.genome_id == candidate_id), None)
            row.append(result.score if result is not None else 0.0)
        matrix.append(row)

    if not matrix or not slice_keys:
        return

    fig, ax = plt.subplots(
        figsize=(max(8, len(slice_keys) * 1.2), max(6, len(top_candidates) * 0.6))
    )
    image = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(slice_keys)))
    ax.set_xticklabels(
        [f"{tranche}/{slice_id}" for tranche, slice_id in slice_keys], rotation=45, ha="right"
    )
    ax.set_yticks(range(len(top_candidates)))
    ax.set_yticklabels(top_candidates)
    ax.set_title("Cross-Slice Score Comparison")
    fig.colorbar(image, ax=ax, label="Surrogate score")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def _plot_robustness_overview(summary: SweepSummary, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not summary.aggregate_rankings:
        return

    aggregates = summary.aggregate_rankings[:10]
    labels = [aggregate.genome_id for aggregate in aggregates]
    robustness = [aggregate.robustness_score for aggregate in aggregates]
    sensitivity = [aggregate.profile_sensitivity_score for aggregate in aggregates]

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.barh(labels, robustness, color="#2f6b7a", alpha=0.88, label="robustness_score")
    ax.scatter(sensitivity, labels, color="#d17a22", s=80, label="profile_sensitivity_score")
    ax.set_xlabel("Metric value")
    ax.set_title("Candidate Robustness Overview")
    ax.legend(loc="lower right")
    ax.set_facecolor("#fbf8f1")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)
