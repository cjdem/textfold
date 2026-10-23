"""The tag build publishes the notes a release carries and runs the Python suite before it builds the app: a release
body is not a placeholder, and a release is not shipped without the tests the change workflow runs locally.

Run from the repo root:
    python -m unittest discover tests
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = ROOT / ".github" / "workflows" / "desktop.yml"


class Release(unittest.TestCase):
    def test_the_tag_build_publishes_notes_and_runs_the_python_suite(self):
        yml = DESKTOP.read_text(encoding="utf-8")
        self.assertIn("--notes-file", yml)
        self.assertIn("docs/releases/$TAG.md", yml)
        self.assertIn('test -s "docs/releases/${GITHUB_REF_NAME}.md"', yml)
        self.assertIn("python.exe -m unittest discover tests", yml)
        self.assertIn('TEXTFOLD_NO_MODELS: "1"', yml)


if __name__ == "__main__":
    unittest.main()
