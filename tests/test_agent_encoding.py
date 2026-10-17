"""What the reader and a coding agent exchange is UTF-8, whatever the system's encoding (GBK on a Chinese Windows):
the pipes of a model call and of the scan, and the files a reply or an agent's own config comes back in. A prompt
holding ▶ (the outline's mark for the section being read) and a reply holding ⟦a1⟧ markers (not in GBK) both pass.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import locale
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import agents, llm, models, notes, store

# none of these is in GBK: ▶ is the character in the translation prompt that crashed the writer thread
MARK = "x" * 134 + "▶ “quoted” — ünïcode"
REPLY = {"units": [{"sentences": ["中文⟦a12 公式⟧句子"]}]}
SPEC = {"kind": "agent", "runtime": "claude-code", "model": "haiku", "id": "claude/claude-code/haiku"}


class Pipes(unittest.TestCase):
    def test_a_reply_outside_the_systems_encoding_is_read(self):
        # the child writes UTF-8 bytes itself: its own stdout would otherwise use the system's encoding too
        r = agents._run([sys.executable, "-c", "import sys; sys.stdout.buffer.write('▶ “quoted”'.encode())"], 30)
        self.assertEqual(r.stdout, "▶ “quoted”")

    def test_a_prompt_outside_the_systems_encoding_reaches_the_child(self):
        # the pipe every model call uses: raw text in, raw text back
        r = subprocess.run([sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
                           input=MARK, capture_output=True, text=True, timeout=10, **agents.TEXT)
        self.assertEqual(r.stdout, MARK)

    def test_a_json_rpc_line_with_utf8_is_read(self):
        # the scan's pipe to `codex app-server` and `pi --mode rpc`: JSON lines both ways
        child = ("import sys, json\n"
                 "for line in sys.stdin:\n"
                 "    out = json.dumps({'id': 1, 'name': '▶ “quoted”'}, ensure_ascii=False) + '\\n'\n"
                 "    sys.stdout.buffer.write(out.encode())\n"
                 "    sys.stdout.buffer.flush()\n")
        got = agents._rpc([sys.executable, "-c", child], [{"id": 1}], timeout=15)
        self.assertEqual((got.get(1) or {}).get("name"), "▶ “quoted”")

    def test_the_claude_call_sends_utf8(self):
        # the reported path itself: claude -p's pipe takes the prompt as UTF-8 text, not locale bytes
        seen = {}

        class Done:
            returncode, stderr = 0, ""
            stdout = json.dumps({"structured_output": {"ok": True}})

        def fake_run(*a, **kw):
            seen.update(kw, args=a)
            return Done()

        with mock.patch.object(agents, "path_of", return_value="claude"), \
             mock.patch.object(agents, "argv", side_effect=lambda p: [sys.executable]), \
             mock.patch.object(llm.subprocess, "run", side_effect=fake_run):
            out, _ = llm._claude("prompt with ▶", {}, "haiku", None, 10)
        self.assertEqual(out, {"ok": True})
        self.assertEqual(seen["encoding"], "utf-8")
        self.assertEqual(seen["input"], "prompt with ▶")

    def test_the_codex_call_sends_utf8(self):
        # run_codex's own pipe and the `-o` file it reads the reply from
        seen = {}

        class Done:
            returncode, stderr, stdout = 0, "", ""

        def fake_run(args, **kw):
            seen.update(kw, args=args)
            Path(args[args.index("-o") + 1]).write_text(json.dumps({"ok": True}), encoding="utf-8")
            return Done()

        with mock.patch.object(agents, "path_of", return_value="codex"), \
             mock.patch.object(agents, "argv", side_effect=lambda p: [sys.executable]), \
             mock.patch.object(agents.subprocess, "run", side_effect=fake_run):
            out, _ = agents.run_codex("gpt-test", "prompt with ▶", {"type": "object"}, "system", None, 10)
        self.assertEqual(out, {"ok": True})
        self.assertEqual(seen["encoding"], "utf-8")
        self.assertEqual(seen["input"], "system\n\nprompt with ▶")

    def test_the_pi_call_sends_utf8(self):
        seen = {}

        class Done:
            returncode, stderr = 0, ""
            stdout = json.dumps({"type": "agent_end", "messages": [{"role": "assistant", "content": [{"type": "text", "text": '{"ok": true}'}],
                                                                   "usage": {"cost": {"total": 0.1}}}]})

        def fake_run(*a, **kw):
            seen.update(kw)
            return Done()

        with mock.patch.object(agents.subprocess, "run", side_effect=fake_run):
            out, cost = agents._pi_once(["pi"], "body with ▶", {"type": "object"}, 10)
        self.assertEqual(out, {"ok": True})
        self.assertEqual(cost, 0.1)
        self.assertEqual(seen["encoding"], "utf-8")
        self.assertEqual(seen["input"], "body with ▶")

    def test_a_codex_config_with_utf8_is_read(self):
        # the scan reads ~/.codex/config.toml for the default effort; a comment in it may hold a typographic quote
        rows = [{"model": "gpt-test", "displayName": "GPT test", "supportedReasoningEfforts": [{"reasoningEffort": "high"}],
                 "defaultReasoningEffort": "low"}]
        old = os.environ.get("CODEX_HOME")
        try:
            with tempfile.TemporaryDirectory() as home:
                (Path(home) / "config.toml").write_text('model_reasoning_effort = "high"   # “high”\n', encoding="utf-8")
                os.environ["CODEX_HOME"] = home
                with mock.patch.object(agents, "_rpc", return_value={2: {"result": {"data": rows}}}):
                    out = agents._codex_models("codex")
        finally:
            if old is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = old
        self.assertEqual(out[0]["defaultEffort"], "high")   # read from the config, not the model's own default


class Replies(unittest.TestCase):
    def test_a_cached_reply_with_utf8_is_written_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            with mock.patch.object(llm, "_once", return_value=(REPLY, None)):
                rec, cached = llm.call("a prompt", {"type": "object"}, SPEC, cache)
            self.assertFalse(cached)
            self.assertEqual(rec["out"], REPLY)
            f, = cache.glob("*.json")
            data = f.read_bytes()
            data.decode("gbk")   # what is written is ASCII-escaped, so a GBK machine can read the file back
            self.assertEqual(json.loads(data.decode("utf-8"))["out"], REPLY)
            with mock.patch.object(llm, "_once", side_effect=AssertionError("the cache should have answered")):
                rec, cached = llm.call("a prompt", {"type": "object"}, SPEC, cache)
            self.assertTrue(cached)
            self.assertEqual(rec["out"], REPLY)

    def test_a_cache_file_a_failed_write_left_empty_is_made_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            with mock.patch.object(llm, "_once", return_value=(REPLY, None)):
                llm.call("a prompt", {"type": "object"}, SPEC, cache)
            f, = cache.glob("*.json")
            f.write_bytes(b"")
            second = {"units": [{"sentences": ["第二次"]}]}
            with mock.patch.object(llm, "_once", return_value=(second, None)):
                rec, cached = llm.call("a prompt", {"type": "object"}, SPEC, cache)
            self.assertFalse(cached)
            self.assertEqual(rec["out"], second)
            self.assertGreater(f.stat().st_size, 0)

    def test_a_cache_from_before_ascii_replies_is_made_again(self):
        # old replies were ensure_ascii=False in the system's encoding — or UTF-8 on another machine; no marker tells
        # them apart, and reading either the wrong way would put mojibake into the document, so both are a miss (once)
        old = {"units": [{"sentences": ["一"]}]}
        old_json = json.dumps({"out": old, "cost": None, "models": ["m"]}, ensure_ascii=False)
        for old_bytes in (old_json.encode(locale.getpreferredencoding(False) or "utf-8"), old_json.encode("utf-8")):
            with tempfile.TemporaryDirectory() as tmp:
                cache = Path(tmp)
                with mock.patch.object(llm, "_once", return_value=(REPLY, None)):
                    llm.call("a prompt", {"type": "object"}, SPEC, cache)
                f, = cache.glob("*.json")
                f.write_bytes(old_bytes)
                second = {"units": [{"sentences": ["第二次"]}]}
                with mock.patch.object(llm, "_once", return_value=(second, None)) as once:
                    rec, cached = llm.call("a prompt", {"type": "object"}, SPEC, cache)
                self.assertFalse(cached)
                self.assertEqual(once.call_count, 1)
                self.assertEqual(rec["out"], second)
                f.read_bytes().decode("ascii")   # rewritten in the new form


class Saved(unittest.TestCase):
    def setUp(self):
        self.old = store.DATA
        store.DATA = Path(tempfile.mkdtemp())

    def tearDown(self):
        store.DATA = self.old

    def test_a_layer_in_a_language_gbk_lacks_is_saved(self):
        # Korean and Hindi are offered languages (langs.py) and are not in GBK at all
        data = {"version": "t", "model": "m", "translation": {"units": {"u1": "한국어 ⟦a1⟧"}}}
        store.write("web-ko", "ko", data)
        self.assertEqual(store.read("web-ko", "ko"), data)

    def test_notes_in_a_language_gbk_lacks_are_saved(self):
        notes._file("web-ko").parent.mkdir(parents=True, exist_ok=True)
        data = {"format": notes.FORMAT, "version": notes.VERSION, "notes": [{"id": "n1", "text": "힌디어 답변 ⟦a2⟧"}]}
        notes._write("web-ko", data)
        self.assertEqual(notes.read("web-ko")["notes"], data["notes"])

    def test_settings_with_a_name_gbk_lacks_are_saved(self):
        s = {"providers": [{"key": "k", "name": "한국어 제공자", "base": "https://x", "api_key": "", "models": []}],
             "use_thoughtdag_env": False}
        old = models.SETTINGS
        try:
            models.SETTINGS = Path(tempfile.mkdtemp()) / "settings.json"
            models.save_settings(s)
            self.assertEqual(models.load_settings()["providers"][0]["name"], "한국어 제공자")
        finally:
            models.SETTINGS = old


if __name__ == "__main__":
    unittest.main()
