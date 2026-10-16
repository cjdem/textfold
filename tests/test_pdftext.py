"""pdftext.py: a PDF's pages, as pdf-inspector writes them in Markdown, into the engine's blocks.

The pages below are cut from what pdf-inspector 1.25 writes for two real papers: an arXiv preprint in Springer's
style (its headings found, its title set over two lines) and an Elsevier journal article (its headings run into their
paragraphs in bold or italics, a running head over every page). The read tests make a PDF with Pillow, one with words
in it and one that is a picture of a page, and check which one is read without the engine. The figure tests write a
page by hand with a drawing between its paragraphs, labels on it and a caption under it.

Run from the repo root:
    python -m unittest discover tests
"""
import tempfile
import unittest
from pathlib import Path

from textfold import pdfdoc, pdftext

ARXIV = [(0, """# A Multi-Stage Hybrid Framework for Automated Interpretation of Multi-View Engineering Drawings

# Using Vision Language Model

Muhammad Tayyab Khan 1, 3*#, Zane Yong<sup>2#</sup>

**Abstract.** Engineering drawings are fundamental to manufacturing communica- tion, serving as the primary medium. The third stage employs two OCR- free VLMs.
"""), (1, """# 1 Introduction

Engineering drawings remain central to industrial communication.

## 1.1 Scope

```
{"id": 1}
```
"""), (2, """# References

[1] Lin, Y.-H., 2023, Machines, **11**(8), p. 802.
""")]

HEAD = "*X. Li et al. Advanced Engineering Informatics 76 (2026) 105034*"
ELSEVIER = [(0, """Advanced Engineering Informatics 76 (2026) 105034

# Advanced Engineering Informatics

journal homepage: www.elsevier.com/locate/aei

# A human-in-the-loop automated framework for high-precision bridge maintenance knowledge graphs: from construction to refinement with

# LLMs and GNNs

**1. Introduction**
relation-entity triples, KGs provide the semantic foundation.
""")] + [(n, f"""{HEAD} texts on page {n}.

**2. Related work**
*2.{n}. Evolution of bridge maintenance informatics toward high-precision* *KGs* Bridge maintenance knowledge management.

*3.2. Two-stage parent*–*child collaborative knowledge fusion* The raw graph.

| a | b |
|---|---|
| 1 | 2 |

{n + 1}
""") for n in range(1, 5)]


def typeset(lines):
    """A one-page PDF with its words in it (Helvetica), written by hand: [(font size, text)], top to bottom."""
    y, at = 740, []
    for size, text in lines:
        y -= size * 2
        at.append((72, y, size, text))
    return page_of(at)


def page_of(words, boxes=()):
    """A one-page PDF of words [(x, y, font size, text)] and filled boxes [(x, y, width, height)], in PDF points."""
    ops = [f"0.3 0.5 0.8 rg {x} {y} {w} {h} re f" for x, y, w, h in boxes] + ["0 g BT"]
    ops += [f"/F1 {size} Tf 1 0 0 1 {x} {y} Tm ({text}) Tj" for x, y, size, text in words]
    ops.append("ET")
    stream = "\n".join(ops).encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    out, at = bytearray(b"%PDF-1.4\n"), []
    for n, o in enumerate(objs, 1):
        at.append(len(out))
        out += b"%d 0 obj\n" % n + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % a for a in at)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def kinds(sc):
    return [(b["type"], b["content"]) for p in sc["pages"] for b in p["blocks"]]


class Structure(unittest.TestCase):
    def test_title_over_two_lines_is_one(self):
        sc = pdftext.structure(ARXIV)
        title, _, md = pdfdoc.to_markdown(sc, "x.pdf")
        self.assertEqual(title, "A Multi-Stage Hybrid Framework for Automated Interpretation of Multi-View Engineering Drawings Using Vision Language Model")
        self.assertNotIn("## Using Vision", md)

    def test_headings_code_and_words_cut_at_a_line_end(self):
        title, _, md = pdfdoc.to_markdown(pdftext.structure(ARXIV), "x.pdf")
        self.assertIn("## 1 Introduction", md)
        self.assertIn("### 1.1 Scope", md)
        self.assertIn("## References", md)
        self.assertIn('```\n{"id": 1}\n```', md)
        self.assertIn("## Abstract\n\nEngineering drawings are fundamental to manufacturing communication, serving", md)
        self.assertIn("two OCR-free VLMs", md)

    def test_journal_name_is_front_matter_not_the_title(self):
        title, _, md = pdfdoc.to_markdown(pdftext.structure(ELSEVIER), "x.pdf")
        self.assertTrue(title.startswith("A human-in-the-loop automated framework"), title)
        self.assertTrue(title.endswith("refinement with LLMs and GNNs"), title)
        self.assertNotIn("Advanced Engineering Informatics", md.split("## 1. Introduction")[0])

    def test_headings_run_into_their_paragraphs(self):
        title, _, md = pdfdoc.to_markdown(pdftext.structure(ELSEVIER), "x.pdf")
        self.assertIn("## 2. Related work", md)
        self.assertIn("### 2.1. Evolution of bridge maintenance informatics toward high-precision KGs", md)
        self.assertIn("### 3.2. Two-stage parent–child collaborative knowledge fusion", md)
        self.assertIn("\nBridge maintenance knowledge management.", md)

    def test_running_head_and_page_numbers_out(self):
        sc = pdftext.structure(ELSEVIER)
        words = " ".join(c for _, c in kinds(sc) if _ != "page_number")
        self.assertNotIn("X. Li et al.", words)
        self.assertIn("texts on page 3.", words)
        self.assertIn(("page_number", "3"), kinds(sc))
        self.assertIn(("table", "| a | b |\n|---|---|\n| 1 | 2 |"), kinds(sc))

    def test_a_titles_first_word_is_no_numbering(self):
        self.assertIsNone(pdftext.NUMBER.match("A Multi-Stage Hybrid Framework"))
        for s in ("3 Methods", "3.2. Data", "A.1 Prompts", "IV. Results"):
            self.assertIsNotNone(pdftext.NUMBER.match(s), s)


class Read(unittest.TestCase):
    def test_a_typeset_pdf_is_read(self):
        body = "Folded text keeps every sentence of the paper and shows the parts that matter first, deeper on request."
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "paper.pdf"
            f.write_bytes(typeset([(20, "Reading Papers at Every Level"), (11, body), (14, "1 Introduction"), (11, body)] + [(11, body)] * 8))
            pages = pdftext.read(f)
            self.assertIsNotNone(pages)
            out = pdftext.convert(f, Path(tmp) / "out")
            title, _, md = pdfdoc.to_markdown(pdfdoc.read_output(out), f.name)
            self.assertIn("Introduction", md)
            self.assertIn("shows the parts that matter first", md)

    def test_words_read_a_picture_needs_the_engine(self):
        from PIL import Image, ImageDraw
        with tempfile.TemporaryDirectory() as tmp:
            scan = Path(tmp) / "scan.pdf"
            page = Image.new("RGB", (1240, 1754), "white")
            draw = ImageDraw.Draw(page)
            for i in range(30):
                draw.text((100, 100 + 40 * i), f"A scanned line of text, number {i}, with its words", fill="black")
            page.save(scan, resolution=150)
            self.assertIsNone(pdftext.read(scan))
            self.assertIsNone(pdftext.convert(scan, Path(tmp) / "out"))
            bad = Path(tmp) / "bad.pdf"
            bad.write_bytes(b"%PDF-1.4 not a pdf")
            with self.assertRaises(ValueError):
                pdftext.read(bad)

    def test_without_pdf_inspector_the_engine_reads_it(self):
        import sys
        from unittest import mock
        with mock.patch.dict(sys.modules, {"pdf_inspector": None}):   # (an import of it fails, as where it is not built)
            self.assertIsNone(pdftext.read("paper.pdf"))


PROSE = "Folded text keeps every sentence of the paper and shows the parts that matter first, deeper on request."
CAPTION = "Figure 1: Accuracy over the epochs of training, for the three models compared."


def with_a_figure():
    """A page: two paragraphs, a drawing between them with its labels on it, its caption under it."""
    words = [(72, 720 - 14 * n, 10, PROSE) for n in range(4)]
    words += [(90, 620, 8, "Accuracy"), (240, 490, 8, "Epochs"), (72, 455, 9, CAPTION)]
    words += [(72, 420 - 14 * n, 10, PROSE) for n in range(12)]
    return page_of(words, boxes=[(72, 480, 320, 170)])


class Figures(unittest.TestCase):
    def convert(self, tmp):
        f = Path(tmp) / "paper.pdf"
        f.write_bytes(with_a_figure())
        out = pdftext.convert(f, Path(tmp) / "out")
        return out, pdfdoc.read_output(out)

    def test_a_figure_is_cut_whole_with_its_caption(self):
        try:
            import pypdfium2   # noqa: F401
        except ImportError:
            self.skipTest("pypdfium2 is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            out, sc = self.convert(tmp)
            pics = [b for p in sc["pages"] for b in p["blocks"] if b["type"] == "image"]
            self.assertEqual(len(pics), 1)
            self.assertTrue((out / pics[0]["image_source"]).is_file())
            self.assertEqual(pics[0]["captions"][0]["content"], CAPTION)
            x0, y0, x1, y1 = pics[0]["bbox"]   # (fractions of the page, from its upper left corner)
            self.assertTrue(0.1 < x0 < 0.13 and 0.17 < y0 < 0.2 and 0.6 < x1 < 0.67 and 0.38 < y1 < 0.41, pics[0]["bbox"])
            title, _, md = pdfdoc.to_markdown(sc, "paper.pdf")
            self.assertIn(f'<img src="{pics[0]["image_source"]}"', md)
            self.assertIn(f"<figcaption>{CAPTION}</figcaption>", md)
            self.assertEqual(md.count(CAPTION), 1)
            self.assertNotIn("Epochs", md)   # (the words drawn on it are its own)
            self.assertEqual(md.count("deeper on request"), 16)

    def test_without_pypdfium2_the_caption_stays(self):
        import sys
        from unittest import mock
        with mock.patch.dict(sys.modules, {"pypdfium2": None}), tempfile.TemporaryDirectory() as tmp:
            out, sc = self.convert(tmp)
            self.assertFalse(any(b["type"] == "image" for p in sc["pages"] for b in p["blocks"]))
            self.assertIn("Figure 1: Accuracy over the epochs", pdfdoc.to_markdown(sc, "paper.pdf")[2])

    def test_a_caption_not_the_text_about_it(self):
        for s in ("Figure 1: Accuracy", "Fig. 3. Overview", "Figure 4 | Results", "FIGURE 2. A map", "Figure 9:"):
            self.assertIsNotNone(pdftext.CAPTION_AT.match(s), s)
        for s in ("Figure 3 shows the results", "Fig. 6 (middle) shows", "Figures 2 and 3", "Table 1: Results"):
            self.assertIsNone(pdftext.CAPTION_AT.match(s), s)

    def test_arxivs_stamp_is_no_heading(self):
        sc = pdftext.structure([(0, "# arXiv:2512.24601v3 [cs.AI] 11 May 2026\n\n# 1 Introduction\n\nText.\n")])
        self.assertNotIn("arXiv:2512.24601v3", " ".join(c for _, c in kinds(sc)))


if __name__ == "__main__":
    unittest.main()
