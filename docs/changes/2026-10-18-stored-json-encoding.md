# A title GBK lacks no longer fails the upload: stored JSON is ASCII-escaped

**Date:** 2026-10-18
**Branch:** `worktree-stored-json-encoding` (at `a6c7a62`)

## What and why

Uploading a PDF whose title ends in ✩ failed after MinerU had read the whole document:
`pdfdoc.store_pdf` → `local.store_doc` wrote `meta.json` with `ensure_ascii=False`, and the system's GBK encoding
raised `UnicodeEncodeError: 'gbk' codec can't encode character '✩'`. The same pattern was in the other JSON the
reader stores about a document or its library, and the exported page was written in the system's encoding while its
markup declares UTF-8.

## The change

- `textfold/local.py` — `meta.json` is ASCII-escaped (`json.dumps(meta, indent=2)`), like layers and notes.
- `textfold/fetch.py` — an arXiv page's `meta.json`, same.
- `textfold/library.py` — `library.json`, whose folder names the reader writes, same.
- `textfold/zotero.py` — `zotero.json` and the `meta.json` `apply` rewrites, same.
- `textfold/server.py` — the name kept beside a file waiting for the engine, same.
- `textfold/webpage.py`, `textfold/store.py` — a web page's `url.txt` is written UTF-8 with a byte-order mark;
  `store.read_url` reads a marked file as UTF-8 and an unmarked one (stored before the mark) in the system's encoding,
  so an old address whose GBK bytes happen to be valid UTF-8 is not silently read as another address.
- `textfold/build.py` — `export` writes the page UTF-8; `data_uri` reads an SVG by an ASCII-compatible XML
  declaration naming a codec Python knows, else UTF-8 (XML's default), else the system's encoding. The old read used
  the system encoding and turned UTF-8 Chinese into replacement characters; assuming UTF-8 would have broken an SVG
  that declares GBK. An unknown codec name and `<?xml-stylesheet` are not mistaken for the declaration.
- `textfold/server.py` — the PDF.js asset reads in `/api/export?pdf` are UTF-8, like the files (the old read raised
  `UnicodeDecodeError` on this machine).
- `textfold/__main__.py` — `textfold get` writes its stdout as UTF-8; redirected to a file on a GBK machine it used to
  raise on the first ✩ in a title.
- `docs/DEVELOPMENT.md` — the encoding paragraph now covers stored JSON, `url.txt`, the exported page and the CLI.
- `tests/test_stored_text.py` — twelve tests: a PDF title with ✩, a folder name, a Zotero title in the index and the
  document, a fresh web address, an address stored before the mark, an arXiv title, the engine-waiting sidecar, a
  UTF-8 SVG, a GBK-declaring SVG, an SVG with an unknown declared encoding, an XML-stylesheet instruction, and an
  exported page. **201 tests.**

## Decisions

- **ASCII-escape instead of moving `meta.json` to UTF-8.** Every reader opens these files with `read_text()` and the
  system's encoding; the one existing metadata file on this machine is GBK (the `·` in its label is a GBK byte, not
  UTF-8; `library.json` here is ASCII and there is no `zotero.json`). Moving the writes to UTF-8 without migrating
  every read would break documents that already exist. ASCII is valid under every encoding, and old GBK JSON still
  reads as before; only new files change.
- **The exported page is UTF-8, not ASCII-escaped.** It is HTML, not stored JSON: it declares `charset="utf-8"`, and
  writing GBK bytes into it would mojibake Chinese even when GBK can encode every character.
- **`url.txt` is UTF-8 with a byte-order mark.** A URL is plain text, so it cannot be ASCII-escaped. The mark tells
  `store.read_url` that a file is UTF-8; an unmarked file is read in the system's encoding, because trying UTF-8 first
  would silently turn some old GBK addresses into different ones (`一` is `D2 BB`, which is valid UTF-8 too).

## Rejected

- Writing with `errors="replace"`: the title would store a `?` where the ✩ is.
- Moving every stored JSON to UTF-8 and adding a fallback to every read: a larger change with more places to miss;
  ASCII-escaped is already the rule for layers, notes, cards, settings and the reply cache.
- Leaving `url.txt` and the export alone: uploading a page whose address or title holds a GBK-unencodable character
  fails the same way, and an export with Chinese was already being written in GBK.

## What is lost

No data is deleted or rewritten. `meta.json`, `library.json`, `zotero.json` and the pending sidecar are less readable
in a text editor for non-ASCII text (it appears as `\uXXXX`), which is the existing convention for stored caches; old
JSON files keep their bytes and still read under the unchanged reads, and an old `url.txt` is read in the system's
encoding, not guessed as UTF-8. One behaviour changes: an SVG with no declaration, saved in the system's encoding, and
whose bytes are also valid UTF-8 is now read as UTF-8 (XML's default) rather than in the system's encoding. No marker
distinguishes the two; a GBK-saving program declares its encoding, which is read correctly.

## How it was verified

- The failing title from the uploaded PDF (`…genetic optimization algorithm ✩`) reproduced the old error at
  `local.py:136`; after the change `store_doc` writes a 517-byte ASCII `meta.json` and the title round-trips.
- A server started from this worktree on port 3118 with a temporary data folder: `POST /api/import` of
  `中文 ✩.md` returned the title, the reader page carried `中文标题 ✩`, and its 302-byte `meta.json` was ASCII and
  round-tripped. (Data folder removed afterwards.)
- The failing PDF itself, re-uploaded through the running server after the change: MinerU converted it, its
  `meta.json` is 663 bytes of ASCII, the title round-trips with the ✩, and the reader page (259,432 characters)
  carries it.
- `textfold get --json` on a Markdown whose title is `中文标题 ✩`, stdout redirected to a file: exit 0, the output
  decodes as UTF-8, and the title round-trips.
- `python .claude/hooks/verify.py` — **201 tests, OK** (12 new); `git diff --check` clean.
- No reader UI changed, so no browser check; the server and storage paths above were exercised instead.
- Zoom smoothness was **not measured** (no `playwright`, no `out/compare/` pages), and no claim is made.

## Not measured

- The one old GBK `meta.json` on this machine was read, not rewritten; no old `library.json` with non-ASCII, no
  `zotero.json` and no `url.txt` exist here. Of those old-file paths only the unmarked `url.txt` read has a test;
  the unchanged reads of old GBK `library.json` and `zotero.json` were checked by hand, not added to the suite.
- A real web page whose URL holds ✩ was not fetched; only `url.txt`'s write and read were tested.
- The `/api/export?pdf` path that reads the PDF.js assets was not run end to end (it needs a stored source PDF); the
  asset reads themselves are plain UTF-8 reads of vendored `.mjs` files.
