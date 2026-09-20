"""Repository readiness checks for local projects."""

__version__ = "0.3.0"

from .model import Check, Report, Severity
from .scanner import scan

__all__ = ["Check", "Report", "Severity", "scan"]
