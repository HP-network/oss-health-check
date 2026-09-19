from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(str, Enum):
    PASS = "pass"
    INFO = "info"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True)
class Check:
    key: str
    title: str
    severity: Severity
    score: int
    message: str
    suggestion: str = ""


@dataclass(frozen=True)
class Report:
    root: Path
    checks: tuple[Check, ...]
    files_scanned: int
    tracked_files: int
    large_files: tuple[str, ...]
    secrets: tuple[str, ...]
    dirty: bool
    branch: str | None

    @property
    def score(self) -> int:
        if not self.checks:
            return 0
        earned = sum(check.score for check in self.checks)
        possible = sum(2 for check in self.checks if check.severity != Severity.INFO)
        return round(100 * earned / possible) if possible else 100

    @property
    def failures(self) -> tuple[Check, ...]:
        return tuple(check for check in self.checks if check.severity == Severity.FAIL)

    @property
    def warnings(self) -> tuple[Check, ...]:
        return tuple(check for check in self.checks if check.severity == Severity.WARN)

    @property
    def status(self) -> str:
        if self.failures:
            return "needs-work"
        if self.warnings:
            return "good-with-notes"
        return "ready"
