# The sidebar picks several documents, moves or deletes them together, and a delete is offered back for ten seconds

**Date:** 2026-10-22 (merged 2026-10-23)
**Branch:** `worktree-sidebar-select`

## What and why

R21 of the round was the sidebar picking several documents, a bar to move or delete them together, and an Undo
(upstream `d80e779`). The review asked to keep the server and the sidebar apart, so R21 was split: R21a (merged,
`4f2448f`) gave the server the bulk delete and the restore route, each deleted folder carrying its place in the
library; this change is **R21b**, the sidebar itself. It is built on R21a's routes: `{papers}` delete answers
`{papers, deleted, busy, failed}`, restore answers `{papers, folders, restored}`.

This fork's sidebar differs from upstream's in the ways that matter here: folders are one level (no `tree()`), documents
cannot be renamed (no `names`, no "Unname"), and only English and Chinese exist. R21a's `failed` and `restored` answers
are surfaced rather than ignored, and the plain counts read right for one as well as many.

## The change

- `textfold/web/app.js`
  - **Picking.** A `chosen` set and the last pick (`chosenAt`): ⌘/Ctrl-click toggles a row, Shift-click takes every row
    shown from the last pick to this one, a plain click toggles while anything is picked, ⌘A/Ctrl+A with the list
    focused picks every row shown, Esc lets go, and a row's menu has **Select**. Ids no longer listed are dropped on each
    draw. Picked rows are tinted and their × becomes a tick; a dark bar under the list says how many and offers
    **Move to…**, **Delete** and ×. The bar's Move menu lists the folders (ticked when all picked ones are in it), Take
    out, New folder… (named for them) and Delete; a right-click on a picked row with more than one picked opens it too.
  - **Together.** A picked row dragged carries the rest, the pointer showing "N selected"; `folders.of` decides the
    from-folder state and whether a drop would change anything; `moveTo` and `saveName` take one id or an array and let
    the selection go after a move or a named folder.
  - **Delete and Undo.** Every delete, single or picked, goes through `POST /api/papers/delete {papers: ids}`; `busy`
    (still generating) and `failed` (folder could not move) are said, the picked ones are let go, and a ten-second toast
    in the corner says what went with **Undo**, calling `POST /api/papers/restore`. Deleting the paper being read puts
    the same Undo in `sessionStorage` (`textfold.undo`) and goes to `/`, where the landing offers it. A restore that
    brings back fewer than were deleted says how many came back, or that the trash no longer has them.
  - **Menus.** A sidebar menu with no room below its button now opens above it (upstream's `showMenu` hunk).
- `textfold/web/i18n.js` — `SEL`, sixteen keys for en/zh, including three beyond upstream: `sel_failed` (the `failed`
  answer), `undo_gone` and `undo_part` (a restore that does not bring all of them back).
- `textfold/web/app.css` — the picked row's tint, the tick where the × was, the bar (count, buttons, ×), and the drag
  label.
- `tests/test_app_sidebar_select.py` — six contract tests: the words and their placeholders in both languages; picking
  (modifiers, Shift range over shown rows, Ctrl+A, Esc only with the sidebar focused, the menu's Select, the check dot
  and the bar); moving together (chosen menu, ticked folder, new folder named for them, array `moveTo`/`saveName`, the
  drag's ids and count, the folder check); deleting through the bulk route with its `busy`/`failed` lines, the
  `sessionStorage` hand-off and the Undo (restore call, all-back vs partial, the timers, the startup read); the menus'
  upward placement; and the CSS.
- `docs/DEVELOPMENT.md` — the sidebar paragraph now describes picking, the bar, the multi-drag, the ten-second Undo on
  both pages, and that a **delete** (not a folder move) names `busy`/`failed`.

## Docs checked

- `docs/DEVELOPMENT.md` — updated as above.
- `docs/notes-format.md`, `docs/reading-card-format.md` — not changed: no note or card format moved.
- `README.md`, `README.zh-CN.md` — not changed: no command, route or promise changed for another program.
- `docs/requirements/2026-10-22-upstream-round.md` — R21b ticked and the execution row written after the merge.

## Decisions

- **Esc belongs to the sidebar only when the sidebar has the focus.** Upstream's listener clears on any Esc. This
  reader's Aa menu, notes popover, chat, lightbox, save/language menus and focus mode are its own overlays, mostly not
  `<dialog>`s, and each closes on Esc; a global clear took the selection with them (verified in Chrome: Aa open, Esc,
  selection silently gone). The Esc branch now needs the event or the focus inside `#sidebar`; the bar's × is always
  there. ⌘A already required focus in the list.
- **Bulk for one row too.** Keeping the old single call would mean two response shapes and two busy paths; the bulk
  route answers arrays and is what R21a tested. A single delete of a row that has just vanished now refreshes the list
  silently instead of alerting "no such paper".
- **`failed` and `restored` are shown.** R21a reports a folder that could not move to the trash and the ids a restore
  actually brought back; the UI says both instead of claiming success.
- **Counts read for one.** `sel_busy` is "Still being generated, and not deleted: {n}.", `del_done_n` is "Deleted {n}"
  and `undo_gone` is "No longer in the trash.", so a mixed delete of two where only one went, or two whose trash was
  emptied, does not say "1 documents" or "it" for two.
- **The picked stay picked across a search or a shut folder (upstream).** The bar and the confirm both state the number,
  and Undo puts back what a delete took; pruning to what is on screen would silently drop picks.
- **No re-tick through the chosen menu.** Picking the folder the picked ones are already in does nothing (the menu ticks
  it), so a stray click cannot reorder the library.
- **No nested folders.** The chosen menu lists this fork's one level, as the row menu does.

## Concurrency, state and locks

No new persistence: the delete and restore are R21a's, serialized by `store.LOCK` and `library._lock`. The client adds
two ways to overlap requests from the UI: a move and a delete can be in flight together (both use their own routes), and
a delete can land while a poll redraws the list. The server's locks keep the library and the trash consistent; the
consequence recorded under Pitfalls is that the place kept for Undo can be the pre-move folder. `chosen` is browser
state only, rebuilt in the rendered HTML, and a redraw while a drag is under way is already deferred by the existing
`if (dragging) return`.

## How it was verified

- `python .claude/hooks/verify.py` — 407 tests, OK (R21a baseline 401; six new). `node --check` on both scripts and
  `git diff --check` clean.
- A server of its own (temporary data folder, `TEXTFOLD_NO_MODELS=1`, port 3021) with four imported Markdown documents
  and a folder:
  - Ctrl-click two rows (bar "2 selected", ticks, no ×); Shift-click a third (three); plain click adds a fourth without
    opening it; Esc clears and the bar goes; Ctrl+A with a row focused picks all four; with the search "alpha" it picks
    only the shown row; **Select** in a row's menu picks it; right-click with one picked gives that row's menu (no
    Select), with two gives the chosen menu.
  - The bar's Move to… creates a folder for the picked ones (selection cleared; both in it with the right `of`) and
    later moves two more into it; the folder is ticked when all picked are in it and clicking it changes nothing.
  - Drag: two picked rows carry `"<id> <id>"`, the drag label says "2 selected", `.sb-out` accepts them and both leave
    the folder; dropping on the folder moves them in; dragend clears `from-folder`.
  - Delete: two picked with the bar (confirm names 2 documents and 0 notes), toast "2 documents deleted", Undo brings
    both back into their folder with their dates; × on one row, toast "Deleted “Alpha”", Undo; a delete while `.trash`
    was a file gave "1 could not be deleted." and the document stayed; deleting the open paper landed on `/` with the
    Undo from `sessionStorage`, whose Undo restored it into its folder; with the trash emptied behind the toast's back,
    Undo said "No longer in the trash."; the toast hid itself after ten seconds; × on the bar cleared without deleting.
  - English and Chinese wording; a 400 px window made the chosen menu open above its button (menu bottom 272, button top
    276); no console errors and no server errors.
- `textfold-verifier` — one pass (~25 minutes, 244 tool uses), **no blocking finding**. It ran the suite (406 at the
  time), drove a real server and Chrome (selection, bar, multi-drag, bulk delete, a real failing folder move, partial
  Undo by removing one trashed folder, the ten-second timer, the open-paper landing Undo), checked escaping and startup
  ordering, and ran 28 mutations. Its non-blocking findings, fixed here: a global Esc took the selection with the Aa
  menu or another reader overlay (now scoped to the sidebar's focus, re-checked in Chrome with the Aa menu open);
  `del_done_n`/`sel_busy`/`undo_gone` said "1 documents"/"them"/"it" for one (now neutral); the DEVELOPMENT sentence
  attributed `busy`/`failed` to a folder move (now to the delete); upstream's `showMenu` upward placement was missing
  (now ported and pinned); and ten of eleven mutation survivors are now pinned — the Shift range built from shown rows,
  the last-pick assignment inside the click handler, the partial-restore condition and its branch, the notes sum,
  `selTip`'s Ctrl substitution, the drag label's `> 1`, the undo close handler and success timer. Left as recorded: the
  selection surviving a search, the move/delete overlap, the silent delete of a vanished row, only the latest delete
  being undoable, and translation swaps between keys (the tests check presence and placeholders, not wording).

## Measured

| | before | after |
|---|---|---|
| Python tests | 401 | 407 |
| Picking documents | one row's × / menu | ⌘/Ctrl-click, Shift range, ⌘A over shown rows, menu Select; Esc or × lets go |
| Moving several | one at a time | bar's Move to…, a new folder named for them, or a drag carrying all |
| Deleting several | one route call per row (R21a route unused) | one `{papers}` call, `busy`/`failed` said, ten-second Undo |
| Undo after deleting the open paper | — | stored in `sessionStorage`, offered on the landing |
| A partial restore | — | "N of them came back…" / "No longer in the trash." |
| Menu near the sidebar's foot | clamped over the button | opens above it |

## Not measured

- **The `busy` branch with a real running job**: `TEXTFOLD_NO_MODELS=1` finishes or fails jobs at once, so `busy` is
  covered by R21a's route tests with a fake job list; the client line is pinned as a contract only.
- **A real pointer drag**: every drag here was a dispatched `DragEvent` with a constructed `DataTransfer`; the native
  pointer path, and touch, were not used.
- **A private window without `sessionStorage`**: the reads and writes are inside `try`, but not exercised.
- **The undo timer in a background tab**: the page was visible; browser timer throttling was not staged.
- **The bar below 720 px of window width** (the small layout); a 220 px sidebar was checked by the verifier.
- **The MyGo shell**, and a second writer during a delete from another tab.
- **Zoom smoothness is unmeasured** (it needs `playwright` and `out/compare/`, neither here). `reader.js` and its zoom
  code are untouched, but that is not the same as the axis being unaffected and it is not reported as such.

## Pitfalls

- The picked ones survive a search or a shut folder: deleting then removes documents that are not on screen. The bar's
  count and the confirm's count are the only warning; Undo puts them back. This is upstream's behaviour and a
  deliberate choice, recorded here.
- Only the latest delete has an offered Undo: a second delete replaces the toast. Earlier papers remain in
  `papers/.trash` and can only be put back by hand or by the restore route.
- A move and a delete can overlap from the UI; the server stays consistent, but the place kept for Undo is what
  `library.forget` saw, so a delete that lands before the move returns the paper to its pre-move folder.
- Deleting a row that has just vanished (another tab) silently refreshes the list; the old single route's "no such
  paper" alert is gone.
- Esc clears the selection only with the focus inside the sidebar (a row, the list, the bar); with the focus on the
  page, the bar's × is the way.
- The reader's overlays and focus mode close on Esc themselves; with the focus in them the sidebar's selection is left
  alone, which is the point of the scoping, but it also means Esc does not clear the selection there.
- `textfold.undo` is in `sessionStorage`, so the landing's Undo is the same tab only; another tab's landing shows none.

## Rejected

- **A global Esc as upstream has it.** It collides with the reader's own overlays; the sidebar's focus is the right
  condition.
- **Pruning the picked ones to what a search shows.** It would make picking several, then narrowing to check one,
  silently lose the rest.
- **A single-row delete through the old route.** Two response shapes for one action, and the bulk route is the tested
  one.
- **Deleting without a confirm, or without Undo.** The confirm says what the trash takes; the Undo covers a mistake for
  ten seconds.
