"""The English layer is keyed by unit id, and an id names the same paragraph only while the parse gives it the same
tokens: a mixed Chinese/English paragraph can be cut into a different number of parts, so every later id can shift
onto another paragraph, and a parser change can renumber the atoms a ladder names. `store.save_en` keeps a
fingerprint of each unit (`h`): its words and its atoms' ids and visible text. `apply_en` reads a unit whose
fingerprint changed with its own local levels instead of another paragraph's takeaway, reporting the layer stale; a
layer saved before fingerprints is trusted only when its unit ids are exactly this parse's.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import fold, ladder, store


def _unit(text):
    toks = [{"t": w, "s": 1} for w in text.split(" ")]
    toks[-1].pop("s")
    return {"toks": toks, "sents": [[0, len(toks)]]}


def _lad(text):
    return {"brief": [{"t": text}], "ev": [0], "tn": 1}


def _doc(units):
    return {"meta": {"id": "md-id-0001"}, "atoms": {},
            "units": {uid: {"id": uid, **u} for uid, u in units.items()}, "chunks": [], "edges": []}


class Applied(unittest.TestCase):
    def test_a_layer_whose_units_still_match_is_used_whole(self):
        doc = _doc({"u0": _unit("Alpha beta.")})
        en = {"units": {"u0": _lad("Alpha")}, "chunks": {}, "edges": [],
              "h": {"u0": store.unit_hash(doc["units"]["u0"])}}
        self.assertTrue(store.apply_en(doc, en))
        self.assertEqual(doc["units"]["u0"]["lad"], en["units"]["u0"])

    def test_a_unit_whose_words_changed_is_read_with_its_own_levels(self):
        doc = _doc({"u0": _unit("Alpha beta.")})
        other = _doc({"u0": _unit("Gamma delta.")})["units"]["u0"]
        en = {"units": {"u0": _lad("the old paragraph")}, "chunks": {}, "edges": [],
              "h": {"u0": store.unit_hash(other)}}
        self.assertFalse(store.apply_en(doc, en))
        self.assertEqual(doc["units"]["u0"]["lad"], ladder.local(doc["units"]["u0"], {}, False))
        self.assertNotEqual(doc["units"]["u0"]["lad"], en["units"]["u0"])

    def test_a_layer_saved_before_fingerprints_is_used_when_its_ids_are_this_parse_s(self):
        doc = _doc({"u0": _unit("Alpha beta.")})
        en = {"units": {"u0": _lad("Alpha")}, "chunks": {}, "edges": []}
        self.assertTrue(store.apply_en(doc, en))
        self.assertEqual(doc["units"]["u0"]["lad"], en["units"]["u0"])

    def test_a_renumbered_atom_makes_the_layer_stale_even_when_its_words_are_the_same(self):
        # (a stored ladder names atoms by id: the same visible text under another id is another token for the reader)
        doc = _doc({"u0": {"toks": [{"t": "The", "s": 1}, {"a": "a1"}], "sents": [[0, 2]]}})
        doc["atoms"] = {"a1": {"kind": "math", "alt": "x^2"}}
        en = {"units": {"u0": _lad("old")}, "chunks": {}, "edges": [],
              "h": {"u0": store.unit_hash({"toks": [{"t": "The", "s": 1}, {"a": "a0"}]},
                                          {"a0": {"kind": "math", "alt": "x^2"}})}}
        self.assertFalse(store.apply_en(doc, en))
        self.assertEqual(doc["units"]["u0"]["lad"], ladder.local(doc["units"]["u0"], doc["atoms"], False))

    def test_a_spacing_flag_change_alone_keeps_the_layer(self):
        doc = _doc({"u0": _unit("Alpha beta.")})   # (the doc's first token says a space follows it)
        saved = {"toks": [{"t": "Alpha"}, {"t": "beta."}], "sents": [[0, 2]]}   # (the layer's does not)
        en = {"units": {"u0": _lad("Alpha")}, "chunks": {}, "edges": [], "h": {"u0": store.unit_hash(saved)}}
        self.assertTrue(store.apply_en(doc, en))   # (the words a unit has, not how the parser spaced them)

    def test_an_old_layer_whose_ids_moved_does_not_put_another_paragraph_s_takeaway_here(self):
        # (the audit's shape: old ids u0, u1, u2 against this parse's u0, u0~2, u2, u3)
        doc = _doc({"u0": _unit("First."), "u0~2": _unit("Second."), "u2": _unit("Third."), "u3": _unit("Fourth.")})
        en = {"units": {"u0": _lad("First"), "u1": _lad("old second"), "u2": _lad("old third")},
              "chunks": {}, "edges": []}
        self.assertFalse(store.apply_en(doc, en))
        for uid in ("u0", "u0~2", "u2", "u3"):
            self.assertEqual(doc["units"][uid]["lad"], ladder.local(doc["units"][uid], {}, False))
        self.assertNotEqual(doc["units"]["u2"]["lad"], en["units"]["u2"])


class Assembled(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)

    def _paper(self, text="One sentence. Another sentence."):
        pid = "md-id-0002"
        d = store.pdir(pid)
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"id": pid, "title": "T"}), encoding="utf-8")
        (d / "source.html").write_text(f'<article class="ltx_document"><p class="ltx_p">{text}</p></article>',
                                       encoding="utf-8")
        doc = store.parsed(pid)
        for u in doc["units"].values():
            u["lad"] = ladder.local(u, doc["atoms"], False)
        store.save_en(doc, "m")
        return pid, doc

    def test_save_en_keeps_the_fingerprint_of_every_unit(self):
        pid, doc = self._paper()
        en = store.read(pid, "en")
        self.assertEqual(en["h"], {uid: store.unit_hash(u, doc["atoms"]) for uid, u in doc["units"].items()})

    def _rewrite(self, pid):
        (store.pdir(pid) / "source.html").write_text(
            '<article class="ltx_document"><p class="ltx_p">Different words now.</p></article>', encoding="utf-8")

    def test_a_paragraph_whose_words_changed_is_reported_stale_and_read_local(self):
        pid, doc = self._paper()
        self._rewrite(pid)   # (the same id now names another paragraph, as a parser change can leave it)
        out = store.assemble(pid)
        self.assertIn("en", out["meta"]["stale"])
        uid = next(iter(out["units"]))
        self.assertEqual(out["units"][uid]["lad"], ladder.local(out["units"][uid], out["atoms"], False))

    def test_an_old_layer_with_a_changed_unit_set_is_read_local_end_to_end(self):
        pid, doc = self._paper()
        en = store.read(pid, "en")
        en.pop("h", None)   # (a layer saved before fingerprints)
        store.write(pid, "en", en)
        (store.pdir(pid) / "source.html").write_text(
            '<article class="ltx_document"><p class="ltx_p">First paragraph.</p>'
            '<p class="ltx_p">Second paragraph.</p></article>', encoding="utf-8")
        out = store.assemble(pid)
        self.assertIn("en", out["meta"]["stale"])
        for u in out["units"].values():
            self.assertEqual(u["lad"], ladder.local(u, out["atoms"], False))

    def test_an_export_of_a_stale_layer_says_so(self):
        pid, doc = self._paper()
        self._rewrite(pid)
        d = fold.document(pid)
        self.assertTrue(d["provenance"].get("stale"))
        self.assertIn("no longer match", fold.markdown(d, "brief"))

    def test_a_translation_on_an_older_base_is_not_marked_in_the_export(self):
        pid, doc = self._paper()
        units = {uid: {"toks": u["toks"], "sents": u["sents"], "lad": {"brief": [{"t": "译"}], "ev": [0], "tn": 1}}
                 for uid, u in doc["units"].items()}
        store.write(pid, "tr-zh", {"version": "t", "base": "older", "model": "m", "units": units, "chunks": {}})
        out = store.assemble(pid)
        self.assertIn("zh", out["meta"]["stale"])
        self.assertNotIn("en", out["meta"]["stale"])
        self.assertNotIn("stale", fold.document(pid, "zh")["provenance"])   # (the reader's menu reports it, not the export)

    def test_a_translation_of_a_base_that_no_longer_fits_is_reported_stale_too(self):
        pid, doc = self._paper()
        en = store.read(pid, "en")
        units = {uid: {"toks": u["toks"], "sents": u["sents"], "lad": {"brief": [{"t": "译"}], "ev": [0], "tn": 1}}
                 for uid, u in doc["units"].items()}
        store.write(pid, "tr-zh", {"version": "t", "base": en["version"], "model": "m",
                                   "units": units, "chunks": {}})
        self._rewrite(pid)
        out = store.assemble(pid)
        self.assertIn("en", out["meta"]["stale"])
        self.assertIn("zh", out["meta"]["stale"])


if __name__ == "__main__":
    unittest.main()
