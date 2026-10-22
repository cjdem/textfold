"""A Chinese paper folds to five levels without a model, and an English paper keeps the prompt and levels it had."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import fold, ladder, local, store, translate
from textfold.tokens import split_sentences, tokenize_text

CHINESE = "# 中文测试\n\n这是背景。实验显示吸附量下降，这个结果支持结论。因此，可以认为该方法有效。\n"
ENGLISH = "# English test\n\nThe first sentence. The second one. The third one.\n"


def unit(text, uid="u0", role="para"):
    toks = tokenize_text(text)
    return {"id": uid, "role": role, "toks": toks, "sents": split_sentences(toks)}


def doc_of(*units):
    return {"atoms": {}, "units": {u["id"]: u for u in units}, "blocks": [],
            "chunks": [{"id": "c", "units": [u["id"] for u in units], "lad": None}]}


class ChineseLevels(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        data = mock.patch.object(store, "DATA", Path(temp.name))
        data.start()
        self.addCleanup(data.stop)

    def assemble(self, text):
        pid = local.import_text(text)
        return store.assemble(pid), pid

    def test_a_chinese_unit_has_five_distinct_levels_without_a_model(self):
        doc, _ = self.assemble(CHINESE)
        uid = next(iter(doc["units"]))
        view = fold.unit(doc, uid)
        self.assertEqual(view["sentences"],
                         ["这是背景。", "实验显示吸附量下降，这个结果支持结论。", "因此，可以认为该方法有效。"])
        self.assertEqual(view["full"], "这是背景。实验显示吸附量下降，这个结果支持结论。因此，可以认为该方法有效。")
        self.assertEqual(view["brief"], ["这是背景。"])
        # the written line is the claim sentence, not the first, as a Chinese unit often opens with a lead-in
        self.assertIn("认为", view["key"])
        self.assertNotEqual(view["key"], view["brief"][0])
        self.assertTrue(view["takeaway"])
        self.assertTrue(view["topic"])

    def test_apparatus_folds_to_nothing_below_full(self):
        doc, _ = self.assemble("# 中文测试\n\n第一章 绪论 ………… 1\n\n"
                               "①魏敬淼.金融法学[M].北京：中国政法大学出版社，2013：45.\n\n这是正文。第二句。\n")
        by_text = {fold.unit(doc, uid)["full"]: uid for uid in doc["units"]}
        for text, uid in by_text.items():
            if text.startswith(("第一章", "①魏敬淼")):
                view = fold.unit(doc, uid)
                self.assertEqual(view["brief"], [])
                self.assertEqual(view["key"], "")
                self.assertEqual(view["takeaway"], "")
                self.assertEqual(view["topic"], "")
        self.assertIn("这是正文。第二句。", by_text)

    def test_a_chinese_document_is_asked_for_levels_in_its_own_language(self):
        doc, _ = self.assemble(CHINESE)
        prompt = ladder.prompt_for(doc, doc["chunks"][0])
        self.assertIn("ONE sentence of at most 40 characters", prompt)
        self.assertIn("Each line is read on its own", prompt)
        self.assertIn("the text's own language", prompt)

    def test_an_english_document_keeps_its_prompt_and_its_levels(self):
        doc, _ = self.assemble(ENGLISH)
        prompt = ladder.prompt_for(doc, doc["chunks"][0])
        self.assertIn("ONE English sentence", prompt)
        self.assertNotIn("Each line is read on its own", prompt)
        self.assertNotIn("the text's own language", prompt)
        for u in doc["units"].values():
            u["lad"] = ladder.local(u, doc["atoms"])
        uid = next(iter(doc["units"]))
        self.assertEqual(fold.unit(doc, uid)["brief"], ["The first sentence."])
        ladder.fold_background(doc["chunks"][0], doc)
        ladder.dress(doc["chunks"][0], doc)
        for u in doc["units"].values():
            self.assertNotIn("glue", u["lad"])
            self.assertNotIn("l3", u["lad"])

    def test_stored_glue_and_l3_survive_a_round_trip(self):
        doc, pid = self.assemble(CHINESE)
        uid = next(iter(doc["units"]))
        doc["units"][uid]["lad"]["glue"] = "前半句"
        doc["units"][uid]["lad"]["l3"] = False
        store.save_en(doc, "test")
        restored = store.assemble(pid)
        self.assertEqual(restored["units"][uid]["lad"]["glue"], "前半句")
        self.assertIs(restored["units"][uid]["lad"]["l3"], False)

    def test_a_contents_line_is_not_glued_to_the_next_paragraph(self):
        toc, para = unit("第一章 绪论 ………… 1", "u0"), unit("从前都是部门规章，而该条例的法律位阶为行政", "u1")
        doc = doc_of(toc, para)
        for u in (toc, para):
            u["lad"] = ladder.local(u, doc["atoms"])
        self.assertEqual(toc["lad"]["brief"], [])           # apparatus: no levels below Full
        ladder.dress(doc["chunks"][0], doc)
        self.assertNotIn("glue", para["lad"])

    def test_a_paragraph_ending_with_an_ellipsis_carries_nothing(self):
        a, b = unit("该制度在实施中仍存在诸多问题……", "u0"), unit("监管部门应当加强协作。", "u1")
        doc = doc_of(a, b)
        for u in (a, b):
            u["lad"] = ladder.local(u, doc["atoms"])
        ladder.dress(doc["chunks"][0], doc)
        self.assertNotIn("glue", b["lad"])

    def test_an_argument_with_a_long_ellipsis_is_not_apparatus(self):
        u = unit("随着实践的发展，我国对于第三方支付的法律监管经历了从无到有的过程…………但这种监管仍然不足。")
        self.assertFalse(ladder.is_apparatus(u, {}))

    def test_section_ladder_keeps_the_budget_it_is_given(self):
        u = unit("正文。")
        got = ladder.section_ladder({"takeaway": "这是本节摘要的一句话说明", "topic": "不在摘要里的说法"},
                                    6, doc_of(u), doc_of(u)["chunks"][0])
        self.assertEqual(len(got["topic"]), 6)

    def test_a_topic_keeps_latin_and_version_numbers(self):
        text = "P2P 平台的风险监管"
        span = ladder.cjk_topic_span(text, 8)
        self.assertTrue(text[span[0]:span[1]].startswith("P2P"), text[span[0]:span[1]])
        text = "3.5版本的法律监管"
        span = ladder.cjk_topic_span(text, 8)
        self.assertTrue(text[span[0]:span[1]].startswith("3.5"), text[span[0]:span[1]])

    def test_a_chinese_model_reply_uses_the_chinese_rules(self):
        u = unit("这是背景。实验显示吸附量下降。")
        lad = ladder.assemble(u, {"role": "result", "takeaway": "吸附量下降", "reason": "因为温度降低",
                                  "topic": "吸附量下降", "evidence": [1]}, {}, "m")
        self.assertEqual(lad["brief"][-1]["t"], "。")
        self.assertLessEqual(len(lad["topic"]), 8)
        note = unit("①魏敬淼.金融法学[M].北京：中国政法大学出版社，2013：45.", "u1")
        self.assertEqual(ladder.assemble(note, {"takeaway": "注", "reason": "", "topic": "注", "evidence": [0]},
                                         {}, "m")["ev"], [])

    def test_an_english_line_that_looks_like_dot_leaders_still_folds(self):
        u = unit("Some argument ... still continues here.")
        self.assertNotEqual(ladder.local(u, {})["brief"], [])

    def test_translation_skips_a_unit_the_ladder_suppressed(self):
        u = unit("①魏敬淼.金融法学[M].")
        u["lad"] = {"brief": [], "ev": [], "tn": 0, "topic": [], "model": "m"}
        self.assertFalse(translate.worded(u))
        normal = unit("这是正文。")
        normal["lad"] = ladder.local(normal, {})
        self.assertTrue(translate.worded(normal))


if __name__ == "__main__":
    unittest.main()
