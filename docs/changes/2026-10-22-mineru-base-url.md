# MinerU's API address is a setting, official by default and v4-only

**Date:** 2026-10-22
**Branch:** `worktree-mineru-base-url`

## What and why

`engine.API` was one hardcoded string: every PDF and picture went to `https://mineru.net/api/v4`. A reader with a
v4-compatible gateway (a proxy, a team endpoint, a local service) had to edit the code. This change makes the address a
setting, `mineru_api_url`, official by default, saved through the existing `/api/settings` and shown in Settings ›
Advanced with a URL field and "Restore official address". Only v4-compatible endpoints are supported; the self-hosted
`mineru-kit` API is v1 and is R12, not this change.

## The change

- `textfold/models.py` — `MINERU_API = "https://mineru.net/api/v4"` (the one literal) and the settings default
  `"mineru_api_url": MINERU_API`. The key must be in the default dict: `_load_settings_locked` keeps only known keys, so
  without it a saved address would be dropped by the next unrelated settings save.
- `textfold/engine.py` — `base_ok(url)` accepts http/https with a host and no query, fragment, sign-in or whitespace,
  and returns the address with its trailing `/` stripped; `api_base()` reads the setting and returns the official base
  when it is absent or empty, and raises `bad-mineru-url` for a saved value that cannot be called (it does not fall
  back: that would send the file to mineru.net when the reader meant another host); `status()` never raises and reports
  `base`, `official` and `baseOk`; `_api` uses the base, and `convert` resolves it once and passes it through
  `_convert_api`/`_api_read`/`_api_wait`, so a save during a conversion cannot redirect its polls. `_put` now follows
  the signed URL's scheme and port (`HTTPConnection` for an http gateway, an explicit port), where it always used
  `HTTPSConnection` on 443.
- `textfold/server.py` — `/api/settings` accepts `mineru_api_url`, normalizes it, refuses an unusable non-empty value
  with 400 `bad-mineru-url` before writing anything, and stores the official base for an empty value. The route
  docstring lists the field.
- `textfold/__main__.py` — `textfold mineru status` prints the address and marks an invalid one.
- `textfold/web/app.js` — the MinerU section has a URL input bound to `mineru.base`, its own Save, and "Restore official
  address" when the saved base differs from `mineru.official`; a rejected save shows the message on that input and
  leaves the stored value. The status line says when the saved address is invalid, and the privacy/connected strings no
  longer promise mineru.net specifically. `errText` maps `bad-mineru-url`.
- `textfold/web/i18n.js` — the address strings in English and Simplified Chinese.
- `textfold/web/app.css` — the URL input shares the key row's width rule.
- `tests/test_engine_api.py` — the status shape test now pins `base`, `official` and `baseOk`; new tests for the
  validation table, the setting/default/normalization, the request URL and Authorization header a call uses, the
  pre-socket failure of an invalid saved value, one base per conversion, and `_put`'s scheme and port.
- `tests/test_mineru_settings.py` — `/api/settings` on a server of its own: official default, a custom address saved
  normalized, an invalid address refused with the old one kept, and an empty address restoring the official one.
- `tests/test_agent_encoding.py` — the concurrent settings test now has three writers (tier, Zotero library, MinerU
  address) and checks all three survive.

## Docs checked

- `README.md`, `README.zh-CN.md` — updated: the API address can be changed for a v4-compatible service, official by
  default, and files and the key go to the address set.
- `docs/DEVELOPMENT.md` — updated: the settings list, and the PDF section (the base, its validation, the refusal of an
  unusable saved value, one base per conversion, v4-only, and that the document leaves for the address in the setting).
- `SECURITY.md` — updated: files go to the MinerU API address in Settings, official by default.
- `site/` — not needed: it names MinerU's Cloud API as the service; no endpoint string, and the default is unchanged.
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — not needed: no stored document format
  changes.
- `desktop-mygo/` — not needed: the payload copies `textfold/` when it is built; no shell change.
- `docs/upstream/2026-10-22.md` — not changed: the review is the source for this round, not current behaviour.
- `docs/requirements/mineru-api-mygo-shell.md` — a one-line later-change note added (the address is now the setting;
  the rest of that implemented requirement describes the state before it), so it no longer reads as the current rule.
- `pyproject.toml`, `requirements.txt` — no dependency change.

## Decisions

- **Absent/empty is official; anything else that cannot be called is refused, not replaced.** A typo must not silently
  send a paper (and the key) to mineru.net. `api_base()` raises `bad-mineru-url` before a socket; the settings page and
  the CLI show the stored value and that it is invalid, so it can be fixed. This includes a hand-edited non-text value
  and text UTF-8 cannot encode: the saved address is not treated as empty, and `status()` reports it with only the
  unencodable characters replaced, so the page that fixes it still opens. A stored JSON `null` counts as absent (the
  file's way of saying no value); a request that sends `null` is refused like any other non-text value. `status()` is
  deliberately total (never raises) because it feeds that page.
- **Validation at the boundary, normalization in one place.** `engine.base_ok` is the single rule (http/https, a host,
  no query, fragment, sign-in or whitespace, trailing `/` stripped); the server rejects a bad save with it, and the
  engine uses it at read time. The path is the reader's business (a proxy may add one); only v4 is claimed.
- **One base per conversion.** `convert` resolves the base once; every creation, poll and the OCR second pass use it.
  Without this, a settings save mid-job would send the next poll for an old batch id to another host and could hold the
  single conversion queue until its 30-minute deadline.
- **The signed upload URL's own scheme and port are honoured.** An accepted `http://` base is honest only if the upload
  can reach the signed URL it returns; the previous `HTTPSConnection` ignored both scheme and port. The official
  service is unchanged (https, 443), and the upload still carries no key.
- **The key check stays key-only.** `available()`/`readable()` do not consult the address, so a bad URL with a key still
  gets a job, and that job fails with the address message. The alternative (report `needs-mineru-key`) would be wrong.
- **The official literal lives in `models.py`.** `status()` reports it as `official`, so the page's Restore button needs
  no second copy in JavaScript; the CLI and tests use the same constant.

## Concurrency and locks

`settings.json` is still written only by `models._write_settings_locked`, under `_SETTINGS_LOCK`, through a temp file
and `os.replace`; the new key adds no writer. `/api/settings` uses `update_settings`, so a save of the address and a
save of another field from two requests keep both (the concurrent test now covers the address, the tier and the Zotero
library). A conversion reads the base once at its start, so a save while it runs affects the next conversion, not the
running one. The document, card, notes and trash paths are untouched by this change.

## How it was verified

- `python .claude/hooks/verify.py` — 299 tests, OK (baseline 284; the status test extended, 15 new tests and one
  concurrent test extended).
- `node --check` on `textfold/web/app.js` and `textfold/web/i18n.js`; `git diff --check` clean.
- UTF-8: the settings writer is unchanged and still writes ASCII-escaped JSON (the existing settings-name test
  passes); the new interface strings are UTF-8 in `i18n.js`, and even a hand-edited lone surrogate is replaced in the
  status payload so it still encodes. No document text passes through this change.
- In the browser against the worktree server with a disposable library and settings home, `TEXTFOLD_NO_MODELS=1` and a
  disposable key (no model or MinerU call):
  - Settings › Advanced showed the official address in the field, no Restore button, and the new privacy line.
  - `ftp://x` was refused: the field showed the localized message, and `/api/settings` still had the official base.
  - `http://127.0.0.1:9/api/v4/` was saved as `http://127.0.0.1:9/api/v4`, the Restore button appeared, and the status
    line still said no key.
  - a disposable key made the status line say the key was saved and that files are read at the address below; the
    custom address stayed; Restore returned the official address and removed the button; closing and reopening settings
    showed the saved custom address (and later the restored official one).
  - hand-editing the settings file to `ftp://proxy.example` made the status line say the address is invalid (red dot),
    the field showed the value, and Restore was offered; `textfold mineru status` printed the address and the invalid
    note; dropping a PDF then made a conversion job that failed with the localized address message and left no socket
    call (the job's error was `bad-mineru-url`).
- `textfold-verifier` — one pass, no blocking. It confirmed the normal paths (official default, a custom base used by
  the whole conversion, invalid refused at save and at conversion, empty restoring official, `status()` surviving a
  hand-edited `ftp://` value, `_put` scheme/port with no key) and found: a lone-surrogate hand edit made the settings
  JSON fail to encode (fixed: `status()` replaces unencodable characters); a non-text saved value (42, a list, an
  object) was treated as empty and a non-text save as a reset (fixed: both refused, and `status()` reports the value
  invalid; a stored null is the documented "no value" exception); the record called the settings dot green for an
  invalid address (fixed: it is red and the page says so); `mineru-api-mygo-shell.md` still
  read as the current address rule (fixed: a later-change note); the test count said 10 new where it was 11 (now 15);
  the per-conversion test did not cover the poll (fixed: `_api_wait` passes its base to `_api`, now tested); and
  `https://@host` was accepted (fixed: any sign-in delimiter, even empty, is refused). A narrow re-check confirmed all
  seven fixes; it found the record's null wording still contradicted the code (fixed: a stored null is the one
  documented "no value" exception) and that a hand-edited surrogate at the end of a path could be shown as `?` and
  saved as a truncated address (fixed: `base_ok` refuses a raw `?` or `#` even when empty, so the shown value is not
  savable).

## Measured

| | before | after |
|---|---|---|
| Python tests | 284 | 299 |

## Not measured

- **No real custom v4 gateway.** The suite proves the request URL, the Authorization header, one base per conversion
  and `_put`'s scheme/port by mocking; the browser check used an address that was never called. A real proxy's signed
  upload and result URLs, and a real custom endpoint's error shapes, were not exercised.
- **The settings UI has no automated test.** The repository has no JavaScript test runner; the browser steps above are
  manual. The route behind it is tested.
- **Zoom smoothness: unmeasured.** The change is in the settings dialog (`app.js`), not `reader.js`; no
  `tools/zoombench.py` run was made (it needs `playwright` and exported comparison pages, neither installed here), so
  the zoom axis is not reported as unaffected.
- **The desktop payload was not rebuilt.** An installed app keeps the old code (and the old fixed address) until its
  payload is built again; no build was run here.

## Pitfalls

- The key must stay in `models._load_settings_locked`'s default dict. If it is removed, `merging` keeps only known keys
  and the next settings save from any route silently drops the address.
- `status()` must not call `api_base()`: a hand-edited invalid address would make `/api/models` fail and the settings
  dialog that fixes it could not open.
- A conversion resolves its base at the start. A settings save during a conversion applies to the next one; a typo fixed
  mid-job does not rescue the running job (retry it).
- `_put` now uses the signed URL's scheme and port. A gateway that signs a URL on an unexpected host will get the file
  (without the key); that is the service's URL, not the base's.
- An `http://` base sends the file, and the key on API calls, in clear text. The note says to use https off this
  computer; a local proxy is the intended case.
- `available()` and `readable()` do not look at the address: in a conversion, the first sign of a bad saved address is
  the job's `bad-mineru-url`. The settings page does show it: a red dot and the invalid-address line, with the value in
  the field and Restore offered.
- A hand-edited value that is not text (except a stored null, which means no value), or text UTF-8 cannot encode (a
  lone surrogate), is reported as invalid rather than taken as empty: `api_base()` refuses it, and `status()` replaces
  only the unencodable characters so the settings page's JSON still encodes and the page opens. `base_ok` refuses a raw
  `?` or `#` even with an empty query, so saving the shown value cannot silently truncate a path. Replace it or restore
  the official address.
- The address is a base, not an endpoint: `.../file-urls/batch` is appended. A full endpoint URL will not work, and the
  note says so.
- Only v4-compatible services work. A `mineru-kit` v1 server is not supported by this setting (R12).

## Rejected

- **Falling back to the official base when the saved one is invalid.** It would hide a typo and could send a document
  to mineru.net when the reader meant another host.
- **A "test connection" button.** It would make a server-side request from a settings page; the job's own error is the
  first real test, and R11 did not ask for a probe.
- **The v1 self-hosted adapter, multipart uploads or `mineru_api_mode`.** That is R12; this change must not imply that
  changing the URL reaches a `mineru-kit` server.
- **Storing the base per paper, or which base converted a paper.** Not needed to read or regenerate; the setting is the
  one used for the next conversion.
- **Making `available()` depend on the address.** It would turn an address problem into a "needs a key" message.
- **Replacing `_put` with urllib.** It was tried before: urllib adds a Content-Type and breaks the signed upload.
