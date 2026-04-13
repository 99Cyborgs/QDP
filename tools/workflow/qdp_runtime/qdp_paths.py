from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[3]

MODULES_DIR = ROOT / "modules"
TOOLS_DIR = ROOT / "tools"
CONFIG_DIR = ROOT / "config"
ARTIFACTS_DIR = ROOT / "artifacts"
DOCS_DIR = ROOT / "docs"
SPECS_DIR = ROOT / "specs"
RUNTIME_DIR = ROOT / "runtime"

SCHEMA_DIR = CONFIG_DIR / "schema"
MANIFEST_DIR = CONFIG_DIR / "manifests"
REGISTRIES_DIR = CONFIG_DIR / "registries"
CONTRACTS_DIR = CONFIG_DIR / "contracts"
POLICIES_DIR = CONFIG_DIR / "policies"

REPORTS_DIR = ARTIFACTS_DIR / "reports"
OUTPUTS_DIR = ARTIFACTS_DIR / "outputs"
SIMULATION_REPORTS_DIR = REPORTS_DIR / "simulations"
SIMULATION_OUTPUTS_DIR = OUTPUTS_DIR / "simulations"
STATE_DIR = ARTIFACTS_DIR / "state"
CAMPAIGNS_DIR = ARTIFACTS_DIR / "campaigns"
LAB_DIR = ARTIFACTS_DIR / "lab"
LAB_REQUESTS_DIR = LAB_DIR / "requests"
LAB_INGESTIONS_DIR = LAB_DIR / "ingestions"
QUEUE_MANIFESTS_DIR = STATE_DIR / "queue_manifests"
QUEUE_LOGS_DIR = STATE_DIR / "queue_logs"

BASE_TEMPLATE = SCHEMA_DIR / "candidate_template.json"
SCHEMA = SCHEMA_DIR / "candidate_schema.json"
FORK_INTAKE_TEMPLATE = SCHEMA_DIR / "fork_intake_template.json"
FORK_INTAKE_SCHEMA = SCHEMA_DIR / "fork_intake_schema.json"
EXPERIMENT_REQUEST_SCHEMA = SCHEMA_DIR / "experiment_request_schema.json"
INSTRUMENT_PROFILE_SCHEMA = SCHEMA_DIR / "instrument_profile_schema.json"
RUN_RESULT_PACKET_SCHEMA = SCHEMA_DIR / "run_result_packet_schema.json"
CALIBRATION_SNAPSHOT_SCHEMA = SCHEMA_DIR / "calibration_snapshot_schema.json"
LINEAGE_RECORD_SCHEMA = SCHEMA_DIR / "lineage_record_schema.json"
CANDIDATE_ARTIFACT_MANIFEST_SCHEMA = SCHEMA_DIR / "candidate_artifact_manifest_schema.json"
SUBSYSTEM_VERDICT_SCHEMA = SCHEMA_DIR / "subsystem_verdict_schema.json"
ALL_MIND_INTERFACE_SCHEMA = SCHEMA_DIR / "all_mind_interface_schema.json"

CANDIDATE_VALIDATOR = TOOLS_DIR / "validators" / "candidate_validator.py"
FORK_INTAKE_VALIDATOR = TOOLS_DIR / "validators" / "fork_intake_validator.py"

REFERENCE_MANIFEST = MANIFEST_DIR / "reference_manifest.json"
GOVERNANCE_REGISTRY = REGISTRIES_DIR / "governance_registry.json"
RULE_BINDING_REGISTRY = REGISTRIES_DIR / "rule_binding_registry.json"
MODULE_REGISTRY_JSON = REGISTRIES_DIR / "module_registry.json"
MODULE_CLOSURE_CONTRACTS = CONTRACTS_DIR / "module_closure_contracts.json"
MODE_DIVERGENCE_POLICY = POLICIES_DIR / "mode_divergence_policy.json"

MODULE_REGISTRY_MD = DOCS_DIR / "repo" / "module_registry.md"

BUILD_SPEC = SPECS_DIR / "core" / "build_spec.md"
MASTER_SPEC = SPECS_DIR / "core" / "master_spec.md"
VALIDATION_GATE = SPECS_DIR / "core" / "validation_gate.md"
MODEL_SPEC = SPECS_DIR / "core" / "model_spec.md"
BATH_GLOSSARY = SPECS_DIR / "core" / "bath_glossary.md"
SIGNATURE_TO_BATH_CHART = SPECS_DIR / "core" / "signature_to_bath_decision_chart.md"
FALSIFIER_REGISTRY = SPECS_DIR / "core" / "falsifier_registry.md"
FORK_QUESTIONS = SPECS_DIR / "intake" / "fork_questions.md"
FORK_INTAKE_FORM = SPECS_DIR / "intake" / "fork_intake_form_one_page.pdf"
DEEP_RESEARCH_REPORT = SPECS_DIR / "research" / "deep_research_report.md"
VORTEX_PINNING_METHODS = SPECS_DIR / "research" / "vortex_pinning_methods.md"
GKSL_SUBSYSTEM_CASE_MATRIX = SPECS_DIR / "subsystem" / "gksl_subsystem_case_matrix.json"

RUNTIME_PROMPT = RUNTIME_DIR / "current" / "runtime_prompt.md"
RETAINED_OPERATIVE_BODY = RUNTIME_DIR / "retained" / "operative_body_v10_1.md"
SURROGATE_OPERATIVE_BODY = RUNTIME_DIR / "missing" / "operative_body_v10_1.md"
SURROGATE_FEDERATED_REGISTRY_OBJECT = RUNTIME_DIR / "missing" / "federated_governance_registry_object.json"

M01_CLOSURE_REPORT = REPORTS_DIR / "m01" / "closure_report.json"
M01_ASSEMBLY_REPORT = REPORTS_DIR / "m01" / "assembly_report.json"
M02_SELFTEST_REPORT = REPORTS_DIR / "m02" / "selftest_report.json"
M03_ORDINARY_REPORT = REPORTS_DIR / "m03" / "reference_resolution_ordinary.json"
M03_SUBSYSTEM_REPORT = REPORTS_DIR / "m03" / "reference_resolution_subsystem.json"
M04_SELFTEST_REPORT = REPORTS_DIR / "m04" / "selftest_report.json"
M11_SELFTEST_REPORT = REPORTS_DIR / "m11" / "selftest_report.json"
M12_SELFTEST_REPORT = REPORTS_DIR / "m12" / "selftest_report.json"
M13_SELFTEST_REPORT = REPORTS_DIR / "m13" / "selftest_report.json"
M14_SELFTEST_REPORT = REPORTS_DIR / "m14" / "selftest_report.json"
M15_SELFTEST_REPORT = REPORTS_DIR / "m15" / "selftest_report.json"
MODE_DIVERGENCE_REPORT = REPORTS_DIR / "system" / "mode_divergence_report.json"
MODULE_CLOSURE_EVALUATION_REPORT = REPORTS_DIR / "system" / "module_closure_evaluation.json"
ALL_MIND_INTERFACE_REPORT = REPORTS_DIR / "system" / "all_mind_interface.json"
RUN_LEDGER_REPORT = REPORTS_DIR / "system" / "run_ledger.json"
QUEUE_REPORT = REPORTS_DIR / "system" / "queue_report.json"
CAMPAIGN_PLAN_REPORT = REPORTS_DIR / "campaigns" / "latest_plan.json"
CAMPAIGN_PREPARE_REPORT = REPORTS_DIR / "campaigns" / "latest_prepare.json"
LAB_REQUEST_REPORT = REPORTS_DIR / "lab" / "latest_request_pack.json"
LAB_INGEST_REPORT = REPORTS_DIR / "lab" / "latest_ingestion_report.json"
CONTROL_PLANE_DB = STATE_DIR / "control_plane.sqlite3"

ALL_MIND_INTERFACE_PROMOTION_NOTE = "Compact status and interface artifacts only; no whole-repo ingestion."
ALL_MIND_INTERFACE_CALLABLE_SURFACES = [
    {"name": "qdp.py", "command": "python qdp.py"},
    {"name": "qdp_validation.py", "command": "python qdp_validation.py"},
    {"name": "readiness", "command": "python qdp.py readiness"},
    {"name": "validate", "command": "python qdp.py validate <target> --kind candidate --mode final"},
]
ALL_MIND_ALLOWED_CONSUMPTION = [
    "artifacts/reports/system/all_mind_interface.json",
    "STATUS.md",
    "PROMOTION_NOTES.md",
]
ALL_MIND_AUTHORITATIVE_READINESS_FIELDS = (
    "ordinary_authoritative_ready",
    "subsystem_authoritative_ready",
)


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


MODULES: Dict[str, Dict[str, Any]] = {
    "m01": {
        "module_id": "M01",
        "name": "runtime_assembly",
        "runner": MODULES_DIR / "m01_runtime_assembly" / "runner.py",
        "patch_notes": MODULES_DIR / "m01_runtime_assembly" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "m01",
        "selftest_cases": MODULES_DIR / "m01_runtime_assembly" / "selftest_cases.json",
        "selftest_report": M01_ASSEMBLY_REPORT,
        "selftest_output_dir": OUTPUTS_DIR / "m01" / "selftests",
        "run_report_flag": "--write-report",
    },
    "m02": {
        "module_id": "M02",
        "name": "schema_validator",
        "runner": MODULES_DIR / "m02_schema_validator" / "runner.py",
        "patch_notes": MODULES_DIR / "m02_schema_validator" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "m02",
        "selftest_cases": MODULES_DIR / "m02_schema_validator" / "selftest_cases.json",
        "selftest_report": M02_SELFTEST_REPORT,
        "selftest_output_dir": OUTPUTS_DIR / "m02" / "selftests",
        "run_report_flag": "--write-report",
    },
    "m03": {
        "module_id": "M03",
        "name": "reference_resolution",
        "runner": MODULES_DIR / "m03_reference_resolution" / "runner.py",
        "patch_notes": MODULES_DIR / "m03_reference_resolution" / "patch_notes.md",
        "supports_selftest": False,
        "run_defaults": {
            "--manifest": REFERENCE_MANIFEST,
            "--registry": GOVERNANCE_REGISTRY,
            "--root": ROOT,
            "--mode": "ordinary",
            "--write-report": M03_ORDINARY_REPORT,
        },
    },
    "m04": {
        "module_id": "M04",
        "name": "branch_registration",
        "runner": MODULES_DIR / "m04_branch_registration" / "runner.py",
        "patch_notes": MODULES_DIR / "m04_branch_registration" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "m04",
        "selftest_cases": MODULES_DIR / "m04_branch_registration" / "selftest_cases.json",
        "selftest_report": M04_SELFTEST_REPORT,
        "selftest_output_dir": OUTPUTS_DIR / "m04" / "selftests",
        "run_report_flag": "--write-registration",
        "run_defaults": {
            "--candidate-template": BASE_TEMPLATE,
            "--registry": GOVERNANCE_REGISTRY,
            "--intake-schema": FORK_INTAKE_SCHEMA,
        },
    },
    "m05": {
        "module_id": "M05",
        "name": "stage_machine",
        "runner": MODULES_DIR / "m05_stage_machine" / "runner.py",
        "patch_notes": MODULES_DIR / "m05_stage_machine" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "m05",
        "selftest_cases": MODULES_DIR / "m05_stage_machine" / "selftest_cases.json",
        "selftest_report": REPORTS_DIR / "m05" / "selftest_report.json",
        "selftest_output_dir": OUTPUTS_DIR / "m05" / "selftests",
        "run_report_flag": "--write-stage-report",
    },
    "m06": {
        "module_id": "M06",
        "name": "bootstrap_harness",
        "runner": MODULES_DIR / "m06_bootstrap_harness" / "runner.py",
        "patch_notes": MODULES_DIR / "m06_bootstrap_harness" / "patch_notes.md",
        "bootstrap_cases": MODULES_DIR / "m06_bootstrap_harness" / "bootstrap_cases.json",
        "bootstrap_report": REPORTS_DIR / "m06" / "bootstrap_report.json",
        "closure_report": REPORTS_DIR / "m06" / "closure_report.json",
        "output_dir": OUTPUTS_DIR / "m06" / "bootstrap",
        "supports_selftest": False,
    },
    "m07": {
        "module_id": "M07",
        "name": "family_triage",
        "runner": MODULES_DIR / "m07_family_triage" / "runner.py",
        "patch_notes": MODULES_DIR / "m07_family_triage" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "generic",
        "selftest_cases": MODULES_DIR / "m07_family_triage" / "selftest_cases.json",
        "selftest_report": REPORTS_DIR / "m07" / "selftest_report.json",
        "selftest_output_dir": OUTPUTS_DIR / "m07" / "selftests",
        "run_report_flag": "--write-triage-report",
    },
    "m08": {
        "module_id": "M08",
        "name": "baseline_fit",
        "runner": MODULES_DIR / "m08_baseline_fit" / "runner.py",
        "patch_notes": MODULES_DIR / "m08_baseline_fit" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "generic",
        "selftest_cases": MODULES_DIR / "m08_baseline_fit" / "selftest_cases.json",
        "selftest_report": REPORTS_DIR / "m08" / "selftest_report.json",
        "selftest_output_dir": OUTPUTS_DIR / "m08" / "selftests",
        "run_report_flag": "--write-baseline-report",
    },
    "m09": {
        "module_id": "M09",
        "name": "mechanism_competition",
        "runner": MODULES_DIR / "m09_mechanism_competition" / "runner.py",
        "patch_notes": MODULES_DIR / "m09_mechanism_competition" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "generic",
        "selftest_cases": MODULES_DIR / "m09_mechanism_competition" / "selftest_cases.json",
        "selftest_report": REPORTS_DIR / "m09" / "selftest_report.json",
        "selftest_output_dir": OUTPUTS_DIR / "m09" / "selftests",
        "run_report_flag": "--write-mechanism-report",
    },
    "m10": {
        "module_id": "M10",
        "name": "artifact_audit",
        "runner": MODULES_DIR / "m10_artifact_audit" / "runner.py",
        "patch_notes": MODULES_DIR / "m10_artifact_audit" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "generic",
        "selftest_cases": MODULES_DIR / "m10_artifact_audit" / "selftest_cases.json",
        "selftest_report": REPORTS_DIR / "m10" / "selftest_report.json",
        "selftest_output_dir": OUTPUTS_DIR / "m10" / "selftests",
        "run_report_flag": "--write-artifact-report",
    },
    "m11": {
        "module_id": "M11",
        "name": "lindblad_equivalence",
        "runner": MODULES_DIR / "m11_lindblad_equivalence" / "runner.py",
        "patch_notes": MODULES_DIR / "m11_lindblad_equivalence" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "generic",
        "selftest_cases": MODULES_DIR / "m11_lindblad_equivalence" / "selftest_cases.json",
        "selftest_report": M11_SELFTEST_REPORT,
        "selftest_output_dir": OUTPUTS_DIR / "m11" / "selftests",
        "run_report_flag": "--write-report",
    },
    "m12": {
        "module_id": "M12",
        "name": "experiment_design",
        "runner": MODULES_DIR / "m12_experiment_design" / "runner.py",
        "patch_notes": MODULES_DIR / "m12_experiment_design" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "generic",
        "selftest_cases": MODULES_DIR / "m12_experiment_design" / "selftest_cases.json",
        "selftest_report": M12_SELFTEST_REPORT,
        "selftest_output_dir": OUTPUTS_DIR / "m12" / "selftests",
        "run_report_flag": "--write-report",
    },
    "m13": {
        "module_id": "M13",
        "name": "cross_device_gate",
        "runner": MODULES_DIR / "m13_cross_device_gate" / "runner.py",
        "patch_notes": MODULES_DIR / "m13_cross_device_gate" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "generic",
        "selftest_cases": MODULES_DIR / "m13_cross_device_gate" / "selftest_cases.json",
        "selftest_report": M13_SELFTEST_REPORT,
        "selftest_output_dir": OUTPUTS_DIR / "m13" / "selftests",
        "run_report_flag": "--write-report",
    },
    "m14": {
        "module_id": "M14",
        "name": "promotion_caps",
        "runner": MODULES_DIR / "m14_promotion_caps" / "runner.py",
        "patch_notes": MODULES_DIR / "m14_promotion_caps" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "generic",
        "selftest_cases": MODULES_DIR / "m14_promotion_caps" / "selftest_cases.json",
        "selftest_report": M14_SELFTEST_REPORT,
        "selftest_output_dir": OUTPUTS_DIR / "m14" / "selftests",
        "run_report_flag": "--write-report",
    },
    "m15": {
        "module_id": "M15",
        "name": "governance_guardrails",
        "runner": MODULES_DIR / "m15_governance_guardrails" / "runner.py",
        "patch_notes": MODULES_DIR / "m15_governance_guardrails" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "generic",
        "selftest_cases": MODULES_DIR / "m15_governance_guardrails" / "selftest_cases.json",
        "selftest_report": M15_SELFTEST_REPORT,
        "selftest_output_dir": OUTPUTS_DIR / "m15" / "selftests",
        "run_report_flag": "--write-report",
    },
    "s16": {
        "module_id": "S16",
        "name": "subsystem_sector_detection",
        "runner": MODULES_DIR / "s16_subsystem_sector_detection" / "runner.py",
        "patch_notes": MODULES_DIR / "s16_subsystem_sector_detection" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "subsystem",
        "selftest_cases": MODULES_DIR / "s16_subsystem_sector_detection" / "selftest_cases.json",
        "selftest_report": REPORTS_DIR / "s16" / "selftest_report.json",
        "selftest_output_dir": OUTPUTS_DIR / "s16" / "selftests",
        "run_report_flag": "--write-report",
    },
    "s17": {
        "module_id": "S17",
        "name": "subsystem_alias_audit",
        "runner": MODULES_DIR / "s17_subsystem_alias_audit" / "runner.py",
        "patch_notes": MODULES_DIR / "s17_subsystem_alias_audit" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "subsystem",
        "selftest_cases": MODULES_DIR / "s17_subsystem_alias_audit" / "selftest_cases.json",
        "selftest_report": REPORTS_DIR / "s17" / "selftest_report.json",
        "selftest_output_dir": OUTPUTS_DIR / "s17" / "selftests",
        "run_report_flag": "--write-report",
    },
    "s18": {
        "module_id": "S18",
        "name": "subsystem_observable_closure",
        "runner": MODULES_DIR / "s18_subsystem_observable_closure" / "runner.py",
        "patch_notes": MODULES_DIR / "s18_subsystem_observable_closure" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "subsystem",
        "selftest_cases": MODULES_DIR / "s18_subsystem_observable_closure" / "selftest_cases.json",
        "selftest_report": REPORTS_DIR / "s18" / "selftest_report.json",
        "selftest_output_dir": OUTPUTS_DIR / "s18" / "selftests",
        "run_report_flag": "--write-report",
    },
    "s19": {
        "module_id": "S19",
        "name": "subsystem_verdict_gate",
        "runner": MODULES_DIR / "s19_subsystem_verdict_gate" / "runner.py",
        "patch_notes": MODULES_DIR / "s19_subsystem_verdict_gate" / "patch_notes.md",
        "supports_selftest": True,
        "selftest_style": "subsystem",
        "selftest_cases": MODULES_DIR / "s19_subsystem_verdict_gate" / "selftest_cases.json",
        "selftest_report": REPORTS_DIR / "s19" / "selftest_report.json",
        "selftest_output_dir": OUTPUTS_DIR / "s19" / "selftests",
        "run_report_flag": "--write-report",
    },
}

VISIBLE_SOURCE_WORKING_PATCH_MODULES = {
    "M02",
    "M04",
    "M07",
    "M08",
    "M09",
    "M10",
    "M11",
    "M12",
    "M13",
    "M14",
    "M15",
    "S16",
    "S17",
    "S18",
    "S19",
}
AUTHORITATIVE_DEPENDENT_MODULES = {"M01", "M03", "M05", "M06"}

RESUME_POLICY = {
    "ordinary_candidate_testing_requires": [f"M{i:02d}" for i in range(1, 16)],
    "subsystem_testing_requires": [f"M{i:02d}" for i in range(1, 16)] + ["S16", "S17", "S18", "S19"],
}

MODULE_REGISTRY_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "M01": {
        "name": "Runtime assembly and freeze",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Assemble the execution-bearing runtime and capture retained-source provenance.",
        "owner_artifacts": [repo_rel(BUILD_SPEC), repo_rel(RETAINED_OPERATIVE_BODY), repo_rel(SURROGATE_OPERATIVE_BODY)],
        "required_outputs": ["runtime_prompt", "closure_report", "provenance_metadata"],
    },
    "M02": {
        "name": "Schema extension and post-run validator",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Own the v10.6 candidate contract and final-mode validator semantics.",
        "owner_artifacts": [repo_rel(BUILD_SPEC), repo_rel(BASE_TEMPLATE), repo_rel(SCHEMA), repo_rel(CANDIDATE_VALIDATOR)],
        "required_outputs": ["schema", "template", "typed_governance_fields", "validator_semantics"],
    },
    "M03": {
        "name": "Reference-resolution and governance-registry module",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Resolve critical references and federate reference state into governance artifacts.",
        "owner_artifacts": [repo_rel(BUILD_SPEC), repo_rel(MASTER_SPEC), repo_rel(FALSIFIER_REGISTRY)],
        "required_outputs": ["reference_resolution_status", "governance_registry", "mode_reports"],
    },
    "M04": {
        "name": "Fork intake and branch registration",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Map intake artifacts into canonical candidate objects before compute stages.",
        "owner_artifacts": [repo_rel(FORK_INTAKE_FORM), repo_rel(FORK_QUESTIONS), repo_rel(MASTER_SPEC)],
        "required_outputs": ["branch_registration", "candidate_from_intake", "precompute_flags"],
    },
    "M05": {
        "name": "Gate-trace and validation-ladder state machine",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Orchestrate gate stages and emit deterministic gate_trace and validation_ladder outputs.",
        "owner_artifacts": [repo_rel(BUILD_SPEC), repo_rel(VALIDATION_GATE), repo_rel(BASE_TEMPLATE)],
        "required_outputs": ["gate_trace", "validation_ladder", "governance_outcome", "scientific_decision"],
    },
    "M06": {
        "name": "Bootstrap harness runner and fixture loader",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Refresh core reports, selftests, bootstrap fixtures, and readiness evaluation.",
        "owner_artifacts": [repo_rel(BUILD_SPEC), repo_rel(RUN_LEDGER_REPORT), repo_rel(CONTROL_PLANE_DB)],
        "required_outputs": ["bootstrap_report", "closure_evaluation", "readiness_flags", "run_ledger"],
    },
    "M07": {
        "name": "Family-class triage and signature-to-bath scorer",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Assign family class, bath ranking, and minimal discriminant measurement.",
        "owner_artifacts": [repo_rel(BATH_GLOSSARY), repo_rel(SIGNATURE_TO_BATH_CHART), repo_rel(BASE_TEMPLATE)],
        "required_outputs": ["assigned_family_class", "inferred_bath_rank_order", "signature_matches"],
    },
    "M08": {
        "name": "Baseline GKSL fit and drift-aware residual diagnostics",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Populate baseline_model and residual_analysis from the visible-source baseline contract.",
        "owner_artifacts": [repo_rel(MODEL_SPEC), repo_rel(DEEP_RESEARCH_REPORT), repo_rel(BASE_TEMPLATE)],
        "required_outputs": ["baseline_model", "residual_analysis"],
    },
    "M09": {
        "name": "Known-mechanism competition suite",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Score known mechanisms before Hamiltonian escalation.",
        "owner_artifacts": [repo_rel(SIGNATURE_TO_BATH_CHART), repo_rel(VORTEX_PINNING_METHODS), repo_rel(BASE_TEMPLATE)],
        "required_outputs": ["mechanism_tests", "strongest_competing_mechanism"],
    },
    "M10": {
        "name": "Artifact-equivalence audit",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Eliminate classical and systematic artifact routes before promotion.",
        "owner_artifacts": [repo_rel(DEEP_RESEARCH_REPORT), repo_rel(FORK_INTAKE_FORM), repo_rel(BASE_TEMPLATE)],
        "required_outputs": ["artifact_tests"],
    },
    "M11": {
        "name": "Lindblad-equivalence gate",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Evaluate whether the candidate remains equivalent within measurement resolution.",
        "owner_artifacts": [repo_rel(BUILD_SPEC), repo_rel(BASE_TEMPLATE)],
        "required_outputs": ["lindblad_equivalence"],
    },
    "M12": {
        "name": "Executable falsifier and experiment-design module",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Build executable falsifier packs and instrument-facing experiment schedules.",
        "owner_artifacts": [repo_rel(FALSIFIER_REGISTRY), repo_rel(FORK_INTAKE_FORM), repo_rel(VALIDATION_GATE), repo_rel(DEEP_RESEARCH_REPORT)],
        "required_outputs": ["exact_falsifier", "hamiltonian_test", "experiment_schedule"],
    },
    "M13": {
        "name": "Cross-device evidence gate",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Normalize cross-device status and enforce matched-fabrication confirmation rules.",
        "owner_artifacts": [repo_rel(BUILD_SPEC), repo_rel(BASE_TEMPLATE), repo_rel(DEEP_RESEARCH_REPORT)],
        "required_outputs": ["cross_device_status", "cross_device_validation"],
    },
    "M14": {
        "name": "Promotion-cap clipping and fallback completion",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Apply irreversible governance and scientific caps plus deterministic fallback completion.",
        "owner_artifacts": [repo_rel(BUILD_SPEC), repo_rel(BASE_TEMPLATE)],
        "required_outputs": ["promotion_cap_governance", "promotion_cap_scientific", "governance_outcome"],
    },
    "M15": {
        "name": "Calibration, drift, identifiability, and dataset-governance guardrails",
        "blocker_class": "CORE_BLOCKER",
        "purpose": "Populate typed governance guardrails and block promotion on calibration or provenance failures.",
        "owner_artifacts": [repo_rel(BUILD_SPEC), repo_rel(DEEP_RESEARCH_REPORT), repo_rel(BASE_TEMPLATE)],
        "required_outputs": ["calibration_status", "drift_ledger", "identifiability_status", "dataset_governance"],
    },
    "S16": {
        "name": "Subsystem slow-sector detection",
        "blocker_class": "SUBSYSTEM_BLOCKER",
        "purpose": "Detect candidate slow sectors and projector stability from the surfaced GKSL subsystem case matrix.",
        "owner_artifacts": [repo_rel(GKSL_SUBSYSTEM_CASE_MATRIX), repo_rel(SUBSYSTEM_VERDICT_SCHEMA)],
        "required_outputs": ["slow_sector_detected", "projector_stability", "diagnostic_report"],
    },
    "S17": {
        "name": "Subsystem alias and null-baseline audit",
        "blocker_class": "SUBSYSTEM_BLOCKER",
        "purpose": "Evaluate symmetry, artifact, TLS, and null-baseline alias routes for subsystem claims.",
        "owner_artifacts": [repo_rel(GKSL_SUBSYSTEM_CASE_MATRIX), repo_rel(SUBSYSTEM_VERDICT_SCHEMA)],
        "required_outputs": ["symmetry_alias_rejection", "artifact_alias_rejection", "null_baseline_rejection"],
    },
    "S18": {
        "name": "Subsystem finite-horizon and closure gate",
        "blocker_class": "SUBSYSTEM_BLOCKER",
        "purpose": "Check finite-horizon control and observable closure requirements before subsystem promotion.",
        "owner_artifacts": [repo_rel(GKSL_SUBSYSTEM_CASE_MATRIX), repo_rel(SUBSYSTEM_VERDICT_SCHEMA)],
        "required_outputs": ["finite_horizon_control", "observable_closure", "closure_metrics"],
    },
    "S19": {
        "name": "Subsystem verdict gate",
        "blocker_class": "SUBSYSTEM_BLOCKER",
        "purpose": "Aggregate surfaced subsystem gates into supported, inconclusive, or not_supported verdicts.",
        "owner_artifacts": [repo_rel(GKSL_SUBSYSTEM_CASE_MATRIX), repo_rel(SUBSYSTEM_VERDICT_SCHEMA)],
        "required_outputs": ["subsystem_verdict", "verdict_report"],
    },
}


def resolve_module(key: str) -> Dict[str, Any]:
    normalized = key.strip().lower()
    if normalized in MODULES:
        return MODULES[normalized]
    for module in MODULES.values():
        if normalized == str(module.get("module_id", "")).lower():
            return module
        if normalized == str(module.get("name", "")).lower():
            return module
    raise KeyError(f"Unknown module: {key}")


PARTITION_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def normalize_partition_token(value: str, *, field: str) -> str:
    token = str(value or "").strip()
    if not token:
        raise ValueError(f"{field} must not be empty.")
    if token in {".", ".."} or "/" in token or "\\" in token:
        raise ValueError(f"{field} must not contain path separators.")
    if not PARTITION_TOKEN_RE.fullmatch(token):
        raise ValueError(
            f"{field} must start with an alphanumeric character and use only letters, numbers, '.', '_' or '-'."
        )
    return token


def resolve_simulation_partition(
    batch: str | None,
    variant: str | None = None,
    *,
    require_variant: bool = False,
) -> tuple[str | None, str | None]:
    normalized_batch = normalize_partition_token(batch, field="batch") if batch is not None else None
    normalized_variant = normalize_partition_token(variant, field="variant") if variant is not None else None
    if normalized_variant is not None and normalized_batch is None:
        raise ValueError("--variant requires --batch.")
    if require_variant and normalized_batch is not None and normalized_variant is None:
        raise ValueError("--batch requires --variant.")
    return normalized_batch, normalized_variant


def simulation_outputs_root(batch: str) -> Path:
    return SIMULATION_OUTPUTS_DIR / normalize_partition_token(batch, field="batch")


def simulation_reports_root(batch: str) -> Path:
    return SIMULATION_REPORTS_DIR / normalize_partition_token(batch, field="batch")


def simulation_module_candidate_path(batch: str, module_key: str, variant: str) -> Path:
    normalized_batch, normalized_variant = resolve_simulation_partition(batch, variant, require_variant=True)
    module = resolve_module(module_key)
    return simulation_outputs_root(normalized_batch) / module["module_id"].lower() / f"{normalized_variant}_candidate.json"


def simulation_module_report_path(batch: str, module_key: str, variant: str) -> Path:
    normalized_batch, normalized_variant = resolve_simulation_partition(batch, variant, require_variant=True)
    module = resolve_module(module_key)
    return simulation_reports_root(normalized_batch) / module["module_id"].lower() / f"{normalized_variant}_report.json"


def simulation_campaign_report_path(batch: str) -> Path:
    return simulation_reports_root(batch) / "campaign_plan.json"


def simulation_campaign_prepare_report_path(batch: str) -> Path:
    return simulation_reports_root(batch) / "campaign_prepare.json"


def simulation_lab_requests_dir(batch: str) -> Path:
    return LAB_REQUESTS_DIR / normalize_partition_token(batch, field="batch")


def simulation_lab_ingest_path(batch: str, variant: str) -> Path:
    normalized_batch, normalized_variant = resolve_simulation_partition(batch, variant, require_variant=True)
    return LAB_INGESTIONS_DIR / normalized_batch / f"{normalized_variant}_updated_candidate.json"
