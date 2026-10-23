# The whole-text note stays out of the chat and on screen at Topic

**Date:** 2026-10-23
**Branch:** `worktree-r22-whole-note-fix`

## What and why

The pre-push audit found two R22 defects. The whole-paper chat picked a whole-text note (`kind: "note"`,
`anchor.on: "paper"`) as its latest conversation; sending a question rewrote that note to `kind: "ask"`, and Stop on
its first question deleted it. At Topic the note used the left margin of a 1280px column; at 1374px with the sidebar
collapsed it was at `left -147`, and at 1674px with the 280px sidebar pinned it sat under the sidebar.

## The change

- `textfold/web/reader.js` — `latestChat` takes only `kind === "ask"`; `openChat` nulls a non-ask; the chat button
  reopens only an ask; `chatSend` creates a new ask instead of reusing a note. `stopAsk` now awaits
  `/api/ask/stop`, then restores `a.before` when it is a note (or a legacy text-bearing ask) and deletes only a
  genuinely new question. A `stopping` set blocks a second question (chat or passage) while the stop is in flight.
- `textfold/web/reader.css` — at Topic, `.paper-head > .lside` is static, in the column, `min(420px, 100%)` wide, under
  the title; the other levels keep the margin card.
- `tests/test_reader_paper_note.py` — two regression tests: the chat/stop guards (including `stopping` and the
  before-before-save ordering) and the Topic rule.
- `docs/DEVELOPMENT.md` — says the note sits under the title at Topic (the map is an overlay), and the chat never treats
  it as a conversation.

## Docs checked

- `docs/DEVELOPMENT.md` — updated as above.
- `docs/notes-format.md` — not needed: `kind`, `thread`, `anchor` and the whole-note shape are unchanged; the chat
  already used `kind: "ask"` for conversations.
- `README.md` / `README.zh-CN.md` — not needed: this is a defect fix to an existing feature, not a new promise.
- `docs/requirements/2026-10-22-upstream-round.md` — not needed: it is the round's historical execution table; this
  follow-up is recorded here. No acceptance item changes.
- `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `SECURITY.md` — not needed: no version, dependency,
  platform or public claim changes.
- `CLAUDE.md`, `docs/WORKFLOW.md`, `.claude/skills/` — not needed: the workflow itself did not change.

## Decisions

- At Topic the note moves under the title, in the column, instead of reserving a margin by narrowing the 1280px card
  grid. The margin is always visible and independent of the rail; the card grid loses no columns.
- A note already converted to `kind: "ask"` by the old code is not auto-split on load. It cannot be told apart from a
  real question reliably, and a read would start writing records and changing counts. `stopAsk` restores such a record
  when the reader stops a pending question on it.
- The Topic map remains an opaque overlay; the note is fixed in the cards/page view, not added to the map. That is a
  separate change (new map nodes, click and popover anchoring).

## Concurrency and locks

`notes.json` still has one writer per server process (`notes._LOCK`); this change adds no field or writer. The
stop/answer crossing was the risky one: the client used to fire `/api/ask/stop` and restore the note immediately, so
an answer's `put` could land after the restore. `stopAsk` now awaits the stop response before saving the restored
record, making the restore the last write; `stopping` blocks a second question in the chat or the passage composer
until that write is sent, so it cannot be overwritten by a restore. The server's `_STOP_LOCK` still serializes the
stop against the answer's `put` (`tests/test_ask_stop.py`, three cases). No new two-writer test: the change adds no
server-side writer; the browser test below used a hanging `/api/ask` and Stop.

## How it was verified

- `D:/Code/textfold/.venv/Scripts/python.exe .claude/hooks/verify.py` — **438 tests, OK, 24.053 s** (436 baseline plus
  the two new tests).
- `node --check textfold/web/reader.js` — OK; `git diff --check` — exit 0.
- Headless Chrome 155 + CDP against a temporary library: opening the chat on a paper with a whole note did not show
  the note; sending a question left the note `kind: "note"` and created a separate `ask` with empty `text`; a hanging
  `/api/ask` followed by Stop removed the new ask and kept the note.
- Topic note rectangles (static, 420px): 1374px collapsed `left 97/right 517`; 1674px docked `left 361/right 781`;
  724px `left 76/right 496`; 574px `left 16/right 436`; the Aa notes switch still hides it (`display:none`).
- A legacy `kind:"ask"` record with text and no turns, given a hanging question and Stop, was saved back as
  `kind:"note"` with its text and no thread.
- With `/api/ask/stop` held open, a second question typed during the wait stayed in the field and was not saved; after
  the stop the restored field held the original question. The `stopping` set is what blocks it.
- Independent `textfold-verifier`: 438 tests OK; no blocking finding. It found that a second question could be sent
  while Stop awaited the server, in the chat and in the passage composer (both fixed with `stopping` and pinned); the
  tab-close window and the map overlay are recorded below. It confirmed both new tests fail on `main` and pass here.

## Measured

| | before | after |
|---|---|---|
| Topic note at 1374px, sidebar collapsed | `left -147`, `right 67` | `left 97`, `right 517` |
| Topic note at 1674px, 280px sidebar pinned | `left 117` (under the rail) | `left 361`, `right 781` |
| Note kind after a chat question | `note → ask` | stays `note`; a new `ask` with `text: ""` |
| Suite | 436 tests, OK | 438 tests, OK, 24.053 s |

## Not measured

- Zoom smoothness: **unmeasured**. `tools/zoombench.py` needs `playwright` and exported pages under `out/compare/`;
  neither is on this machine. The change touches `reader.js` and `reader.css`, so it cannot be reported unaffected.
- The Topic map view: the note is under the opaque map overlay and not visible there; only the cards/page view is fixed.
- A real model answer, two real tabs, print/PDF, the MyGo shell, and touch/narrow devices.
- Legacy notes already converted to `ask` by the old code are not auto-repaired; only the Stop path can restore one.

## Pitfalls

- The map is an opaque fixed overlay; a note in the page is not visible while it is shown. Do not read the Topic fix as
  covering map view.
- At Topic the note is now in the column: it pushes the card grid down by about a card height, and multiple notes stack.
- `stopAsk` now waits for the local `/api/ask/stop` response before restoring; a hung server delays the UI restore.
  If the tab closes or reloads during that wait, the restore is never sent and the pending turn can remain on disk.
  The window is one loopback round trip; no test covers a tab closing in it.
- `deleteTurn` on a legacy converted ask still deletes the record when its last turn goes; that is the other old path.
- Do not reword the `docs/notes-format.md` sentence pinned by `tests/test_reader_paper_note.py`; append instead.

## Rejected

- Reserving 540px of the Topic column with `:has()`/`calc`: fewer card columns on 1240–1680px windows, needs `sb-narrow`
  mirrored into the zoom sandbox, and the note still sits under the map.
- Drawing notes into the map's title column: new node kind, click handling, popover anchor and repaint; a separate change.
- Auto-splitting already-converted notes on load: writes on read, new ids/counts, and no reliable way to tell a legacy
  note from a real question.
