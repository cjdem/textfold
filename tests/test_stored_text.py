"""What the reader stores about a document and its library is ASCII-escaped JSON, so a title, a folder's name or a
file's name can hold a character the system's encoding lacks (a ✩ after an Elsevier paper's title, measured on a GBK
Windows machine); a web address is UTF-8 with a byte-order mark, and an exported page and an SVG in it are UTF-8.

Each test uses a data folder of its own (store.DATA).

Run from the repo root:
    python -m unittest discover tests
"""
import json
import locale
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from textfold import build, fetch, library, local, server, store, webpage, zotero

STAR = "✩"
TITLE = f"Fuzzy controller design of micro-unmanned helicopter {STAR}"


class StoredText(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def ascii_json(self, path):
        raw = path.read_bytes()
        self.assertTrue(all(b < 128 for b in raw), f"{path} is not ASCII-escaped")
        return json.loads(raw.decode("ascii"))

    def test_a_pdf_title_with_a_star_is_stored_and_read_back(self):
        meta = {"id": "pdf-star", "version": "", "title": TITLE, "authors": ["Yanpeng Hu"], "date": "2020",
                "snapshot": "2026-10-18", "abs_url": "", "html_url": "", "doi": "", "license": "",
                "source": {"kind": "pdf", "name": "Fuzzy controller design.pdf", "tier": "accurate",
                           "engine": "MinerU API"},
                "label": "PDF · Fuzzy controller design.pdf"}
        local.store_doc("pdf-star", "<p>text</p>", meta, "source.md", "text",
                        lambda folder: (lambda src: None), sizes=True)
        stored = self.ascii_json(store.pdir("pdf-star") / "meta.json")
        self.assertEqual(stored["title"], TITLE)
        self.assertEqual(stored["label"], meta["label"])
        # the reader's own read (the system's encoding) gets the same title back
        self.assertEqual(json.loads((store.pdir("pdf-star") / "meta.json").read_text())["title"], TITLE)

    def test_a_folder_name_with_a_star_is_stored_and_read_back(self):
        library.change({"op": "new", "name": f"Thesis {STAR}"})
        stored = self.ascii_json(self.tmp_path() / "library.json")
        self.assertEqual(stored["folders"][0]["name"], f"Thesis {STAR}")
        self.assertEqual(library.folders()["folders"][0]["name"], f"Thesis {STAR}")

    def tmp_path(self):
        return Path(self.tmp.name)

    def test_a_zotero_title_with_a_star_is_stored_in_the_index_and_the_document(self):
        d = store.pdir("pdf-zotero-star")
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"id": "pdf-zotero-star", "title": "Before",
                                                 "source": {"kind": "pdf", "name": "file.pdf"}}))
        zotero.link("users/0", "ITEM1", "pdf-zotero-star", f"Index {STAR}",
                    {"title": TITLE, "authors": ["Yanpeng Hu"], "date": "2020", "citekey": "Hu2020"})
        self.assertEqual(self.ascii_json(self.tmp_path() / "zotero.json")["users/0/ITEM1"]["title"],
                         f"Index {STAR}")
        self.assertTrue(zotero.apply("pdf-zotero-star"))
        meta = self.ascii_json(d / "meta.json")
        self.assertEqual(meta["title"], TITLE)
        self.assertEqual(meta["zotero"], {"library": "users/0", "item": "ITEM1", "citekey": "Hu2020"})

    def test_a_web_address_with_a_star_is_stored_as_utf8(self):
        url = f"https://example.com/星{STAR}"
        pid = webpage.register(url)
        f = store.pdir(pid) / "url.txt"
        self.assertTrue(f.read_bytes().startswith(b"\xef\xbb\xbf"), "the address was not written with the mark")
        self.assertEqual(f.read_bytes().decode("utf-8-sig"), url)
        self.assertEqual(store.read_url(f), url)

    def test_an_address_stored_before_the_mark_is_read_in_the_system_encoding(self):
        url = "https://一.com/page"   # GBK's D2 BB is also valid UTF-8: trying UTF-8 first would read another address
        f = self.tmp_path() / "url.txt"
        try:
            raw = url.encode(locale.getpreferredencoding(False))
        except UnicodeEncodeError:
            self.skipTest("the system's encoding cannot hold this address")
        f.write_bytes(raw)
        self.assertEqual(store.read_url(f), url)

    def test_an_arxiv_title_with_a_star_is_stored(self):
        abs_html = (f'<html><head><meta name="citation_title" content="A title {STAR}">'
                    '<meta name="citation_author" content="A. Author"></head></html>')
        with mock.patch.object(fetch, "get", side_effect=[
                (b"<html><body>page</body></html>", "https://arxiv.org/html/2512.00001"),
                (abs_html.encode("utf-8"), "https://arxiv.org/abs/2512.00001")]):
            d = fetch.fetch("2512.00001", self.tmp_path())
        self.assertEqual(self.ascii_json(d / "meta.json")["title"], f"A title {STAR}")

    def test_a_file_waiting_for_the_engine_keeps_an_ascii_name(self):
        f = self.tmp_path() / f"论文 · A {STAR}.pdf"
        f.write_bytes(b"%PDF-1.7")
        server.Jobs.wait_for_engine(SimpleNamespace(pending={}), f.stem, str(f), f.name, "en")
        self.assertEqual(self.ascii_json(f.with_suffix(".json"))["name"], f.name)

    def test_an_svg_with_chinese_keeps_its_text(self):
        f = self.tmp_path() / "图.svg"
        f.write_text(f"<svg><text>中文 {STAR}</text></svg>", encoding="utf-8")
        uri = build.data_uri(f)
        self.assertIn(f"中文 {STAR}", urllib.parse.unquote(uri.split(",", 1)[1]))

    def test_an_svg_that_declares_gbk_is_read_in_gbk(self):
        f = self.tmp_path() / "旧图.svg"
        f.write_bytes('<?xml version="1.0" encoding="GBK"?><svg><text>中文</text></svg>'.encode("gbk"))
        uri = build.data_uri(f)
        self.assertIn("中文", urllib.parse.unquote(uri.split(",", 1)[1]))

    def test_an_svg_with_an_unknown_declared_encoding_falls_back_to_utf8(self):
        f = self.tmp_path() / "怪图.svg"
        f.write_bytes('<?xml version="1.0" encoding="x-user-defined"?><svg><text>中文</text></svg>'.encode("utf-8"))
        uri = build.data_uri(f)
        self.assertIn("中文", urllib.parse.unquote(uri.split(",", 1)[1]))

    def test_an_xml_stylesheet_instruction_is_not_a_declaration(self):
        f = self.tmp_path() / "样式.svg"
        f.write_text('<?xml-stylesheet type="text/xsl" href="s.xsl" encoding="GBK"?>'
                     "<svg><text>中文</text></svg>", encoding="utf-8")
        uri = build.data_uri(f)
        self.assertIn("中文", urllib.parse.unquote(uri.split(",", 1)[1]))

    def test_an_exported_page_is_utf8(self):
        pid = local.import_text(f"# 中文标题 {STAR}\n\n正文里有星号 {STAR}。", f"中文 {STAR}.md")
        f = build.export(pid)
        text = f.read_bytes().decode("utf-8")
        self.assertIn(f"中文标题 {STAR}", text)
        self.assertIn('<meta charset="utf-8">', text)
