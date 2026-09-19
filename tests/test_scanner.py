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
