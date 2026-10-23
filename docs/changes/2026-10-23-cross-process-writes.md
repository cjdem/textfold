# The notes, the cards and the Zotero index are saved by one process at a time

**Date:** 2026-10-23
**Branch:** `worktree-cross-process-writes`

## What and why

The app and `textfold serve` may share one data folder. Each of a note, a card and the Zotero index is read, changed
in memory and written back, and only the library's round was serialized across processes (a lock byte in a file beside
it). Two processes saving one of the others could both read the same file before either write, and the later write
silently dropped the earlier one: a note typed in one window disappears when the other saves, a card edit or a Zotero
link the same. A PDF re-conversion had the same gap even within one process for notes: it snapshots `notes.json` and
`card.json`, rebuilds the folder and copies the snapshot back, and a save made during that window was overwritten by
the copy-back. Now a lock file in the data folder makes one read-modify-write of each file run at a time across
processes, the re-conversion holds the notes' and card's locks for its whole document write, and the library uses the
same helper instead of its own copy.

## The change

- `textfold/store.py` — `file_lock(name, wait=10.0)`: a context manager taking a lock byte in `<name>.lock` in the
  data folder (`msvcrt` on Windows with a retry loop to `wait`, `fcntl` elsewhere; the OS releases the byte when the
  process ends). `_lock_byte` moves here from `library.py`. The lock file is opened empty and never written.
- `textfold/library.py` — the private lock implementation is gone; `_locked()` takes `store.file_lock("library")`. The
  lock file is `library.lock` in the data folder (it was `library.json.lock`; both are in the same folder).
- `textfold/notes.py` — `put` and `delete` hold `store.file_lock("notes", wait=60)` across their read, change and
  write.
- `textfold/cards.py` — the eight read-modify-write blocks (create, save, a finished generation's candidate, evidence,
  adopting one item or the candidate, discard, review) take `_locked()`, which is the existing thread lock plus
  `store.file_lock("cards", wait=60)`.
- `textfold/zotero.py` — `link`, the only writer of `zotero.json`, holds `store.file_lock("zotero")` across its round.
- `textfold/pdfdoc.py` — a replacing conversion takes `cards._LOCK`, `notes.lock` and `cards.lock` for its whole
  snapshot, rebuild and copy-back, so a save in this process or another waits for the rebuilt document.
- `.gitignore` — `/*.lock` replaces `/library.json.lock`: run from the clone, the server keeps four lock files in the
  repository root, and none of them belongs in `git status`.
- `tests/test_cross_process_writes.py` — six tests: two interpreters sharing a temporary data folder read their file
  and then wait at a gate; the test opens the gate once both have read (or after a second, when the second is blocked
  at the lock). Both notes survive; a card save that lost the race is refused as `stale-card` rather than both being
  accepted against one revision; both Zotero links survive. In a re-conversion held at a mocked `local.store_doc`, a
  second handle cannot take the notes or cards byte while the conversion is held, and a note and a card saved from
  another process have not landed before the conversion is released and are kept after it.
- `docs/DEVELOPMENT.md` — the storage paragraph says every read-modify-write is serialized across processes, names
  the four lock files, gives the re-conversion its locks, and states what the move to the trash does and does not
  guarantee across processes.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the storage constraints, the lock files, the re-conversion and the trash.
- `README.md` / `README.zh-CN.md` — not needed: no reader-visible change.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no file or field changes.
- `docs/requirements/` — none covers this; the audit under `notes/` is the working note.
- `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`,
  `docs/changes/README.md`, `docs/upstream/README.md`, `desktop-mygo/README.md`, `.claude/agents/`, `CLAUDE.md`,
  `.claude/skills/`, `docs/WORKFLOW.md` — not needed: no dependency, version, platform, security, contribution,
  desktop or process change.
- `docs/changes/2026-10-23-library-safe-writes.md` — left as written: it records what that change did, when the lock
  file was called `library.json.lock`; this record names the rename.

## Decisions

- One lock per kind of file (`notes`, `cards`, `zotero`, `library`), not one per document: a save is short and a
  reader edits one document at a time, so the contention a per-paper name would avoid does not exist, and constant
  names keep the lock files in one place.
- The lock files live in the data folder, never in `papers/<id>/`: on Windows a document's folder cannot be moved to
  the trash while a lock file inside it is open, and a lock file left there would travel to the trash with it.
- The thread lock stays outside the file lock (`with _LOCK: with store.file_lock(...)`), the same order everywhere, so
  two threads in one process and two processes cannot deadlock each other.
- Notes and cards wait up to 60 s for the lock, not the default 10 s: a re-conversion in another process holds them
  for its whole document write, which can take longer than ten seconds, and a save that gave up would be lost. A
  holder that died has had its lock released by the OS, so the wait is not a crash detector.
- The re-conversion's copy-back is not merged with the rebuilt folder's files: notes and cards have no merge rule (a
  deletion looks like an absence), so the window is closed by holding the locks across it instead.
- `store.file_lock` is in `store.py` because all its users already import it, and because the lock must cover the same
  temporary-file-and-replace write the module owns.
- The card's `rev` check stays: the lock makes the rounds one at a time, and `rev` still refuses a save composed
  against an older card, now also when the older card was written by another process.

## Concurrency and locks

This is the change. `_locked()` order: the process's thread lock, then the cross-process file lock. No card function
called inside a `_locked()` block takes `_locked()` again — msvcrt locks are per handle, so a second lock file handle
in the same process would wait on itself. The re-conversion takes `store.LOCK`, then `notes.lock`, then `cards.lock`,
and holds them until the snapshot has been copied back. The tests run two interpreters with a shared `TEXTFOLD_DATA`;
each reads and then waits at a gate, and the test opens the gate once both have read (or after a second, when the
second cannot read because the first holds the lock), so on the unlocked code both writes start from the same old
file. The re-conversion tests hold the conversion at a mocked `local.store_doc`, probe the two locks from a second
handle (refused while held, free after), start the saving process, and check before releasing the conversion that the
save has not landed in the old file; they then assert it is in the rebuilt one.

## How it was verified

- `python .claude/hooks/verify.py` — 469 tests, OK (37.8 s); `git diff --check` prints nothing.
- `tests.test_cross_process_writes` — 6 tests, OK (8.2 s), run repeatedly.
- The same tests against a scratch tree from `HEAD` (the unlocked code) — 5 failures and 1 error: a note, a Zotero
  link and one card save are lost, the conversion's locks are absent, and the two saves made during a re-conversion
  land in the old folder (or, for the card, fail loudly with `no-document` depending on when the child reaches it)
  and are dropped by the copy-back.
- The library's own two-process test still passes through the shared helper.

## Not measured

- The desktop app itself (MyGo) sharing the folder with `serve`: the tests use two Python interpreters, not the Go
  app. The lock is the same OS lock either way.
- A real PDF re-conversion: the tests mock `local.store_doc` and hold it open; they prove the lock is held and the
  save waits, not that a conversion of a large PDF finishes within the 60 s wait.
- A data folder on a network drive (SMB), where Windows byte-range locking may behave differently: not tested; the
  library lock already made the same assumption.
- Zoom smoothness: this change touches no reader JavaScript, but it is not measured here — `tools/zoombench.py` needs
  `playwright` and exported comparison pages, neither installed.
- The move to the trash across two processes: analysed from the code, not run; see the limitation in
  `docs/DEVELOPMENT.md` (the library's forget-and-move is not atomic against another process's library write).
- A re-conversion against a move to the trash or an Undo in another process: not covered. The conversion holds the
  notes' and card's locks, but the trash takes neither, so a trash or undo crossing a conversion can still move the
  folder the conversion is rebuilding. That is the folder-lifecycle half of the audit's trash item and belongs with
  it, not with these per-file locks.
- The two-writer tests are timing-based: a child that takes longer than the one-second gate to reach its read would
  make the unlocked code look safe. On the unlocked code the tests now fail consistently here; the direct lock probe
  (a second handle refused while the conversion holds the byte) does not depend on timing.

## Pitfalls

- msvcrt's blocking lock gives up after the given wait; `_lock_byte` retries to the same deadline and then raises, so a
  save that cannot get the lock fails loudly rather than writing over. Saves during a long re-conversion rely on the
  60 s wait; a conversion that outlasts it makes the save fail. For a card, the first wait is the process's thread
  lock, which has no deadline; only the cross-process file lock after it uses the 60 s.
- A second `file_lock` of the same name in one process is not re-entrant (a different handle waits on itself); keep
  the lock at the outermost read-modify-write of each call path.
- The lock file must stay empty: writing a byte before taking the lock is a race of its own.
- `library.json.lock` is gone. A build from before this change and one after it would not exclude each other on the
  library; no such build is released (the lock was added locally and is not pushed).
- `cards.read` still renames an unreadable card aside outside the lock; a save landing between that read and the rename
  could be moved aside with it. Narrow (the card must already be unreadable) and pre-existing, not covered here.
- On Windows a lock file opened by one process does not stop another from opening it, only from taking its byte; a
  stale lock file left by a crash is harmless.

## Rejected

- One global lock for all four files: it would serialize unrelated saves and still need the same helper and names.
- Per-document lock files inside `papers/<id>/`: they would block the trash move on Windows and travel with the folder.
- Merging the re-conversion's snapshot with the rebuilt folder instead of locking: notes and cards have no merge rule,
  and a deleted note would come back.
- A database (SQLite) for notes, cards and links: a much larger change than the lost-update problem needs, and the
  files are the documented format.
