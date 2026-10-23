"""A note drafted in the popover (the whole text's New note) keeps what was typed when it closes before the 700 ms save
timer fires, whether Escape is pressed, the page is clicked, or another note is opened. A question typed but not sent
is a draft too, but its words are the question field rather than the note's text, and closing it still discards them;
this change does not touch that. There is no JS test runner here, so this holds the close path a Python test can see;
the browser check is in the change's record.

Run from the repo root:
    python -m unittest discover tests
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class NoteDraft(unittest.TestCase):
    def test_a_draft_closed_with_words_saves_them(self):
        js = (ROOT / "textfold" / "web" / "reader.js").read_text(encoding="utf-8")
        start = js.index("function closeNote()")
        block = js[start:js.index("npop.addEventListener('input'", start)]
        self.assertIn("if (popDraft)", block)
        self.assertIn("const v = field ? field.value : '';", block)
        self.assertIn("if (v.trim()) {", block)
        self.assertIn("saveNote({ ...popNote, text: v })", block)
        self.assertLess(block.index("saveNote({ ...popNote, text: v })"), block.index("deleteNote({ ...popNote, text: '' })"))
        self.assertIn("} else if (notes.some((x) => x.id === popNote.id)) deleteNote({ ...popNote, text: '' });", block)

    def test_another_note_opened_over_a_draft_keeps_its_words_first(self):
        js = (ROOT / "textfold" / "web" / "reader.js").read_text(encoding="utf-8")
        start = js.index("function openNote(")
        block = js[start:js.index("function placePop()", start)]
        self.assertIn("if (popNote && popNote.id !== n.id) closeNote();", block)
        self.assertLess(block.index("if (popNote && popNote.id !== n.id) closeNote();"), block.index("popDraft = draft;"))


if __name__ == "__main__":
    unittest.main()
