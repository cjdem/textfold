"""New imports of RTF, OpenDocument and old Office files are refused with their own message, from the
landing and from `textfold get`; a PDF renamed to one of those extensions still opens as a PDF.

The kinds stay known to the engine, so a document converted before the rule still opens, and can be
converted again where the engine reads it. Zotero prefers an attachment of a kind still imported, and
falls back to a DOI before offering a legacy-only file.

Run from the repo root:
    python -m unittest discover tests
"""
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

from textfold import __main__ as cli
from textfold import engine, fold, pdfdoc, pipeline, server, store, zotero

LEGACY = ("doc", "ppt", "xls", "rtf", "odt", "ods", "odp")


def cli_args(ref):
    return Namespace(ref=ref, lang="en", no_generate=True, json=False, level="full", section=None)


class LegacyImports(unittest.TestCase):
    def test_each_legacy_kind_is_refused_with_its_own_message(self):
        with tempfile.TemporaryDirectory() as folder:
            old = store.DATA
            store.DATA = Path(folder)
            try:
                for ext in LEGACY:
                    reply, code = server.take_file(None, b"not a pdf", {"X-Name": f"paper.{ext}", "X-Lang": "en"})
                    self.assertEqual((reply, code), ({"error": "legacy-format"}, 400), ext)
                self.assertFalse((store.DATA / "uploads").exists())   # (refused before anything is written)
            finally:
                store.DATA = old

    def test_the_extension_is_matched_case_insensitively(self):
        reply, code = server.take_file(None, b"not a pdf", {"X-Name": "Paper.ODT", "X-Lang": "en"})
        self.assertEqual((reply, code), ({"error": "legacy-format"}, 400))

    def test_the_kinds_stay_known_for_stored_documents(self):
        for ext in LEGACY:
            self.assertEqual(engine.kind_of(f"paper.{ext}"), ext)
            self.assertIn(ext, engine.FILES)
            self.assertIn(ext, engine.LEGACY)

    def test_the_kinds_the_reader_still_takes_are_not_legacy(self):
        for ext in ("docx", "pptx", "xlsx", "csv", "tsv", "html", "htm", "mhtml", "mht", "epub", "ofd", "pdf"):
            self.assertNotIn(ext, engine.LEGACY, ext)
            self.assertEqual(engine.kind_of(f"paper.{ext}"), ext)

    def test_a_pdf_named_odt_still_goes_to_the_pdf_route(self):
        with mock.patch.object(server, "take_pdf", return_value=({"paper": "p"}, 200)) as pdf:
            reply, code = server.take_file(None, b"%PDF-1.7", {"X-Name": "paper.odt", "X-Lang": "en"})
        self.assertEqual((reply, code), ({"paper": "p"}, 200))
        pdf.assert_called_once()

    def test_a_legacy_file_converted_before_still_opens(self):
        with tempfile.TemporaryDirectory() as folder:
            old = store.DATA
            store.DATA = Path(folder)
            try:
                data, ext = b"converted before the rule", "odt"
                pid = pdfdoc.pid_of(data, ext)
                d = store.pdir(pid)
                d.mkdir(parents=True)
                (d / "meta.json").write_text("{}", encoding="utf-8")
                jobs = mock.Mock()
                jobs.submit.return_value = {"id": "j1"}
                reply, code = server.take_file(jobs, data, {"X-Name": "paper.odt", "X-Lang": "en"})
                self.assertEqual((reply.get("via"), code), ("file", 200))
                jobs.submit.assert_called_once_with(pid, "en", False)
            finally:
                store.DATA = old


class LegacyCli(unittest.TestCase):
    def run_get(self, ref):
        with mock.patch.object(cli, "_say"), \
             mock.patch.object(pipeline, "generate") as generate, \
             mock.patch.object(fold, "document", return_value={}), \
             mock.patch.object(fold, "markdown", return_value=""):
            code = cli.get(cli_args(ref))
        return code, generate

    def test_get_refuses_a_new_legacy_file(self):
        with tempfile.TemporaryDirectory() as folder:
            old = store.DATA
            store.DATA = Path(folder)
            try:
                f = Path(folder) / "paper.odt"
                f.write_bytes(b"not a zip")
                with mock.patch.object(cli, "_say") as say:
                    code = cli.get(cli_args(str(f)))
                self.assertEqual(code, 2)
                self.assertIn("no longer opens", say.call_args.args[0])
            finally:
                store.DATA = old

    def test_get_allows_a_legacy_file_converted_before(self):
        with tempfile.TemporaryDirectory() as folder:
            old = store.DATA
            store.DATA = Path(folder)
            try:
                f = Path(folder) / "paper.odt"
                data = b"converted before the rule"
                f.write_bytes(data)
                d = store.pdir(pdfdoc.pid_of(data, "odt"))
                d.mkdir(parents=True)
                (d / "meta.json").write_text("{}", encoding="utf-8")
                (d / "source.html").write_text("<p>Kept.</p>", encoding="utf-8")
                code, generate = self.run_get(str(f))
                self.assertEqual(code, 0)
                self.assertTrue(generate.called)
            finally:
                store.DATA = old

    def test_get_reads_a_pdf_named_odt_as_a_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            old = store.DATA
            store.DATA = Path(folder)
            try:
                f = Path(folder) / "paper.odt"
                f.write_bytes(b"%PDF-1.7\nnot really a pdf")
                with mock.patch.object(engine, "readable", return_value=False), \
                     mock.patch("textfold.pdftext.save", return_value=True):
                    code, generate = self.run_get(str(f))
                self.assertEqual(code, 0)
                self.assertTrue(generate.called)
            finally:
                store.DATA = old


class ZoteroOrder(unittest.TestCase):
    def test_a_supported_attachment_comes_before_a_legacy_one(self):
        kids = [{"data": {"itemType": "attachment", "contentType": "application/vnd.oasis.opendocument.text",
                          "linkMode": "imported_file", "key": "ABCD2345"}},
                {"data": {"itemType": "attachment", "contentType": "text/html",
                          "linkMode": "imported_file", "key": "EFGH6789"}}]
        with mock.patch.object(zotero, "_all", return_value=kids):
            out = zotero._attachments("lib", "ITEM2345")
        self.assertEqual([a["contentType"] for a in out],
                         ["text/html", "application/vnd.oasis.opendocument.text"])

    def test_a_legacy_only_file_yields_to_the_doi(self):
        item = {"arxiv": "", "doi": "10.1234/xyz", "title": "A paper"}
        att = {"key": "ABCD2345", "contentType": "application/msword", "linkMode": "imported_file"}
        with tempfile.NamedTemporaryFile(suffix=".doc") as f, \
             mock.patch.object(zotero, "_check"), \
             mock.patch.object(zotero, "_get", return_value=({}, None)), \
             mock.patch.object(zotero, "item_of", return_value=item), \
             mock.patch.object(zotero, "_attachments", return_value=[att]), \
             mock.patch.object(zotero, "_file", return_value=Path(f.name)):
            got = zotero.read("lib", "ITEM2345")
        self.assertEqual(got["ref"], "10.1234/xyz")


if __name__ == "__main__":
    unittest.main()
