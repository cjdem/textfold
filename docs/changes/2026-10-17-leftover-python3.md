# The leftover python3 spellings developers copy on Windows

**Date:** 2026-10-17
**Branch:** `worktree-leftover-python3`

## What and why

Step 6 (2026-10-17) rewrote `python3` → `python` in the eight files its item
named, and its record listed the `python3` left outside them. Some of those were
deliberate (Linux CI, the non-Windows route on the website); the rest were
developer-facing lines that no checklist item owned — including the one message
a Windows user actually sees: `textfold/parse.py`'s
`RuntimeError("The lxml package is missing: run  python3 -m pip install …")`,
which on Windows points at a command that does not exist (`python3` on this
machine resolves to the Microsoft Store stub). This change fixes that batch.
Nothing executable changed; the test suite, CI and every platform-specific
command are untouched.

## The change

- `textfold/parse.py:329` — the missing-lxml `RuntimeError` says `python -m pip
  install` (and loses the double space). The only edit in the file; the
  `try/except` and control flow are byte-identical.
- `docs/format.md:7` — the format document's two `python -m textfold get`
  examples, the commands a reader is meant to copy.
- `adr/__init__.py:1` — `python -m adr`, now consistent with the `adr/__main__.py`
  step 6 fixed.
- `tests/test_*.py` (ten files) — the "Run from the repo root: `python -m
  unittest discover tests`" line in each header. `test_agents_windows.py` never
  had one.
- `tools/gallery.py:3-4`, `tools/readme_assets.py:3`, `site/build.py:9-10` —
  dev-only usage docstrings. These blocks have hand-aligned trailing comments;
  each line kept its comment column by absorbing the freed character into the
  gap (verifier measured the columns: unchanged).
- `desktop/scripts/smoke.py:4` — said `payload/python/bin/python3
  scripts/smoke.py` (the Mac payload's path, which steps 3–4 stopped producing)
  with the Windows form in parentheses; now it is only the line the release
  build actually runs (`.github/workflows/desktop.yml`): `payload\python\python.exe
  scripts\smoke.py`.

## How it was verified

- `python .claude/hooks/verify.py` — 85 tests, OK (6.3 s).
- `python -m py_compile` over all sixteen changed `.py` files — OK (the suite
  does not import `tools/` or `site/build.py`, so this is not implied by it).
- `git diff --check` — clean. `git diff --stat` — 17 files, 19 insertions, 19
  deletions.
- `git grep -n python3` over tracked files: every remaining hit is one of the
  exclusions below; none is a line a developer would copy on Windows.
- `textfold-verifier` on the diff: **sound**, zero breaking findings. It read all
  19 changed pairs, checked no changed string is read by `__doc__`/`getdoc`/
  doctest or asserted anywhere, confirmed the comment columns (69/69, 51/51/51,
  57) are preserved to the character, checked `smoke.py` against the workflow
  that runs it, and re-ran the suite (85, OK, 5.967 s). It corrected two of this
  change's own rationales, recorded under Rejected; neither changes a line.

## Not measured

- **Smoothness: unmeasured.** This change touches no reader file — nothing under
  `textfold/web/` is in the diff — but `tools/zoombench.py` needs `playwright`
  and an exported page under `out/compare/`, and this machine has neither, so
  the axis is not measurable here and this record does not report it as
  unaffected.

## Rejected / notes

- **`python3` kept on purpose**: `.claude/hooks/verify.py` (interpreter
  discovery must probe both names); `.github/workflows/site.yml:38` (Linux
  runner); `plugins/pi-textfold/tests/tui_smoke.py:14` (a deliberately Unix-only
  test); `README.md:254`, `README.zh-CN.md:254` (history is not rewritten).
- **The website's `python3` stayed** (`site/strings.py`, `site/template.html`,
  `site/build.py:105`, `:173`, `:190`). The verifier's nit, accepted: these are
  not all "PyPI instructions shown to non-Windows visitors" — `:105` is JSON-LD
  served to every crawler and `:173` is the llms.txt line for AI agents. They
  stay because they are the site's Python-package route, which step 5 kept by
  decision, and because neither spelling is right for everyone (`pip install`
  needs `python3` on macOS and Linux, `python` on Windows; the pages send
  Windows visitors to the installer at `site/build.py:189`). Noted consequence:
  an agent on Windows following llms.txt would hit the Store stub. Changing the
  site's wording is a policy decision beyond this sweep, and is flagged rather
  than taken.
- **`desktop/main.js` stayed, including its comment at `:7`.** The verifier
  corrected this change's own description: `:7` is a comment, not an executable
  path. It is still right to leave — it already names both forms ("the python3
  on the PATH (python on Windows)") and accurately describes the code (`:17`,
  `:19` and `prepare-payload.mjs:51`, `:60`, including the `^python3\.\d+$`
  directory-name regex) that steps 3–4 deliberately left in place.
- **The four `⌘` code comments in `textfold/web/`** are outside this request
  (`python3` only) and remain listed as open in `WINDOWS-ONLY.md` §七.
- **`tests/test_agents_windows.py` shows as modified in `git status` and is
  byte-identical to HEAD** — a stat-cache artifact of rewriting test files in
  place; the verifier confirmed `git hash-object` equals `HEAD:`'s.
- `git diff` warns "LF will be replaced by CRLF" for the rewritten files under
  `core.autocrlf`; the diff is one line each, with no whole-file churn.
