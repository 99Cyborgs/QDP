from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[3]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"

path_str = str(QDP_IO_SRC)
if path_str not in sys.path:
    sys.path.insert(0, path_str)

from qdp_io.artifacts import dump_json
from qdp_io.serialization import load_json_object
from tools.workflow.qdp_runtime.qdp_paths import (
    BASE_TEMPLATE,
    CANDIDATE_VALIDATOR,
    FORK_INTAKE_SCHEMA,
    GOVERNANCE_REGISTRY,
    GKSL_SUBSYSTEM_CASE_MATRIX,
    M01_CLOSURE_REPORT,
    MODULES,
    REFERENCE_MANIFEST,
    RETAINED_OPERATIVE_BODY,
    RUNTIME_PROMPT,
    SCHEMA,
    SUBSYSTEM_VERDICT_SCHEMA,
    SURROGATE_OPERATIVE_BODY,
    resolve_module,
)


def load_json(path: Path) -> Dict[str, Any]:
    return load_json_object(path)


@lru_cache(maxsize=None)
def load_runner(module_key: str):
    module = resolve_module(module_key)
    runner_path = Path(module["runner"])
    spec = importlib.util.spec_from_file_location(f"qdp_runner_{module_key}", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import runner: {runner_path}")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def describe_module(module_key: str) -> Dict[str, Any]:
    module = resolve_module(module_key)
    return {
        "module_key": module_key.lower(),
        "module_id": module["module_id"],
        "name": module["name"],
        "supports_selftest": bool(module.get("supports_selftest", False)),
        "runner": str(module["runner"]),
    }


def module_keys_with_selftests() -> List[str]:
    return [key for key, meta in MODULES.items() if meta.get("supports_selftest", False)]


def _generic_selftest_call(module_key: str) -> Dict[str, Any]:
    meta = resolve_module(module_key)
    runner = load_runner(module_key)
    if meta["module_id"] in {"M07", "M08", "M09", "M10"}:
        base_template = load_json(BASE_TEMPLATE)
        report = runner.run_selftests(
            base_template,
            Path(meta["selftest_cases"]),
            CANDIDATE_VALIDATOR,
            SCHEMA,
            Path(meta["selftest_output_dir"]),
        )
        dump_json(Path(meta["selftest_report"]), report)
        return report
    report = runner.run_selftests(
        Path(meta["selftest_cases"]),
        BASE_TEMPLATE,
        CANDIDATE_VALIDATOR,
        SCHEMA,
        Path(meta["selftest_output_dir"]),
        Path(meta["selftest_report"]),
    )
    return report


def selftest_module(module_key: str) -> Dict[str, Any]:
    meta = resolve_module(module_key)
    if not meta.get("supports_selftest", False):
        raise KeyError(f"{meta['module_id']} does not support selftests.")
    runner = load_runner(module_key)
    style = meta.get("selftest_style", "generic")
    if style == "m01":
        report = runner.run_selftests(
            Path(meta["selftest_cases"]),
            REFERENCE_MANIFEST,
            RUNTIME_PROMPT,
            RETAINED_OPERATIVE_BODY,
            SURROGATE_OPERATIVE_BODY,
            Path(meta["selftest_output_dir"]),
            Path(meta["selftest_report"]),
        )
    elif style == "m02":
        report = runner.run_selftests(
            Path(meta["selftest_cases"]),
            BASE_TEMPLATE,
            CANDIDATE_VALIDATOR,
            SCHEMA,
            Path(meta["selftest_output_dir"]),
            Path(meta["selftest_report"]),
        )
    elif style == "m04":
        report = runner.run_selftests(
            Path(meta["selftest_cases"]),
            BASE_TEMPLATE,
            GOVERNANCE_REGISTRY,
            FORK_INTAKE_SCHEMA,
            CANDIDATE_VALIDATOR,
            SCHEMA,
            Path(meta["selftest_output_dir"]),
            Path(meta["selftest_report"]),
        )
    elif style == "m05":
        report = runner.run_selftests(
            Path(meta["selftest_cases"]),
            BASE_TEMPLATE,
            CANDIDATE_VALIDATOR,
            SCHEMA,
            Path(meta["selftest_output_dir"]),
            Path(meta["selftest_report"]),
        )
    elif style == "subsystem":
        report = runner.run_selftests(
            Path(meta["selftest_cases"]),
            GKSL_SUBSYSTEM_CASE_MATRIX,
            SUBSYSTEM_VERDICT_SCHEMA,
            Path(meta["selftest_output_dir"]),
            Path(meta["selftest_report"]),
        )
    else:
        report = _generic_selftest_call(module_key)
    return {
        "module_key": module_key.lower(),
        "module_id": meta["module_id"],
        "execution": {"ok": True, "mode": "in_process"},
        "report_path": str(meta["selftest_report"]),
        "report": report,
    }


def run_selftests(module_keys: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    return {key: selftest_module(key) for key in module_keys}


def run_module(module_key: str, **kwargs: Any) -> Dict[str, Any]:
    meta = resolve_module(module_key)
    runner = load_runner(module_key)
    module_id = meta["module_id"]

    if module_id == "M01":
        manifest = load_json(Path(kwargs.get("manifest", REFERENCE_MANIFEST)))
        assembly_report, closure_report = runner.build_reports(
            manifest,
            Path(kwargs.get("runtime_prompt", RUNTIME_PROMPT)),
            Path(kwargs.get("retained_runtime_source", RETAINED_OPERATIVE_BODY)),
            Path(kwargs.get("surrogate_runtime_source", SURROGATE_OPERATIVE_BODY)),
        )
        report_path = Path(kwargs.get("report", meta["selftest_report"]))
        closure_path = Path(kwargs.get("output", M01_CLOSURE_REPORT))
        dump_json(report_path, assembly_report)
        dump_json(closure_path, closure_report)
        return {"report": assembly_report, "closure_report": closure_report, "report_path": str(report_path), "output_path": str(closure_path)}

    if module_id == "M02":
        report = {
            "artifact_id": "QDP_V10_6_M02_REPORT",
            "module_id": "M02",
            "contract_checks": runner.contract_checks(BASE_TEMPLATE, CANDIDATE_VALIDATOR, SCHEMA),
        }
        candidate_path = kwargs.get("candidate")
        if candidate_path:
            from tools.workflow.qdp_runtime.qdp_validation import validate_candidate_file

            report["candidate_validation"] = validate_candidate_file(Path(candidate_path), CANDIDATE_VALIDATOR, SCHEMA, mode="final")
        report_path = Path(kwargs.get("report", meta["selftest_report"]))
        dump_json(report_path, report)
        return {"report": report, "report_path": str(report_path)}

    if module_id == "M03":
        manifest_path = Path(kwargs.get("manifest", meta["run_defaults"]["--manifest"]))
        registry_path = Path(kwargs.get("registry", meta["run_defaults"]["--registry"]))
        root = Path(kwargs.get("root", meta["run_defaults"]["--root"]))
        mode = str(kwargs.get("mode", meta["run_defaults"]["--mode"]))
        manifest = load_json(manifest_path)
        registry = load_json(registry_path)
        resolved, unresolved = runner.resolve_manifest(manifest, root, mode)
        critical_unresolved = [u for u in unresolved if u.get("required") and str(u.get("criticality", "")).startswith("CRITICAL")]
        report = {
            "artifact_id": "QDP_V10_6_REFERENCE_RESOLUTION_REPORT_M03",
            "module_id": "M03",
            "mode": mode,
            "resolved_count": len(resolved),
            "unresolved_count": len(unresolved),
            "critical_unresolved_count": len(critical_unresolved),
            "reference_resolution_status": "FAILED" if critical_unresolved else "PASSED",
            "system_status": "REFERENCE_RESOLUTION_FAILURE" if critical_unresolved else "HARNESS_REQUIRED",
            "promotion_cap_governance": "SANDBOX_ONLY" if critical_unresolved else "",
            "resolved_references": [
                {
                    "ref_id": r["ref_id"],
                    "relative_path": r["relative_path"],
                    "sha256": r["sha256"],
                    "bytes": r["bytes"],
                }
                for r in resolved
            ],
            "unresolved_references": [
                {
                    "ref_id": u["ref_id"],
                    "relative_path": u["relative_path"],
                    "criticality": u["criticality"],
                    "required": u["required"],
                    "missing_reason": u["missing_reason"],
                }
                for u in unresolved
            ],
        }
        report_path = Path(kwargs.get("report", meta["run_defaults"]["--write-report"]))
        dump_json(report_path, report)
        candidate_path = kwargs.get("candidate")
        output_path = kwargs.get("output")
        patched_candidate = None
        if candidate_path and output_path:
            candidate = load_json(Path(candidate_path))
            patched_candidate = runner.update_candidate(candidate, registry, critical_unresolved, report.get("report_id", ""), [str(manifest_path), str(registry_path), str(report_path)])
            dump_json(Path(output_path), patched_candidate)
        return {"report": report, "report_path": str(report_path), "candidate": patched_candidate, "output_path": str(output_path or "")}

    if module_id == "M04":
        intake_path = Path(kwargs["intake"])
        intake = load_json(intake_path)
        candidate_template = load_json(Path(kwargs.get("candidate_template", BASE_TEMPLATE)))
        registry = load_json(Path(kwargs.get("registry", GOVERNANCE_REGISTRY)))
        if kwargs.get("intake_schema", FORK_INTAKE_SCHEMA):
            runner.validate_against_schema(intake, Path(kwargs.get("intake_schema", FORK_INTAKE_SCHEMA)))
        candidate, registration = runner.build_registration(intake, registry, candidate_template, intake_path)
        if kwargs.get("output"):
            dump_json(Path(kwargs["output"]), candidate)
        if kwargs.get("report"):
            dump_json(Path(kwargs["report"]), registration)
        return {"candidate": candidate, "registration": registration}

    if module_id == "M05":
        candidate = load_json(Path(kwargs["candidate"]))
        base = runner.load_json(BASE_TEMPLATE)
        merged = runner.deep_merge(runner.make_minimal_final_candidate(base), candidate)
        stage_inputs = load_json(Path(kwargs["stage_inputs"])) if kwargs.get("stage_inputs") else {}
        out_candidate, report = runner.run_state_machine(merged, stage_inputs, schema_path=SCHEMA, validator_path=CANDIDATE_VALIDATOR)
        if kwargs.get("output"):
            dump_json(Path(kwargs["output"]), out_candidate)
        if kwargs.get("report"):
            dump_json(Path(kwargs["report"]), report)
        return {"candidate": out_candidate, "report": report}

    if module_id in {"M07", "M08", "M09", "M10", "M11", "M12", "M13", "M14", "M15"}:
        function_name = {
            "M07": "run_family_triage",
            "M08": "run_baseline_fit",
            "M09": "run_mechanism_competition",
            "M10": "run_artifact_audit",
            "M11": "run_lindblad_equivalence",
            "M12": "run_experiment_design",
            "M13": "run_cross_device_gate",
            "M14": "run_promotion_caps",
            "M15": "run_governance_guardrails",
        }[module_id]
        candidate = load_json(Path(kwargs["candidate"]))
        result_candidate, report = getattr(runner, function_name)(candidate)
        if kwargs.get("output"):
            dump_json(Path(kwargs["output"]), result_candidate)
        if kwargs.get("report"):
            dump_json(Path(kwargs["report"]), report)
        return {"candidate": result_candidate, "report": report}

    if module_id in {"S16", "S17", "S18", "S19"}:
        case_id = str(kwargs["case_id"])
        matrix_path = Path(kwargs.get("matrix", GKSL_SUBSYSTEM_CASE_MATRIX))
        result_payload, report = runner.run_subsystem_module(case_id, matrix_path)
        if kwargs.get("output"):
            dump_json(Path(kwargs["output"]), result_payload)
        if kwargs.get("report"):
            dump_json(Path(kwargs["report"]), report)
        return {"candidate": result_payload, "report": report}

    raise KeyError(f"Unsupported module run path for {module_id}")

