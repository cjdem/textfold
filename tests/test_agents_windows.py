"""Windows subprocess behavior: a child process starts without a console window."""
import os
import subprocess
import sys
import unittest

from textfold import server


@unittest.skipUnless(os.name == "nt", "Windows only")
class QuietChildren(unittest.TestCase):
    def test_a_child_starts_without_a_window(self):
        init = subprocess.Popen.__init__
        self.addCleanup(setattr, subprocess.Popen, "__init__", init)
        server._quiet_children()
        p = subprocess.Popen([sys.executable, "-c", "print(1)"], stdout=subprocess.PIPE)
        self.assertEqual(p.communicate()[0].strip(), b"1")


if __name__ == "__main__":
    unittest.main()
