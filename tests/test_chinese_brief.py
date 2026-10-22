"""Chinese imports must expose separate sentences for the verbatim Brief level, without a model call."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import fold, ladder, local, store
from textfold.tokens import plain


class ChineseBrief(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        data = mock.patch.object(store, "DATA", Path(temp.name))
        data.start()
        self.addCleanup(data.stop)

    def test_local_brief_keeps_only_the_first_sentence(self):
        pid = local.import_text("# 中文测试\n\n这是背景。实验显示吸附量下降。这个结果支持结论。\n")
        doc = store.assemble(pid)
        uid = next(iter(doc["units"]))
        view = fold.unit(doc, uid)
        self.assertEqual(view["sentences"], ["这是背景。", "实验显示吸附量下降。", "这个结果支持结论。"])
        self.assertEqual(view["brief"], ["这是背景。"])
        self.assertEqual(view["full"], "这是背景。实验显示吸附量下降。这个结果支持结论。")
        self.assertNotEqual(" ".join(view["brief"]), view["full"])

    def test_selected_evidence_survives_storage_with_inline_math(self):
        pid = local.import_text("# 中文测试\n\n这是背景。实验显示**吸附量下降**，满足$x<1$。这个结果支持结论。\n")
        doc = store.assemble(pid)
        uid = next(iter(doc["units"]))
        u = doc["units"][uid]
        self.assertEqual(len(u["sents"]), 3)
        prompt = ladder.prompt_for(doc, doc["chunks"][0])
        self.assertIn("  0: 这是背景。\n  1: 实验显示吸附量下降，满足$x<1$。\n  2: 这个结果支持结论。", prompt)
        u["lad"] = ladder.assemble(u, {"evidence": [1], "takeaway": "Adsorption decreases",
                                      "topic": "Adsorption", "reason": ""}, doc["atoms"], "test")
        store.save_en(doc, "test")
        restored = store.assemble(pid)
        view = fold.unit(restored, uid)
        self.assertEqual(view["evidence"], [1])
        self.assertEqual(view["brief"], ["实验显示吸附量下降，满足$x<1$。"])
        self.assertEqual(plain(restored["units"][uid]["toks"], restored["atoms"]),
                         "这是背景。实验显示吸附量下降，满足$x<1$。这个结果支持结论。")
        exported = fold.document(pid)
        brief = fold.markdown(exported, "brief")
        self.assertIn(view["brief"][0], brief)
        self.assertNotIn("这是背景。", brief)
        self.assertNotIn("这个结果支持结论。", brief)
        self.assertIn("这个结果支持结论。", fold.markdown(exported, "full"))

    def test_long_chinese_paragraph_stays_one_unit_with_valid_sentence_ranges(self):
        # a CJK paragraph is not cut into parts (parse.cjk_heavy): a paper read before sentences ended at 。 keeps
        # its unit ids, so its stored levels stay on their paragraphs
        sentences = [f"这是第{i}句。" for i in range(15)]
        pid = local.import_text("# 中文测试\n\n" + "".join(sentences) + "\n\n另一段。\n")
        doc = store.assemble(pid)
        # the following paragraph keeps the id it had when the long paragraph was one sentence
        self.assertEqual(list(doc["units"]), ["u0", "u1"])
        actual = [s for uid in doc["units"] if uid == "u0" for s in fold.unit(doc, uid)["sentences"]]
        self.assertEqual(actual, sentences)
        u = doc["units"]["u0"]
        self.assertEqual(u["sents"][0][0], 0)
        self.assertEqual(u["sents"][-1][1], len(u["toks"]))

    def test_a_long_japanese_paragraph_stays_one_unit_too(self):
        # the splitter treats kana as CJK; the guard counts the same characters
        sentences = [f"これは第{i}です。" for i in range(15)]
        pid = local.import_text("# 日本語\n\n" + "".join(sentences))
        doc = store.assemble(pid)
        self.assertEqual(len(doc["units"]), 1)
        actual = [s for uid in doc["units"] for s in fold.unit(doc, uid)["sentences"]]
        self.assertEqual(actual, sentences)

    def test_a_long_english_paragraph_is_still_cut_into_parts(self):
        # the CJK guard must not change English: its page-long paragraphs are still cut as before
        sentences = [f"This is sentence {i}." for i in range(15)]
        pid = local.import_text("# English test\n\n" + " ".join(sentences))
        doc = store.assemble(pid)
        self.assertEqual(list(doc["units"]), ["u0", "u0~2", "u0~3"])
        actual = [s for uid in doc["units"] for s in fold.unit(doc, uid)["sentences"]]
        self.assertEqual(actual, sentences)


if __name__ == "__main__":
    unittest.main()
