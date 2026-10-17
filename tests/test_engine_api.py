"""The MinerU cloud API's output as the structured content the engine on this computer writes (engine._structured):
pages of blocks, boxes 0-1, the types pdfdoc reads. Nothing here calls the API: the zip's own JSON is stood in.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import locale
import tempfile
import unittest
from pathlib import Path

from textfold import engine, store


def page(*blocks):
    return list(blocks)


V2 = [
    page(
        {"type": "title", "content": {"title_content": [{"type": "text", "content": "A paper"}], "level": 1},
         "bbox": [70, 232, 766, 288]},
        {"type": "page_header", "content": {"page_header_content": [{"type": "text", "content": "Journal 1 (2026)"}]},
         "bbox": [70, 37, 396, 52]},
        {"type": "paragraph", "content": {"paragraph_content": [
            {"type": "text", "content": "It holds, for "},
            {"type": "equation_inline", "content": "x=1"},
            {"type": "text", "content": " every x."}]}, "bbox": [72, 313, 697, 337]},
        {"type": "image", "content": {"image_source": {"path": "images/a.jpg"}, "content": "",
                                      "image_caption": [{"type": "text", "content": "Fig. 1 The thing."}]},
         "bbox": [100, 400, 500, 600]},
    ),
    page(
        {"type": "paragraph", "content": {"paragraph_content": [{"type": "text", "content": "Second page."}]},
         "bbox": [72, 90, 500, 120]},
        {"type": "table", "content": {"image_source": {"path": "images/b.jpg"}, "html": "<table><tr><td>1</td></tr></table>",
                                      "table_caption": [{"type": "text", "content": "Table 1 Data."}],
                                      "table_footnote": []}, "bbox": [80, 200, 500, 400]},
        {"type": "equation_interline", "content": {"math_content": "x^2", "math_type": "latex",
                                                   "image_source": {"path": "images/c.jpg"}}, "bbox": [200, 450, 400, 500]},
        {"type": "list", "content": {"list_type": "text_list", "list_items": [
            {"item_type": "text", "item_content": [{"type": "text", "content": "one"}]},
            {"item_type": "text", "item_content": [{"type": "text", "content": "two"}]}]}, "bbox": [78, 520, 478, 560]},
        {"type": "page_number", "content": {"page_number_content": [{"type": "text", "content": "200"}]},
         "bbox": [87, 40, 115, 52]},
    ),
]

FLAT = [
    {"type": "text", "text": "First.", "page_idx": 0, "bbox": [70, 100, 700, 130]},
    {"type": "text", "text": "Second.", "page_idx": 1, "bbox": [70, 100, 700, 130]},
    # the flat format keeps the words at the top of the block, and these kinds carry their own keys
    {"type": "header", "text": "Journal 1 (2026)", "page_idx": 1, "bbox": [70, 20, 500, 40]},
    {"type": "chart", "img_path": "images/chart.jpg", "chart_caption": ["Fig. 2 A chart."],
     "page_idx": 1, "bbox": [100, 300, 400, 500]},
    {"type": "page_footnote", "text": "* Corresponding author.", "page_idx": 1, "bbox": [70, 900, 500, 930]},
    {"type": "page_number", "text": "7", "page_idx": 1, "bbox": [300, 940, 320, 960]},
]


class Structured(unittest.TestCase):
    def folder(self, name, data):
        d = Path(tempfile.mkdtemp())
        (d / name).write_text(json.dumps(data), encoding="utf-8")
        return d

    def test_v2_becomes_engine_blocks(self):
        sc = engine._structured(self.folder("x_content_list_v2.json", V2), "pdf")
        self.assertEqual(sc["metadata"]["file_suffix"], "pdf")
        self.assertEqual([p["page_idx"] for p in sc["pages"]], [0, 1])
        first, second = sc["pages"][0]["blocks"], sc["pages"][1]["blocks"]
        # the title of the first page is the document's; its box is 0-1 of the page
        self.assertEqual(first[0]["type"], "doc_title")
        self.assertEqual(first[0]["content"], "A paper")
        self.assertEqual(first[0]["bbox"], [0.07, 0.232, 0.766, 0.288])
        # a run of the page's words (a header is kept as the engine's, which pdfdoc drops)
        self.assertEqual(first[1]["type"], "header")
        self.assertEqual(first[2]["type"], "text")
        self.assertEqual(first[2]["content"], "It holds, for $x=1$ every x.")
        # a picture with its caption; a table with its HTML; a formula's LaTeX
        image = next(b for b in first if b["type"] == "image")
        self.assertEqual(image["image_source"], "images/a.jpg")
        self.assertEqual(image["captions"], [{"content": "Fig. 1 The thing."}])
        table = next(b for b in second if b["type"] == "table")
        self.assertTrue(table["content"].startswith("<table"))
        self.assertEqual(table["captions"], [{"content": "Table 1 Data."}])
        self.assertEqual(next(b for b in second if b["type"] == "equation")["content"], "x^2")
        self.assertEqual(next(b for b in second if b["type"] == "list")["content"], "- one\n- two")
        self.assertEqual(next(b for b in second if b["type"] == "page_number")["content"], "200")

    def test_flat_list_is_grouped_by_page(self):
        sc = engine._structured(self.folder("x_content_list.json", FLAT), "pdf")
        self.assertEqual([p["page_idx"] for p in sc["pages"]], [0, 1])
        second = sc["pages"][1]["blocks"]
        self.assertEqual(second[0]["content"], "Second.")
        kinds = [b["type"] for b in second]
        self.assertIn("header", kinds)          # a running head stays a header (pdfdoc drops it)
        self.assertIn("page_footnote", kinds)   # a footnote keeps its words
        chart = next(b for b in second if b["type"] == "image")
        self.assertEqual(chart["image_source"], "images/chart.jpg")
        self.assertEqual(chart["captions"], [{"content": "Fig. 2 A chart."}])
        self.assertIn("page_number", kinds)

    def test_no_document_is_an_error(self):
        with self.assertRaises(RuntimeError):
            engine._structured(self.folder("other.json", []), "pdf")


class OldPages(unittest.TestCase):
    """A page stored before local.py wrote UTF-8 (the system's encoding, on a GBK Windows machine) still opens."""

    def test_a_page_stored_in_the_systems_encoding_is_read(self):
        if locale.getpreferredencoding(False).lower().replace("-", "") in ("utf8", "cp65001"):
            self.skipTest("a page stored in another encoding needs a machine that writes pages in it")
        old = store.DATA
        try:
            store.DATA = Path(tempfile.mkdtemp())
            pid = "web-oldpage"
            d = store.pdir(pid)
            d.mkdir(parents=True)
            page = '<article class="ltx_document"><p class="ltx_p">中文，a page.</p></article>'
            (d / "source.html").write_bytes(page.encode(locale.getpreferredencoding(False)))
            (d / "meta.json").write_text(json.dumps({"id": pid}), encoding="utf-8")
            doc = store.parsed(pid)
            words = "".join(t["t"] for u in doc["units"].values() for t in u["toks"])   # (one token per character)
            self.assertIn("中文", words)
        finally:
            store.DATA = old


if __name__ == "__main__":
    unittest.main()
