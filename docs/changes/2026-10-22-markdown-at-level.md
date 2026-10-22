# The whole text saves as Markdown at the level being read

**Date:** 2026-10-22
**Branch:** `worktree-md-level-export`

## What and why

The save dialog could give the whole text as one HTML file (made by the server, in the language being read or all of
them) or a PDF at the level being read, and the notes as Markdown; there was no Markdown of the text itself. This is
R20 of the round, upstream `7d94f25`: a third format for the whole text, **Markdown, at {level}**, written in the
language being read. It carries the headings, each section's summary where the level shows one (Topic, Takeaway, Key),
the paragraphs as bullets at those levels and as paragraphs at Brief and Full, the marks chosen under their paragraph
(a highlight alone marked in the author's words, `==…==`, where those words are in the level), and at Topic an outline
that an outliner or a mind-map plugin draws. The notes' own Markdown keeps its format; both files now share the head and
the note writer.

## The change

- `textfold/web/reader.js` — the notes' head (`mdHead`) and one note's block (`noteMd`) are split out of `notesMarkdown`
  and used by both files; `docMarkdown` walks the document at the level being read: the front matter says `level` and
  `lang`, the title is the one being read (the original in italics below it when translated), the whole paper's notes
  come first, then each section's heading (its depth, capped at six), its summary where the level shows one, its notes,
  and its units — a bullet each at the written levels (a list marker when the unit has one), a paragraph each at Brief
  and Full (a caption in italics), a highlight marked in place where the level shows the whole of its anchor's tokens
  (`markedText`; the tokens, not a search in the text, so a repeated word is not marked twice or split) and otherwise
  under the paragraph as a quote with its block id. A CJK document's section summary is written at Brief too, where the
  page shows it. The helpers it needs (`LEVEL_NAMES`, `piecesText`, `secTitle`, `headingOf`, `summaryOf`, `markedText`)
  are added beside it. The save dialog offers `md` for the whole text, names it for the level
  (`… (Full).md`) and makes it in the browser; the all-languages choice stays the server-made HTML's.
- `textfold/web/i18n.js` — `sv_md_level`: "Markdown, at {level}" / "Markdown（{level}层）".
- `tests/test_reader_markdown_export.py` — four contract tests: the words in both languages, the dialog's format list
  and file name, the document builder's level/notes/highlight decisions (a highlight placed by its tokens, a CJK
  document's summary at Brief, the heading depth, list markers, captions, the blank-line collapse), and the notes'
  Markdown still written through the shared writers with its block ids and format line.
- `docs/DEVELOPMENT.md` — the save paragraph lists the new format and what it carries.

## Docs checked

- `docs/DEVELOPMENT.md` — updated (above).
- `docs/notes-format.md` — not changed: the notes' file keeps its format (`textfold/notes@1`, block ids, callouts).
- `README.md`, `README.zh-CN.md` — not changed: no command, level or promise changed.
- `docs/format.md` — not changed: it describes the stored document and the CLI's one-level Markdown (`fold.markdown`),
  which carries section ids and a map and has no notes. The Save dialog's Markdown is a second, browser-made shape; the
  stored format is untouched.
- `site/`, `desktop-mygo/` — not needed: the payload copies `textfold/web/`.

## Decisions

- **In the dialog, not the one-click menu.** The menu's Markdown is the notes' export, one click for every mark; the
  whole text at a level is a choice like the level's PDF, so it sits with the formats in the dialog.
- **One language.** The current one: the level's words and the page's summaries are already in it. The all-languages
  file remains the server-made HTML, which can carry every language a paper has.
- **The page's level, not a separate choice.** `level` (and a paragraph opened in place, through `levelOf`) decides what
  goes in, so a reader who followed a `#level=` link or came back to a saved place exports what is on screen.
- **A highlight already in the words is a mark, not a block.** Where the level shows the highlighted words, the export
  marks them `==…==`; where it does not (Topic, Takeaway, Key), the note goes under its paragraph with its `^n-…` block
  id, exactly as the notes' file writes it. The notes' own Markdown is unchanged for unit and section notes; a note on
  the whole paper now writes no empty quote line (upstream's writer; the base wrote `> ` for it).
- **A highlight is placed by its anchor's tokens, not by searching for its words.** Upstream finds the passage with
  `indexOf` on the quote, which marks a repeated word's first occurrence and can split a word; the export inserts
  `==…==` at the tokens the note anchors on, and only when the level shows all of them.
- **A CJK document's summary is written at Brief.** The page shows the section's line there (`.doc.cjk[data-level="3"]
  .stake`, R15); the export follows the page rather than upstream's Topic/Takeaway/Key alone.
- **One writer for both files.** The head (properties, title, byline) and a note's block are shared, so a change to the
  notes' Markdown cannot leave the whole-text one behind.

## Concurrency and locks

None: the export is made in the browser from what is loaded; no server file or document is written, and no model is
called.

## How it was verified

- `python .claude/hooks/verify.py` — 385 tests, OK (R19 baseline 381; four new contract tests). `node --check` on
  `reader.js` and `i18n.js` clean; `git diff --check` clean.
- In the in-app browser, on a copy (read-only) of a real paper with English and Chinese layers and a source PDF, in a
  temporary data directory, `TEXTFOLD_NO_MODELS=1`; the file picker was stubbed in the page to capture the file:
  - at Full, the dialog offered **Markdown, at Full** beside the HTML and the level's PDF; the file was named
    `… (Full).md`, 26,094 characters, its front matter `level: full`, `lang: en`, its headings `##`/`###` by depth, and
    the highlight appeared as `==In this paper, the dynamic model of unmanned helicopter==` in the abstract; a note
    with words sat under its paragraph with `^n-md2`, its text and its link back;
  - at Brief (`#level=Brief`), 16,655 characters, no section summaries, two real list bullets (the paper's lists), both
    marks under their paragraph (their words are not in the Brief line);
  - at Key (`#level=Key`), 13,271 characters, 14 section summaries in bold and 92 bullets (a topic each), the abstract's
    highlight as a quote under its paragraph;
  - at Topic (`#level=Topic`), 4,875 characters, 16 headings, 14 summaries and 92 topic bullets — an outline, no
    paragraph text;
  - in Chinese (`?lang=zh#level=Key`), the front matter `lang: zh`, the H1 the translated title with the original in
    italics below, Chinese summaries and bullets, 4,643 characters; the notes' quotes stayed in the language they were
    made in;
  - a highlight anchored on the second "design" in a paragraph that also says "designs" (u87, token 56) exported as
    `the ==design==.` — the right occurrence, no `==designs==` and no split word;
  - the one-click **Export notes (Markdown)** still wrote `format: textfold/notes@1` and `^n-md1`/`^n-md2`;
  - no console warning or error and no server error.
- `textfold-verifier` — one pass, one blocking finding, fixed: a highlight was placed with `indexOf` on its quote (the
  upstream line), so a repeated word was marked at its first occurrence and could be split (`this paper ==design==s…`);
  `markedText` now inserts the mark at the anchor's tokens, and the browser check above reproduces the fixed output. It
  also ran the suite (385 OK) and a Node harness that slices the real functions out of `reader.js` and reproduces every
  number in this record (Full 26,094, Brief 16,655, Key 13,271, Topic 4,875, zh Key 4,643), compared the refactored
  `notesMarkdown` with the base (identical for unit and section notes; a whole-paper note no longer writes an empty
  quote line), and mutation-tested the four tests. Its non-blocking findings, all fixed here: the record's "unchanged" claim now
  names the whole-paper note difference and the tests keep the `!whole` guard; a CJK document's summary was missing at
  Brief though the page shows it (the condition now includes `CJK_DOC && level === 3`); six mutations the tests could
  not catch (empty-unit skip, heading depth cap, list markers, the blank-line collapse, captions, the highlight search)
  are now pinned as exact lines; the pitfall about opened paragraphs was wrong (`levelOf` counts them as Full, so their
  highlights are inline); and the record/DEVELOPMENT now say that display equations, figures and tables are not in the
  file and that `docs/format.md`'s one-level Markdown is a different, CLI format. It confirmed a paper with no layers
  exports without throwing, and that no server file is written.

## Measured

| | before | after |
|---|---|---|
| Python tests | 381 | 385 |
| Whole-text formats in the save dialog | HTML (app), PDF | HTML (app), PDF, Markdown |
| Markdown at Full (the fixture paper) | — | 26,094 chars, `==…==` on the highlight |
| Markdown at Topic (the fixture paper) | — | 4,875 chars: 16 headings, 14 summaries, 92 topic bullets |
| Markdown in Chinese at Key | — | 4,643 chars, translated title + original |
| Highlight on the second "design" (u87, token 56) | — | `the ==design==.`; no `==designs==` |
| File name | — | `<id> <title> (<level>).md` |

## Not measured

- **Zoom smoothness: unmeasured.** The export reads the reader's data and DOM; no zoom path changed, but no
  `tools/zoombench.py` run was made (it needs `playwright` and exported `out/compare/` pages, neither present), so the
  axis is not reported as unaffected.
- **A paper with no generated layers** was exported by the verifier, not by this session's browser: it did not throw,
  and wrote the headings and the local briefs with no summaries.
- **Inline formulas** are written by `tokPlain` as `$…$`; the fixture's paragraphs were not inspected for one.
  **Display equations, figures and tables are not in the file at all** — it walks the text's units; the page shows
  them, the export does not.
- **A static page** (one exported HTML file, no server) offers the whole-text Markdown too, but only the app page was
  tried; the desktop app's own save dialog (`window.desktop.saveFile`) was not exercised (the browser's picker was
  stubbed).
- **CJK at Brief** was not exported (Chinese was checked at Key); the CJK cleaning inside `pieces` is shared with the
  page, not changed here.

## Pitfalls

- At Full and Brief, a highlight whose words the level shows is `==…==` and has no `^n-…` line; at Topic, Takeaway and
  Key it is a quote with its block id under the paragraph — and so is one whose passage the level shows only in part. A
  paragraph opened in place counts as Full (`levelOf`), so a highlight in it is inline even at Topic.
- Display equations, figures and tables are not in the file: it walks the text's units only. A paper that leans on them
  exports less than the page shows.
- The final `\n{3,}` collapse runs over the notes' own text and quotes too, so three blank lines inside a note become one.
- The level line and the format's label come from the interface language (`T[ui]`), so a Chinese paper read with an
  English interface says "Key · TextFold" in the file; the paper's text is in the language being read.
- The summary comes from the section's `lad.take`; a paper generated without layers has none, and the folded exports
  then carry less.
- The title's italics line appears only when the H1 is a translation; the front matter always keeps the original title.

## Rejected

- **Putting it in the one-click menu.** That menu is the notes' Markdown; a whole text at a level is a format choice
  beside the level's PDF.
- **A server-made Markdown (a new `/api/export` format).** The browser has the level, the opened paragraphs and the
  notes as they stand; a server path would rebuild them and could differ from the page.
- **All languages in one Markdown file.** A translated layer is a reading of the same text; mixing them in one file
  makes neither readable. The HTML export keeps that choice for its own file.
