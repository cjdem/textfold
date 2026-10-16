# The docs and the interface stop saying python3 and the Mac modifier keys

**Date:** 2026-10-17
**Branch:** `worktree-wording-windows-only`

## What and why

The last content step of making this fork Windows-only. Every document and
every visible string in the reader's interface had been written for a Mac:
`python3 -m textfold` everywhere, `⌘K` for search and `⌘/Ctrl` for the zoom
modifier, a download section offering "macOS (Apple silicon or Intel) or
Windows", a paragraph explaining why the docs avoid the bare `textfold` command
by describing macOS's `~/Library/Python/3.9/bin`, and a note that the PDF
engine could read `.doc`/`.rtf`/`.odt` on a Mac through `textutil` (removed in
step 2). On Windows `python3` is not a command at all, so this is not just
tidier: the documented commands did not work.

## The change

- `README.md`, `README.zh-CN.md` — the download line says Windows only; the
  parenthetical "(the one macOS ships with works)" is gone; `python3` →
  `python`; present-tense `⌘K` → `Ctrl+K` and `⌘ / Ctrl + scroll` →
  `Ctrl + scroll`. The Chinese "有 Windows 版" became "只有 Windows 版".
  **The "What's new" history entries are untouched** and still carry `python3`
  and the October 14 macOS line.
- `CONTRIBUTING.md` — the three `python3` commands are `python`.
- `docs/DEVELOPMENT.md` — the paragraph on why the docs write
  `python -m textfold` was rewritten for Windows (pip's `Scripts\` folder may
  be off the PATH) where it described macOS's `~/Library/Python/3.9/bin`; the
  app paragraph now says Windows only; `⌘/Ctrl-scroll`, `⌘P` and `⌘K` are
  `Ctrl`; the "and on a Mac .doc, .rtf and .odt through `textutil`" clause is
  gone; the smoothness section describes the tool as Windows' Direct3D 11
  backend needing playwright and an exported page, and says the Metal numbers
  recorded before are not comparable; a sentence claiming agents are found "on
  the login shell's PATH" (false since step 2 deleted that probe) is corrected;
  `python3` → `python` throughout.
- `textfold/__main__.py`, `adr/__main__.py` — every `python3 -m …` is
  `python -m …`, which also removes the inconsistency inside `__main__.py`,
  whose docstring's first four lines already said `python`.
- `textfold/web/i18n.js` — the twelve languages' `hint` string: `⌘` → `Ctrl`,
  except German, where the app's own tutorial calls the key `Strg`.
- `textfold/web/tutorial.js` — the twelve languages' `zoom_d` string loses
  "⌘ or Ctrl" and keeps its own local word; the tutorial's keyboard diagram now
  draws "Ctrl" in its keycap (see "Rejected / notes" for the one geometry
  consequence); a code comment and the keycap row at the dialog's foot likewise.

## How it was verified

- `node --check textfold/web/i18n.js`, `node --check textfold/web/tutorial.js` —
  OK. `python -m py_compile textfold/__main__.py adr/__main__.py` — OK.
- `python .claude/hooks/verify.py` — 85 tests, OK (6.0 s). No test asserts any
  string this change touches (`grep` over `tests/` for `prog=`,
  `python3 -m textfold`, `Ctrl`, `zoom_d`, `hint` finds nothing relevant).
- `grep -c "⌘"` in `i18n.js` and `tutorial.js` → 0 and 0. The only `python3`
  left in the eight files are the two intended history entries
  (`README.md:254`, `README.zh-CN.md:254`).
- `git diff --check` — clean. The `git diff` looks like whole-file churn under
  `core.autocrlf`, which the verifier confirmed is line endings only.
- `textfold-verifier` on the diff: claims that every substitution landed in the
  right language (checked all twelve of each, per language), that `python` is
  correct everywhere it now appears, and that "Ctrl" fits the 14-unit keycap at
  6px hold. It raised two things, both fixed: the German hint said `Ctrl+Scrollen`
  while the German tutorial says `Strg` (now `Strg+Scrollen` in both), and the
  Chinese download line read loosely (now `只有 Windows 版`).

## Not measured

- **Smoothness: unmeasured.** `textfold/web/i18n.js` and `tutorial.js` are the
  reader's own JavaScript, so this change touches the reader — with strings and
  one static SVG `<text>` only, no layout, animation or rendering logic. But
  the axis is unmeasured: `tools/zoombench.py` needs `playwright` and an
  exported page under `out/compare/`, and this machine has neither. "No impact
  on performance" is not something this record will say.
- **The tutorial's keyboard diagram was not rendered.** The claim that "Ctrl"
  fits its keycap is a font-metric estimate (≈9.3–10.3 units of a 14-unit rect),
  not a screenshot.

## Rejected / notes

- **The tutorial diagram's baseline moved** (`y=18.6` → `17.5`) and the label
  gained an inline `font-size:6px`, because "Ctrl" is four letters where `⌘` was
  one and would overflow the keycap at the stylesheet's 8.5px. The rect, its
  position and the rest of the diagram are unchanged. This is the one place the
  change is not purely a string.
- **German says `Strg`, not `Ctrl`.** The checklist says `⌘` → `Ctrl` for all
  twelve hints; applied literally the German would name the key differently from
  the German tutorial two files away, and differently from the German keyboard.
  `Strg` it is, disclosed here.
- **`python3` left outside these eight files, on purpose, and why**: the
  interpreter discovery in `.claude/hooks/verify.py` must probe both names;
  `.github/workflows/site.yml` runs on Linux; `desktop/main.js` and
  `prepare-payload.mjs` keep their non-Windows payload paths (steps 3 and 4
  deliberately left those); the website's Python instructions are the
  non-Windows route by step 5's decision; `docs/changes/*.md` are records of
  what was true then.
- **`python3` left outside these eight files that no item of the checklist
  covers**, flagged rather than changed (changing a file outside its item is a
  stop condition in this checklist): `docs/format.md:7`; the user-facing
  runtime message `textfold/parse.py:329`; `adr/__init__.py:1`, now inconsistent
  with the `adr/__main__.py` this change fixed; the dev-only docstrings in
  `tests/*.py`, `tools/gallery.py`, `tools/readme_assets.py` and
  `desktop/scripts/smoke.py:4`; and `plugins/pi-textfold/tests/tui_smoke.py:14`,
  which is item 7's file and is not to be touched at all.
- **`⌘` left in four code comments** (`textfold/web/app.js:270`,
  `reader.js:2473` and `:3363`, `reader.css:656`). They are comments, the code
  accepts `metaKey` and `ctrlKey` alike, and no user-visible `⌘` remains.
