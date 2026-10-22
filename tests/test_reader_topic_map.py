"""Topic can be read as cards grouped under their section or as a map of the text's outline. Like the type's menu, it
is JavaScript and CSS only; these hold the contracts a Python test can see: the map's words in both languages, the
hooks that draw and dismiss it, the cards' grouping classes, and the map's own stylesheet (including its dark rule,
which must follow the reader's chosen light as well as the system's).

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


class TopicMap(unittest.TestCase):
    def test_the_map_words_are_written_in_both_languages(self):
        js = text("i18n.js")
        keys = re.findall(r"(\w+): w\[\d+\]", re.search(r"const tvs = \(w\) => \(\{(.*?)\}\);", js, re.S).group(1))
        self.assertEqual(keys, ["tv_label", "tv_cards", "tv_map", "mm_all", "mm_secs", "mm_hint"])
        block = re.search(r"const TV = \{(.*?)\n  \};", js, re.S).group(1)
        for lang in ("en", "zh"):
            m = re.search(rf"\b{lang}: tvs\((\[.*?\])\)", block, re.S)
            self.assertIsNotNone(m, lang)
            words = json.loads(m.group(1))
            self.assertEqual(len(words), len(keys), lang)
            for key, word in zip(keys, words):
                self.assertTrue(isinstance(word, str) and word.strip(), f"{lang} {key}")

    def test_the_map_is_drawn_only_at_topic_and_kept_per_browser(self):
        js = text("reader.js")
        for hook in ("TV_KEY = 'textfold.topicview'", "function mapTree()", "function mapLayout()", "function mapSync()",
                     "function mapAway()"):
            self.assertIn(hook, js)
        # the zoom hides it before the first frame, and it comes back only at Topic, at rest, with no place open
        self.assertIn("const kick = () => { if (mapShown) mapAway(); if (!rafId) rafId = requestAnimationFrame(tick); };", js)
        self.assertIn("topicView === 'map' && level === 0 && !localLevel.size", js)
        self.assertIn("!document.documentElement.classList.contains('compare')", js)
        self.assertIn("!document.documentElement.classList.contains('focus')", js)
        # a size change lays the open map out again (its nodes are measured)
        self.assertIn("if (mapShown) mapRender(); else mapKey = '';", js)
        # the PDF pane opening or closing re-syncs it
        self.assertIn("classList.add('compare');\n    mirrorType(); mapSync();", js)
        self.assertIn("classList.remove('compare');\n    mirrorType(); mapSync();", js)

    def test_the_cards_group_under_their_section(self):
        js, css = text("reader.js"), text("reader.css")
        block = re.search(r"the Topic map's rows.*?\n  \}", js, re.S).group(0)
        self.assertIn("const lv = (c) => c.level || 2, top = Math.min(...D.chunks.map(lv));", block)
        self.assertIn("const sc = secs.get(c.id), next = D.chunks[i + 1], prev = D.chunks[i - 1];", block)
        self.assertIn("if (next && lv(next) > lv(c) && (c.num || c.title)) sc.sec.classList.add('parent'", block)
        self.assertIn("if (prev && lv(prev) > lv(c)) sc.sec.classList.add('newrow')", block)
        for sel in ('.doc[data-level="0"] .chunk.parent', '.doc[data-level="0"] .chunk.parent > .hd',
                    '.doc[data-level="0"] .chunk.newrow'):
            self.assertIn(sel, css)

    def test_the_map_has_its_own_styles_and_follows_the_chosen_light(self):
        css = text("reader.css")
        for sel in ('.tview', '.mmap', '.mm-tools', '.mm-canvas', '.mm-root', '.mm-sec', '.mm-leaf', '.zrow'):
            self.assertIn(sel, css)
        self.assertIn(':root:not([data-theme]) .tview button[aria-checked="true"]', css)
        self.assertIn(':root[data-theme="dark"] .tview button[aria-checked="true"]', css)


if __name__ == "__main__":
    unittest.main()
