from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
PRIMARY_BUCKETS = ("active_runtime", "staged_donor", "generated_artifacts")
BUCKET_ORDER = PRIMARY_BUCKETS + ("docs_metadata",)

ACTIVE_RUNTIME_ROOT_FILES = {
    "qdp.py",
    "qdp_validation.py",
}
ACTIVE_RUNTIME_PREFIXES = (
    "modules/",
    "packages/",
    "apps/",
    "tools/workflow/qdp_runtime/",
    "tools/validators/",
    "config/",
    "configs/",
    "scripts/",
    "tests/",
)
STAGED_DONOR_PREFIXES = ("legacy/imported_artifacts/",)
GENERATED_ARTIFACT_PREFIXES = (
    "artifacts/outputs/",
    "artifacts/reports/",
    "artifacts/lab/",
    "runs/",
)
DOCS_METADATA_PREFIXES = ("docs/",)
TEST_PREFIX = "tests/"


def normalize_repo_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def is_root_markdown(path: str) -> bool:
    return "/" not in path and path.endswith(".md")


def classify_path(path: str) -> str | None:
    normalized = normalize_repo_path(path)
    if not normalized:
        return None
    if normalized in ACTIVE_RUNTIME_ROOT_FILES:
        return "active_runtime"
    if normalized.startswith(ACTIVE_RUNTIME_PREFIXES):
        return "active_runtime"
    if normalized.startswith(STAGED_DONOR_PREFIXES):
        return "staged_donor"
    if normalized.startswith("staging/imported_"):
        return "staged_donor"
    if normalized.startswith(GENERATED_ARTIFACT_PREFIXES):
        return "generated_artifacts"
    if normalized.startswith(DOCS_METADATA_PREFIXES) or is_root_markdown(normalized):
        return "docs_metadata"
    return None


def classify_paths(paths: Sequence[str]) -> dict[str, list[str]]:
    bucket_files = {bucket: [] for bucket in BUCKET_ORDER}
    bucket_files["unclassified"] = []
    normalized_paths = {normalize_repo_path(path) for path in paths}
    for path in sorted(path for path in normalized_paths if path):
        bucket = classify_path(path)
        bucket_files[bucket if bucket is not None else "unclassified"].append(path)
    return bucket_files


def mixed_scope_pairs(primary_buckets: Sequence[str]) -> list[str]:
    pairs: list[str] = []
    for index, left in enumerate(primary_buckets):
        for right in primary_buckets[index + 1 :]:
            pairs.append(f"{left}+{right}")
    return pairs


def summarize_scope(paths: Sequence[str], allow_mixed_scope: bool = False) -> dict[str, Any]:
    bucket_files = classify_paths(paths)
    present_primary_buckets = [bucket for bucket in PRIMARY_BUCKETS if bucket_files[bucket]]
    runtime_test_files = [path for path in bucket_files["active_runtime"] if path.startswith(TEST_PREFIX)]
    runtime_source_files = [
        path for path in bucket_files["active_runtime"] if not path.startswith(TEST_PREFIX)
    ]

    mixed_violations = mixed_scope_pairs(present_primary_buckets) if len(present_primary_buckets) > 1 else []
    policy_violations: list[str] = []
    if bucket_files["unclassified"]:
        policy_violations.append("unclassified_paths_present")
    if runtime_test_files and not runtime_source_files:
        policy_violations.append("tests_without_runtime_source")

    accepted_mixed_scope = mixed_violations if allow_mixed_scope else []
    blocking_mixed_violations = [] if allow_mixed_scope else mixed_violations

    if not any(bucket_files[bucket] for bucket in bucket_files):
        status = "no_changes"
    elif policy_violations or blocking_mixed_violations:
        status = "scope_violation"
    elif accepted_mixed_scope:
        status = "allowed_mixed_scope"
    else:
        status = "ok"

    if len(present_primary_buckets) == 1:
        primary_bucket: str | None = present_primary_buckets[0]
    elif not present_primary_buckets and bucket_files["docs_metadata"]:
        primary_bucket = "docs_metadata"
    else:
        primary_bucket = None

    return {
        "status": status,
        "primary_bucket": primary_bucket,
        "present_primary_buckets": present_primary_buckets,
        "mixed_scope_violations": blocking_mixed_violations,
        "accepted_mixed_scope": accepted_mixed_scope,
        "policy_violations": policy_violations,
        "bucket_files": {bucket: bucket_files[bucket] for bucket in BUCKET_ORDER},
        "unclassified_files": bucket_files["unclassified"],
        "runtime_source_files": runtime_source_files,
        "runtime_test_files": runtime_test_files,
        "all_files": [path for bucket in BUCKET_ORDER for path in bucket_files[bucket]] + bucket_files["unclassified"],
    }


def git_diff_name_only(*, staged: bool, refspec: str | None) -> list[str]:
    command = ["git", "diff", "--name-only"]
    if staged:
        command.append("--cached")
    if refspec:
        command.append(refspec)

    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git diff --name-only failed")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify changed paths into commit-scope buckets.",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--staged",
        action="store_true",
        help="Classify the staged git diff (`git diff --cached --name-only`).",
    )
    source_group.add_argument(
        "--ref",
        metavar="BASE..HEAD",
        help="Classify a git ref diff (`git diff --name-only BASE..HEAD`).",
    )
    parser.add_argument(
        "--allow-mixed-scope",
        action="store_true",
        help="Allow mixed primary buckets and report which ones were explicitly accepted.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        paths = git_diff_name_only(staged=args.staged, refspec=args.ref)
    except RuntimeError as exc:
        print(json.dumps({"status": "git_error", "error": str(exc)}, indent=2))
        return 2

    summary = summarize_scope(paths, allow_mixed_scope=args.allow_mixed_scope)
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] in {"ok", "no_changes", "allowed_mixed_scope"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
