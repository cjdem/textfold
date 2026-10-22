# MinerU API-only and the MyGo desktop shell

- Status: implemented and built for Windows 2026-10-21; signed-release
  migration remains open.
- Later change (2026-10-22): the base is the `mineru_api_url` setting, official
  `https://mineru.net/api/v4` by default and v4-compatible only; item 2 below
  describes the state before that setting. See
  `docs/changes/2026-10-22-mineru-base-url.md`.
- Goal: remove every local MinerU engine install and execution path, use MinerU's
  Cloud API for the conversions that need MinerU, and make MyGo the Windows
  desktop shell around the existing Python server.
- This is deliberately a hybrid migration. MyGo owns the window, process
  lifecycle, desktop dialogs and update hooks. Python keeps the reader, the
  document model, the local parsers and the local HTTP API.

## What stays

1. PDFium (through pypdfium2) cuts figures from a PDF's pages after MinerU has
   supplied the block geometry; it does not read the PDF's words.
2. `textfold/office.py` reads DOCX, PPTX, XLSX, EPUB, CSV, TSV, HTML and MHTML
   locally.
3. Existing papers and generated levels stay readable. Nothing under the data
   folder is deleted by this change.
4. The browser-served app and `python -m textfold serve` still work.

## What changes

1. No path may install, locate or run a local MinerU/mineru-kit process.
2. Scanned PDFs and MinerU-only formats use `mineru_api_key` and
   `mineru.net/api/v4` only. API failure is reported; there is no local MinerU
   fallback.
3. Every new PDF goes directly to MinerU's Cloud API. There is no local PDF
   text extraction and no fallback. A text PDF and a scan follow the same
   route. `pdftext.py` and the pdf-inspector dependency are removed.
4. Settings expose the MinerU API key, whether it is configured, and the
   conversion tier. The key is never returned to the page.
5. The desktop app becomes a Go/MyGo process that starts the bundled Python
   server on a random loopback port and shows it in WebView2.
6. The page-side `window.desktop` contract stays: external links, save-file
   dialog, version, update state/check/download/install/dismiss.
7. The bundled app keeps using `%LOCALAPPDATA%\TextFold` for reader data and
   `~/.textfold` for settings, shared with the command-line server.

## Format boundary

- MinerU API supports PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX, HTML, PNG, JPEG, JP2,
  WebP, GIF and BMP.
- TextFold itself keeps EPUB, CSV/TSV, MHTML and the common Office formats.
- New OFD and TIFF imports are refused once the local engine is gone.
- New RTF, OpenDocument and old Office imports remain refused.
- Stored old-format documents remain readable. Re-conversion through the
  removed local engine is no longer offered.

## States and failure paths

| State | Result |
|---|---|
| No MinerU key, PDF or image | `needs-mineru-key`, nothing queued |
| API key set, PDF or image | queue a MinerU conversion |
| API key set, Office/EPUB/CSV/HTML | TextFold reads the common kinds locally |
| API refuses, times out or has no quota | conversion job fails with the API message; no local fallback |
| Unsupported kind | `not-supported`; no file left waiting in `uploads/` |
| MyGo cannot start Python | window shows the server log path and a readable error |
| MyGo quits or updates | Python child is terminated before the app exits |

## Shared writers

- Settings still have one writer at a time through `models.save_settings()`.
- Conversion jobs still run one at a time on the conversion queue; generation
  remains on its separate queue.
- The MyGo shell starts exactly one Python server. A second app instance focuses
  the first rather than starting another server.

## Acceptance

- [test] No production import or command path calls a local MinerU install or
  `mineru-kit`.
- [test] Every PDF route reaches MinerU, including one with its own text; no
  code path calls pdftext or pdf-inspector.
- [test] A scanned PDF without a key returns `needs-mineru-key` and creates no
  pending upload.
- [test] API output still becomes the same `structured_content.json` consumed by
  `pdfdoc.py`.
- [test] Saving a MinerU key never returns the secret in `/api/models` or
  `/api/settings`.
- [test] The MyGo server locator uses repository code in development and the
  packaged payload in a build.
- [test] The desktop bridge validates save-file extensions and external URLs.
- [test] MyGo starts one server, waits for `/api/models`, and terminates the
  child on quit.
- [manual] The packaged Windows app opens, imports Markdown, opens a PDF beside
  its text, opens an external link, saves a Markdown export and exits without an
  orphan Python process.
- [unmeasured] Zoom smoothness; this change does not touch the reader's
  animation code and Playwright comparison pages are not available here.

## Not in this change

- Rewriting the Python backend in Go.
- Moving papers, notes or generated layers to a new format.
- Publishing signed MyGo updates. The desktop code exposes the update
  contract, but a MyGo update key and release manifest are release work.
