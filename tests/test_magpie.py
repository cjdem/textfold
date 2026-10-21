"""Magpie discovery and chat use its optional local OpenAI-compatible gateway."""
import json
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from textfold import bridges, llm, models, providers


class Gateway(BaseHTTPRequestHandler):
    models_body = {"data": [
        {"id": "local/first", "display_name": "First local model", "supported_reasoning_levels": [{"effort": "low"}]},
        {"id": "local/second", "magpie_label": "Second local model"},
        {"id": ""},
        {},
        None,
    ]}
    requests = []
    delay = 0.0

    def do_GET(self):
        type(self).requests.append(("GET", self.path, self.headers.get("Authorization")))
        if type(self).delay:
            time.sleep(type(self).delay)
        if self.path == "/v1/models":
            body, status = type(self).models_body, 200
        else:
            body, status = {"error": "not found"}, 404
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        type(self).requests.append(("POST", self.path, self.headers.get("Authorization"), body))
        data = json.dumps({"choices": [{"message": {"content": '{"ok":true}'}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class Magpie(unittest.TestCase):
    def setUp(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        Gateway.requests = []
        Gateway.delay = 0.0
        self.base = f"http://127.0.0.1:{self.httpd.server_port}/v1"
        self.env = {k: os.environ.get(k) for k in ("MAGPIE_BASE_URL", "MAGPIE_MODELS", "TEXTFOLD_NO_MODELS")}
        os.environ["MAGPIE_BASE_URL"] = self.base
        os.environ.pop("MAGPIE_MODELS", None)
        os.environ.pop("TEXTFOLD_NO_MODELS", None)
        self.magpie_before = dict(providers.MAGPIE)
        self.clear_magpie()
        models._clear_provider_cache()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        for key, value in self.env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        providers.MAGPIE.update(self.magpie_before)
        models._clear_provider_cache()

    @staticmethod
    def clear_magpie():
        providers.MAGPIE.update(base=None, at=0.0, models=[])

    def wait_for_probe(self, base=None):
        base = base or self.base
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if providers.MAGPIE["at"] and providers.MAGPIE["base"] == base:
                return
            time.sleep(0.01)
        self.fail("Magpie probe did not finish")

    def test_models_are_discovered_with_dynamic_ids_and_labels(self):
        base, pending = providers.magpie_models()
        self.assertEqual(base, self.base)
        self.assertEqual(pending, [])
        self.wait_for_probe()
        _, found = providers.magpie_models()
        self.assertEqual([(m["id"], m["name"]) for m in found], [
            ("local/first", "First local model"), ("local/second", "Second local model")])
        self.assertEqual(found[0]["efforts"], ["low"])
        self.assertIn(("GET", "/v1/models", "Bearer magpie"), Gateway.requests)

    def test_malformed_answers_leave_no_models(self):
        class Response:
            def __init__(self, body):
                self.body = body
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return self.body

        for body in (b"not json", b'{"data": null}', b'{"data": "not a list"}', b'{"data": [{"no_id": 1}]}'):
            with mock.patch.object(providers.urllib.request, "urlopen", return_value=Response(body)):
                providers._MAGPIE_LOCK.acquire()
                providers._magpie_probe(self.base)
            self.assertEqual(providers.MAGPIE["models"], [], body)
        error = providers.urllib.error.HTTPError(self.base, 500, "boom", {}, None)
        with mock.patch.object(providers.urllib.request, "urlopen", side_effect=error):
            providers._MAGPIE_LOCK.acquire()
            providers._magpie_probe(self.base)
        error.close()
        self.assertEqual(providers.MAGPIE["models"], [])

    def test_magpie_has_priority_default_explicit_choice_and_collision_resolution(self):
        providers.magpie_models()
        self.wait_for_probe()
        other = {"key": "other", "name": "Other", "protocol": "openai", "base": "https://other/v1", "api_key": "k",
                 "source": "env", "models": [{"id": "local/first", "name": "Collision"}, {"id": "other/model", "name": "Other model"}]}
        with mock.patch.object(providers, "env_providers", return_value=[other]), \
             mock.patch.object(providers, "ui_providers", return_value=[]), \
             mock.patch.object(providers, "ollama_models", return_value=[]), \
             mock.patch.object(bridges, "bridge_provider", return_value=None), \
             mock.patch.object(bridges, "bridge_status", return_value={"running": False}):
            settings = {"providers": [], "use_thoughtdag_env": False}
            rows = models.provider_list(settings)
            self.assertEqual(rows[0]["key"], "magpie")
            catalog, _ = models.catalog(settings)
            self.assertEqual(models.default_model(settings, catalog), "local/first")
            self.assertEqual(next(m for m in catalog if m["id"] == "local/first")["group"], "magpie")
            self.assertEqual(models.default_model({**settings, "model": "other/model"}, catalog), "other/model")
            spec = models.resolve("local/first", settings)
        self.assertEqual((spec["base"], spec["api_key"], spec["protocol"]), (self.base, "magpie", "openai"))

    def test_manual_magpie_is_authoritative_and_not_duplicated(self):
        providers.magpie_models()
        self.wait_for_probe()
        manual = {"key": "magpie", "preset": "magpie", "name": "Manual Magpie", "base": "http://127.0.0.1:9/v1",
                  "api_key": "", "models": [{"id": "manual/model"}]}
        second = {"key": "magpie", "preset": "magpie", "name": "Second Magpie", "base": "http://127.0.0.1:10/v1",
                  "api_key": "", "models": [{"id": "second/model"}]}
        with mock.patch.object(providers, "env_providers", return_value=[]), \
             mock.patch.object(providers, "ui_providers", wraps=providers.ui_providers), \
             mock.patch.object(providers, "ollama_models", return_value=[]), \
             mock.patch.object(bridges, "bridge_provider", return_value=None), \
             mock.patch.object(bridges, "bridge_status", return_value={"running": False}):
            rows = models.provider_list({"providers": [manual, second], "use_thoughtdag_env": False})
        self.assertEqual([p["key"] for p in rows].count("magpie"), 1)
        self.assertEqual((rows[0]["name"], rows[0]["base"], rows[0]["api_key"]),
                         ("Manual Magpie", manual["base"], "magpie"))
        self.assertEqual([m["id"] for m in rows[0]["models"]], ["manual/model"])

    def test_a_probe_answer_and_the_rows_come_from_one_snapshot(self):
        answers = [(self.base, []), (self.base, [{"id": "local/late", "name": "Late"}])]

        def magpie_models(wait=False):
            return answers.pop(0) if len(answers) > 1 else answers[0]

        other = {"key": "other", "name": "Other", "protocol": "openai", "base": "https://other/v1", "api_key": "k",
                 "source": "env", "models": [{"id": "other/model", "name": "Other model"}]}
        with mock.patch.object(providers, "magpie_models", side_effect=magpie_models) as probe, \
             mock.patch.object(providers, "env_providers", return_value=[other]), \
             mock.patch.object(providers, "ui_providers", return_value=[]), \
             mock.patch.object(providers, "ollama_models", return_value=[]), \
             mock.patch.object(bridges, "bridge_provider", return_value=None), \
             mock.patch.object(bridges, "bridge_status", return_value={"running": False}):
            settings = {"providers": [], "use_thoughtdag_env": False}
            first = models.provider_list(settings)
            second = models.provider_list(settings)
        self.assertEqual(probe.call_count, 2)
        self.assertNotIn("magpie", [p["key"] for p in first])
        self.assertIn("magpie", [p["key"] for p in second])

    def test_failed_probe_keeps_other_providers_available(self):
        offline = "http://127.0.0.1:1/v1"
        os.environ["MAGPIE_BASE_URL"] = offline
        self.clear_magpie()
        providers.magpie_models()
        self.wait_for_probe(offline)
        self.assertEqual(providers.MAGPIE["models"], [])
        other = {"key": "other", "name": "Other", "protocol": "openai", "base": "https://other/v1", "api_key": "k",
                 "source": "env", "models": [{"id": "other/model", "name": "Other model"}]}
        with mock.patch.object(providers, "env_providers", return_value=[other]), \
             mock.patch.object(providers, "ui_providers", return_value=[]), \
             mock.patch.object(providers, "ollama_models", return_value=[]), \
             mock.patch.object(bridges, "bridge_provider", return_value=None), \
             mock.patch.object(bridges, "bridge_status", return_value={"running": False}):
            settings = {"providers": [], "use_thoughtdag_env": False}
            rows = models.provider_list(settings)
            self.assertEqual(models.default_model(settings), "other/model")
        self.assertEqual([p["key"] for p in rows], ["other"])

    def test_concurrent_requests_start_one_probe(self):
        Gateway.delay = 0.2
        threads = [threading.Thread(target=providers.magpie_models) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)
        self.wait_for_probe()
        self.assertEqual(len([r for r in Gateway.requests if r[0] == "GET"]), 1)

    def test_chat_uses_openai_compatible_endpoint_without_starting_a_cli(self):
        spec = {"id": "local/first", "model": "local/first", "provider": "Magpie", "protocol": "openai",
                "base": self.base, "api_key": "magpie"}
        with mock.patch("subprocess.Popen", side_effect=AssertionError("no product CLI may launch")):
            out, _ = llm._once("prompt", {"type": "object"}, spec, 2, "system")
        self.assertEqual(out, {"ok": True})
        post = next(r for r in Gateway.requests if r[0] == "POST")
        self.assertEqual(post[1:3], ("/v1/chat/completions", "Bearer magpie"))
        self.assertEqual(post[3]["model"], "local/first")

    def test_a_generation_waits_for_a_probe_already_under_way(self):
        Gateway.delay = 0.4
        providers.magpie_models()   # the page's own call: answers at once and probes in the background
        settings = {"providers": [], "use_thoughtdag_env": False}
        spec = models.resolve(None, settings)
        self.assertEqual((spec["id"], spec["base"], spec["api_key"]), ("local/first", self.base, "magpie"))

    def test_an_old_agent_model_is_unavailable_and_falls_back(self):
        rows = [{"key": "magpie", "name": "Magpie", "protocol": "openai", "base": self.base, "api_key": "magpie",
                 "source": "local", "models": [{"id": "local/first", "name": "First local model"}]}]
        settings = {"model": "claude/claude-code/sonnet", "providers": [], "use_thoughtdag_env": False}
        with mock.patch.object(models, "provider_list", return_value=rows):
            catalog, _ = models.catalog(settings)
            self.assertEqual(models.default_model(settings, catalog), "local/first")
            with self.assertRaisesRegex(RuntimeError, "provider is gone"):
                models.resolve("claude/claude-code/sonnet", settings)

    def test_magpie_models_environment_override_skips_http_discovery(self):
        os.environ["MAGPIE_MODELS"] = "custom/one,custom/two"
        base, found = providers.magpie_models()
        self.assertEqual(base, self.base)
        self.assertEqual([m["id"] for m in found], ["custom/one", "custom/two"])
        self.assertFalse(Gateway.requests)


if __name__ == "__main__":
    unittest.main()
