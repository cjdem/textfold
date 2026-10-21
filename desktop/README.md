# TextFold as an app

> Migration note: `desktop-mygo/` is the new hybrid shell. It keeps this
> Python server and replaces Electron with MyGo. The Electron code here stays
> available as a fallback until the MyGo installer and update transition have
> been validated.

The same local server and reader in one window, with its own Python, so a reader needs nothing installed. Agents
on the computer (Claude Code, Codex, Pi), the ChatGPT bridge and API providers work as they do in the browser.
What you read is kept where `python -m textfold serve` keeps it, so the two share one library:
`%LOCALAPPDATA%\TextFold\`. Settings and keys are in `~/.textfold/`. `TEXTFOLD_DATA` points the app at another
folder, as it does the server.

| System | File | Signed |
|---|---|---|
| Windows, 64-bit | `TextFold-win-x64-setup.exe` | not yet: SmartScreen asks once, More info › Run anyway |

The installer's name carries no version, so `releases/latest/download/<name>` is always the newest (the download
page links there).

## Updates

The app asks GitHub for the newest release a few seconds after it starts and every four hours: it reads the
release's public `latest.yml`, and sends nothing of the reader's. A newer version shows as a note
at the bottom right of the page, in the reader's language. Nothing downloads until they click Download (only what
changed, when the blockmap allows), and the new version installs when they click Restart, or the next time they quit.
Settings shows the version and checks by hand. A copy run from the code (`npm start`) does not update itself.
`TEXTFOLD_UPDATES=<url>` points the app at another folder of release files, for a test.

## Build

```bash
cd desktop
npm install
npm run dist:win      # Windows, on Windows: the setup .exe
```

`npm run payload` (run by each) downloads a standalone CPython 3.12 for the system (python-build-standalone),
installs `requirements.txt` into it and copies `textfold/` (the reader's pages inside it) beside it, in
`desktop/payload/`. Build outside a synced folder (Dropbox, iCloud Drive), or have it skip `desktop/node_modules`,
`desktop/payload` and `desktop/out` (several hundred MB).

Before it ships, that Python runs TextFold's tests, reads a Markdown, an HTML and a CSV file without a model, and
serves the reader with them listed:

```bash
payload\python\python.exe scripts\smoke.py
```

## Releases

The release workflows are parked in `.github/workflows-disabled/` for now (see its README); GitHub runs only what is in
`.github/workflows/`. Once they are moved back: `desktop.yml` builds the app on windows-latest when a version is
tagged, as `publish.yml` sends the package to PyPI. It goes into a draft release, published once it has succeeded, with the file the app updates from:
`latest.yml`. The tag, `textfold/__init__.py` and this folder's `package.json` name the same version, or nothing is
built. Run by hand (Actions › desktop › Run workflow), the files are the run's artifacts, and a version may be given
to the app alone: two such builds, an older and a newer, try an update from one to the other.

## Windows

The server runs with no console window of its own, and the programs it starts (agents, npx) start without
one either (`server._quiet_children`). An agent installed by npm is a `.cmd` shim, which would pass its arguments
through cmd.exe; the script it names is run by node instead (`agents.argv`). The installer is per user, in
`%LOCALAPPDATA%\Programs\TextFold`.
