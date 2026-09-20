from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .report import as_json, as_markdown, as_sarif
from .scanner import scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oss-health-check",
        description="Check whether a local repository is ready to share and maintain.",
    )
    parser.add_argument("path", nargs="?", default=".", help="repository directory (default: current directory)")
    parser.add_argument("--format", choices=("text", "json", "markdown", "sarif"), default="text")
    parser.add_argument("--strict", action="store_true", help="exit 1 when a check fails")
    parser.add_argument(
        "--min-score",
        type=_score,
        metavar="0-100",
        help="exit 1 when the repository score is below this threshold",
    )
    parser.add_argument(
        "--strict-workflow-pins",
        action="store_true",
        help="fail when a third-party GitHub Action is not pinned to a commit SHA",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = scan(Path(args.path), strict_workflow_pins=args.strict_workflow_pins)
    except ValueError as error:
        print(f"oss-health-check: {error}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(as_json(report))
    elif args.format == "markdown":
        print(as_markdown(report), end="")
    elif args.format == "sarif":
        print(as_sarif(report))
    else:
        _print_text(report)
    failed_checks = args.strict and bool(report.failures)
    below_threshold = args.min_score is not None and report.score < args.min_score
    return 1 if failed_checks or below_threshold else 0


def _score(value: str) -> int:
    score = int(value)
    if not 0 <= score <= 100:
        raise argparse.ArgumentTypeError("score must be between 0 and 100")
    return score


def _print_text(report) -> None:
    print(f"{report.root.name}: {report.score}/100 ({report.status})")
    print(f"branch={report.branch or '-'} working_tree={'dirty' if report.dirty else 'clean'}")
    for check in report.checks:
        print(f"[{check.severity.value.upper():4}] {check.title}: {check.message}")
        if check.suggestion and check.severity.value in ("warn", "fail"):
            print(f"       -> {check.suggestion}")
    print(f"Scanned {report.files_scanned} files; {report.tracked_files} tracked files.")
