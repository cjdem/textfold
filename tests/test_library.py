"""library.py: the reader's folders in the library, and when each document came in and was last opened, in a data
folder of its own (store.DATA, set to a temporary one for each test).

Run from the repo root:
    python -m unittest discover tests
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textfold import library, store


class Library(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def paper(self, pid, at):
        d = store.pdir(pid)
        d.mkdir(parents=True)
        for name in ("meta.json", "source.md"):
            (d / name).write_text("{}", encoding="utf-8")
            os.utime(d / name, (at, at))
        return {"id": pid, "title": pid}

    def test_folders_made_named_and_filled(self):
        a = library.change({"op": "new", "name": "  Thesis   chapter 2 "})["folders"][0]
        self.assertEqual(a["name"], "Thesis chapter 2")
        b = library.change({"op": "new", "name": "Reading group"})["folders"][1]
        got = library.change({"op": "move", "papers": ["2512.24601", "wiki-en-13460"], "folder": a["id"]})
        self.assertEqual(got["of"], {"2512.24601": a["id"], "wiki-en-13460": a["id"]})
        got = library.change({"op": "move", "papers": ["2512.24601"], "folder": b["id"]})   # (one folder at a time)
        self.assertEqual(got["of"]["2512.24601"], b["id"])
        got = library.change({"op": "move", "papers": ["wiki-en-13460"], "folder": None})
        self.assertNotIn("wiki-en-13460", got["of"])
        self.assertEqual(library.change({"op": "rename", "id": b["id"], "name": "Group"})["folders"][1]["name"], "Group")
        self.assertEqual(json.loads(library.path().read_text(encoding="utf-8"))["folders"][1]["name"], "Group")

    def test_a_new_folder_with_the_document_it_was_made_for(self):   # (the menu a document's right click opens)
        a = library.change({"op": "new", "name": "A"})["folders"][0]
        library.change({"op": "move", "papers": ["2512.24601"], "folder": a["id"]})
        got = library.change({"op": "new", "name": "B", "papers": ["2512.24601"]})
        self.assertEqual(got["of"], {"2512.24601": got["folders"][1]["id"]})
        with self.assertRaises(ValueError):
            library.change({"op": "new", "name": "C", "papers": ["../etc"]})
        self.assertEqual(len(library.folders()["folders"]), 2)

    def test_a_document_named_in_the_library(self):
        listed = library.stamp([self.paper("pdf-0123456789abcdef", 1_790_000_000), self.paper("2512.24601", 1_790_000_000)])
        self.assertNotIn("name", listed[0])
        library.name("pdf-0123456789abcdef", "  Smith   2024 review ")
        listed = library.stamp([{"id": "pdf-0123456789abcdef", "title": "untitled"}, {"id": "2512.24601", "title": "x"}])
        self.assertEqual(listed[0]["name"], "Smith 2024 review")
        self.assertEqual(listed[0]["title"], "untitled")   # (its own title stays its own)
        self.assertNotIn("name", listed[1])
        self.assertEqual(library.name_of("pdf-0123456789abcdef"), "Smith 2024 review")
        self.assertEqual(json.loads(library.path().read_text(encoding="utf-8"))["names"], {"pdf-0123456789abcdef": "Smith 2024 review"})
        library.name("pdf-0123456789abcdef", "张三 的综述")
        self.assertTrue(library.path().read_text(encoding="utf-8").isascii())   # (the library stays plain ASCII)
        self.assertEqual(library.name_of("pdf-0123456789abcdef"), "张三 的综述")
        library.name("pdf-0123456789abcdef", "x" * 250)
        self.assertEqual(len(library.name_of("pdf-0123456789abcdef")), 200)   # (a name is at most 200 characters)
        library.name("pdf-0123456789abcdef", "")   # (cleared: its title again)
        self.assertIsNone(library.name_of("pdf-0123456789abcdef"))
        library.name("2512.24601", "Kept")
        self.assertEqual(library.forget("2512.24601")["name"], "Kept")
        self.assertIsNone(library.name_of("2512.24601"))
        with self.assertRaises(ValueError):
            library.name("../etc", "x")
        # what a hand-edited library carries is not trusted
        library.path().write_text(json.dumps({"names": {"2512.24601": ["x"], "../etc": "y", "pdf-0123456789abcdef": ""}}), encoding="utf-8")
        self.assertEqual(library.load()["names"], {})

    def test_a_folder_deleted_leaves_its_documents(self):
        a = library.change({"op": "new", "name": "Old"})["folders"][0]
        library.change({"op": "move", "papers": ["2512.24601"], "folder": a["id"]})
        got = library.change({"op": "delete", "id": a["id"]})
        self.assertEqual(got, {"folders": [], "of": {}})

    def test_what_is_refused(self):
        a = library.change({"op": "new", "name": "A"})["folders"][0]
        for body in ({"op": "new", "name": "   "}, {"op": "rename", "id": "f-none", "name": "B"}, {"op": "delete", "id": "f-none"},
                     {"op": "move", "papers": ["2512.24601"], "folder": "f-none"}, {"op": "move", "papers": ["../etc"], "folder": a["id"]},
                     {"op": "move", "papers": "2512.24601", "folder": a["id"]}, {"op": "drop"}):
            with self.assertRaises(ValueError, msg=body):
                library.change(body)
        self.assertEqual(library.folders()["of"], {})

    def test_when_it_came_in_is_its_oldest_file_and_stays(self):
        listed = library.stamp([self.paper("2512.24601", 1_790_000_000), self.paper("wiki-en-13460", 1_791_000_000)])
        self.assertEqual([p["added"] for p in listed], [1_790_000_000, 1_791_000_000])
        self.assertEqual([p["opened"] for p in listed], [None, None])
        os.utime(store.pdir("2512.24601") / "meta.json", (1_700_000_000, 1_700_000_000))   # (its files changed since: the date stays)
        self.assertEqual(library.stamp([{"id": "2512.24601"}])[0]["added"], 1_790_000_000)

    def test_opened_and_forgotten(self):
        library.stamp([self.paper("2512.24601", 1_790_000_000)])
        library.opened("2512.24601")
        library.opened("../etc")   # (not a document's id: nothing)
        self.assertGreater(library.stamp([{"id": "2512.24601"}])[0]["opened"], 1_790_000_000)
        a = library.change({"op": "new", "name": "A"})["folders"][0]
        library.change({"op": "move", "papers": ["2512.24601"], "folder": a["id"]})
        kept = library.forget("2512.24601")
        self.assertEqual((kept["of"], kept["added"]), (a["id"], 1_790_000_000))
        self.assertGreater(kept["opened"], 1_790_000_000)
        d = library.load()
        self.assertEqual((d["of"], d["names"], d["added"], d["opened"]), ({}, {}, {}, {}))
        self.assertEqual(library.forget("2512.24601"), {})   # (gone already: nothing to remember)

    def test_a_deleted_document_can_be_remembered(self):
        library.stamp([self.paper("2512.24601", 1_790_000_000)])
        library.opened("2512.24601")
        a = library.change({"op": "new", "name": "A"})["folders"][0]
        library.change({"op": "move", "papers": ["2512.24601"], "folder": a["id"]})
        library.name("2512.24601", "Smith 2024 review")
        kept = library.forget("2512.24601")
        library.remember("2512.24601", kept)
        d = library.load()
        self.assertEqual((d["of"]["2512.24601"], d["added"]["2512.24601"]), (a["id"], 1_790_000_000))
        self.assertEqual(d["opened"]["2512.24601"], kept["opened"])
        self.assertEqual(d["names"]["2512.24601"], "Smith 2024 review")   # (the name came with the place)
        # a folder deleted while the document was in the trash: the dates still come back, unfiled
        library.forget("2512.24601")
        library.change({"op": "delete", "id": a["id"]})
        library.remember("2512.24601", kept)
        d = library.load()
        self.assertEqual((d["of"], d["added"]["2512.24601"]), ({}, 1_790_000_000))
        # what a damaged or foreign file could carry is dropped; an unknown id is not written
        library.remember("2512.24601", {"of": "f-gone", "added": "yesterday", "opened": True, "names": "x"})
        self.assertEqual((library.load()["of"], library.load()["added"]["2512.24601"]), ({}, 1_790_000_000))
        self.assertEqual(library.name_of("2512.24601"), "Smith 2024 review")   # (a "names" key is not a name)
        library.remember("../etc", {"added": 1})
        self.assertNotIn("../etc", library.load()["added"])

    def test_a_hostile_place_is_dropped(self):
        library.remember("2512.24601", {"of": ["f-1"], "name": ["x"], "added": 10 ** 400, "opened": float("nan")})
        library.remember("2512.24601", {"name": "   "})
        d = library.load()
        self.assertEqual((d["of"], d["names"], d["added"], d["opened"]), ({}, {}, {}, {}))
        self.assertFalse(library.path().exists())   # (nothing written at all)

    def test_a_damaged_file_reads_as_none(self):
        library.path().write_text("{not json", encoding="utf-8")
        self.assertEqual(library.folders(), {"folders": [], "of": {}})


if __name__ == "__main__":
    unittest.main()
