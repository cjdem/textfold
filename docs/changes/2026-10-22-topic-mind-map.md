# Topic: cards under their section, or the text as a map

**Date:** 2026-10-22
**Branch:** `worktree-topic-mind-map`

## What and why

At Topic the reader showed one flat grid of cards: a section's own topics and its subsections' sat side by side, and
nothing said which was whose. This is the second slice of upstream `fb9f95c` (R18 was split into headings, the map and
the margins): a section with sections under it now heads a row of their cards, a section that follows a deeper one
starts a new row, and a choice beside the zoom bar switches Topic between those cards and a map of the text's outline —
the title at the left, each section a branch in a colour, each paragraph's topic at a branch's end. The map is drawn
over the page at rest at Topic and only then; a section folds with a click, and a topic opens its paragraph at Key. The
choice is kept in this browser.

## The change

- `textfold/web/reader.js` — the Topic view's state (`textfold.topicview`), the cards/map toggle beside the zoom bar
  (the bar is wrapped in a `.zrow` so the toggle can sit to its right), and the map itself: the tree from the chunks
  (a section under the last higher one; a paragraph's topic under its section; the opening text's under the title), the
  fold states (closed, or sections without their topics), the layout (each node right of its parent, its children one
  under another), the connectors, the map's own buttons ("Open all", "Sections only"), the click on a topic (its
  paragraph at Key, the map gone first) and on a section (fold or open, the section kept where it was clicked). The map
  is shown only at Topic, at rest, with no paragraph opened in place, not beside the PDF and not in focus; a zoom, a
  wheel-zoom or a pinch hides it first. It is drawn again in the new language and when the paper changes language, and
  laid out again when the Aa size changes while it is open; `updateBar` shows the toggle only where the map can be
  drawn; after a zoom `rest()` → `updateBar()` re-syncs it, and `done()` covers the other motions; opening or closing
  the PDF pane re-syncs it. At startup the chunks get the cards' row classes (`parent`, `top`, `newrow`).
- `textfold/web/reader.css` — the row classes for the cards, and the map: the frame over the page, the tools, the
  canvas and its connectors, the root/section/topic nodes, the branch colours, the toggle's look (with the dark rule
  following both the system and the chosen light), the phone layout and print.
- `textfold/web/i18n.js` — the toggle and the map's six words in English and Simplified Chinese.
- `tests/test_reader_topic_map.py` — four contract tests: the words in both languages, the map's hooks and its Topic-only
  condition, the cards' row classes, and the map's own stylesheet including its dark rule. The R18a headings test now
  allows the one Topic heading that draws a rule on purpose (a group's header) and asserts it.
- `docs/DEVELOPMENT.md` — the reader section now describes the grouping and the map.

## Data contract

`localStorage['textfold.topicview']` is `'cards'` or `'map'` (anything else reads as cards). Per browser, for every
text. The map's fold state lives in memory only; a reload starts from the outline open (the control the reader last
used is not kept). Nothing is stored on the server.

## Concurrency and locks

None: no server file, no shared writer. The one key is a viewer's preference.

## Docs checked

- `docs/DEVELOPMENT.md` — updated (above).
- `README.md`, `README.zh-CN.md` — not changed: no level's meaning or command changed.
- `docs/format.md` — not changed: the map is a view of the parsed document, not an export.
- `site/`, `desktop-mygo/` — not needed: the payload copies `textfold/web/`.
- `docs/upstream/2026-10-22.md` — not changed: it is the round's review.

## Decisions

- **The map is a view over the page, not a replacement for it.** The page stays laid out under the map, so a zoom
  starts from the cards exactly as before and the map can be dropped in the same event (`mapAway` on `kick`). This is
  upstream's design and it is what keeps the zoom's promise.
- **Topic only, at rest.** The map is not shown while a paragraph is opened in place, beside the PDF, or mid-zoom; each
  of those would either change the page under it or fight the layout it is drawn from.
- **A section with sections heads a row of their cards.** The grouping is classes on the existing sections (`parent`,
  `top`, `newrow`) rather than a rebuilt grid, so the cards' DOM and the zoom's copies are untouched.

## How it was verified

- `python .claude/hooks/verify.py` — 377 tests, OK (R18a baseline 373; four new contract tests).
- `node --check textfold/web/reader.js` and `i18n.js`; `git diff --check` clean.
- In the in-app browser on a paper with two sections and a subsection: at Topic the section with a subsection carried
  `parent top`, the second section `newrow`; the toggle sat beside the zoom bar in a `.zrow` and showed 卡片/导图; the map
  drew a root, the sections at depths 1 and 2 and four topics at branch ends with their positions set by the layout;
  "Sections only" left the one topic outside any section and put `+1` on each section; "Open all" restored four; folding
  the first section left two topics and `+2` on it; reopening restored four; clicking a topic hid the map; the choice
  was stored as `map` and switching back stored `cards`. No console or server error.
- Not observed: the click on a topic arriving at Key (the preview tab runs no animation frames), the toggle hiding at
  Full, and the map's frame in the app beside the sidebar.
- `textfold-verifier` — one pass, no blocking finding. It confirmed the map block and every hook are byte-identical to
  upstream, that the i18n is the upstream block cut to two languages, that the dark rule follows this fork's
  `data-theme`, that the map injects only HTML already in the document, and that `kick()` hides the map before the
  first frame. Its non-blocking findings, all fixed: (1) changing the Aa size while the map was open left its measured
  layout stale (labels grew, rows overlapped, connectors pointed at old centres), and re-opening it did not redraw —
  `setType` now re-renders an open map and clears the render key otherwise; (2) opening the PDF beside it did not hide
  the map, and closing it did not bring it back — `openCompare`/`closeCompare` now call `mapSync`; (3) focus left the
  map over the "text alone" — `setFocus` now hides it on entry and re-syncs on exit, and `mapSync` refuses while
  `html.focus`; (4) the toggle was shown where the map cannot be drawn (a paragraph opened in place, beside the PDF) —
  `updateBar` now hides it there; (5) and (6) two tests could not fail for the hooks they claimed (the kick line, the
  `mapSync` condition, the grouping's `next`/`prev` and its `(c.num || c.title)` guard) — now asserted exactly; (7)
  `docs/DEVELOPMENT.md` still said every Topic heading is a label with no rule (a group's header has one) and that every
  section gets its own colour (subsections inherit) — corrected; (8) the record said `done()` re-syncs after a zoom
  (it is `rest()` → `updateBar()`) — corrected.

## Measured

| | before | after |
|---|---|---|
| Python tests | 373 | 377 |
| Topic cards under a sectioned section | one flat grid | `parent top` row header, `newrow` after a deeper one |
| Topic views | cards | cards or map (`textfold.topicview`), map over the page at Topic |

## Not measured

- **Zoom smoothness: unmeasured.** The map adds a fixed overlay, a scroll-driven layout and a toggle; no
  `tools/zoombench.py` run was made (it needs `playwright` and exported `out/compare/` pages, neither present), so the
  axis is not reported as unaffected.
- **The map's click-to-Key** (a topic opening its paragraph at Key) was not watched: the preview tab ran no animation
  frames, so `setLevel` never completed. The map hiding on the click was observed.
- **The app's frame** (`mapFrame` beside the sidebar) and a phone width were not rendered.
- **A long paper's map** (hundreds of topics, its own scrolling) was not tried; the fixture has four topics.

## Pitfalls

- The map's fold state is not kept: a reload draws the outline open again, even though the cards/map choice is kept.
- The map is drawn from `pieces(uid, 0)` (the topic tokens of the current language), so a language switch redraws it;
  a translation with no topic for a paragraph leaves that topic out of the map.
- `mapSync` is called from `updateBar` and `done()`; a new place that changes the level without either would leave the
  map over a level that is no longer Topic.
- The map covers the page from the top bar down (`z-index: 6`, under the bar's 20); the zoom bar stays above it, which
  is where its toggle lives.

## Rejected

- **Rebuilding the Topic grid for grouping.** Class-based rows keep the cards' elements and their keyframe copies as
  they are; a rebuilt grid would change the zoom's layout for a view-only feature.
- **Keeping the map under the zoom.** The map is an overlay over a laid-out page; playing a zoom under it would move
  the page under a fixed drawing. Upstream's map-away-first rule is kept.
- **Porting the whole of `fb9f95c` at once.** The margins switch (R18c) touches the type state and every margin's CSS;
  it is a separate change.
