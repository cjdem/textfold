"""The landing page builds the model catalog once — building it probes the computer's own model servers, and four
builds made returning to the home page take a quarter of a minute — and the provider list is reused for ten seconds.
The local probes answer from their last result at once and refresh in the background: a probe to a closed port
waits for its whole timeout on some computers (a closed port is dropped, not refused, there).

Run from the repo root:
    python -m unittest discover tests
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import library, models, providers, server, store


class Landing(unittest.TestCase):
    def setUp(self):
        self.old = store.DATA
        store.DATA = Path(tempfile.mkdtemp())

    def tearDown(self):
        store.DATA = self.old

    def landing(self, settings, cat):
        jobs = mock.Mock()
        jobs.list.return_value = []
        with mock.patch.object(models, "load_settings", return_value=settings), \
             mock.patch.object(models, "catalog", return_value=(cat, [])) as catalog, \
             mock.patch.object(library, "stamp", return_value=[]), \
             mock.patch.object(library, "folders", return_value=[]):
            page = server.landing_page(jobs)
        return page, catalog

    def test_the_model_catalog_is_built_once(self):
        cat = [{"id": "m1", "name": "Model One", "kind": "api", "group": "g", "efforts": [], "defaultEffort": None}]
        page, catalog = self.landing({"model": "m1"}, cat)
        self.assertEqual(catalog.call_count, 1)
        self.assertIn("Model One", page)

    def test_the_ask_model_is_named_from_the_same_catalog(self):
        cat = [{"id": "m1", "name": "Model One", "kind": "api", "group": "g", "efforts": [], "defaultEffort": None},
               {"id": "m2", "name": "Ask Two", "kind": "api", "group": "g", "efforts": [], "defaultEffort": None}]
        page, catalog = self.landing({"model": "m1", "ask_model": "m2"}, cat)
        self.assertEqual(catalog.call_count, 1)
        self.assertIn('"askName": "Ask Two"', page)
        page, _ = self.landing({"model": "m1", "ask_model": "m1"}, cat)
        self.assertIn('"askName": ""', page)   # its own model: no second name


class Providers(unittest.TestCase):
    def setUp(self):
        models._clear_provider_cache()
        self.no_models = os.environ.pop("TEXTFOLD_NO_MODELS", None)   # (this class tests the list itself)

    def tearDown(self):
        models._clear_provider_cache()
        if self.no_models is not None:
            os.environ["TEXTFOLD_NO_MODELS"] = self.no_models

    def probe(self):
        return mock.patch.object(providers, "env_providers", return_value=[]), \
            mock.patch.object(providers, "ui_providers", return_value=[]), \
            mock.patch.object(providers, "ollama_models", return_value=[]), \
            mock.patch.object(providers, "magpie_models", return_value=("http://127.0.0.1:3425/v1", []))

    def test_the_provider_list_is_reused_for_a_moment(self):
        s = {"providers": [], "use_thoughtdag_env": False}
        a, b, c, d = self.probe()
        with a as env, b, c, d:
            models.provider_list(s)
            models.provider_list(s)
        self.assertEqual(env.call_count, 1)

    def test_a_changed_live_answer_rebuilds_the_list(self):
        s = {"providers": [], "use_thoughtdag_env": False}
        a, b, c, d = self.probe()
        with a as env, b, c, d:
            models.provider_list(s)
            providers.ollama_models.return_value = ["llama3:8b"]   # (a background probe answered between the calls)
            models.provider_list(s)
        self.assertEqual(env.call_count, 2)

    def test_the_list_is_rebuilt_after_ten_seconds(self):
        s = {"providers": [], "use_thoughtdag_env": False}
        clock = [1000.0]
        a, b, c, d = self.probe()
        with a as env, b, c, d, mock.patch.object(models.time, "time", side_effect=lambda: clock[0]):
            models.provider_list(s)
            clock[0] += 11
            models.provider_list(s)
        self.assertEqual(env.call_count, 2)

    def test_saving_the_settings_probes_again(self):
        s = {"providers": [], "use_thoughtdag_env": False}
        old = models.SETTINGS
        try:
            models.SETTINGS = Path(tempfile.mkdtemp()) / "settings.json"
            a, b, c, d = self.probe()
            with a as env, b, c, d:
                models.provider_list(s)
                models.save_settings(s)
                models.provider_list(s)
            self.assertEqual(env.call_count, 2)
        finally:
            models.SETTINGS = old


if __name__ == "__main__":
    unittest.main()
