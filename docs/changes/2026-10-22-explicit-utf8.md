# Every text read and write names UTF-8

**Date:** 2026-10-22
**Branch:** `worktree-explicit-utf8`

## What and why

On Windows, `Path.read_text()`, `Path.write_text()` and a text-mode subprocess default to the system's codepage —
GBK on a Chinese Windows — while TextFold's text is UTF-8. A title, a note, a translation or an imported Markdown
file holding a character outside that codepage then raises or comes back mangled, and an HTTP response announced
`charset=utf-8` while its bytes had been encoded with the codepage. This makes every text read and write name
UTF-8, gives the command line UTF-8 streams, and lets a Markdown file imported from the command line, saved in a
Chinese Windows's codepage, be read as GBK rather than as replacement characters.

## The change

- `store.py`, `cards.py`, `library.py`, `notes.py`, `pdf.py`, `pdfdoc.py`, `zotero.py`, `server.py`, `fetch.py`,
  `office.py`, `local.py` — every `read_text()` / `write_text()` names `encoding="utf-8"`.
- `server.py` — the response body is encoded with `body.encode("utf-8")` explicitly.
- `local.py` — `_read()` decodes an imported file as UTF-8 (BOM stripped), then GBK (a Chinese Windows's codepage),
  then UTF-8 with stand-ins, and normalizes line ends as `Path.read_text` did; `import_file()` uses it. A GBK-saved
  Markdown file no longer imports as replacement characters; a UTF-8 file with CRLF keeps its id on re-import (a GBK
  file the old command line imported as replacement text gets a new id, because its text is now different).
- `library.py`, `zotero.py` — a UTF-8 decode failure is re-raised instead of being read as an empty file, so this
  change cannot save an empty library or Zotero index over an older codepage's file before R3 migrates it.
- `engine.py` — the curl result reader names `encoding="utf-8", errors="replace"`.
- `__main__.py` — `_utf8_streams()` reconfigures stdout and stderr to UTF-8 with replacement, so a redirected
  Chinese title does not raise on a GBK console. `adr/__main__.py`'s stderr and `.claude/hooks/verify.py`'s test pipe
  name UTF-8 too.
- tests — the test fixtures' own reads and writes name UTF-8; a new test imports a GBK-saved Markdown file and a
  UTF-8 BOM file and checks the stored title.

## Docs checked

- `docs/DEVELOPMENT.md` — updated: the text-encoding paragraph now says every read and write names UTF-8, the import
  fallback, and the command line's streams.
- `README.md`, `README.zh-CN.md` — not needed: no user-facing promise changes; the app's behaviour is the same on a
  UTF-8 file and now correct on a GBK console.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: they do not state an encoding,
  and the JSON bytes do not change.
- `site/` — not needed: the site does no text I/O in the product.
- `pyproject.toml`, `requirements.txt` — not needed: no dependency or platform change.
- `NOTICE`, `LICENSE`, `SECURITY.md` — not needed.
- `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md` — not needed: formats unchanged.
- `desktop-mygo/README.md`, `.claude/agents/` — not needed: MyGo already starts the server with `PYTHONUTF8=1`, and
  the agent prompts do not describe file I/O.

## Decisions

- Every file TextFold writes is UTF-8; a file from an older TextFold that was written in the system's codepage is
  **not** read in R2. Migrating those once is R3, the next change, exactly as the round document orders it.
- An imported Markdown file is different: it is the reader's own file, not TextFold's, so it falls back to GBK before
  the replacement decode.
- The ASCII-escaped JSON stays ASCII-escaped. It is no longer needed to survive a codepage, but it keeps the files
  readable by any tool and the existing tests pin it.
- The UTF-8 fallback is only for reading; nothing is rewritten in place here.
- A file that cannot be decoded as UTF-8 is an error, not an empty library: `library.load()` and `zotero.links()`
  re-raise the decode error, so nothing writes an empty file over it before R3 migrates it.

## Concurrency and locks

No shared state is added. The settings writer (`models._SETTINGS_LOCK` plus the atomic replace) and the store's
per-document lock are unchanged; the new code only names an encoding. No file's contents change on disk except when
the app writes it as it already did.

## How it was verified

- `python .claude/hooks/verify.py` — 214 tests, OK (baseline 211; 3 added).
- `grep` over `textfold/` and `tests/` — every `read_text`/`write_text` names an encoding (the four hits are the
  first lines of calls whose `encoding=` is on the next line), and every `text=True` pipe names one.
- Real data: `store.papers()` over `D:\Code\textfold\papers` lists the remaining paper and its title under strict
  UTF-8.
- New tests: a GBK-saved Markdown file and a UTF-8 BOM file import with their Chinese title; a CRLF file's text is
  normalized as `Path.read_text` did; a GBK `library.json` and `zotero.json` raise instead of being read as empty,
  and their bytes are unchanged after the failed read, stamp and open.
- `textfold-verifier` — did not break the core claim. It found that a GBK `library.json` / `zotero.json` would read
  as empty and then be saved over (fixed: the decode error is re-raised, with tests that check the bytes are
  unchanged), that the browser's dropped-file path decodes UTF-8 before POSTing (the DEVELOPMENT and record wording
  is scoped to the command-line import), that `_read` did not normalize line ends as `Path.read_text` did (fixed; a
  re-import keeps its id), and that the DEVELOPMENT sentence was too broad for external HTML/SVG/Office text
  (scoped). It also noted that the write-side encodings are unobservable while the JSON stays ASCII-escaped.

## Measured

| | before | after |
|---|---|---|
| tests | 211 | 214 |

## Not measured

- CLI output on a GBK console was not inspected by eye. The streams are reconfigured to UTF-8 with replacement, so
  a character outside the console's font cannot raise; the console's own rendering is outside this change.
- Write-side encodings: every JSON this change writes is ASCII-escaped, so a wrong encoding argument would produce
  the same bytes today, and the unchanged read-side encodings are unobservable for the same reason. The tests pin the
  guard reads, the import fallback and the data-loss guards; the server's UTF-8 response body and the curl pipe's
  encoding are not exercised with non-ASCII content. The encoding is explicit for the next non-ASCII write.
- No performance measurement: the change adds an explicit codec name, not a new pass over the data.

## Pitfalls

- Strict UTF-8 reads mean an old file written in the system's codepage now raises until R3 migrates it. One
  pre-existing paper's `meta.json` was GBK and could not be read as UTF-8; at the requester's instruction it was
  moved to `papers/.trash` before this change and will be re-imported. It is not part of the commit.
- `Path.write_text()` without an encoding is not merely a lint: on a GBK Windows it fails on a character GBK lacks
  (the ✩ after an Elsevier title) and silently writes cp936 otherwise. The ASCII-escaped JSON avoided the first
  case; the explicit encoding closes both.
- A text-mode subprocess (`engine.py`'s curl) decodes its stderr with the codepage unless told otherwise; the pipe
  now says UTF-8 with replacement.
- The CLI's `sys.stdout` was already reconfigured; `sys.stderr` was not, and neither used `errors="replace"`.
- A Markdown file dropped on the landing page is decoded by the browser (`File.text()`, UTF-8) before the POST; the
  GBK fallback applies to `python -m textfold <file>`, not to the drop zone.
- A GBK file whose bytes also happen to be valid UTF-8 is read as UTF-8 (`D2 BB`, "一", is U+04BB); no marker tells
  them apart. R3's migration has the same limit.
- `Path.write_text` writes `\n` as `\r\n` on Windows; `_read` normalizes on the way in, so ids stay stable.

## Rejected

- A UTF-8-then-codepage read fallback in R2 — that is R3's migration; the one file that would have needed it was
  removed at the requester's request.
- `errors="replace"` on TextFold's own files — it would hide a corrupt file instead of failing, and R3's migration
  needs the distinction between UTF-8, the codepage, and neither.
- Reading a decode failure as an empty library, as the old `except ValueError` did — it silently erased folders and
  Zotero links the moment anything saved.
- Changing `ensure_ascii` — it is a separate storage decision, and the existing tests pin the ASCII-escaped form.
