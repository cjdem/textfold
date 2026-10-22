# The sidebar can be pinned beside a paper

**Date:** 2026-10-22
**Branch:** `worktree-sidebar-pin`

## What and why

Over a paper the sidebar opened from its rail and covered the text; there was no way to keep it open beside the paper.
This is R19 of the round, upstream `b977bba`: a pin in the sidebar's head keeps it open beside a paper as on the
landing, folding and opening as there, and the page, the zoom bar and a PDF beside the text start at the sidebar's edge.
A window too narrow to hold the sidebar and the margins both has the notes and answers in the column, as it already does
beside a PDF, and the reader stops stacking them at the margin.

The pin is a browser preference (`localStorage` `textfold.sbpin`), not a per-paper one, and the sidebar still starts
folded over a paper when it has never been pinned.

## The change

- `textfold/web/app.js` — the pin icon and `PIN_KEY` (`textfold.sbpin`); a `.sb-hbtns` group with the pin beside the fold
  button; `.sb-pin` toggles `setPinned`; `dockState()` works out `sb-docked` (a paper, pinned, open, window wider than
  720px, the small layout's breakpoint) and `sb-narrow` (the width left of the sidebar under 1248px), and asks the
  reader to lay out again when either class changes; `setPinned` keeps the pin and, when pinning, the fold state; a fold
  stores its state while pinned (as on the landing) and always re-docks; an unpinned open sidebar still folds when the
  reader clicks outside it. The remembered width is applied before the first dock tests it. The resize listener calls
  `dockState` again, and the three width changes that tell the page (drag end, double-click reset, arrow keys) keep the
  dock and the reader together.
- `textfold/web/app.css` — the pin's styles (pressed in the accent colour, its head filled; hidden under 720px); the
  docked layout: `html.app.sb-docked` sets `--rail` to the sidebar's width and takes that width out of the column's cap,
  `sb-narrow` and `compare` give the column the window back, and a docked sidebar casts no shadow because it no longer
  covers the text; `html.sb-narrow` puts `.side`, `.lside` and their chunk hosts in the column. The docked rules sit
  before the focus rules, so focus still takes the rail's room back (`html.app.focus { --rail: 0px }`).
- `textfold/web/i18n.js` — `PINS`: the pin and unpin names in English and Simplified Chinese (the fork's two reading
  languages; upstream's other ten are not carried).
- `textfold/web/reader.js` — `layoutSides` stands down beside a pinned sidebar in a narrow window, as it does beside a
  PDF.
- `textfold/web/reader.css` — a PDF's default width beside a docked sidebar also subtracts the rail, so the text keeps
  the reader's 420px; a width the reader dragged is already clamped that way when the dock tells it to lay out again.
- `tests/test_app_sidebar_pin.py` — three contract tests: the words in both languages, the pin's state and every place
  the dock is asked again, and the docked/narrow CSS (including the focus rule coming after the dock's).
- `docs/DEVELOPMENT.md` — the sidebar paragraph now describes the pin, the dock and the narrow-window fallback.

## Docs checked

- `docs/DEVELOPMENT.md` — updated (above).
- `README.md`, `README.zh-CN.md` — not changed: no command, level or promise changed.
- `docs/format.md`, `docs/notes-format.md` — not changed: no export or stored record changed.
- `site/`, `desktop-mygo/` — not needed: the payload copies `textfold/web/`.
- `docs/upstream/2026-10-22.md` — not changed: it is the round's review.

## Decisions

- **Two languages, as the scope locks.** Upstream writes the pin in twelve; this fork reads and speaks English and
  Simplified Chinese only, so the other ten are not added.
- **No links selector in the narrow layout.** Upstream also moves `.lk` into the column; this fork removed argument
  links, so only the answers and the notes have a margin.
- **The dock's rule before focus's.** Both set `--rail` with the same specificity; keeping the dock first lets focus's
  `0px` win, which is how focus already behaved. Focus keeps the docked column cap, though — the cap still subtracts
  the sidebar while focus has it off-screen; upstream does the same, and it is recorded as a pitfall rather than
  changed here.
- **A width change made without a drag is announced too.** Upstream only tells the page after a drag ends; a double-click
  reset or the arrow keys would leave `sb-narrow` and the reader's stacking stale. One code path, three call sites,
  asserted by the test.
- **The pin is shown on the landing.** It is the same head; there it only records the preference for the next paper.
- **A docked PDF leaves the text its 420px.** Upstream's default pane width (`min(46vw, 860px)`) does not know the rail,
  so at 1200px with a 280px sidebar the text would get 368px. The docked rule subtracts the rail too; a dragged width
  is already clamped by the reader, which re-runs its clamp when the dock tells it to lay out again.

## Concurrency and locks

None on the server: no document, parser or stored layer is touched. The pin, the fold state and the sidebar's width are
three `localStorage` keys written whole, last-writer-wins across tabs as the type already is; they are browser
preferences, not data.

## How it was verified

- `python .claude/hooks/verify.py` — 381 tests, OK (R18c baseline 378; three new contract tests). `node --check` on
  `app.js` is clean; `git diff --check` clean.
- In the in-app browser, on a temporary data directory holding an imported Markdown paper with sections, a subsection
  and a note, `TEXTFOLD_NO_MODELS=1`, at 1400, 1600, 1000 and 640px:
  - a paper opened folded to the rail (body and zoom bar at 52px); the rail's list button opened the sidebar over the
    page (shadow, page still at 52px);
  - the pin made it docked: `html.app.sb-docked`, `--rail` 280px, body padding and the zoom bar's left at 280px, the
    sidebar's shadow gone, the pin pressed and named "Unpin: open it over the text", `textfold.sbpin` `1`; the page
    reloaded still docked;
  - at 1600px with the sidebar 280px (1320px left) the classes were `sb-docked` only; the note's `.lside` computed
    `position: absolute` at the left of the text, as a margin; at 1000px (720px left) `sb-narrow` joined, the note
    computed `position: static` and 648px wide, in the column, and `--colmax` was `100vw`;
  - the arrow keys took the sidebar's width to 640px and `sb-narrow` came on (`100vw` cap, page padding 640px); a
    double-click put it back to 280px and `sb-narrow` went off, without reloading;
  - `F` (focus) with the sidebar docked took the page's room back (body padding 0, `--rail` 0, sidebar translated off);
    `Esc` restored the dock; folding a pinned sidebar removed the dock and remembered the fold, reopening from the rail
    docked it again; unpinning returned the shadow and the fold-on-outside-click, and an outside click folded it;
  - at 640px the pin was `display: none` and not clickable, and an open sidebar covered the page as before;
  - at exactly 720px the sidebar opened over the page and no dock was attempted: body padding and the zoom bar stayed at
    0, the small layout's, with the sidebar's shadow back;
  - a reload with a stored 400px width at 1600px came up docked with `sb-narrow` already on (1200px left), its note in
    the column — the first dock had run after the remembered width was applied;
  - the landing page had no `sb-docked`; no console warning or error and no server error.
- `textfold-verifier` — one pass, one blocking finding, fixed: the first dock ran before the remembered sidebar width
  was applied (`setWidth` came later), so a paper that loaded pinned with a stored width got the wrong `sb-narrow`
  state until a resize; `dockState()` now runs after the width, and the test pins the order. It also ran the suite (381
  OK), `node --check`, `git diff --check`, 38 in-memory mutations (30 caught) and a headless Chrome run of the real
  sheets and `app.js` at 720, 721, 1200, 1300, 1474 and 1574px. Its non-blocking findings, all fixed here: docking at
  exactly 720px made no room for the page because the small layout starts there (the dock now needs a window wider than
  720px); the default PDF width beside a docked sidebar squeezed the text under 420px (new reader.css rule); `setPinned`
  not calling `dockState` and the `sb-docked` toggle were untested (now asserted); the i18n test did not check the
  `w[i]` bindings or that the words reach `S` (now asserted); the `layoutSides` check was a substring, so `||` → `&&`
  passed (now the whole condition is asserted); and the record's verifier line was a stub. It confirmed the port is
  faithful, the extra dispatch sites are the fork's only additions besides the dropped `.lk` selectors, and it could
  not judge zoom smoothness (playwright absent).

## Measured

| | before | after |
|---|---|---|
| Python tests | 378 | 381 |
| Sidebar over a paper, never pinned | folded to the rail | folded to the rail (unchanged) |
| Sidebar open over a paper with the pin on | not possible | open beside it, page at its edge |
| Page (and zoom bar) left, 1600px, 280px sidebar | 52px | 280px |
| Column cap beside it (1600px) | `100vw - 592px` | `calc(100vw - 540px - 280px)`; `100vw` when narrow |
| Notes at 1000px with the sidebar open | beside the text (or over it) | in the column |
| Reload pinned with a stored 400px width, 1600px window | — | docked, `sb-narrow` on at load |
| Window at exactly 720px, pinned, open | — | no dock; the sidebar covers the page with its shadow |

## Not measured

- **Zoom smoothness: unmeasured.** The dock changes the page's width and tells the reader to lay out again; a dock that
  happens during a zoom was not exercised, and no `tools/zoombench.py` run was made (it needs `playwright` and exported
  `out/compare/` pages, neither present), so the axis is not reported as unaffected.
- **A PDF beside the text** (`html.compare`): no paper with a source PDF was in the fixture, so the PDF starting at the
  sidebar's edge, the docked `compare` cap and the 420px the text keeps beside it are checked by the CSS contract only.
- **A drag of the sidebar's edge** was not performed with a pointer; the arrow keys and double-click exercise the same
  width path and the drag-end dispatch is asserted by the test.
- **A touch device under 720px**: the pin is hidden by the stylesheet; not tried on a phone.

## Pitfalls

- `--rail` becomes the sidebar's width when docked, so anything positioned from the rail (the page's padding, the zoom
  bar, the PDF pane) follows without its own rule.
- The narrow test is about the width left of the sidebar (`innerWidth - sb < 1248`), not the viewport: a 1600px window
  with a 640px sidebar is narrow, and a 1300px window with a 280px sidebar is too.
- Focus keeps the docked column cap while it hides the sidebar, so the reading column can stay narrower than the window;
  it is upstream's behaviour and is left as it is.
- The preview pane did not fire a `resize` event when its emulated size changed; the check dispatched one by hand. A
  real window resize does fire it.
- Hiding the pin under 720px uses `display: none` on the button, but a folded sidebar already hides its head; the pin is
  no more reachable there than the fold button.
- Below 720px a pinned sidebar is not docked, does not fold when the reader clicks outside it (the pin keeps it open),
  and its pin is hidden by the small layout: the fold arrow is the way out until the window widens. Upstream has the
  same pair of rules.

## Rejected

- **Upstream's `.lk` selectors.** This fork has no argument links.
- **The other ten languages.** The round locks the reader to English and Simplified Chinese.
- **Docking without a pin.** It would change what every reader sees on opening a paper; the pin keeps the old default.
- **A per-paper pin.** The sidebar is the same list for every paper, and the landing already keeps itself this way.
