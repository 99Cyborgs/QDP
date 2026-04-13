from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .artifacts import dump_json
from .serialization import write_text


def derived_status_for(module_id: str, closure_by_module: Mapping[str, Mapping[str, Any]]) -> str:
    return str(closure_by_module.get(module_id, {}).get("derived_status", "BLOCKED"))


def closure_limitations_for(module_id: str, closure_by_module: Mapping[str, Mapping[str, Any]]) -> list[str]:
    limitations = closure_by_module.get(module_id, {}).get("closure_limitations", [])
    if not isinstance(limitations, list):
        return []
    return [str(item) for item in limitations if str(item).strip()]


def build_module_registry_json(
    blueprints: Mapping[str, Mapping[str, Any]],
    *,
    resume_policy: Mapping[str, Any],
    closure_by_module: Mapping[str, Mapping[str, Any]],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    modules = []
    for module_id, spec in blueprints.items():
        modules.append(
            {
                "module_id": module_id,
                "name": spec["name"],
                "blocker_class": spec["blocker_class"],
                "owner_artifacts": spec["owner_artifacts"],
                "required_outputs": spec["required_outputs"],
                "status": derived_status_for(module_id, closure_by_module),
                "derived_closure_status": derived_status_for(module_id, closure_by_module),
                "closure_limitations": closure_limitations_for(module_id, closure_by_module),
            }
        )

    return {
        "artifact_id": "QDP_V10_6_MODULE_REGISTRY_V2",
        "version": "2.0",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "resume_policy": dict(resume_policy),
        "readiness": dict(readiness),
        "modules": modules,
        "next_phase": {
            "subsystem_modules_in_scope": ["S16", "S17", "S18", "S19"],
            "note": "Subsystem modules are scaffolded in the current repo; authoritative status is governed by the live readiness predicates and explicit authoritative bindings recorded in this registry.",
        },
    }


def build_module_registry_md(
    blueprints: Mapping[str, Mapping[str, Any]],
    *,
    closure_by_module: Mapping[str, Mapping[str, Any]],
    readiness: Mapping[str, Any],
) -> str:
    lines = [
        "# QDP v10.6 Module Registry",
        "Version 2.0",
        f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        "## Purpose",
        "",
        "Generated core-module registry for M01-M15 from canonical repo metadata and live closure evaluation.",
        "Verification evidence is module-specific: selftest-backed modules publish selftest reports, M01 publishes assembly plus closure reports, M03 publishes strict reference-resolution reports, and M06 publishes bootstrap-harness evidence.",
        "",
        "## Readiness",
        "",
        f"- ordinary_recovery_ready: {str(bool(readiness.get('ordinary_recovery_ready', False))).lower()}",
        f"- ordinary_authoritative_ready: {str(bool(readiness.get('ordinary_authoritative_ready', False))).lower()}",
        f"- ordinary_testing_ready: {str(bool(readiness.get('ordinary_testing_ready', False))).lower()}",
        f"- subsystem_recovery_ready: {str(bool(readiness.get('subsystem_recovery_ready', False))).lower()}",
        f"- subsystem_authoritative_ready: {str(bool(readiness.get('subsystem_authoritative_ready', False))).lower()}",
        f"- subsystem_testing_ready: {str(bool(readiness.get('subsystem_testing_ready', False))).lower()}",
        "",
        "## Resume-testing policy",
        "",
        "### Ordinary candidate testing",
        "Do not resume ordinary candidate testing until the required core modules are closure-complete under the active policy.",
        "",
        "### Authoritative lane",
        "Do not claim authoritative readiness until retained-source-dependent modules clear without unresolved surrogate provenance and visible-source modules have explicit authoritative bindings.",
        "",
        "### Subsystem lane",
        "Subsystem readiness is reported independently from the ordinary lane and only aliases subsystem_testing_ready when authoritative requirements are met.",
        "",
        "## Modules",
        "",
        "| ID | Module | Purpose | Required outputs | Current derived status |",
        "|---|---|---|---|---|",
    ]
    for module_id, spec in blueprints.items():
        lines.append(
            f"| {module_id} | {spec['name']} | {spec['purpose']} | "
            f"{'; '.join(spec['required_outputs'])} | {derived_status_for(module_id, closure_by_module)} |"
        )
    limited_modules = [module_id for module_id in blueprints if closure_limitations_for(module_id, closure_by_module)]
    if limited_modules:
        lines.extend(
            [
                "",
                "## Closure limitations",
                "",
            ]
        )
        for module_id in limited_modules:
            limitations = "; ".join(closure_limitations_for(module_id, closure_by_module))
            lines.append(f"- {module_id}: {limitations}")
    lines.extend(
        [
            "",
            "## Next phase",
            "",
            "Subsystem modules S16-S19 remain governed by the live readiness predicates in this registry; surfaced-source origin alone does not decide authoritative status once explicit bindings are recorded.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_module_registry(
    registry_json_path: Path,
    registry_md_path: Path,
    blueprints: Mapping[str, Mapping[str, Any]],
    *,
    resume_policy: Mapping[str, Any],
    closure_by_module: Mapping[str, Mapping[str, Any]],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    payload = build_module_registry_json(
        blueprints,
        resume_policy=resume_policy,
        closure_by_module=closure_by_module,
        readiness=readiness,
    )
    dump_json(registry_json_path, payload)
    write_text(
        registry_md_path,
        build_module_registry_md(
            blueprints,
            closure_by_module=closure_by_module,
            readiness=readiness,
        ),
    )
    return payload
