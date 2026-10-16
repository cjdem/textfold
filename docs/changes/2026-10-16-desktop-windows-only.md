# The desktop app drops its macOS build chain

**Date:** 2026-10-16
**Branch:** `worktree-desktop-windows-only`

## What and why

Step 3 of making this fork Windows-only. `desktop/` could build, sign, notarize
and ship a macOS app as well as a Windows one: a second menu template, a macOS
PATH in the launched server's environment, three npm scripts and a whole
`build.mac` block for electron-builder, the entitlements and icon assets those
needed, a script that merged the two Macs' update feeds, and the README to
explain it. None of that can run here and none of it is wanted by a fork that
ships one Windows installer. This removes it; the Windows build, its icon, its
`nsis` installer, its `latest.yml` update feed and the code that starts the
server are untouched.

## The change

- `desktop/main.js` — the application menu is built from one template (no
  `process.platform === 'darwin'` branch: `fileMenu`, and Check for Updates in
  Help); the launcher's PATH no longer has a macOS arm (`/opt/homebrew/bin`,
  `/usr/local/bin`) or the comment about asking the login shell; the
  data-folder comment no longer describes the Mac path or `python3`.
- `desktop/package.json` — `dist:mac`, `dist:mac:x64` and `pack:mac` scripts
  gone; the `build.mac` and `build.dmg` blocks gone. `win`, `nsis`,
  `build.icon` (`build/icon.png`), `publish` and the `electron-updater`
  dependency all stay.
- `desktop/scripts/prepare-payload.mjs` — `TARGETS` is `win32-x64` alone; the
  Rosetta wrapper around `run()` is gone (`execFileSync(py, args, opts)`); the
  darwin comments are gone. The Windows pruning branches are kept.
- Deleted: `desktop/scripts/latest-mac.py`, `desktop/build/entitlements.mac.plist`,
  `desktop/build/icon.icns`, `desktop/build/Assets.car`, `desktop/build/icon.icon/`
  (whole directory). `desktop/build/icon.png` stays.
- `desktop/README.md` — the two macOS download rows, the "Signing and
  notarization" section and the Mac build commands are gone, along with the
  `latest-mac.yml` statements; the Windows build/update text stays.

## How it was verified

Static, plus the suite. A real build was not run — see "Not measured".

- `node --check desktop/main.js` — OK. `node --check desktop/scripts/prepare-payload.mjs` — OK.
- `desktop/package.json` parses as JSON.
- `python .claude/hooks/verify.py` — 85 tests, OK (6.0 s).
- `git diff --check` — clean.
- `desktop/build/` now holds only `icon.png`.
- Repo-wide grep for `Assets.car`, `icon.icns`, `entitlements.mac`,
  `latest-mac`, `dist:mac`, `pack:mac`, `icon.icon`: the only survivors are in
  `.github/workflows/desktop.yml` and `.github/workflows/icon.yml`, which item 4
  of the same checklist owns and changes next. `pack:mac` has no hit at all;
  `package-lock.json` has no hit at all (only npm's own `@electron/notarize`
  dependency appears there).
- `textfold-verifier` on the diff: **no finding that breaks the Windows build,
  start or update path.** It confirmed `win`/`nsis`/`icon.png`/`publish` are
  intact and that removing `build.mac`/`build.dmg` cannot affect a `--win`
  build (those keys only ever applied to darwin/dmg targets); that
  `prepare-payload.mjs` is still coherent with one TARGET (the argv defaults, the
  missing-target error and the run-on-its-own-system guard all still apply); and
  that the only callers of the deleted scripts are the CI workflows item 4
  rewrites.

## Not measured

- **The app was not built or started.** `npm install`, `npm start` and
  `electron-builder` were not run (the checklist forbids installing anything,
  and neither is set up here). `node --check` only parses a file — it does not
  execute the Electron main process. So "the Windows app still builds and
  starts" rests on reading `package.json`, `main.js` and `prepare-payload.mjs`,
  not on a build.
- **Smoothness: unmeasured.** Nothing here touches the reader, the zoom or the
  rendering, but no measurement was taken either — `tools/zoombench.py` needs
  `playwright` and an exported page, and this machine has neither.
- **CI was not run.** This machine cannot run GitHub Actions; the CI-side
  breaks the verifier found in `desktop.yml` and `icon.yml` are read from the
  YAML.

## Rejected / notes

- **Removing the other dead non-Windows fragments** in `main.js`
  (`path.join(PAYLOAD, 'python', 'bin', 'python3')`, `PYTHON`'s `'python3'`
  fallback, `else if (WIN)`, `WIN ? '' : '/usr/bin:/bin'`): not done. The
  checklist scopes this item's `main.js` edits to the menu branch and the PATH
  Mac segment; `WIN` is still read at four places, so nothing is unused. Left as
  a known leftover.
- **`.gitignore:22`** still says "desktop/build/ is the app's icon and
  entitlements" — the entitlements file no longer exists. `.gitignore` is
  outside every item's file list, so it was left alone and flagged in the run's
  final report rather than changed here.
- **`desktop/README.md`'s Releases paragraph is briefly ahead of CI**: it now
  says the workflow builds the app on `windows-latest`, while
  `.github/workflows/desktop.yml` still lists three jobs. Item 4 rewrites that
  workflow immediately after this change; leaving the old text would have kept
  the two deleted-file names (`latest-mac.yml`, `scripts/latest-mac.py`) in a
  document this change was making true.
- **`docs/DEVELOPMENT.md:48-50`** still describes the app as built for
  "macOS, Apple silicon and Intel, signed and notarized". That paragraph is
  item 6's, verbatim, so it is a deliberate deferral, not a miss.
- **`desktop/package-lock.json`** was not touched, per the checklist: npm
  resolves per-platform optional dependencies itself and editing it would break
  its integrity check. It needed no edit anyway.
