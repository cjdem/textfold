# New imports of RTF, OpenDocument and old Office files are refused; stored documents still open

**Date:** 2026-10-18
**Branch:** `worktree-legacy-formats`

## What and why

Item 5 of the confirmed product scope. The formats only the local PDF engine could read — RTF,
OpenDocument (ODT, ODS, ODP) and old Word, PowerPoint and Excel files (DOC, PPT, XLS) — are easy
to save as DOCX, PPTX, XLSX or PDF, and keeping them in the import path means a failed conversion
or a 3.4 GB engine for a file the reader could hand over in a modern format. New imports of those
seven kinds are refused with a clear message; OFD, EPUB and MHTML are untouched, and a document
already in the library keeps opening, its generated layers and its stored original.

## The change

- `textfold/engine.py` — new `LEGACY` set of the seven extensions. They stay in `FILES` and in
  `kind_of`, so a document converted before the rule still opens and can be converted again where
  the engine reads it; the module docstring and the API comment say the same.
- `textfold/server.py` — `take_file` refuses a new legacy import with `{"error":
  "legacy-format"}`, 400, after the PDF-magic branch and after the "converted before" lookup, so a
  PDF renamed `.odt` goes to the PDF route and an existing `doc-<hash>` reopens; nothing is
  written to `uploads/` on refusal. Endpoint and function docstrings updated.
- `textfold/__main__.py` — `textfold get` refuses a new legacy file with the same sentence and
  exit 2; a PDF renamed to a legacy extension is read as a PDF, and an already-converted legacy
  file is allowed. It is the other documented entry point, so leaving it open would have made the
  rule false.
- `textfold/web/app.js`, `app.html` — the picker and the drop-zone hint no longer offer the seven
  extensions; a dropped legacy file is still uploaded so the server answers (which keeps a PDF
  renamed `.odt` working), and `errText` shows the server's message. `i18n.js` — `md_only` names
  Word (DOCX), PowerPoint (PPTX) and Excel (XLSX); new `legacy_format` in English and Chinese.
- `textfold/zotero.py` — an item with a supported attachment chooses it before a legacy one; a
  legacy-only item with a DOI tries the DOI first and otherwise returns the file so `take_file`
  shows the message. `READS` order and the docstring say the legacy types come last.
- `README.md`, `README.zh-CN.md`, `docs/DEVELOPMENT.md`, `textfold/office.py`, and the site's
  `llms.txt` list the narrowed formats and say existing documents stay readable.
- New `tests/test_legacy_formats.py` (11 tests): all seven refused with the message and nothing
  written; case-insensitive; kinds stay known and re-convertible; accepted kinds unaffected; a
  PDF named `.odt` reaches `take_pdf`; a converted legacy file reopens; `get` refuses a new file,
  reads a renamed PDF, and allows a converted file; Zotero prefers HTML over ODT and a legacy-only
  file yields to the DOI.

## Decisions

- Keep the seven kinds in `engine.FILES` and `kind_of`. Removing them there would also hide a
  stored document's original from re-conversion; the refusal belongs at the entry points that
  take a new file.
- Refuse in the server and the CLI, not only in the picker. The picker is a convenience; a drag,
  an agent script or `textfold get` would otherwise import the file anyway.
- Let the UI upload a legacy-named file instead of refusing it in the browser: the server checks
  the bytes first, so a PDF renamed `.odt` still opens as the PDF it is.
- A file already converted under one of these kinds reopens from the drop path: the rule is about
  new imports, not about hiding what the library already holds.
- Zotero tries a supported attachment, then the DOI, then the legacy file. An item with an old
  attachment and an open DOI is readable without a conversion.
- Regeneration is not blocked or warned about. `pipeline.generate` reads `source.html`, never the
  original file, so a stored document regenerates as before; the scope's "say so when
  regenerating" is met where the format is offered again — drop, picker, Zotero, `textfold get` —
  which is the only place the restriction can matter. A regenerate-time "format unsupported"
  message would be false, since the format is not read.

## Rejected

- Removing the kinds from `engine.FILES`: it would also break re-conversion of documents already
  in the library, against the scope's keep-the-data rule.
- Refusing only in the browser: the CLI and an upload straight to `/api/files` bypass it.
- Refusing an already-converted legacy file when it is dropped again: the library copy is exactly
  what the scope keeps readable.
- Deleting `office.py`, the engine or a format parser: the scope keeps them; this only narrows
  what is newly imported.
- A new setting to re-enable the formats: the confirmed scope removes them from the first batch,
  and a switch would leave the same maintenance.

## What is lost

- New RTF, ODT/ODS/ODP and DOC/PPT/XLS imports, and the automatic conversion of such a file to a
  document. The reader must save it as DOCX, PPTX, XLSX or PDF first.
- Zotero items whose only attachment is one of those kinds no longer open from the attachment;
  with a DOI they try Europe PMC, otherwise they show the format message.
- Existing documents, their layers, their stored originals and their re-conversion where the
  engine or API reads the kind are unchanged.
- OFD, EPUB and MHTML are untouched.

## How it was verified

- `python .claude/hooks/verify.py` — **188 tests, OK** (7.1 s), 11 of them new.
- `node --check textfold/web/app.js`, `node --check textfold/web/i18n.js` — clean;
  `python site/build.py` — `unfilled: []`.
- In the browser: the file picker's `accept` and the drop-zone hint contain none of the seven
  extensions; dropping `paper.odt` shows the Chinese `legacy_format` message, and
  `POST /api/files` with the same name answers 400 `legacy-format`; a renamed PDF reaches
  `take_pdf` in the server tests.
- An independent verifier pass found that `textfold get` still imported the formats, that Zotero
  preferred a legacy attachment over HTML, that a renamed PDF was refused in the browser, that a
  converted legacy file was refused when dropped again, and several doc/string inaccuracies. All
  were fixed and the tests extended; a second pass confirmed the refusal at every entry point, the
  reopen and PDF paths, the Zotero order, and that a refusal writes nothing.
- The one deliberately unchanged item is noted under Decisions: regeneration never reads the
  original, so no regenerate-time prompt was added.

## Invariants

- **Parsed HTML through `textfold/semantic.py`:** no parser or renderer change; the new messages
  are set as text.
- **Parser change renumbers atoms:** not applicable; no parser change.
- **Persistent writes serialized per document:** no new writer. A refusal happens before any
  upload write, and a stored document's reopen only reads and queues the existing generation.
- **UTF-8 on a Chinese Windows:** the new Chinese string is UTF-8 in `i18n.js`; the browser showed
  it correctly and the site build stayed clean. No new file or subprocess encoding path.
- **No new dependencies:** requirements and package metadata untouched.

## Not measured

- Zoom smoothness: **unmeasured** on this machine (no `playwright`, no exported pages under
  `out/compare/`); no reader or zoom file changed, and no claim is made that it is unaffected.
- A real engine or MinerU API conversion of a legacy file was not run; the tests stub the
  conversion path and verify the gates.
- A real Zotero instance with a mixed-attachment item was not exercised; the ordering and DOI
  fallback are unit-tested with stand-ins.
- The Zotero library tag still shows Zotero's own "best attachment" type, which can say ODT while
  the reader picks an HTML child; it is a label in the list, left as it was.
