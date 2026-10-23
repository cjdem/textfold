# The Topic map draws the reader's whole-paper notes above the outline

**Date:** 2026-10-23
**Branch:** `worktree-map-note`

## What and why

The Topic mind map is a fixed, opaque overlay over the page. R22 moved the reader's note on the whole paper into the
column under the title, which made it visible in the cards view at Topic — but the map still covered it: the note's
box was in the page, and `elementFromPoint` on it hit `.mm-n.mm-root`. The pre-push audit left this as B4, and the
R22 record named the work (option C: draw the note into the map) as its own change. Now the map draws the reader's
whole-paper notes in its left column, above the title and the outline, and a click opens the note beside the card.

## The change

- `textfold/web/reader.js`
  - `noteCard(n)` and `mineOn('¶')` are taken out of `renderNoteCards` so the margin and the map draw a note the same
    way (the map keeps the reader's own notes, never an Ask conversation).
  - `mapNotes()` builds the map's left column: a heading (`n_whole`) and one card per note.
  - `mapLayout()` measures that block and starts the title and the outline below it; the canvas is as wide as the
    block, and the block's width is the viewport less the sidebar (`--mm-left`, set by `mapFrame`) less two paddings.
  - A click on `.mm-notes .ncard` opens the note (the map stays under the popover).
  - `placePop` prefers the map's card for a note while the map is shown, so the popover anchors where the note is
    drawn rather than to the head the map covers; it re-places on the map's own scroll (the map is its own scroller,
    so its scroll events do not reach the window's handler) and on a resize.
  - `notesChanged('¶')` repaints the map when it is shown, and invalidates it (`mapKey = ''`) when it is not, so a
    note changed in the cards view is drawn when the map opens.
  - The notes are ordered by `created`, so a save (which appends the note to `notes`) leaves its card where it was.
  - A resize re-lays out the map when it is shown (a narrower note wraps taller, and the title has to move down with
    it); while it is hidden the map is invalidated, so it is built at the new width when it opens.
  - The margins' "notes" switch shows no block at all, not a hidden one holding space (which would lower the title
    by the gap).
- `textfold/web/reader.css` — `.mm-notes` (absolute, above the title), its heading, its width rule, and the rule that
  hides it with `html[data-hide~="notes"]`.
- `tests/test_reader_map_note.py` — new, four cases: the map draws the notes above the outline and measures them
  (ordered by creation, not drawn at all when the margins hide notes); a map card opens the note, the popover prefers
  the map's card and follows the map's own scroll; a note change repaints or invalidates the map, and a resize
  re-lays it out or invalidates it; the notes hide with the other margins.
- `tests/test_reader_paper_note.py` — the pinned `notesChanged('¶')` branch is the new one, and the notes-format
  sentence is the longer one.
- `docs/DEVELOPMENT.md` — the Topic map paragraph and the whole-note paragraph say where the note is drawn and how it
  opens there.
- `docs/notes-format.md` — the whole-paper note's display sentence now names the map's left column too.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the map's left column, the click, the width, and the whole note's two homes.
- `docs/notes-format.md` — updated: the display sentence said only "by the paper's title, at every level"; it now
  names the map's left column. The stored shape is unchanged.
- `docs/format.md`, `docs/reading-card-format.md` — not needed: no export or card change.
- `README.md` / `README.zh-CN.md` — not needed: no new capability or promise; an existing note is now visible on an
  existing surface.
- `site/`, `pyproject.toml`, `requirements.txt`, `NOTICE`, `LICENSE`, `SECURITY.md`, `docs/requirements/`,
  `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md`, `desktop-mygo/README.md`,
  `.claude/agents/`, `CLAUDE.md`, `.claude/skills/`, `docs/WORKFLOW.md` — not needed: no dependency, version,
  platform, security, contribution, desktop or process change; this is a fix from the pre-push audit.

## Decisions

- Above the title in the left column, not a node in the outline: a whole-paper note is not a section or a paragraph,
  and a branch to it would claim a place in the paper's structure.
- The same `ncard` as the margin, clamped to four lines, with the full text in the popover: the map is a map, and
  the note is read and edited in the popover as anywhere else.
- The map keeps the reader's own notes only; a conversation about the whole paper stays in the chat (the same filter
  the paper's head uses).
- The map's card anchors the popover while the map is shown; the head card still exists under the map and anchors it
  when the map is gone.
- A note saved while the map is shown repaints it immediately; a note changed while the map is hidden invalidates the
  built map, so the next open is fresh rather than stale.
- The map's cards keep their creation order (`created`). `saveNote` appends a note to `notes`, so without the sort an
  edited card would move to the end of the block — below the fold with many notes — and the popover would follow it
  there.
- The popover follows the map's own scroll and a resize: the map is its own scroll container, so the window's scroll
  handler never sees it, and a resize moves the card as well as the layout.
- The block's width follows the viewport and the sidebar in CSS (`--mm-left`), so the same rule holds at every window
  width, and the title starts under the measured block, so a wrapped note cannot overlap it.
- The map hides with the margins' "notes" switch, like the page cards, and builds no block then: a hidden block would
  still hold the 20 px gap above the title.

## Concurrency and locks

Not applicable: this is the reader's drawing only. Notes are still written by the server's `notes.put` under its own
lock; no field, file or writer is added.

## How it was verified

- `python .claude/hooks/verify.py` — 501 tests, OK (39.9 s); `node --check textfold/web/reader.js`; `git diff --check`
  prints nothing.
- `tests.test_reader_map_note` and `tests.test_reader_paper_note` — 10 tests, OK.
- Browser, a disposable library served by `python -m textfold serve` (no model), one paper with a section or two:
  - At Topic with the map chosen: `.mm-notes` at x 76, 360 × 50, the heading "全文" and the note's text; `.mm-root`
    at y 196, 20 px under the block (y 126 + 50); the map visible, no console error.
  - A click on the card (in the page, `HTMLElement.click()`) opened `.npop` at x 76, y 184, 380 × 170, with the
    note's text in the textarea and the map still shown.
  - Typing in the popover (the 700 ms save) updated the map's card to the new text with the popover open and in place.
  - Changing the text while the map was hidden (cards view), then opening the map: the card showed the new text.
  - `html[data-hide~="notes"]`: `display: none` on `.mm-notes`; with the block built, the root transform went from
    y 742 to y 34 (the no-notes position), and back when the switch was removed — no 20 px gap remains.
  - With twenty notes: the map scrolled (content 1025, view 643); a click on the fifth card put `.npop` at the card's
    bottom + 8, and after `scrollTop` 100 plus a dispatched scroll event the popover moved to the new bottom + 8
    (320 → 220), on the map's own scroll. (The hidden preview pane fired no automatic scroll event for a programmatic
    scroll — a probe saw none — so the event was dispatched; the handler and the re-placement are what the run shows.)
  - Editing the first of the twenty (the note appended to `notes` on save) left its card first at the same y, with the
    popover still under it; without the `created` sort the card would have moved to the block's end.
  - Hiding the map, resizing to 390 (a dispatched resize, since the emulated viewport change fires none), then opening
    it: the block was 342 wide, x 24, right 366 (inside 390), 698 high, and the root 20 px under it — rebuilt at the
    new width rather than laid out at the old one.
  - The preview pane's input injection delivered no mouse or pointer events to the page in this session (a capture
    listener saw none), so the click was driven in the page; the handler, the anchor and the layout are what the
    browser run proves, not a physical pointer.

## Not measured

- A physical pointer click and keyboard activation (Enter/Space) on a map card: the button is native and the handler
  is a click listener, but the preview pane could not inject input; the click was run in the page.
- A real window resize and a real scroll-wheel/trackpad scroll: the emulated viewport fired no resize and the hidden
  pane fired no scroll event for a programmatic scroll, so both were driven (a dispatched event after the change).
- With many notes the block fills the map's first screen: with twenty it was 698 px at 390 wide and 1,347 at 1280, so
  the title and outline begin below the fold and the map opens on the notes. That is the intended "notes first" but
  unasked; a cap or a "go to outline" control would be a product decision.
- Print/PDF, the MyGo shell, a touch screen, a real docked sidebar at the moment the map opens, a second tab.
- Zoom smoothness: `reader.js` and `reader.css` are touched, and this machine cannot run `tools/zoombench.py`
  (`playwright` and `out/compare/` are absent). The map is only shown at rest and is hidden before a zoom starts, but
  that is not a measurement.

## Pitfalls

- `notesChanged` now reaches into the map's variables. It runs from `loadNotes`, which the reader calls after the map
  section has initialized; a future caller placed earlier would hit the `mapKey` declaration before it exists.
- `mapRender` replaces the map's cards; while a note is open, `notesChanged` calls `placePop` after the repaint so the
  popover follows the new card. A card replaced without that call would leave the popover where the old one was.
- The page's card for the note still exists under the map. `placePop` chooses the map's card only while `mapShown`;
  after the map closes, the head card is the anchor again.
- The block sits at the top of the scrollable canvas, so scrolling a long map scrolls the note away; the page's own
  card is not sticky either, and a floating block could cover branches. With many notes the block itself pushes the
  title below the first screen.
- The map keeps its cards in `created` order, but the page's head list still follows `notes` (a save appends); the two
  surfaces can order the same notes differently after an edit. That is the existing head-list behavior, left as is.
- Every whole-note save or whole-paper answer redraws the whole map while it is shown (`mapRender`); the map is only
  visible at rest, but the cost on a large paper is not measured.
- The map's width rule subtracts `--mm-left`, which `mapFrame` sets from the body's left padding; a future sidebar
  change that moves the map by another mechanism must set it too.

## Rejected

- Drawing the note as a child of the root in the outline: the map would claim the note is part of the paper's
  structure, and the note would sit among sections.
- Starting the map below the paper's head: the map would shrink by the head's height, depend on page scroll, and show
  the title twice.
- Moving the page's card into the map: the page is still under the map and the card must be there for the map to
  close onto; moving it would disturb the page's layout.
- Hiding the map or switching to cards when a whole note exists: the reader chose the map.
- A fixed floating notes panel over the canvas: it would cover branches while the map scrolls.
