"""The sidebar's pin is JavaScript, CSS and two languages' words over a paper; there is no JS test runner here, so this
holds what a Python test can see of it: the words exist in both languages, the pin and the dock run at start, on a fold,
on a resize and after the width changes, and the docked layout starts the page (and the zoom bar) at the sidebar's edge
while a window too narrow for the margins as well puts them in the column.

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


class SidebarPin(unittest.TestCase):
    def test_the_pin_is_written_in_both_languages(self):
        js = text("i18n.js")
        self.assertIn("const pins = (w) => ({ sb_pin: w[0], sb_unpin: w[1] });", js)   # (each word its own index)
        self.assertIn("for (const [code, words] of Object.entries(PINS)) Object.assign(S[code], words);", js)   # (and they reach the reader)
        block = re.search(r"const pins = \(w\) => \(\{(.*?)\}\);", js, re.S).group(1)
        keys = re.findall(r"(\w+): w\[\d+\]", block)
        self.assertEqual(keys, ["sb_pin", "sb_unpin"])
        body = re.search(r"const PINS = \{(.*?)\n  \};", js, re.S).group(1)
        langs = re.findall(r"^\s*(\w+): pins\(", body, re.M)
        self.assertEqual(langs, ["en", "zh"])   # (the fork's two reading languages)
        for lang in langs:
            words = json.loads(re.search(rf"\b{lang}: pins\((\[.*?\])\)", body, re.S).group(1))
            self.assertEqual(len(words), len(keys), lang)
            for key, word in zip(keys, words):
                self.assertTrue(word.strip(), f"{lang} {key}")

    def test_the_pin_is_wired_and_the_dock_follows_the_sidebar(self):
        js = text("app.js")
        self.assertIn("PIN_KEY = 'textfold.sbpin'", js)
        self.assertIn("let pinned = store.get(PIN_KEY) === '1';", js)
        self.assertIn("side.querySelector('.sb-pin').onclick = () => setPinned(!pinned);", js)
        self.assertIn('class="sb-pin" aria-pressed="${pinned}"', js)   # (pressed is pinned)
        self.assertIn("${esc(pinned ? T.sb_unpin : T.sb_pin)}", js)
        self.assertIn("function setPinned(p)", js)
        self.assertIn("if (p) store.set('dr-sidebar', side.classList.contains('collapsed') ? '1' : '0');", js)
        self.assertIn("dockState();", re.search(r"function setPinned\(p\) \{(.*?)\n  \}", js, re.S).group(1))   # (the pin docks it at once)
        self.assertIn("function dockState()", js)
        self.assertIn("const on = !!PAPER && pinned && !side.classList.contains('collapsed') && innerWidth > 720;", js)
        self.assertIn("r.classList.toggle('sb-docked', on);", js)
        self.assertIn("r.classList.toggle('sb-narrow', on && innerWidth - sb < 1248);", js)
        # the remembered width comes before the dock that tests it
        self.assertIn("if (sbw) setWidth(sbw);", js)
        self.assertLess(js.index("if (sbw) setWidth(sbw);"), js.index("if (sbw) dockState();"))
        self.assertIn("if (was !== `${r.classList.contains('sb-docked')}${r.classList.contains('sb-narrow')}`) dispatchEvent(new Event('resize'));", js)
        # a fold stores the preference while pinned, and every fold, resize and width change asks the dock again
        self.assertIn("if (!PAPER || pinned) store.set('dr-sidebar', c ? '1' : '0');", js)
        self.assertIn("dockState();", re.search(r"function setCollapsed\(c\) \{(.*?)\n  \}", js, re.S).group(1))
        self.assertIn("setWidth(+store.get(SBW)); dockState();", js)
        self.assertEqual(js.count("if (document.documentElement.classList.contains('sb-docked')) dispatchEvent(new Event('resize'));"), 3)   # drag, double-click, arrow keys
        # over a paper it starts folded unless pinned, and only an unpinned open sidebar folds on an outside click
        self.assertIn("if (PAPER && !pinned) side.classList.add('collapsed');", js)
        self.assertIn("if (!pinned && !side.classList.contains('collapsed') && !e.composedPath().includes(side)) setCollapsed(true);", js)

    def test_the_docked_layout_starts_at_the_sidebars_edge_and_a_narrow_window_keeps_the_margins_in_the_column(self):
        css = text("app.css")
        for rule in ('.sb-pin {', '.sb-pin[aria-pressed="true"] .pin-head { fill: currentColor; }',
                     '@media (max-width: 719px) { .sb-pin { display: none; } }',
                     'html.app.sb-docked { --rail: var(--sb); --colmax: calc(100vw - 540px - var(--sb)); }',
                     'html.app.sb-docked.sb-narrow, html.app.sb-docked.compare { --colmax: 100vw; }',
                     'html.app.sb-docked #sidebar:not(.collapsed) { box-shadow: none; }',
                     'html.sb-narrow .side, html.sb-narrow .lside { position: static;',
                     'html.sb-narrow .chunk > .side, html.sb-narrow .chunk > .lside { position: static; }'):
            self.assertIn(rule, css)
        # focus still takes the room back: its --rail: 0px comes after the dock's
        self.assertLess(css.index('html.app.sb-docked {'), css.index('html.app.focus { --rail: 0px; }'))
        # a PDF beside the docked text leaves the reader's 420px: its default width takes the rail out too
        reader_css = text("reader.css")
        self.assertIn('html.app.sb-docked.compare { --pdfw: min(46vw, 860px, calc(100vw - var(--rail, 0px) - 420px)); }', reader_css)
        # the reader stops stacking the side notes in a column layout of its own (both conditions, not either alone)
        js = text("reader.js")
        self.assertIn("if (root.classList.contains('compare') || root.classList.contains('sb-narrow') || !matchMedia(D.app ? '(min-width: 1300px)' : '(min-width: 1240px)').matches) return;", js)
        layout = re.search(r"function layoutSides\(\) \{(.*?)\n  \}", js, re.S).group(1)
        self.assertIn("root.classList.contains('compare')", layout)
        self.assertIn("root.classList.contains('sb-narrow')", layout)


if __name__ == "__main__":
    unittest.main()
