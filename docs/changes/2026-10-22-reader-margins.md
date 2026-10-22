# The reader's margins can be shown or hidden

**Date:** 2026-10-22
**Branch:** `worktree-margin-switch`

## What and why

The Aa menu can now show or hide the reader's two margins: the conversations with the model on the right and the
reader's own notes on the left. This is the third slice of upstream `fb9f95c` (R18 was split into headings, the Topic
map and the margins). Upstream's switch also offers the argument links; this fork removed them from the reader
(`2026-10-18-links-ui-removed.md`), so the row has two buttons, not three, and the third is not ported — there is
nothing in this reader for it to show or hide.

The switch is part of the type the reader keeps: it persists with the size, width, font, colours and spacing in
`localStorage` `textfold.type`, resets with 恢复默认, and is mirrored into the sandbox the zoom stages its levels in,
so the sandbox lays out like the page when the margins are in flow (the narrow and compare widths).

## The change

- `textfold/web/reader.js` — `MARGINS = ['asks', 'notes']`; `TYPE0.hide = []`; the stored value is filtered on read;
  `applyType()` sets or removes `html[data-hide]`; `mirrorType()` copies `hide` to the zoom's host as it does the font
  and width; `isType0()` counts a hidden margin as a change (so the reset button appears); a 页边 row of two
  `aria-pressed` buttons in `renderTypeMenu()`; a click branch that toggles its key; the focus selector includes
  `data-margin`, so the pressed button keeps the focus after the menu is drawn again.
- `textfold/web/i18n.js` — `TYM`: 页边 / AI 问答 / 我的笔记 and Margins / AI answers / My notes.
- `textfold/web/reader.css` — the pressed style shared with the other segments, a line through a hidden margin's label,
  and the hide rule. Upstream's one line is not enough here: `.u[data-l] > .lside` and
  `.doc[data-level] .chunk > .lside` set `display: flex` further down the sheet, and the latter outranks it, so a hidden
  notes margin still showed at Full and at the zoomed-out chunk layouts. The rule now has a selector that outranks each
  of them. Upstream has the same ordering, so its own notes switch is likely overridden there too; this is a fix, not a
  port. The `links` selector is not carried: `.side-links` was removed with the links UI.
- `tests/test_reader_type.py` — a new test for the words, the storage key and value, the attribute, the pressed
  direction, the toggle, the focus selector, the mirror, the reset and the hide rule, including a specificity check
  that every rule making a margin a flex box is outranked by a hide selector for that margin; two existing tests
  extended for the new key.
- `docs/DEVELOPMENT.md` — the Aa paragraph says what the menu's margin row does and why this fork has two margins.

## Docs checked

- `docs/DEVELOPMENT.md` — updated (above).
- `README.md`, `README.zh-CN.md` — not changed: no level, promise or command changed.
- `docs/format.md` — not changed: margins are a view, not an exported format.
- `site/`, `desktop-mygo/` — not needed: the payload copies `textfold/web/`.
- `docs/upstream/2026-10-22.md` — not changed: it is the round's review.

## Decisions

- **Two margins, not upstream's three.** The links margin does not exist in this reader since `f80969e` and its record;
  offering a button that hides nothing would be a lie in the menu, and carrying `.side-links` in the hide rule would be
  dead CSS. What is given up: a reader of this fork cannot switch an argument-links margin because there is none.
- **A pressed pair, not a checkbox list.** The menu already speaks in segmented choices; a margin's label stays in the
  row with a line through it when hidden, so the row reads as state, not as a missing choice.
- **The hide rule outranks the layout rules.** A CSS rule earlier in the sheet loses a specificity tie; the level rules
  that give a margin `display: flex` are the reason upstream's single selector does nothing. The contract test pins the
  outranking so a later refactor cannot quietly reintroduce the bug.
- **Keep the switch in the type state.** It is the same kind of choice as width and spacing: read once at start, kept
  per browser, reset together, and copied into the zoom's sandbox.

## Concurrency and locks

The server's documents are untouched: no parser, no layer, no `card.json` or `notes.json` write. The type state in
`localStorage` is written whole by every reader window and is last-writer-wins across tabs, as it already was for the
size and width: a tab loaded before a margin was hidden can restore it by changing the size. It is a browser-local
preference, not a document, and no lock is added here.

## How it was verified

- `python .claude/hooks/verify.py` — 378 tests, OK (R18b baseline 377; one new contract test).
- `git diff --check` clean.
- In the in-app browser, on a temporary data directory holding a paper with two sections and a subsection and one note
  on a paragraph, `TEXTFOLD_NO_MODELS=1`:
  - the Aa menu had seven rows, the last of the choices 页边 with AI 问答 and 我的笔记 pressed by default; with the UI
    set to English it read Margins / AI answers / My notes;
  - clicking 我的笔记 set `html[data-hide="notes"]`, stored `hide: ["notes"]`, drew the button unpressed, and the notes
    margin computed `display: none` where it had been `flex`;
  - the state survived a reload, and 恢复默认 cleared it: the attribute and the stored key went, the margin computed
    `flex` again;
  - a `.lside` appended directly under a `.chunk` (the layout a section's notes use) computed `none` while notes were
    hidden and `flex` when they were not, so both hosts the sheet shows a margin in are covered;
  - the asks button toggled its state and storage the same way;
  - no console warning or error and no server error.
- `textfold-verifier` — one pass, no blocking finding. It ran the suite (378 OK) and mutation-tested the test: 18
  mutations, among them every removed hide selector, a weakened `mirrorType`, an unfiltered stored value, a changed
  `isType0`, reordered `MARGINS`, a changed `TYPE0` and changed i18n words, were all caught. It checked the cascade in
  headless Chrome at 1400 and 800 px (both `.lside` hosts computed `none` while hidden, `.side-notes` `none` with the
  `.side` wrapper at height 0), ran the type's parse/`applyType` block in Node against null, junk, old and
  upstream-shaped stored values, and confirmed the sandbox's `:host([data-hide~="notes"])` selectors hide both hosts. It
  also confirmed upstream's one-line hide is outranked there, so the added selectors are a fix, not a port. Its
  non-blocking findings, all fixed here: the toggle branch, the pressed direction, the focus selector and the storage
  key had no assertions (now asserted in the new test); `.paper-head > .lside` was a dead selector in this fork
  (removed); the mirror comment overstated what the sandbox does with margins (corrected here and in
  `docs/DEVELOPMENT.md`); and the two-tab last-writer-wins on `localStorage` is now stated under concurrency.

## Measured

| | before | after |
|---|---|---|
| Python tests | 377 | 378 |
| Aa menu rows at Full | 6 | 7 |
| Notes margin with 我的笔记 pressed off | shown (`display: flex`) | hidden (`display: none`) |
| Stored type keys | size, width, font, mode, style, lead | + `hide` |

## Not measured

- **Zoom smoothness: unmeasured.** The margins are outside the keyframed column, and `mirrorType()` keeps the sandbox's
  layout in step when they are in flow; no `tools/zoombench.py` run was made (it needs `playwright` and exported
  `out/compare/` pages, neither present), so the axis is not reported as unaffected.
- **The asks margin was never rendered.** `TEXTFOLD_NO_MODELS=1` means no model answers were generated, so its hide
  rule, its card and its layout were not observed; only its state, storage, pressed button and the contract test were.
- **A paper with several notes at different paragraphs** was not used, so the stacking (`layoutSides`) after a margin
  comes back was not exercised visually; `setType` schedules it.
- **A print** of the hidden-margin layout was not exercised.

## Pitfalls

- A CSS rule that hides a margin must outrank the rule that shows it; the layout sets `display: flex` on `.lside` at two
  depths, and the `.doc[data-level] .chunk > .lside` one outranks a single `html[data-hide~="notes"] .lside`.
- The menu is drawn again after every choice; a testing script must look the button up again before clicking it twice,
  or it clicks a detached copy.
- The zoom's sandbox has its own copy of the sheet; `mirrorType()` is what keeps a hidden margin out of the frames.

## Rejected

- **Upstream's single-line hide rule.** It does not win the cascade in this fork (or, by the same ordering, upstream).
- **A checkbox per margin.** The menu's other choices are segmented; pressed buttons keep one visual language and one
  keyboard tab stop per margin.
- **Keeping the `links` selector for fidelity.** It would name an element this fork no longer creates.
