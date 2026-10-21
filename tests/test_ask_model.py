"""models.ask_choice and ask_spec: questions use the levels' API model unless configured otherwise."""
import unittest
from unittest import mock

from textfold import models

LEVELS = ["off", "low", "medium", "high", "xhigh", "max"]
CAT = [{"id": "magpie/fast", "name": "Magpie Fast", "kind": "api", "group": "magpie", "efforts": LEVELS},
       {"id": "magpie/strong", "name": "Magpie Strong", "kind": "api", "group": "magpie", "efforts": LEVELS},
       {"id": "openrouter/free", "name": "openrouter/free", "kind": "api", "group": "openrouter", "efforts": []}]


def settings(**kw):
    return {"model": "magpie/fast", "ask_model": None, "ask_effort": None, "efforts": {}, "providers": [], **kw}


class AskModel(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(models, "catalog", return_value=(CAT, []))
        p.start()
        self.addCleanup(p.stop)

    def test_none_chosen_uses_the_levels_model_at_the_default(self):
        s = settings()
        self.assertEqual(models.ask_choice(s, CAT), (None, None))
        with mock.patch.object(models, "resolve", return_value={"id": "magpie/fast"}):
            spec = models.ask_spec(s)
        self.assertEqual((spec["id"], spec["effort"]), ("magpie/fast", models.DEFAULT_THINKING["ask"]))

    def test_a_stronger_model_reasoning_more(self):
        with mock.patch.object(models, "resolve", return_value={"id": "magpie/strong", "model": "strong"}):
            spec = models.ask_spec(settings(ask_model="magpie/strong", ask_effort="high"))
        self.assertEqual((spec["id"], spec["model"], spec["effort"]), ("magpie/strong", "strong", "high"))

    def test_the_same_model_reasoning_more(self):
        with mock.patch.object(models, "resolve", return_value={"id": "magpie/fast"}):
            spec = models.ask_spec(settings(ask_effort="xhigh"))
        self.assertEqual((spec["id"], spec["effort"]), ("magpie/fast", "xhigh"))

    def test_a_model_gone_or_a_level_it_has_not(self):
        self.assertEqual(models.ask_choice(settings(ask_model="gone/model"), CAT), (None, None))
        self.assertEqual(models.ask_choice(settings(ask_model="openrouter/free", ask_effort="high"), CAT), ("openrouter/free", None))
        self.assertEqual(models.ask_choice(settings(ask_effort="ultra"), CAT), (None, None))


if __name__ == "__main__":
    unittest.main()
