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
        used |= {"ty_width", "ty_font", "ty_m_asks", "ty_m_notes"}   # (chosen by name: t[`ty_${key}`], t[`ty_m_${k}`])
        js = text("i18n.js")
        defined = set(self.keys())
        for block in ("const rds = ", "const tym = "):
            defined |= set(re.findall(r"(ty_\w+): w\[\d+\]", re.search(block + r"\(w\) => \(\{(.*?)\}\);", js, re.S).group(1)))
        defined.add("ty_focus_off")       # (written by the loop after RDS)
        self.assertLessEqual(used, defined)

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

    def test_the_appearance_words_are_written_in_both_languages(self):
        js = text("i18n.js")
        keys = re.findall(r"(\w+): w\[\d+\]", re.search(r"const rds = \(w\) => \(\{(.*?)\}\);", js, re.S).group(1))
        self.assertEqual(len(keys), 14)
        block = re.search(r"const RDS = \{(.*?)\n  \};", js, re.S).group(1)
        for lang in ("en", "zh"):
            m = re.search(rf"\b{lang}: rds\((\[.*?\])\)", block, re.S)
            self.assertIsNotNone(m, lang)
            words = json.loads(m.group(1))
            self.assertEqual(len(words), len(keys), lang)
            for key, word in zip(keys, words):
                self.assertTrue(isinstance(word, str) and word.strip(), f"{lang} {key}")
        self.assertIn('en: "Leave focus", zh: "退出专注"', js)

    def test_the_appearance_the_place_and_focus_are_kept_with_the_type(self):
        js = text("reader.js")
        self.assertIn("const MODES = ['auto', 'light', 'dark'], STYLES = ['default', 'paper']", js)
        self.assertIn("LEADS = { tight: 0.9, standard: 1, loose: 1.15 }", js)
        self.assertIn("const TYPE0 = { size: 1, width: 'standard', font: 'serif', hide: [], mode: 'auto', style: 'default', lead: 'standard' }", js)
        self.assertIn("POS_KEY = 'textfold.pos'", js)
        self.assertIn("else if (e.key === 'f' || e.key === 'F') setFocus(!focusOn);", js)
        self.assertIn("r.classList.toggle('focus', on);", js)

    def test_the_margins_can_be_hidden(self):
        js = text("i18n.js")
        block = re.search(r"const tym = \(w\) => \(\{(.*?)\}\);", js, re.S).group(1)
        keys = re.findall(r"(\w+): w\[\d+\]", block)
        self.assertEqual(keys, ["ty_margin", "ty_m_asks", "ty_m_notes"])
        body = re.search(r"const TYM = \{(.*?)\n  \};", js, re.S).group(1)
        for lang in ("en", "zh"):
            words = json.loads(re.search(rf"\b{lang}: tym\((\[.*?\])\)", body, re.S).group(1))
            self.assertEqual(len(words), len(keys), lang)
            for key, word in zip(keys, words):
                self.assertTrue(word.strip(), f"{lang} {key}")
        reader = text("reader.js")
        self.assertIn("TYPE_KEY = 'textfold.type'", reader)
        self.assertIn("WIDTHS = ['narrow', 'standard', 'wide'], MARGINS = ['asks', 'notes']", reader)
        self.assertIn("hide: Array.isArray(v.hide) ? MARGINS.filter((k) => v.hide.includes(k)) : []", reader)
        self.assertIn("if (type.hide.length) r.dataset.hide = type.hide.join(' '); else delete r.dataset.hide;", reader)
        self.assertIn("for (const k of ['font', 'width', 'hide', 'theme', 'style'])", reader)
        self.assertIn("font === TYPE0.font && !type.hide.length", reader)
        # the button's state and the toggle: pressed is shown, and a click flips that one margin only
        self.assertIn('aria-pressed="${!type.hide.includes(k)}"', reader)
        self.assertIn("else if (b.dataset.margin) { const k = b.dataset.margin; setType({ hide: MARGINS.filter((x) => (x === k) !== type.hide.includes(x)) }); }", reader)
        self.assertIn('b.dataset.margin ? `[data-margin="${b.dataset.margin}"]`', reader)   # the redrawn menu keeps the focus
        css = text("reader.css")
        self.assertIn('html[data-hide~="asks"] .side-notes', css)
        # a hidden margin has to outrank every rule that shows it: the plain one does not, the level rules set
        # display: flex further down the sheet, and the .doc[data-level] one outranks the attribute alone
        for sel in ('html[data-hide~="notes"] .lside', 'html[data-hide~="notes"] .u > .lside',
                    'html[data-hide~="notes"] .chunk > .lside',
                    'html[data-hide~="notes"] .doc[data-level] .chunk > .lside'):
            self.assertIn(sel, css)
        # every rule that makes a margin a flex box is outranked by a hide selector for that margin
        def spec(sel):   # (ids, classes and attributes, elements: no pseudo-class or ::-element here)
            return (len(re.findall(r"#[\w-]+", sel)), len(re.findall(r"\.[\w-]+|\[[^\]]*\]", sel)),
                    len(re.findall(r"(?:^|[\s>+~])([a-zA-Z][\w-]*)", sel)))
        shown = [s for s in re.findall(r"([^{}]+)\{[^}]*display: *flex[^}]*\}", css) if ".lside" in s or ".side-notes" in s]
        self.assertTrue(shown)
        hide = re.search(r"html\[data-hide~=\"asks\"\][^{]*\{[^}]*display: none[^}]*\}", css).group(0).split("{")[0]
        hide_sels = [s.strip() for s in hide.split(",")]
        for rule in shown:
            for sel in rule.split(","):
                subject = ".side-notes" if ".side-notes" in sel else ".lside" if ".lside" in sel else None
                if not subject:
                    continue
                outranks = [h for h in hide_sels if subject in h and spec(h) > spec(sel.strip())]
                self.assertTrue(outranks, f"{sel.strip()} shows a margin no hide selector outranks")

    def test_the_page_can_be_light_dark_or_paper_and_the_lines_spaced(self):
        css = text("reader.css")
        for rule in (':root[data-theme="dark"]', ':root[data-theme="light"]', ':root[data-style="paper"]',
                     '--lh: 1 !important', 'html.focus .topbar', '.readprog', '.rpill'):
            self.assertIn(rule, css)
        # a chosen light is data-theme="light"; the system's dark applies only when no choice is made
        self.assertNotIn(':root:not([data-theme="light"])', css)
        self.assertIn(':root[data-style="paper"]:not([data-theme])', css)   # paper in a dark system
        self.assertIn('@media screen { :root[data-theme="dark"] .zthumb', css)
        # the reading lines take the spacing
        for sel in ('.u[data-l="4"], .u[data-l="3"]', '.u[data-l="2"]', '.u[data-l="1"]',
                    'html[data-lang="zh"] .u[data-l="4"], html[data-lang="zh"] .u[data-l="3"]'):
            rule = re.search(re.escape(sel) + r" \{[^}]*\}", css).group(0)
            self.assertIn('var(--lh, 1)', rule, sel)

    def test_the_reading_card_follows_the_chosen_light(self):
        """The drawer's error and status colours are light-on-light if its dark rules follow the system alone."""
        card = text("card.css")
        self.assertGreaterEqual(card.count(':root[data-theme="dark"]'), 5)
        self.assertEqual(card.count(':root:not([data-theme])'), card.count(':root[data-theme="dark"]'))
        self.assertNotRegex(card, r"@media \(prefers-color-scheme: dark\) \{\s*\.")

    def test_the_sizes_and_widths_are_what_the_css_styles(self):
        js = text("reader.js")
        self.assertEqual(json.loads(re.search(r"const SIZES = (\[[^\]]+\])", js).group(1)),
                         [0.86, 0.93, 1, 1.08, 1.16, 1.25, 1.35])
        widths = re.search(r"WIDTHS = (\[[^\]]+\])", js).group(1).replace("'", '"')
        self.assertEqual(json.loads(widths), ["narrow", "standard", "wide"])


if __name__ == "__main__":
    unittest.main()
