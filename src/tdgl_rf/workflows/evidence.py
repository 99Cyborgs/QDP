"""Evidence bundle generation for the validated deterministic phase-1 baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Any

from tdgl_rf.config.loaders import repo_root
from tdgl_rf.exceptions import ConfigError
from tdgl_rf.io.reports import write_json
from tdgl_rf.workflows.run_matrix import load_experiment_matrix
from tdgl_rf.workflows.validation import load_threshold_spec


@dataclass(frozen=True)
class EvidenceBundleInputs:
    validation_dir: str
    validation_summary_json_path: str
    validation_summary_csv_path: str
    validation_report_path: str
    campaign_summary_json_path: str
    campaign_summary_csv_path: str
    campaign_summary_markdown_path: str
    reference_check_json_path: str
    reference_check_markdown_path: str
    refinement_summary_json_path: str
    refinement_summary_csv_path: str
    matrix_path: str
    thresholds_path: str
    reference_manifest_path: str
    refinement_config_path: str
    validation_memo_path: str
    validation_campaign_doc_path: str
    acceptance_doc_path: str


@dataclass(frozen=True)
class EvidenceBundleSummary:
    status: str
    validation_dir: str
    output_dir: str
    overview_path: str
    technical_summary_path: str
    operating_conditions_path: str
    limitations_path: str
    refinement_summary_path: str
    manifest_path: str
    copied_artifact_count: int
    generated_artifact_count: int


DEFAULT_PHASE1_SURFACE = {
    "surface_id": "phase1_short_horizon_legacy",
    "display_name": "Deterministic Phase-1",
    "claim_scope": "Short-horizon deterministic strip and simple masked-strip baseline with conservative numerical gates on the committed matrix surface only.",
    "reproduction_command": "tdgl-rf validate-phase1 matrices/phase1_validation_matrix_v1.csv validation/thresholds.yaml validation/reference_manifest.yaml configs/phase1_refinement_sanity.yaml",
    "accepted_use": "Cite the current runtime as a short-horizon deterministic baseline for strip and simple masked-strip runs inside the validated matrix surface.",
    "not_established": [
        "Asymptotic convergence certification.",
        "PETSc parity or broader cross-stack reproducibility.",
        "Stochastic robustness or ensemble behavior.",
        "Seeded-vortex support or broader geometry support beyond the committed phase-1 surface.",
        "Long-horizon or very-long-time stability beyond the committed short-horizon matrix.",
        "Broader physics-validation or external-benchmark claims.",
    ],
}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ConfigError(f"expected JSON object payload at {path}")
    return payload


def _require_file(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"missing {label}: {resolved}")
    return resolved


def _copy_file(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return str(destination)


def _format_value(value: Any, *, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _format_sequence(values: list[Any], *, digits: int = 4) -> str:
    rendered: list[str] = []
    for value in values:
        if isinstance(value, float):
            rendered.append(f"{value:.{digits}f}")
        else:
            rendered.append(str(value))
    return ", ".join(rendered)


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    rule_row = "| " + " | ".join("---" for _ in headers) + " |"
    body_rows = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_row, rule_row, *body_rows, ""])


def _unique_sorted(records: list[dict[str, Any]], key: str) -> list[Any]:
    values = {record.get(key) for record in records if record.get(key) is not None}
    return sorted(values)


def _matrix_unique_values(matrix_path: Path, key: str) -> list[Any]:
    rows = load_experiment_matrix(matrix_path)
    values = {row.values.get(key) for row in rows if row.values.get(key) is not None}
    return sorted(values)


def _default_output_dir(validation_dir: Path) -> Path:
    matrix_stem = validation_dir.parent.name if validation_dir.parent != validation_dir else validation_dir.name
    return (repo_root() / "runs" / "evidence" / matrix_stem / validation_dir.name).resolve()


def _phase1_surface(validation_payload: dict[str, Any]) -> dict[str, Any]:
    surface = validation_payload.get("surface")
    if not isinstance(surface, dict):
        return dict(DEFAULT_PHASE1_SURFACE)
    resolved = dict(DEFAULT_PHASE1_SURFACE)
    resolved.update(surface)
    return resolved


def _extract_markdown_bullets(path: Path, heading: str) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    marker = f"## {heading}"
    in_section = False
    bullets: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            if in_section:
                break
            in_section = stripped == marker
            continue
        if in_section and stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    if not bullets:
        raise ConfigError(f"markdown section '{heading}' was missing or empty in {path}")
    return bullets


def resolve_evidence_bundle_inputs(validation_dir: str | Path) -> EvidenceBundleInputs:
    validation_path = Path(validation_dir).resolve()
    if not validation_path.exists() or not validation_path.is_dir():
        raise FileNotFoundError(f"validation directory does not exist: {validation_path}")

    validation_summary_json_path = _require_file(validation_path / "validation_summary.json", label="validation summary json")
    validation_summary_csv_path = _require_file(validation_path / "validation_summary.csv", label="validation summary csv")
    validation_report_path = _require_file(validation_path / "validation_report.md", label="validation report markdown")

    campaign_summary_json_path = _require_file(
        validation_path / "campaign_summary" / "proposal_summary.json",
        label="campaign summary json",
    )
    campaign_summary_csv_path = _require_file(
        validation_path / "campaign_summary" / "proposal_summary.csv",
        label="campaign summary csv",
    )
    campaign_summary_markdown_path = _require_file(
        validation_path / "campaign_summary" / "proposal_summary.md",
        label="campaign summary markdown",
    )
    reference_check_json_path = _require_file(
        validation_path / "reference_checks" / "reference_check.json",
        label="reference check json",
    )
    reference_check_markdown_path = _require_file(
        validation_path / "reference_checks" / "reference_check.md",
        label="reference check markdown",
    )
    refinement_summary_json_path = _require_file(
        validation_path / "refinement_sanity" / "comparison_table.json",
        label="refinement summary json",
    )
    refinement_summary_csv_path = _require_file(
        validation_path / "refinement_sanity" / "comparison_table.csv",
        label="refinement summary csv",
    )

    validation_payload = _read_json(validation_summary_json_path)
    matrix_path = _require_file(Path(str(validation_payload.get("matrix_path"))), label="matrix definition")
    thresholds_path = _require_file(Path(str(validation_payload.get("thresholds_path"))), label="threshold spec")
    reference_manifest_path = _require_file(
        Path(str(validation_payload.get("reference_manifest_path"))),
        label="reference manifest",
    )
    refinement_config_path = _require_file(
        Path(str(validation_payload.get("refinement_config_path"))),
        label="refinement config",
    )

    docs_root = repo_root() / "docs"
    validation_memo_path = _require_file(docs_root / "PHASE1_VALIDATION_MEMO.md", label="validation memo")
    validation_campaign_doc_path = _require_file(
        docs_root / "PHASE1_VALIDATION_CAMPAIGN.md",
        label="validation campaign document",
    )
    acceptance_doc_path = _require_file(docs_root / "PHASE1_ACCEPTANCE.md", label="phase-1 acceptance document")

    return EvidenceBundleInputs(
        validation_dir=str(validation_path),
        validation_summary_json_path=str(validation_summary_json_path),
        validation_summary_csv_path=str(validation_summary_csv_path),
        validation_report_path=str(validation_report_path),
        campaign_summary_json_path=str(campaign_summary_json_path),
        campaign_summary_csv_path=str(campaign_summary_csv_path),
        campaign_summary_markdown_path=str(campaign_summary_markdown_path),
        reference_check_json_path=str(reference_check_json_path),
        reference_check_markdown_path=str(reference_check_markdown_path),
        refinement_summary_json_path=str(refinement_summary_json_path),
        refinement_summary_csv_path=str(refinement_summary_csv_path),
        matrix_path=str(matrix_path),
        thresholds_path=str(thresholds_path),
        reference_manifest_path=str(reference_manifest_path),
        refinement_config_path=str(refinement_config_path),
        validation_memo_path=str(validation_memo_path),
        validation_campaign_doc_path=str(validation_campaign_doc_path),
        acceptance_doc_path=str(acceptance_doc_path),
    )


def generate_operating_conditions_markdown(
    validation_payload: dict[str, Any],
    *,
    matrix_path: str | Path,
    thresholds_path: str | Path,
) -> str:
    campaign = validation_payload["campaign"]
    reference = validation_payload["reference"]
    reproducibility = validation_payload["reproducibility"]
    campaign_records = list(campaign.get("records", []))
    refinement_records = list(validation_payload["refinement"].get("records", []))
    thresholds = load_threshold_spec(thresholds_path)
    surface = _phase1_surface(validation_payload)

    geometry_values = _unique_sorted(campaign_records, "geometry_family")
    mesh_values = sorted({f"{int(record['nx'])}x{int(record['ny'])}" for record in campaign_records if record.get("nx") is not None and record.get("ny") is not None})
    amplitude_values = _matrix_unique_values(Path(matrix_path), "a_rf")
    frequency_values = _matrix_unique_values(Path(matrix_path), "omega")
    dt_values = _matrix_unique_values(Path(matrix_path), "dt")
    step_values = _matrix_unique_values(Path(matrix_path), "n_steps")
    refinement_dt_values = _unique_sorted(refinement_records, "dt")
    reference_ids = [str(record["reference_id"]) for record in reference.get("records", []) if record.get("reference_id")]

    rows = [
        [
            "Phase surface",
            f"`{surface['display_name']}`; deterministic phase `D` only",
            surface["claim_scope"],
        ],
        [
            "Geometry families",
            _format_sequence(geometry_values),
            f"Campaign acceptable rows `{campaign['pass_count']}/{campaign['case_count']}`",
        ],
        [
            "Mesh levels",
            _format_sequence(mesh_values, digits=0),
            "Campaign rows plus refinement sanity cross-check",
        ],
        [
            "RF amplitude `a_rf`",
            _format_sequence(amplitude_values, digits=3),
            "Validation matrix rows",
        ],
        [
            "RF frequency `omega`",
            _format_sequence(frequency_values, digits=3),
            "Validation matrix rows",
        ],
        [
            "Campaign timestep / horizon",
            f"`dt={_format_sequence(dt_values, digits=4)}`; `n_steps={_format_sequence(step_values, digits=0)}`",
            "Validation matrix definition",
        ],
        [
            "Refinement sanity timesteps",
            _format_sequence(refinement_dt_values, digits=4),
            "Committed refinement sanity harness",
        ],
        [
            "Campaign gates",
            f"`final_charge_residual_inf <= {thresholds['campaign']['max_charge_residual_inf']}`; `max_vortex_count <= {thresholds['campaign']['max_vortex_count']}`",
            "Committed threshold spec",
        ],
        [
            "Reference controls",
            f"`{reference['pass_count']}/{reference['case_count']}` matched; ids: `{', '.join(reference_ids)}`",
            "Frozen reference manifest and reference check",
        ],
        [
            "Reproducibility control",
            "exact same-stack equality on selected summary metrics and final observables" if reproducibility.get("overall_pass") else "check failed",
            "Deterministic reproducibility check",
        ],
    ]

    lines = [
        "# Recorded Operating Conditions",
        "",
        f"This table records the deterministic operating surface explicitly characterized by `{surface['display_name']}`.",
        "",
        _markdown_table(["Condition", "Validated values", "Evidence"], rows),
    ]
    return "\n".join(lines)


def generate_limitations_markdown(
    *,
    acceptance_path: str | Path,
    memo_path: str | Path,
) -> str:
    acceptance_unsupported = _extract_markdown_bullets(Path(acceptance_path), "Unsupported or explicitly out of scope")
    memo_not_established = _extract_markdown_bullets(Path(memo_path), "What This Does Not Establish")
    memo_future_work = _extract_markdown_bullets(Path(memo_path), "Future Validation Still Required")

    def _require_match(source: list[str], keyword: str, label: str) -> None:
        if not any(keyword in bullet.lower() for bullet in source):
            raise ConfigError(f"{label} was not found in the supporting phase-1 documents")

    _require_match(acceptance_unsupported, "stochastic", "stochastic limitation")
    _require_match(acceptance_unsupported, "petsc", "PETSc limitation")
    _require_match(acceptance_unsupported, "seeded-vortex", "seeded-vortex limitation")
    _require_match(memo_not_established, "long-horizon", "long-horizon limitation")
    _require_match(memo_not_established, "publication-grade", "physics-validation limitation")
    _require_match(memo_future_work, "external benchmark", "external benchmark limitation")

    rows = [
        [
            "Stochastic noise / ensembles",
            "unsupported in the current phase-1 runtime and not validated by the deterministic tranche",
            "Acceptance boundary; validation memo",
        ],
        [
            "Seeded-vortex initial conditions",
            "unsupported in the accepted phase-1 surface",
            "Acceptance boundary",
        ],
        [
            "PETSc parity / larger-scale runs",
            "not yet validated; separate backend and scale evidence is required before proposal-facing claims",
            "Acceptance boundary; validation memo",
        ],
        [
            "Long-horizon deterministic behavior",
            "not established beyond the short validation horizon used in the current matrix and refinement checks",
            "Validation memo",
        ],
        [
            "Asymptotic convergence certification",
            "not established beyond the committed refinement sanity harness",
            "Acceptance boundary; validation memo",
        ],
        [
            "Broader geometry / boundary-condition regimes",
            "not validated for proposal use beyond the strip and simple masked-strip surfaces summarized here",
            "Acceptance boundary; validation memo",
        ],
        [
            "Broad physics or external-benchmark claims",
            "not supported by the current local evidence bundle",
            "Acceptance boundary; validation memo",
        ],
    ]

    lines = [
        "# Known Limitations And Unsupported Regimes",
        "",
        "This table compresses the current scope limits that remain in force after deterministic phase-1 validation.",
        "",
        _markdown_table(["Area", "Current status", "Basis"], rows),
    ]
    return "\n".join(lines)


def generate_refinement_summary_markdown(refinement_payload: dict[str, Any]) -> str:
    results = list(refinement_payload.get("results", []))
    if not isinstance(results, list) or not results:
        raise ConfigError("refinement summary payload must define a non-empty results list")

    rows: list[list[str]] = []
    for row in results:
        rows.append(
            [
                str(row.get("case_id", "n/a")),
                str(row.get("mesh_level", "n/a")),
                _format_value(row.get("dt"), digits=4),
                _format_value(row.get("delta_mean_abs2_vs_reference")),
                _format_value(row.get("delta_charge_residual_inf_vs_reference")),
                _format_value(row.get("delta_delta_f_over_f0_vs_reference")),
                _format_value(row.get("delta_qinv_vs_reference")),
            ]
        )

    lines = [
        "# Refinement Sanity Summary",
        "",
        "This summary restates the committed refinement sanity comparison used by the deterministic phase-1 validation tranche.",
        "",
        f"- Reference case: `{refinement_payload.get('reference_case_id', 'n/a')}`",
        f"- Compared rows: `{len(results)}`",
        "",
        _markdown_table(
            [
                "case_id",
                "mesh",
                "dt",
                "d(mean_abs2)",
                "d(charge_residual)",
                "d(delta_f_over_f0)",
                "d(qinv)",
            ],
            rows,
        ),
    ]
    return "\n".join(lines)


def generate_technical_summary_markdown(
    validation_payload: dict[str, Any],
    *,
    thresholds_path: str | Path,
) -> str:
    campaign = validation_payload["campaign"]
    refinement = validation_payload["refinement"]
    reference = validation_payload["reference"]
    reproducibility = validation_payload["reproducibility"]
    thresholds = load_threshold_spec(thresholds_path)
    surface = _phase1_surface(validation_payload)

    campaign_records = list(campaign.get("records", []))
    refinement_records = list(refinement.get("records", []))
    if not campaign_records:
        raise ConfigError("validation payload contained zero campaign records")
    if not refinement_records:
        raise ConfigError("validation payload contained zero refinement records")

    worst_charge_row = max(
        campaign_records,
        key=lambda row: float(row.get("final_charge_residual_inf") or float("-inf")),
    )
    worst_refinement_charge = max(
        refinement_records,
        key=lambda row: float(row.get("delta_charge_residual_inf_vs_reference") or float("-inf")),
    )

    geometry_values = _unique_sorted(campaign_records, "geometry_family")
    mesh_values = sorted({f"{int(row['nx'])}x{int(row['ny'])}" for row in campaign_records if row.get("nx") is not None and row.get("ny") is not None})
    amplitude_values = _unique_sorted(campaign_records, "a_rf")
    frequency_values = _unique_sorted(campaign_records, "omega")

    lines = [
        f"# {surface['display_name']} Technical Summary",
        "",
        f"Claim scope: {surface['claim_scope']}",
        "",
        "This note packages the recorded deterministic validation surface for internal technical review. It is bounded local evidence, not authorization for broader solver claims or phase-2 feature work.",
        "",
        "## Evidence Snapshot",
        "",
        f"- Overall validation status: `{validation_payload['overall_status']}`",
        f"- Campaign: `{campaign['pass_count']}/{campaign['case_count']}` acceptable rows across geometries `{_format_sequence(geometry_values)}`, meshes `{_format_sequence(mesh_values, digits=0)}`, amplitudes `{_format_sequence(amplitude_values, digits=3)}`, and frequencies `{_format_sequence(frequency_values, digits=3)}`.",
        f"- Highest observed `final_charge_residual_inf`: `{float(worst_charge_row['final_charge_residual_inf']):.6f}` on `{worst_charge_row['case_id']}` against limit `{float(thresholds['campaign']['max_charge_residual_inf']):.6f}`.",
        f"- Refinement sanity: `{refinement['pass_count']}/{refinement['case_count']}` rows within drift limits; largest `d(charge_residual)` was `{float(worst_refinement_charge['delta_charge_residual_inf_vs_reference']):.6f}` on `{worst_refinement_charge['case_id']}`.",
        f"- Frozen references: `{reference['pass_count']}/{reference['case_count']}` matched the committed manifest.",
        f"- Reproducibility: `{'pass' if reproducibility['overall_pass'] else 'fail'}` with payload hash match `{'yes' if reproducibility.get('payload_hash_match') else 'no'}`.",
        "",
        "## Surface Use",
        "",
        f"- {surface['accepted_use']}",
        "- Use the conservative numerical gates, frozen reference outputs, and same-stack reproducibility check as regression-quality controls on the recorded surface.",
        "",
        "## Not Established",
        "",
    ]
    lines.extend([f"- {item}" for item in surface["not_established"]])
    lines.extend(
        [
        "",
        ]
    )
    return "\n".join(lines)


def _bundle_overview_markdown(
    *,
    validation_payload: dict[str, Any],
    validation_dir: Path,
    output_dir: Path,
    generated_files: dict[str, str],
) -> str:
    surface = _phase1_surface(validation_payload)
    lines = [
        f"# {surface['display_name']} Evidence Bundle",
        "",
        f"This bundle packages `{surface['display_name']}` for internal review and bounded claim interpretation. It remains a compact evidence bundle, not a phase-2 authorization by itself.",
        "",
        f"Claim scope: {surface['claim_scope']}",
        "",
        "## Status",
        "",
        f"- Validation outcome: `{validation_payload['overall_status']}`",
        f"- Campaign acceptable rows: `{validation_payload['campaign']['pass_count']}/{validation_payload['campaign']['case_count']}`",
        f"- Refinement sanity rows within bounds: `{validation_payload['refinement']['pass_count']}/{validation_payload['refinement']['case_count']}`",
        f"- Frozen references matched: `{validation_payload['reference']['pass_count']}/{validation_payload['reference']['case_count']}`",
        f"- Deterministic reproducibility: `{'pass' if validation_payload['reproducibility']['overall_pass'] else 'fail'}`",
        "",
        "## Contents",
        "",
        f"- Technical summary: `{Path(generated_files['technical_summary_path']).relative_to(output_dir)}`",
        f"- Recorded operating conditions: `{Path(generated_files['operating_conditions_path']).relative_to(output_dir)}`",
        f"- Known limitations: `{Path(generated_files['limitations_path']).relative_to(output_dir)}`",
        f"- Validation report: `{Path(generated_files['validation_report_path']).relative_to(output_dir)}`",
        f"- Campaign summary: `{Path(generated_files['campaign_summary_markdown_path']).relative_to(output_dir)}`",
        f"- Frozen reference status: `{Path(generated_files['reference_check_markdown_path']).relative_to(output_dir)}`",
        f"- Refinement sanity summary: `{Path(generated_files['refinement_summary_path']).relative_to(output_dir)}`",
        "",
        "## Reproduction",
        "",
        "- Regenerate validation outputs from committed inputs:",
        f"  `{surface['reproduction_command']}`",
        "- Package a completed validation run into this bundle form:",
        f"  `tdgl-rf evidence-bundle {validation_dir}`",
        "",
    ]
    return "\n".join(lines)


def build_evidence_bundle(
    validation_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> EvidenceBundleSummary:
    inputs = resolve_evidence_bundle_inputs(validation_dir)
    validation_path = Path(inputs.validation_dir)
    destination = Path(output_dir).resolve() if output_dir is not None else _default_output_dir(validation_path)
    destination.mkdir(parents=True, exist_ok=True)

    validation_payload = _read_json(Path(inputs.validation_summary_json_path))
    refinement_payload = _read_json(Path(inputs.refinement_summary_json_path))

    copied_paths = {
        "validation_summary_json_path": _copy_file(
            Path(inputs.validation_summary_json_path),
            destination / "source_artifacts" / "validation_summary.json",
        ),
        "validation_summary_csv_path": _copy_file(
            Path(inputs.validation_summary_csv_path),
            destination / "source_artifacts" / "validation_summary.csv",
        ),
        "validation_report_path": _copy_file(
            Path(inputs.validation_report_path),
            destination / "source_artifacts" / "validation_report.md",
        ),
        "campaign_summary_json_path": _copy_file(
            Path(inputs.campaign_summary_json_path),
            destination / "source_artifacts" / "campaign_summary.json",
        ),
        "campaign_summary_csv_path": _copy_file(
            Path(inputs.campaign_summary_csv_path),
            destination / "source_artifacts" / "campaign_summary.csv",
        ),
        "campaign_summary_markdown_path": _copy_file(
            Path(inputs.campaign_summary_markdown_path),
            destination / "source_artifacts" / "campaign_summary.md",
        ),
        "reference_check_json_path": _copy_file(
            Path(inputs.reference_check_json_path),
            destination / "source_artifacts" / "reference_check.json",
        ),
        "reference_check_markdown_path": _copy_file(
            Path(inputs.reference_check_markdown_path),
            destination / "source_artifacts" / "reference_check.md",
        ),
        "refinement_summary_json_path": _copy_file(
            Path(inputs.refinement_summary_json_path),
            destination / "source_artifacts" / "refinement_comparison.json",
        ),
        "refinement_summary_csv_path": _copy_file(
            Path(inputs.refinement_summary_csv_path),
            destination / "source_artifacts" / "refinement_comparison.csv",
        ),
        "matrix_path": _copy_file(
            Path(inputs.matrix_path),
            destination / "inputs" / Path(inputs.matrix_path).name,
        ),
        "thresholds_path": _copy_file(
            Path(inputs.thresholds_path),
            destination / "inputs" / Path(inputs.thresholds_path).name,
        ),
        "reference_manifest_path": _copy_file(
            Path(inputs.reference_manifest_path),
            destination / "inputs" / Path(inputs.reference_manifest_path).name,
        ),
        "refinement_config_path": _copy_file(
            Path(inputs.refinement_config_path),
            destination / "inputs" / Path(inputs.refinement_config_path).name,
        ),
        "validation_memo_path": _copy_file(
            Path(inputs.validation_memo_path),
            destination / "source_docs" / Path(inputs.validation_memo_path).name,
        ),
        "validation_campaign_doc_path": _copy_file(
            Path(inputs.validation_campaign_doc_path),
            destination / "source_docs" / Path(inputs.validation_campaign_doc_path).name,
        ),
        "acceptance_doc_path": _copy_file(
            Path(inputs.acceptance_doc_path),
            destination / "source_docs" / Path(inputs.acceptance_doc_path).name,
        ),
    }

    technical_summary_path = destination / "summaries" / "technical_summary.md"
    operating_conditions_path = destination / "summaries" / "validated_operating_conditions.md"
    limitations_path = destination / "summaries" / "known_limitations.md"
    refinement_summary_path = destination / "summaries" / "refinement_sanity_summary.md"

    technical_summary_path.parent.mkdir(parents=True, exist_ok=True)
    technical_summary_path.write_text(
        generate_technical_summary_markdown(validation_payload, thresholds_path=inputs.thresholds_path),
        encoding="utf-8",
    )
    operating_conditions_path.write_text(
        generate_operating_conditions_markdown(
            validation_payload,
            matrix_path=inputs.matrix_path,
            thresholds_path=inputs.thresholds_path,
        ),
        encoding="utf-8",
    )
    limitations_path.write_text(
        generate_limitations_markdown(
            acceptance_path=inputs.acceptance_doc_path,
            memo_path=inputs.validation_memo_path,
        ),
        encoding="utf-8",
    )
    refinement_summary_path.write_text(generate_refinement_summary_markdown(refinement_payload), encoding="utf-8")

    generated_paths = {
        **copied_paths,
        "technical_summary_path": str(technical_summary_path),
        "operating_conditions_path": str(operating_conditions_path),
        "limitations_path": str(limitations_path),
        "refinement_summary_path": str(refinement_summary_path),
    }

    overview_path = destination / "README.md"
    overview_path.write_text(
        _bundle_overview_markdown(
            validation_payload=validation_payload,
            validation_dir=validation_path,
            output_dir=destination,
            generated_files=generated_paths,
        ),
        encoding="utf-8",
    )
    manifest_path = destination / "manifest.json"
    write_json(
        manifest_path,
        {
            "generated_at": datetime.now().isoformat(),
            "validation_dir": str(validation_path),
            "output_dir": str(destination),
            "overall_status": validation_payload["overall_status"],
            "copied_artifacts": copied_paths,
            "generated_artifacts": {
                "overview_path": str(overview_path),
                "technical_summary_path": str(technical_summary_path),
                "operating_conditions_path": str(operating_conditions_path),
                "limitations_path": str(limitations_path),
                "refinement_summary_path": str(refinement_summary_path),
            },
        },
    )

    return EvidenceBundleSummary(
        status="success",
        validation_dir=str(validation_path),
        output_dir=str(destination),
        overview_path=str(overview_path),
        technical_summary_path=str(technical_summary_path),
        operating_conditions_path=str(operating_conditions_path),
        limitations_path=str(limitations_path),
        refinement_summary_path=str(refinement_summary_path),
        manifest_path=str(manifest_path),
        copied_artifact_count=len(copied_paths),
        generated_artifact_count=5,
    )
