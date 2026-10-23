# A library that survives a byte-order mark, a damaged file, and a second process

**Date:** 2026-10-23
**Branch:** `worktree-library-safe-writes`

## What and why

The pre-push audit found three ways `library.json` could lose what the reader arranged. A file saved by Notepad
carries a UTF-8 byte-order mark, which `json.loads` refuses: the library was read as empty and the next save wrote that
emptiness over it. A file that was not JSON, or was JSON of a shape the library does not write, was read as empty and
saved over the same way. And every writer used one fixed `<name>.tmp`, while the library's read-modify-write was
serialized only within one process: `textfold serve` and the app writing at once could make one save fail or mix a file,
and one could drop the other's folder. Now each file is written whole or not at all, the library's read-modify-write is
serialized across processes, a damaged library is copied aside and left alone, and a byte-order mark is read as the
UTF-8 it is.

## The change

- `textfold/store.py` — `read_text` decodes `utf-8-sig` first, so a byte-order mark is dropped and the rest is still
  UTF-8; `write_text_atomic` and `write_bytes_atomic` write a unique temporary file beside the target, flush it to the
  disk, and move it over, retrying the move for four seconds on the `PermissionError` Windows raises while a reader
  holds the target; they do not create the target's folder. `store.write` and the trash place file use them.
- `textfold/library.py` — `LibraryError`; `library.json.lock`, opened empty and locked on its first byte (Windows locks
  a byte past the end of an empty file, so nothing is written before the lock is taken); `msvcrt.LK_NBLCK` retried to
  a ten-second deadline, `fcntl.flock` elsewhere; all six mutators take the process lock and then the file lock;
  `load` accepts a missing, empty or BOM-led file, copies invalid JSON, a non-object top level, or a field that is not
  the list or object the library writes to `library.json.corrupt-<time>` and raises without writing, and drops bad
  rows inside good fields; dates are kept only as `0 < t < 1e12`; `_save` uses the shared atomic write.
- `textfold/notes.py`, `textfold/cards.py`, `textfold/zotero.py`, `textfold/pdf.py` — their files go through the shared
  helpers; no fixed `.tmp` or `.part` name is left in them; a note, card or PDF write no longer creates a document
  folder that was moved to the trash.
- `tests/test_library.py` — the BOM survives its next save; a damaged file is copied aside and not saved over; JSON of
  the wrong shape is copied aside; a bad row in a good field is dropped; two processes keep both folders.
- `tests/test_safe_writes.py` — a failed move leaves the old file, removes the temporary one, and creates no folder.
- `tests/test_store_trash.py` — a PDF write after the move to the trash fails instead of leaving a ghost folder.
- `tests/test_old_codepage_files.py` — a byte-order-mark read of `store.read_text`.
- `.gitignore`, `docs/DEVELOPMENT.md`.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the byte-order mark in `store.read_text`, the atomic writes, the library lock and
  lock file, the damaged-file rule, the no-ghost rule, and the lost-update limit that remains for notes, cards and the
  Zotero index.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: the formats are unchanged; only
  how their files reach the disk.
- `README.md` / `README.zh-CN.md` — not needed: no promise changes; a damaged library now fails with its backup named
  instead of silently starting empty.
- `docs/requirements/` — none covers this; the audit under `notes/` is a local working note.
- `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`,
  `docs/changes/README.md`, `docs/upstream/README.md`, `desktop-mygo/README.md`, `.claude/agents/`, `CLAUDE.md`,
  `.claude/skills/`, `docs/WORKFLOW.md` — not needed: no dependency, platform, version, contribution, desktop or
  process change.

## Decisions

- A field that is not the container the library writes is damage, not an empty field: reading it as empty is what the
  next save would write over. A bad row inside a good list or object is dropped instead, so a hand-edited library keeps
  its good folders and names.
- An empty or whitespace-only file is an empty library, with no copy aside: there is nothing in it to preserve.
- `LibraryError` is a `RuntimeError`, not a `ValueError`: the routes answer a `ValueError` with 400 "bad request",
  which would misdescribe a damaged file. It reaches the client as a 500 carrying the message that names the copy.
- The lock file is never written to before the lock is taken. A byte created at open time is a race of its own — two
  processes creating it at once, one of them failing the write — and Windows can lock the first byte past the end of
  an empty file.
- The lock byte waits by retrying `LK_NBLCK` for ten seconds instead of calling msvcrt's blocking `LK_LOCK`, which
  gives up after ten seconds with an error — and that error would lose the save it was waiting to make.
- Every save is flushed to the disk with `fsync`. The audit's finding was the collision, but "whole or not at all" also
  means a power cut leaves the old file, not a shorter new one.
- The atomic writers do not create the target's folder: a save that crosses a document's move to the trash must fail,
  not leave a ghost folder that makes the Undo refuse.
- Notes, cards and the Zotero index get a unique temporary file but not a cross-process read-modify-write lock. Their
  later save can still overwrite an earlier one from another process; a per-document lock is a larger change.

## Concurrency and locks

The order is `store.LOCK` (process) → `library._lock` (process) → the lock byte (across processes). `server.trash_paper`
holds `store.LOCK` and calls `library.forget`; `store.untrash` holds it and calls `library.remember`; nothing takes them
the other way. Reads take no lock: `os.replace` leaves a reader with the old file or the new one, never a mixture.

`tests/test_library.py::test_two_processes_do_not_lose_each_others_folders` runs two interpreters behind a barrier with
a slowed `_save`; it kept both folders in fifty consecutive runs, and eight writers on a fresh data folder kept all
eight names in twenty rounds.

Still possible, outside this change: a folder moving to the trash in one process while another process saves the
library (a folder's entry can outlive or precede it); a generation layer saved after the folder moved to the trash
(`store.write` still creates `layers/`, as it did before, and that ghost folder makes the Undo refuse); and the
cross-process lost update of notes, cards and the Zotero index described above.

## How it was verified

- `python .claude/hooks/verify.py` — 446 tests, OK (26.8 s); `git diff --check` prints nothing.
- `tests.test_library`, `tests.test_store_trash`, `tests.test_safe_writes`, `tests.test_old_codepage_files` — 37 tests,
  OK.
- Before the fix, the library tests added in the first draft ran as 1 failure and 3 errors: the BOM ended in
  `IndexError`, the damaged and wrong-shape files in `AttributeError` (no `LibraryError`), and the two processes lost
  `b`.
- An independent verifier found three defects in the first draft, all fixed here: a lock-byte creation race that lost
  a fresh-folder save about once in twenty-five runs, a wrong-shape *object* still read as empty, and the atomic
  writers recreating a trashed document's folder. Its reproduction of the first is now 0 failures in 50 test runs and
  0 in 20 rounds of eight writers.

## Measured

| | before | after |
|---|---|---|
| suite | 438 tests, OK, 22.8 s | 446 tests, OK, 26.8 s |
| two library writers | one folder lost (`b` absent) | 0 failures in 50 runs |
| eight library writers | — | 0 bad rounds in 20 |

## Not measured

- Zoom smoothness: not measured on this machine — `tools/zoombench.py` needs `playwright` and exported comparison
  pages, neither installed here. This change does not touch the reader, but the rule stays unmeasured.
- The cost of `fsync` on a note or card save; a power cut (only process kills were tried); a hold on `library.json`
  longer than four seconds; the `fcntl` branch, which this Windows machine never takes.

## Pitfalls

- A lock byte written before the lock is taken is itself a race; keep the lock file empty and lock past its end.
- `os.replace` on Windows raises `PermissionError` while another process has the target open for reading; a save that
  does not retry fails for a reason that will be gone a moment later. The retry is four seconds, not forever.
- `msvcrt.LK_LOCK` is a blocking call with a ten-second timeout, and its timeout is an exception, not a wait.
- A write that creates its folder can resurrect a document moved to the trash, and the Undo then finds a folder already
  there and refuses. The shared writers therefore require the folder.
- `utf-8-sig` only changes a file that starts with the UTF-8 byte-order mark; the encoding choice (UTF-8, else the
  system's codepage) is the one `read_text` already made.
- Each failed load of a damaged library copies it again (`library.json.corrupt-<second>[-n]`); keeping every copy is
  deliberate, but a client retrying in a loop leaves many.
- `notes.py`, `cards.py` and `zotero.py` still read, change and write without a cross-process lock: two processes can
  lose one update, though the file is never mixed or half-written.

## Rejected

- Writing a byte into the lock file before locking it — the first draft did, and two processes creating the file
  together could fail one save, about once in twenty-five runs.
- Creating the target folder inside the atomic writers — convenient for the library, but it turned a save crossing the
  move to the trash into a ghost folder that broke the Undo.
- Reading a damaged library as empty and letting the next save write over it — that is the data loss this fixes.
- One fixed temporary name plus a lock around it — the unique temporary file is what removes the collision for every
  file, not only the library.
- Taking the library lock for reads — unnecessary with atomic replacement, and every page load would wait on a writer.
- A per-document lock for notes, cards and the Zotero index in this change — a separate change, and the audit's finding
  was the collision of temporary files.
