# MinerU reads through its cloud API when a key is set

**Date:** 2026-10-17
**Branch:** `worktree-mineru-api`

## What and why

Every PDF, Office file, HTML page and picture needed the local MinerU install
— about 3.4 GB — before the reader could open it. MinerU also runs as a cloud
service (`mineru.net/api/v4`), so a reader who puts a key in the settings can
have those files read there instead, with no install. With no key, nothing
changes: the same code paths as before, the local engine if it is installed.
If the API fails and the local engine is there, the file falls back to it.

This was asked for as "make MinerU use the API", with a key supplied for
testing. The key itself is a secret: it lives only in
`~/.textfold/settings.json` — outside the repository, git-ignored, beside the
reader's other settings — and appears nowhere in this change's diff, records
or logs (the one scratch script that held it was deleted).

## The change

- `textfold/engine.py` — the adapter, the bulk of the change:
  - `API_FILES` is what the API reads (PDFs, doc/docx/ppt/pptx/xls/xlsx,
    html/htm, and `API_PICTURES`: png/jpg/jpeg/jp2/webp/gif/bmp — not tiff,
    which the API does not take; the local engine still reads `.tif`).
  - `api_key()` reads `mineru_api_key` from the settings and rejects one with
    whitespace or unprintable characters before it can reach a log line.
  - `available()` / `readable(ext)` replace the old `where()` checks
    throughout: a file is readable if the engine is installed or the API key
    is set and the kind is one the API takes. `status()` gains `"api"`.
  - `convert()` sends those kinds to `_convert_api` first when a key is
    configured; on an exception it falls back to the local engine if one is
    installed, and otherwise raises the API's own error.
  - `_api_read`: `POST /file-urls/batch` → upload each file with a raw
    `http.client` PUT to the signed URL (urllib adds a Content-Type header,
    which breaks the signature — measured, 403), poll
    `/extract-results/batch/{id}` to `done`, download the zip. The download
    uses the system `curl` (Schannel) when present: the result CDN refuses
    Python's TLS handshake for every context tried (TLS 1.2/1.3, ALPN, no
    verification — all EOF) on this machine; urllib is the fallback.
  - `_api_wait` checks the deadline first each round and fails on a non-zero
    `code`; a PDF whose result has no text is read once more with OCR.
  - `_structured` writes the zip's `*_content_list_v2.json` (else the flat
    `*_content_list.json`, grouped by `page_idx` and normalized) into the same
    `structured_content.json` the local engine writes: pages of blocks, boxes
    0-1000 divided to 0-1, kinds mapped to what `pdfdoc.py` reads, the first
    page's first title as the document title, metadata `producer: MinerU API`.
    Everything downstream — `pdfdoc`, the store, the reader — is untouched.
  - Tiers: fast → `pipeline`, accurate → `vlm`.
- `textfold/models.py` — `mineru_api_key: ""` joins the settings defaults, so
  the server's `/api/settings` (which touches only `pdf_tier` and
  `use_thoughtdag_env`) cannot drop it.
- `textfold/server.py`, `textfold/__main__.py` — every "is the engine there"
  gate becomes `readable`/`available`; the needs-engine message offers the key
  only for the kinds the API reads; `engine status` prints "MinerU API key
  set" when one is configured. The CLI's own reader for Office files and PDFs
  with words in them keeps working exactly as before when only a key is set.
- `textfold/web/app.js`, `textfold/web/i18n.js` — the settings dialog's engine
  section shows a "MinerU API" row when a key is set and hides the install
  button; `engine_api` is in all twelve languages (zh-Hant in Traditional).
- **Encoding fixes found by the end-to-end run on this GBK Windows machine**,
  a necessary part of the feature because the cloud path stores documents
  whose text can contain characters GBK has none for (U+2212 in a formula
  crashed `store_pdf`):
  - `textfold/local.py` writes `source.html` and the raw source as UTF-8;
    `textfold/store.py` reads them as UTF-8 first and falls back to the
    system's encoding for pages stored before this change.
  - `textfold/engine.py`, `pdfdoc.py`, `pdftext.py`, `office.py` write
    `structured_content.json` / `layout.json` ASCII-escaped, since every
    existing reader reads them in the system's encoding; `meta.json` is
    deliberately left on the write-and-read-in-the-same-locale convention.
- `tests/test_engine_api.py` (new) — the zip's JSON stood in, no network: v2
  pages become engine blocks with 0-1 boxes and captions/LaTeX/HTML intact;
  the flat list is grouped by page and normalized; no document is an error;
  a page stored in the system's encoding still parses.
- `docs/DEVELOPMENT.md` — the engine paragraph now describes the API path,
  the coordinate and tier mapping, the OCR retry, that the document leaves
  this computer, and that RTF/OpenDocument still need the engine while
  EPUB/CSV keep TextFold's own reader. `CLAUDE.md` — 89 tests.

## How it was verified

- `python .claude/hooks/verify.py` — **89 tests, OK** (6.4 s).
- Real calls with the supplied key and the supplied PDF in `tests/`, three
  times end to end (the last after the verifier's fixes): create batch,
  upload, poll, download, adapt, `pdfdoc.store_pdf` — vlm tier **11.9 s**,
  11 pages, 215 blocks, 41 images, stored as `pdf-26103edc63843929` with
  `meta.json`, `structured_content.json`, `layout.json`, `source.html`,
  `source.md` and `img/`. Coordinates checked against the zip's
  `layout.json` page sizes and title boxes.
- `node --check textfold/web/app.js`, `node --check textfold/web/i18n.js`,
  `git diff --check` — clean.
- `git grep` for the key's prefix in the whole tree: no hits; the one probe
  script that held it (`out/api-probe/set_key.py`, git-ignored) was deleted.
- `textfold-verifier`: 13 findings. Eleven were fixed in code: the old-encoding
  page fallback, the CLI's Office/PDF-with-words regression, incomplete flat
  normalization, the key in a scratch script (file deleted), an invalid key
  reaching logs, a poll loop that could outlive its deadline, TIFF in the API
  picture list, the server's `take_file` gate, unmapped `aside_text`, a false
  EPUB claim in `docs/DEVELOPMENT.md`, and the bundled minors (`curl` without
  `--fail`, a repeated OCR pass for pictures). One was process — the untracked
  PDF and the new test file (the test file is committed, the PDF never was; the
  worktree copy was deleted). One behavior was kept deliberately and is
  recorded here: when a key is set with no local engine, an API failure
  surfaces the API's error rather than a needs-engine message — the honest
  report, since the key *is* the configured reader and the failure reason is
  what the user needs. The local engine's retention is this change's own
  design choice, not a verifier finding.

## Not measured

- **Smoothness: unmeasured.** This change touches `textfold/web/app.js` and
  `i18n.js` (one rendered row and string tables); `tools/zoombench.py` needs
  `playwright` and exported pages under `out/compare/`, neither installed
  here. This record does not claim the zoom is unaffected.
- **The settings dialog was not clicked in a browser.** The UI change was
  checked statically (`node --check`) and by the verifier, not by screenshot.
- **API failure paths** (quota, a revoked key, a server error) are handled as
  an exception with local fallback, but only the success path ran against the
  real service.
- **The local engine was not removed.** Whether to delete the 3.4 GB install
  path, its 12-language copy and `engine install` altogether is a follow-up
  decision, not part of this change.
