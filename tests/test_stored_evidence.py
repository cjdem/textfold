"""A stored layer's evidence names sentences by number. A parser change can make an ordinal point past the end of a
shorter part (a sentence split out before it, and the paragraph cut into parts), where the reader would index an
undefined sentence; assemble falls back to the first sentence instead."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import fold, local, store


class StoredEvidence(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        data = mock.patch.object(store, "DATA", Path(temp.name))
        data.start()
        self.addCleanup(data.stop)

    def test_evidence_past_the_end_falls_back_to_the_first_sentence(self):
        pid = local.import_text("# T\n\nOne. Two.\n")
        doc = store.assemble(pid)
        uid = next(iter(doc["units"]))
        doc["units"][uid]["lad"]["ev"] = [9]
        store.save_en(doc, "test")
        restored = store.assemble(pid)
        self.assertEqual(restored["units"][uid]["lad"]["ev"], [0])
        self.assertEqual(fold.unit(restored, uid)["brief"], ["One."])

    def test_an_empty_stored_ladder_falls_back_to_the_local_one(self):
        pid = local.import_text("# T\n\nOne. Two.\n")
        uid = next(iter(store.assemble(pid)["units"]))
        store.write(pid, "en", {"version": "t", "model": "test", "units": {uid: {}}, "chunks": {}, "edges": []})
        doc = store.assemble(pid)
        self.assertEqual(doc["units"][uid]["lad"]["model"], "local")
        self.assertEqual(fold.unit(doc, uid)["brief"], ["One."])


if __name__ == "__main__":
    unittest.main()
