# Export opens on the two everyday Markdown files; the rest is one item deeper

**Date:** 2026-10-18
**Branch:** `worktree-export-menu`

## What and why

Item 6b of the confirmed product scope. The Save button opened one dialog that treated the whole
page as HTML, the notes as HTML/PDF/Markdown/JSON, the languages and the original-PDF choice as
equal formats; the two files a reader most often wants — the notes and the reading card as
Markdown — were several choices in, or in the card drawer. Export now opens a small menu with
those two directly, and **More export options…** opens the existing dialog unchanged for the whole
page and the other formats.

## The change

- `textfold/web/reader.js` — the button beside the notes is now **Export** and opens a menu:
  - **Export notes (Markdown)** — every highlight, note and question in reading order, using the
    whole-paragraph choice saved in the dialog; disabled with a count of 0 when there is nothing
    to export;
  - **Export reading card (Markdown)** — the card drawer's own export, in the app when the card
    exists; a paper without a card opens the drawer with its "make a card" note;
  - **More export options…** — the existing save dialog: the whole page as one HTML file or a PDF,
    the marks as HTML, PDF, Markdown or JSON.
  The menu carries the same terms-of-the-original-text notice the dialog carries. It closes on an
  outside click, when the notes menu opens, and when the dialog opens. The notes menu's footer
  now says **More export options…** too.
- `textfold/web/card.js` — `window.PFCard.exportMarkdown()` loads the card if the drawer has not
  been opened and then runs the existing export, which flushes unsaved edits first. A failed load
  is remembered, so the drawer and the next export try again instead of treating its placeholder
  as the card; "Add to reading card" follows the same rule.
- `textfold/web/i18n.js` — `sv_export`, `sv_export_notes`, `sv_export_card`, `sv_more` in English
  and Chinese; the now-unused `sv_save` removed.
- `textfold/web/reader.css` — the menu's width, its count and disabled state, and the licence line.
- `textfold/web/tutorial.js` — the first-run guide's notes page says Export, not the old Save
  button (both languages).
- `README.md`, `README.zh-CN.md`, `docs/DEVELOPMENT.md` — the export section and the table row now
  describe the menu and the dialog; the CLI export line stays for item 6c.

## Decisions

- Keep the dialog as the one place every file goes, and put the two everyday exports in front of
  it. The existing dialog, its saved state (`textfold.save`), its language and PDF choices and
  `POST /api/export` are unchanged, so all formats and the licence notice remain.
- The direct notes export uses all three kinds and the saved whole-paragraph choice. A reader who
  wants only highlights, or JSON, uses More export options; the menu is for the common file, not a
  second set of checkboxes.
- The card item calls the drawer's own export instead of a second implementation: it flushes edits
  and uses `cards.markdown()`, so the file is identical to the drawer's.
- Exporting from the menu bypasses the dialog but not its notice: the menu repeats the licence
  sentence.
- Rename the button from Save to Export. The dialog keeps the title Save; the button opens a menu
  of exports, and "Save" suggested a file was written immediately.

## Rejected

- One click straight to notes Markdown without a menu: the button would silently choose a format
  and could not offer the card.
- Removing the dialog: whole-page HTML, notes PDF and JSON still need it, and the scope keeps
  them.
- A second, simpler dialog for JSON: more UI for a format the scope calls advanced.
- Exporting the card inside the reader menu without the drawer: the drawer owns the card's save
  state and its flush, and a second export path would drift.

## What is lost

- Whole-page HTML, notes PDF and JSON are one item deeper (Export → More export options…), and
  the notes' kind checkboxes and language choice are only in that dialog.
- The button says Export instead of Save; the dialog is otherwise unchanged.
- No export format, saved preference or capability is removed; the whole-page HTML save and the
  card export still exist.

## How it was verified

- `python .claude/hooks/verify.py` — **188 tests, OK**; `node --check textfold/web/reader.js`,
  `textfold/web/card.js`, `textfold/web/i18n.js` — clean.
- In the browser, on a temporary Markdown document with one note and a card (removed afterwards):
  - Chinese and English menus show Export notes (Markdown) with the note count, Export reading
    card (Markdown), More export options…, and the licence sentence;
  - with the note deleted, the notes item is disabled and shows 0;
  - Export notes writes the Markdown blob: front matter, `format: textfold/notes@1`, the note text
    and the quoted passage;
  - Export reading card writes the card Markdown blob (`format: textfold/reading-card@1`);
  - More export options and the notes menu's footer both open the save dialog, with the whole
    text and its HTML/PDF formats by default;
  - the menu closes on an outside click, and opening it closes the notes menu.
- An independent verifier drove the page in headless Chrome. It found that the Export menu and the
  language menu could be open together and overlap (they are now mutually exclusive, Escape closes
  the Export menu, and the button carries `aria-haspopup`/`aria-expanded`), that a failed direct
  notes export was silent (it now opens the save dialog with `sv_failed`), that an open menu kept
  a stale count and labels after notes or the interface language changed (the button's update now
  redraws an open menu), that a failed card load was reported as "no card" (the drawer now opens
  with its load error), and that the October 13 entry described the wrong action. All were fixed.
- A second verifier pass, reading the fixes and the whole diff, found more: one failed card GET
  left the placeholder counting as loaded, so the card export could never retry in that session
  (the failure is now recorded, and the drawer, the export and "Add to reading card" retry it);
  the first-run guide still named Save (fixed); the failure dialog opened on the last-saved choice
  and its Save would have written the whole page, not the notes that failed (it now opens on
  Notes/Markdown); the reading-card button stops its click from bubbling and left the Export menu
  open behind the drawer (outside clicks are now heard in the capture phase, so every menu closes
  even on such buttons); `role="menu"` had no menu items (the three buttons now carry
  `role="menuitem"`, the licence line `role="none"`, and a keyboard pick or Escape returns focus
  to the Export button); and the notes button left the language menu open (it now closes it, as
  the other buttons already closed the Export menu). All were fixed.
- After those fixes, headless Chrome re-drove the menu paths on a temporary Chinese Markdown
  document with a Chinese note: Export and the language, notes and reading-card buttons each close
  the other menus (the card button included, though it stops the click), a keyboard Escape closes
  the menu and leaves focus on Export, the forced-failure dialog shows 保存失败：磁盘已满 with
  Notes/Markdown selected, a card GET made to fail opens the drawer with its error and a later
  click retries and clears it, and Export notes wrote a UTF-8 Markdown blob with the Chinese title,
  quote and note text and `format: textfold/notes@1`.
- The test document, note and card were deleted (`papers/` removed, `library.json` removed), the
  preview server stopped, and `git diff --check` is clean.

## Invariants

- **Parsed HTML through `textfold/semantic.py`:** no parser or renderer change; the menu's values
  are static strings and counts.
- **Parser change renumbers atoms:** not applicable.
- **Persistent writes serialized per document:** no writer added. The notes export only reads the
  in-memory notes; the card export calls the existing route, which flushes under the card's own
  lock.
- **UTF-8 on a Chinese Windows:** the new Chinese menu strings are UTF-8 in `i18n.js` and rendered
  in the browser; the exported Markdown kept its Chinese-capable front matter. No new file or
  subprocess encoding path.
- **No new dependencies:** none.

## Not measured

- Zoom smoothness: **unmeasured** on this machine (no `playwright`, no exported pages under
  `out/compare/`). The change adds toolbar markup and listeners but no zoom or rendering path; no
  claim is made that it is unaffected.
- No real file-picker or desktop save dialog was completed: the browser check stubbed the picker
  and read the blob it would have written; `saveAs` and the desktop path are unchanged.
- The card item without an existing card (it should open the drawer with its no-card note) was
  read in the code but not clicked in the browser; the verifier exercised it and the failed-load
  path.
- The menu on a phone width and in print were not checked separately; the verifier checked
  320/360/375 px widths and print media.
- The menu has no automated test: the suite is Python-only, so its count, disabled state, direct
  exports, mutual exclusion and failure paths rest on the browser checks. A future regression
  would leave the suite green.
- The menu is a `role="menu"` of `menuitem` buttons without arrow-key movement; Tab and Enter work,
  as they do in the language menu beside it.
- The card export awaits its first GET before opening the file picker. On a local card that is
  fast; a GET slower than the browser's transient-activation window would fall back to a download
  rather than the picker. The notes path is synchronous.
