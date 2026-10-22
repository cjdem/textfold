# An EPUB's chapters are decoded before they are parsed

**Date:** 2026-10-22
**Branch:** `worktree-epub-decode`

## What and why

An EPUB's content documents are UTF-8 unless they say otherwise. A chapter saved without a declaration was handed to
lxml's HTML parser as bytes, and that parser guesses: when a non-ASCII byte comes early in the document it guesses
Windows-1252, so a Chinese chapter became `ä¸­æ–‡…` in the imported document. This change decodes each chapter before
the parser sees it, honouring the byte-order mark and the chapter's own declaration (XML declaration or
`<meta charset>`), and decoding the rest with the office reader's fallback order (UTF-8, gb18030, cp1252, latin-1).
A chapter that names Latin-1, GBK, Big5 or UTF-16 is read in it, a full XHTML chapter's head title is not its text,
and an SVG spine item still yields its text.

The one-line version of upstream's fix (`_fragment(_decode(bytes))`) was tried first and broke three things the
verifier caught: the decoded string was wrapped in a `<div>` as a fragment, which drops `<head>`/`<body>` and hoists
the XHTML `<title>` into the document as a paragraph; `_decode` tries gb18030 before cp1252, so an undeclared Latin-1
chapter and a *declared* cp1252/Big5/Shift-JIS one were misread; and `_decode` has no UTF-16 step, so a UTF-16 chapter
became NULs. Decoding into a string then introduced a fourth: lxml's HTML parser refuses a Unicode string carrying an
XML declaration with `encoding=`, which is the standard EPUB chapter header, so the import failed outright. The final
change strips the declaration (already used to decode) before parsing and fixes all four.

## The change

- `textfold/office.py` — `_chapter(data)` decodes a content document: a UTF-8 or UTF-16 byte-order mark, else the
  encoding its XML declaration or `<meta charset>` names, else `_decode` (UTF-8, gb18030, cp1252, latin-1). A
  declaration that does not decode falls back to `_decode`.
- `textfold/office.py` — `_fragment(str)` drops leading XML declarations and comments (the declaration was already
  used to decode; lxml refuses it in a Unicode string), then parses a whole document as one when the text starts with
  a DOCTYPE, `<html` or `<svg`, so its `<head>` is not hoisted; a fragment (several top-level nodes possible) still
  goes inside a `<div>`. The bytes path is unchanged.
- `textfold/office.py` — `_epub` reads each spine item with `_fragment(_chapter(z.read(part)))`.
- `tests/test_epub_encoding.py` — new: an undeclared UTF-8 chapter with Chinese (fails on the old line with the
  mojibake quoted above); a full XHTML chapter whose head title does not enter the text; the standard
  `<?xml version="1.0" encoding="utf-8"?>` header (which failed to import before the declaration was stripped); a
  chapter naming windows-1252, Big5, Shift-JIS or GBK in its declaration; a chapter declaring windows-1252 or GBK via
  `<meta charset>`; a UTF-16 chapter with a BOM; an SVG spine item whose text is kept; a long comment before the
  DOCTYPE; a document without an `<html>` element and one after a processing instruction.

## Docs checked

- `docs/DEVELOPMENT.md` — not needed: it names `office.py` as the Office/EPUB reader, not the decoders inside it.
- `README.md`, `README.zh-CN.md` — not needed: the supported formats do not change; the import is now correct for the
  format's own default, and an empty chapter is skipped rather than failing the book (recorded under Pitfalls).
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: the structured content keeps
  its shape. (The base parser already left a full XHTML chapter's head out; the change keeps that while fixing the
  text's encoding. A decode-first version that wrapped the document in a `<div>` would have hoisted the title; it was
  rejected.)
- `site/`, `desktop-mygo/`, `.claude/agents/` — not needed: no reader or app change.
- `pyproject.toml`, `requirements.txt` — not needed: no new dependency (lxml and zipfile were already used).

## Decisions

- **The declaration is honoured, and the EPUB default is UTF-8.** A chapter's XML declaration or `<meta charset>` names
  its encoding; a chapter naming none is UTF-8 by the EPUB spec, and only then do the fallbacks run. A chapter that
  declares an encoding its bytes do not fit (a bad file) falls back to `_decode`, as the parser used to guess.
- **A whole document is not a fragment.** `_fragment` wrapped every string in a `<div>`, which is right for a
  fragment with several top-level nodes and wrong for a document: the HTML parser drops `head`/`body` inside a div and
  hoists the title. The wrapper now applies only when the text has no document marker.
- **An SVG spine item is parsed as the document it is.** The document marker set includes `<svg`, so the SVG root is
  walked as before and its `<text>` is kept.
- **An empty spine item no longer fails the book.** The bytes parser raised on empty input, so one empty chapter made
  the whole import `bad-file`; an empty document now has no page and the other chapters import. This is the one
  behaviour change besides the text being right.
- **Re-conversion drops layers.** A parser-shaped import change does not re-parse stored documents: an EPUB converted
  before this change keeps its stored `source.html`; converting it again rebuilds the folder and its layers go, as
  with any re-conversion (`local.store_doc`).

## Concurrency and locks

None added. The change is a pure decode and parse of bytes already read from the zip; no file is written differently
and no lock is involved.

## How it was verified

- `python .claude/hooks/verify.py` — 269 tests, OK (baseline 259; 10 added).
- The undeclared UTF-8 test fails on the previous line with the mojibake quoted in What and why; the declared
  windows-1252/Big5/Shift-JIS/GBK, UTF-16, SVG, standard-declaration and long-comment tests cover the cases the first
  versions broke, and the full-XHTML test asserts the head title is absent from the text.
- `textfold-verifier` — its first pass rejected the one-line version with the three regressions above, plus the SVG
  and empty-chapter changes and several record errors. Its second pass found the standard `encoding=` declaration
  crash (finding 1), the long-comment document false negative, and the record's overclaim about declarations; all
  three are fixed here, with tests. It also confirmed DOCX's mammoth output is unchanged (mammoth escapes marker-like
  text) and that the base parser already kept a full XHTML head out (the record now says so).

## Measured

| | before | after |
|---|---|---|
| tests | 259 | 269 |

## Not measured

- **Smoothness: unmeasured.** No `tools/zoombench.py` run (it needs `playwright` and exported comparison pages,
  neither installed here); the change is in a server-side import, no reader code is touched, and the zoom axis is not
  reported as unaffected.
- A real EPUB from a store was not imported; the tests build minimal ones. A very large chapter was not tried:
  decoding plus parsing holds the chapter as text and as a tree, as the office reader already does for DOCX/HTML.
- A chapter that declares an encoding with a byte sequence of another encoding (a lying declaration) is read in the
  declared one when it decodes, else by the fallback.

## Pitfalls

- An **undeclared** chapter in a legacy encoding is still at the mercy of the fallback order: cp1252 bytes that are
  valid gb18030 are read as Chinese (`région` can become `r問ion`). The EPUB spec makes an undeclared chapter UTF-8,
  and real legacy books declare their encoding; a declaration is the reliable path.
- A declared encoding that Python does not know, or whose bytes do not decode, falls back to the reader's order.
- A UTF-16 chapter is read by its BOM; a UTF-16 chapter without a BOM is not detected (XML requires the BOM for
  UTF-16).
- The head title is excluded because the body is walked; a title that also appears in the body still appears, as it
  should.
- An empty chapter is now skipped rather than failing the book; a book with no readable chapters still fails
  (`bad-file`).
- `_fragment` strips leading XML declarations, processing instructions and comments in a loop, then decides document
  or fragment from what follows; a document marker that comes after other text (not only after those) is still a
  fragment. A content document without an `<html>` element but starting with `<head>` or `<body>` is parsed as a
  document too, so its title stays out of the text; only a malformed document that starts with neither takes the
  fragment path, and its head title can appear as text.
- An XML declaration with `encoding=` is removed before parsing (the text is already decoded); a declaration that is
  not at the start is left as text, which is invalid XML and rare.

## Rejected

- **The one-line port** (`_fragment(_decode(bytes))`): it fixed the mojibake and broke the head title, declared legacy
  encodings and UTF-16.
- **Decoding every chapter with `_decode` only**: it cannot honour a declaration and has no UTF-16 step; a chapter
  that declares its encoding is the normal EPUB case.
- **Re-encoding the decoded text to UTF-8 bytes and feeding the bytes parser**: the parser would guess again on the
  new bytes, and injecting a meta charset means rewriting the document.
- **Letting lxml guess, with a UTF-8 meta tag injected first**: same objection, and it could mislead a chapter that
  declares another encoding.
