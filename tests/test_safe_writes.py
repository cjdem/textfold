"""The shared writer every file TextFold rewrites goes through: a temporary file of its own beside the file, moved over
it only when whole; a move that fails leaves the old file and takes the temporary one away; and the write does not
create the folder, so a save that crosses a document's move to the trash cannot leave a ghost folder behind.

Run from the repo root:
    python -m unittest discover tests
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import store


class SafeWrites(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_a_move_that_fails_leaves_the_old_file_and_takes_the_temporary_away(self):
        d = Path(self.tmp.name) / "x"
        d.mkdir()
        f = d / "a.json"
        f.write_text("old", encoding="utf-8")
        with mock.patch.object(store, "_replace", side_effect=PermissionError(13, "in use")):
            with self.assertRaises(PermissionError):
                store.write_text_atomic(f, "new")
        self.assertEqual(f.read_text(encoding="utf-8"), "old")
        self.assertEqual([p.name for p in d.iterdir()], ["a.json"])   # (no temporary file left)

    def test_a_write_does_not_create_the_folder(self):
        f = Path(self.tmp.name) / "gone" / "a.json"
        with self.assertRaises(FileNotFoundError):
            store.write_text_atomic(f, "new")
        self.assertFalse(f.parent.exists())


if __name__ == "__main__":
    unittest.main()
