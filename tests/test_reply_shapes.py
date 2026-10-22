"""A model's reply read whatever shape it comes in (#17): an OpenAI-compatible endpoint in JSON mode promises valid JSON,
not the schema's shape, so a reply's units may come as strings, as an object keyed by id or as one JSON string, and its
text as a list of parts. No model is called.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import ladder, llm, llm_openai, local, pipeline, store, translate

UNIT = {"id": "U0", "role": "claim", "takeaway": "Folding helps readers", "topic": "folding", "reason": "Levels nest",
        "evidence": [0]}


class UnitsTest(unittest.TestCase):
    def test_as_asked(self):
        self.assertEqual(llm.units_of({"units": [UNIT]}), [UNIT])

    def test_other_shapes(self):
        for units in ([json.dumps(UNIT)], {"U0": {k: v for k, v in UNIT.items() if k != "id"}}, json.dumps([UNIT])):
            with self.subTest(units=type(units).__name__):
                self.assertEqual(llm.units_of({"units": units})[0]["takeaway"], UNIT["takeaway"])

    def test_the_key_names_the_unit(self):
        self.assertEqual(llm.units_of({"units": {"U0": {"takeaway": "x"}}})[0]["id"], "U0")
        self.assertEqual(llm.units_of({"units": {"U0": {"id": "U9", "takeaway": "x"}}})[0]["id"], "U0")   # (the key wins)
        self.assertEqual(llm.units_of({"units": {"U0": json.dumps({"takeaway": "x"})}})[0]["id"], "U0")

    def test_what_cannot_be_read_is_dropped(self):
        self.assertEqual(llm.units_of({"units": ["U0", "U1"]}), [])
        self.assertEqual(llm.units_of({"units": "not json"}), [])
        self.assertEqual(llm.units_of("a string, not an object"), [])

    def test_as_obj(self):
        self.assertEqual(llm.as_obj('{"takeaway": "x"}'), {"takeaway": "x"})
        self.assertEqual(llm.as_obj("x"), {})
        self.assertEqual(llm.as_obj(None), {})
        self.assertEqual(llm.as_obj({"takeaway": "x"}), {"takeaway": "x"})


class ContentTest(unittest.TestCase):
    def test_text_or_parts(self):
        self.assertEqual(llm_openai._content({"choices": [{"message": {"content": "{}"}}]}), "{}")
        parts = [{"type": "text", "text": '{"a"'}, {"type": "text", "text": ": 1}"}]
        self.assertEqual(llm_openai._content({"choices": [{"message": {"content": parts}}]}), '{"a": 1}')
        self.assertEqual(llm_openai._content({"choices": [{"message": "{}"}]}), "{}")

    def test_a_part_that_is_not_text_is_not_the_reply(self):
        parts = [{"type": "reasoning", "text": '{"scratch": 1}'}, {"type": "text", "text": '{"units": []}'}]
        self.assertEqual(llm_openai._content({"choices": [{"message": {"content": parts}}]}), '{"units": []}')
        self.assertEqual(llm_openai._content({"choices": [{"message": {"content": [{"type": "output_text", "text": "{}"}]}}]}), "{}")
        odd = [{"type": ["text"], "text": "{}"}]   # (a type that is not a string is not a reasoning part)
        self.assertEqual(llm_openai._content({"choices": [{"message": {"content": odd}}]}), "{}")

    def test_not_a_completion(self):
        for body in ({"error": "Model busy"}, {"choices": ["x"]}, "a string", {"choices": []}):
            with self.subTest(body=body):
                self.assertIsNone(llm_openai._content(body))


class SectionTest(unittest.TestCase):
    def test_a_section_written_as_a_string(self):
        lad = ladder.section_ladder("A plain sentence")
        self.assertEqual(" ".join(t["t"] for t in lad["take"]), "A plain sentence")

    def test_a_section_written_as_a_json_string_twice(self):
        lad = ladder.section_ladder(json.dumps("A plain sentence"))
        self.assertEqual(" ".join(t["t"] for t in lad["take"]), "A plain sentence")   # (no quotes kept)


class FallbackTest(unittest.TestCase):
    """A reply of a shape still not foreseen falls back locally, rather than failing the document."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        p = mock.patch.object(store, "DATA", self.tmp / "data")
        p.start()
        self.addCleanup(p.stop)
        pid = local.import_text("# A note\n\nA short sentence that states one thing.\n")
        self.pid = pid
        self.doc = store.parsed(pid)
        for u in self.doc["units"].values():   # (what a translation prompt reads; the ladder's own fallback)
            u["lad"] = ladder.local(u, self.doc["atoms"])
        store.save_en(self.doc, "local")
        self.cfg = {"kind": "api", "id": "test/model", "protocol": "openai", "effort": None}

    def test_a_one_chunk_document_falls_back_to_local_ladders(self):
        reply = {"out": {"units": [{"id": "U0", "takeaway": 5}]}, "cost": 0}
        with mock.patch.object(llm, "call", return_value=(reply, False)):
            ladder.build(self.doc, self.cfg, self.tmp / "cache", log=lambda *a: None)   # (an unreadable shape must not fail the build)
        self.assertTrue(all("lad" in u for u in self.doc["units"].values()))

    def test_a_translation_reply_that_names_no_unit_fails_its_part(self):
        for out in ([{"id": "U0"}], {"units": []}, {"units": "not json"}):
            with self.subTest(out=type(out).__name__):
                doc = store.parsed(self.pid)
                for u in doc["units"].values():
                    u["lad"] = ladder.local(u, doc["atoms"])
                with mock.patch.object(llm, "call", return_value=({"out": out}, False)):
                    with self.assertRaises(RuntimeError):
                        translate.build(doc, "zh", self.cfg, self.tmp / "cache2", log=lambda *a: None)
                for u in doc["units"].values():
                    self.assertNotIn("zh", u.get("tr", {}))   # (nothing half-translated is left behind)

    def test_a_field_wrong_translation_reply_fails_its_part(self):
        out = {"units": [{"id": "U0", "sentences": [1]}]}   # (a sentence not a string: the reader raises)
        with mock.patch.object(llm, "call", return_value=({"out": out}, False)):
            with self.assertRaises(RuntimeError):
                translate.build(self.doc, "zh", self.cfg, self.tmp / "cache3", log=lambda *a: None)
        for u in self.doc["units"].values():
            self.assertNotIn("zh", u.get("tr", {}))

    def test_a_translation_whose_every_call_failed_is_not_saved(self):
        with mock.patch.object(translate, "build", side_effect=RuntimeError("no reply")) as build, \
                mock.patch.object(store, "save_tr") as save:
            with self.assertRaises(RuntimeError):
                pipeline.generate(self.pid, "zh", self.cfg, log=lambda *a: None)
        build.assert_called_once()   # (the translation was asked for, and then not saved)
        save.assert_not_called()   # (nothing was translated: a layer of no translation is no layer)

    def test_a_part_that_fails_late_removes_what_it_already_translated(self):
        pid = local.import_text("# Two\n\nFirst paragraph here.\n\nSecond paragraph here.\n")
        doc = store.parsed(pid)
        for u in doc["units"].values():
            u["lad"] = ladder.local(u, doc["atoms"])
        self.assertGreaterEqual(len(doc["units"]), 2)
        out = {"units": [{"id": "U0"}, {"id": "U1"}]}

        def assemble(u, o, atoms, lang, warn):
            if o and o.get("id") == "U0":
                return {"toks": [], "sents": [], "lad": {"brief": [], "tn": 0, "topic": []}}
            raise AttributeError("a field of the wrong type")

        with mock.patch.object(llm, "call", return_value=({"out": out}, False)), \
                mock.patch.object(translate, "assemble", side_effect=assemble):
            with self.assertRaises(RuntimeError):
                translate.build(doc, "zh", self.cfg, self.tmp / "cache4", log=lambda *a: None)
        self.assertFalse(any("zh" in u.get("tr", {}) for u in doc["units"].values()))   # (U0's tr was removed too)


class ForgetTest(unittest.TestCase):
    def test_a_kept_reply_its_caller_could_not_read_is_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "abc.json"
            f.write_text("{}")
            llm.forget({"file": str(f)})
            self.assertFalse(f.exists())
            llm.forget({})   # a reply that was never kept: nothing to drop

    def test_the_next_call_asks_again(self):
        spec = {"id": "test/model", "protocol": "openai", "effort": None}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ), \
                mock.patch.object(llm, "spec_of", return_value=spec), \
                mock.patch.object(llm, "_once", return_value=({"units": [UNIT]}, None)) as once:
            os.environ.pop("TEXTFOLD_NO_MODELS", None)   # (the suite runs with it; the model here is a stand-in)
            rec, cached = llm.call("Fold this.", {}, "test/model", Path(tmp))
            self.assertFalse(cached)
            self.assertTrue(Path(rec["file"]).exists())   # (the reply is kept, and the caller can name it)
            again, cached = llm.call("Fold this.", {}, "test/model", Path(tmp))
            self.assertTrue(cached)   # (the kept reply is read back, and it names its file too)
            self.assertEqual(again["file"], rec["file"])
            llm.forget(rec)
            self.assertFalse(Path(rec["file"]).exists())
            _, cached = llm.call("Fold this.", {}, "test/model", Path(tmp))
            self.assertFalse(cached)   # (the dropped reply was not read back)
            self.assertEqual(once.call_count, 2)

    def test_a_reply_held_open_is_left(self):
        if os.name != "nt":
            self.skipTest("on Windows an open file cannot be deleted")
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "held.json"
            f.write_text("{}")
            with open(f, "rb"):
                llm.forget({"file": str(f)})   # (the delete is skipped, not raised)
            self.assertTrue(f.exists())


if __name__ == "__main__":
    unittest.main()
