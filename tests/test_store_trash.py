"""store.trash and store.untrash: a deleted paper's folder (source, layers, notes) comes back whole, and the place it
had in the library comes with it when the reader undoes the delete.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from textfold import store

PID = "2512.24601"


class Trash(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)
        d = store.pdir(PID)
        d.mkdir(parents=True)
        (d / "meta.json").write_text('{"id": "%s", "title": "A"}' % PID, encoding="utf-8")
        (d / "notes.json").write_text('{"notes": []}', encoding="utf-8")

    def trashdir(self):
        return store.DATA / "papers" / ".trash"

    def copy(self, name, kept=None, meta=True):
        d = self.trashdir() / name
        d.mkdir(parents=True, exist_ok=True)
        if meta:
            (d / "meta.json").write_text("{}", encoding="utf-8")
        if kept is not None:
            (d / "library.json").write_text(json.dumps(kept), encoding="utf-8")
        return d

    def test_the_place_comes_back_with_the_folder(self):
        kept = {"of": "f-3a9c01d2", "added": 1790000000.0, "opened": 1791000000.0}
        where = store.trash(PID, kept)
        self.assertTrue((where / "meta.json").exists())
        self.assertTrue((where / "notes.json").exists())
        self.assertEqual(json.loads((where / "library.json").read_text(encoding="utf-8")), kept)
        self.assertFalse(store.pdir(PID).exists())
        self.assertEqual([p.name for p in (store.DATA / "papers").iterdir() if p.name.startswith(".") and p.name != ".trash"], [])   # (no temporary file left)
        self.assertEqual(store.untrash(PID), kept)
        self.assertTrue((store.pdir(PID) / "notes.json").exists())
        self.assertFalse((store.pdir(PID) / "library.json").exists())   # (the reader's file does not stay in the paper)
        self.assertEqual(list(self.trashdir().iterdir()), [])

    def test_a_delete_without_a_place_writes_no_library_file(self):
        where = store.trash(PID)
        self.assertFalse((where / "library.json").exists())
        self.assertEqual(store.untrash(PID), {})

    def test_restoring_what_is_not_there(self):
        self.assertIsNone(store.untrash(PID))   # (never deleted)
        self.assertIsNone(store.untrash("../etc"))
        where = store.trash(PID)
        store.pdir(PID).mkdir(parents=True)   # (read again while a copy is in the trash: the copy stays)
        (store.pdir(PID) / "meta.json").write_text("{}", encoding="utf-8")
        self.assertIsNone(store.untrash(PID))
        self.assertTrue(where.exists())

    def test_the_latest_copy_comes_back(self):
        shutil.rmtree(store.pdir(PID))
        old = self.copy(f"{PID}-20260101-000000", {"added": 1})
        new = self.copy(f"{PID}-20260102-000000", {"added": 2})
        self.assertEqual(store.untrash(PID), {"added": 2})
        self.assertTrue(store.pdir(PID).exists())
        self.assertFalse(new.exists())
        self.assertTrue(old.exists())   # (the older copy is left where it is)

    def test_a_damaged_place_comes_back_empty(self):
        shutil.rmtree(store.pdir(PID))
        where = self.copy(f"{PID}-20260103-000000", None)
        (where / "library.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(store.untrash(PID), {})
        self.assertTrue(store.pdir(PID).exists())
        self.assertFalse((store.pdir(PID) / "library.json").exists())

    def test_the_place_is_held_until_the_library_has_it(self):
        store.trash(PID, {"added": 1})
        seen = {}

        def use(kept):
            seen.update(kept)
            self.assertTrue((store.pdir(PID) / "library.json").exists())   # (still there while the library takes it)

        self.assertEqual(store.untrash(PID, use), {"added": 1})
        self.assertEqual(seen, {"added": 1})
        self.assertFalse((store.pdir(PID) / "library.json").exists())
        # a library that fails leaves the place in the paper, to be read again
        store.trash(PID, {"added": 2})

        def boom(kept):
            raise RuntimeError("no")

        with self.assertRaises(RuntimeError):
            store.untrash(PID, boom)
        self.assertTrue((store.pdir(PID) / "library.json").exists())

    def test_another_documents_copy_is_not_taken(self):
        shutil.rmtree(store.pdir(PID))
        other = self.copy(f"{PID}-1-20260101-000000", {"added": 1})
        self.assertIsNone(store.untrash(PID))
        self.assertTrue(other.exists())

    def test_a_copy_without_its_meta_is_skipped(self):
        shutil.rmtree(store.pdir(PID))
        where = self.copy(f"{PID}-20260104-000000", None, meta=False)
        (where / "notes.json").write_text("{}", encoding="utf-8")
        self.assertIsNone(store.untrash(PID))
        self.assertTrue(where.exists())

    def test_two_restores_do_not_both_take_it(self):
        store.trash(PID, {"added": 1})
        got = []

        def run():
            try:
                got.append(store.untrash(PID))
            except Exception as e:   # (the test reports what the restore raised)
                got.append(e)

        threads = [threading.Thread(target=run, daemon=True) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(5)
        self.assertEqual(len([g for g in got if isinstance(g, dict)]), 1, got)
        self.assertTrue(all(g is None or isinstance(g, dict) for g in got), got)
        self.assertTrue(store.pdir(PID).exists())
        self.assertEqual(list(self.trashdir().iterdir()), [])


if __name__ == "__main__":
    unittest.main()
