"""OpenRouter's one-click authorisation: its PKCE consent URL, the code exchange, and the key kept until saved.

The ChatGPT local bridge used to sit beside this door; these tests are what keeps the remaining one working after it
is gone.
"""
import http.client
import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

from textfold import openrouter, server


class Consent(unittest.TestCase):
    def setUp(self):
        openrouter._OR.clear()

    def tearDown(self):
        openrouter._OR.clear()

    def test_start_builds_a_pkce_consent_url(self):
        with mock.patch.object(openrouter.secrets, "token_bytes", return_value=b"\x00" * 48):
            url = openrouter.openrouter_start("http://localhost:3017/oauth/openrouter", "/p/x")
        parts = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parts.query)
        self.assertEqual((parts.scheme, parts.netloc, parts.path), ("https", "openrouter.ai", "/auth"))
        self.assertEqual(query["callback_url"], ["http://localhost:3017/oauth/openrouter"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        # A fixed verifier and the S256 challenge it must produce: a challenge that drifts fails here.
        self.assertEqual(query["code_challenge"], ["1T7aemN8mcx_tWbZbp-hCb8VxHhBCj9etNTE4mzQgfY"])
        self.assertEqual(openrouter._OR["verifier"], "A" * 64)
        self.assertIsNone(openrouter.minted())
        self.assertFalse(openrouter.for_desktop())

    def test_a_desktop_authorisation_is_remembered(self):
        openrouter.openrouter_start("http://localhost:3017/oauth/openrouter", "/", desktop=True)
        self.assertTrue(openrouter.for_desktop())
        openrouter.openrouter_start("http://localhost:3017/oauth/openrouter", "/")
        self.assertFalse(openrouter.for_desktop())

    def test_finish_exchanges_the_code_and_keeps_the_key_until_saved(self):
        openrouter.openrouter_start("http://localhost:3017/oauth/openrouter", "/p/x")
        verifier = openrouter._OR["verifier"]
        reply = mock.MagicMock()
        reply.__enter__.return_value.read.return_value = b'{"key": "sk-or-1"}'
        with mock.patch.object(openrouter.urllib.request, "urlopen", return_value=reply) as urlopen:
            key, error, back = openrouter.openrouter_finish("the-code")
        self.assertEqual((key, error, back), ("sk-or-1", None, "/p/x"))
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data),
                         {"code": "the-code", "code_verifier": verifier, "code_challenge_method": "S256"})
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 30)
        self.assertTrue(openrouter.minted())
        self.assertEqual(openrouter.take_minted(), "sk-or-1")
        self.assertIsNone(openrouter.take_minted())
        self.assertFalse(openrouter.minted())

    def test_a_failed_exchange_reports_the_error_and_mints_nothing(self):
        openrouter.openrouter_start("http://localhost:3017/oauth/openrouter", "/")
        with mock.patch.object(openrouter.urllib.request, "urlopen", side_effect=OSError("no route")):
            key, error, back = openrouter.openrouter_finish("the-code")
        self.assertIsNone(key)
        self.assertIn("no route", error)
        self.assertEqual(back, "/")
        self.assertIsNone(openrouter.minted())

    def test_finish_without_a_start_reports_no_authorisation(self):
        self.assertEqual(openrouter.openrouter_finish("the-code"), (None, "no authorisation was under way", "/"))

    def test_a_reply_without_a_key_is_an_error(self):
        openrouter.openrouter_start("http://localhost:3017/oauth/openrouter", "/")
        reply = mock.MagicMock()
        reply.__enter__.return_value.read.return_value = b"{}"
        with mock.patch.object(openrouter.urllib.request, "urlopen", return_value=reply):
            key, error, _ = openrouter.openrouter_finish("the-code")
        self.assertEqual((key, error), (None, "no key in the reply"))


class Routes(unittest.TestCase):
    """The server's own doors: the bridge's are gone, OpenRouter's still answer."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(mock.Mock()))
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        openrouter._OR.clear()

    def url(self, path):
        return f"http://127.0.0.1:{self.httpd.server_port}{path}"

    def get(self, path):
        with urllib.request.urlopen(self.url(path), timeout=2) as r:
            return json.loads(r.read())

    def page(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=2)
        try:
            conn.request("GET", path)
            return conn.getresponse().read().decode()
        finally:
            conn.close()

    def test_the_bridge_routes_are_gone(self):
        for path, method in (("/api/bridge", "GET"), ("/api/bridge/start", "POST")):
            with self.subTest(path=path):
                data = b"{}" if method == "POST" else None   # (a GET with a body can be aborted on Windows)
                request = urllib.request.Request(self.url(path), data=data, method=method,
                                                 headers={"Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    urllib.request.urlopen(request, timeout=2)
                self.assertEqual(cm.exception.code, 404)
                cm.exception.close()

    def test_the_openrouter_minted_route_still_answers(self):
        self.assertEqual(self.get("/api/openrouter/minted"), {"minted": False})

    def test_the_openrouter_start_route_returns_a_consent_url(self):
        request = urllib.request.Request(self.url("/api/openrouter/start"), data=b'{"back": "/"}',
                                         headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=2) as r:
            url = json.loads(r.read())["url"]
        self.assertTrue(url.startswith("https://openrouter.ai/auth?"))
        self.assertIn("code_challenge=", url)

    def test_the_consent_return_redirects_with_the_minted_fragment(self):
        openrouter.openrouter_start("http://localhost:3017/oauth/openrouter", "/p/x")
        reply = mock.MagicMock()
        reply.__enter__.return_value.read.return_value = b'{"key": "sk-or-1"}'
        with mock.patch.object(openrouter.urllib.request, "urlopen", return_value=reply):
            page = self.page("/oauth/openrouter?code=the-code")
        self.assertIn('location.replace("/p/x#or-minted")', page)
        self.assertEqual(openrouter.minted(), "sk-or-1")

    def test_the_consent_return_reports_a_failure(self):
        page = self.page("/oauth/openrouter?code=the-code")
        self.assertIn("#or-failed=no%20authorisation%20was%20under%20way", page)

    def test_a_desktop_return_keeps_the_key_for_the_app(self):
        openrouter.openrouter_start("http://localhost:3017/oauth/openrouter", "/", desktop=True)
        reply = mock.MagicMock()
        reply.__enter__.return_value.read.return_value = b'{"key": "sk-or-1"}'
        with mock.patch.object(openrouter.urllib.request, "urlopen", return_value=reply):
            page = self.page("/oauth/openrouter?code=the-code")
        self.assertIn("Return to TextFold", page)
        self.assertEqual(openrouter.minted(), "sk-or-1")


if __name__ == "__main__":
    unittest.main()
