# TextFold's MyGo shell

This is the hybrid desktop migration: MyGo owns the window, the Python process
and desktop dialogs; the Python package remains the application. It does not
rewrite the reader or document pipeline in Go.

## Development

From this folder:

```powershell
$env:Path = "E:\Go\bin;$env:USERPROFILE\.bun\bin;$env:Path"
go run .
```

The locator uses `TEXTFOLD_PYTHON` first, then `.venv` in this checkout, then
the main checkout of a linked worktree, and finally `python.exe` on PATH.
Override it when the virtual environment lives elsewhere:

```powershell
$env:TEXTFOLD_PYTHON = "D:\Code\textfold\.venv\Scripts\python.exe"
go run .
```

Set `TEXTFOLD_DATA` for a disposable test library. It defaults to
`%LOCALAPPDATA%\TextFold`, the same folder as the Python server.

## Payload and build

The packaged app needs a standalone CPython, TextFold's packages and the
Anthropic API's SDK:

```powershell
node scripts/prepare-payload.mjs
go tool mygo build
```

`prepare-payload.mjs` writes `resources/payload/{python,app}`. The SDK is
installed into the payload even though `requirements.txt` leaves it optional:
the Settings offer the Anthropic API, and an installed app has no way to run
pip. The MyGo build output is under `build/`.
If GitHub's API is unreachable, pass a downloaded python-build-standalone
archive and its published digest:

```powershell
$env:PBS_FILE = "$env:TEMP\cpython-...-install_only_stripped.tar.gz"
$env:PBS_SHA256 = "<published sha256>"
node scripts/prepare-payload.mjs
```

## Updates

The app checks `https://github.com/cjdem/textfold/releases/latest` shortly
after launch and every four hours. A newer signed release shows as a note at
the bottom right of the page; nothing downloads until the reader asks, and the
new version starts when they restart. The installed copy sits in
`%LOCALAPPDATA%\Programs\TextFold`, which the current user can write, so it
updates itself without administrator rights. The release notes are
`docs/releases/v<version>.md`: the tag build publishes that file as the release
body, and the note's link opens that release.

The public key is in `mygo.json`; the secret key is **not** in the repository.
`go tool mygo keygen` wrote this machine's pair to
`%APPDATA%\mygo\update-keys\mygo-update.key` (secret) and `mygo-update.pub`
(public). Back the secret up: installed apps accept only updates signed with
it, so losing it strands them. A release build needs it in
`MYGO_UPDATER_PRIVATE_KEY`; the workflow reads it from the
`MYGO_UPDATER_PRIVATE_KEY` repository secret.

`go tool mygo build` writes the installer, the update archive and the signed
manifest under `build/windows-amd64/`. A tag build uploads all of them to the
draft release; the installer is also copied to the stable
`TextFold-win-x64-setup.exe` name the download page uses. Without the secret,
the build still makes the app and the installer, but no update files.

The Electron shell that came before is gone. A copy installed before this
change follows the old `latest.yml` feed and cannot install a MyGo build; those
readers need to uninstall and install this version once. After that, updates
work as above.

## Boundaries

- `resources/payload/` and `build/` are generated and ignored.
- The WebView trusts only the exact dynamic `http://127.0.0.1:<port>` origin.
- `preload.js` restores the old `window.desktop` API through bound Go methods.
- Windows Job Objects kill the Python process tree if MyGo exits unexpectedly.
- The update manifest cannot update the old Electron installation; the first
  MyGo release is a manual reinstall.

## Licenses

`resources/LICENSE.txt` and `resources/NOTICE.txt` are copies of the repository's
`LICENSE` and `NOTICE`, shipped next to the executable so an installed copy carries
them. `go test` fails if the copies drift; copy them again after changing either.
