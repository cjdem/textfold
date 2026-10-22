# Several documents deleted at once, and the reader's Undo brings them back

**Date:** 2026-10-22
**Branch:** `worktree-bulk-trash`

## What and why

R21 of the round is upstream `15d7b8a` + `d80e779`: a sidebar that picks several documents, moves or deletes them
together, and puts back what a delete took with a ten-second Undo. The review asked to keep the server and the sidebar
apart, so R21 is split: this change is **R21a, the server** — `POST /api/papers/delete` takes `{papers: [ids]}` (the ones
being generated stay, and the answer says which went and which stayed), and `POST /api/papers/restore` moves deleted
documents back from `papers/.trash`. The delete now writes the document's place in the library (its folder and dates)
into the trash beside it, so a restore comes back in its folder and with its date, not as a new arrival. R21b will be
the sidebar's selection and Undo bar.

This fork has no document renaming, so the place kept is the folder and the two dates; upstream also keeps a name, and
that key is simply absent here.

## The change

- `textfold/store.py` — `trash(pid, kept=None)` writes `kept` to a temporary file beside `papers/` before the move, moves
  the folder under the lock, and puts that file inside the trashed folder as `library.json` under the same lock (so a
  restore cannot see the folder before its place is there, and a failed or partial write cannot leave a truncated place
  in the trash); `untrash(pid, use=None)` takes the latest matching `papers/.trash/<id>-<time>/` (the whole name must be
  the id and a timestamp, and its `meta.json` must be there), reads that file (`{}` when missing or damaged), moves the
  folder back, hands the place to `use` while the lock is still held (the server's `library.remember`), and removes the
  reader's file from the paper folder after it; the file stays if `use` raises, to be read again. `{}` when there was no
  place, `None` when there is nothing to restore or the id is listed again.
- `textfold/library.py` — `forget(pid)` returns what it took out (`of`, `added`, `opened`, those it had);
  `remember(pid, kept)` puts back the folder if it still exists and the dates, taking nothing from a damaged place: the
  folder must be a string naming a folder still there, and a date a finite number in range (a list, a 400-digit integer
  or a NaN is dropped, not written).
- `textfold/server.py` — the delete route takes `{papers: [ids]}` as well as `{paper: id}` (unchanged: a list, 404 for
  no such paper, 409 for busy); the bulk answer is `{papers, deleted, busy, failed}` — a folder that could not move is
  put back in the library and named under `failed`, the rest still go — and a document being generated is left
  (`busy_deleting`, a card draft aside). The new restore route answers `{papers, folders, restored}`; the place is
  remembered inside `store.untrash`'s lock. If the folder cannot be moved on a single delete, the library entry is put
  back before the error goes on. `DEVELOPMENT.md`'s data layout and routes are updated.
- `tests/test_library.py` — `forget` returns the place and dates; `remember` restores them (opened too), keeps the dates
  when the folder has since been deleted, drops invalid values and unknown ids, and writes nothing at all for a hostile
  place (an unhashable folder, an enormous date, a NaN).
- `tests/test_store_trash.py` — the folder and its place come back, no place writes no file, no temporary file is left,
  restoring what is not there, the latest of two copies, another document's copy (a shared prefix) and a copy without
  its meta are not taken, a damaged place, the place held while the library takes it (and left if that raises), and two
  restores at once (one wins).
- `tests/test_server_trash.py` — the routes on a server of its own: three deleted at once (one unknown id), the list,
  the folder, the date, `failed` empty, restore and its idempotence; one deleted as before; the same id twice deleted
  once; and which documents a delete must leave.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the trash keeps the library place and the restore route brings it back; a delete can
  take several.
- `docs/notes-format.md`, `docs/reading-card-format.md` — not changed: a card still travels with its folder and comes
  back with it, which the existing test holds (`test_trash_and_restore_keep_the_card`).
- `README.md`, `README.zh-CN.md` — not changed: no command or promise changed.
- `textfold/web/` — not changed: the sidebar's single delete uses the same route as before; the selection is R21b.

## Decisions

- **Split R21 into the server and the sidebar.** The review asked not to move both `server.py` and `app.js` in one
  change; this half can be tested without a browser, and the Undo bar can be built on a route that already answers.
- **The place travels with the folder.** Keeping it in the data folder's `library.json` would leave the entry of a
  deleted document behind and could not tell a restore from a new arrival; inside the trash it cannot be forgotten by a
  later delete of something else, and it leaves with the folder if the trash is cleaned by hand.
- **Prepared, then written under the folder's lock.** The place is written to a temporary file before the move (a
  truncated write cannot land in the trash), and installed in the trashed folder under the same lock as the move, so a
  restore cannot read a folder without its place.
- **The place is taken while the restore still holds that lock.** `untrash` hands the place to `library.remember` before
  releasing it; a delete of the same id waits, so the library cannot be left with an entry for a paper back in the
  trash. The place file leaves the paper only after the library has it; a failure leaves it there to be read again.
- **The place is not trusted.** A trash folder can be edited by hand: `remember` accepts a folder only if it is a
  string naming a folder still there, and a date only if it is a finite number in range. A list as the folder or a
  400-digit date would otherwise raise after the only copy of the place had been removed, and a NaN would be written
  into the library and break every page that reads it.
- **A failed move puts the place back.** On Windows a rename can fail while a file is open; the library entry is
  restored before the error goes on, so the document does not stay listed in no folder with its dates lost. In a bulk
  delete the other documents still go, and the answer names the one that could not under `failed`.
- **The latest deleted copy wins.** Two copies of one id can exist (an older one left by hand); the newest by its
  timestamp is the one the Undo takes, and the older is left where it is.
- **No `names`.** This fork has no document renaming, so `forget` returns the keys it has and `remember` accepts those.

## Concurrency and locks

`store.LOCK` serializes a delete's move and a restore's read-move-and-remember (and, as before, a card save), so two
restores of one id cannot both take it (a test runs two threads), a restore cannot cross a move, and a delete cannot
slip between a restore and the library taking its place. `library._lock` serializes each `forget`/`remember`; the
store→library order is the only one used, and no path takes the library lock and then the store's. The delete's pair
(forget, then trash) is not one lock: the rollback covers a failed move; a crash between the two can leave a document
listed without its place, which the next listing re-dates, and no document is lost.

## How it was verified

- `python .claude/hooks/verify.py` — 401 tests, OK (R20 baseline 385; sixteen new tests). `git diff --check` clean.
- A server of its own (temporary data folder, `TEXTFOLD_NO_MODELS=1`), through the real routes: three imported
  documents, two in a new folder; `{"papers": [a, b, unknown]}` answered `deleted: [a, b]`, `busy: []`, `failed: []`,
  the list without them, the folder without a; the trash held a folder for a; `{"papers": [a, b]}` restored both,
  `folders.of` put them back in the folder, `added` was their old date; a second restore restored nothing; one alone
  still answered with the list, then 404; a restore of nothing answered nothing; the same id twice deleted once.
- In the in-app browser on the same temporary folder: the sidebar's × (confirm accepted) deleted a document and the
  list and its folder dropped it; the restore route brought it back into the folder, seen after a reload; the bulk route
  deleted two and restored them; no console warning or error and no server error.
- `textfold-verifier` — one pass, one blocking finding, fixed: `library.remember` took the place file on trust, so a
  hand-edited trash folder could crash a restore after its only place file had been removed, write a NaN into the
  library, or (with a 400-digit date) make every later `library.load` raise; the guards now require a string folder that
  still exists and a finite date in range, and a hostile place writes nothing. It also ran the suite and a base-tree
  suite (385 OK), drove the routes in-process with fake job lists, and ran 18 mutations. Its non-blocking findings, all
  fixed here: a bulk delete that failed on a later folder answered 500 after deleting the earlier ones (each id is now
  tried, the failed one's place is put back, and `failed` names it); the restore's `untrash`→`remember` pair was not one
  lock, so a concurrent delete could leave a library entry for a paper back in the trash (`untrash` now hands the place
  to the library while it holds the lock; the test holds it until the library has it); the place was written straight
  into the trashed folder after the rename (now prepared in a temporary file before the move and installed under the
  lock, and a place that cannot be installed no longer undoes the delete); and six test gaps (the live set, the single
  409, dedupe, the rollback, `opened`, the exact-name match, the meta check) are now pinned or recorded. It confirmed
  the port matches upstream except for the recorded choices (no names, card drafts, the lock, the rollback, the
  ASCII-escaped place), and that `../etc`, `..` and glob ids restore nothing.

## Measured

| | before | after |
|---|---|---|
| Python tests | 385 | 401 |
| `POST /api/papers/delete` | one id, the list | one id, the list; or `{papers}` → `{papers, deleted, busy, failed}` |
| `POST /api/papers/restore` | — | `{papers, folders, restored}` |
| A deleted document's place | forgotten | in `papers/.trash/<id>-<time>/library.json`, restored |
| Two restores of one id at once | — | one restores, the other gets `None` |
| A hand-edited place (a list, a huge date, a NaN) | — | dropped; nothing written; no crash |

## Not measured

- **A failed rename on Windows** (the rollback path) was not made to happen in this session: the code puts the library
  entry back and re-raises, but a read-only folder or an open file was not staged. The verifier simulated one with a
  patched `store.trash`; a bulk delete with one failed folder (the `failed` answer) was not staged.
- **A generation actually in progress** during a bulk delete was not produced in a live server (`TEXTFOLD_NO_MODELS=1`
  jobs finish at once); `busy_deleting` is tested with a fake job list, and the single 409 path is unchanged.
- **The ten-second Undo bar** is R21b; nothing in the browser offers it yet.
- **A trash cleaned by hand**, or two copies of one id made by hand, was not exercised beyond the latest-copy test.

## Pitfalls

- The trash folder's name has one-second resolution. Delete → restore → delete within one second is fine (the restore
  moves the folder out of the way, and the second delete makes the name again); the collision is a stale same-second
  copy still in the trash while the id is listed again (a re-import and a delete in that second): the rename fails, the
  library entry is put back, and a bulk delete would name it under `failed`.
- A restore skips an id that is listed again, and leaves the trashed copy in place, so the copy of a document that came
  back another way is not lost.
- If the library cannot take the place after the folder has come back (a full disk), the place file stays in the paper
  folder: the next delete replaces it, and a hand restore of an older copy would read it.
- A crash between the folder's move and the temporary place file's installation leaves the hidden
  `papers/.<id>-place.tmp` behind; it is ignored by the list and by a later restore, and can be removed by hand.
- The place file is ASCII-escaped like the library's own; it carries no reader text (no names in this fork).
- The delete route's bulk answer is an object while the single answer is the list: the sidebar's old call still gets a
  list, R21b will use the object and its `failed` list.
- A body carrying both `paper` and `papers` is read as the bulk request, and a `papers` that is not a list falls to the
  single one (a 404); the sidebar sends one shape or the other.

## Rejected

- **One change for both halves.** The review's point stands: the route and the sidebar are separately testable, and the
  sidebar is the larger and more visual half.
- **Keeping the place in the data folder's `library.json`.** It would survive a restore of a hand-moved folder only by
  luck and would need a separate record of what was deleted.
- **Deleting the trash folder after an Undo window.** Nothing is erased by this project's design; old copies stay for a
  person to remove.
