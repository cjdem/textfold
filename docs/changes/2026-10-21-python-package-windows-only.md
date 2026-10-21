# The Python package is Windows-only

- Date: 2026-10-21.
- Mode: scope correction after the first Windows release.
- Decision: state the fork's real scope: the Python package is Windows-only,
  like the desktop app.

## Why

The Python package was still described as OS Independent in `pyproject.toml`
and "on any system" in the README and the website. The code is not:
`textfold/server.py` unconditionally sets Windows-only `creationflags` on
every child process, and `textfold/agents.py` searches only `.exe`, `.cmd`
and `.bat`. On macOS and Linux, PDF conversion, agents and the npx bridge
would fail.

## What changed

- `README.md` and `README.zh-CN.md` say the whole fork is Windows-only, not
  just the desktop app; the Python install section says Windows.
- `pyproject.toml` declares `Operating System :: Microsoft :: Windows`
  instead of OS Independent.
- The site says Windows in the meta description, Python card, JSON-LD and
  `llms.txt`; `site/page.js` no longer offers the Python package as the
  download for a non-Windows computer.
- `docs/DEVELOPMENT.md` says the Python package is Windows-only and no
  longer tells readers to `pip install textfold` from PyPI (the original
  project's package).

## Not done

- The Python code still uses Windows-only subprocess flags and agent
  extensions; that is consistent with the declared scope. A future
  cross-platform change would need to guard both and add Linux CI.

## Verification

- `python site/build.py` fills both pages with no `{{...}}` placeholders.
- The built pages contain no "any system" or OS Independent claim.
- The Python tests pass on Windows.
