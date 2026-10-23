"""A key TextFold keeps is not a key a page can send somewhere else: a saved provider's key goes only to that
provider's saved address, a minted OpenRouter key only to OpenRouter, and a page on another local port may not drive a
writing POST (the OpenRouter return is a GET outside that rule). The server runs on this computer with its own settings
file; providers.probe is a recorder, so no request leaves the machine.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from textfold import models, openrouter, providers, server

ROOT = Path(__file__).resolve().parent.parent
SAVED = "https://api.acme.example/v1"
OTHER = "https://attacker.example/v1"
SECRET = "sk-acme-secret"


class ProviderKeys(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(models, "SETTINGS", Path(self.tmp.name) / "settings.json")
        patch.start()
        self.addCleanup(patch.stop)
        old_homes = models.OLD_HOMES
        models.OLD_HOMES = []
        self.addCleanup(setattr, models, "OLD_HOMES", old_homes)
        env = mock.patch.dict(os.environ, {"TEXTFOLD_NO_MODELS": "1"})
        env.start()
        self.addCleanup(env.stop)
        models.save_settings({"use_thoughtdag_env": False,
                              "providers": [{"key": "acme", "preset": "custom", "name": "Acme", "base": SAVED,
                                             "api_key": SECRET, "models": []}]})
        self.seen = []
        probe = mock.patch.object(providers, "probe", side_effect=lambda base, key: self.seen.append((base, key)) or [])
        probe.start()
        self.addCleanup(probe.stop)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(mock.Mock()))
        self.httpd_port = self.httpd.server_port
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        openrouter._OR.clear()
        self.addCleanup(openrouter._OR.clear)

    def post(self, path, body):
        req = urllib.request.Request(f"http://127.0.0.1:{self.httpd_port}{path}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            code, data = e.code, json.loads(e.read())
            e.close()
            return code, data

    def test_a_saved_key_is_not_sent_to_another_address(self):
        code, d = self.post("/api/providers/probe", {"key": "acme", "base": OTHER})
        self.assertEqual((code, d["error"]), (400, server.KEY_ADDRESS))
        self.assertEqual(self.seen, [])   # (nothing left the process)
        code, _ = self.post("/api/providers/probe", {"key": "acme", "base": SAVED})
        self.assertEqual(code, 200)
        self.assertEqual(self.seen, [(SAVED, SECRET)])
        code, _ = self.post("/api/providers/probe", {"key": "acme", "base": OTHER, "api_key": "sk-typed"})
        self.assertEqual(code, 200)
        self.assertEqual(self.seen[-1], (OTHER, "sk-typed"))   # (the caller's own key may go where it is asked)

    def test_a_minted_key_goes_only_to_openrouter(self):
        openrouter._OR["minted"] = "sk-or-secret"
        code, d = self.post("/api/providers/probe", {"minted": True, "base": OTHER})
        self.assertEqual((code, d["error"]), (400, server.KEY_ADDRESS))
        self.assertEqual(self.seen, [])
        self.assertEqual(openrouter.minted(), "sk-or-secret")   # (still there for the right address)
        code, _ = self.post("/api/providers/probe", {"minted": True, "base": server.OPENROUTER_BASE})
        self.assertEqual(code, 200)
        self.assertEqual(self.seen, [(server.OPENROUTER_BASE, "sk-or-secret")])

    def test_a_saved_key_does_not_move_to_another_address_on_save(self):
        body = {"key": "acme", "preset": "custom", "name": "Acme", "base": OTHER, "models": []}
        code, d = self.post("/api/providers/save", body)
        self.assertEqual((code, d["error"]), (400, server.KEY_ADDRESS))
        saved = models.load_settings()["providers"][0]
        self.assertEqual((saved["base"], saved["api_key"]), (SAVED, SECRET))   # (nothing moved)
        code, _ = self.post("/api/providers/save", body | {"api_key": "sk-new"})
        self.assertEqual(code, 200)
        saved = models.load_settings()["providers"][0]
        self.assertEqual((saved["base"], saved["api_key"]), (OTHER, "sk-new"))   # (the caller's own key is theirs)
        code, _ = self.post("/api/providers/save", {"key": "acme", "preset": "custom", "name": "Acme", "base": OTHER, "models": []})
        self.assertEqual(code, 200)   # (the address is unchanged now: the saved key may stay)

    def test_a_minted_key_is_not_saved_for_another_address(self):
        openrouter._OR["minted"] = "sk-or-secret"
        body = {"key": "openrouter-acme", "preset": "openrouter", "name": "OpenRouter", "base": OTHER, "models": []}
        code, d = self.post("/api/providers/save", body | {"minted": True})
        self.assertEqual((code, d["error"]), (400, server.KEY_ADDRESS))
        self.assertEqual(openrouter.minted(), "sk-or-secret")   # (not consumed by the refused save)
        self.assertNotIn("openrouter-acme", [p["key"] for p in models.load_settings()["providers"]])
        code, _ = self.post("/api/providers/save", body | {"minted": True, "base": server.OPENROUTER_BASE})
        self.assertEqual(code, 200)
        rows = models.load_settings()["providers"]
        self.assertEqual(next(p for p in rows if p["key"] == "openrouter-acme")["api_key"], "sk-or-secret")
        self.assertIsNone(openrouter.minted())

    def test_a_probe_racing_a_save_never_sees_the_key_at_another_address(self):
        seen = []

        def slow(base, key):
            seen.append((base, key))
            time.sleep(0.002)
            return []

        def probes():
            for i in range(40):   # (half at the saved address, half at the other one: the dangerous direction too)
                self.post("/api/providers/probe", {"key": "acme", "base": SAVED if i % 2 else OTHER})

        def moves():
            for i in range(10):
                self.post("/api/providers/save", {"key": "acme", "preset": "custom", "name": "Acme", "base": OTHER,
                                                  "api_key": f"sk-new-{i}", "models": []})

        with mock.patch.object(providers, "probe", side_effect=slow):
            prober, mover = threading.Thread(target=probes), threading.Thread(target=moves)
            prober.start()
            mover.start()
            prober.join(20)
            mover.join(20)
        self.assertNotIn((OTHER, SECRET), seen)   # (a save changes the address and the key together, under the lock)
        self.assertTrue(all(k != SECRET or b == SAVED for b, k in seen), seen)


class Dialog(unittest.TestCase):
    def test_a_refused_save_shows_its_message(self):
        js = (ROOT / "textfold" / "web" / "app.js").read_text(encoding="utf-8")
        start = js.index("q('.pf-save').onclick")
        block = js[start:js.index("async function fetchModels", start)]
        self.assertIn("try {", block)
        self.assertIn("q('.pf-err')", block)
        self.assertIn("x.message", block)


if __name__ == "__main__":
    unittest.main()
