from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from .models import MMMDataset, RunManifest, ScoreResult

DECISION_COLORS = {
    "lead_branch": "#1b5e20",
    "primary_screen": "#1565c0",
    "sandbox_only": "#ef6c00",
    "reject": "#b71c1c",
}


def write_leaderboard_csv(frame: pd.DataFrame, output: str | Path) -> Path:
    """Persist a ranked candidate table."""

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return output


def plot_leaderboard(frame: pd.DataFrame, output: str | Path, top_n: int = 10) -> Path:
    """Create a portfolio-friendly leaderboard plot."""

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plot_frame = frame.head(top_n).copy()
    colors = [DECISION_COLORS.get(value, "#455a64") for value in plot_frame["decision_band"]]

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.scatter(
        plot_frame["fabrication_complexity_score"],
        plot_frame["score"],
        s=120,
        c=colors,
        edgecolors="#102027",
        linewidths=0.8,
    )
    for _, row in plot_frame.iterrows():
        ax.annotate(
            row["genome_id"],
            (row["fabrication_complexity_score"], row["score"]),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=9,
        )

    ax.set_title("MMM Studio Candidate Leaderboard")
    ax.set_xlabel("Fabrication complexity score")
    ax.set_ylabel("Weighted surrogate score")
    ax.set_facecolor("#faf8f2")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_score_breakdown(frame: pd.DataFrame, output: str | Path, top_n: int = 5) -> Path:
    """Create a stacked bar view of the score subcomponents for top candidates."""

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plot_frame = frame.head(top_n).copy()
    component_columns = [
        "coherence_uplift",
        "null_separation",
        "detectability_margin",
        "geometry_scaling_clarity",
        "fabrication_robustness",
        "replication_portability",
        "simulation_confidence",
        "standard_lab_feasibility",
    ]
    component_colors = [
        "#264653",
        "#2a9d8f",
        "#e9c46a",
        "#f4a261",
        "#e76f51",
        "#577590",
        "#4d908e",
        "#90be6d",
    ]

    fig, ax = plt.subplots(figsize=(12, 7))
    left = pd.Series([0.0] * len(plot_frame), index=plot_frame.index)
    for column, color in zip(component_columns, component_colors, strict=True):
        ax.barh(
            plot_frame["genome_id"],
            plot_frame[column],
            left=left,
            color=color,
            alpha=0.88,
            label=column,
        )
        left += plot_frame[column]

    ax.set_title("Top Candidate Score Breakdown")
    ax.set_xlabel("Unweighted component values")
    ax.set_ylabel("Candidate")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_facecolor("#fffdf8")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a small Markdown table without external dependencies."""

    header_row = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_row, divider, *body])


def render_candidate_report(dataset: MMMDataset, result: ScoreResult) -> str:
    """Render a traceable Markdown report for one candidate."""

    genome = dataset.genome_index[result.genome_id]
    structure = dataset.structure_index[result.parent_structure_id]

    component_rows = [
        [
            component.feature,
            f"{component.value:.3f}",
            f"{component.weight:.3f}",
            f"{component.weighted_value:.3f}",
        ]
        for component in result.components
    ]

    return "\n".join(
        [
            f"# Candidate Report: {result.genome_id}",
            "",
            "## Positioning",
            "",
            f"- Structure: `{result.parent_structure_id}` ({structure.name})",
            f"- Screening status: `{result.screening_status}`",
            f"- Scoring profile: `{result.scoring_profile}`",
            f"- Score backend: `{result.score_backend}`",
            f"- Total surrogate score: `{result.score:.3f}`",
            (
                f"- Null-model baseline score: `{result.baseline_score:.3f}`"
                if result.baseline_score is not None
                else "- Null-model baseline score: `n/a`"
            ),
            (
                f"- Primary-minus-baseline delta: `{result.score_delta:.3f}`"
                if result.score_delta is not None
                else "- Primary-minus-baseline delta: `n/a`"
            ),
            f"- Decision band: `{result.decision_band}`",
            f"- Reject reason: `{result.reject_reason or 'none'}`",
            "",
            "## Candidate Metadata",
            "",
            f"- Topology: {genome.lattice_topology}",
            f"- Material system: {genome.material_system}",
            f"- Fabrication complexity: {genome.fabrication_complexity_score}/10",
            f"- Null risk: {genome.null_risk_score}/10",
            f"- Notes: {genome.notes}",
            "",
            "## Score Components",
            "",
            markdown_table(
                ["Feature", "Value", "Weight", "Weighted"],
                component_rows,
            ),
            "",
            "## Interpretation",
            "",
            "- This report is generated from the baseline surrogate scoring pipeline.",
            (
                "- No full-wave electromagnetic, phononic, or measured RF result "
                "is implied by this ranking."
            ),
            "",
        ]
    )


def render_run_report(
    dataset: MMMDataset, results: list[ScoreResult], manifest: RunManifest
) -> str:
    """Render a Markdown summary for a scored run."""

    top_rows = [
        [
            f"{index + 1}",
            result.genome_id,
            result.parent_structure_id,
            f"{result.score:.3f}",
            result.decision_band,
        ]
        for index, result in enumerate(results[:5])
    ]
    artifact_rows = [[name, path] for name, path in sorted(manifest.artifact_paths.items())]

    return "\n".join(
        [
            "# MMM Studio Run Summary",
            "",
            "## Run Metadata",
            "",
            f"- Run ID: `{manifest.run_id}`",
            f"- Created at: `{manifest.created_at.isoformat()}`",
            f"- Dataset root: `{manifest.root}`",
            f"- Scoring profile: `{manifest.scoring_profile}`",
            f"- Score backend: `{manifest.score_backend}`",
            f"- Top candidate: `{manifest.top_candidate_id or 'n/a'}`",
            (
                f"- Mean score delta: `{manifest.metrics['mean_score_delta']:.3f}`"
                if "mean_score_delta" in manifest.metrics
                and manifest.metrics["mean_score_delta"] is not None
                else "- Mean score delta: `n/a`"
            ),
            "",
            "## Top Candidates",
            "",
            markdown_table(
                ["Rank", "Genome", "Structure", "Score", "Band"],
                top_rows,
            ),
            "",
            "## Artifacts",
            "",
            markdown_table(["Artifact", "Path"], artifact_rows),
            "",
            "## Notes",
            "",
            "- Ranking outputs are generated by the baseline surrogate scorer.",
            (
                "- Simulation and RF integrations remain scaffolded unless explicit "
                "backend results are present in the artifact set."
            ),
            "",
        ]
    )
