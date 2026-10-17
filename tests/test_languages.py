"""The reader offers two languages, English and Simplified Chinese. A translation of any other language — stored before
the list was trimmed — stays on disk but is neither listed nor read (store.languages filters by langs.LANGS), and the
command line refuses it rather than failing deep in a translation.

Run from the repo root:
    python -m unittest discover tests
"""
import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import __main__ as cli
from textfold import langs, notes, pipeline, store


class Offered(unittest.TestCase):
    def test_the_reader_offers_english_and_simplified_chinese(self):
        self.assertEqual(sorted(langs.LANGS), ["en", "zh"])
        self.assertEqual(langs.LANGS["zh"][1], "简体中文")

    def test_a_translation_of_a_removed_language_is_not_offered(self):
        old = store.DATA
        try:
            store.DATA = Path(tempfile.mkdtemp())
            for lang in ("zh", "ja", "de"):
                store.write("web-x", f"tr-{lang}", {"version": "v", "base": "b"})
            self.assertEqual(store.languages("web-x"), ["zh"])
        finally:
            store.DATA = old

    def test_the_command_line_refuses_a_removed_language(self):
        a = argparse.Namespace(ref="2512.24601", lang="ja", no_generate=True, json=False, level="full", section=None)
        with mock.patch.object(cli, "_say") as say:
            self.assertEqual(cli.get(a), 2)
        self.assertIn("unknown language", say.call_args.args[0])

    def test_the_pipeline_refuses_a_removed_language(self):
        # (the guard behind every caller: a launch, a job, a conversion that a stored sentence still names)
        with self.assertRaisesRegex(RuntimeError, "unknown language ja"):
            pipeline.generate("2512.24601", "ja", None)


class Stored(unittest.TestCase):
    def setUp(self):
        self.old = store.DATA
        store.DATA = Path(tempfile.mkdtemp())
        d = store.pdir("md-x")
        d.mkdir(parents=True)
        (d / "source.html").write_text('<article class="ltx_document"><p class="ltx_p">Some text.</p></article>', encoding="utf-8")
        (d / "meta.json").write_text(json.dumps({"id": "md-x", "title": "A text"}), encoding="utf-8")

    def tearDown(self):
        store.DATA = self.old

    def test_a_note_written_in_a_removed_language_is_answered_in_english(self):
        text, _ = notes.prompt(store.parsed("md-x"), {"anchor": {"on": "paper", "lang": "ja"}}, "q", "ja")
        self.assertIn("in English", text)


if __name__ == "__main__":
    unittest.main()
