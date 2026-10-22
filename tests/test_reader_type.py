"""The reader's Aa menu is JavaScript, CSS and two languages' words; there is no JS test runner here, so this holds
what a Python test can see of it: every word the menu shows is written in both languages the reader offers, every
word the reader asks for exists, and a zoom's sandbox takes the font and width the page was set to (c38804e: without
them the last frame of a zoom sat apart from the page it gave way to).

Run from the repo root:
    python -m unittest discover tests
"""
import json
import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "textfold" / "web"


def text(name):
    return (WEB / name).read_text(encoding="utf-8")


class TypeMenu(unittest.TestCase):
    def keys(self):
        block = re.search(r"const tys = \(w\) => \(\{(.*?)\}\);", text("i18n.js"), re.S).group(1)
        return re.findall(r"(ty_\w+):", block)

    def test_every_word_is_written_in_both_languages(self):
        block = re.search(r"const TY = \{(.*?)\n  \};", text("i18n.js"), re.S).group(1)
        keys = self.keys()
        self.assertEqual(len(keys), 13)
        for lang in ("en", "zh"):
            m = re.search(rf"\b{lang}: tys\((\[.*?\])\)", block, re.S)
            self.assertIsNotNone(m, lang)
            words = json.loads(m.group(1))
            self.assertEqual(len(words), len(keys), lang)
            for key, word in zip(keys, words):
                self.assertTrue(isinstance(word, str) and word.strip(), f"{lang} {key}")

    def test_every_word_the_menu_uses_exists(self):
        used = set(re.findall(r"\bt\.(ty_\w+)", text("reader.js")))
        used |= {"ty_width", "ty_font"}   # (chosen by name: t[`ty_${key}`] in renderTypeMenu)
        self.assertLessEqual(used, set(self.keys()))

    def test_a_zoom_takes_the_font_and_width_it_was_set_to(self):
        css = text("reader.css")
        for rule in ('--fs:', '--colw:', '--col:', '--text:', 'html[data-width="narrow"]', 'html[data-font="sans"]',
                     '@media print { :root { --fs: 1 !important;'):
            self.assertIn(rule, css)
        js = text("reader.js")
        self.assertIn("function mirrorType()", js)
        mirror = re.search(r"function mirrorType\(\) \{(.*?)\n  \}", js, re.S).group(1)
        self.assertIn("--fs", mirror)                        # the size: :host { --fs: 1 } would otherwise win
        for k in ("'app'", "'compare'"):
            self.assertIn(k, mirror)                         # the page's own column cap
        self.assertIn("applyType(); mirrorType();", js)      # a change reaches the keyframes, not only the page
        self.assertIn("mirrorType();\n  // KaTeX", js)        # and the sandbox has it before the first zoom
        self.assertEqual(js.count("mirrorType();"), 4)        # startup, a type change, and compare on and off

    def test_the_sizes_and_widths_are_what_the_css_styles(self):
        js = text("reader.js")
        self.assertEqual(json.loads(re.search(r"const SIZES = (\[[^\]]+\])", js).group(1)),
                         [0.86, 0.93, 1, 1.08, 1.16, 1.25, 1.35])
        widths = re.search(r"WIDTHS = (\[[^\]]+\])", js).group(1).replace("'", '"')
        self.assertEqual(json.loads(widths), ["narrow", "standard", "wide"])


if __name__ == "__main__":
    unittest.main()
