# A document takes a name in the library, and the reader can write a note on the whole text

**Date:** 2026-10-22 (merged 2026-10-23)
**Branch:** `worktree-paper-name-note`

## What and why

R22 of the round is two of the four parts of upstream `d457cfa`: **a document's name in the library** (a PDF whose
title came out wrong, a file named by its date) and **a note of the reader's own on the whole text**, not on a passage.
The other two parts are already here or left for another round: the paragraph-gap retry is R8 (`c6e6b4b`), and folders
inside folders are R23. R22 is marked optional in the round table; the review has not removed it, so it is done as the
next task.

This fork shows the name in the sidebar, the page's `<title>` and the reader's head (the document's own title below, in
the language being read); the name reaches the whole-text Markdown and both exports, and it travels into the trash with
the document's place so the Undo brings it back. A whole-text note sits by the paper's title at every level, has no quote
and no Ask beside it (the chat is where the whole paper is asked about), and is written from the notes menu.

## The change

- `textfold/library.py` — `library.json` gains `names` (id → name), validated when read (a valid id and a non-blank
  string); `stamp` puts `name` on a listed document; `name(pid, value)` collapses whitespace, trims to 200 characters,
  clears on empty, and refuses an invalid id; `name_of(pid)`; `forget` takes the name out with the folder and dates and
  returns it as `{"name": …}` in the place, and `remember` puts it back (a non-string or blank name is dropped, like the
  hostile dates and folder of R21a). The docstring and the file's shape are written in.
- `textfold/server.py` — `assembled(pid, only)` adds `meta.name` to what the reader gets; the page cache's signature
  includes the name; `/api/papers/name {paper, name}` answers the list (404 for an unknown or invalid id) and goes through
  `name_paper`, which checks the folder and writes the name **under `store.LOCK`**; the delete route's per-document
  `forget` + `trash` moved into `trash_paper`, which takes the same lock, so a name cannot be written for a document
  whose folder is moving away (the two-writer test below); the export uses `assembled`.
- `textfold/build.py` — a page's `<title>` is the name when there is one; `build.export` (the CLI's
  `python -m textfold export`) puts the name into the assembled document too.
- `textfold/web/app.js` — the sidebar row shows the name (its own title stays its tooltip); **Rename** and **Use its own
  title** in the row's menu; the name written in place in the row (`.sb-dname-in`, Enter keeps, Esc lets go, leaving the
  field keeps), preserved through a poll's redraw; the search covers the name; a delete's prompt names it; an open reader
  is told through `window.__reader.rename`.
- `textfold/web/reader.js` — the head shows the name over the document's own title (translated, if reading a
  translation); `rename(name)` updates `meta.name`, the head and the window's title; `hostOf('¶')` is the head,
  `notesChanged('¶')` redraws its margin, `renderNoteCards('¶')` shows the reader's notes only; `openNote`/`flyToNote`
  send only `kind === 'ask'` to the chat, a whole note scrolls to the top and opens by the head; the notes menu's
  **New note** writes a draft (`newPaperNote`) with `anchor.on: "paper"`, no quote, no Ask; the list shows it without a
  quote line; a draft closed with no words is not kept, and one the debounce saved a moment before is deleted again.
  `noteMd` already wrote a whole note without a quote (R20).
- `textfold/web/reader.css` — `.paper-head` is positioned, `.paper-head > .lside` shows the notes at every level, the
  notes margin switch hides it, and `.nl-new` styles the menu's button.
- `textfold/web/app.css` — `.sb-dname-in`, sharing the folder-name field's look.
- `textfold/web/i18n.js` — one block, en/zh: `d_name`, `d_unname`, `n_paper_note`, `n_paper_note_tip` (upstream's
  `n_card` would read as this fork's reading card).
- `docs/notes-format.md` — a reader's note on the whole paper, by the title at every level.
- `docs/DEVELOPMENT.md` — the library paragraph (names, the head, the search, the Undo), the notes paragraphs (the
  whole-text note and the menu's New note), and the Layout line for `library.py`.
- Tests — `tests/test_library.py` (a name's round trip and clearing, the 200-character cap, ASCII in the file, a hostile
  library, the name in the place), `tests/test_paper_name.py` (the route, the page drawn again, the export, delete →
  restore, the CLI export, and the two-writer lock test), `tests/test_app_paper_name.py` (the words, the server and
  reader wiring, the sidebar's input), `tests/test_reader_paper_note.py` (the whole note's routing, margin, menu, CSS
  and format, and the server keeping it).

## Decisions

- **The name is a library value, kept with the place.** R21a's trash already carries what a restored document had; a
  name is part of that, so `forget` returns it and `remember` restores it, and the delete prompt and the Undo toast say
  the name the reader sees.
- **A name and a delete of the same document do not interleave.** They take `store.LOCK` (already an `RLock`) across
  "the folder is there" + the name write, and across the delete's `forget` + move. A rename that starts while the folder
  moves waits and then finds no document; a rename that finished first is taken into the trash with the place. This was
  the verifier's blocking finding.
- **A draft with no words leaves nothing.** Upstream keeps whatever the debounce saved; an emptied draft here is deleted
  on close, so an abandoned note does not become a blank highlight in the list and the export.
- **"New note" is written as a note, not as a card.** This fork already has a reading card; upstream's `n_card`/`newCard`
  names would be read as it. The note is `n_paper_note`, its anchor `on: "paper"`, and it lives in `notes.json` like any
  other note.
- **The CLI export carries the name too.** The served page and the static file say the same thing; upstream's CLI export
  did not, but the reader's name is the library's, and an export should not silently undo it.
- **Whitespace is collapsed and the name capped at 200.** A pasted title with line breaks stays one line; the field's
  `maxlength` is a convenience, the library is the contract.

## Concurrency and locks

`library._lock` serializes each name, folder or date change's load-modify-save. The new part is the pair name/delete:
`store.LOCK` is taken by `name_paper` and by `trash_paper` around their critical sections, and `store.trash`/`untrash`
re-enter it (an `RLock`). The lock order is store → library, the same as a restore's `untrash` → `remember`; no path
takes the library lock and then the store's. A name and a folder move, two names, a name and a stamp are serialized by
`library._lock`. `opened()` and `stamp()` keep an older, pre-existing exposure: a `GET /api/papers` or a reader's open
during a delete can write a date for a paper whose folder is moving (the verifier noticed it); it is not this change's
and is recorded under Pitfalls.

## How it was verified

- `python .claude/hooks/verify.py` — 421 tests, OK (R21b baseline 407; fourteen new/extended). `node --check` on the
  three scripts and `git diff --check` clean.
- A server of its own (temp data folder, `TEXTFOLD_NO_MODELS=1`, port 3022), two imported Markdown documents:
  - Rename from the row menu (input shows the current title as placeholder, `maxlength` 200): the row, `/api/papers` and
    the menu gain the name and **Use its own title**; search "smith" finds it; the delete prompt says the name.
  - The reader page's `<title>`, `h1` and `.orig` line show "Smith 2024 review" over "scan 0042"; renaming live from the
    reader's sidebar changed h1/title/meta without a reload; **Use its own title** restored the title and dropped the
    `.orig` line.
  - Deleting the named open paper landed on `/` with the toast naming it; Undo returned it with its name and its note;
    the reopened page showed the name.
  - The notes menu's **New note** (en/zh) wrote a note with `on: "paper"`, kind note, empty quote; the card appeared in
    `.paper-head > .lside` by the title and in the list under "The whole paper" without a quote; clicking the list item
    scrolled to the top and opened it; a typed draft the debounce saved and then emptied and closed left no note (2 → 1
    in `notes.json`); Escape on an untouched draft left none; the Aa margin switch hid and showed the head card; a live
    UI language switch kept it; delete/restore of a paper still worked after the route's refactor; `POST
    /api/papers/name` for a missing id answered 404; no console error except that deliberate 404.
- `textfold-verifier` — one pass (~22 minutes, 199 tool uses), **one blocking finding**, fixed: a name request that
  passed its "the folder is there" check while a delete was between `forget` and the folder's move could write the name
  after the delete had removed it (the verifier reproduced it with a paused `store.trash`; a re-import then carried the
  stale name and date). `name_paper` and `trash_paper` now take `store.LOCK` across their checks and writes, and a
  threaded two-writer test holds the delete inside its window while a name attempt must wait and then be refused.
  Non-blocking findings, fixed here: the "own title written back clears the name" branch was not pinned (the exact
  `nameDoc(pid, own ? '' : name)` line is now asserted); the 200-character cap was unpinned (a 250-character name is
  tested to 200); a whole-note draft typed and then emptied left a blank note behind (the draft's close now deletes a
  saved-but-empty draft; re-checked in Chrome); the CLI export did not carry the name (now it does, with a unit test);
  the Layout line for `library.py` was stale (updated). Left and recorded: a name value that is not a string is
  stringified like a folder's (its route behaves the same), a hand-written lone surrogate can make `self.json` fail
  (the same pre-existing class as folder names and note text; not reachable from the app), and the older `opened`/`stamp`
  window against a delete.
  The verifier also ran the real `reader.css` in headless Chrome at 1500 px and 800 px: the head margin is `flex` at
  levels 4, 3, 2, 1 and 0 while unit and section cards drop below Key, `data-hide="notes"` hides it and `data-hide="asks"`
  does not, and the narrow/compare rules cannot override it; 14 mutations, 12 killed (the two survivors were the cap and
  the own-title clearing, now pinned).

## Measured

| | before | after |
|---|---|---|
| Python tests | 407 | 421 |
| A document's library name | — | `library.json` `names`; the list, page title, reader head, both exports, the trash place |
| The sidebar | title only | name over the title, Rename / Use its own title, written in place, searched |
| A delete's prompt and Undo | title | the name the reader gave it |
| A note on the whole text | only the chat's questions | the notes menu's New note, by the title at every level, no quote, no Ask |
| A name racing a delete | would outlive it | serialized by `store.LOCK`; the late name is refused |

## Not measured

- **Levels with real layers**: imported Markdown has no layers, so the reader stayed at Full; "by the title at every
  level" was checked by the CSS cascade (the verifier's headless Chrome at five levels), not by a rendered layered paper.
- **The Markdown export of a whole note in a browser** (the save picker was not stubbed this time); `noteMd`'s
  whole-anchor branch is from R20 and the contract test pins it.
- **The CLI export end to end** (`python -m textfold export` was not run; its name is unit-tested with a patched page).
- **Two real tabs** renaming and deleting at once; the two-writer test uses threads and the real routes in-process.
- **The reading card drawer** with a whole-text note beside it, print/PDF, and narrow/compare layouts were not walked.
- **The MyGo shell**, and a name with a lone surrogate sent by a raw client (its 500 class is pre-existing).
- **Zoom smoothness is unmeasured** (it needs `playwright` and `out/compare/`, neither here). The change adds a card to
  the head and redraws the head on a rename; whether either costs frames is not known, and it is not reported as
  unaffected.

## Pitfalls

- The sidebar row's tooltip stays the document's own title while the row shows the name; the notes Markdown export is
  headed with the document's title (as before), while the whole-text Markdown and both page exports use the name.
- A name is coerced like a folder's (`123` becomes "123", a list its repr) and capped at 200; blank clears.
- A hand-written lone surrogate in the library's `names` (or a folder's name, or a note's text) can make `self.json`
  raise; the app can send neither.
- The delete prompt's note count comes from the last list the sidebar drew, so a note made a moment before can show as
  0; the delete and the Undo keep the notes themselves.
- The notes list groups a whole note under "The whole paper" where the note stands in `notes.json` (creation order), not
  necessarily first.
- A passage note emptied by the reader still becomes a highlight (its quote stays); only a whole-text note has no quote
  to fall back on, which is why an empty draft is removed.
- `opened()` and `stamp()` can still write a date for a document a delete is moving (pre-existing, not this change).

## Rejected

- **Keeping names only in the browser's library of names outside the trash place.** Undo would return the document
  without the name the reader had given it.
- **A separate lock for names and deletes.** `store.LOCK` is already the lock a folder's move takes; a second lock would
  need the same ordering rules and would not protect the place's write.
- **Upstream's `newCard` / `n_card` names.** This fork's reading card owns that word; a note on the whole text is a
  note.
- **Showing the head margin only at the levels that show unit margins.** It would vanish exactly where the reader looks
  first.
