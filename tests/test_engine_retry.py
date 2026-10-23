"""A MinerU conversion that loses its connection resumes where it stopped: its batch, its upload, its download and
its parsed output are kept, and importing the same file again continues the conversion instead of uploading the paper a
second time. Nothing here touches the network or MinerU: the API, the signed upload and the zip download are stood in.

Run from the repo root:
    python -m unittest discover tests
"""
import io
import json
import tempfile
import threading
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock

from textfold import engine

PDF = b"%PDF-1.7\n"
SC = {"pages": [{"page_idx": 0, "blocks": [{"type": "text", "content": "The words."}]}],
      "metadata": {"file_suffix": "pdf", "producer": {"name": "MinerU API"}, "document": {}}}
NO_TEXT = {"pages": [{"page_idx": 0, "blocks": []}],
           "metadata": {"file_suffix": "pdf", "producer": {"name": "MinerU API"}, "document": {}}}


def done(name, url="https://zip.example/1", state="done"):
    return {"code": 0, "data": {"extract_result": [{"file_name": name, "state": state, "full_zip_url": url}]}}


class Fake:
    """MinerU's API, the signed upload and the download, stood in. `creates` and `answers` are queues of answers, one
    per create or poll call (an exception is raised, a dict returned); an empty queue is the ordinary success."""
    name = "paper.pdf"

    def __init__(self):
        self.created, self.polls, self.puts, self.gets = [], [], [], []
        self.creates, self.answers, self.get_answers = [], [], []
        self.put_error = None
        self.n = 0

    def api(self, path, body=None, base=None):
        if path == "/file-urls/batch":
            self.created.append(body)
            if self.creates:
                return self._take(self.creates)
            self.n += 1
            return {"code": 0, "data": {"batch_id": f"batch{self.n}",
                                        "file_urls": [f"https://upload.example/{self.n}"]}}
        self.polls.append(path)
        if self.answers:
            return self._take(self.answers)
        return done(self.name)

    @staticmethod
    def _take(queue):
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def put(self, url, file):
        self.puts.append(url)
        if self.put_error:
            raise self.put_error

    def get(self, url, dest):
        self.gets.append(url)
        if self.get_answers:
            answer = self.get_answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
        Path(dest).write_bytes(b"PK")


class Stop:
    def __init__(self):
        self.stopped = False

    def wait(self, seconds):
        return self.stopped

    def is_set(self):
        return self.stopped


class Conversion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.pdf = self.dir / "paper.pdf"
        self.pdf.write_bytes(PDF)
        self.out = self.dir / "out"
        self.fake = Fake()
        self.stop = Stop()
        self.log = []
        patches = [
            mock.patch.object(engine, "api_key", return_value="k"),
            mock.patch.object(engine, "api_base", return_value="https://api.example/v4"),
            mock.patch.object(engine, "_api", side_effect=self.fake.api),
            mock.patch.object(engine, "_put", side_effect=self.fake.put),
            mock.patch.object(engine, "_get", side_effect=self.fake.get),
            mock.patch.object(engine, "_unzip", side_effect=lambda z, out: Path(z).unlink()),
            mock.patch.object(engine, "_structured", side_effect=lambda folder, ext: SC),
            mock.patch.object(engine, "_pause", side_effect=lambda stop, seconds: False),
            mock.patch.object(engine, "LAND_GRACE", 0),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def convert(self):
        return engine.convert(self.pdf, self.out, "fast", log=self.log.append, stop=self.stop)

    def state(self):
        return json.loads((self.out / engine.STATE_NAME).read_text(encoding="utf-8"))

    def test_a_poll_that_loses_the_connection_retries_the_same_batch(self):
        self.fake.answers = [urllib.error.URLError(ConnectionResetError()), urllib.error.URLError(TimeoutError()),
                             done(self.fake.name)]
        self.convert()
        self.assertEqual(len(self.fake.created), 1)
        self.assertEqual(len(self.fake.puts), 1)
        self.assertEqual(self.fake.polls, ["/extract-results/batch/batch1"] * 3)
        self.assertTrue((self.out / "structured_content.json").exists())
        self.assertTrue(any("the poll failed" in line for line in self.log))
        self.assertFalse(any("Token" in line or "https://upload" in line for line in self.log))

    def test_a_task_the_api_no_longer_has_is_submitted_again(self):
        self.fake.answers = [{"code": -60012, "msg": "task not found or expire"}, done(self.fake.name)]
        self.convert()
        self.assertEqual(len(self.fake.created), 2)
        self.assertEqual(len(self.fake.puts), 2)

    def test_an_upload_whose_answer_was_lost_is_not_sent_again_when_the_batch_has_it(self):
        self.fake.put_error = urllib.error.URLError(ConnectionResetError())
        self.fake.answers = [done(self.fake.name, state="pending"), done(self.fake.name)]
        self.convert()
        self.assertEqual(len(self.fake.created), 1)
        self.assertEqual(len(self.fake.puts), 3)   # the tries, and no fourth after the batch said it has the file
        self.assertEqual(set(self.fake.polls), {"/extract-results/batch/batch1"})

    def test_an_upload_that_did_not_land_is_sent_to_a_new_batch(self):
        self.fake.put_error = urllib.error.URLError(ConnectionResetError())
        self.fake.answers = [done(self.fake.name, state="waiting-file"), done(self.fake.name, state="waiting-file")]
        with self.assertRaises(engine.Resumable):
            self.convert()
        self.assertEqual(len(self.fake.created), 2)
        self.assertEqual(len(self.fake.puts), 6)
        state = self.state()
        self.assertEqual((state["batch_id"], state["uploaded"]), ("", False))

    def test_a_batch_whose_file_never_arrived_is_uploaded_to_again(self):
        self.fake.answers = [{"code": -60011, "msg": "Failed to get valid file"}, done(self.fake.name)]
        self.convert()
        self.assertEqual(len(self.fake.created), 1)
        self.assertEqual(len(self.fake.puts), 2)

    def test_a_service_error_code_is_waited_out(self):
        self.fake.answers = [{"code": -10001, "msg": "Service error"}, done(self.fake.name)]
        self.convert()
        self.assertEqual(len(self.fake.created), 1)
        self.assertEqual(len(self.fake.polls), 2)

    def test_an_upload_the_api_could_not_read_is_sent_once_more(self):
        self.fake.creates = [{"code": -60003, "msg": "File read failure"}]
        self.convert()
        self.assertEqual(len(self.fake.created), 2)
        self.assertEqual(len(self.fake.puts), 1)

    def test_a_5xx_upload_is_tried_again_on_its_url(self):
        errors = [engine._UploadRejected(503), engine._UploadRejected(503)]

        def put(url, file):
            self.fake.puts.append(url)
            if errors:
                raise errors.pop(0)

        with mock.patch.object(engine, "_put", side_effect=put):
            self.convert()
        self.assertEqual(len(self.fake.created), 1)
        self.assertEqual(len(self.fake.puts), 3)

    def test_a_resume_that_cannot_reach_the_batch_keeps_it(self):
        self.fake.put_error = urllib.error.URLError(ConnectionResetError())
        self.fake.answers = [urllib.error.URLError(ConnectionResetError())]   # (the one poll of the empty grace)
        with self.assertRaises(engine.Resumable):
            self.convert()
        state = self.state()
        self.assertEqual((state["batch_id"], state["uploaded"]), ("batch1", False))

        puts = len(self.fake.puts)
        self.fake.put_error = None
        self.fake.answers = [done(self.fake.name, state="pending"), done(self.fake.name)]
        self.convert()
        self.assertEqual(len(self.fake.puts), puts)   # the resumed attempt polls first, and does not re-upload
        self.assertEqual(len(self.fake.created), 1)

    def test_a_parsed_pass_is_finished_without_the_network(self):
        self.convert()
        state = self.state()
        state["stage"] = "parsed"
        (self.out / engine.STATE_NAME).write_text(json.dumps(state), encoding="utf-8")
        (self.out / "structured_content.json").unlink()
        counts = (len(self.fake.created), len(self.fake.polls), len(self.fake.puts), len(self.fake.gets))
        self.convert()
        self.assertEqual((len(self.fake.created), len(self.fake.polls), len(self.fake.puts), len(self.fake.gets)), counts)
        self.assertEqual(self.state()["stage"], "done")
        self.assertTrue((self.out / "structured_content.json").exists())

    def test_a_refused_result_is_not_resumed(self):
        self.fake.answers = [done(self.fake.name, state="failed")]
        with self.assertRaises(RuntimeError):
            self.convert()
        self.assertFalse((self.out / engine.STATE_NAME).exists())
        self.convert()
        self.assertEqual(len(self.fake.created), 2)

    def test_the_state_holds_no_key_or_signed_url(self):
        with mock.patch.object(engine, "api_key", return_value="SECRET-KEY"):
            self.convert()
        text = (self.out / engine.STATE_NAME).read_text(encoding="utf-8")
        self.assertNotIn("SECRET-KEY", text)
        self.assertNotIn("upload.example", text)
        self.assertNotIn("zip.example", text)
        self.assertNotIn("Authorization", text)

    def test_a_download_that_fails_is_tried_again(self):
        self.fake.get_answers = [urllib.error.URLError(ConnectionResetError()), urllib.error.URLError(TimeoutError())]
        self.convert()
        self.assertEqual(len(self.fake.gets), 3)
        self.assertEqual((len(self.fake.created), len(self.fake.puts)), (1, 1))

    def test_a_result_link_that_stopped_working_is_refreshed_from_the_batch(self):
        self.fake.answers = [done(self.fake.name, "https://zip.example/1"), done(self.fake.name, "https://zip.example/2")]
        self.fake.get_answers = [engine._DownloadGone("403")]
        self.convert()
        self.assertEqual(self.fake.gets, ["https://zip.example/1", "https://zip.example/2"])
        self.assertEqual(len(self.fake.polls), 2)

    def test_an_incomplete_zip_is_downloaded_again(self):
        patches = [zipfile.BadZipFile(), lambda z, out: Path(z).unlink()]
        with mock.patch.object(engine, "_unzip", side_effect=patches):
            self.convert()
        self.assertEqual(len(self.fake.gets), 2)
        self.assertEqual((len(self.fake.created), len(self.fake.puts)), (1, 1))

    def test_a_finished_conversion_is_not_run_again(self):
        self.convert()
        counts = (len(self.fake.created), len(self.fake.polls), len(self.fake.puts), len(self.fake.gets))
        self.convert()
        self.assertEqual((len(self.fake.created), len(self.fake.polls), len(self.fake.puts), len(self.fake.gets)), counts)
        self.assertEqual(self.state()["stage"], "done")

    def test_a_changed_file_does_not_resume_the_old_batch(self):
        self.convert()
        self.pdf.write_bytes(b"%PDF-1.7\nother paper\n")
        self.convert()
        self.assertEqual(len(self.fake.created), 2)

    def test_the_same_bytes_from_another_path_resume_the_batch(self):
        self.convert()
        created, puts = len(self.fake.created), len(self.fake.puts)
        state = self.state()
        state["stage"] = "uploaded"
        (self.out / engine.STATE_NAME).write_text(json.dumps(state), encoding="utf-8")
        (self.out / "structured_content.json").unlink()
        other = self.dir / "Attention.pdf"   # (the command line's path; the server's is uploads/<pid>.pdf)
        other.write_bytes(PDF)
        self.fake.answers = [done(self.fake.name)]   # (its row is matched by name, or by the batch's only row)
        engine.convert(other, self.out, "fast", log=self.log.append, stop=self.stop)
        self.assertEqual((len(self.fake.created), len(self.fake.puts)), (created, puts))
        self.assertTrue((self.out / "structured_content.json").exists())

    def test_a_stop_during_a_wait_ends_the_job(self):
        self.fake.answers = [urllib.error.URLError(ConnectionResetError())]

        def pause(stop, seconds):
            stop.stopped = True
            return True

        with mock.patch.object(engine, "_pause", side_effect=pause):
            with self.assertRaises(engine.Stopped):
                self.convert()
        self.assertEqual(len(self.fake.polls), 1)

    def test_a_bad_key_is_not_tried_again(self):
        self.fake.creates = [{"code": "A0211", "msg": "Token expired"}]
        with self.assertRaises(RuntimeError) as cm:
            self.convert()
        self.assertIn("Token expired", str(cm.exception))
        self.assertEqual(len(self.fake.created), 1)
        self.assertEqual(self.fake.puts, [])

    def test_an_http_refusal_is_not_tried_again(self):
        self.fake.creates = [urllib.error.HTTPError("https://api.example/v4/file-urls/batch", 401, "Unauthorized", {},
                                                    io.BytesIO(b""))]
        with self.assertRaises(urllib.error.HTTPError):
            self.convert()
        self.assertEqual(len(self.fake.created), 1)

    def test_a_scan_is_read_again_with_its_own_batch_and_that_batch_is_resumed(self):
        scanner = mock.patch.object(engine, "_structured", side_effect=[NO_TEXT, SC])
        scanner.start()
        self.addCleanup(scanner.stop)
        self.fake.answers = [done(self.fake.name)] + [urllib.error.URLError(ConnectionResetError())] * engine.MAX_MISSES
        with self.assertRaises(engine.Resumable):
            self.convert()
        self.assertEqual(len(self.fake.created), 2)
        self.assertTrue(self.fake.created[1]["files"][0]["is_ocr"])
        state = self.state()
        self.assertEqual((state["pass"], state["batch_id"]), (2, "batch2"))

        with mock.patch.object(engine, "_structured", side_effect=lambda folder, ext: SC):
            self.fake.answers = [done(self.fake.name, "https://zip.example/2")]
            self.convert()
        self.assertEqual((len(self.fake.created), len(self.fake.puts)), (2, 2))   # the first pass is not read again


class State(unittest.TestCase):
    """The state file two processes could write: the server and the command line convert the same folder."""

    def test_two_writers_leave_one_whole_state(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        errors = []

        def write(who):
            try:
                for n in range(30):
                    engine._state_save(out, {"v": engine.STATE_V, "who": who, "n": n})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write, args=(who,)) for who in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        state = json.loads((out / engine.STATE_NAME).read_text(encoding="utf-8"))
        self.assertIn(state["who"], ("a", "b"))


class Download(unittest.TestCase):
    """curl's answer as the download reads it: a 5xx on the link is waited out, a 403 is a dead link."""

    def get(self, status):
        result = mock.Mock(returncode=22, stdout=str(status), stderr="curl: (22) the requested URL returned error")
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(engine.shutil, "which", return_value="curl"), \
             mock.patch.object(engine.subprocess, "run", return_value=result):
            with self.assertRaises(Exception) as caught:
                engine._get("https://zip.example/x", Path(tmp) / "z")
        return caught.exception

    def test_a_5xx_is_tried_again_and_a_403_is_a_dead_link(self):
        self.assertIsInstance(self.get(503), engine._DownloadFailed)
        self.assertIsInstance(self.get(429), engine._DownloadFailed)
        self.assertIsInstance(self.get(403), engine._DownloadGone)
        self.assertIsInstance(self.get(404), engine._DownloadGone)

    def test_the_urllib_fallback_calls_every_4xx_a_dead_link(self):
        error = urllib.error.HTTPError("https://zip.example/x", 401, "Unauthorized", {}, io.BytesIO(b""))
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(engine.shutil, "which", return_value=None), \
             mock.patch.object(engine.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(engine._DownloadGone):
                engine._get("https://zip.example/x", Path(tmp) / "z")


class Server(unittest.TestCase):
    """What the conversion queue keeps when the engine stops for now, and what it removes when the file is refused."""

    def wait(self, job):
        import time
        deadline = time.monotonic() + 10
        while job["status"] not in ("error", "done", "stopped") and time.monotonic() < deadline:
            time.sleep(0.02)

    def test_a_lost_connection_keeps_the_folder_and_a_refusal_removes_it(self):
        from textfold import server, store
        old = store.DATA
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(setattr, store, "DATA", old)
        store.DATA = Path(tmp.name)
        jobs = server.Jobs()
        with mock.patch.object(server.engine, "convert", side_effect=engine.Resumable("the connection was lost")), \
             mock.patch.object(server.office, "reads", return_value=False):
            f = store.DATA / "uploads" / "pdf-a.pdf"
            f.parent.mkdir(parents=True)
            f.write_bytes(PDF)
            out = store.DATA / "uploads" / "pdf-a-fast"
            out.mkdir()
            job = jobs.convert("pdf-a", f, "paper.pdf", "en", tier="fast")
            self.wait(job)
        self.assertEqual(job["status"], "error")
        self.assertIn("connection was lost", job["error"])
        self.assertTrue(out.exists())

        with mock.patch.object(server.engine, "convert", side_effect=RuntimeError("the file was refused")), \
             mock.patch.object(server.office, "reads", return_value=False):
            f = store.DATA / "uploads" / "pdf-b.pdf"
            f.write_bytes(PDF)
            out = store.DATA / "uploads" / "pdf-b-fast"
            out.mkdir()
            job = jobs.convert("pdf-b", f, "paper.pdf", "en", tier="fast")
            self.wait(job)
        self.assertEqual(job["status"], "error")
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
