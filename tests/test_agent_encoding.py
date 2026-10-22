"""UTF-8 model cache and subprocess behavior on a Chinese Windows."""
import json
import locale
import os
import subprocess
import threading
import unittest
from pathlib import Path
from unittest import mock

from textfold import library, llm, local, models, notes, store, zotero

MARK = "x" * 134 + "▶ “quoted” — ünïcode"
REPLY = {"units": [{"sentences": ["中文⟦a12 公式⟧句子"]}]}
SPEC = {"kind": "api", "protocol": "openai", "base": "http://127.0.0.1:3425/v1", "api_key": "magpie",
        "model": "auto/model", "id": "auto/model"}


class Pipes(unittest.TestCase):
    def test_a_prompt_outside_the_systems_encoding_reaches_the_child(self):
        r = subprocess.run([os.sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
                           input=MARK, capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
        self.assertEqual(r.stdout, MARK)


class Imports(unittest.TestCase):
    def test_a_markdown_file_saved_in_gbk_or_with_a_bom_is_imported(self):
        with __import__("tempfile").TemporaryDirectory() as tmp:
            old = store.DATA
            store.DATA = Path(tmp) / "data"
            try:
                gbk = Path(tmp) / "旧笔记.md"
                gbk.write_bytes("# 中文标题\n\n正文。\n".encode("gbk"))
                pid = local.import_file(gbk)
                meta = json.loads((store.pdir(pid) / "meta.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["title"], "中文标题")
                bom = Path(tmp) / "带 BOM.md"
                bom.write_bytes(b"\xef\xbb\xbf" + "# 另一个标题\n\n正文。\n".encode("utf-8"))
                pid = local.import_file(bom)
                meta = json.loads((store.pdir(pid) / "meta.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["title"], "另一个标题")
                crlf = Path(tmp) / "CRLF.md"
                crlf.write_bytes("# 标题\r\n\r\n正文。\r\n".encode("utf-8"))
                self.assertEqual(local._read(crlf), "# 标题\n\n正文。\n")   # (as Path.read_text gives it: a re-import keeps its id)
            finally:
                store.DATA = old


class OldFiles(unittest.TestCase):
    """A file from an older TextFold in the system's codepage is not read as empty and saved over before R3 migrates it."""

    def setUp(self):
        self.tmp = __import__("tempfile").TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old = store.DATA
        store.DATA = Path(self.tmp.name)
        self.addCleanup(setattr, store, "DATA", self.old)

    def test_a_gbk_library_is_not_read_as_empty_and_saved_over(self):
        p = library.path()
        raw = json.dumps({"folders": [{"id": "f1", "name": "我的文件夹"}], "of": {}}, ensure_ascii=False).encode("gbk")
        p.write_bytes(raw)
        with self.assertRaises(UnicodeDecodeError):
            library.load()
        with self.assertRaises(UnicodeDecodeError):
            library.stamp([])
        with self.assertRaises(UnicodeDecodeError):
            library.opened("md-0123456789abcdef")   # (the overwrite path: load, change, save)
        self.assertEqual(p.read_bytes(), raw)

    def test_a_gbk_zotero_index_is_not_read_as_empty_and_saved_over(self):
        p = zotero._links_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps({"users/0/A": {"paper": "pdf-x", "title": "我的论文"}}, ensure_ascii=False).encode("gbk")
        p.write_bytes(raw)
        with self.assertRaises(UnicodeDecodeError):
            zotero.links()
        with self.assertRaises(UnicodeDecodeError):
            zotero.link("users/0", "B", "pdf-y", "另一篇")
        self.assertEqual(p.read_bytes(), raw)


class Replies(unittest.TestCase):
    def test_a_cached_reply_with_utf8_is_written_and_read(self):
        with __import__("tempfile").TemporaryDirectory() as tmp:
            cache = Path(tmp)
            with mock.patch.object(llm, "_once", return_value=(REPLY, None)):
                rec, cached = llm.call("a prompt", {"type": "object"}, SPEC, cache)
            self.assertFalse(cached)
            self.assertEqual(rec["out"], REPLY)
            f, = cache.glob("*.json")
            data = f.read_bytes()
            data.decode("gbk")
            self.assertEqual(json.loads(data.decode("utf-8"))["out"], REPLY)
            with mock.patch.object(llm, "_once", side_effect=AssertionError("the cache should have answered")):
                rec, cached = llm.call("a prompt", {"type": "object"}, SPEC, cache)
            self.assertTrue(cached)
            self.assertEqual(rec["out"], REPLY)

    def test_a_cache_file_a_failed_write_left_empty_is_made_again(self):
        with __import__("tempfile").TemporaryDirectory() as tmp:
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
        old = {"units": [{"sentences": ["一"]}]}
        old_json = json.dumps({"out": old, "cost": None, "models": ["m"]}, ensure_ascii=False)
        for old_bytes in (old_json.encode(locale.getpreferredencoding(False) or "utf-8"), old_json.encode("utf-8")):
            with __import__("tempfile").TemporaryDirectory() as tmp:
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
                f.read_bytes().decode("ascii")


class Saved(unittest.TestCase):
    def test_settings_with_a_name_gbk_lacks_are_saved(self):
        s = {"providers": [{"key": "k", "name": "한국어 제공자", "base": "https://x", "api_key": "", "models": []}],
             "use_thoughtdag_env": False}
        old = models.SETTINGS
        try:
            models.SETTINGS = Path(__import__("tempfile").mkdtemp()) / "settings.json"
            models.save_settings(s)
            self.assertEqual(models.load_settings()["providers"][0]["name"], "한국어 제공자")
        finally:
            models.SETTINGS = old

    def test_concurrent_settings_updates_keep_both_fields(self):
        old = models.SETTINGS
        with __import__("tempfile").TemporaryDirectory() as tmp:
            try:
                models.SETTINGS = Path(tmp) / "settings.json"
                models.save_settings({"providers": [], "use_thoughtdag_env": False, "pdf_tier": "fast", "zotero": {}})
                gate = threading.Barrier(3)
                errors = []

                def update(change):
                    try:
                        gate.wait(timeout=2)
                        models.update_settings(change)
                    except Exception as e:
                        errors.append(e)

                workers = [threading.Thread(target=update, args=(lambda s: s.update(pdf_tier="accurate"),)),
                           threading.Thread(target=update, args=(lambda s: s.update(zotero={"library": "groups/42"}),))]
                for worker in workers:
                    worker.start()
                gate.wait(timeout=2)
                for worker in workers:
                    worker.join(timeout=2)
                    self.assertFalse(worker.is_alive())
                self.assertEqual(errors, [])
                saved = models.load_settings()
                self.assertEqual(saved["pdf_tier"], "accurate")
                self.assertEqual(saved["zotero"]["library"], "groups/42")
                self.assertFalse(list(models.SETTINGS.parent.glob("settings-*.tmp")))
            finally:
                models.SETTINGS = old

    def test_layer_and_note_text_round_trip(self):
        old = store.DATA
        store.DATA = Path(__import__("tempfile").mkdtemp())
        try:
            data = {"version": "t", "model": "m", "translation": {"units": {"u1": "한국어 ⟦a1⟧"}}}
            store.write("web-ko", "ko", data)
            self.assertEqual(store.read("web-ko", "ko"), data)
            notes._file("web-ko").parent.mkdir(parents=True, exist_ok=True)
            saved = {"format": notes.FORMAT, "version": notes.VERSION, "notes": [{"id": "n1", "text": "힌디어 답변 ⟦a2⟧"}]}
            notes._write("web-ko", saved)
            self.assertEqual(notes.read("web-ko")["notes"], saved["notes"])
        finally:
            store.DATA = old


if __name__ == "__main__":
    unittest.main()
