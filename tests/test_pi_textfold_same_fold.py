"""The Pi extension folds as the Claude Code mod does: the same engine, byte for byte, and the same style section.

Each harness installs its own folder and nothing outside it, so plugins/pi-textfold keeps copies of the mod's fold.ts
and of its section; these tests fail as soon as one copy is changed without the other.

Run from the repo root:
    python -m unittest discover tests
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / "plugins" / "textfold" / "hooks"
PI = ROOT / "plugins" / "pi-textfold" / "extension"


def style(path):
    found = re.search(r"const STYLE = `(.*?)`", path.read_text(encoding="utf-8"), re.S)
    return found.group(1) if found else None


class SameFoldTest(unittest.TestCase):
    def test_engine(self):
        self.assertEqual((PI / "fold.ts").read_bytes(), (MOD / "fold.ts").read_bytes(),
                         "plugins/pi-textfold/extension/fold.ts is not plugins/textfold/hooks/fold.ts: copy the mod's over")

    def test_style(self):
        mod, pi = style(MOD / "register.tsx"), style(PI / "index.ts")
        self.assertTrue(mod and mod.startswith("# Replies that fold"), "the mod's STYLE was not found")
        self.assertEqual(pi, mod, "the Pi extension's STYLE is not the mod's: copy the mod's over")


if __name__ == "__main__":
    unittest.main()
