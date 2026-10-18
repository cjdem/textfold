"""Generation no longer asks a model for argument links.

The links a layer already holds stay on disk and are still applied when a paper is opened; a
regeneration still replaces the English layer, as it always did, and the new layer has none.
The reader no longer draws them; `textfold get` still exports them. Author-written
cross-references come from the parser and are unaffected.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import build, fold, links, models, pipeline, store

PAGE = ('<article class="ltx_document"><p class="ltx_p">First paragraph here.</p>'
        '<p class="ltx_p">Second paragraph here.</p></article>')
CFG = {"kind": "agent", "runtime": "claude-code", "model": "haiku", "id": "test/model"}


class ArgumentLinks(unittest.TestCase):
    def setUp(self):
        self.old = store.DATA
        store.DATA = Path(tempfile.mkdtemp())
        self.pid = "md-links"
        d = store.pdir(self.pid)
        d.mkdir(parents=True)
        (d / "source.html").write_text(PAGE, encoding="utf-8")
        (d / "meta.json").write_text(json.dumps({"id": self.pid}), encoding="utf-8")

    def tearDown(self):
        store.DATA = self.old

    def generate(self, force=False, progress=None):
        with mock.patch.object(pipeline, "task", side_effect=lambda c, n: c), \
             mock.patch.object(pipeline.ladder, "build"), \
             mock.patch.object(pipeline.translate, "build"), \
             mock.patch.object(links, "build") as built:
            pipeline.generate(self.pid, "en", CFG, force=force, also_zh=False,
                              progress=progress or (lambda *a: None))
        return built

    def edge(self, f, t, rel="supports"):
        return {"f": f, "t": t, "rel": rel, "tk": "unit"}

    def test_links_is_no_longer_a_task(self):
        self.assertNotIn("links", models.TASKS)
        self.assertNotIn("links", models.DEFAULT_THINKING)
        self.assertEqual(set(models.TASKS), set(models.DEFAULT_THINKING))

    def test_generation_does_not_call_the_link_model(self):
        stages = []
        built = self.generate(progress=lambda stage, done, total: stages.append(stage))
        self.assertFalse(built.called)
        self.assertNotIn("links", stages)
        self.assertEqual(stages[-1], "done")
        self.assertEqual(store.read(self.pid, "en")["edges"], [])   # (cross-references come from the parse, not the layer)

    def test_a_regeneration_replaces_the_layer_and_its_links(self):
        self.generate()
        ids = sorted(store.parsed(self.pid)["units"])
        self.assertGreaterEqual(len(ids), 2)
        en = store.read(self.pid, "en")
        en["edges"] = [self.edge(ids[0], ids[1])]
        store.write(self.pid, "en", en)

        self.generate(force=True)

        self.assertEqual(store.read(self.pid, "en")["edges"], [])
        self.assertNotIn("unit", {e.get("tk") for e in store.assemble(self.pid)["edges"]})

    def test_an_old_link_is_applied_when_the_paper_opens(self):
        self.generate()
        ids = sorted(store.parsed(self.pid)["units"])
        en = store.read(self.pid, "en")
        en["units"] = {u: ["kept"] for u in ids}
        en["edges"] = [self.edge(ids[0], ids[1])]
        store.write(self.pid, "en", en)

        doc = store.assemble(self.pid)

        self.assertIn(self.edge(ids[0], ids[1]), doc["edges"])

    def test_the_page_carries_no_edges_but_get_still_exports_them(self):
        self.generate()
        ids = sorted(store.parsed(self.pid)["units"])
        en = store.read(self.pid, "en")
        en["edges"] = [self.edge(ids[0], ids[1])]
        store.write(self.pid, "en", en)

        doc = store.assemble(self.pid)
        self.assertIn(self.edge(ids[0], ids[1]), doc["edges"])   # stored data still assembles

        data = json.loads(build.payload(doc, False))
        self.assertNotIn("edges", data)                          # ... but the reader is not sent it

        self.assertEqual(fold.document(self.pid)["links"],
                         [{"from": ids[0], "to": ids[1], "rel": "supports"}])


if __name__ == "__main__":
    unittest.main()
