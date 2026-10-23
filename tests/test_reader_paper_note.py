"""A note of the reader's own on the whole text: the notes menu writes one, it sits by the paper's title at every level
and opens beside the head, it has no quote and no Ask, and the notes list and export leave out the quote a passage note
has. There is no JS test runner here, so this holds what a Python test can see of it, and that the note's shape is one
the server keeps and reads back.

Run from the repo root:
    python -m unittest discover tests
"""
import ast
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import notes, store

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "textfold" / "web"


def text(name):
    return (WEB / name).read_text(encoding="utf-8")


class PaperNote(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_the_notes_menu_writes_one_and_the_margins_show_it(self):
        reader = text("reader.js")
        self.assertIn("if (key === '¶') return { el: paperHead, after: null };", reader)   # (by the title)
        self.assertIn("if (uid === '¶') { renderNoteCards(uid); continue; }", reader)
        self.assertIn("asks = key === '¶' ? [] : list.filter((n) => n.kind === 'ask')", reader)   # (chats stay in the chat)
        self.assertIn("if (whole(n.anchor) && n.kind === 'ask') { openChat(n, back); return; }", reader)
        self.assertIn("${!ask && !whole(a) ? `<button type=\"button\" data-act=\"ask\">", reader)   # (no Ask on the whole text)
        self.assertIn("if (whole(a) && n.kind === 'ask') { openChat(n); return; }", reader)
        self.assertIn("if (whole(a)) { if (popNote) closeNote(); scrollTo({ top: 0, behavior: 'smooth' }); afterZoom(() => openNote(n), 260); return; }", reader)
        new = re.search(r"function newPaperNote\(\) \{(.*?)\n  \}", reader, re.S).group(1)
        self.assertIn("const n = { id: noteId(), kind: 'note', text: '', thread: [],", new)
        self.assertIn("anchor: { unit: null, section: null, on: 'paper', lang, level, tokens: null, sents: null, quote: { exact: '' } } };", new)
        self.assertIn("afterZoom(() => openNote(n, true), 260);", new)   # (a draft: kept once it has words)
        self.assertIn("if (popDraft) {   // (words typed and let go before the debounce are kept; no words: not kept, even one the timer saved empty)", reader)
        self.assertIn("if (v.trim()) {", reader)
        self.assertIn("if (v !== (popNote.text || '')) saveNote({ ...popNote, text: v });", reader)
        self.assertIn("} else if (notes.some((x) => x.id === popNote.id)) deleteNote({ ...popNote, text: '' });", reader)
        self.assertIn('<button type="button" class="nl-new" data-x="paper" title="${esc(t.n_paper_note_tip)}">＋ ${esc(t.n_paper_note)}</button>', reader)
        self.assertIn("if (e.target.closest('[data-x=\"paper\"]')) { nmenu.hidden = true; newPaperNote(); }", reader)
        self.assertIn("${a.quote.exact ? `<span class=\"nl-q\">“${texLite(clipTex(a.quote.exact, 80))}”</span>` : ''}", reader)   # (a whole note has no quote)
        self.assertIn("} else if (!whole(n.anchor)) out.push(...", reader)   # (nor in the Markdown it writes)

    def test_the_head_holds_the_notes_at_every_level_and_the_margin_switch_hides_them(self):
        css = text("reader.css")
        self.assertIn(".paper-head { margin: 28px 0 34px; position: relative; }", css)
        self.assertIn(".paper-head > .lside { display: flex; }", css)   # (no level rule: every level)
        self.assertIn("html[data-hide~=\"notes\"] .paper-head > .lside { display: none; }", css)
        self.assertIn(".nl-new { margin-left: auto; font: 600 12px var(--sans);", css)

    def test_the_chat_never_takes_a_whole_note_for_a_conversation(self):
        reader = text("reader.js")
        self.assertIn("const latestChat = () => notes.filter((x) => x.kind === 'ask' && x.anchor && whole(x.anchor))", reader)
        self.assertIn("if (n && n.kind !== 'ask') n = null;", reader)   # (the chat's own door too)
        self.assertIn("const last = chatNote && notes.find((x) => x.id === chatNote.id);", reader)
        self.assertIn("openChat(last && last.kind === 'ask' ? last : latestChat());", reader)
        self.assertIn("async function stopAsk(n) {", reader)
        self.assertIn("try { await post('/api/ask/stop', { req: a.req }); }", reader)   # (the restore is the last write)
        self.assertIn("const stopping = new Set();", reader)   # (no second question while a stop is on its way)
        self.assertIn("if (!a || stopping.has(n.id)) return;", reader)
        self.assertIn("stopping.has(chatNote.id)", reader)
        self.assertIn("if (asking.has(n.id) || stopping.has(n.id)) return;", reader)   # (the passage's Ask too)
        self.assertIn("stopping.has(popNote.id)", reader)
        self.assertIn("stopping.has(n.id) || !confirm(T[ui].n_turn_del_q)", reader)
        self.assertIn("const n = chatNote && chatNote.kind === 'ask' ? chatNote : { id: noteId(), kind: 'ask', text: '', thread: [],", reader)
        self.assertIn("else if (before && before.kind === 'note') saveNote(before);", reader)
        self.assertIn("else if (before && before.text) saveNote({ ...before, kind: 'note', thread: [] });", reader)
        ask = re.search(r"async function askNote\(n, q\) \{(.*?)\n  \}", reader, re.S).group(1)
        self.assertLess(ask.index("before: notes.find"), ask.index("await saveNote(note)"))   # (the question's before is the note before it)
        stop = re.search(r"async function stopAsk\(n\) \{(.*?)\n  \}", reader, re.S).group(1)
        self.assertLess(stop.index("await post('/api/ask/stop'"), stop.index("saveNote(before)"))   # (the restore is last)

    def test_the_whole_note_stays_in_the_column_at_topic(self):
        css = text("reader.css")
        self.assertIn('.doc[data-level="0"] .paper-head > .lside { position: static; width: min(420px, 100%); max-width: 100%; margin-top: 6px; }', css)

    def test_the_words_are_in_both_languages(self):
        js = text("i18n.js")
        block = re.search(r"const NAME = \{(.*?)\n  \};", js, re.S).group(1)
        for code in ("en", "zh"):
            words = ast.literal_eval(re.search(rf"^\s*{code}: (\[.*?\]),?$", block, re.M).group(1))
            self.assertTrue(words[2].strip() and words[3].strip(), code)

    def test_the_server_keeps_a_note_on_the_whole_text(self):
        pid = "md-paper-note-0001"
        store.pdir(pid).mkdir(parents=True)
        (store.pdir(pid) / "meta.json").write_text('{"title": "A paper"}', encoding="utf-8")
        note = {"id": "n-paper01", "kind": "note", "text": "The whole of it, in a line.",
                "anchor": {"unit": None, "section": None, "on": "paper", "lang": "en", "level": 4,
                           "tokens": None, "sents": None, "quote": {"exact": ""}}}
        notes.put(pid, note)
        kept = notes.read(pid)["notes"]
        self.assertEqual([(n["id"], n["anchor"]["on"], n["text"]) for n in kept], [("n-paper01", "paper", "The whole of it, in a line.")])
        self.assertEqual(notes.kind(kept[0]), "note")
        doc = (ROOT / "docs" / "notes-format.md").read_text(encoding="utf-8")
        self.assertIn('So does a note of the reader\'s own on the whole paper, not on a passage (`kind:\n    "note"` with its `text`, written from the notes menu): it is shown by the paper\'s title, at every level.', doc)


if __name__ == "__main__":
    unittest.main()
