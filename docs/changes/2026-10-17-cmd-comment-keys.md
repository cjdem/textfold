# The reader's code comments call the modifier key Ctrl

**Date:** 2026-10-17
**Branch:** `worktree-cmd-comment-keys`

## What and why

Step 6 changed every user-visible `⌘` to Ctrl and left four code comments behind
— recorded in `docs/changes/2026-10-17-windows-only-wording.md`'s "Rejected"
section — because the code itself still accepts `metaKey` and `ctrlKey` alike.
They were then the last `⌘` in the repository's code, while every visible
string, `docs/DEVELOPMENT.md` and the tutorial already say Ctrl; a developer
reading this Windows-only fork's reader should not have to know the Mac key.
This follow-up sweeps the four.

## The change

- `textfold/web/app.js:270` — `⌘K (Ctrl+K), or / outside a field: the search`
  → `Ctrl+K, or / outside a field: the search` (the parenthetical was the
  repetition of the two names).
- `textfold/web/reader.js:2473` — `⌘P prints the same` → `Ctrl+P prints the
  same`.
- `textfold/web/reader.js:3363` — `⌘/Ctrl + wheel` → `Ctrl + wheel`.
- `textfold/web/reader.css:656` — `or ⌘P` → `or Ctrl+P`.

Four lines in three files, comments only. The code around each site (which
tests `e.metaKey || e.ctrlKey`) is byte-identical to HEAD, so the reader still
accepts either key on either platform; only what the comments call it changed.

## How it was verified

- `git diff --stat` — 3 files, 4 insertions, 4 deletions; `git diff -U0` shows
  exactly four hunks and nothing else moved; `git diff --check` clean.
- `node --check textfold/web/app.js`, `node --check textfold/web/reader.js` —
  both parse.
- `python .claude/hooks/verify.py` — 85 tests, OK (6.0 s).
- `git grep -n "⌘"` — zero hits in code; only `docs/changes/*.md` (records of
  what was true then, not rewritten). `i18n.js`, `tutorial.js` and the HTML are
  already free of it.
- `textfold-verifier`: **sound**, zero breaking findings. It proved comment-only
  by byte comparison — masked the changed line, normalized line endings, and
  sha256'd the rest against the HEAD blob for all three files: identical. Since
  `reader.js` embeds CSS in template literals elsewhere, it ruled out the real
  trap by injecting a `//` + backtick payload at each of the three JS sites and
  running `node --check` (method validated first on synthetic controls): all
  still parse, so none is template raw text; the CSS site's comment delimiters
  balance 52/52 around it. It also confirmed there is no second copy to edit —
  the desktop payload (`prepare-payload.mjs`) and the static-page inliner
  (`textfold/build.py`) copy these files at build time.

## Not measured

- **Smoothness: unmeasured.** This change touches the reader's own files
  (`app.js`, `reader.js`, `reader.css`) — with comment text only and no code
  byte different — but the axis stays unmeasured: `tools/zoombench.py` needs
  `playwright` and an exported page under `out/compare/`, and this machine has
  neither. "No impact on performance" is not something this record will say.

## Rejected / notes

- **The older records keep their `⌘`**: `2026-10-17-windows-only-wording.md`
  and `2026-10-17-leftover-python3.md` describe these four comments as left
  behind; they record what was true then and are not rewritten. This record is
  the note that the sites are now done.
- **`⌘K (Ctrl+K)` parenthetical and `Ctrl/⌘` spellings rejected** — step 6's
  convention names the Windows key only; a comment listing both would keep the
  Mac form in the text developers read most.
- **`reader.js:3363` now says Ctrl while its handler still accepts `metaKey`**
  — intended, and the verifier's observation, not a defect: the code keeps
  working with either key, and this is what `docs/DEVELOPMENT.md` and every
  visible string already say.
