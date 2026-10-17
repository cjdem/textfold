"""An English document is made with its Simplified Chinese version by default: the app's generation calls
pipeline.generate(also_zh=True), and the translation is built at the end of that same generation — unless the
language asked for was zh, the Chinese layer already stands on the current English base, or there is no model. A
failure of the default does not fail the generation the reader asked for.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from textfold import pipeline, server, store

PAGE = '<article class="ltx_document"><p class="ltx_p">English words here.</p></article>'
DEFAULT = object()


class WantsZh(unittest.TestCase):
    def test_no_english_base_wants_none(self):
        self.assertFalse(pipeline._wants_zh(None, None))

    def test_an_english_base_without_a_chinese_layer_wants_one(self):
        self.assertTrue(pipeline._wants_zh({"version": "v1"}, None))

    def test_a_corrupt_chinese_layer_is_made_again(self):
        self.assertTrue(pipeline._wants_zh({"version": "v1"}, []))

    def test_a_chinese_layer_on_the_current_base_is_kept(self):
        self.assertFalse(pipeline._wants_zh({"version": "v1"}, {"base": "v1"}))

    def test_a_chinese_layer_on_an_older_base_is_made_again(self):
        self.assertTrue(pipeline._wants_zh({"version": "v2"}, {"base": "v1"}))


class Generation(unittest.TestCase):
    def setUp(self):
        self.old = store.DATA
        store.DATA = Path(tempfile.mkdtemp())
        self.pid = "md-en"
        d = store.pdir(self.pid)
        d.mkdir(parents=True)
        (d / "source.html").write_text(PAGE, encoding="utf-8")
        (d / "meta.json").write_text(json.dumps({"id": self.pid}), encoding="utf-8")
        self.cfg = {"kind": "agent", "runtime": "claude-code", "model": "haiku", "id": "test/model"}

    def tearDown(self):
        store.DATA = self.old

    def run_generate(self, lang="en", also_zh=True, translate=None, cfg=DEFAULT):
        calls, logs = [], []

        def fake_translate(doc, lg, spec, cache, **kw):
            calls.append(lg)
            return 0.0, 0

        with mock.patch.object(pipeline, "task", side_effect=lambda c, n: c), \
             mock.patch.object(pipeline.ladder, "build"), \
             mock.patch.object(pipeline.translate, "build", side_effect=translate or fake_translate):
            pipeline.generate(self.pid, lang, self.cfg if cfg is DEFAULT else cfg,
                              progress=lambda *a: None, log=logs.append, also_zh=also_zh)
        return calls, logs

    def test_an_english_generation_also_makes_chinese(self):
        self.assertEqual(self.run_generate()[0], ["zh"])

    def test_a_current_chinese_version_is_not_made_again(self):
        self.run_generate()
        self.assertEqual(self.run_generate()[0], [])

    def test_the_language_zh_makes_it_once_and_needs_no_default(self):
        self.assertEqual(self.run_generate(lang="zh")[0], ["zh"])

    def test_the_app_asks_and_the_command_line_does_not(self):
        self.assertEqual(self.run_generate(also_zh=False)[0], [])

    def test_a_run_with_no_model_makes_no_default(self):
        self.run_generate(also_zh=False)   # its English base exists
        self.assertEqual(self.run_generate(cfg=None)[0], [])

    def test_a_failure_of_the_default_leaves_the_generation_done(self):
        def fail(doc, lg, spec, cache, **kw):
            raise RuntimeError("boom")

        calls, logs = self.run_generate(translate=fail)
        self.assertIn("Simplified Chinese version could not be made", " ".join(logs))

    def test_an_unreadable_chinese_layer_is_made_again(self):
        layers = store.pdir(self.pid) / "layers"
        layers.mkdir(parents=True, exist_ok=True)
        (layers / "tr-zh.json").write_text("{bad json", encoding="utf-8")
        self.assertEqual(self.run_generate()[0], ["zh"])       # (the read does not fail the job)
        self.assertIsInstance(store.read(self.pid, "tr-zh"), dict)   # and the save replaced it

    def test_a_partial_chinese_pass_is_not_saved_as_current(self):
        def partial(doc, lg, spec, cache, **kw):
            return 0.0, 2   # (two parts failed: translate.build's report)

        calls, logs = self.run_generate(translate=partial)
        self.assertIn("incomplete", " ".join(logs))
        self.assertIsNone(store.read(self.pid, "tr-zh"))
        self.assertEqual(self.run_generate()[0], ["zh"])       # (so the next generation tries again)


class Wiring(unittest.TestCase):
    def setUp(self):
        self.old = store.DATA
        store.DATA = Path(tempfile.mkdtemp())
        d = store.pdir("md-en")
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"id": "md-en"}), encoding="utf-8")

    def tearDown(self):
        store.DATA = self.old

    def test_the_app_generates_the_chinese_default(self):
        spec = {"id": "test/model"}
        with mock.patch.object(server.models, "resolve", return_value=spec), \
             mock.patch.object(server.pipeline, "generate", return_value="md-en") as gen:
            server.Jobs().submit("md-en", "en", False)
            deadline = time.time() + 5
            while time.time() < deadline and not gen.called:
                time.sleep(0.01)
        self.assertTrue(gen.called)
        self.assertIs(gen.call_args.kwargs.get("also_zh"), True)


if __name__ == "__main__":
    unittest.main()
