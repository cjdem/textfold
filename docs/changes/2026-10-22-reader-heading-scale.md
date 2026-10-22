# The reader's headings are a scale

**Date:** 2026-10-22
**Branch:** `worktree-reader-heading-scale`

## What and why

The three heading depths were 24px, 19px and 16.5px: close enough that a section and its subsection read as the same
kind of line, and the deepest was smaller than the surrounding text at the reader's usual size. This is the first
slice of upstream `fb9f95c` (the round's R18 was split into headings, the Topic map and the margins, as the review
recommended): a section is 27px with a rule under it, a subsection 21.5px, the next level as large as the text (18.5px)
and lighter; at Topic a heading becomes a card's label. Nothing else in the commit — the parent/newrow grouping of
Topic cards, the mind map and the margins switch — is taken here.

## The change

- `textfold/web/reader.css` — `.chunk.l2 > .hd` 27px/700, margins 56/16 × `--fs`, 8px of padding and an inset shadow
  rule under it (a shadow rather than a border so `looks()` copies it into the zoom's keyframes); `.chunk.l3 > .hd`
  21.5px/680; `.chunk.l4 > .hd, .chunk.l5 > .hd` 18.5px/650; `.chunk.l5 > .hd` in `--ink-2`; the Topic card's heading
  cancels the rule and the padding (`box-shadow: none; padding-bottom: 0`). All sizes and margins still scale with
  `--fs`.
- `tests/test_reader_headings.py` — three contract tests: the scale's sizes and weights, the section's rule (and the
  Topic card's having none), and the deepest heading's lighter ink.
- `docs/DEVELOPMENT.md` — the reader section now says what the heading scale is and why the rule is a shadow.

## Docs checked

- `docs/DEVELOPMENT.md` — updated (above).
- `README.md`, `README.zh-CN.md` — not changed: no level, promise or command changed; a heading's size is not in them.
- `docs/format.md` — not changed: headings are the parsed document's, not an exported format.
- `site/`, `desktop-mygo/` — not needed: the payload copies `textfold/web/`.
- `docs/upstream/2026-10-22.md` — not changed: it is the round's review.

## Decisions

- **Take the heading slice alone.** R18's three parts touch different code (headings are CSS, the map is a large
  reader change, margins are the type state and a CSS rule); one change per pull request and independent verification
  favour three. The review said the same.
- **A shadow for the rule, not a border.** The zoom's copies take a computed look (`looks()` writes out the shadow);
  a border would need the box model copied too. This is upstream's reason and it holds here.
- **The Topic card cancels the rule explicitly.** Without it a section heading read at Topic (a card's label) would
  draw a 27px-scale rule under 13.5px text.

## Concurrency and locks

None: CSS and a test; no data, no writer, no server file.

## How it was verified

- `python .claude/hooks/verify.py` — 373 tests, OK (R17 baseline 370; three new contract tests).
- `git diff --check` clean.
- In the in-app browser on a paper with a section and a subsection: at Full the section heading computed 27px/700 with
  8px of bottom padding and `inset 0 -1px 0` in the paragraph's colour, the subsection 21.5px/680, a paragraph 18.5px
  (serif); at Topic both headings were a card's label at 13.5px/650 with no shadow and no padding; one size step (108%)
  took the card heading to 14.58px and the section's would follow `--fs`. No console or server error.
- `textfold-verifier` — one pass, no blocking finding. It confirmed the heading block is upstream's byte for byte, that
  every value scales with `--fs` and nothing with `--lh`, that `looks()` copies the shadow and the rect includes the
  8px padding, that the Topic card's rule is cancelled by specificity and never merges into a Full heading's copy
  group, and it mutation-tested the three tests (they caught 27→24px, a removed `box-shadow: none`, a changed selector
  and a removed l5 rule). Its non-blocking findings, all fixed: the scale test asserted bare literals, so a heading
  changed to `font-size: 27px` (ignoring the Aa size) or a deleted padding stayed green — now the `calc(… * var(--fs))`
  wrappers, both margins and the padding are asserted; nothing pinned the shadow's reason (`looks()`), now asserted;
  the Topic claim checked a rule's text rather than the cascade, now every Topic heading rule with a shadow must
  cancel it. It also found the paper title capped at 26px on a narrow window while a section heading is 27px — upstream's
  own pair, kept and recorded as a Pitfall — and a wording overstatement in `docs/DEVELOPMENT.md`, corrected.
- One full-suite run failed on a transient `ConnectionAbortedError` in a local-socket test; two immediate reruns were
  373 tests OK. The change adds no Python and no networking, so the flake is not attributable to it.

## Measured

| | before | after |
|---|---|---|
| Python tests | 370 | 373 |
| Section / subsection / next heading at Full, 100% | 24px / 19px / 16.5px | 27px / 21.5px / 18.5px |
| Rule under a section heading | none | `inset 0 -1px 0` in `--line`; none on a Topic card |

## Not measured

- **Zoom smoothness: unmeasured.** The heading sizes and their rule are inside the keyframed layout; `looks()` carries
  the shadow, but no `tools/zoombench.py` run was made (it needs `playwright` and exported `out/compare/` pages,
  neither present), so the axis is not reported as unaffected.
- **The deepest heading's lighter ink** (`.chunk.l5`) was not rendered: the fixture has sections and subsections only
  (levels 2 and 3), and no l5 chunk was made. The rule is asserted by the test.
- **A print** of the new heading margins was not exercised.

## Pitfalls

- A section's rule is an inset shadow on the heading; a copy that writes out only borders would lose it.
- The Topic card's heading is 13.5px regardless of depth (the card's label), so the scale collapses at Topic by design.
- The heading sizes scale with `--fs`, not `--lh`; line spacing leaves headings alone.
- On a window under 640px the paper's own title is capped at 26px while a section heading is 27px, so a section can
  outrank the title there. It is upstream's pair, left as it is; a narrow-window title is a separate change.

## Rejected

- **`fb9f95c` in one change.** It carries three unrelated features (headings, the Topic map, margins) in +312 lines;
  the review recommended three and the round's task table allowed it.
- **Keeping 24/19/16.5 and only enlarging the text.** It leaves the section and subsection too close to tell apart at
  the reader's size, which is what the change is for.
