"""The library's delete and Undo routes on a server of its own (its own HOME and data folder, no model): several
documents deleted at once leave out the ones being generated and say which went, and they come back with the reader's
Undo in their folder and with their date; one alone still answers with the list, as before.

Run from the repo root:
    python -m unittest discover tests
"""
import http.client
import json
import os
import site
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from textfold import server

ROOT = Path(__file__).resolve().parent.parent


class WhichStay(unittest.TestCase):
    def test_being_generated_stay_and_a_card_draft_does_not(self):
        class Jobs:
            def list(self):
                return [{"pid": "a", "status": "running"}, {"pid": "b", "status": "queued", "kind": "card"},
                        {"pid": "c", "status": "done"}, {"pid": "d", "status": "running", "kind": "card"},
                        {"pid": "e", "status": "running", "kind": "convert"}]
        self.assertEqual(server.busy_deleting(Jobs()), {"a", "e"})


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LibraryRoutes(unittest.TestCase):
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

    def import_md(self, name):
        code, body = self.call("/api/import", {"name": f"{name}.md", "text": f"# {name}\n\nA paragraph for {name}.\n"})
        self.assertEqual(code, 200)
        return body["paper"]

    def test_several_deleted_at_once_and_brought_back(self):
        ids = [self.import_md(f"undo-{k}") for k in range(3)]
        code, f = self.call("/api/folders", {"op": "new", "name": "Undo box", "papers": ids[:2]})
        box = f["folders"][-1]["id"]
        before = {p["id"]: p for p in self.call("/api/papers")[1]}
        code, r = self.call("/api/papers/delete", {"papers": [ids[0], ids[1], "md-none-0000"]})
        self.assertEqual((code, r["deleted"], r["busy"], r["failed"]), (200, ids[:2], [], []))
        self.assertEqual({p["id"] for p in r["papers"]} & set(ids), {ids[2]})
        self.assertNotIn(ids[0], self.call("/api/folders")[1]["of"])
        self.assertTrue(any(d.name.startswith(ids[0]) for d in (self.data / "papers" / ".trash").iterdir()))
        code, r = self.call("/api/papers/restore", {"papers": ids[:2]})
        self.assertEqual((code, r["restored"]), (200, ids[:2]))
        rows = {p["id"]: p for p in r["papers"]}
        self.assertEqual((r["folders"]["of"][ids[0]], r["folders"]["of"][ids[1]]), (box, box))
        self.assertEqual(rows[ids[0]]["added"], before[ids[0]]["added"])   # (its date, not the day it came back)
        self.assertFalse((self.data / "papers" / ids[0] / "library.json").exists())
        self.assertEqual(self.call("/api/papers/restore", {"papers": ids[:2]})[1]["restored"], [])   # (nothing left there)

    def test_one_deleted_as_before(self):
        pid = self.import_md("single")
        code, listed_ = self.call("/api/papers/delete", {"paper": pid})
        self.assertEqual(code, 200)
        self.assertIsInstance(listed_, list)
        self.assertNotIn(pid, {p["id"] for p in listed_})
        self.assertEqual(self.call("/api/papers/delete", {"paper": pid})[0], 404)
        self.assertEqual(self.call("/api/papers/restore", {"papers": [pid]})[1]["restored"], [pid])

    def test_the_same_id_twice_is_deleted_once(self):
        pid = self.import_md("twice")
        code, r = self.call("/api/papers/delete", {"papers": [pid, pid]})
        self.assertEqual((code, r["deleted"], r["failed"]), (200, [pid], []))
        self.assertEqual(self.call("/api/papers/restore", {"papers": [pid]})[1]["restored"], [pid])

    def test_a_restore_of_what_is_not_there(self):
        self.assertEqual(self.call("/api/papers/restore", {"papers": ["md-none-0001"]})[1]["restored"], [])
        self.assertEqual(self.call("/api/papers/restore", {})[1]["restored"], [])


if __name__ == "__main__":
    unittest.main()
