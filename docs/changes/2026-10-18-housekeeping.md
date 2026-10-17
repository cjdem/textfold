# The workspace ignores what a source run leaves, the docs catch up, and the build workflows are parked

**Date:** 2026-10-18

## What and why

`git status` was not clean: three files a source checkout or a manual check
leaves behind sat untracked. Each now has an ignore rule with a comment, and
none was moved or deleted:

- `library.json` — the sidebar's state. `store.DATA` is the clone when the
  server runs from source (`SOURCE`), so this is the same kind of data as
  `papers/`, not a stray file.
- `tests/*.pdf` — a sample dropped there for a manual check. The suite makes
  its own PDFs; no test reads this one, and it must never be committed.
- `WINDOWS-ONLY.md` — the maintainer's Windows-only checklist, kept beside
  `STATUS.md`, which is already ignored.

The docs also disagreed with the code, so they were corrected:

- `CONTRIBUTING.md` said the interface is translated in twelve languages;
  `textfold/web/i18n.js` and `langs.LANGS` now have English and Simplified
  Chinese only.
- `.claude/skills/optimize/SKILL.md` and the record template expected 85
  tests; the suite is 130.
- `CLAUDE.md` and `references/invariants.md` say the test gate sets
  `TEXTFOLD_NO_MODELS=1`, but `verify.py` built that environment and never
  passed it to `subprocess.run`: the suite had been running with the models
  available. `run()` now takes `env`, and the test run is given the gate's
  environment. The suite passes in that mode (checked by hand before the
  change, and through the gate after it).
- `README.md` and `README.zh-CN.md` did not mention the MinerU cloud API,
  now in the file table (with the privacy note: the file leaves the computer)
  and in **What's new**, together with the English document's Simplified
  Chinese version made by default. RTF, OpenDocument, EPUB and CSV still need
  the engine or TextFold's own reader, and both READMEs say so.
- `docs/DEVELOPMENT.md` now states the landing page's rule: the catalog is
  built once, the Ollama and bridge probes answer from their last result and
  refresh in the background, and `provider_list` caches the rows for ten
  seconds, keyed by the settings, the environment and the probe answers.

The three GitHub Actions workflows were **parked, not deleted**:
`desktop.yml`, `publish.yml` and `site.yml` moved to
`.github/workflows-disabled/`, which GitHub does not read, so a push builds
nothing. A README there says which trigger each one had and how to move it
back; `desktop/README.md` and `docs/DEVELOPMENT.md` now describe them as
parked rather than active. The build and release steps themselves are
unchanged for when they are wanted again.

## How it was verified

- `python .claude/hooks/verify.py` — **130 tests, OK** (6.12 s), now with the
  gate actually passing `TEXTFOLD_NO_MODELS=1`.
- `TEXTFOLD_NO_MODELS=1 python -m unittest discover tests` — 130, OK, run by
  hand as well.
- `git status --short` — only the files of this change (the edited docs and
  ignore rules, the three renames, the parked workflows' README and this
  record); the three ignored files no longer appear.
- `ls .github/workflows` — empty; `ls .github/workflows-disabled` — the three
  workflows and the README.
- `git diff --check` — no whitespace errors.

## Not measured

- No application code changed. The only executable change is the test gate's
  environment, which makes the documented mode real rather than changing
  what the suite checks.
- The parked workflows were not run here (GitHub Actions cannot run on this
  machine); their triggers and steps are unchanged from the last commit that
  touched them.
- `WINDOWS-ONLY.md` stays on disk. If it should be committed instead of
  ignored, remove its line from `.gitignore`.
