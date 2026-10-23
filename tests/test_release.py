"""The tag build publishes the notes a release carries and runs the Python suite before it builds the app: a release
body is not a placeholder, and a release is not shipped without the tests the change workflow runs locally.

Run from the repo root:
    python -m unittest discover tests
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = ROOT / ".github" / "workflows" / "desktop.yml"


class Release(unittest.TestCase):
    def setUp(self):
        self.yml = DESKTOP.read_text(encoding="utf-8")

    def step(self, name):
        """One named step's lines, up to the next one, with its comments taken out: a comment must not satisfy a
        check of what the step runs."""
        after = self.yml.split(f"- name: {name}", 1)[1]
        block = after.split("- name:", 1)[0]
        return "\n".join(line.split(" #", 1)[0] for line in block.splitlines()
                         if not line.lstrip().startswith("#"))

    def test_the_draft_is_built_from_the_notes_file(self):
        self.assertNotIn("Building the app.", self.yml)   # (the placeholder the workflow used to publish)
        draft = self.step("A draft release, filled by the build")
        self.assertIn('--notes-file "docs/releases/$TAG.md"', draft)
        self.assertIn('gh release edit "$TAG" -R "$REPO" --notes-file', draft)
        notes = self.step("The release has notes of its own")
        self.assertIn('test -s "docs/releases/${GITHUB_REF_NAME}.md"', notes)
        self.assertLess(self.yml.index("- name: The release has notes of its own"),
                        self.yml.index("- name: A draft release, filled by the build"))

    def test_the_tag_build_runs_the_python_suite_in_utf8(self):
        python = self.step("Python tests")
        self.assertIn("python.exe -m unittest discover tests", python)
        self.assertIn('TEXTFOLD_NO_MODELS: "1"', python)
        self.assertIn('PYTHONUTF8: "1"', python)   # (a clean en-US runner's ANSI page cannot encode the suite's text)

    def test_the_current_version_has_release_notes(self):
        version = re.search(r'^__version__ = "([^"]+)"',
                            (ROOT / "textfold" / "__init__.py").read_text(encoding="utf-8"), re.M).group(1)
        notes = ROOT / "docs" / "releases" / f"v{version}.md"
        self.assertTrue(notes.is_file(), f"no release notes at {notes.relative_to(ROOT)}")
        self.assertIn(version, notes.read_text(encoding="utf-8").strip().splitlines()[0])


if __name__ == "__main__":
    unittest.main()
