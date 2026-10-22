"""A document's name in the library, on a server of its own (its own HOME and data folder, no model): the name reaches
the list, the page's title and the reader's data, the page is drawn again when it changes, an emptied name gives the
title back, a delete keeps the name with the place so the Undo brings both back, and an unknown document is refused.

Run from the repo root:
    python -m unittest discover tests
"""
import http.client
import json
import os
import re
import site
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from textfold import build, library, server, store

ROOT = Path(__file__).resolve().parent.parent


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class PaperName(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        home = Path(cls.tmp.name) / "home"
        home.mkdir()
        cls.data = Path(cls.tmp.name) / "data"
        cls.port = free_port()
        env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home), "LOCALAPPDATA": str(home / "AppData" / "Local"),
               "TEXTFOLD_DATA": str(cls.data), "TEXTFOLD_NO_MODELS": "1", "PYTHONUSERBASE": site.getuserbase()}
        cls.proc = subprocess.Popen([sys.executable, "-m", "textfold", "serve", "--port", str(cls.port)], cwd=ROOT, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(cls.proc.wait, timeout=10)   # (reverse order: terminate, then wait)
        cls.addClassCleanup(cls.proc.terminate)
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{cls.port}/api/papers", timeout=1)
                break
            except OSError:
                time.sleep(0.1)

    def call(self, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        c.request("POST" if data is not None else "GET", path, body=data,
                  headers={"Content-Type": "application/json"} if data is not None else {})
        r = c.getresponse()
        return r.status, json.loads(r.read())

    def html(self, path, body):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        c.request("POST", path, body=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        return r.read().decode("utf-8")

    def page(self, pid):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        c.request("GET", f"/p/{pid}")
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        return r.read().decode("utf-8")

    def test_the_name_reaches_the_list_and_the_page(self):
        _, body = self.call("/api/import", {"name": "scan-0042.md", "text": "# scan 0042\n\nA paragraph of the scan.\n"})
        pid = body["paper"]
        before = self.page(pid)   # (rendered and kept before the name: it must be drawn again)
        self.assertEqual(re.search(r"<title>(.*?)</title>", before).group(1), "scan 0042")
        code, listed = self.call("/api/papers/name", {"paper": pid, "name": "  Smith  2024 review "})
        row = next(p for p in listed if p["id"] == pid)
        self.assertEqual((code, row["name"], row["title"]), (200, "Smith 2024 review", "scan 0042"))
        page = self.page(pid)
        self.assertEqual(re.search(r"<title>(.*?)</title>", page).group(1), "Smith 2024 review")
        data = json.loads(re.search(r'<script type="application/json" id="paper-data">(.*?)</script>', page, re.S).group(1))
        self.assertEqual((data["meta"]["name"], data["meta"]["title"]), ("Smith 2024 review", "scan 0042"))
        # cleared: its own title again, and the page is drawn anew
        self.call("/api/papers/name", {"paper": pid, "name": ""})
        page = self.page(pid)
        self.assertEqual(re.search(r"<title>(.*?)</title>", page).group(1), "scan 0042")
        data = json.loads(re.search(r'<script type="application/json" id="paper-data">(.*?)</script>', page, re.S).group(1))
        self.assertNotIn("name", data["meta"])
        self.assertEqual(self.call("/api/papers/name", {"paper": "md-none-0000", "name": "x"})[0], 404)

    def test_the_export_carries_the_name(self):
        _, body = self.call("/api/import", {"name": "exported.md", "text": "# exported\n\nA paragraph for the export.\n"})
        pid = body["paper"]
        self.call("/api/papers/name", {"paper": pid, "name": "The exported one"})
        html = self.html("/api/export", {"paper": pid, "lang": "en", "langs": "current", "kinds": ["note"]})
        self.assertEqual(re.search(r"<title>(.*?)</title>", html).group(1), "The exported one")
        data = json.loads(re.search(r'<script type="application/json" id="paper-data">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(data["meta"]["name"], "The exported one")

    def test_a_delete_and_its_undo_keep_the_name(self):
        _, body = self.call("/api/import", {"name": "named.md", "text": "# named\n\nA paragraph with a name.\n"})
        pid = body["paper"]
        self.call("/api/papers/name", {"paper": pid, "name": "Kept through the trash"})
        code, r = self.call("/api/papers/delete", {"papers": [pid]})
        self.assertEqual((code, r["deleted"]), (200, [pid]))
        code, r = self.call("/api/papers/restore", {"papers": [pid]})
        self.assertEqual((code, r["restored"]), (200, [pid]))
        row = next(p for p in r["papers"] if p["id"] == pid)
        self.assertEqual(row["name"], "Kept through the trash")
        self.assertEqual(re.search(r"<title>(.*?)</title>", self.page(pid)).group(1), "Kept through the trash")


class NameAgainstDelete(unittest.TestCase):
    """A name and a delete of the same document at once: the delete holds store.LOCK while its folder moves, and the
    name route takes the same lock, so no name is written for a document whose folder is going away (or went a moment
    ago), and a name written first travels into the trash with its place."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)
        self.pid = "md-race-0001"
        store.pdir(self.pid).mkdir(parents=True)
        (store.pdir(self.pid) / "meta.json").write_text('{"title": "race"}', encoding="utf-8")

    def test_a_name_cannot_outlive_a_delete_it_raced(self):
        entered, release, out = threading.Event(), threading.Event(), {}
        real = store.trash

        def paused(pid, kept):   # (the window between the library's record and the folder's move)
            entered.set()
            release.wait(5)
            return real(pid, kept)

        with mock.patch.object(store, "trash", paused):
            gone = threading.Thread(target=server.trash_paper, args=(self.pid,))
            gone.start()
            self.assertTrue(entered.wait(5))

            def name_it():
                try:
                    server.name_paper(self.pid, "Late name")
                except KeyError:
                    out["refused"] = True

            named = threading.Thread(target=name_it)
            named.start()
            time.sleep(0.2)
            out["blocked"] = named.is_alive()   # (it waits: the delete has the lock until its folder has moved)
            release.set()
            gone.join(5)
            named.join(5)

        self.assertTrue(out.get("blocked"), "the name was not kept waiting for the delete")
        self.assertTrue(out.get("refused"), "the name was written for a document being deleted")
        self.assertIsNone(library.name_of(self.pid))
        self.assertFalse(store.pdir(self.pid).exists())

    def test_a_name_written_before_the_delete_goes_with_it(self):
        server.name_paper(self.pid, "Named first")
        self.assertEqual(library.name_of(self.pid), "Named first")
        server.trash_paper(self.pid)
        self.assertIsNone(library.name_of(self.pid))
        place = next((store.DATA / "papers" / ".trash").glob(f"{self.pid}-*/library.json"))
        self.assertEqual(json.loads(place.read_text(encoding="utf-8"))["name"], "Named first")   # (the Undo has it)


class BuildExport(unittest.TestCase):
    def test_the_cli_export_carries_the_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(store, "DATA", Path(tmp)), \
                    mock.patch.object(build.store, "assemble", return_value={"meta": {"title": "scan 0042"}}), \
                    mock.patch.object(build.library, "name_of", return_value="Smith 2024 review"), \
                    mock.patch.object(build, "page", return_value="<html>") as page:
                out = build.export("md-export-0001")
                page.assert_called_once()
                self.assertEqual(page.call_args.args[0]["meta"]["name"], "Smith 2024 review")
                self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
