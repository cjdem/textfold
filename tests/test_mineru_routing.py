"""PDFs go straight to MinerU; only TextFold's own Office/E-book/CSV/HTML readers stay local."""
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
