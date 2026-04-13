from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


INTERFACE_PATHS = {
    "INTEGRATION_PLAN.md",
    "VALIDATION.md",
    "qdp_validation.py",
    "run_repo_validation.py",
    "all_mind_interface_schema.json",
    "test_all_mind_interface_validation.py",
}

READINESS_PATHS = {
    "test_authoritative_readiness.py",
    "VALIDATION.md",
    "README.md",
    "STATUS.md",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=os.getcwd())
    parser.add_argument("--changed", nargs="*", default=[])
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    changed = [Path(path) for path in args.changed]

    required_files = [
        "README.md",
        "REPO_MAP.md",
        "VALIDATION.md",
        "INTEGRATION_PLAN.md",
        "config/schema/all_mind_interface_schema.json",
        "artifacts/reports/system/all_mind_interface.json",
        "artifacts/reports/system/repo_validation_report.json",
    ]

    required_status = [
        {"path": str(repo_root / path), "exists": (repo_root / path).exists()}
        for path in required_files
    ]

    interface_surface = [str(path) for path in changed if path.name in INTERFACE_PATHS]
    readiness_surface = [str(path) for path in changed if path.name in READINESS_PATHS]
    queue_surface = [str(path) for path in changed if "queue" in path.as_posix().lower()]
    campaign_surface = [str(path) for path in changed if "campaign" in path.as_posix().lower()]
    generated_artifact_edits = [
        str(path)
        for path in changed
        if any(part.lower() == "artifacts" for part in path.parts)
    ]

    recommended_commands = ["python scripts/run_repo_validation.py"]
    if interface_surface:
        recommended_commands.append(
            "python qdp.py validate artifacts/reports/system/all_mind_interface.json --kind all-mind-interface"
        )
    if readiness_surface:
        recommended_commands.append("python scripts/run_repo_validation.py --require-authoritative-ready")

    operator_followups = []
    if queue_surface:
        operator_followups.extend(
            [
                "python qdp.py queue list",
                "python qdp.py queue show <queue_id>",
                "python qdp.py queue log <queue_id>",
            ]
        )
    if campaign_surface:
        operator_followups.extend(
            [
                "python qdp.py campaign prepare --batch <batch>",
                "python qdp.py campaign plan --batch <batch>",
            ]
        )

    payload = {
        "repo_root": str(repo_root),
        "required_files": required_status,
        "interface_surface": interface_surface,
        "readiness_surface": readiness_surface,
        "queue_surface": queue_surface,
        "campaign_surface": campaign_surface,
        "generated_artifact_edits": generated_artifact_edits,
        "recommended_commands": recommended_commands,
        "operator_followups": operator_followups,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
