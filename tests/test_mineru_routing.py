"""PDFs go straight to MinerU; only TextFold's own Office/E-book/CSV/HTML readers stay local."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import engine, server, store


class PdfRouting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_a_text_pdf_goes_to_mineru_not_a_local_reader(self):
        jobs = mock.Mock()
        jobs.convert.return_value = {"id": "mineru"}
        with mock.patch.object(engine, "available", return_value=True):
            reply, code = server.take_pdf(jobs, b"%PDF-1.7\n% text that could be read locally\n",
                                          {"X-Name": "paper.pdf", "X-Lang": "en"})
        self.assertEqual((reply, code), ({"job": {"id": "mineru"}, "via": "pdf"}, 200))
        jobs.convert.assert_called_once()
        jobs.submit.assert_not_called()
        self.assertTrue(any((store.DATA / "uploads").iterdir()))

    def test_a_pdf_with_an_online_reference_still_goes_to_mineru(self):
        jobs = mock.Mock()
        jobs.convert.return_value = {"id": "mineru"}
        with mock.patch.object(engine, "available", return_value=True):
            reply, code = server.take_pdf(jobs, b"%PDF-1.7\n",
                                          {"X-Name": "paper.pdf", "X-Lang": "en",
                                           "X-Refs": '["2201.11903", "10.1234/example"]'})
        self.assertEqual((reply, code), ({"job": {"id": "mineru"}, "via": "pdf"}, 200))
        jobs.convert.assert_called_once()
        jobs.submit.assert_not_called()

    def test_the_same_bytes_are_the_same_paper(self):
        """The landing reads a file's pid before uploading it: the same bytes must be the same paper, one job per upload.

        The browser (app.js `filePid`) copies this name to skip a duplicate before uploading. The exact name is pinned,
        so a change here fails the test rather than silently letting the browser's pre-check stop matching.
        """
        jobs = mock.Mock()
        jobs.convert.return_value = {"id": "mineru"}
        headers = {"X-Name": "paper.pdf", "X-Lang": "en"}
        data = b"%PDF-1.7\nsame\n"
        with mock.patch.object(engine, "available", return_value=True):
            server.take_pdf(jobs, data, headers)
            server.take_pdf(jobs, data, headers)
            server.take_pdf(jobs, b"%PDF-1.7\nother\n", headers)
        pids = [c.args[0] for c in jobs.convert.call_args_list]
        self.assertEqual(len(pids), 3)
        self.assertEqual(pids[0], "pdf-" + hashlib.sha256(data).hexdigest()[:16])
        self.assertEqual(pids[0], pids[1])   # (a second file of the same bytes is skipped in the browser)
        self.assertNotEqual(pids[0], pids[2])

    def test_an_office_file_is_named_by_its_bytes_too(self):
        """The browser's other branch (doc-) is pinned as well: an Office file of the same bytes is the same paper."""
        jobs = mock.Mock()
        jobs.submit.return_value = {"id": "local"}
        data = b"<html><body><p>same bytes</p></body></html>"
        with mock.patch.object(server.office, "reads", return_value=True), \
             mock.patch.object(server.office, "save"):
            reply, code = server.take_file(jobs, data, {"X-Name": "same.html", "X-Lang": "en"})
        self.assertEqual((code, reply.get("via")), (200, "file"))
        self.assertEqual(jobs.submit.call_args.args[0], "doc-" + hashlib.sha256(data).hexdigest()[:16])

    def test_a_pdf_without_a_key_is_refused_without_leaving_a_file(self):
        with mock.patch.object(engine, "available", return_value=False):
            reply, code = server.take_pdf(mock.Mock(), b"%PDF-1.7\n",
                                          {"X-Name": "paper.pdf", "X-Lang": "en"})
        self.assertEqual((code, reply["error"]), (409, "needs-mineru-key"))
        self.assertFalse(any((store.DATA / "uploads").iterdir()))

    def test_an_office_file_uses_its_local_reader_before_mineru(self):
        jobs = mock.Mock()
        jobs.submit.return_value = {"id": "local"}
        office = server.office
        with mock.patch.object(office, "reads", return_value=True), \
             mock.patch.object(office, "save") as save, \
             mock.patch.object(engine, "readable", return_value=True), \
             mock.patch.object(engine, "convert") as convert:
            reply, code = server.take_file(jobs, b"docx bytes", {"X-Name": "paper.docx", "X-Lang": "en"})
        self.assertEqual((code, reply.get("via")), (200, "file"))
        save.assert_called_once()
        convert.assert_not_called()
        jobs.convert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
