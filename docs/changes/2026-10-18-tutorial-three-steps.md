# The first-run guide is three pages: bring a text in, fold it, check it against the original

**Date:** 2026-10-18
**Branch:** `worktree-tutorial-three-steps`

## What and why

Item 6e of the confirmed product scope. The guide had four pages: import, fold, whose words, and
a fourth that mixed the original, asking and notes. It now has three: import, fold, and one page
on checking what you read against its source — the author's words set apart from the model's, the
model's lines pointing back to the author's sentences, and the original pages beside the text.
Asking and notes are left to their buttons and the selection bar, where they are used.

## The change

- `textfold/web/tutorial.js` — `PAGES` is three entries; the third is `voice`, `anchor` and
  `original`. The `ask` and `notes` cards are gone, with their words and their pictures, and the
  art CSS only they used (`tk-hl`, `tk-note`, `tk-warm`). The subtitle says **Three short pages**
  / **三页**; page three is **Back to the original** / **回查原文**; the old fourth-page label is
  removed. The dots derive from `PAGES`; the keyboard strip is a fixed line and is unchanged.
- `docs/requirements/product-scope.md` — item 6e ticked.

## Decisions

- Keep **whose words** and **AI points to its source** on page three with **beside the original**:
  "check it against the original" means both the original pages and the trace back to the
  author's sentences. Removing them would also remove the only explanation of the serif/sans
  convention and of the evidence links.
- Drop asking and notes rather than squeeze them in: their entry points are visible in the reader
  (the selection bar, **Ask the whole text**, **Notes**), and a three-page guide does not need to
  teach every button.
- Add no new coach marks. The scope's "the rest as nearby hints" is already served by the
  selection bar, the ask and notes buttons, the role legend and the tooltips; another layer of
  first-run pointers would add UI rather than remove it.
- Keep the page dots and the keyboard strip: the dots follow the pages, and the strip is one line
  about the reader's keys.

## Rejected

- Keeping four pages and shortening them: the scope asks for three steps.
- A page of asking and notes without pictures: still a fourth page, and the buttons explain
  themselves.
- Removing the keyboard strip: it is one line and covers the reader's keys.

## What is lost

- The first-run guide no longer explains asking or notes; a new reader meets them through the
  selection bar and the two buttons, with no page describing what notes do or how they stay
  through a zoom.
- The guide is one page and two cards shorter.

## How it was verified

- `node --check textfold/web/tutorial.js` is clean; `python .claude/hooks/verify.py` — **188
  tests, OK**; `git diff --check` is clean.
- Headless Chrome, on a temporary Markdown paper (removed afterwards):
  - `TFTutorial.open('en')` and `open('zh')` each show three dots;
  - page 1: Bring a text in (Paste a link, Or drop a file, Read in your language), 56 SVG
    elements; page 2: Fold and unfold (Five levels, A map of the text, Zoom under your fingers),
    83; page 3: Back to the original (Serif is the author, AI points to its source, Beside the
    original), 50, with **Got it** and no next arrow;
  - the Chinese guide says 三页，看懂怎样把一份文本折起来读。 and its page three is 回查原文 with
    衬线体是作者的原话 / AI 的每句话都有出处 / 对照原文;
  - a screenshot of the Chinese third page shows the three cards, three dots and the done button.
- The Chinese strings are UTF-8 and rendered as written; no encoding errors.
- Zoom smoothness: **not measured** (no `playwright`, no `out/compare/` pages on this machine).
  The change is the guide's own words and pictures; no reader or renderer file is touched, and no
  claim is made about the measured smoothness.

## Invariants

- **Parsed HTML through `textfold/semantic.py`:** not applicable; no parser or renderer change.
- **Parser change renumbers atoms:** not applicable.
- **Persistent writes serialized per document:** no writer added or changed.
- **UTF-8 on a Chinese Windows:** the new Chinese strings are UTF-8 in `tutorial.js` and rendered
  in the browser. No new file or subprocess encoding path.
- **No new dependencies:** none.

## Not measured

- Phone widths were not driven; the existing `max-width: 720px` rules turn the cards into rows and
  hide the keyboard strip, and the guide's card count fits either way.
- The guide was opened through `TFTutorial.open`, not from the landing's first visit or the
  **How it works** button; those callers are unchanged.
- The guide has no automated test; the suite is Python-only, so a future edit could break a page
  or leave a missing picture with the suite green.
