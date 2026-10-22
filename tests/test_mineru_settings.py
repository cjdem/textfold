"""`POST /api/settings` and the MinerU API address: the official base by default, a v4-compatible one if chosen, and
an unusable address refused before anything is written. The server runs on this computer with its own settings file and
no model; nothing here reaches MinerU."""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from textfold import models, server


class SettingsRoute(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(models, "SETTINGS", Path(self.tmp.name) / "settings.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        old_homes = models.OLD_HOMES
        models.OLD_HOMES = []
        self.addCleanup(setattr, models, "OLD_HOMES", old_homes)
        env = mock.patch.dict(os.environ, {"TEXTFOLD_NO_MODELS": "1"})
        env.start()
        self.addCleanup(env.stop)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(mock.Mock()))
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def post(self, body):
        req = urllib.request.Request(f"http://127.0.0.1:{self.httpd.server_port}/api/settings",
                                     data=json.dumps(body).encode(), headers={"Content-Type": "application/json"},
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            code, data = e.code, json.loads(e.read())
            e.close()
            return code, data

    def test_a_fresh_settings_file_has_the_official_address(self):
        code, d = self.post({})
        self.assertEqual(code, 200)
        self.assertEqual((d["mineru"]["base"], d["mineru"]["official"], d["mineru"]["baseOk"]),
                         (models.MINERU_API, models.MINERU_API, True))
        self.assertEqual(models.load_settings()["mineru_api_url"], models.MINERU_API)

    def test_a_custom_v4_address_is_saved_normalized(self):
        code, d = self.post({"mineru_api_url": " https://proxy.example/api/v4/ "})
        self.assertEqual(code, 200)
        self.assertEqual(d["mineru"]["base"], "https://proxy.example/api/v4")
        self.assertEqual(models.load_settings()["mineru_api_url"], "https://proxy.example/api/v4")

    def test_an_unusable_address_is_refused_and_the_old_one_kept(self):
        self.post({"mineru_api_url": "https://proxy.example/api/v4"})
        code, d = self.post({"mineru_api_url": "ftp://proxy.example/api/v4"})
        self.assertEqual((code, d["error"]), (400, "bad-mineru-url"))
        self.assertEqual(models.load_settings()["mineru_api_url"], "https://proxy.example/api/v4")

    def test_an_empty_address_restores_the_official_one(self):
        self.post({"mineru_api_url": "https://proxy.example/api/v4"})
        code, d = self.post({"mineru_api_url": ""})
        self.assertEqual(code, 200)
        self.assertEqual(d["mineru"]["base"], models.MINERU_API)
        self.assertEqual(models.load_settings()["mineru_api_url"], models.MINERU_API)

    def test_a_non_text_address_is_refused_not_taken_as_a_reset(self):
        self.post({"mineru_api_url": "https://proxy.example/api/v4"})
        code, d = self.post({"mineru_api_url": 42})
        self.assertEqual((code, d["error"]), (400, "bad-mineru-url"))
        self.assertEqual(models.load_settings()["mineru_api_url"], "https://proxy.example/api/v4")


if __name__ == "__main__":
    unittest.main()
