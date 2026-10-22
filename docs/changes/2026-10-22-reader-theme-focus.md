# The reader's appearance, line spacing, the place it was left and focus

**Date:** 2026-10-22
**Branch:** `worktree-reader-theme-focus`

## What and why

The reader had one look: the system's light or dark, one line spacing, no memory of where a text was left, and no way
to put the chrome away. This ports the final state of upstream `e5bd668` + `a670e57` + `920a270`: in the Aa menu, a
brightness (light, dark, or the system's) and a style (the default, or paper) that combine, each style having its light
and its dark; a line spacing (tight, standard, loose); and a focus mode (`F`, `Esc` to leave) that moves the top bar,
the zoom bar, the sidebar and the chat off the page and brings them back at the pointer's edge. The reader also keeps
where each text was being read — the paragraph at the reading line and the level — and comes back there when the text
is opened again, with a word over the page saying so and a 2px line under the top bar showing how far in it is. The
middle commits added four styles and reading-time labels; upstream cut them to two styles and no minutes before
v0.10.22, and this port takes that final state.

## The change

- `textfold/web/reader.js` — the type state gains `mode` (`auto | light | dark`), `style` (`default | paper`) and
  `lead` (`tight | standard | loose`, `--lh` 0.9/1/1.15), validated per field at startup; a stored `theme` from an
  earlier demo is read as `mode`, and `theme: "paper"` as the paper style. `applyType` sets `data-theme` and
  `data-style` (absent at the default), `--lh` (absent at standard). `mirrorType` copies the two new data attributes
  onto the zoom's sandbox. The Aa menu gains the brightness, style and spacing rows and a foot with Focus and Reset;
  `isType0` counts all of it. `F` toggles focus, `Esc` leaves it; the edge reveal is pointer-driven (mouse move, or a
  touch at an edge for four seconds). Where the text was left is read before the first frame, saved 700 ms after a
  scroll or a zoom and on `pagehide`/`visibilitychange` (`textfold.pos`, the last 300 texts), and restored once the
  page is laid out and again when the fonts are in; the progress line is drawn on scroll.
- `textfold/web/reader.css` — the colour choices: the system's dark rule now keys on the absence of `data-theme`, the
  chosen dark and light are `html[data-theme]`, the paper style is `html[data-style="paper"]` with its own dark and its
  own "system dark" rule (`color-scheme` follows); `--lh` multiplies the line-height of the reading levels, the
  section stakes, figure captions and the Chinese line height, and a print is standard spacing; the focus rules
  (top bar, zoom bar, chat moved and faded, not removed), the progress line, the pill, the style dots and the menu's
  foot.
- `textfold/web/app.js` — the app reads the stored brightness and style before the reader is built, so the sidebar and
  the landing take them too.
- `textfold/web/app.css` — focus takes the sidebar off to the left (the page takes the rail's room) and brings it back
  at the pointer's edge.
- `textfold/web/card.css` — the reading card's drawer had its own dark colours keyed to the system alone, so with Light
  or Paper chosen on a dark-mode computer its error and status lines were light on light; each now applies to the
  system's dark only when no choice was made, and to `html[data-theme="dark"]` on screen.
- `textfold/web/i18n.js` — fourteen words for the appearance, the place and focus, in English and Simplified Chinese;
  the Aa button's name is now "Reading appearance" / "阅读外观", which is what the dialog holds.
- `tests/test_reader_type.py` — four more contract tests: the appearance words in both languages, the constants and
  the position/focus hooks in the reader, the theme/style/`--lh`/focus rules in the CSS (with the reading rules' own
  `var(--lh, 1)` and no stale `:not([data-theme="light"])`), and the reading card's dark rules following the choice
  (eight in all).

## Data contract

`localStorage['textfold.type']` is JSON `{size, width, font, mode, style, lead}`: `mode` `auto | light | dark`,
`style` `default | paper`, `lead` `tight | standard | loose`; each invalid or missing field falls back to its default.
`localStorage['textfold.pos']` maps a text's id to `{u, l, y, t}` — the unit at the reading line, the level, the unit's
viewport top and the time — pruned to the 300 most recent. Nothing is stored on the server. States: the menu closed or
open; focus on or off; edges shown or hidden while focus is on. Transitions: a type change snaps the zoom, keeps the
paragraph on screen, relayouts, rebuilds the keyframes and persists (ignored while a zoom plays); `F`/`Esc` toggle
focus with a resize so the column reflows; a scroll or a level change schedules a position save. Failure paths: a
private window reads nothing and ignores writes (defaults every load; no saved place); malformed JSON in either key
falls back (`{}` / defaults); a saved unit that no longer exists is ignored; a link that names a place wins over the
stored one; `pf-keep` (the page again after a generation) suppresses the restore so the app's own place wins.

## Concurrency and locks

None added. Both keys are `localStorage`, written by the reader alone; no server file, no shared writer, no new lock.
Two tabs of one text last-writer-wins on the position. Two tabs of different texts each read the whole map before
writing it, so if both write inside the same few microseconds one text's saved place can be lost; the window is one
read-and-write in one task, and the next scroll of that text saves it again — recorded in Pitfalls rather than locked,
because `localStorage` has no compare-and-swap to lock it with.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the Aa paragraph now covers the brightness, the style, the line spacing, focus and
  the stored place; the print reset mentions the spacing.
- `README.md`, `README.zh-CN.md` — not changed (upstream changed none: the levels, the anchoring and the reading
  promise are unchanged; appearance is a viewer's preference).
- `docs/format.md` — not changed: neither key is part of a paper or an export.
- `site/`, `desktop-mygo/` — not needed: the payload copies `textfold/web/`.
- `.claude/skills/optimize/references/invariants.md` — not changed: focus moves the column with a resize (as a window
  resize does), and the zoom's own promise — nothing laid out while it runs, every level in the type it was set to —
  holds.

## How it was verified

- `python .claude/hooks/verify.py` — 370 tests, OK (R16 baseline 366; four new contract tests).
- `node --check` on `reader.js`, `i18n.js` and `app.js`; `git diff --check` clean.
- In the in-app browser on a disposable 40-paragraph paper (1280×900): the Aa menu shows Appearance (Auto/Light/Dark),
  Style (Default/Paper), Size, Font, Line spacing, Width and a Focus foot; Light gives `data-theme="light"` and the
  `#FAF9F7` page, Paper `#F3EEE4`, Paper + Dark `#221E19`; Loose sets `--lh: 1.15` and the author's line height from
  29.97px to 34.47px (18.5 × 1.62 × 1.15); the whole choice is stored as
  `{"size":1,"width":"standard","font":"serif","mode":"dark","style":"paper","lead":"loose"}`. Focus (button or `F`)
  sets `html.focus`, moves the top bar up 57px and shows the pill `专注模式：按 F 或 Esc 退出`; `Esc` leaves it; with the
  app's rail, focus takes the body's 52px padding to 0 and slides the sidebar out, and `Esc` brings both back.
- Position saving: after scrolling, `textfold.pos` holds `{u:"u36", l:4, y:262, t:…}` for this text, and the earlier
  entry was replaced rather than accumulated. Restoring, the progress line and the touch edge reveal were not observed
  (see below).
- `textfold-verifier` — one pass, one blocking finding. (1) **Blocking, fixed:** `card.css` (a fork-only sheet) keyed
  its dark colours to the system alone, so on a dark-mode computer with Light or Paper chosen the reading card's
  errors and statuses were light on light (≈1.6–1.8:1); each rule now also applies to `html[data-theme="dark"]` on
  screen, with a contract test. (2) Two tabs of different texts can each read the position map and overwrite the
  other's entry within one debounce; no compare-and-swap exists in `localStorage`, so this is recorded in Pitfalls and
  the record no longer claims the loss is impossible. (3) The new CSS test could not fail: it asserted strings that
  `:root:not([data-theme="light"])` also satisfies, and nothing checked a scaled line-height; the test now asserts the
  reading rules' `var(--lh, 1)`, the absence of the stale selector, paper's system-dark rule and the card's rules.
  (4) The second restore pass after `document.fonts.ready` could yank a reader who had already scrolled; it now runs
  only if the scroll position has not moved since the first pass. (5) `color-scheme` followed only the explicit
  choice; added to both system-dark rules. (6) The landing ignored the legacy `theme` names the reader maps; `app.js`
  now maps them too. (7) The Aa dialog's accessible name still said "Text size, width and font"; renamed. (8) The
  DEVELOPMENT sentence overstated which lines `--lh` scales, and the restore guard tested a `#s=` no page uses; both
  corrected.

## Measured

| | before | after |
|---|---|---|
| Python tests | 366 | 370 |
| Page colour, system dark / Light / Paper / Paper+Dark | one (system) | `#1B1915` / `#FAF9F7` / `#F3EEE4` / `#221E19` |
| Author line height at 100%, standard → loose | 29.97px | 34.47px |
| `localStorage['textfold.type']` after the appearance choices | size/width/font only | + `mode`, `style`, `lead` |

## Not measured

- **Zoom smoothness: unmeasured.** The change adds CSS variables and data attributes, saves a position on scroll and
  zoom, and mirrors two more attributes into the sandbox; no frame was measured (`tools/zoombench.py` needs
  `playwright` and `out/compare/`, neither present), so the axis is not reported as unaffected.
- **Restoring the place, the progress line and the touch edge reveal were not watched**: this preview tab ran no
  animation frames, and both the restore's scroll and the progress line's draw happen in `requestAnimationFrame`. The
  save side, the stored shape and the unit-still-exists guard were checked directly. The pill was not seen for a deep
  position either (the saved unit was near the start, where the reader does not announce).
- **The MyGo app's landing page and sidebar** were not rendered with a stored theme; `app.js` reads the same keys as
  the reader and sets the same attributes.
- **A phone width** and the touch edge reveal were not exercised.
- **Printing** was not exercised; the stylesheet resets `--fs`, `--lh` and `--colw` under `@media print`.

## Pitfalls

- The reading place is keyed by a text's id and a unit id. A parser change that renumbers units can leave a saved unit
  pointing at another paragraph; the id still exists, so the guard (`unitEl.has`) does not catch it. The paragraph at
  the reading line moves with the text — that is the point — but a stale place is not marked stale.
- A saved place is written 700 ms after the last scroll/zoom; closing the tab within that window writes on `pagehide`
  or when the page is hidden, not otherwise.
- Two texts open in two tabs can lose one saved place if their writes interleave inside the same debounce; the map is
  read and written whole, and `localStorage` has no compare-and-swap. The next scroll of the lost text saves it again.
- The brightness is stored per browser and shown on the landing too; a dark page with the paper style is dark paper,
  not the warm light page.
- Focus moves the column (the rail's room is given up) with a resize; the zoom's keyframes are rebuilt after it, as
  after a window resize. A change that assumes the column is fixed while focus toggles would be wrong.
- `data-theme="light"` is a choice, not the absence of dark: a system dark with light chosen stays light, and the
  system-dark media rule keys on the attribute's absence.

## Rejected

- **The reading-time labels on the bar (`e5bd668`).** Upstream removed them in `a670e57`; their minutes were an
  estimate that made the bar noisy, and the final state is what this round asked for.
- **The four styles (`sage`, `graphite`).** Cut upstream in `920a270` to two; porting the middle state would diverge
  from v0.10.22.
- **A server-side reading position.** It belongs to the reader's browser, as the type does; storing it in the paper
  would make a text resume differently on another machine and add a writer to the paper's folder.
- **Hiding the chrome by removing it.** Focus moves and fades the bars rather than removing them, so nothing in the
  column moves except the rail's room and the edge reveal has something to bring back.
