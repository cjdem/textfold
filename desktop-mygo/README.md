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
`%LOCALAPPDATA%\TextFold`, the same folder as the Python server and the old
Electron app.

## Payload and build

The packaged app needs a standalone CPython and TextFold's packages:

```powershell
node scripts/prepare-payload.mjs
go tool mygo build
```

`prepare-payload.mjs` reuses `../desktop/scripts/prepare-payload.mjs` and writes
`resources/payload/{python,app}`. The MyGo build output is under `build/`.
If GitHub's API is unreachable, pass a downloaded python-build-standalone
archive and its published digest:

```powershell
$env:PBS_FILE = "$env:TEMP\cpython-...-install_only_stripped.tar.gz"
$env:PBS_SHA256 = "<published sha256>"
node scripts/prepare-payload.mjs
```

## Boundaries

- `resources/payload/` is generated and ignored.
- The WebView trusts only the exact dynamic `http://127.0.0.1:<port>` origin.
- `preload.js` restores the old `window.desktop` API through bound Go methods.
- Windows Job Objects kill the Python process tree if MyGo exits unexpectedly.
- Signed MyGo updates are not configured yet; the existing Electron update
  manifest cannot update a MyGo installation.
