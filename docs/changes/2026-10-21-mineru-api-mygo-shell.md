# MinerU API only, with a MyGo desktop shell

- Date: 2026-10-21.
- Mode: feature migration in `codex/mineru-api-mygo-hybrid`.
- Decision: keep the Python backend and replace only the Electron desktop
  shell with MyGo. A full Go rewrite is not justified now.

## What changed

- Every new PDF goes directly to MinerU Cloud API. The browser no longer reads
  a PDF's text to find arXiv ids or DOIs, the server no longer prefers an
  online paper named by `X-Refs`, and Zotero reads a stored file before an
  item's arXiv or DOI reference.
- `textfold/pdftext.py`, pdf-inspector and every local MinerU/mineru-kit
  install or execution path were removed. `pypdfium2` remains only to crop
  figures from MinerU's page boxes.
- PDFs and pictures without a MinerU key return `needs-mineru-key` and leave
  no pending upload. Settings can save, clear and validate the key without
  returning it to the page.
- Office, EPUB, CSV/TSV, HTML and MHTML continue through `office.py` on the
  computer.
- New OFD and TIFF imports are refused. Existing documents and generated
  layers are not deleted.
- `desktop-mygo/` starts one bundled Python server on a random loopback port,
  loads it in WebView2, exposes the existing `window.desktop` contract, and
  keeps `TEXTFOLD_DATA` at `%LOCALAPPDATA%\TextFold`.
- A Windows Job Object and explicit process-tree termination prevent orphan
  Python processes when the shell exits or crashes.
- The existing Electron shell remains in `desktop/` as a fallback until the
  MyGo build and release path have been exercised on a clean machine.

## What is lost

- Offline PDF conversion.
- Local MinerU fallback when the Cloud API is down, rate-limited or lacks a
  key.
- Local text extraction from PDFs, including the old "read this PDF without
  the engine" path.
- New OFD and TIFF imports.
- Re-conversion of stored old-format documents through a local MinerU engine.

## Verification

- `D:\Code\textfold\.venv\Scripts\python.exe -m unittest discover tests -v`:
  195 tests passed.
- `go test ./...` and `go vet ./...` in `desktop-mygo`: passed.
- The MyGo development app opened a `TextFold` window, loaded the local server,
  and `/api/models` returned the expected catalog.
- The Windows payload was built from CPython
  `3.12.15+20261020-x86_64-pc-windows-msvc-install_only_stripped` and
  verified against its published SHA-256. Its bundled Python served
  `/api/models`.
- `go tool mygo build` produced `TextFold.exe` and a 32.8 MB
  `TextFold Setup 0.10.7 amd64.exe`.
- The packaged app started `payload/python/python.exe`, opened a `TextFold`
  window, and answered `/api/models`. Closing the window normally left no
  Python process behind.
- Forced shell termination also left no `python -m textfold serve` process.
- Zoom smoothness was not measured; no reader animation code changed.

## Release risk

The old Electron `electron-updater/latest.yml` protocol is not compatible with
MyGo's signed update manifests. Existing users need either a transition build
through the old updater or a documented reinstall before MyGo can become the
next release. MyGo update signing is intentionally left to release work.
