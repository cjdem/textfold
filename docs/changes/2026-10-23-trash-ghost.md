# A save or a re-conversion does not bring a trashed document back

**Date:** 2026-10-23
**Branch:** `worktree-trash-ghost`

## What and why

`store.write` created the document's `layers/` folder as it saved, and `local.store_doc` (which a PDF re-conversion
runs) rebuilt `papers/<id>/` from a temporary folder. If the document moved to `papers/.trash` in between — a delete in
the same process or, now that two processes may share the data folder, in the other one — the save or the conversion
made the folder again. That ghost kept the Undo from finding the trashed copy (`untrash` refuses while
`papers/<id>` exists), and a later import of the same id met a folder nobody made. A re-conversion could also cross a
trash or an Undo in the other process: the trash moved the folder the conversion was rebuilding, and the conversion's
rename recreated it, or the conversion's `rmtree` deleted a folder an Undo had just restored. Now a layer save takes
the store's lock and refuses when the document is gone, the trash, the Undo and a replacing conversion share a
`papers` lock, and a conversion that finds the document already trashed stops instead of making the folder again.

## The change

- `textfold/store.py` — `write` takes `store.LOCK` and then `store.file_lock("papers", wait=60)` — the check, the
  `layers/` folder and the write are inside both — and raises `ValueError("no-document")` when `papers/<id>/meta.json`
  is absent. `trash` and `untrash` take the same `papers` lock inside their lock, so a save, a re-conversion or an Undo
  in another process cannot cross the folder move.
- `textfold/local.py` — `store_doc` takes the `papers` lock around its check, write and rename (a direct import of the
  same id cannot rewrite the folder a conversion is rebuilding); a caller that already holds it (a replacing
  conversion) passes `lock=False`. Its temporary folder is now made by `tempfile.mkdtemp` — a folder of its own, where
  two writers used to share `papers/<id>.tmp`.
- `textfold/pdfdoc.py` — a replacing conversion takes the `papers` lock (after the store lock, before the notes' and
  card's locks), checks `meta.json` under it and raises `ValueError("no-document")` when the folder is gone instead of
  rebuilding it; it calls `local.store_doc(..., lock=False)` because it holds the lock already.
- `textfold/__main__.py` — a `ValueError("no-document")` from a generation (the document was deleted while the command
  was reading it) is a sentence and exit code 1 in `get` and in `generate`, not a traceback.
- `textfold/server.py` — the cleanup that removes a fetched PDF's address-only folder checks `meta.json` under the
  `papers` lock first, so it cannot delete a document that arrived meanwhile.
- `tests/test_store_trash.py` — a layer save after the trash raises and makes no folder (the Undo still finds the copy);
  a layer save and a trash in two threads do not cross: the folder stays until the save is done, then moves with the
  layer inside.
- `tests/test_cross_process_writes.py` — a layer save and a trash in another process do not cross (the trash waits, the
  layer travels with the folder, no folder is left behind); a trash in another process waits for a held re-conversion,
  which then finishes and the rebuilt folder is the one in the trash; a re-conversion of a document already trashed
  raises and never reaches the folder rebuild; a second handle cannot take `papers`, `notes` or `cards` while a
  conversion holds them.
- `tests/test_cli_get.py` — `get` and `generate` say the document is gone and exit 1 when the folder was deleted while
  the command was reading it.
- `tests/test_cards.py` — its mocked `store_doc` takes the new `lock` argument.
- `tests/test_agent_encoding.py`, `tests/test_languages.py` — the two tests that wrote a layer into a bare data folder
  now create the document's `meta.json` first, as a document has.
- `docs/DEVELOPMENT.md` — the storage paragraph gives a re-conversion, a layer save and `store_doc` the `papers` lock,
  says the trash and an Undo take it too, and says a layer save or a re-conversion does not create a missing
  document's folder.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the trash and re-conversion locks, the ghost rule for layers and conversions.
- `README.md` / `README.zh-CN.md` — not needed: no reader-visible change.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no file or field changes.
- `docs/requirements/`, `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `SECURITY.md`,
  `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md`, `desktop-mygo/README.md`,
  `.claude/agents/`, `CLAUDE.md`, `.claude/skills/`, `docs/WORKFLOW.md` — not needed: no dependency, version,
  platform, security, contribution, desktop or process change.

## Decisions

- `ValueError("no-document")` as in `cards._write`: the server answers it as a failed save, and the caller can say the
  document is gone.
- The lock is taken by `store.write`, not by `save_en`/`save_tr`: every layer write goes through it, including a test's
  and a future caller's.
- The `papers` lock is taken by every path that writes or moves a document's folder: `store.write`, `store.trash`,
  `store.untrash`, `local.store_doc` and a replacing conversion. A new document's `store_doc` takes it too; the lock
  serializes writers, it does not stand for the folder existing, so creation inside it works.
- The trash now waits up to 60 s for a conversion (in this process or the other) instead of moving the folder under it.
  A slow delete is better than a folder the conversion then rebuilds or deletes.
- The check for a trashed document is a `meta.json` test under the lock, not a search of `papers/.trash`: a conversion
  arriving after the trash sees no document and stops; the trash's copy is the reader's to Undo.
- `local.store_doc` takes the `papers` lock with `lock=False` only from a replacing conversion, which already holds it:
  a second handle on the same lock in one process would wait on itself (msvcrt locks per handle). A direct import of
  the same id during a re-conversion now waits, then finds the rebuilt document and returns early instead of
  `rmtree`-ing it.
- Its temporary folder is `tempfile.mkdtemp`, not `papers/<id>.tmp`: two writers no longer share one half-written
  folder. Two simultaneous imports of the same id still end with one of them, not a mixture.
- The CLI says the document is gone and exits 1: a traceback is not an answer to a file that was deleted while the
  command was reading it.

## Concurrency and locks

Lock order: `store.LOCK`, then `papers`, then `notes`, then `cards`. The trash, the Undo and a layer save take
`store.LOCK` then `papers`; `local.store_doc` takes `papers` alone; a conversion takes all four in that order for its
whole snapshot, rebuild and copy-back. The tests hold a mocked `local.store_doc` open, start a trash in a second
interpreter, and check that it has not returned before the conversion is released; after it, `papers/<id>` is absent
and the rebuilt folder is the one in `papers/.trash`. A layer-save test widens the save's window inside the lock and
trashes from the other process: the trash waits, and the layer is in the trashed folder.

## How it was verified

- `python .claude/hooks/verify.py` — 476 tests, OK (39.3 s); `git diff --check` prints nothing.
- `tests.test_store_trash`, `tests.test_cross_process_writes`, `tests.test_cli_get` — 26 tests, OK (11.4 s).
- The eight new tests against a scratch tree from this change's base (f87c365, which already has the per-file locks) —
  6 failures and 2 errors, all eight: the layer save recreates the folder, the save and the trash cross, the trash does
  not wait, the conversion rebuilds a trashed document, the papers lock is not held, and both CLI commands raise a
  traceback where they now say the document is gone.

## Not measured

- A real PDF re-conversion against a trash in another process: the tests mock `local.store_doc` and hold it open; they
  prove the lock is taken and the trash waits, not that a conversion of a large PDF finishes inside the 60 s wait.
- The MyGo app sharing the folder with `serve`: two Python interpreters, not the Go app.
- A data folder on SMB, where Windows byte-range locking may behave differently.
- The library's forget-and-move remains not atomic against another process's library write (a delete and a rename in
  the other process can still leave a library entry for a folder that moved); this change covers the folder, not that
  window.
- The `papers` lock is one file for all documents, so the 60 s wait is global: a conversion or a slow import of any
  document makes a trash, an Undo, a layer save or another import wait up to 60 s, then fail. In one process a layer
  save waits while holding `store.LOCK`, so card saves and the trash in that process wait behind it too. A
  per-document lock name would avoid this but needs a safe name for an id; not done.
- Two simultaneous imports of the same id serialize on the `papers` lock: the second waits, then finds the rebuilt
  document and returns early. There is no merge, because an imported file has no revision a merge could stand on.
- Zoom smoothness: no reader JavaScript is touched; unmeasured here (`tools/zoombench.py` needs `playwright` and
  exported comparison pages, neither installed).

## Pitfalls

- A conversion that outlasts 60 s makes a waiting trash, Undo, layer save or `store_doc` fail (loudly) rather than
  cross the folder. The lock is global, so this includes other documents' operations.
- `local.store_doc` takes the `papers` lock for every caller; a replacing conversion passes `lock=False` because it
  holds the lock already (a second handle in the same process would wait on itself).
- `store.write` now raises where it used to create a folder; a test or tool that wrote a layer into a bare data folder
  must create the document first (two tests did, and were updated).
- The direct `pdfdoc.store_pdf` check reads `meta.json` under the lock; a document trashed before the conversion starts
  never reaches the snapshot, so there is nothing to copy back.

## Rejected

- Letting a replacing conversion re-enter `local.store_doc`'s own lock: msvcrt locks per handle, so the conversion
  would wait on itself; it passes `lock=False` instead.
- Letting the ghost appear and teaching `untrash` to ignore a folder without `meta.json`: an import of the same id
  would still land on the ghost, and the folder would be visible in `papers/` with no meta.
- Taking the `papers` lock for every save: a note or card save must fail when its document is gone, not wait for a
  conversion to finish; the notes' and card's locks already serialize those with the conversion.
- Searching the trash for the id in `store.write`: a save is not a restore; the Undo is.
- A lock file per document for `papers`: its name would carry the id, and a hand-edited or hostile id could point it
  outside the data folder; the constant name is one file for all documents, and the wait is documented.
- Letting a replacing conversion call `store_doc` without `lock=False` and rely on re-entrancy: msvcrt locks per
  handle would make the conversion wait on itself.
