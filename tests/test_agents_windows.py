"""Windows subprocess behavior retained for the ChatGPT bridge."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import bridges, procenv, server


@unittest.skipUnless(os.name == "nt", "Windows only")
class QuietChildren(unittest.TestCase):
    def test_a_child_starts_without_a_window(self):
        init = subprocess.Popen.__init__
        self.addCleanup(setattr, subprocess.Popen, "__init__", init)
        server._quiet_children()
        p = subprocess.Popen([sys.executable, "-c", "print(1)"], stdout=subprocess.PIPE)
        self.assertEqual(p.communicate()[0].strip(), b"1")


class BridgeEnvironment(unittest.TestCase):
    def test_npx_uses_the_widened_path(self):
        with mock.patch.object(procenv, "search_dirs", return_value=["C:/node", "C:/npm"]):
            env = procenv.child_env()
        self.assertEqual(env["PATH"], os.pathsep.join(["C:/node", "C:/npm"]))

    def test_bridge_start_resolves_npx_from_the_widened_path(self):
        with tempfile.TemporaryDirectory() as home, \
             mock.patch.object(procenv, "child_env", return_value={"PATH": "C:/node;C:/npm"}), \
             mock.patch.object(bridges.shutil, "which", return_value="C:/npm/npx.cmd") as which, \
             mock.patch.object(bridges, "HOME", Path(home)), \
             mock.patch("builtins.open", mock.mock_open()), \
             mock.patch.object(bridges.subprocess, "Popen") as popen, \
             mock.patch.object(bridges, "bridge_status", return_value={"running": True}):
            bridges.bridge_start()
        which.assert_called_once_with("npx", path="C:/node;C:/npm")
        self.assertEqual(popen.call_args.kwargs["env"], {"PATH": "C:/node;C:/npm"})


if __name__ == "__main__":
    unittest.main()
