# The reader stops drawing stored argument links, and the page stops carrying them

**Date:** 2026-10-18
**Branch:** `worktree-links-ui-removed` (at `219ea29`)
**Supersedes:** `2026-10-18-links-generation-stopped.md` on one point — stored links no longer
render; that entry's generation change still stands.

## What and why

Item 7 of the confirmed product scope, the second step after item 4 stopped generating argument
links. Stored links in older English layers were still drawn in three places: rows in the right
margin, lit chips on the Topic map, and hover previews. The scope removes that interface. The
stored edges stay on disk, `store.apply_en` still assembles them, and `textfold get` still exports
them; the reader no longer receives or draws them.

## The change

- `textfold/web/reader.js` — removed the edge index (`EDGES`, `outOf`/`inOf`),
  `edgeTarget`/`targetLabel`, `renderSide` and the `sideNode` calls, the `.side-links` half of the
  margin, `clearFocus`/`mapFocus` and their calls, the `.lk` hover preview and click, and the
  Topic-map linked-chip lighting. Kept the left notes margin, `.side-notes`, the shared
  `go`/Back pill, author `a[href^="#"]` jumps and previews, footnote previews, note-hover
  previews and the role legend. `plain` no longer strips `linked`/`focal`; the warm-up no longer
  checks `mapfocus`.
- `textfold/web/reader.css`, `app.css` — removed the `--rel-*` colours, `.rel-*`, `.linked`,
  `.focal`, `.mapfocus`, the `.lk` rules, and the `.lk` parts of the responsive, print and
  compare rules; kept `.side`, `.lside`, `.side-notes`, `.peek` and the note cards.
- `textfold/web/i18n.js` — removed the `rel` helper, both argument-link label maps and the `eq`
  label, which no longer has a reader.
- `textfold/build.py` — the page payload no longer includes `"edges"`.
- `textfold/links.py` — the docstring says the reader no longer draws stored links and
  `textfold get` still exports them.
- `docs/DEVELOPMENT.md` — the Notes paragraph, the Links paragraph and the module map updated.
  `docs/notes-format.md` — the right margin no longer mentions links. `docs/format.md` — the
  Links section says the reader no longer draws them.
- `tests/test_links_stopped.py` — a new test: a stored edge still assembles and `fold.document`
  exports it, while `build.payload` does not carry it. **189 tests.**
- `docs/requirements/product-scope.md` — item 7 ticked.

## Decisions

- Remove all `.lk` margin rows, including the author `rel:"ref"` rows. The author's **inline**
  figure and reference jumps and their previews stay; the scope keeps the jumps, not the extra
  margin list, and the margin existed for the argument links.
- Leave `resolve()` as it was. A draft added a `data-id="eq:…"` fallback on the theory that a
  margin row could reach an equation with no DOM id; review showed no inline href can name such
  an id (an equation without a source id is never linkable, and one with an id keeps it in the
  DOM), while the fallback made a dangling `#eq0` link jump to a generated equation. Removed.
- Keep `store.apply_en` and the stored edges on disk: item 4 left the data path alone, and
  `textfold get` is a kept programmatic format. Deleting the data or the module is a separate
  decision, not this interface change.
- Stop sending `edges` in the page payload. The reader has no consumer left; a dead
  multi-kilobyte field in every page and saved file invites accidental rendering. The CLI still
  exports links, so the data remains reachable.
- Remove the `eq` and relation labels with their only consumers.
- Keep the Topic-map chips and their click-to-open; only the edge-driven dimming goes.

## Rejected

- Keeping the margin rows for author `rel:"ref"` edges: that would keep the `.lk` machinery, its
  previews and its CSS alive for a feature the inline links already provide.
- Removing `store.apply_en`, `links.py`, or the stored edges: that is a data change with its own
  risks, and the scope says the data stays.
- Leaving `edges` in the page payload "just in case": the reader would carry a field nothing
  reads, and a later change could start drawing it again by accident.

## What is lost

- Stored argument links (supports / builds on / qualifies / explains) are no longer visible in
  the reader: no margin rows, no map lighting, no hover previews, no click to jump.
- The author cross-reference margin rows also disappear; the inline figure, table and reference
  links still preview and jump.
- Pages saved before this change embed the old reader and still draw their links; they are user
  files and were not rewritten. New saved pages carry no edge data and have no link UI.
- No user data on disk is deleted, and `textfold get` still exports stored links.

## How it was verified

- `python .claude/hooks/verify.py` — **189 tests, OK** (6.9 s), one of them new; `node --check`
  on `reader.js` and `i18n.js` clean; `git diff --check` clean.
- Headless Chrome on a temporary Markdown paper whose `layers/en.json` was given a `supports`
  edge between two units (removed afterwards):
  - the page's `paper-data` has no `edges` key, and `.lk` and `.side-links` count 0;
  - at Topic, hovering a chip adds no `.mapfocus`, `.linked` or `.focal`;
  - a note on the first paragraph still shows as a card in the left margin at Full, and hovering
    that paragraph at Topic still opens its note preview;
  - the Legend button still opens and lights a role.
- The author anchor, footnote and reading-card evidence paths were read against the diff, not
  driven in a browser (the fixture has no anchors or card).
- Chinese round trip against a temporary data directory (removed afterwards): a Markdown file
  with a Chinese heading, body, emphasis, quote, list and equation was imported through
  `POST /api/import`; the reader payload decoded back to the same text; a Chinese note was stored
  and read; `POST /api/export` returned a 1.3 MB HTML whose decoded payload still carried the
  text and the note; `source.md` was valid UTF-8, and no replacement character appeared.
- Zoom smoothness: **not measured** (no `playwright`, no `out/compare/` pages on this machine).
  The change removes per-hover work and per-level `clearFocus` calls, but no frame timing was
  taken, and no claim is made.

## Invariants

- **Parsed HTML through `textfold/semantic.py`:** no parser or renderer file changed; previews
  still render sanitized document HTML.
- **Parser change renumbers atoms:** stored edges are still applied by unit id on assembly, as
  before; the page no longer receives them, and regeneration still drops them.
- **Persistent writes serialized per document:** no writer added or changed. The browser fixture
  wrote an `en` layer in a temporary data directory; production writers are untouched.
- **UTF-8 on a Chinese Windows:** removed strings only; no encoding path changed.
- **No new dependencies:** none.

## Not measured

- The author anchor and footnote previews and the reading-card evidence jumps were not driven in
  a browser against a real paper with figures, equations and citations; their code paths were
  checked in the diff, and the fixture paper has none.
- Saved HTML files from before this change still draw stored links with their embedded old
  reader; no inventory of user files exists and none was rewritten.
- The reader UI has no automated test (the suite is Python-only), so a future regression in the
  removal or in a kept preview path would leave the suite green.
