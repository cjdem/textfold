# The reader's Aa menu, and a zoom that keeps the font and width it was set to

**Date:** 2026-10-22
**Branch:** `worktree-reader-type-menu`

## What and why

The reader had no way to change how the text looks: its size, how wide the column is, and whether the author's words
are set in the serif the paper was written in. This ports upstream `f76eb4d` and `c38804e`: an Aa menu beside the
language's sets a size (86% to 135% in seven steps, the whole column scaling with it, so a line still holds as many
words), a column width (narrow, standard, wide, capped so the margins keep the notes their room) and the font of the
author's words (serif or sans-serif), kept in this browser for every text. The second commit is a correctness fix,
not a look: the zoom's sandbox had the page's language but not its font or width, so it laid the next level out in
serif sizes and the last frame sat up to hundreds of pixels apart from the page it gave way to.

## The change

- `textfold/web/reader.js` — the type state (`TYPE_KEY = 'textfold.type'`, `SIZES`, `WIDTHS`, `TYPE0`), read and
  validated at startup, `applyType()` before anything is drawn (`--fs` on `<html>`; `data-width`/`data-font` for the
  standard and serif cases, so the default DOM carries no attribute); the Aa button and its dialog (`renderTypeMenu`,
  `setType`, `closeTypeMenu`), inserted before the language picker; the key it was pressed with keeps the focus after
  the menu is drawn anew; `Escape` closes it and returns the focus; it closes when the language menu opens, and the
  language menu closes when it opens; a click anywhere else closes it in the capture phase, so the Notes, Export and
  Legend buttons, which stop the click at themselves, close it too. `mirrorType()` copies the font and width onto the
  sandbox host, the `app`/`compare` classes that set the page's own column cap, and the size (`--fs` inline on the
  host: the sandbox's copy of the sheet has `:host { --fs: 1 }`, which would otherwise override the inherited value);
  it runs at startup, on every type change (`applyType(); mirrorType();`) and when the PDF pane opens or closes.
- `textfold/web/reader.css` — the type variables (`--fs`, `--colw` and the capped `--col`, `--text`) and every size in
  the column scaled by `--fs`: the paper's head, headings and stakes, the four levels' text, figures and captions,
  equations and raw blocks, the bibliography, boxes, the print view (`--fs: 1` and `--colw: 700px`, `!important`, so a
  printed page is the usual size); the author's words in the paragraph preview, the quoted passage, the notes list's
  highlight and the passages kept when the text zooms out follow `--text` too; the width rules (`html[data-width]`, with wide's larger columns at 1480px and
  1760px) and `--colmax` (`calc(100vw - 540px)`, the app's rail at 1300px, the whole width beside the PDF); the Aa
  button and menu's own styles.
- `textfold/web/i18n.js` — the menu's thirteen words in English and Simplified Chinese (`TY`), which are the only two
  languages this fork offers.
- `tests/test_reader_type.py` — four tests for what Python can see of a JS feature: every word is written in both
  languages, every word the reader asks for exists, the CSS knobs and both `mirrorType` calls are there, and the sizes
  and widths are the ones the CSS styles.

## Data contract

`localStorage['textfold.type']` is JSON `{size, width, font}`: `size` one of `0.86, 0.93, 1, 1.08, 1.16, 1.25, 1.35`,
`width` `narrow | standard | wide`, `font` `serif | sans`. On read, a missing key, malformed JSON (a hand-written
value), a non-object, or any value not in the list falls back per field to `1 / standard / serif`. Nothing is stored
on the server; the setting is per browser, for every text. States: the menu is closed (default) or open; a size step
is disabled at the two ends; the reset button is hidden when the type is the default. Transitions: a change snaps the
current zoom, keeps the paragraph being read at the same place on screen (`defaultAnchor` → `settle`), then relayouts,
rebuilds the keyframes and persists; during a zoom (`busy`) a change is ignored rather than interleaved. Failure
paths: `localStorage` unavailable (a private window) reads `null` and ignores the write, so the type is the default
each load; a sandbox without the host (never: it is created before this) would throw at startup, which the smoke
check covers.

## Concurrency and locks

None added. The setting is one `localStorage` key written by the reader itself; no server file, no shared writer, no
new lock. Two tabs may hold different values (each writes its own and applies it on its next load); neither reads the
other's.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the reader section now describes the Aa menu, the variables it sets, the width
  cap, the sandbox's `mirrorType`, and the print reset.
- `.claude/skills/optimize/references/invariants.md` — updated: serif is still the author's by default, but the
  reader may set the author in sans, and the written levels are then told by colour and size; a change relying on
  serif-versus-sans alone must hold in both fonts.
- `README.md`, `README.zh-CN.md` — not changed (upstream `f76eb4d` changed no README: the five levels and the
  anchoring promise are unchanged).
- `docs/format.md` — not changed: no exported field; the type is a viewer's preference, not part of a paper.
- `site/`, `desktop-mygo/` — not needed: the payload copies `textfold/web/`.
- `docs/upstream/2026-10-22.md` — not changed: it is the round's review.

## How it was verified

- `python .claude/hooks/verify.py` — 366 tests, OK (R15 baseline 362; four new contract tests).
- `node --check textfold/web/reader.js` and `i18n.js`; `git diff --check` clean.
- In the in-app browser on a disposable paper: the Aa button sits between Export and the language picker and is
  labelled `字号、栏宽和字体`; opening it shows Size 100% / Width Narrow Standard Wide / Font Serif Sans-serif and
  the reset; one step larger gives 108% and the column 740px at a 1280px viewport (700 × 1.08 capped by
  `100vw - 540px`); Narrow gives 648px (600 × 1.08); Sans-serif changes the author's words to the sans stack while
  the written levels stay sans; reset clears `--fs`, both data attributes, the stored value and hides itself;
  `Escape` and a click outside close the menu; a click on Notes (which stops propagation) closes it; the choice
  survives a reload; `.zhost` carries `data-font="sans"`, `data-width="narrow"`, `class="zhost app"` and the inline
  `--fs` (empty again after a reset). No console or server error.
- Not observed: the zoom animation itself and the alignment of its last frame. The preview tab never ran an animation
  frame (`requestAnimationFrame` returned none while the page was hidden), so a zoom could not be played through; the
  sandbox's attributes were read instead, and the `html[…]` → `:host(…)` rewrite it relies on is unchanged code.
- `textfold-verifier` — one pass, one blocking finding. (1) **Blocking, fixed:** `mirrorType` copied only font and
  width; the size is an inline `--fs` on `<html>` and the sandbox's copy of the sheet has `:host { --fs: 1 }`, so the
  neighbouring keyframe was laid out at 100% and a non-default size ended its zoom misaligned (the verifier reproduced
  the precedence in headless Chrome: page 740px / 19.98px at 108%, sandbox 700px / 18.5px). Fixed by mirroring `--fs`
  as an inline property on the host, with a test. (2) The sandbox did not get the `app` class, so in the MyGo app at a
  wide window its `--colmax` differed from the page's; fixed by mirroring `app`/`compare` (and on this machine's app
  page the host now carries `class="zhost app"`). (3) A click on Notes, Export or Legend left the Aa menu open,
  because those buttons stop the click before a bubble listener; fixed by listening in the capture phase (checked by
  clicking Notes with the menu open). (4) Kept highlights, the paragraph preview, the quoted passage in a note and the
  notes list's highlight stayed serif in sans mode; switched to `--text`. (5) The record claimed a print-reset
  description in `docs/DEVELOPMENT.md` that was not there, and
  `.claude/skills/optimize/references/invariants.md` still stated serif/sans as the only mark of authored vs written
  text; both updated. (6) Its process note (untracked tests and record) is the staging state before this commit; all
  files are committed together.

## Measured

| | before | after |
|---|---|---|
| Python tests | 362 | 366 |
| Column width at 1280px, default / 108% / 108% narrow | 700px | 700px / 740px / 648px |
| `localStorage['textfold.type']` after serif→sans, standard→narrow at 108% | absent | `{"size":1.08,"width":"narrow","font":"sans"}` |
| Sandbox host at 108% / sans / the app page | no host attributes | `--fs: 1.08`, `data-font="sans"`, `class="zhost app"` |

## Not measured

- **Zoom smoothness: unmeasured.** The change adds a menu, changes CSS variables, and calls `mirrorType` on each
  change; the zoom's own path is untouched except that the sandbox now lays out with the same font and width as the
  page. No `tools/zoombench.py` run was made (it needs `playwright` and exported `out/compare/` pages, neither
  present), so the axis is not reported as unaffected.
- **The end of a zoom with a non-default type**: not watched (no animation frames in the preview tab). `c38804e`
  exists because that frame was visibly off; here it was checked by mechanism — the sandbox host's attributes and
  inline `--fs` after each change, and the verifier's headless reproduction of the `:host` precedence — not by eye.
- **The MyGo app's page** (`html.app`, the rail at 1300px, `--colmax: calc(100vw - 592px)`) was not rendered; the rule
  is upstream's and the class is set by `app.html`.
- **A phone width** (where the width row is hidden and the author's sans size is 16px × `--fs`) was not checked.

## Pitfalls

- The type is per browser, not per paper and not stored on the server: clearing site data resets it, and another
  browser or the MyGo app starts at 100% / standard / serif.
- `--fs` is an inline custom property on `<html>`; the print rule overrides it with `!important`. A stylesheet that
  tries to set `--fs` without `!important` will lose to the reader's choice.
- Sans-serif makes the author's words and the written levels both sans; they are told apart by colour and size (the
  header comment in `reader.css` says so). A theme that changes those colours without keeping that contrast would
  weaken the five levels' visual grammar.
- `.typepick` and `.langbtn` both have `order: 3`; the Aa button comes first because it is inserted before the
  language picker in the DOM. A toolbar rebuilt in another order would swap them.
- The menu is hidden when the reader zooms (`setType` returns while `busy`); a pressed key during a zoom does nothing
  and the menu stays as it was.
- The sandbox's layout depends on mirroring everything on `<html>` that its copy of the sheet reads: `data-font`,
  `data-width`, the inline `--fs`, and the `app`/`compare` classes for `--colmax`. A new html-level class or variable
  that changes the column must be added to `mirrorType`, or a zoom's last frame will sit apart from the page again.
- Kept highlights and the previews follow the reader's font for the author's words; the notes' own text and the
  printed export stay serif, as the reader's writing rather than the paper's.

## Rejected

- **A server setting or a per-paper type.** The reader's own browser is where a viewer's eyes are; storing it per
  paper would make a paper look different on another machine and add a writer to the paper's folder for no gain.
- **Only the sandbox fix (`c38804e`) without the menu.** `applyType` and `data-font`/`data-width` do not exist in this
  fork, so the fix alone is a no-op; the two commits are one change.
- **The draggable paragraphs and the drag handle upstream carries in the same file.** External editor/app linkage
  (`textfold://`, dragging a paragraph out) is out of this round's scope; only the type menu was taken from the hunk's
  tail.
