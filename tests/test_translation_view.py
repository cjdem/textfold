"""A translation is read with the base layer's page-break join (`glue`) and its background step-down: a translated unit
that lost them would open mid-sentence and show at Takeaway a background line the Chinese base hides at that level.
The reader takes both from the unit's own language layer (`view()` in reader.js), so a document read for the reader
(`store.assemble`) gives the translated lad the base's `glue` and `tn: 0`. The join is the base's words: the page
break cut the unit in the same place, so it is copied only into a Chinese translation of a text whose own words are
Chinese. A generation attaches layers without the view — it saves them back, and must not write the base's fields into
the translation file.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import store


class Applied(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)

    def _doc(self, lad):
        return {"meta": {"id": "md-tr-0001"}, "atoms": {}, "units": {"u0": {"toks": [], "sents": [[0, 1]], "lad": lad}},
                "chunks": [], "edges": []}

    def _tr(self, lad):
        return {"version": "v", "units": {"u0": {"toks": [], "sents": [[0, 1]], "lad": lad}}, "chunks": {}}

    def _applied(self, base, translated):
        doc = self._doc(base)
        store.apply_tr(doc, "zh", self._tr(translated), view=True)
        return doc["units"]["u0"]["tr"]["zh"]["lad"]

    def test_the_page_break_join_is_carried_into_the_translation(self):
        lad = self._applied({"brief": [], "tn": 2, "glue": "上一段被切断的尾部"}, {"brief": [], "tn": 2, "topic": []})
        self.assertEqual(lad["glue"], "上一段被切断的尾部")

    def test_a_takeaway_that_stepped_down_steps_down_in_the_translation(self):
        lad = self._applied({"brief": [], "tn": 0}, {"brief": [], "tn": 3, "topic": []})
        self.assertEqual(lad["tn"], 0)

    def test_a_translation_keeps_its_own_join(self):
        lad = self._applied({"brief": [], "tn": 2, "glue": "base"}, {"brief": [], "tn": 2, "glue": "translated", "topic": []})
        self.assertEqual(lad["glue"], "translated")

    def test_a_base_without_the_join_or_step_down_leaves_the_translation_alone(self):
        lad = self._applied({"brief": [], "tn": 2}, {"brief": [], "tn": 3, "topic": []})
        self.assertEqual(lad["tn"], 3)
        self.assertNotIn("glue", lad)

    def test_a_japanese_join_is_not_copied_into_a_chinese_translation(self):
        lad = self._applied({"brief": [], "tn": 0, "glue": "日本語の"}, {"brief": [], "tn": 3, "topic": []})
        self.assertNotIn("glue", lad)   # (another language's words are not this sentence's opening)
        self.assertEqual(lad["tn"], 0)   # (the step-down is the section's, not the language's)

    def test_every_written_form_of_kana_and_hangul_refuses_the_join(self):
        # (halfwidth katakana, katakana phonetic extensions, halfwidth hangul, jamo, compatibility jamo)
        for glue in ["ｶﾘｳﾍ", "ㇰ", "ﾡ", "한", "ㄱ"]:
            with self.subTest(glue=glue):
                lad = self._applied({"brief": [], "tn": 2, "glue": glue}, {"brief": [], "tn": 2, "topic": []})
                self.assertNotIn("glue", lad)

    def test_a_generation_attaches_without_the_view_and_saves_a_clean_layer(self):
        pid = "md-tr-0002"
        store.pdir(pid).mkdir(parents=True)
        (store.pdir(pid) / "meta.json").write_text('{"id": "md-tr-0002"}', encoding="utf-8")
        doc = self._doc({"brief": [], "tn": 0, "glue": "上一段的尾部"})
        doc["meta"]["id"] = pid
        store.apply_tr(doc, "zh", self._tr({"brief": [], "tn": 2, "topic": []}))   # (the pipeline's attach)
        store.save_tr(doc, "zh", "base", "m")
        kept = store.read(pid, "tr-zh")["units"]["u0"]["lad"]
        self.assertNotIn("glue", kept)   # (the base's fields are not written into the translation file)
        self.assertEqual(kept["tn"], 2)

    def test_a_document_read_for_the_reader_carries_the_view(self):
        pid = "md-tr-0003"
        d = store.pdir(pid)
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"id": pid, "title": "T"}), encoding="utf-8")
        (d / "source.html").write_text('<article class="ltx_document"><p class="ltx_p">第一段。第二段。</p></article>',
                                       encoding="utf-8")
        unit = {"toks": [{"t": "第一段。"}, {"t": "第二段。"}], "sents": [[0, 1], [1, 2]]}
        store.write(pid, "en", {"version": "v", "model": "m", "units": {"u0": {
            "brief": [{"t": "第一段。"}], "tn": 0, "glue": "上一段的尾部", "ev": [0], "topic": []}},
            "chunks": {"c0": None}, "edges": []})
        store.write(pid, "tr-zh", {"version": "t", "base": "v", "model": "m", "units": {"u0": {**unit, "lad": {
            "brief": [{"t": "第一段。"}], "tn": 2, "ev": [0], "topic": []}}}, "chunks": {"c0": None}})
        doc = store.assemble(pid, only=["zh"])
        lad = doc["units"]["u0"]["tr"]["zh"]["lad"]
        self.assertEqual(lad["glue"], "上一段的尾部")
        self.assertEqual(lad["tn"], 0)
        kept = store.read(pid, "tr-zh")["units"]["u0"]["lad"]   # (a read does not write the view into the file)
        self.assertNotIn("glue", kept)
        self.assertEqual(kept["tn"], 2)


if __name__ == "__main__":
    unittest.main()
