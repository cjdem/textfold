"""Two processes writing the reader's own files: the app and `textfold serve` may share one data folder, and each of a
note, a card and the Zotero index is read, changed and written back. A lock file in the data folder makes that one
round at a time across processes, so the later save reads what the earlier one wrote instead of overwriting it. In
these tests each interpreter reads its file and then waits; the test lets the writers go only after both have read (or,
on the locked code, after the one that could read went first) — so on the unlocked code both writes start from the same
old file, and on the locked code the second reads what the first wrote. A document being re-converted holds the notes'
and cards' locks for its whole document write: a save from another process has not landed while the conversion is
held, and lands in the rebuilt document once it is let go.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from textfold import cards, notes, store, zotero

ROOT = Path(__file__).resolve().parent.parent
START = """
go, tag = sys.argv[1], sys.argv[2]
base = os.path.dirname(go)
open(os.path.join(base, tag + ".ready"), "w").close()
while not os.path.exists(go):
    time.sleep(0.01)
def hold(name):
    open(os.path.join(base, tag + "." + name), "w").close()
    while not os.path.exists(go + ".write"):
        time.sleep(0.01)
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name)
        patch = mock.patch.object(store, "DATA", self.data)
        patch.start()
        self.addCleanup(patch.stop)

    def _paper(self, pid):
        d = store.pdir(pid)
        d.mkdir(parents=True)
        (d / "meta.json").write_text('{"title": "A paper"}', encoding="utf-8")
        (d / "source.html").write_text('<article class="ltx_document"><p class="ltx_p">One sentence here. '
                                       'Another follows it.</p></article>', encoding="utf-8")

    def _env(self):
        env = os.environ.copy()
        env.update({"TEXTFOLD_DATA": str(self.data), "TEXTFOLD_NO_MODELS": "1",
                    "PYTHONPATH": str(ROOT), "PYTHONIOENCODING": "utf-8"})
        return env

    def _wait(self, count, suffix, deadline):
        end = time.monotonic() + deadline
        while time.monotonic() < end and len(list(self.data.glob(f"*{suffix}"))) < count:
            time.sleep(0.02)

    def _two(self, script, tags):
        """Start both, let them read, and only then let them write. The locked code has one reader: the second waits at
        the lock, so the read signals do not all come, and the gate opens after a second."""
        go = self.data / "go"
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        procs = [subprocess.Popen([sys.executable, "-c", script, str(go), tag], env=self._env(),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                  creationflags=flags) for tag in tags]
        self._wait(len(tags), ".ready", 5.0)
        go.write_text("go", encoding="utf-8")
        self._wait(len(tags), ".read", 1.0)
        Path(f"{go}.write").write_text("go", encoding="utf-8")
        out = [p.communicate(timeout=60) for p in procs]
        return [(p.returncode, o, e) for p, (o, e) in zip(procs, out)]


class TwoWriters(Base):
    def test_two_processes_keep_both_notes(self):
        pid = "md-two-writers-0001"
        self._paper(pid)
        script = f'''
import os, sys, time
from textfold import notes
{START}
orig = notes.read
def read(pid):
    data = orig(pid)
    hold("read")
    return data
notes.read = read
notes.put("{pid}", {{"id": "n-" + tag, "kind": "note", "text": tag,
                    "anchor": {{"unit": None, "on": "paper", "quote": {{"exact": ""}}}}}})
'''
        results = self._two(script, ["a", "b"])
        for code, _, err in results:
            self.assertEqual(code, 0, err)
        self.assertEqual({n["id"] for n in notes.read(pid)["notes"]}, {"n-a", "n-b"})
        self.assertTrue((self.data / "notes.lock").exists())
        self.assertFalse((store.pdir(pid) / "notes.json.lock").exists())   # (a lock inside papers/ would block the trash move)

    def test_two_processes_do_not_both_save_one_card_revision(self):
        pid = "md-two-writers-0002"
        self._paper(pid)
        rev = cards.create(pid)["rev"]
        script = f'''
import os, sys, time
from textfold import cards
{START}
orig = cards.read
def read(pid):
    card = orig(pid)
    hold("read")
    return card
cards.read = read
try:
    cards.save("{pid}", {{"sections": {{"problem": [{{"text": tag}}]}}, "rev": {rev}, "lang": "en"}})
except ValueError as e:
    print(e)
    sys.exit(1)
'''
        results = self._two(script, ["a", "b"])
        self.assertEqual(sorted(code for code, _, _ in results), [0, 1], results)   # (the second is told the card moved on)
        self.assertIn("stale-card", [o.strip() for _, o, _ in results])
        card = cards.read(pid)
        self.assertEqual(card["rev"], rev + 1)
        self.assertEqual(len(card["sections"]["problem"]), 1)   # (one revision, one save: nothing silently overwritten)

    def test_two_processes_keep_both_zotero_links(self):
        self.data.mkdir(parents=True, exist_ok=True)
        script = f'''
import os, sys, time
from textfold import zotero
{START}
orig = zotero.store.read_text
def read_text(f):
    try:
        text = orig(f)
    finally:
        hold("read")   # (the first read of a missing index raises: it still counts as this process's read)
    return text
zotero.store.read_text = read_text
zotero.link("users/0", tag, "md-zot-item-" + tag, "T" + tag)
'''
        results = self._two(script, ["a", "b"])
        for code, _, err in results:
            self.assertEqual(code, 0, err)
        self.assertEqual(set(zotero.links()), {"users/0/a", "users/0/b"})
        self.assertTrue((self.data / "zotero.lock").exists())


class Conversion(Base):
    """A re-converted PDF snapshots the reader's notes and card, rebuilds the folder, and copies them back. The notes'
    and card's locks are held for that whole window: the saving process reaches its save, and the save has not landed
    while the conversion is held; it lands in the rebuilt document once the conversion is let go."""

    PID = "pdf-0123456789abcdef"

    def _pdf(self):
        d = store.pdir(self.PID)
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"id": self.PID, "title": "Old", "version": ""}), encoding="utf-8")
        (d / "source.html").write_text('<article class="ltx_document"><p class="ltx_p">Old text.</p></article>',
                                       encoding="utf-8")
        (d / "notes.json").write_text('{"notes": []}', encoding="utf-8")
        (d / "card.json").write_text(json.dumps({"format": cards.FORMAT, "sections": {"problem": []}}), encoding="utf-8")

    def _held_conversion(self):
        """Start store_pdf with `local.store_doc` held open at `entered`; returns the thread, the release and errors."""
        from textfold import engine, local, pdfdoc
        d = store.pdir(self.PID)
        entered, release, errors = threading.Event(), threading.Event(), []

        def store_doc(pid, html, meta, raw_name, raw, resolver, sizes=False):
            entered.set()
            release.wait(10)
            shutil.rmtree(d)   # (local.store_doc writes the document whole)
            d.mkdir(parents=True)
            (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            (d / "source.html").write_text('<article class="ltx_document"><p class="ltx_p">New text.</p></article>',
                                           encoding="utf-8")

        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        def convert():
            try:
                with mock.patch.object(pdfdoc, "to_markdown", return_value=("New text.", ["A"], "")), \
                     mock.patch.object(pdfdoc, "cut_figures", return_value={}), \
                     mock.patch.object(pdfdoc.markdown, "to_html", return_value=("<article></article>", [])), \
                     mock.patch.object(pdfdoc, "layout_of", return_value=[]), \
                     mock.patch.object(pdfdoc, "source_of", return_value=None), \
                     mock.patch.object(local, "store_doc", side_effect=store_doc), \
                     mock.patch.object(engine, "kind_of", return_value="pdf"), \
                     mock.patch.object(engine, "tier_for", return_value="fast"):
                    pdfdoc.store_pdf(self.PID, Path(folder), {}, "x.pdf", "fast", replace=True)
            except Exception as e:   # the test reports the thread's failure
                errors.append(e)

        thread = threading.Thread(target=convert)
        thread.start()
        self.assertTrue(entered.wait(10))
        return thread, release, errors

    def _convert(self, child_script, landed_now):
        """Start the saving child while the conversion is held, check what landed, then let the conversion finish.
        `landed_now()` is read before the conversion is released: an unlocked save has landed by then, a locked one
        has not."""
        thread, release, errors = self._held_conversion()
        ready = self.data / "child.ready"
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        child = subprocess.Popen([sys.executable, "-c", child_script, str(ready)], env=self._env(),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                 creationflags=flags)
        end = time.monotonic() + 5
        while time.monotonic() < end and not ready.exists():
            time.sleep(0.02)
        done = Path(f"{ready}.done")
        end = time.monotonic() + 1.5   # (an unlocked save finishes here; a locked one cannot)
        while time.monotonic() < end and not done.exists():
            time.sleep(0.02)
        finished = done.exists()
        landed = landed_now()
        release.set()
        thread.join(20)
        out, err = child.communicate(timeout=60)
        self.assertFalse(errors, errors)
        return finished, landed, child.returncode, out, err

    def test_a_reconversion_holds_the_notes_and_cards_locks(self):
        self._pdf()
        thread, release, errors = self._held_conversion()
        try:
            for name in ("notes", "cards"):   # (a second handle cannot take the byte the conversion holds)
                with self.assertRaises(OSError, msg=name):
                    with store.file_lock(name, wait=0.05):
                        pass
        finally:
            release.set()
            thread.join(20)
        self.assertFalse(errors, errors)
        for name in ("notes", "cards"):   # (free again once the conversion is done)
            with store.file_lock(name, wait=0.05):
                pass

    def test_a_note_saved_during_a_reconversion_is_kept(self):
        self._pdf()
        script = f'''
import os, sys
from textfold import notes
ready = sys.argv[1]
open(ready, "w").close()
notes.put("{self.PID}", {{"id": "n-kept", "kind": "note", "text": "Saved during conversion",
                         "anchor": {{"unit": None, "on": "paper", "quote": {{"exact": ""}}}}}})
open(ready + ".done", "w").close()
'''
        finished, landed, code, out, err = self._convert(
            script, lambda: "n-kept" in {n["id"] for n in notes.read(self.PID)["notes"]})
        self.assertFalse(finished, "the save landed while the conversion held the folder")
        self.assertFalse(landed, "the save landed in the old folder while the conversion held it")
        self.assertEqual(code, 0, err)
        self.assertIn("n-kept", {n["id"] for n in notes.read(self.PID)["notes"]})

    def test_a_card_saved_during_a_reconversion_is_kept(self):
        self._pdf()
        script = f'''
import os, sys
from textfold import cards
ready = sys.argv[1]
open(ready, "w").close()
cards.save("{self.PID}", {{"sections": {{"problem": [{{"text": "Saved during conversion"}}]}}, "rev": 0, "lang": "en"}})
open(ready + ".done", "w").close()
'''
        finished, landed, code, out, err = self._convert(
            script, lambda: [it["text"] for it in cards.read(self.PID)["sections"]["problem"]])
        self.assertFalse(finished, "the save landed while the conversion held the folder")
        self.assertEqual(landed, [], "the save landed in the old card while the conversion held it")
        self.assertEqual(code, 0, err)
        self.assertEqual([it["text"] for it in cards.read(self.PID)["sections"]["problem"]], ["Saved during conversion"])


if __name__ == "__main__":
    unittest.main()
