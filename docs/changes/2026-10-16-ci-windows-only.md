# The desktop release workflow builds Windows only

**Date:** 2026-10-16
**Branch:** `worktree-ci-windows-only`

## What and why

Step 4 of making this fork Windows-only. The workflow that builds and releases
the desktop app ran three jobs — an Apple silicon Mac, an Intel Mac and Windows
— each signed and notarized on its own runner, then merged the two Macs' update
feeds into `latest-mac.yml` before publishing the draft release. This fork ships
one Windows installer, so two of those jobs could only fail, and the merge step
could only fail with them. This leaves the Windows job and the
publish-the-draft step, and deletes `icon.yml`, which existed only to compile
the macOS icon assets from `desktop/build/icon.icon/` (deleted in step 3).

## The change

- `.github/workflows/desktop.yml` — the matrix is `win-x64` alone; the "A tag's
  Mac app is signed" pre-check, the `CSC_LINK`/`CSC_KEY_PASSWORD`/`APPLE_*`
  environment variables and the `CSC_LINK`-unset shell guard are gone
  (`GITHUB_TOKEN` and `VERSION` stay); the artifact upload and the "Into the
  draft release" globs lost `*.dmg` and `*.zip`; the smoke step runs
  `payload/python/python.exe` directly instead of probing the Mac path first;
  the top comment describes Windows only. The `publish` job keeps exactly the
  step that flips the draft release live
  (`gh release edit "$TAG" -R "$REPO" --draft=false --latest`) and its
  `needs: build`; its checkout, artifact download, `latest-mac.py` merge and
  `latest-mac.yml` upload are gone.
- `.github/workflows/icon.yml` — deleted.
- `publish.yml` and `site.yml` — untouched, as the checklist requires.

## How it was verified

CI cannot be run from this machine, so this is static verification; see "Not
measured".

- The YAML parses (PyYAML, already installed for the system Python) into the
  same shape: `prepare` → `build` → `publish`, `build needs: prepare`,
  `publish needs: build`, matrix `[{name: win-x64, os: windows-latest,
  script: dist:win}]`. No tabs, no trailing whitespace, `git diff --check` clean.
- The tag path was traced end to end on the parsed document: `prepare` creates
  the draft release, `build` uploads `*.exe`/`*.blockmap`/`latest.yml`,
  `publish` runs `gh release edit … --draft=false --latest`. A tag still ends in
  a published release.
- Removing `actions/checkout` from `publish` does not break it: its one step
  reads no file and passes `-R "$REPO"`, so `gh` needs no checkout.
- `grep -i` over `.github/` for `mac`, `macos`, `darwin`, `osx`, `apple`, `.dmg`,
  `csc`, `notariz`, `actool`, `iconutil`, `codesign`, `Assets.car`, `.icns`,
  `entitlement`, `provision`, `latest-mac`, `icon.yml`, `.plist` — zero hits.
  Nothing references `icon.yml`; no workflow has a `workflow_run` on another.
- Repo-wide grep for `latest-mac`, `dist:mac`, `pack:mac`, `icon.icon`,
  `Assets.car`, `entitlements.mac`, `MAC_CERT`: the only hits are in the previous
  item's change record, which names them as things it removed.
- `python .claude/hooks/verify.py` — 85 tests, OK (6.0 s).
- `textfold-verifier` on the diff: **no finding that breaks anything.** It parsed
  the YAML, traced the tag path, confirmed the kept expressions work on a
  windows-latest runner with `shell: bash`, and confirmed nothing macOS-only
  remains in `.github/`. It also noted the old `publish` job downloaded
  `pattern: textfold-mac-*` unconditionally, which errors when nothing matches —
  so the new `publish` is also a fix for a manual `workflow_dispatch` run.

## Not measured

- **CI was not run, and no build was run.** This machine cannot run GitHub
  Actions, and `npm install`/`electron-builder` are forbidden here (step 3's
  record says the same). So "still builds the Windows app and still publishes
  the release" is read from the parsed YAML plus the kept `package.json` and
  `prepare-payload.mjs`, not observed.
- **Smoothness: unmeasured.** Nothing here touches the reader, zoom or
  rendering, and no measurement was taken: `tools/zoombench.py` needs
  `playwright` and an exported page, neither of which is here.

## Rejected / notes

- **Keeping a `macos-*` job that is skipped**, e.g. `if: false`: rejected — a
  job that can never run is worse than no job; it still reports as a check.
- **Narrowing the upload glob `latest*.yml` to `latest.yml`**: not done. It
  matches only `latest.yml` on a Windows build anyway, and the checklist scopes
  this item to removing `*.dmg`/`*.zip`.
- **The `publish` job keeps its name and `needs: build`** even though it is now
  one step: a tag's release must still only go live after the build succeeded.
- **Out of scope, flagged not fixed**: `docs/DEVELOPMENT.md:48-49` still says the
  app is built "For macOS, Apple silicon and Intel, signed and notarized"
  (item 6 owns that file); `README.md:93` and `site/` still offer macOS downloads
  (items 5 and 6); `desktop/scripts/smoke.py:4` still documents the Mac-first
  invocation `payload/python/bin/python3`; `.gitignore:22` still names the
  deleted entitlements file. None is in this item's file list.
