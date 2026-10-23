# A note draft keeps its words when it closes

**Date:** 2026-10-23
**Branch:** `worktree-note-draft-close`

## What and why

A note on the whole text (the notes menu's **New note**) opens as a draft. What was typed was saved only by a 700 ms
timer; closing the draft sooner — Escape, a click elsewhere, another note opened over it — either ran the draft branch
of `closeNote`, which only deleted an empty note and never saved words, or replaced the popover without closing it at
all. Typing and leaving within that window lost the text. Now closing a draft with words saves them, an empty draft is
still not kept, a draft the timer already saved with the same words is not written twice, and opening another note
closes the draft first so its words are kept.

A question typed but not sent shares the draft flag, but its words live in the question field (`.np-input`) rather
than the note's text; closing one still discards it, as it did before. This change does not touch that path.

## The change

- `textfold/web/reader.js` — `closeNote`'s draft branch: non-empty field text is saved before the popover closes,
  compared with `popNote.text` so the debounce's own save is not repeated; the empty-draft delete stays. `openNote`
  now closes an open popover first when the note it is asked for is a different one, so a card or highlight click
  cannot replace a draft without keeping its words.
- `tests/test_reader_note_draft.py` — new: the close path saves non-empty draft text before the delete branch, and
  `openNote` closes the old note before it takes a different one.
- `tests/test_reader_paper_note.py` — the R22 test pinned the old delete-only branch; it now pins the save and the
  empty-draft delete.
- `docs/DEVELOPMENT.md` — the whole-text note paragraph says a draft keeps its words when it closes.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the whole-text note's draft behaviour.
- `README.md` / `README.zh-CN.md` — not needed: no new capability; the menu item's description is unchanged.
- `docs/notes-format.md`, `docs/format.md`, `docs/reading-card-format.md` — not needed: the stored note format is
  unchanged.
- `docs/requirements/` — none covers this; the audit under `notes/` is the working note.
- `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`,
  `docs/changes/README.md`, `docs/upstream/README.md`, `desktop-mygo/README.md`, `.claude/agents/`, `CLAUDE.md`,
  `.claude/skills/`, `docs/WORKFLOW.md` — not needed: no dependency, version, platform, security, contribution,
  desktop or process change.

## Decisions

- Save on close, not on every keystroke: the 700 ms timer stays for what is still being typed; the close is the last
  chance to keep what is there.
- An empty draft is still not kept, and one the timer saved empty is still removed on close.
- Compare the field with `popNote.text` (which the timer updates) so closing a draft the timer already saved does not
  write the same note twice.
- An unsent question is not turned into a note on close: its text is the question, not the note's text, and a note
  with an empty conversation would show as one in the margin.

## Concurrency and locks

The close save is one more caller of the existing `notes.put` path: `notes._LOCK` serializes threads in this process,
and the file is written through `store.write_text_atomic` (a unique temporary file and an atomic replace). No new
storage code is added, and no test with two writers is added here. Across the desktop app and `textfold serve`, two
read-modify-write rounds on one `notes.json` still let the later writer win; that is the audit's separate A3 item, and
the lock for it is not part of this change.

## How it was verified

- `python .claude/hooks/verify.py` — 457 tests, OK (28.1 s); `git diff --check` prints nothing.
- `tests.test_reader_note_draft` and `tests.test_reader_paper_note` — 8 tests, OK.
- In the Browser pane, against a server with its own temporary HOME and data folder: imported a text, opened the
  reader, and ran the close twice.
  - **New note** on the whole text, typed "Escape within the timer" and pressed Escape immediately;
    `GET /api/notes/md-a-note-draft-058523c0` returned the notes document, whose entry was
    `{"kind": "note", "anchor": {"on": "paper", …}, "text": "Escape within the timer"}`.
  - **New note** again, typed "Kept when another note is opened", then clicked a passage note's card in the margin
    within the 700 ms window; the notes document held the whole-text note with that text, and the popover showed the
    passage note. Before the change the draft branch had no save and `openNote` replaced the popover, so the text was
    dropped in both runs.

## Not measured

- Zoom smoothness: the reader calls `closeNote` when a zoom starts (`zoomBy`, `setLevel`), so a draft with words now
  runs the save a changed note's close already ran — `notesChanged` renders the card and schedules a 30 ms relayout
  and warm-up during the 560 ms animation. Whether that is felt cannot be measured here: `tools/zoombench.py` needs
  `playwright` and exported comparison pages, neither installed. This is not "unaffected".
- A reload or a tab closed within the 700 ms window still loses a draft: there is no `pagehide`/`beforeunload` save,
  and none is added.
- A failing save: `saveNote` is fire-and-forget, as the debounce already was. The popover closes, the note is shown
  as saved from the in-memory list, and a rejected POST leaves nothing retrying it until the page is reloaded.

## Pitfalls

- The draft timer may have already saved the same text: writing again would duplicate a note save (not a duplicate
  note, but a needless POST); the comparison with `popNote.text` avoids it.
- Closing a draft whose field was emptied after the timer saved it deletes the note again — intended: an empty draft
  is not kept.
- The R22 test in `tests/test_reader_paper_note.py` pinned the old branch's exact string; a test that pins source must
  be updated with the behaviour it pins, not worked around.
- `openNote` is also called to redraw the same note (an answered question, a sent message); it must not close that
  one, which is why the guard compares ids rather than closing whenever a popover is open.

## Rejected

- Saving on every input event — a server write per keystroke, and the debounce exists for that reason.
- Keeping empty drafts until some later cleanup — an empty note is not a note, and the existing delete is the intent.
- A separate "discard" state — closing already means keep what has words and drop what has none.
- Keeping an unsent question on close by writing it as the note's text — it would become an answered-looking note with
  no conversation.
