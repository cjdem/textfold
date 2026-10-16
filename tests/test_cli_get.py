"""`textfold get` writes the levels with the model chosen in the settings, an agent's too: the agents on this computer
are found first, as the server finds them when it starts (#6). Nothing here runs an agent or calls a model.

Run from the repo root:
    python -m unittest discover tests
"""
import argparse
import unittest
from unittest import mock

from textfold import __main__ as cli
from textfold import agents, fold, models, pipeline, store


def args(**kw):
    return argparse.Namespace(**{"ref": "2512.24601", "lang": "en", "no_generate": False, "json": False, "level": "full",
                                 "section": None, **kw})


class Get(unittest.TestCase):
    def run_get(self, chosen, **kw):
        with mock.patch.object(models, "load_settings", return_value={"model": chosen} if chosen else {}), \
             mock.patch.object(agents, "scan") as scan, \
             mock.patch.object(models, "resolve", return_value={"id": chosen}) as resolve, \
             mock.patch.object(store, "resolve", return_value="2512.24601"), \
             mock.patch.object(pipeline, "generate") as generate, \
             mock.patch.object(fold, "document", return_value={}), \
             mock.patch.object(fold, "markdown", return_value=""):
            self.assertEqual(cli.get(args(**kw)), 0)
        return scan, resolve, generate

    def test_an_agents_model_finds_the_agents_first(self):
        scan, resolve, generate = self.run_get("pi/openai-codex/gpt-5.6-terra")
        scan.assert_called_once()
        resolve.assert_called_once_with(None)
        self.assertEqual(generate.call_args.args[2], {"id": "pi/openai-codex/gpt-5.6-terra"})

    def test_no_model_chosen_finds_the_agents_too(self):
        scan, _, _ = self.run_get(None)
        scan.assert_called_once()

    def test_a_providers_model_needs_no_scan(self):
        scan, resolve, _ = self.run_get("openrouter/free")
        scan.assert_not_called()
        resolve.assert_called_once_with(None)

    def test_no_generate_looks_for_nothing(self):
        scan, resolve, generate = self.run_get("claude/claude-code/sonnet", no_generate=True)
        scan.assert_not_called()
        resolve.assert_not_called()
        self.assertIsNone(generate.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
