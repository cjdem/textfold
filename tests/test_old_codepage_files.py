"""A library TextFold 0.10.9 or before left on a Chinese Windows: its files in the system's codepage (GBK), with
Windows' line ends. 0.10.10 reads and writes UTF-8, and read such a file as UTF-8: "'utf-8' codec can't decode byte
0xa1" (the first byte of 。 in GBK) on the first page, a library read as empty. Now each is read in the codepage, left
as it is, and written again as UTF-8 by its next save. A scratch data folder; the codepage is GBK's here, whatever this
computer's.

Run from the repo root:
    python -m unittest discover tests
"""
import json
import locale
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import library, local, models, notes, store, zotero


def as_old_windows(f):
    """The file as the old TextFold wrote it on a Chinese Windows: its own characters in GBK, CRLF. (What is written
    now is ASCII-escaped, so the characters are written out first, as the old writer did.)"""
    p = Path(f)
    if p.suffix == ".json":
        text = json.dumps(json.loads(p.read_text(encoding="utf-8")), ensure_ascii=False, indent=1)
    else:
        text = p.read_text(encoding="utf-8")
    p.write_bytes(text.replace("\n", "\r\n").encode("gbk"))


class OldCodepageFiles(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        for p in (mock.patch.object(store, "DATA", self.tmp / "data"), mock.patch.object(store, "codepage", return_value="gbk"),
                  mock.patch.object(models, "SETTINGS", self.tmp / "settings.json")):
            p.start()
            self.addCleanup(p.stop)
        self.pid = local.import_text("# 第三方跨境支付的法律监管\n\n近年来，跨境电子商务迅速发展。监管规则大多针对银行业务制定。\n")
        self.d = store.pdir(self.pid)

    def old(self, *names):
        """The paper's files as the old TextFold wrote them; their bytes, for "left as it was"."""
        for name in names:
            as_old_windows(self.d / name)
        return {name: (self.d / name).read_bytes() for name in names}

    def test_a_paper_written_in_gbk_opens_and_is_left_as_it_was(self):
        raw = self.old("meta.json", "source.html")
        with self.assertRaises(UnicodeDecodeError):
            raw["meta.json"].decode("utf-8")   # (what 0.10.10 to 0.10.13 met)
        doc = store.assemble(self.pid)
        self.assertEqual(doc["meta"]["title"], "第三方跨境支付的法律监管")
        self.assertIn("跨境电子商务", "".join(t.get("t", "") for u in doc["units"].values() for t in u["toks"]))
        for name, before in raw.items():
            self.assertEqual((self.d / name).read_bytes(), before)   # (a read writes nothing)
        self.assertEqual(store.assemble(self.pid)["meta"]["title"], "第三方跨境支付的法律监管")

    def test_the_list_of_papers_and_their_translated_titles(self):
        layers = self.d / "layers"
        layers.mkdir(exist_ok=True)
        (layers / "tr-zh.json").write_text(json.dumps({"title": "跨境支付。", "units": {}, "chunks": {}, "version": "v1"}, ensure_ascii=False, indent=1), encoding="utf-8")
        raw = self.old("meta.json")
        as_old_windows(layers / "tr-zh.json")
        row = next(p for p in store.papers() if p["id"] == self.pid)
        self.assertEqual(row["title"], "第三方跨境支付的法律监管")
        self.assertEqual(row["titles"], {"zh": "跨境支付。"})
        self.assertEqual((self.d / "meta.json").read_bytes(), raw["meta.json"])

    def test_the_library_its_folders_kept_and_its_next_save_writes_utf8(self):
        library.path().write_text(json.dumps({"folders": [{"id": "f1", "name": "法学论文"}], "of": {self.pid: "f1"}}, ensure_ascii=False, indent=1), encoding="utf-8")
        as_old_windows(library.path())
        before = library.path().read_bytes()
        self.assertEqual([f["name"] for f in library.load()["folders"]], ["法学论文"])   # (read as empty before, and saved so)
        self.assertEqual(library.path().read_bytes(), before)   # (a read writes nothing)
        library.change({"op": "new", "name": "新文件夹"})   # (the save path: atomic, and UTF-8 now)
        saved = json.loads(library.path().read_bytes().decode("utf-8"))
        self.assertEqual([f["name"] for f in saved["folders"]], ["法学论文", "新文件夹"])

    def test_the_settings_and_the_notes(self):
        models.SETTINGS.write_text(json.dumps({"model": "claude/claude-code/sonnet", "use_thoughtdag_env": False, "name": "读者。"}, ensure_ascii=False, indent=1), encoding="utf-8")
        as_old_windows(models.SETTINGS)
        before = models.SETTINGS.read_bytes()
        self.assertEqual(models.load_settings()["model"], "claude/claude-code/sonnet")
        self.assertEqual(models.SETTINGS.read_bytes(), before)
        models.update_settings(lambda s: s.update(pdf_tier="accurate"))
        saved = json.loads(models.SETTINGS.read_bytes().decode("utf-8"))
        self.assertEqual((saved["model"], saved["pdf_tier"]), ("claude/claude-code/sonnet", "accurate"))

        nf = notes._file(self.pid)
        nf.parent.mkdir(parents=True, exist_ok=True)
        nf.write_text(json.dumps({"notes": [{"id": "n1", "text": "这一段说明了监管的困境。"}]}, ensure_ascii=False, indent=1), encoding="utf-8")
        as_old_windows(nf)
        before = nf.read_bytes()
        self.assertEqual(notes.read(self.pid)["notes"][0]["text"], "这一段说明了监管的困境。")
        self.assertEqual(nf.read_bytes(), before)
        notes.put(self.pid, {"id": "n-2", "anchor": {}, "text": "新笔记"})
        saved = json.loads(nf.read_bytes().decode("utf-8"))
        self.assertEqual([n["text"] for n in saved["notes"]], ["这一段说明了监管的困境。", "新笔记"])

    def test_a_zotero_index_written_in_gbk_is_read_and_its_next_save_writes_utf8(self):
        p = zotero._links_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"users/0/A": {"paper": "pdf-x", "title": "我的论文"}}, ensure_ascii=False), encoding="utf-8")
        as_old_windows(p)
        before = p.read_bytes()
        self.assertEqual(zotero.links(), {"users/0/A": "pdf-x"})   # (read as empty before, and a link saved so)
        self.assertEqual(p.read_bytes(), before)
        zotero.link("users/0", "B", "pdf-y", "另一篇")
        saved = json.loads(p.read_bytes().decode("utf-8"))
        self.assertEqual(saved["users/0/A"]["title"], "我的论文")   # (the old row is kept)
        self.assertEqual(saved["users/0/B"]["title"], "另一篇")

    def test_a_file_in_utf8_reads_as_it_did(self):
        f = self.tmp / "x.json"
        f.write_bytes('{"a": "跨境"}\r\n'.encode("utf-8"))
        self.assertEqual(store.read_text(f), '{"a": "跨境"}\n')
        self.assertEqual(f.read_bytes(), '{"a": "跨境"}\r\n'.encode("utf-8"))   # (left as it is)

    def test_a_file_in_neither_encoding_is_an_error_and_left_as_it_was(self):
        bad = self.tmp / "bad.json"
        bad.write_bytes(b'{"a": "\xff\xfe"}')   # in neither UTF-8 nor GBK
        with self.assertRaises(UnicodeDecodeError):
            store.read_text(bad)
        self.assertEqual(bad.read_bytes(), b'{"a": "\xff\xfe"}')   # (never read as empty and saved over)

class Codepage(unittest.TestCase):
    def test_before_python_311_the_codepage_comes_from_windows_ansi_code_page(self):
        if os.name != "nt":
            self.skipTest("GetACP is the stand-in before Python 3.11, and this fork runs on Windows")
        import ctypes
        with mock.patch.object(locale, "getencoding", None):   # (as on Python 3.9 and 3.10)
            self.assertEqual(store.codepage(), f"cp{ctypes.windll.kernel32.GetACP()}")


class Undecodable(unittest.TestCase):
    """A file in neither encoding: the guarded readers raise, so the save that follows a read cannot write emptiness
    over it. (UnicodeDecodeError is a ValueError, which those readers catch for other reasons: the order matters.)"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for p in (mock.patch.object(store, "DATA", Path(tmp.name)), mock.patch.object(store, "codepage", return_value="gbk")):
            p.start()
            self.addCleanup(p.stop)

    def test_an_undecodable_library_is_not_read_as_empty_and_saved_over(self):
        p = library.path()
        raw = b'{"folders": [{"id": "f1", "name": "\xff\xfe"}]}'
        p.write_bytes(raw)
        for call in (library.load, lambda: library.stamp([]), lambda: library.opened("md-0123456789abcdef")):
            with self.assertRaises(UnicodeDecodeError):
                call()
        self.assertEqual(p.read_bytes(), raw)

    def test_an_undecodable_zotero_index_is_not_read_as_empty_and_saved_over(self):
        p = zotero._links_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = b'{"users/0/A": {"paper": "pdf-x", "title": "\xff\xfe"}}'
        p.write_bytes(raw)
        with self.assertRaises(UnicodeDecodeError):
            zotero.links()
        with self.assertRaises(UnicodeDecodeError):
            zotero.link("users/0", "B", "pdf-y", "another")
        self.assertEqual(p.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
