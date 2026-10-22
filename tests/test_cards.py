"""The reading card (cards.py): its storage contract, evidence validation, candidate adoption, stale detection,
broken links and Markdown export. The document and the model are stand-ins here: nothing reads a paper or calls out.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from textfold import cards, llm, store

PAGE = """<article class="ltx_document">
<p class="ltx_p">The abstract states the problem. We propose method A.</p>
<section class="ltx_section" id="S1"><h2 class="ltx_title"><span class="ltx_tag">1</span> Introduction</h2>
<p class="ltx_p">Prior work is limited. We propose method A.</p></section>
<section class="ltx_section" id="S2"><h2 class="ltx_title"><span class="ltx_tag">2</span> Method</h2>
<p class="ltx_p">Method A takes input X and outputs Y.</p></section>
<section class="ltx_section" id="S3"><h2 class="ltx_title"><span class="ltx_tag">3</span> Experiments</h2>
<p class="ltx_p">We use dataset D with 1000 samples.</p>
<p class="ltx_p">Our method reaches 92.5% accuracy, against 88.1% for baseline B.</p></section>
<section class="ltx_section" id="S4"><h2 class="ltx_title"><span class="ltx_tag">4</span> Limitations</h2>
<p class="ltx_p">The method applies only when condition Z holds.</p></section>
</article>"""
META = {"id": "md-card", "title": "A Card Paper", "authors": ["Ada Lovelace"], "date": "2025-05-01",
        "doi": "10.1/example", "version": "v1", "abs_url": "https://example.org/paper", "html_url": ""}
PID = "md-card"


def reply(items):
    return {"out": {"items": items}}, None


class CardTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.old = store.DATA
        store.DATA = Path(tmp.name)
        self.addCleanup(setattr, store, "DATA", self.old)
        cards._DOCS.clear()
        cards._PAGES.clear()
        cards._MODEL.update(at=0.0, value=None)
        self.addCleanup(cards._DOCS.clear)
        self.addCleanup(cards._PAGES.clear)
        d = store.pdir(PID)
        d.mkdir(parents=True)
        (d / "source.html").write_text(PAGE, encoding="utf-8")
        (d / "meta.json").write_text(json.dumps(META), encoding="utf-8")
        p = mock.patch.object(cards, "_model_info", return_value=None)
        p.start()
        self.addCleanup(p.stop)
        self.doc = cards._doc(PID)
        self.units = list(self.doc["units"])

    def item(self, text="A point.", state="found", origin="user", evidence=None, verified=False, **kw):
        return {"id": "c-" + text[:6].replace(" ", "") + "0", "text": text, "state": state, "origin": origin,
                "edited": False, "verified": verified, "issue": "", "evidence": evidence or [], **kw}

    def save(self, sections, rev=None, lang="en"):
        card = cards.read(PID) or cards.create(PID, lang)
        return cards.save(PID, {"rev": card.get("rev", 0) if rev is None else rev, "lang": lang,
                                "sections": {k: list(v) for k, v in sections.items()}})

    def evidence(self, uid=None, quote=None):
        return cards._evidence_for(PID, self.doc, uid or self.units[0], quote=quote)

    # ── storage ──────────────────────────────────────────────────────────
    def test_create_save_reload_and_language_kept(self):
        card = cards.create(PID, "en")
        created = card["created"]
        self.assertEqual(card["lang"], "en")
        item = self.item("研究问题", evidence=[self.evidence()])
        card = cards.save(PID, {"rev": card["rev"], "lang": "zh", "sections": {**card["sections"], "problem": [item]}})
        self.assertEqual(card["lang"], "en")   # a saved card keeps its language
        self.assertEqual(card["created"], created)
        self.assertGreater(card["rev"], 1)
        again = cards.read(PID)
        self.assertEqual(again["sections"]["problem"][0]["text"], "研究问题")
        raw = (store.pdir(PID) / "card.json").read_bytes()
        raw.decode("ascii")   # ASCII-escaped, UTF-8 (and so safe on a GBK Windows)
        payload = cards.payload(PID)
        self.assertTrue(payload["exists"])
        self.assertEqual(payload["document"]["year"], "2025")
        self.assertEqual(payload["document"]["url"], "https://example.org/paper")

    def test_create_is_idempotent(self):
        first = cards.create(PID)
        second = cards.create(PID)
        self.assertEqual(first["rev"], second["rev"])
        self.assertEqual(first["created"], second["created"])

    def test_corrupt_card_is_copied_aside_not_overwritten(self):
        f = store.pdir(PID) / "card.json"
        f.write_text("{bad json", encoding="utf-8")
        self.assertIsNone(cards.read(PID))
        bad = list(store.pdir(PID).glob("card.bad-*.json"))
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0].read_text(encoding="utf-8"), "{bad json")
        cards.create(PID)
        self.assertTrue(f.exists())

    def test_a_malformed_candidate_is_ignored_not_fatal(self):
        card = cards.create(PID)
        card["candidate"] = {"sections": {"problem": [{"id": "c-x", "text": "x", "evidence": ["not a record"]}]}}
        (store.pdir(PID) / "card.json").write_text(json.dumps(card), encoding="utf-8")
        got = cards.read(PID)
        self.assertIsNotNone(got)
        self.assertIsNone(got["candidate"])

    def test_a_card_with_a_bad_source_or_evidence_is_copied_aside(self):
        for bad in ({"source": "v1"},
                    {"sections": {"problem": [{"id": "c-x", "text": "x", "evidence": [{"unit": ["x"]}]}]}},
                    {"sections": {"problem": [{"id": "c-x", "text": "x", "evidence": [{"quote": ["x"]}]}]}}):
            with self.subTest(bad=bad):
                shutil.rmtree(store.pdir(PID), ignore_errors=True)
                (store.pdir(PID) / "card.json").parent.mkdir(parents=True, exist_ok=True)
                (store.pdir(PID) / "card.json").write_text(json.dumps({"format": cards.FORMAT, **bad}), encoding="utf-8")
                self.assertIsNone(cards.read(PID))
                self.assertTrue(list(store.pdir(PID).glob("card.bad-*.json")))

    def test_a_card_with_bad_optional_scalars_still_loads(self):
        card = cards.create(PID)
        card["lang"] = ["x"]
        card["generation"] = "x"
        card["sections"]["problem"] = [self.item("A point")]
        card["sections"]["problem"][0]["gen"] = "x"
        card["candidate"] = {"lang": ["x"], "sections": {"problem": [self.item("A draft")]}}
        (store.pdir(PID) / "card.json").write_text(json.dumps(card), encoding="utf-8")
        got = cards.read(PID)
        self.assertEqual(got["lang"], "en")
        self.assertIsNone(got["generation"])
        self.assertIsNone(got["sections"]["problem"][0]["gen"])
        self.assertEqual(got["candidate"]["lang"], "en")
        self.assertTrue(cards.payload(PID)["exists"])
        self.assertIn("A point", cards.markdown(PID))

    def test_a_save_after_trash_does_not_recreate_the_document(self):
        card = cards.create(PID)
        store.trash(PID)
        with self.assertRaises(ValueError):
            cards.save(PID, {"rev": card["rev"], "sections": card["sections"]})
        self.assertFalse(store.pdir(PID).exists())

    def test_a_save_and_the_trash_do_not_cross(self):
        card = self.save({**cards.create(PID)["sections"], "problem": []})
        entered, release, errors = threading.Event(), threading.Event(), []
        original = cards._write

        def slow_write(*args, **kwargs):
            entered.set()
            release.wait(5)
            return original(*args, **kwargs)

        def save():
            try:
                cards.save(PID, {"rev": card["rev"], "sections": {**card["sections"], "problem": [self.item("Kept")]}})
            except Exception as e:   # the test reports what the save raised
                errors.append(e)

        thread = threading.Thread(target=save, daemon=True)
        with mock.patch.object(cards, "_write", side_effect=slow_write):
            thread.start()
            self.assertTrue(entered.wait(3))
            trash = threading.Thread(target=lambda: store.trash(PID), daemon=True)
            trash.start()
            time.sleep(0.15)
            self.assertTrue(trash.is_alive())   # (the save holds the document's lock)
            release.set()
            thread.join(5)
            trash.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertFalse(store.pdir(PID).exists())
        kept = next((store.DATA / "papers" / ".trash").iterdir()) / "card.json"
        self.assertEqual(json.loads(kept.read_text(encoding="utf-8"))["sections"]["problem"][0]["text"], "Kept")

    def test_trash_and_restore_keep_the_card(self):
        card = cards.create(PID)
        item = self.item("Kept", evidence=[self.evidence()])
        cards.save(PID, {"rev": card["rev"], "sections": {**card["sections"], "problem": [item]}})
        where = store.trash(PID)
        self.assertTrue((where / "card.json").exists())
        where.rename(store.pdir(PID))
        self.assertEqual(cards.read(PID)["sections"]["problem"][0]["text"], "Kept")

    # ── editing and verification ─────────────────────────────────────────
    def test_editing_a_found_item_returns_it_to_check(self):
        item = self.item("Original", origin="model", evidence=[self.evidence()], verified=True)
        card = self.save({**cards.create(PID)["sections"], "problem": [item]})
        changed = dict(card["sections"]["problem"][0], text="Rewritten")
        card = cards.save(PID, {"rev": card["rev"], "sections": card["sections"] | {"problem": [changed]}})
        kept = card["sections"]["problem"][0]
        self.assertEqual(kept["state"], "check")
        self.assertFalse(kept["verified"])
        self.assertTrue(kept["edited"])
        self.assertEqual(kept["origin"], "model")

    def test_editing_a_missing_item_keeps_its_state(self):
        item = self.item("Nothing stated", state="missing", origin="model", verified=True)
        card = self.save({**cards.create(PID)["sections"], "problem": [item]})
        changed = dict(card["sections"]["problem"][0], text="Nothing stated here")
        card = cards.save(PID, {"rev": card["rev"], "sections": card["sections"] | {"problem": [changed]}})
        kept = card["sections"]["problem"][0]
        self.assertEqual(kept["state"], "missing")
        self.assertFalse(kept["verified"])

    def test_an_unchanged_save_keeps_verified(self):
        item = self.item("Checked", evidence=[self.evidence()], verified=True)
        card = self.save({**cards.create(PID)["sections"], "problem": [item]})
        # the next save omits "verified": the server keeps the stored check
        bare = {k: v for k, v in card["sections"]["problem"][0].items() if k != "verified"}
        card = cards.save(PID, {"rev": card["rev"], "sections": card["sections"] | {"problem": [bare]}})
        self.assertTrue(card["sections"]["problem"][0]["verified"])

    def test_a_model_claim_without_locatable_evidence_is_check(self):
        item = self.item("A claim", origin="model", evidence=[])
        card = self.save({**cards.create(PID)["sections"], "problem": [item]})
        kept = card["sections"]["problem"][0]
        self.assertEqual(kept["state"], "check")
        self.assertEqual(kept["issue"], "no-evidence")
        bad = self.item("Another claim", origin="model", evidence=[{"unit": "missing.unit", "quote": "x"}])
        card = cards.save(PID, {"rev": card["rev"], "sections": card["sections"] | {"problem": [bad]}})
        kept = card["sections"]["problem"][0]
        self.assertEqual(kept["state"], "check")
        self.assertEqual(kept["issue"], "bad-citation")
        self.assertEqual(kept["evidence"][0]["quote"], "x")   # the excerpt is kept

    def test_model_evidence_quoting_other_words_is_check(self):
        ev = self.evidence()
        ev["quote"] = "words this paragraph does not contain"
        item = self.item("A claim", origin="model", evidence=[ev])
        card = self.save({**cards.create(PID)["sections"], "problem": [item]})
        kept = card["sections"]["problem"][0]
        self.assertEqual(kept["state"], "check")
        self.assertEqual(kept["issue"], "bad-citation")
        self.assertEqual(kept["evidence"][0]["quote"], "words this paragraph does not contain")

    def test_an_empty_new_point_is_not_saved(self):
        card = cards.create(PID)
        card = cards.save(PID, {"rev": card["rev"], "sections": {**card["sections"], "problem": [self.item("")]}})
        self.assertEqual(card["sections"]["problem"], [])

    def test_a_stale_revision_is_refused(self):
        card = self.save({**cards.create(PID)["sections"], "problem": [self.item("First")]})
        old = card["rev"] - 1
        with self.assertRaises(ValueError) as e:
            cards.save(PID, {"rev": old, "sections": card["sections"] | {"problem": [self.item("Second")]}})
        self.assertEqual(str(e.exception), "stale-card")
        self.assertEqual(cards.read(PID)["sections"]["problem"][0]["text"], "First")

    # ── evidence ─────────────────────────────────────────────────────────
    def test_forged_evidence_frame_is_recomputed(self):
        forged = {"doc": "elsewhere", "unit": self.units[1], "section": "S9", "quote": "Prior work is limited.",
                  "sents": [99], "page": 999, "block": "nope", "lang": "zh"}
        card = self.save({**cards.create(PID)["sections"], "method": [self.item("Point", evidence=[forged])]})
        ev = card["sections"]["method"][0]["evidence"][0]
        self.assertIsNone(ev["page"])   # not a PDF: no page is invented
        self.assertIsNone(ev["block"])
        self.assertEqual(ev["section"], self.doc["units"][self.units[1]]["chunk"])
        self.assertEqual(ev["sents"], [])
        self.assertEqual(ev["doc"], PID)

    def test_a_selection_becomes_the_authors_own_excerpt(self):
        card = cards.create(PID)
        item = self.item("A point", evidence=[])
        card = cards.save(PID, {"rev": card["rev"], "sections": card["sections"] | {"problem": [item]}})
        iid = card["sections"]["problem"][0]["id"]
        anchor = {"unit": self.units[1], "sents": [0], "lang": "zh", "quote": {"exact": "被翻译的句子"}}
        card = cards.add_evidence(PID, iid, [anchor])
        ev = card["sections"]["problem"][0]["evidence"][0]
        self.assertEqual(ev["quote"], "Prior work is limited.")
        self.assertEqual(ev["lang"], "en")
        self.assertEqual(card["sections"]["problem"][0]["state"], "check")
        with self.assertRaises(ValueError):
            cards.add_evidence(PID, iid, [{"unit": "nope", "sents": [0]}])
        with self.assertRaises(ValueError):
            cards.add_evidence(PID, iid, [{"unit": self.units[1], "sents": []}])

    def test_re_link_replaces_a_broken_target(self):
        broken = {"unit": "gone", "section": "S1", "quote": "old excerpt", "sents": [0], "lang": "en"}
        card = self.save({**cards.create(PID)["sections"], "problem": [self.item("Point", evidence=[broken])]})
        iid = card["sections"]["problem"][0]["id"]
        anchor = {"unit": self.units[2], "sents": [0], "quote": {"exact": "x"}}
        card = cards.add_evidence(PID, iid, [anchor], drop=0)
        evs = card["sections"]["problem"][0]["evidence"]
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["unit"], self.units[2])

    def test_re_link_to_a_passage_already_linked_still_drops_the_broken_one(self):
        broken = {"unit": "gone", "section": "S1", "quote": "old excerpt", "sents": [0], "lang": "en"}
        valid = self.evidence(self.units[2])
        card = self.save({**cards.create(PID)["sections"], "problem": [self.item("Point", evidence=[broken, valid])]})
        iid = card["sections"]["problem"][0]["id"]
        anchor = {"unit": valid["unit"], "sents": valid["sents"]}
        card = cards.add_evidence(PID, iid, [anchor], drop=0)
        evs = card["sections"]["problem"][0]["evidence"]
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["unit"], valid["unit"])

    def test_page_comes_only_from_the_layout_map(self):
        with mock.patch.object(cards, "_page_of", return_value=7):
            ev = self.evidence()
        self.assertEqual(ev["page"], 7)
        with mock.patch.object(cards, "_page_of", return_value=None):
            ev = self.evidence()
        self.assertIsNone(ev["page"])

    # ── generation ───────────────────────────────────────────────────────
    def test_a_first_generation_becomes_the_card(self):
        out = [{"section": "problem", "text": "The paper solves a problem.", "state": "found", "evidence": [1]},
               {"section": "method", "text": "Method A maps X to Y.", "state": "found", "evidence": [3]},
               {"section": "results", "text": "Accuracy reaches 92.5%.", "state": "found", "evidence": [5]}]
        with mock.patch.object(llm, "call", return_value=reply(out)):
            card = cards.generate(PID, "en", {"id": "test/model"})
        self.assertTrue(card["generation"])
        self.assertFalse(card["generation"]["partial"])
        self.assertEqual(card["sections"]["problem"][0]["text"], "The paper solves a problem.")
        self.assertTrue(card["sections"]["problem"][0]["evidence"])
        self.assertIsNotNone(card["sections"]["problem"][0]["gen"])
        # setup had no item and no part failed: it says so rather than staying blank
        self.assertEqual(card["sections"]["setup"][0]["state"], "missing")

    def test_a_second_generation_is_a_candidate_and_keeps_the_card(self):
        base = cards.create(PID)
        item = self.item("Mine", evidence=[self.evidence()])
        cards.save(PID, {"rev": base["rev"], "sections": {**base["sections"], "problem": [item]}})
        out = [{"section": "problem", "text": "A model point.", "state": "found", "evidence": [1]}]
        with mock.patch.object(llm, "call", return_value=reply(out)):
            card = cards.generate(PID, "en", {"id": "test/model"})
        self.assertEqual(card["sections"]["problem"][0]["text"], "Mine")
        self.assertEqual(card["candidate"]["sections"]["problem"][0]["text"], "A model point.")

    def test_adopting_a_stale_candidate_rechecks_its_evidence(self):
        base = cards.create(PID)
        cards.save(PID, {"rev": base["rev"], "sections": {**base["sections"], "problem": [self.item("Mine")]}})
        out = [{"section": "problem", "text": "A model point.", "state": "found", "evidence": [1]}]
        with mock.patch.object(llm, "call", return_value=reply(out)):
            cards.generate(PID, "en", {"id": "test/model"})
        (store.pdir(PID) / "source.html").write_text(
            '<article class="ltx_document"><p class="ltx_p">Entirely different words now.</p></article>', encoding="utf-8")
        cards._DOCS.clear()
        card = cards.adopt(PID, "replace")
        kept = card["sections"]["problem"][0]
        self.assertEqual(kept["state"], "check")
        self.assertEqual(kept["issue"], "bad-citation")
        self.assertTrue(kept["evidence"])

    def test_a_generation_does_not_invalidate_a_save_in_progress(self):
        base = self.save({**cards.create(PID)["sections"], "problem": [self.item("Before")]})
        rev = base["rev"]
        out = [{"section": "problem", "text": "A model point.", "state": "found", "evidence": [1]}]
        with mock.patch.object(llm, "call", return_value=reply(out)):
            cand = cards.generate(PID, "en", {"id": "test/model"})
        self.assertIsNotNone(cand["candidate"])
        typed = dict(base["sections"]["problem"][0], text="Typed while the model read")
        card = cards.save(PID, {"rev": rev, "sections": {**base["sections"], "problem": [typed]}})
        self.assertEqual(card["sections"]["problem"][0]["text"], "Typed while the model read")
        self.assertIsNotNone(card["candidate"])   # the save keeps the draft that arrived meanwhile

    def test_a_failed_part_is_visible_and_not_written_as_missing(self):
        lock = {"first": True}

        def call(*a, **k):
            if lock["first"]:
                lock["first"] = False
                return reply([{"section": "problem", "text": "A point.", "state": "found", "evidence": [1]}])
            raise RuntimeError("provider failed with a fake key sk-not-a-real-key")
        with mock.patch.object(cards, "PART_CHARS", 10), mock.patch.object(llm, "call", side_effect=call):
            card = cards.generate(PID, "en", {"id": "test/model"})
        self.assertTrue(card["generation"]["partial"])
        self.assertGreaterEqual(card["generation"]["failed"], 1)
        self.assertEqual(card["generation"]["note"], "part-failed")   # no provider text in the card
        self.assertNotIn("sk-not-a-real-key", json.dumps(card))
        # the sections whose parts failed are empty, not "not clearly stated"
        self.assertTrue(any(not v for v in card["sections"].values()))

    def test_all_parts_failing_keeps_the_card(self):
        cards.create(PID)
        before = (store.pdir(PID) / "card.json").read_bytes()
        with mock.patch.object(llm, "call", side_effect=RuntimeError("no")):
            with self.assertRaises(RuntimeError):
                cards.generate(PID, "en", {"id": "test/model"})
        self.assertEqual((store.pdir(PID) / "card.json").read_bytes(), before)

    def test_an_empty_reply_is_a_failure(self):
        with mock.patch.object(llm, "call", return_value=reply([])):
            with self.assertRaises(ValueError) as e:
                cards.generate(PID, "en", {"id": "test/model"})
        self.assertEqual(str(e.exception), "no-items")
        self.assertFalse((store.pdir(PID) / "card.json").exists())

    def test_stop_before_a_part_leaves_no_card(self):
        stop = threading.Event()
        stop.set()
        with mock.patch.object(llm, "call", return_value=reply([])):
            with self.assertRaises(llm.Stopped):
                cards.generate(PID, "en", {"id": "test/model"}, stop=stop)
        self.assertFalse((store.pdir(PID) / "card.json").exists())

    def test_adopt_item_merge_and_replace(self):
        base = cards.create(PID)
        cards.save(PID, {"rev": base["rev"], "sections": {**base["sections"], "method": [self.item("Mine")]}})
        out = [{"section": "method", "text": "Model point.", "state": "found", "evidence": [3]},
               {"section": "results", "text": "Number.", "state": "found", "evidence": [5]}]
        with mock.patch.object(llm, "call", return_value=reply(out)):
            card = cards.generate(PID, "en", {"id": "test/model"})
        iid = card["candidate"]["sections"]["results"][0]["id"]
        card = cards.adopt_item(PID, iid)
        self.assertEqual(len(card["sections"]["results"]), 1)
        self.assertEqual(card["sections"]["method"][0]["text"], "Mine")
        card = cards.adopt(PID, "merge")
        self.assertEqual(len(card["sections"]["method"]), 2)
        self.assertIsNone(card["candidate"])
        with mock.patch.object(llm, "call", return_value=reply(out)):
            card = cards.generate(PID, "zh", {"id": "test/model"})
        with self.assertRaises(ValueError):
            cards.adopt_item(PID, card["candidate"]["sections"]["results"][0]["id"])
        card = cards.adopt(PID, "replace")
        self.assertEqual(card["lang"], "zh")
        self.assertIsNone(card["candidate"])

    def test_discard(self):
        cards.create(PID)
        with mock.patch.object(llm, "call", return_value=reply([{"section": "problem", "text": "P.", "state": "found", "evidence": [1]}])):
            cards.generate(PID, "en", {"id": "test/model"})
        self.assertIsNotNone(cards.read(PID)["candidate"])
        self.assertIsNone(cards.discard(PID)["candidate"])

    # ── staleness and broken evidence ────────────────────────────────────
    def test_layers_do_not_stale_a_card_but_text_and_version_do(self):
        card = cards.create(PID)
        cards.save(PID, {"rev": card["rev"], "sections": {**card["sections"], "problem": [self.item("P", evidence=[self.evidence()])]}})
        store.write(PID, "en", {"version": "v1", "units": {}, "chunks": {}, "edges": []})
        store.write(PID, "tr-zh", {"version": "v1", "base": "v1", "units": {}, "chunks": {}})
        self.assertFalse(cards.payload(PID)["stale"])
        meta = dict(META, version="v2")
        (store.pdir(PID) / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        cards._DOCS.clear()
        p = cards.payload(PID)
        self.assertTrue(p["stale"])
        self.assertTrue(p["sections"]["problem"][0]["recheck"])
        cards.review(PID)
        self.assertFalse(cards.payload(PID)["stale"])
        (store.pdir(PID) / "source.html").write_text(PAGE.replace("92.5%", "93.0%"), encoding="utf-8")
        cards._DOCS.clear()
        self.assertTrue(cards.payload(PID)["stale"])

    def test_evidence_that_no_longer_resolves_is_kept(self):
        gone = {"unit": "S9.p1", "section": "S9", "quote": "The saved excerpt.", "sents": [0], "lang": "en"}
        card = self.save({**cards.create(PID)["sections"], "results": [self.item("Result", evidence=[gone])]})
        p = cards.payload(PID)
        ev = p["sections"]["results"][0]["evidence"][0]
        self.assertTrue(ev["broken"])
        self.assertEqual(ev["quote"], "The saved excerpt.")
        md = cards.markdown(PID, "http://localhost:3017")
        self.assertIn("The saved excerpt.", md)
        self.assertIn("target no longer found", md)
        self.assertNotIn("#u=S9.p1", md)

    # ── Markdown ─────────────────────────────────────────────────────────
    def test_markdown_has_sections_states_evidence_and_links(self):
        item = self.item("A checked point.", origin="model", evidence=[self.evidence()], verified=True)
        missing = self.item("Not stated", state="missing", origin="model")
        card = self.save({**cards.create(PID)["sections"], "problem": [item], "setup": [missing]})
        with mock.patch.object(llm, "call", side_effect=AssertionError("export must not call a model")):
            md = cards.markdown(PID, "http://localhost:3017")
        self.assertIn("A Card Paper", md)
        self.assertIn("研究阅读卡", md) if card["lang"] == "zh" else self.assertIn("Reading card", md)
        self.assertIn("A checked point.", md)
        self.assertIn("Not stated", md)
        self.assertIn("Not clearly stated", md)
        self.assertIn("✓", md)
        self.assertIn("http://localhost:3017/p/md-card", md)
        self.assertIn("#u=", md)
        self.assertIn("TextFold", md)
        self.assertNotIn("llm", md)

    def test_markdown_uses_the_card_language(self):
        card = cards.create(PID, "zh")
        item = self.item("中文要点", evidence=[self.evidence()])
        cards.save(PID, {"rev": card["rev"], "sections": {**card["sections"], "problem": [item]}})
        md = cards.markdown(PID)
        self.assertIn("研究阅读卡", md)
        self.assertIn("研究问题与贡献", md)
        self.assertIn("中文要点", md)

    def test_export_name_is_safe(self):
        cards.create(PID)
        name = cards.export_name(PID)
        self.assertTrue(name.endswith("reading-card.md"))
        self.assertNotIn("/", name)

    # ── pages and static files ───────────────────────────────────────────
    def test_static_pages_do_not_load_the_card(self):
        from textfold import build
        doc = store.assemble(PID)
        static = build.page(doc, app=False)
        self.assertNotIn("/static/card.js", static)
        self.assertNotIn("/static/card.css", static)
        app = build.page(store.assemble(PID), app=True)
        self.assertIn("/static/card.js", app)
        self.assertIn("/static/card.css", app)

    def test_a_document_with_no_headings_still_has_a_part(self):
        page = '<article class="ltx_document"><p class="ltx_p">Only words, no heading.</p></article>'
        (store.pdir(PID) / "source.html").write_text(page, encoding="utf-8")
        cards._DOCS.clear()
        doc = cards._doc(PID)
        parts = cards._parts(doc)
        self.assertTrue(parts)
        self.assertIn("Only words, no heading.", cards._part_prompt(doc, parts[0], "en"))


class CardJobs(unittest.TestCase):
    def test_a_draft_in_another_language_is_another_job(self):
        import queue
        from textfold import server
        jobs = server.Jobs.__new__(server.Jobs)
        jobs.items, jobs.q, jobs.eq, jobs.stops, jobs.pending = {}, queue.Queue(), queue.Queue(), {}, {}
        a = jobs.card(PID, "en")
        b = jobs.card(PID, "zh")
        c = jobs.card(PID, "en")
        self.assertIsNot(a, b)
        self.assertIs(a, c)
        self.assertEqual((a["kind"], b["kind"]), ("card", "card"))


class ConvertedPdf(unittest.TestCase):
    """A PDF converted again is a new text: the levels go, but the reader's card and notes stay, and the card's own
    fingerprint marks it for review. This is the keep list in pdfdoc.store_pdf, exercised without an engine."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.old = store.DATA
        store.DATA = Path(tmp.name)
        self.addCleanup(setattr, store, "DATA", self.old)
        self.pid = "pdf-0123456789abcdef"
        d = store.pdir(self.pid)
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"id": self.pid, "title": "Old", "version": ""}), encoding="utf-8")
        (d / "source.html").write_text('<article class="ltx_document"><p class="ltx_p">Old text.</p></article>', encoding="utf-8")
        (d / "notes.json").write_text('{"notes": []}', encoding="utf-8")
        (d / "card.json").write_text(json.dumps({"format": cards.FORMAT, "sections": {"problem": []}}), encoding="utf-8")

    def test_a_replaced_conversion_keeps_the_card(self):
        from textfold import engine, local, pdfdoc
        d = store.pdir(self.pid)

        def store_doc(pid, html, meta, raw_name, raw, resolver, sizes=False):
            shutil.rmtree(d)   # (local.store_doc writes the document whole)
            d.mkdir(parents=True)
            (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            (d / "source.html").write_text(html, encoding="utf-8")
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        with mock.patch.object(pdfdoc, "to_markdown", return_value=("New text.", ["A"], "")), \
             mock.patch.object(pdfdoc, "cut_figures", return_value={}), \
             mock.patch.object(pdfdoc.markdown, "to_html", return_value=("<article></article>", [])), \
             mock.patch.object(pdfdoc, "layout_of", return_value=[]), \
             mock.patch.object(pdfdoc, "source_of", return_value=None), \
             mock.patch.object(local, "store_doc", side_effect=store_doc), \
             mock.patch.object(engine, "kind_of", return_value="pdf"), \
             mock.patch.object(engine, "tier_for", return_value="fast"):
            pdfdoc.store_pdf(self.pid, Path(tempfile.mkdtemp()), {}, "x.pdf", "fast", replace=True)
        self.assertTrue((d / "card.json").exists())
        self.assertTrue((d / "notes.json").exists())
        self.assertEqual(json.loads((d / "card.json").read_text(encoding="utf-8"))["format"], cards.FORMAT)

    def test_a_save_during_a_replaced_conversion_is_not_overwritten(self):
        from textfold import engine, local, pdfdoc
        d = store.pdir(self.pid)
        base = cards.read(self.pid)
        entered, release, errors = threading.Event(), threading.Event(), []

        def store_doc(pid, html, meta, raw_name, raw, resolver, sizes=False):
            entered.set()
            release.wait(5)
            shutil.rmtree(d)   # (local.store_doc writes the document whole)
            d.mkdir(parents=True)
            (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            (d / "source.html").write_text('<article class="ltx_document"><p class="ltx_p">New text.</p></article>', encoding="utf-8")

        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        def convert():
            try:
                with mock.patch.object(pdfdoc, "to_markdown", return_value=("New text.", ["A"], "")), \
                     mock.patch.object(pdfdoc, "cut_figures", return_value={}), \
                     mock.patch.object(pdfdoc.markdown, "to_html", return_value=("<article></article>", [])), \
                     mock.patch.object(pdfdoc, "layout_of", return_value=[]), \
                     mock.patch.object(pdfdoc, "source_of", return_value=None), \
                     mock.patch.object(engine, "kind_of", return_value="pdf"), \
                     mock.patch.object(engine, "tier_for", return_value="fast"):
                    pdfdoc.store_pdf(self.pid, Path(folder), {}, "x.pdf", "fast", replace=True)
            except Exception as e:   # the test reports the thread's failure
                errors.append(e)

        def save():
            try:
                cards.save(self.pid, {"rev": base["rev"], "sections": {**base["sections"], "problem": [
                    {"id": "c-save001", "text": "Written during conversion", "state": "found", "origin": "user",
                     "edited": False, "verified": False, "issue": "", "evidence": []}]}})
            except Exception as e:
                errors.append(e)

        with mock.patch.object(local, "store_doc", side_effect=store_doc):
            thread = threading.Thread(target=convert, daemon=True)
            thread.start()
            self.assertTrue(entered.wait(3))
            saving = threading.Thread(target=save, daemon=True)
            saving.start()
            time.sleep(0.15)
            self.assertTrue(saving.is_alive())   # (the conversion holds the card's lock)
            release.set()
            thread.join(5)
            saving.join(5)
        self.assertFalse(thread.is_alive())
        self.assertFalse(saving.is_alive())
        self.assertEqual(errors, [])
        kept = cards.read(self.pid)["sections"]["problem"][0]
        self.assertEqual(kept["text"], "Written during conversion")


if __name__ == "__main__":
    unittest.main()
