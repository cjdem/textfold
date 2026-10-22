"""An EPUB's chapters are decoded before they are parsed: a content document with no declaration is UTF-8 by the EPUB
spec, and lxml's HTML parser would guess Windows-1252 when a non-ASCII byte comes early, putting mojibake in the
document. A chapter that names its encoding (Latin-1, GBK, UTF-16's BOM) is read in it, and a full XHTML chapter's
head title is not its text.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from textfold import office

CONTAINER = ('<?xml version="1.0"?><container version="1.0" '
             'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
             '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
             "</rootfiles></container>")


def opf(href="chapter.xhtml", media="application/xhtml+xml"):
    return ('<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>A book</dc:title></metadata>'
            f'<manifest><item id="c1" href="{href}" media-type="{media}"/></manifest>'
            '<spine><itemref idref="c1"/></spine></package>')


def make_epub(path, chapter, href="chapter.xhtml", media="application/xhtml+xml"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("META-INF/container.xml", CONTAINER)
        z.writestr("OEBPS/content.opf", opf(href, media))
        z.writestr(f"OEBPS/{href}", chapter)


class EpubEncoding(unittest.TestCase):
    def blocks(self, chapter, href="chapter.xhtml", media="application/xhtml+xml"):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "book.epub"
            make_epub(p, chapter, href, media)
            out = office.convert(p, Path(tmp) / "out")
            sc = json.loads((Path(out) / "structured_content.json").read_text(encoding="utf-8"))
        return [b for page in sc["pages"] for b in page["blocks"]]

    def text(self, chapter, **kw):
        return "".join(b.get("content") or "" for b in self.blocks(chapter, **kw) if b["type"] == "text")

    def test_an_undeclared_utf8_chapter_is_read_as_utf8(self):
        # (no declaration: the HTML parser's guess would be Windows-1252, and 中文 is not that)
        got = self.text("<html><body><p>中文开篇：跨境支付。</p><p>第二段。</p></body></html>".encode("utf-8"))
        self.assertIn("中文开篇：跨境支付。", got)
        self.assertNotIn("ä¸­", got)

    def test_a_full_xhtml_chapter_keeps_its_head_out_of_the_text(self):
        chapter = ('<?xml version="1.0"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml">'
                   "<head><title>Chapter One</title></head><body><h1>Heading</h1><p>中文</p></body></html>")
        got = self.text(chapter.encode("utf-8"))
        self.assertIn("中文", got)
        self.assertNotIn("Chapter One", got)   # (the head's title is not the chapter's text)

    def test_the_usual_declaration_with_an_encoding_is_read(self):
        # (the standard EPUB header: lxml refuses this declaration in a Unicode string unless it is dropped first)
        chapter = ('<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml">'
                   "<head><title>Chapter One</title></head><body><h1>Heading</h1><p>中文</p></body></html>")
        got = self.text(chapter.encode("utf-8"))
        self.assertIn("中文", got)
        self.assertNotIn("Chapter One", got)

    def test_a_chapter_that_names_its_encoding_in_the_declaration_is_read(self):
        for enc, words in (("windows-1252", "café Müller"), ("big5", "中文測試"), ("shift_jis", "日本語"), ("gbk", "跨境支付")):
            with self.subTest(encoding=enc):
                chapter = f'<?xml version="1.0" encoding="{enc}"?><html><body><p>{words}</p></body></html>'
                self.assertIn(words, self.text(chapter.encode(enc)))

    def test_a_long_comment_before_the_doctype_does_not_hide_the_document(self):
        chapter = ("<!--" + "x" * 3000 + "--><!DOCTYPE html><html><head><title>Chapter One</title></head>"
                   "<body><p>中文</p></body></html>")
        got = self.text(chapter.encode("utf-8"))
        self.assertIn("中文", got)
        self.assertNotIn("Chapter One", got)

    def test_a_document_without_an_html_element_or_after_a_processing_instruction(self):
        for chapter in ("<head><title>Chapter One</title></head><body><p>中文</p></body>",
                        '<?php echo "x"; ?><html><head><title>Chapter One</title></head><body><p>中文</p></body></html>'):
            with self.subTest(start=chapter[:12]):
                got = self.text(chapter.encode("utf-8"))
                self.assertIn("中文", got)
                self.assertNotIn("Chapter One", got)

    def test_a_chapter_that_names_windows_1252_is_read_in_it(self):
        chapter = ('<html><head><meta charset="windows-1252"/></head>'
                   "<body><p>café Müller</p></body></html>")
        self.assertIn("café Müller", self.text(chapter.encode("cp1252")))

    def test_a_chapter_that_names_gbk_is_read_in_it(self):
        chapter = ('<html><head><meta http-equiv="Content-Type" content="text/html; charset=gbk"/></head>'
                   "<body><p>跨境支付</p></body></html>")
        self.assertIn("跨境支付", self.text(chapter.encode("gbk")))

    def test_a_utf16_chapter_with_a_bom_is_read(self):
        self.assertIn("中文", self.text("<html><body><p>中文</p></body></html>".encode("utf-16")))

    def test_an_svg_spine_item_keeps_its_text(self):
        svg = ('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><text>Hello</text></svg>')
        blocks = self.blocks(svg.encode("utf-8"), "chapter.svg", "image/svg+xml")
        self.assertIn("Hello", "".join(b.get("content") or "" for b in blocks))


if __name__ == "__main__":
    unittest.main()
