# The server's Python drops its macOS and Linux branches

**Date:** 2026-10-16
**Branch:** `worktree-server-windows-only`

## What and why

Step 2 of making this fork Windows-only: the server carried a second code path
for macOS (and a third for Linux) in the places where the system decides where
data lives, where the engine's binaries are, how to find a coding agent and
which files it can read by itself. On Windows none of those branches ever ran;
they were only reachable on the platforms this fork is dropping. This removes
them and leaves the Windows branch as the only one, with a note saying so, so
that the next reader of `app_data()` or `search_dirs()` does not have to work
out which branch Windows took.

Two small Windows-facing fixes ride with it, both named in the checklist that
authorised this change: the engine's path was split on `/` only, so a Windows
path was shown whole in the settings dialog; and the engine status carried a
`supported` field that no one read.

## The change

- `textfold/store.py` — `app_data()` keeps only the Windows location; docstring
  says Windows-only; the now-unused `sys` import goes.
- `textfold/engine.py` — `legacy()` keeps only the Windows folder; `_bin()` is
  always `venv/Scripts/<name>.exe`; `status()` loses the unread `supported`
  key. `_uv()`'s candidate list (which does try `bin/uv` and `Scripts/uv.exe`)
  is deliberately untouched.
- `textfold/agents.py` — `COMMON` is the Windows list unconditionally and
  `EXTS` is `(".exe", ".cmd", ".bat")`; the zsh/fish login-shell PATH probe,
  the `_login_path` global and its reset in `scan()`, the `~/Library/...`
  fnm/pnpm patterns and `child_env()`'s `pwd`-based USER/LOGNAME fallback are
  gone. The cross-platform version-manager patterns (`~/.nvm`, `~/.volta`,
  `~/.bun`, `~/.local/share/pnpm`, ...) and `WIN` (still used by `argv()`)
  stay. Module docstring no longer claims a login shell is asked.
- `textfold/server.py` — `serve()` calls `_quiet_children()` unconditionally.
- `textfold/office.py` — `TEXTUTIL`, the textutil branch in `reads()`,
  `_textutil()` and its call site in `convert()` are gone, with the docstring
  sentence that described them and the now-unused `subprocess`/`sys` imports;
  a comment that credited textutil for a quirk in `table()` is reworded.
- `textfold/web/app.js` — the engine path in the settings dialog is split on
  `/` **and** `\` (`.split(/[\\/]/)`), so Windows shows the last three
  segments rather than the whole path.

## How it was verified

- `python .claude/hooks/verify.py` — 85 tests, OK (5.5 s).
- `python -m py_compile` on each of the five edited Python files — OK.
- `git diff --check` — clean.
- `textfold-verifier` on the diff: **no finding that breaks or might break
  anything on Windows.** It reconstructed the pre-change Windows expressions
  and compared them: `app_data`, `legacy` and `_bin` return exactly what the
  `win32` branches returned (both executed on this machine); it re-ran the old
  `search_dirs()` body against the new one (`OLD == NEW: True`; the dropped
  `_login_path.split(":")` only ever contributed `""`, filtered out anyway, and
  the two removed `~/Library/...` patterns expand to directories that do not
  exist); `child_env()`'s old Windows path took `except ImportError` on
  `import pwd` and did nothing; `.doc/.rtf/.odt` on Windows still reach the
  engine through `engine.FILES`; and no reader anywhere consumes
  `status()["supported"]`.
- Grep for `TEXTUTIL`, `_textutil`, `_login_path`, `textutil` after the change —
  no code reference remains.

## Not measured

- **Smoothness: unmeasured.** `tools/zoombench.py` cannot run here (no
  `playwright`, no exported page under `out/compare/`). The one reader-adjacent
  line is `textfold/web/app.js:1173`, a path string in the settings dialog, not
  the zoom or the rendering — but that is a reason to expect no effect, not a
  measurement, and none was taken.
- **The Mac/Linux behaviour this removes** is not tested here and cannot be:
  those platforms are what the fork is dropping.
- **`status()`'s removed `supported` key** — no consumer exists in this repo
  (grep over Python, `textfold/web/`, `desktop/`, `site/`, `tests/`), but an
  out-of-repo one cannot be ruled out.

## Rejected / notes

- **`if WIN:` guards left in place "just in case"**: rejected — a Windows-only
  fork keeping a live macOS branch is the thing this work exists to remove.
- **Deleting `_uv()`'s `bin/uv` / `Scripts/uv.exe` candidates**: rejected and
  explicitly forbidden by the checklist; that list is how the tool finds uv
  whatever pip produced.
- **Touching `docs/DEVELOPMENT.md` and `desktop/main.js`**, which now describe a
  login-shell probe that no longer exists (`DEVELOPMENT.md:73`) and the textutil
  path (`DEVELOPMENT.md:279`): left for items 3 and 6, which own those files —
  a change outside its item's file list is a stop condition in this checklist.
  Flagged in the item's local log and the run's final report.
- **One change per branch**: the `app.js` display fix and the `supported` key
  removal are not deletions of a Mac/Linux branch. The checklist orders both
  into this item ("小修（并入本项，记录里分两小节）"), so they are deliberate, not
  drift; the verifier flagged them as the borderline case and they are recorded
  here as such.
