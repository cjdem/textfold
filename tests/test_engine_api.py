"""The MinerU cloud API's output as structured content (engine._structured): pages of blocks, boxes 0-1, the types
pdfdoc reads. Nothing here calls the API: the zip's own JSON is stood in.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import engine, models, store


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

    def test_v2_becomes_reader_blocks(self):
        sc = engine._structured(self.folder("x_content_list_v2.json", V2), "pdf")
        self.assertEqual(sc["metadata"]["file_suffix"], "pdf")
        self.assertEqual([p["page_idx"] for p in sc["pages"]], [0, 1])
        first, second = sc["pages"][0]["blocks"], sc["pages"][1]["blocks"]
        # the title of the first page is the document's; its box is 0-1 of the page
        self.assertEqual(first[0]["type"], "doc_title")
        self.assertEqual(first[0]["content"], "A paper")
        self.assertEqual(first[0]["bbox"], [0.07, 0.232, 0.766, 0.288])
        # a run of the page's words (a header is kept as MinerU's, which pdfdoc drops)
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
        old = store.DATA
        try:
            store.DATA = Path(tempfile.mkdtemp())
            pid = "web-oldpage"
            d = store.pdir(pid)
            d.mkdir(parents=True)
            page = '<article class="ltx_document"><p class="ltx_p">中文，a page.</p></article>'
            (d / "source.html").write_bytes(page.encode("gbk"))   # (the old writer's encoding, whatever this computer's)
            (d / "meta.json").write_text(json.dumps({"id": pid}), encoding="utf-8")
            with mock.patch.object(store, "codepage", return_value="gbk"):
                doc = store.parsed(pid)
            words = "".join(t["t"] for u in doc["units"].values() for t in u["toks"])   # (one token per character)
            self.assertIn("中文", words)
            self.assertTrue((d / "source.html").read_bytes().startswith(page[:4].encode("ascii")))   # (left as it was)
            self.assertRaises(UnicodeDecodeError, (d / "source.html").read_bytes().decode, "utf-8")
        finally:
            store.DATA = old


class TempSettings(unittest.TestCase):
    """A settings file of this test's own: no real ~/.textfold, and no old home to copy it from."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.saved = (models.SETTINGS, models.OLD_HOMES)
        models.SETTINGS = Path(self.tmp.name) / "settings.json"
        models.OLD_HOMES = []
        self.addCleanup(self._restore)

    def _restore(self):
        models.SETTINGS, models.OLD_HOMES = self.saved


class ApiOnly(TempSettings):
    def test_status_describes_the_api_not_a_local_install(self):
        st = engine.status()
        self.assertEqual(set(st), {"api", "service", "version", "base", "official", "baseOk", "tiers"})
        self.assertEqual((st["service"], st["version"]), ("MinerU API", "v4"))
        self.assertEqual((st["base"], st["official"], st["baseOk"]), (models.MINERU_API, models.MINERU_API, True))
        self.assertNotIn("installed", st)
        self.assertNotIn("path", st)

    def test_a_key_is_one_printable_word(self):
        self.assertTrue(engine.key_ok("abc-123"))
        self.assertFalse(engine.key_ok(""))
        self.assertFalse(engine.key_ok("two words"))
        self.assertFalse(engine.key_ok("line\nbreak"))


class BaseAddress(TempSettings):
    """`mineru_api_url`: the setting, its one official default, and the calls that use it. Nothing here opens a socket."""

    def test_a_base_is_http_or_https_with_a_host_and_no_trailing_slash(self):
        self.assertEqual(engine.base_ok("https://mineru.net/api/v4"), "https://mineru.net/api/v4")
        self.assertEqual(engine.base_ok("https://mineru.net/api/v4/"), "https://mineru.net/api/v4")
        self.assertEqual(engine.base_ok("  http://127.0.0.1:8080/api/v4/  "), "http://127.0.0.1:8080/api/v4")
        self.assertEqual(engine.base_ok("https://gateway.example/"), "https://gateway.example")
        self.assertEqual(engine.base_ok("http://[::1]:8080/api/v4"), "http://[::1]:8080/api/v4")

    def test_a_base_that_could_not_be_called_is_refused(self):
        for bad in ("", "   ", None, 42, "mineru.net/api/v4", "ftp://mineru.net/api/v4", "https://", "https:mineru.net",
                    "https://mineru.net/api/v4?q=1", "https://mineru.net/api/v4?", "https://mineru.net/api/v4#",
                    "https://mineru.net/api/v4#x", "https://user:pass@mineru.net/api/v4",
                    "https://@mineru.net/api/v4", "https://mineru.net:bad/api/v4", "https://mineru.net/api v4"):
            self.assertEqual(engine.base_ok(bad), "", bad)

    def test_the_effective_base_is_the_setting_or_the_official_one(self):
        self.assertEqual(engine.api_base(), models.MINERU_API)   # (no file: the official base)
        models.update_settings(lambda s: s.update(mineru_api_url=" https://proxy.example/api/v4/ "))
        self.assertEqual(engine.api_base(), "https://proxy.example/api/v4")
        models.update_settings(lambda s: s.update(mineru_api_url=""))
        self.assertEqual(engine.api_base(), models.MINERU_API)
        models.update_settings(lambda s: s.update(mineru_api_url=None))
        self.assertEqual(engine.api_base(), models.MINERU_API)   # (the file's null: no value, official)
        models.update_settings(lambda s: s.update(mineru_api_url="ftp://proxy.example"))
        with self.assertRaises(RuntimeError) as cm:
            engine.api_base()
        self.assertEqual(str(cm.exception), "bad-mineru-url")

    def test_a_call_goes_to_the_configured_base(self):
        models.update_settings(lambda s: s.update(mineru_api_key="k", mineru_api_url="https://proxy.example/v4/"))
        seen = {}

        class Reply:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b'{"code": 0, "data": {}}'

        def urlopen(req, timeout):
            seen["url"], seen["auth"] = req.full_url, req.get_header("Authorization")
            return Reply()

        with mock.patch.object(engine.urllib.request, "urlopen", side_effect=urlopen):
            self.assertEqual(engine._api("/file-urls/batch", {}), {"code": 0, "data": {}})
        self.assertEqual(seen["url"], "https://proxy.example/v4/file-urls/batch")
        self.assertEqual(seen["auth"], "Bearer k")

    def test_an_unusable_saved_base_fails_before_a_socket(self):
        models.update_settings(lambda s: s.update(mineru_api_key="k", mineru_api_url="ftp://proxy.example"))
        with mock.patch.object(engine.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(RuntimeError) as cm:
                engine._api("/file-urls/batch", {})
        self.assertEqual(str(cm.exception), "bad-mineru-url")
        urlopen.assert_not_called()
        st = engine.status()
        self.assertEqual((st["base"], st["baseOk"]), ("ftp://proxy.example", False))

    def test_a_non_text_saved_base_is_refused_and_reported(self):
        models.update_settings(lambda s: s.update(mineru_api_url=42))
        with self.assertRaises(RuntimeError) as cm:
            engine.api_base()
        self.assertEqual(str(cm.exception), "bad-mineru-url")
        st = engine.status()
        self.assertEqual((st["base"], st["baseOk"]), ("42", False))
        json.dumps(st, ensure_ascii=False).encode("utf-8")   # (the page's payload can still be sent)

    def test_a_hand_edited_unencodable_base_does_not_break_the_payload(self):
        Path(models.SETTINGS).write_text(json.dumps({"use_thoughtdag_env": False, "mineru_api_url": "\ud800"}),
                                        encoding="utf-8")
        with self.assertRaises(RuntimeError):
            engine.api_base()
        st = engine.status()
        self.assertFalse(st["baseOk"])
        self.assertEqual(engine.base_ok(st["base"]), "")   # (the shown value cannot be saved as a truncated address)
        json.dumps(st, ensure_ascii=False).encode("utf-8")   # (the settings page that fixes it can still open)

    def test_a_conversion_keeps_the_base_it_started_with(self):
        f = Path(self.tmp.name) / "paper.pdf"
        f.write_bytes(b"%PDF-1.7\n")
        with mock.patch.object(engine, "api_key", return_value="k"), \
             mock.patch.object(engine, "api_base", side_effect=["https://a.example/v4", "https://b.example/v4"]) as base, \
             mock.patch.object(engine, "_convert_api", return_value="done") as convert:
            self.assertEqual(engine.convert(f, Path(self.tmp.name) / "out"), "done")
        self.assertEqual(convert.call_args.args[-1], "https://a.example/v4")
        self.assertEqual(base.call_count, 1)

    def test_a_poll_keeps_the_conversions_base(self):
        class Stop:
            def wait(self, seconds): return False

        row = {"file_name": "paper.pdf", "state": "done", "full_zip_url": "https://z"}
        reply = {"code": 0, "data": {"extract_result": [row]}}
        with mock.patch.object(engine, "_api", return_value=reply) as api:
            self.assertEqual(engine._api_wait("batch1", "paper.pdf", lambda line: None, Stop(), "https://a.example/v4"),
                             row)
        self.assertEqual(api.call_args.kwargs["base"], "https://a.example/v4")

    def test_an_upload_url_keeps_its_scheme_and_port(self):
        f = Path(self.tmp.name) / "paper.pdf"
        f.write_bytes(b"data")
        for url, name, args in (("https://upload.example/put", "HTTPSConnection", ("upload.example", None)),
                                ("http://127.0.0.1:8080/put", "HTTPConnection", ("127.0.0.1", 8080))):
            with mock.patch(f"http.client.{name}") as cls:
                conn = cls.return_value
                conn.getresponse.return_value.status = 200
                conn.getresponse.return_value.read.return_value = b""
                engine._put(url, f)
            cls.assert_called_once_with(*args, timeout=300)
            conn.request.assert_called_once_with("PUT", "/put", body=b"data")


if __name__ == "__main__":
    unittest.main()
