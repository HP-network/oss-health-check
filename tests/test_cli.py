import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from oss_health_check.cli import main


class CliTest(unittest.TestCase):
    def test_min_score_controls_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", ".gitignore", "pyproject.toml"):
                (root / name).write_text("x", encoding="utf-8")
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "ci.yml").write_text("name: CI", encoding="utf-8")
            (root / "tests").mkdir()

            with redirect_stdout(StringIO()):
                self.assertEqual(main([str(root), "--min-score", "100"]), 0)
            (root / "LICENSE").unlink()
            with redirect_stdout(StringIO()):
                self.assertEqual(main([str(root), "--min-score", "100"]), 1)

            with self.assertRaises(SystemExit) as error:
                main([str(root), "--min-score", "101"])
            self.assertEqual(error.exception.code, 2)
