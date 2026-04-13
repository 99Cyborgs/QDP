from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QDP_IO_SRC = ROOT / "packages" / "qdp_io" / "src"
QDP_VALIDATION_SRC = ROOT / "packages" / "qdp_validation" / "src"

for path in (QDP_IO_SRC, QDP_VALIDATION_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qdp_validation import emit_artifact_validation_result, validate_all_mind_interface_file

INTERFACE_PATH = ROOT / "artifacts" / "reports" / "system" / "all_mind_interface.json"
REPORT_PATH = ROOT / "artifacts" / "reports" / "system" / "repo_validation_report.json"


def run_command(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def cleanup_validation_bytecode() -> None:
    pycache_dir = ROOT / "__pycache__"
    if pycache_dir.exists():
        for child in pycache_dir.rglob("*"):
            if child.is_file():
                child.unlink()
        for child in sorted(pycache_dir.rglob("*"), reverse=True):
            if child.is_dir():
                child.rmdir()
        pycache_dir.rmdir()


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(f"missing expected validation artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_interface_artifact_or_exit(path: Path = INTERFACE_PATH) -> dict[str, object]:
    result = validate_all_mind_interface_file(path)
    if not result.get("valid", False):
        emit_artifact_validation_result(result)
        raise SystemExit(1)
    return load_json(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the canonical QDP validation flow and summarize the frozen ALL-MIND interface.",
    )
    parser.add_argument(
        "--require-authoritative-ready",
        action="store_true",
        help="Fail unless both authoritative readiness flags are true.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    run_command([sys.executable, "-m", "pytest", "-q", "tests/test_authoritative_readiness.py"])
    cleanup_validation_bytecode()
    run_command([sys.executable, str(ROOT / "qdp_validation.py")])

    report = load_json(REPORT_PATH)
    interface = validate_interface_artifact_or_exit(INTERFACE_PATH)
    readiness = interface["readiness"]

    summary = {
        "structural_consistency_passed": report["structural_consistency_passed"],
        "all_mind_interface_valid": True,
        "ordinary_recovery_ready": readiness["ordinary_recovery_ready"],
        "ordinary_authoritative_ready": readiness["ordinary_authoritative_ready"],
        "subsystem_recovery_ready": readiness["subsystem_recovery_ready"],
        "subsystem_authoritative_ready": readiness["subsystem_authoritative_ready"],
        "interface_path": str(INTERFACE_PATH),
    }
    print(json.dumps(summary, indent=2))

    if args.require_authoritative_ready and not (
        readiness["ordinary_authoritative_ready"]
        and readiness["subsystem_authoritative_ready"]
    ):
        print("authoritative readiness is still false", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
