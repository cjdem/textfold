"""`textfold get` uses the API model selected in TextFold settings, when one is available.

Run from the repo root:
    python -m unittest discover tests
"""
import argparse
import unittest
from unittest import mock

from textfold import __main__ as cli
from textfold import fold, models, pipeline, store


def args(**kw):
    return argparse.Namespace(**{"ref": "2512.24601", "lang": "en", "no_generate": False, "json": False, "level": "full",
                                 "section": None, **kw})


class Get(unittest.TestCase):
    def run_get(self, chosen, **kw):
        with mock.patch.object(models, "load_settings", return_value={"model": chosen} if chosen else {}), \
             mock.patch.object(models, "resolve", return_value={"id": chosen}) as resolve, \
             mock.patch.object(store, "resolve", return_value="2512.24601"), \
             mock.patch.object(pipeline, "generate") as generate, \
             mock.patch.object(fold, "document", return_value={}), \
             mock.patch.object(fold, "markdown", return_value=""):
            self.assertEqual(cli.get(args(**kw)), 0)
        return resolve, generate

    def test_a_selected_api_model_is_resolved_for_generation(self):
        resolve, generate = self.run_get("magpie/auto")
        resolve.assert_called_once_with(None)
        self.assertEqual(generate.call_args.args[2], {"id": "magpie/auto"})

    def test_no_selected_model_uses_the_provider_default(self):
        resolve, generate = self.run_get(None)
        resolve.assert_called_once_with(None)
        self.assertEqual(generate.call_args.args[2], {"id": None})

    def test_no_generate_does_not_resolve_a_model(self):
        resolve, generate = self.run_get("openrouter/free", no_generate=True)
        resolve.assert_not_called()
        self.assertIsNone(generate.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
