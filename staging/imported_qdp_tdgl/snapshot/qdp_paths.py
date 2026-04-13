from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parent

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

BASE_TEMPLATE = SCHEMA_DIR / "candidate_template.json"
SCHEMA = SCHEMA_DIR / "candidate_schema.json"
FORK_INTAKE_TEMPLATE = SCHEMA_DIR / "fork_intake_template.json"
FORK_INTAKE_SCHEMA = SCHEMA_DIR / "fork_intake_schema.json"

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
GKSL_SUBSYSTEM_CASE_MATRIX = SPECS_DIR / "subsystem" / "specs/subsystem/gksl_subsystem_case_matrix.json"

RUNTIME_PROMPT = RUNTIME_DIR / "current" / "runtime_prompt.md"
RETAINED_OPERATIVE_BODY = RUNTIME_DIR / "retained" / "operative_body_v10_1.md"
SURROGATE_OPERATIVE_BODY = RUNTIME_DIR / "missing" / "operative_body_v10_1.md"
SURROGATE_FEDERATED_REGISTRY_OBJECT = RUNTIME_DIR / "missing" / "federated_governance_registry_object.json"

M01_CLOSURE_REPORT = REPORTS_DIR / "m01" / "closure_report.json"
M03_ORDINARY_REPORT = REPORTS_DIR / "m03" / "reference_resolution_ordinary.json"
M03_SUBSYSTEM_REPORT = REPORTS_DIR / "m03" / "reference_resolution_subsystem.json"
MODE_DIVERGENCE_REPORT = REPORTS_DIR / "system" / "mode_divergence_report.json"
MODULE_CLOSURE_EVALUATION_REPORT = REPORTS_DIR / "system" / "module_closure_evaluation.json"


MODULES: Dict[str, Dict[str, Any]] = {
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
        "supports_selftest": False,
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
}


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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
