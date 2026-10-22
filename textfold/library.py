"""The reader's own order in the library, as the sidebar shows it: folders, the names they gave documents, and when
each document came in and when it was last opened. Kept in library.json in the data folder, beside papers/, so that the
app and `textfold serve` show the same and a copy of the library carries it.

Folders: one level, a document in one at most (dragged into another, it moves). A document in no folder stays under
its kind, or under when it came in or was opened; deleting a folder leaves its documents there.

A name: what the reader calls a document in the library (a PDF whose title came out wrong, a file named by its
date), shown instead of its title; the title stays the document's own, and the name goes when it is cleared.

When a document came in is noted the first time the list shows it, from the oldest file in its folder (so one read
before this was kept is dated as well); when it was opened, each time the reader shows it.

    {"folders": [{"id": "f-3a9c01d2", "name": "Thesis"}], "of": {"2512.24601": "f-3a9c01d2"},
     "names": {"pdf-0123456789abcdef": "Smith 2024 review"},
     "added": {"2512.24601": 1791000000.0}, "opened": {"2512.24601": 1792000000.0}}
"""
import json
import re
import secrets
import threading
import time

from . import store

_lock = threading.Lock()


def path():
    return store.DATA / "library.json"


def _times(d, key):
    v = d.get(key) if isinstance(d.get(key), dict) else {}
    return {p: float(t) for p, t in v.items() if store.valid_id(p) and isinstance(t, (int, float))}


def load():
    try:
        d = json.loads(store.read_text(path()))
    except UnicodeDecodeError:
        raise   # (in neither UTF-8 nor the codepage: never read it as empty and save that over it)
    except (OSError, ValueError):
        d = {}
    folders = [{"id": f["id"], "name": f["name"]} for f in d.get("folders") or []
               if isinstance(f, dict) and isinstance(f.get("id"), str) and isinstance(f.get("name"), str)]
    ids = {f["id"] for f in folders}
    of = d.get("of") if isinstance(d.get("of"), dict) else {}
    names = d.get("names") if isinstance(d.get("names"), dict) else {}
    return {"folders": folders, "of": {p: f for p, f in of.items() if f in ids and store.valid_id(p)},
            "names": {p: n for p, n in names.items() if store.valid_id(p) and isinstance(n, str) and n.strip()},
            "added": _times(d, "added"), "opened": _times(d, "opened")}


def _save(d):
    f = path()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    # ASCII-escaped: a folder's name is the reader's, in any language, and the file stays plain ASCII
    tmp.write_text(json.dumps(d, indent=1), encoding="utf-8")
    tmp.replace(f)


def folders():
    """The folders, in the order they were made, and which folder each document is in (none: not listed)."""
    d = load()
    return {"folders": d["folders"], "of": d["of"]}


def _name(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip()[:80]
    if not s:
        raise ValueError("a folder needs a name")
    return s


def change(body):
    """One change to the folders, the folders after it: {op: "new", name, papers?: [ids] moved into it} ·
    {op: "rename", id, name} · {op: "delete", id} · {op: "move", papers: [ids], folder: id or null (out of any)}.
    ValueError for one that cannot be made."""
    op = body.get("op")
    with _lock:
        d = load()
        ids = {f["id"] for f in d["folders"]}
        if op == "new":
            f = {"id": f"f-{secrets.token_hex(4)}", "name": _name(body.get("name"))}
            pids = _papers(body.get("papers", []))
            d["folders"].append(f)
            d["of"].update(dict.fromkeys(pids, f["id"]))
        elif op in ("rename", "delete"):
            f = next((f for f in d["folders"] if f["id"] == body.get("id")), None)
            if f is None:
                raise ValueError("no such folder")
            if op == "rename":
                f["name"] = _name(body.get("name"))
            else:
                d["folders"].remove(f)
                d["of"] = {p: x for p, x in d["of"].items() if x != f["id"]}
        elif op == "move":
            to = body.get("folder") or None
            if to is not None and to not in ids:
                raise ValueError("no such folder")
            for p in _papers(body.get("papers")):
                if to:
                    d["of"][p] = to
                else:
                    d["of"].pop(p, None)
        else:
            raise ValueError("op: new, rename, delete or move")
        _save(d)
        return {"folders": d["folders"], "of": d["of"]}


def name(pid, value):
    """What the reader calls a document in the library: a name ("" or None: its own title again). The names after it."""
    if not store.valid_id(pid):
        raise ValueError("no such document")
    with _lock:
        d = load()
        v = re.sub(r"\s+", " ", str(value or "")).strip()[:200]
        if v:
            d["names"][pid] = v
        else:
            d["names"].pop(pid, None)
        _save(d)
        return d["names"]


def name_of(pid):
    return load()["names"].get(pid)


def _papers(pids):
    if not isinstance(pids, list) or not all(isinstance(p, str) and store.valid_id(p) for p in pids):
        raise ValueError("papers: a list of document ids")
    return pids


def _came_in(pid):
    """When a document came in, from its folder: its oldest file, or the folder itself when that is older."""
    d = store.pdir(pid)
    st = d.stat()
    times = [f.stat().st_mtime for f in d.rglob("*") if f.is_file()]
    return min(times + [getattr(st, "st_birthtime", st.st_mtime)])


def stamp(papers):
    """The documents of the list (store.papers), each with when it came in ("added") and when it was last opened
    ("opened", or None), and the name the reader gave it, if any; one listed for the first time is dated here and kept."""
    with _lock:
        d = load()
        new = {p["id"]: _came_in(p["id"]) for p in papers if p["id"] not in d["added"]}
        if new:
            d["added"].update(new)
            _save(d)
    return [{**p, "added": d["added"][p["id"]], "opened": d["opened"].get(p["id"]),
             **({"name": d["names"][p["id"]]} if p["id"] in d["names"] else {})} for p in papers]


def opened(pid):
    """The reader shows a document: when."""
    if not store.valid_id(pid):
        return
    with _lock:
        d = load()
        d["opened"][pid] = time.time()
        _save(d)


def forget(pid):
    """A document deleted from the library: out of its folder, its name and dates gone (read again, it comes in anew).
    What it had, to remember it by: {"of": folder, "name": name, "added": time, "opened": time}, those it had."""
    with _lock:
        d = load()
        gone = {k: d[k].pop(pid) for k in ("of", "added", "opened") if pid in d[k]}
        if pid in d["names"]:
            gone["name"] = d["names"].pop(pid)
        if gone:
            _save(d)
        return gone


def remember(pid, kept):
    """A deleted document back (its Undo): in its folder if that is still there, with its name and dates."""
    if not store.valid_id(pid) or not isinstance(kept, dict):
        return
    with _lock:
        d = load()
        ids = {f["id"] for f in d["folders"]}
        stamp = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v < 1e12   # (a JSON number, a date)
        put = False
        for k, into, ok in (("of", "of", lambda v: isinstance(v, str) and v in ids), ("name", "names", lambda v: isinstance(v, str) and bool(v.strip())),
                            ("added", "added", stamp), ("opened", "opened", stamp)):
            if k in kept and ok(kept[k]):
                d[into][pid] = kept[k]
                put = True
        if put:
            _save(d)
