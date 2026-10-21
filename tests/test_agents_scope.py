"""API-only model catalog and server contract regressions."""
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

from textfold import bridges, engine, models, providers, server


class ProviderOnly(unittest.TestCase):
    def test_catalog_has_only_api_models(self):
        with mock.patch.object(models, "provider_list", return_value=[
            {"key": "magpie", "models": [{"id": "auto/model", "name": "Auto model"}]}
        ]):
            catalog, _ = models.catalog({"providers": [], "use_thoughtdag_env": False})
        self.assertEqual([row["kind"] for row in catalog], ["api"])

    def test_server_payload_has_no_agent_scan_state(self):
        with mock.patch.object(models, "load_settings", return_value={}), \
             mock.patch.object(models, "catalog", return_value=([], [])), \
             mock.patch.object(bridges, "bridge_status", return_value={"running": False}), \
             mock.patch.object(engine, "status", return_value={}):
            payload = server.models_payload()
        self.assertNotIn("agents", payload)
        self.assertNotIn("scanning", payload)
        self.assertNotIn("scannedAt", payload)

    def test_agent_scan_route_returns_404(self):
        jobs = mock.Mock()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(jobs))
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        req = urllib.request.Request(f"http://127.0.0.1:{httpd.server_port}/api/agents/scan", data=b"{}",
                                     headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=2)
        self.assertEqual(cm.exception.code, 404)
        cm.exception.close()

    def test_no_models_suppresses_local_provider_probes(self):
        with mock.patch.dict("os.environ", {"TEXTFOLD_NO_MODELS": "1"}), \
             mock.patch.object(providers, "magpie_models", side_effect=AssertionError("probed")):
            self.assertEqual(models.provider_list({}), [])

    def test_startup_launches_no_agent_scan_thread(self):
        self.assertFalse(hasattr(server, "agents"))
        with mock.patch.object(server, "Jobs"), \
             mock.patch.object(server, "ThreadingHTTPServer") as httpd, \
             mock.patch.object(server.threading, "Thread") as thread:
            httpd.return_value.serve_forever.side_effect = KeyboardInterrupt
            server.serve(0)
        thread.assert_not_called()

    def test_cli_runtime_module_is_absent(self):
        from pathlib import Path
        self.assertFalse((Path(server.__file__).parent / "agents.py").exists())

    def test_development_workflow_agents_remain(self):
        from pathlib import Path
        root = Path(server.__file__).parent.parent
        self.assertTrue((root / ".claude" / "agents" / "textfold-scout.md").exists())
        self.assertTrue((root / ".claude" / "agents" / "textfold-verifier.md").exists())


if __name__ == "__main__":
    unittest.main()
