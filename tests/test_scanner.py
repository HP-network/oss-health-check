import subprocess
import tempfile
import unittest
from pathlib import Path

from oss_health_check.scanner import scan


def write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ScannerTest(unittest.TestCase):
    def test_scans_documentation_ci_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", ".gitignore", "pyproject.toml"):
                write(root / name)
            write(root / ".github" / "workflows" / "ci.yml")
            write(root / "tests" / "test_demo.py")

            report = scan(root)

            self.assertEqual(report.score, 100)
            self.assertEqual(report.failures, ())
            self.assertEqual(report.status, "ready")

    def test_reports_tracked_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / "README.md")
            write(root / "config.env", "AWS_" + "SECRET_ACCESS_KEY=" + "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "README.md", "config.env"], cwd=root, check=True)

            report = scan(root)

            self.assertEqual(report.secrets, ("config.env",))
            self.assertTrue(any(check.key == "secrets" and check.severity.value == "fail" for check in report.checks))

    def test_reports_ai_provider_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / "README.md")
            write(root / "settings.env", "OPENAI_" + "API_KEY=sk-" + "a" * 32)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "README.md", "settings.env"], cwd=root, check=True)

            report = scan(root)

            self.assertEqual(report.secrets, ("settings.env",))

    def test_workflow_action_pins_are_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / "README.md")
            write(root / ".github" / "workflows" / "ci.yml", "steps:\n  - uses: actions/checkout@v4\n")

            report = scan(root)
            self.assertFalse(report.failures)
            self.assertEqual(report.checks[6].key, "workflow-pins")
            self.assertEqual(report.checks[6].severity.value, "info")

            strict_report = scan(root, strict_workflow_pins=True)
            self.assertEqual([check.key for check in strict_report.failures], ["workflow-pins"])

            write(root / ".github" / "workflows" / "ci.yml", "steps:\n  - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n")
            pinned_report = scan(root, strict_workflow_pins=True)
            self.assertFalse(pinned_report.failures)
