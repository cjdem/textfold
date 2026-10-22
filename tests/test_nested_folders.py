"""Folders inside folders: a folder's parent in library.json (a parent that is gone, or a loop, read as at the top),
deleting a folder moving what is in it up into its parent, the sidebar's tree and its drag, and the two languages' words
for a folder made inside another and for moving one up.

There is no JS test runner here, so the sidebar is held as what a Python test can see of it: the drawing recurses by
parent, the menus list the tree with how deep each folder is, a folder is dragged into another but not into itself, and
a folder's count takes in the documents in the folders inside it.

Run from the repo root:
    python -m unittest discover tests
"""
import ast
import json
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from textfold import library, store

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "textfold" / "web"


def text(name):
    return (WEB / name).read_text(encoding="utf-8")


def body_of(js, start):
    """The body of the function whose first line starts at `start` (up to the closing two-space brace)."""
    at = js.index(start)
    end = js.index("\n  }", at)
    return js[at:end]


class Library(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patch = mock.patch.object(store, "DATA", Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def made(self, name, parent=None):
        return library.change({"op": "new", "name": name, **({"parent": parent} if parent else {})})["folders"][-1]

    def test_a_folder_is_made_inside_another_and_keeps_its_parent(self):
        a = self.made("Thesis")
        b = self.made("Chapter 2", a["id"])
        self.assertEqual(b["parent"], a["id"])
        self.assertNotIn("parent", a)   # (at the top: nothing to write)
        self.assertEqual(library.load()["folders"][1]["parent"], a["id"])   # (the file carries it)
        got = library.change({"op": "move", "papers": ["2512.24601"], "folder": b["id"]})
        self.assertEqual(got["of"], {"2512.24601": b["id"]})
        with self.assertRaises(ValueError):   # (the folder it would go in must be there)
            self.made("Lost", "f-none")

    def test_a_folder_moves_up_a_level_or_to_the_top(self):
        a = self.made("Thesis")
        b = self.made("Chapter 2", a["id"])
        c = self.made("Notes")
        got = library.change({"op": "nest", "id": b["id"], "parent": c["id"]})["folders"]
        self.assertEqual(got[1]["parent"], c["id"])
        self.assertEqual(library.change({"op": "nest", "id": b["id"], "parent": None})["folders"][1].get("parent"), None)
        with self.assertRaises(ValueError):
            library.change({"op": "nest", "id": b["id"], "parent": "f-none"})

    def test_a_folder_cannot_go_inside_itself_nor_inside_one_it_holds(self):
        a = self.made("A")
        b = self.made("B", a["id"])
        c = self.made("C", b["id"])
        d = self.made("D")
        for fid, parent in ((a["id"], a["id"]), (a["id"], b["id"]), (a["id"], c["id"]), (b["id"], c["id"])):
            with self.assertRaises(ValueError, msg=(fid, parent)):
                library.change({"op": "nest", "id": fid, "parent": parent})
        self.assertEqual(library.load()["folders"][2]["parent"], b["id"])   # (nothing moved)
        library.change({"op": "nest", "id": a["id"], "parent": d["id"]})   # (a folder beside it is fine)
        self.assertEqual(library.load()["folders"][0]["parent"], d["id"])
        library.change({"op": "nest", "id": c["id"], "parent": a["id"]})   # (up into one above it is fine too)
        self.assertEqual(library.load()["folders"][2]["parent"], a["id"])

    def test_deleting_a_folder_moves_what_is_in_it_up(self):
        a = self.made("Thesis")
        b = self.made("Chapter 2", a["id"])
        c = self.made("Section 2.1", b["id"])
        library.change({"op": "move", "papers": ["2512.24601"], "folder": b["id"]})
        library.change({"op": "move", "papers": ["wiki-en-13460"], "folder": c["id"]})
        got = library.change({"op": "delete", "id": b["id"]})   # (its folder and its document go up into Thesis)
        self.assertEqual([f["id"] for f in got["folders"]], [a["id"], c["id"]])
        self.assertEqual(got["folders"][1]["parent"], a["id"])
        self.assertEqual(got["of"], {"2512.24601": a["id"], "wiki-en-13460": c["id"]})   # (a folder keeps its own)
        got = library.change({"op": "delete", "id": a["id"]})   # (at the top: its own go to the top, its documents out)
        self.assertEqual(got["folders"], [{"id": c["id"], "name": "Section 2.1"}])
        self.assertEqual(got["of"], {"wiki-en-13460": c["id"]})

    def test_a_parent_that_is_gone_or_loops_is_at_the_top(self):
        # a file edited by hand: a parent that is not there, two folders under each other, a parent that is not an id
        library.path().write_text(json.dumps({"folders": [
            {"id": "f-a", "name": "A", "parent": "f-gone"},
            {"id": "f-b", "name": "B", "parent": "f-c"},
            {"id": "f-c", "name": "C", "parent": "f-b"},
            {"id": "f-d", "name": "D", "parent": 7},
            {"id": "f-e", "name": "E", "parent": "f-a"},
        ]}), encoding="utf-8")
        got = {f["id"]: f for f in library.load()["folders"]}
        self.assertNotIn("parent", got["f-a"])   # (the parent is gone)
        self.assertNotIn("parent", got["f-d"])   # (not an id)
        self.assertEqual(got["f-e"]["parent"], "f-a")   # (a chain that is there stays)
        # a loop is broken at one of its edges: no folder is under itself, however many steps it takes
        for f in got.values():
            seen, p = {f["id"]}, f.get("parent")
            while p is not None:
                self.assertNotIn(p, seen, f)   # (a loop: it must end)
                seen.add(p)
                p = got[p].get("parent")
        library.change({"op": "nest", "id": "f-a", "parent": "f-b"})   # (and a repaired one can be nested again)
        self.assertEqual({f["id"]: f for f in library.load()["folders"]}["f-a"]["parent"], "f-b")

    def test_a_deleted_document_returns_to_its_nested_folder(self):
        a = self.made("A")
        b = self.made("B", a["id"])
        c = self.made("C", b["id"])
        library.change({"op": "move", "papers": ["2512.24601"], "folder": c["id"]})
        library.name("2512.24601", "Smith 2024 review")
        kept = library.forget("2512.24601")
        library.remember("2512.24601", kept)
        d = library.load()
        self.assertEqual((d["of"]["2512.24601"], d["names"]["2512.24601"]), (c["id"], "Smith 2024 review"))
        library.forget("2512.24601")
        library.change({"op": "delete", "id": c["id"]})   # (the folder goes while the document is in the trash)
        library.remember("2512.24601", kept)
        d = library.load()
        self.assertEqual((d["of"], d["names"]["2512.24601"]), ({}, "Smith 2024 review"))   # (dates and name, unfiled)

    def test_nest_and_delete_from_several_writers_keep_a_tree(self):
        a = self.made("A")
        b = self.made("B", a["id"])
        kids = [self.made(f"K{i}", b["id"])["id"] for i in range(6)]
        failed = []

        def work(fid, i):
            try:
                for n in range(8):
                    library.change({"op": "nest", "id": fid, "parent": a["id"] if n % 2 else b["id"]})
                    tmp = library.change({"op": "new", "name": f"T{i}-{n}", "parent": fid})["folders"][-1]["id"]
                    library.change({"op": "delete", "id": tmp})   # (an empty one, lifted nowhere)
            except Exception as e:  # noqa: BLE001
                failed.append(e)

        threads = [threading.Thread(target=work, args=(fid, i)) for i, fid in enumerate(kids)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(failed, [])
        d = library.load()
        ids = {f["id"] for f in d["folders"]}
        by = {f["id"]: f for f in d["folders"]}
        for f in d["folders"]:
            self.assertIn(f.get("parent"), ids | {None}, f)
            seen, p = {f["id"]}, f.get("parent")
            while p is not None:   # (every chain ends: no loop, no dangling parent)
                self.assertNotIn(p, seen, f)
                seen.add(p)
                p = by[p].get("parent")
        for fid in d["of"].values():
            self.assertIn(fid, ids)
        self.assertEqual({f["id"] for f in d["folders"] if f.get("parent") is None}, {a["id"]})   # (one root: nothing was orphaned)
        for fid in ids:   # (and everything is still under it)
            seen, p = {fid}, by[fid].get("parent")
            while p is not None:
                seen.add(p)
                p = by[p].get("parent")
            self.assertIn(a["id"], seen, fid)

    def test_two_writers_do_not_corrupt_the_tree(self):
        a = self.made("Thesis")
        failed = []

        def make(i):
            try:
                self.made(f"K{i}", a["id"])
            except Exception as e:   # noqa: BLE001  (a writer failing is the finding)
                failed.append(e)

        threads = [threading.Thread(target=make, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(failed, [])
        d = json.loads(library.path().read_text(encoding="utf-8"))
        ids = [f["id"] for f in d["folders"]]
        self.assertEqual(len(ids), 13)
        self.assertEqual(len(set(ids)), 13)   # (each change read what the one before wrote)
        self.assertEqual([f.get("parent") for f in d["folders"][1:]], [a["id"]] * 12)


class Sidebar(unittest.TestCase):
    def test_the_sidebar_draws_folders_inside_folders(self):
        js = text("app.js")
        self.assertIn("function kidsOf(id) { return folders.folders.filter((f) => (f.parent || null) === id); }", js)
        self.assertIn("for (const f of folders.folders) if (out.has(f.parent) && !out.has(f.id)) { out.add(f.id); more = true; }", js)   # (however deep)
        self.assertIn("const fresh = (parent) => (editing === 'new' && within === parent ?", js)
        self.assertIn("const ps = docs.filter((p) => folders.of[p.id] === f.id), subs = kidsOf(f.id), shut = folded.has(f.id), under = inside(f.id);", js)
        self.assertIn('`<span class="sb-fn">${docs.filter((p) => under.has(folders.of[p.id])).length}</span></button>`', js)   # (inside too)
        self.assertIn("const inner = fresh(f.id) + subs.map(folder).join('') + ps.map(item).join('');", js)
        self.assertIn("? fresh(null) + kidsOf(null).map(folder).join('') +", js)
        self.assertIn('`<div class="sb-folder${shut ? \' shut\' : \'\'}" data-folder="${f.id}"><div class="sb-frow"${editing === f.id ? \'\' : \' draggable="true"\'}>${head}</div>` +', js)

    def test_a_folder_made_inside_another_opens_it(self):
        js = text("app.js")
        edit = body_of(js, "function editName(id, pid = null, parent = null) {")
        self.assertIn("editing = id; moving = pid; within = parent;", edit)
        self.assertIn("if (parent && folded.delete(parent)) store.set(FOLDED, [...folded].join(' '));", edit)   # (it opens for it)
        self.assertIn("if (parent && sbQuery) sbQuery = '';   // (a search that hides the folder would hide the field too)", edit)
        save = body_of(js, "async function saveName(value) {")
        self.assertIn("parent = within", save)
        self.assertIn("{ op: 'new', name, papers, parent }", save)
        self.assertIn("editing = null; moving = null; within = null;", save)
        menu = body_of(js, "function folderMenu(btn, id, at) {")
        self.assertIn('data-act="sub"', menu)
        self.assertIn("if (act === 'sub') editName('new', null, id);", menu)
        self.assertIn('(up ? `<button type="button" role="menuitem" data-act="up">${esc(T.f_up)}</button>` : \'\') +', menu)
        self.assertIn("else if (act === 'up') nestFolder(id, up.parent || null);", menu)
        nest = body_of(js, "async function nestFolder(id, parent) {")
        self.assertIn("{ op: 'nest', id, parent }", nest)

    def test_the_menus_list_the_tree_by_depth(self):
        js = text("app.js")
        self.assertIn("function tree(id = null, depth = 0) { return kidsOf(id).flatMap((f) => [[f, depth], ...tree(f.id, depth + 1)]); }", js)
        self.assertIn('data-to="${f.id}" style="--d:${depth}">', js)
        for start in ("function docMenu(btn, pid, at) {", "function chosenMenu(btn, at) {"):
            menu = body_of(js, start)
            self.assertIn("const fs = tree().map(([f, depth]) =>", menu)

    def test_a_folder_is_dragged_into_another_and_not_into_itself(self):
        js = text("app.js")
        self.assertIn("const head = !row && e.target.closest && e.target.closest('.sb-folder[data-folder] > .sb-frow');", js)
        self.assertIn("draggingFolder = head.parentElement.dataset.folder;", js)
        self.assertIn("const parentOf = (id) => ((folders.folders.find((f) => f.id === id) || {}).parent || null);", js)
        self.assertIn("if (draggingFolder) return parentOf(draggingFolder) === to || (to && inside(draggingFolder).has(to)) ? undefined : to;", js)
        self.assertIn("if (dragging || draggingFolder) edgeScroll(e);", js)
        self.assertIn("if (!(dragging || draggingFolder) || !edgeStep || performance.now() - edgeAt > 700) { edgeRaf = 0; return; }", js)
        self.assertIn("dragging = null; draggingFolder = null; edgeStep = 0;", js)
        self.assertIn("if (fid) nestFolder(fid, to); else moveTo(pids.length > 1 ? pids : pids[0], to);", js)
        self.assertIn("if (dragging || draggingFolder) return;   // (drawn again after the drop: the row being dragged stays where the drag began)", js)

    def test_the_words_are_written_in_both_languages(self):
        js = text("i18n.js")
        block = re.search(r"const NEST = \{(.*?)\n  \};", js, re.S).group(1)
        langs = re.findall(r"^\s*(\w+): \[(.*?)\],?$", block, re.M)
        self.assertEqual([c for c, _ in langs], ["en", "zh"])
        for code, words in langs:
            vals = ast.literal_eval(f"[{words}]")
            self.assertEqual(len(vals), 2, code)
            self.assertTrue(all(v.strip() for v in vals), code)
        self.assertIn("for (const [code, [a, b]] of Object.entries(NEST)) Object.assign(S[code], { f_new_sub: a, f_up: b });", js)
        # deleting a folder says where what is in it goes
        self.assertIn("What is in it moves up a level; its documents stay in the library.", js)
        self.assertIn("里面的文档和子文件夹会移到上一层", js)

    def test_the_shut_folder_hides_only_its_own_rows(self):
        css = text("app.css")
        self.assertIn(".sb-folder.shut:not(.found) > .sb-frow .sb-chev { transform: none !important; }", css)
        self.assertIn(".sb-folder.shut:not(.found) > .sb-fitems { display: none; }", css)
        self.assertIn(".sb-menu [data-to] { padding-left: calc(10px + var(--d, 0) * 14px); }", css)

    def test_the_folders_reach_the_server_inside_one_another(self):
        server = (ROOT / "textfold" / "server.py").read_text(encoding="utf-8")
        self.assertIn("GET  /api/folders           the reader's folders (inside one another) and which document is in which (library.py)", server)
        self.assertIn("POST /api/folders           {op: new | rename | delete | nest | move, ...}: one change; the folders after it", server)
        self.assertIn("return self.json(library.change(body))", server)
        self.assertIn('return self.json({"error": str(e)}, 400)', server)


if __name__ == "__main__":
    unittest.main()
