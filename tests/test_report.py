import tempfile
import unittest
from pathlib import Path

from oss_health_check.report import as_json, as_markdown
from oss_health_check.scanner import scan


class ReportTest(unittest.TestCase):
    def test_json_and_markdown_are_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Example", encoding="utf-8")
            report = scan(root)

            payload = as_json(report)
            markdown = as_markdown(report)

            self.assertIn('"score"', payload)
            self.assertIn("## Checks", markdown)
            self.assertIn("README", markdown)
