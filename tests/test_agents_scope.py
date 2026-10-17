"""Only the agents the reader can drive are scanned and listed: a tool that is found but cannot run a generation is
not offered, so no scan row has a `runnable` flag any more and no other runtime is registered.

Run from the repo root:
    python -m unittest discover tests
"""
import os
import unittest
from unittest import mock

from textfold import agents, bridges, engine, models, server


class Registry(unittest.TestCase):
    def test_only_the_three_drivable_agents_are_registered(self):
        self.assertEqual([r[0] for r in agents.REGISTRY], ["claude-code", "codex", "pi"])

    def test_a_scan_returns_only_those_three(self):
        old = dict(agents.STATE)
        try:
            with mock.patch.dict(os.environ, {"TEXTFOLD_NO_MODELS": "1"}):
                state = agents.scan()
            self.assertEqual([a["runtime"] for a in state["agents"]], ["claude-code", "codex", "pi"])
            self.assertTrue(all(a["path"] is None for a in state["agents"]))
            self.assertTrue(all("runnable" not in a for a in state["agents"]))
        finally:
            agents.STATE.clear()
            agents.STATE.update(old)

    def test_a_found_agent_is_asked_for_its_models(self):
        old = dict(agents.STATE)
        catalog = {rt: (lambda path, rt=rt: [{"id": rt, "name": rt}]) for rt in ("claude-code", "codex", "pi")}
        try:
            with mock.patch.dict(os.environ, {"TEXTFOLD_NO_MODELS": ""}), \
                 mock.patch.object(agents, "locate", side_effect=lambda binary, extra: f"/fake/{binary}"), \
                 mock.patch.object(agents, "_run", return_value=mock.Mock(stdout="1.0", stderr="")), \
                 mock.patch.dict(agents.CATALOG, catalog):
                state = agents.scan()
            self.assertEqual([len(a["models"]) for a in state["agents"]], [1, 1, 1])
            self.assertTrue(all("runnable" not in a for a in state["agents"]))
            self.assertEqual([m["id"] for m in agents.models()], ["claude-code", "codex", "pi"])
        finally:
            agents.STATE.clear()
            agents.STATE.update(old)


class Payload(unittest.TestCase):
    def test_agent_rows_carry_no_runnable_flag(self):
        old = dict(agents.STATE)
        try:
            agents.STATE.update(agents=[{"runtime": "pi", "label": "Pi", "binary": "pi", "path": "/fake/pi",
                                         "version": "1.0", "models": [{"id": "pi/x", "name": "Pi · x"}], "error": None}],
                                scanning=False, scanned_at=1.0)
            with mock.patch.object(models, "load_settings", return_value={}), \
                 mock.patch.object(models, "catalog", return_value=([], [])), \
                 mock.patch.object(bridges, "bridge_status", return_value={"running": False}), \
                 mock.patch.object(engine, "status", return_value={}):
                payload = server.models_payload()
            self.assertEqual(payload["agents"], [{"runtime": "pi", "label": "Pi", "binary": "pi", "path": "/fake/pi",
                                                 "version": "1.0", "error": None, "models": 1}])
        finally:
            agents.STATE.clear()
            agents.STATE.update(old)


if __name__ == "__main__":
    unittest.main()
