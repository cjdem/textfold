"""The Topic mind map is an opaque overlay: the whole-paper note drawn by the page's title sits under it. The map now
draws the reader's own notes on the whole paper in its left column, above the title and the outline, and a click opens
the note beside that card (the popover's card lookup prefers the map's card while the map is shown). A note saved from
there repaints the map, and a note changed while the map is hidden makes it build afresh when it opens. There is no JS
test runner here, so this holds what a Python test can see of it.

Run from the repo root:
    python -m unittest discover tests
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "textfold" / "web"


def text(name):
    return (WEB / name).read_text(encoding="utf-8")


class MapNote(unittest.TestCase):
    def test_the_map_draws_the_readers_whole_paper_notes_above_the_outline(self):
        reader = text("reader.js")
        self.assertIn("function mapNotes() {", reader)
        self.assertIn("const list = mineOn('¶');", reader)   # (only the reader's own notes; chats stay in the chat)
        self.assertIn("list.sort((a, b) => (a.created || a.updated || '').localeCompare(b.created || b.updated || ''));",
                      reader)   # (a save appends the note; the map keeps its card in place)
        self.assertIn('`<div class="mm-notes-h">${esc(T[ui].n_whole)}</div>`', reader)
        self.assertIn("for (const n of list) box.append(noteCard(n));", reader)
        self.assertIn("if ((document.documentElement.dataset.hide || '').split(' ').includes('notes')) return null;",
                      reader)   # (hidden with the margins: no block and no gap above the title)
        self.assertIn("const notes = mapNotes();", reader)
        self.assertIn("startY = PAD + notes.offsetHeight + 20;", reader)   # (the title and outline begin under it)
        self.assertIn("right = PAD + notes.offsetWidth;", reader)   # (and the canvas is wide enough for it)
        self.assertIn("mapEl.style.setProperty('--mm-left', `${left}px`);", reader)   # (the note's width follows the sidebar)
        self.assertIn("})(mapRoot, PAD, startY);", reader)

    def test_a_map_card_opens_the_note_beside_it(self):
        reader = text("reader.js")
        click = reader[reader.index("mapCanvas.addEventListener('click'"):]
        self.assertIn("const card = e.target.closest('.mm-notes .ncard');", click)
        self.assertLess(click.index("const card = e.target.closest('.mm-notes .ncard');"),
                        click.index("const leaf = e.target.closest('.mm-leaf')"))
        self.assertIn("const n = notes.find((x) => x.id === card.dataset.note);", click)
        self.assertIn("if (n) openNote(n);", click)
        self.assertIn("const card = (mapShown && mapEl.querySelector(`.ncard[data-note=\"${CSS.escape(popNote.id)}\"]`))",
                      reader)   # (the popover anchors to the card that is visible, not the one the map covers)
        self.assertIn("mapEl.addEventListener('scroll', () => { if (popNote) placePop(); }, { passive: true });", reader)
        # (the map is its own scroller: its scroll events do not reach the window's handler)

    def test_a_note_change_repaints_the_map_or_marks_it_to_build_again(self):
        reader = text("reader.js")
        self.assertIn("if (mapShown) { mapRender(); if (popNote) placePop(); } else mapKey = '';", reader)
        self.assertIn("if (mapKey !== `${lang}|${ui}` || !mapRoot) mapRender();", reader)   # (the label follows the language)
        self.assertIn("if (mapShown) { mapFrame(); mapLayout(); if (popNote) placePop(); }", reader)   # (a narrower note wraps taller)
        self.assertIn("else mapKey = '';   // (the map is built afresh at the new width when it opens)", reader)

    def test_the_map_notes_are_hidden_with_the_other_margins(self):
        css = text("reader.css")
        self.assertIn(".mm-notes { position: absolute; left: 0; top: 0; width: min(360px, calc(100vw - 48px - var(--mm-left, 0px)));", css)
        self.assertIn('html[data-hide~="notes"] .mm-notes { display: none; }', css)


if __name__ == "__main__":
    unittest.main()
