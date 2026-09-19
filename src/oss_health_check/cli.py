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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = scan(Path(args.path))
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
    return 1 if args.strict and report.failures else 0


def _print_text(report) -> None:
    print(f"{report.root.name}: {report.score}/100 ({report.status})")
    print(f"branch={report.branch or '-'} working_tree={'dirty' if report.dirty else 'clean'}")
    for check in report.checks:
        print(f"[{check.severity.value.upper():4}] {check.title}: {check.message}")
        if check.suggestion and check.severity.value in ("warn", "fail"):
            print(f"       -> {check.suggestion}")
    print(f"Scanned {report.files_scanned} files; {report.tracked_files} tracked files.")
