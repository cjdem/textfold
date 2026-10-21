# MyGo updates, its own payload, and the Electron shell removed

- Date: 2026-10-21.
- Mode: completion of the MyGo desktop migration in `codex/mineru-api-mygo-hybrid`.
- Decision: finish the release path the MyGo shell was missing, then remove
  `desktop/` rather than keep two shells.

## What changed

- `desktop-mygo/scripts/prepare-payload.mjs` now builds the payload itself,
  under `desktop-mygo/resources/payload`. It no longer calls
  `desktop/scripts/prepare-payload.mjs`, so removing the Electron shell does
  not break the MyGo build.
- The MyGo shell updates itself: `main.go` reads the one version in
  `mygo.json`, checks the signed feed shortly after launch and every four
  hours, and the Help menu has Check for Updates. `bridge.go` now implements
  the whole `window.desktop` update contract the page already used:
  `updateState`, `checkForUpdates`, `downloadUpdate`, `installUpdate`,
  `dismissUpdate`, and the `onUpdate` event. Progress, dismissal and the
  first launch after an update behave as they did in Electron.
- `mygo.json` names the update feed (`cjdem/textfold`) and the public key;
  the secret key stays outside the repository. `desktop.yml` reads it from
  the `MYGO_UPDATER_PRIVATE_KEY` secret and releases the installer, the
  signed manifest and the update archive together.
- The Electron shell in `desktop/` is removed, with its Node/Electron build
  tools and splash window.

## What is lost

- The Electron fallback itself. A copy installed before this change follows
  the old `latest.yml` feed and cannot install a MyGo build; it needs one
  manual uninstall and install. Later versions update themselves.
- The splash window: MyGo opens its window after the Python server answers
  `/api/models`, so a slow first start shows no window until then. A failed
  start shows the error page instead.
- The bundled Chromium: the app now uses the system WebView2 runtime. Windows
  11 includes it; a Windows 10 machine may need it installed first.
- The dormant macOS/Linux branches of the Electron shell. This fork builds
  Windows only (`dist:win` was its only target), so no shipped build is lost.

## Verification

- `go test ./...` and `go vet ./...` in `desktop-mygo`: passed, including
  new tests for update-state dismissal, the "updated from" note, and the
  version in `mygo.json` matching `textfold/__init__.py`.
- `python -m unittest discover tests`: 195 tests passed.
- `node --check` on the payload script and preload; `mygo.json` parses.
- `node desktop-mygo/scripts/prepare-payload.mjs` rebuilt the payload from
  the cached CPython archive and its published SHA-256, installed the
  packages, and passed its import check; `desktop-mygo/scripts/smoke.py` then
  served `/api/models` from that payload.
- `MYGO_UPDATER_PRIVATE_KEY=… go tool mygo build`: produced `TextFold.exe`,
  `TextFold Setup 0.10.7 amd64.exe`, `textfold-0.10.7-windows-amd64.tar.gz`
  and `update-windows-amd64.json`, whose URL, size and signature point at the
  fork's `v0.10.7` release. No delta was made: the build's lookup of an
  earlier manifest did not reach GitHub on this machine, and no earlier MyGo
  release exists.
- The packaged app started from a disposable `TEXTFOLD_DATA`, served
  `/api/models`, and left no Python process after it was closed.

## Not verified

- A signed update from one installed version to another end to end: the feed
  has no release yet, and this machine's TLS chain refused GitHub during the
  build's delta lookup.
- Installing an update while the bundled Python server is running. MyGo
  renames the running app's files aside and replaces them; the server is
  stopped only when the reader restarts. This is the main release risk left.
- A clean Windows 10 machine without WebView2.
- Zoom smoothness (`tools/zoombench.py`): not measured. The shell changed
  rendering engines, so it must not be reported as unaffected.

## Release setup

- The secret key is `%APPDATA%\mygo\update-keys\mygo-update.key` on this
  machine. Back it up, and add its contents as the
  `MYGO_UPDATER_PRIVATE_KEY` repository secret.
- The first MyGo release must be tagged `v0.10.7` (or a later version) and
  published from `cjdem/textfold`; the manifest and archive must be uploaded
  with the installer, or installed copies cannot update.
- The site and README download links still point at
  `chenxiachan/textfold`. They must move to the fork before its first
  release, or the download page keeps serving the old Electron build.
