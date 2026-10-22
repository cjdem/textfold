"""The reader's headings are a scale, not three sizes of the same thing: a section's well above a subsection's, a
subsection's well above the text, the next as large as the text; a section's carries a rule under it, drawn as an
inset shadow so the zoom's copies carry it (`looks()` copies the shadow). A contract test: the sizes are the design,
and a change to them is a change to the product.

Run from the repo root:
    python -m unittest discover tests
"""
import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "textfold" / "web" / "reader.css").read_text(encoding="utf-8")


def rule(selector):
    """The rule whose selector is exactly this one (not a combined rule that ends with it)."""
    return re.search(r"(?:^|\n)" + re.escape(selector) + r"\s*\{[^}]*\}", CSS).group(0)


class Headings(unittest.TestCase):
    def test_the_scale(self):
        l2, l3, text = rule(".chunk.l2 > .hd"), rule(".chunk.l3 > .hd"), rule('.chunk.l4 > .hd, .chunk.l5 > .hd')
        self.assertIn("font-size: calc(27px * var(--fs))", l2)        # (the Aa size scales a heading too)
        self.assertIn("font-size: calc(21.5px * var(--fs))", l3)
        self.assertIn("font-size: calc(18.5px * var(--fs))", text)    # the author's size: the next heading as large
        self.assertIn("margin: calc(56px * var(--fs)) 0 calc(16px * var(--fs))", l2)
        self.assertIn("padding-bottom: calc(8px * var(--fs))", l2)
        self.assertIn("font-weight: 700", l2)
        self.assertIn("font-weight: 680", l3)

    def test_a_section_has_a_rule_under_it(self):
        self.assertIn("box-shadow: inset 0 -1px 0 var(--line)", rule(".chunk.l2 > .hd"))
        # ...and a Topic card has none: every Topic heading rule with a shadow cancels it
        cards = re.findall(r'\.doc\[data-level="0"\][^{]*\.hd[^{]*\{[^}]*box-shadow[^}]*\}', CSS)
        self.assertTrue(cards)
        for r in cards:
            if "box-shadow" in r:
                self.assertIn("box-shadow: none", r)
        self.assertIn("padding-bottom: 0", rule('.doc[data-level="0"] .chunk > .hd'))
        # the zoom's keyframe copies write out the shadow (looks), or the rule vanishes during a zoom
        js = (Path(__file__).resolve().parent.parent / "textfold" / "web" / "reader.js").read_text(encoding="utf-8")
        self.assertIn("box-shadow:${cs.boxShadow}", js)

    def test_the_heading_text_is_darker_going_out(self):
        self.assertIn("color: var(--ink-2)", rule(".chunk.l5 > .hd"))


if __name__ == "__main__":
    unittest.main()
