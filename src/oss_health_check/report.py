from __future__ import annotations

import json
from dataclasses import asdict

from .model import Report, Severity


def as_json(report: Report) -> str:
    payload = {
        "path": str(report.root),
        "status": report.status,
        "score": report.score,
        "branch": report.branch,
        "dirty": report.dirty,
        "files_scanned": report.files_scanned,
        "tracked_files": report.tracked_files,
        "large_files": list(report.large_files),
        "secrets": list(report.secrets),
        "checks": [asdict(check) | {"severity": check.severity.value} for check in report.checks],
    }
    return json.dumps(payload, indent=2, sort_keys=False)


def as_markdown(report: Report) -> str:
    lines = [
        f"# Repository health: `{report.root.name}`",
        "",
        f"**Status:** `{report.status}`  ",
        f"**Score:** `{report.score}/100`  ",
        f"**Branch:** `{report.branch or 'not a Git worktree'}`  ",
        f"**Working tree:** `{'dirty' if report.dirty else 'clean'}`",
        "",
        "## Checks",
        "",
        "| Result | Check | Details |",
        "| --- | --- | --- |",
    ]
    icons = {Severity.PASS: "PASS", Severity.INFO: "INFO", Severity.WARN: "WARN", Severity.FAIL: "FAIL"}
    for check in report.checks:
        detail = check.message.replace("|", "\\|")
        lines.append(f"| `{icons[check.severity]}` | {check.title} | {detail} |")
        if check.suggestion and check.severity in (Severity.WARN, Severity.FAIL):
            lines.append(f"|  |  | _Next: {check.suggestion}_ |")
    lines.extend(["", "## Inventory", "", f"- Files scanned: `{report.files_scanned}`", f"- Tracked files: `{report.tracked_files}`"])
    if report.large_files:
        lines.append("- Large files: " + ", ".join(f"`{path}`" for path in report.large_files))
    if report.secrets:
        lines.append("- Possible secrets: " + ", ".join(f"`{path}`" for path in report.secrets))
    return "\n".join(lines) + "\n"


def as_sarif(report: Report) -> str:
    results = []
    for check in report.checks:
        if check.severity not in (Severity.WARN, Severity.FAIL):
            continue
        results.append({
            "ruleId": check.key,
            "level": "error" if check.severity == Severity.FAIL else "warning",
            "message": {"text": check.message},
        })
    return json.dumps({
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "oss-health-check", "informationUri": "https://github.com/HP-network/oss-health-check"}},
            "results": results,
        }],
    }, indent=2)
