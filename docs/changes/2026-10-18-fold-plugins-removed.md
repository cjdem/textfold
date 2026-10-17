# The Claude Code and Pi reply-folding plugins are gone, with their installation promotion and their invariant

**Date:** 2026-10-18
**Branch:** `worktree-plugins-removed`

## What and why

Item 3 of the confirmed product scope. Folding a coding assistant's replies in place was a
second product living in the same repository: a Claude Code mod, a Pi extension, their market
place entry, two TypeScript fold engines, and installation instructions on the site and in both
READMEs. The scope keeps the reader and the model calls and removes the display plugins; the
plugins never wrote layers or called a model, so nothing under `textfold/` changed.

## The change

- Deleted `plugins/textfold/` and `plugins/pi-textfold/` in full: the fold engines, the Claude
  Code hooks and register component, the Pi extension, both TypeScript test suites, the Pi TUI
  smoke test, the package files and the plugin READMEs.
- Deleted `.claude-plugin/marketplace.json` (its only plugin was `plugins/textfold`) and
  `tests/test_pi_textfold_same_fold.py` (two tests, the only check that the two `fold.ts` copies
  matched).
- Deleted the plugin GIFs `docs/assets/textfold.gif` and `docs/assets/pi.gif`; the removed
  sections were their only use.
- `README.md`, `README.zh-CN.md` — removed the "Also for agent output" opener, the whole "In
  Claude Code and Pi" section, the "Fold your agent's replies" bullet (the heading is now "One
  fold, two places" / "一种折叠，两个地方"), the October 15 Pi entry and the October 7 mod entry,
  and the reply-folding clause from the October 9 rename entry.
- `docs/format.md` — the paragraph on author-written folds no longer names the Claude Code mod.
- `SECURITY.md` — the mod is no longer in the in-scope list.
- `site/template.html`, `site/strings.py`, `site/style.css` — the plugin command block, the
  agent paragraph, its two strings and its rule removed. `site/build.py` — the `llms.txt` bullet
  that told an agent to install the plugin, the JSON-LD feature "Folds an agent's replies in
  Claude Code", the `llms.txt` link to the removed README section, and the preview's description
  of the plugin were removed.
- Workflow docs — `CLAUDE.md` and `invariants.md` no longer state the byte-identical fold-engine
  invariant; `optimize/SKILL.md` drops the plugin check (seven checks become six, renumbered) and
  the verifier agent's invariant list drops the fold-engine line. `docs/DEVELOPMENT.md` never
  listed the plugins in its module map, so it needed no edit.

## Decisions

- Remove the plugins rather than keep them without promotion: the code, its two engines and its
  tests exist only for folding replies in place, and nothing else calls them.
- Remove the GIFs and the two "what's new" entries with the feature. The entries advertise a
  capability that no longer exists; the history stays in git.
- Retire the fold-engine invariant with the code it guarded. With no copies left there is
  nothing to compare, and a rule about absent files would outlive the feature.
- Keep the generic "an agent's output is text" framing (the PyPI summary, the `llms.txt` opening,
  the sources illustration). The reader still reads a text file or a Markdown file whoever wrote
  it; only the in-place reply folding was removed. The scope's item 6 pulls the command line and
  agent interface back from the README and homepage, which is where the remaining positioning is
  dealt with.
- No model integration, summary, translation or Q&A code was touched. Claude Code, Codex and Pi
  remain the three runtimes the settings can drive.

## Rejected

- Keeping the plugins but hiding their installation: the engines and their tests still need
  maintenance, and the README still has to explain them.
- Removing only the Claude Code mod and keeping the Pi extension: both are the same capability,
  and the scope removes both.
- Keeping the invariant and its test with no plugin: `tests/test_pi_textfold_same_fold.py` would
  fail on missing files, and the invariant names paths that no longer exist.
- Removing the model runtimes or `textfold get`: the plugins were a display layer; the scope
  keeps both.

## What is lost

- Folding a reply in place, with one key per level, in Claude Code and in Pi, including the Pi
  `/fold` command and the starting-level setting.
- The two TypeScript suites (`fold.test.ts`, `level.test.ts`, `ui.test.ts`) and the Pi TUI smoke
  test, none of which could run on this machine anyway.
- The plugin READMEs, the marketplace entry, the two GIFs, and the "what's new" entries for
  October 15 and October 7.

## How it was verified

- `python .claude/hooks/verify.py` — **173 tests, OK** (6.9 s); the count dropped from 175 by the
  two tests in the deleted file.
- `python site/build.py` — `unfilled: []`; `node --check site/page.js`, `node --check
  site/ascii.js` — clean.
- In the browser, both built pages: no `claude plugin` text, no `.agent` block, no video; the
  download CTA, the pipeline block with its `textfold get` commands and five FAQ entries are
  present. Chinese page: title and H1 correct, "下载 Windows 版", five FAQ entries.
- `grep` from the repository root for `plugins/`, `pi-textfold`, `fold.ts`, `claude plugin`,
  `agent_h`/`agent_p`, `textfold.gif`/`pi.gif`, `#in-claude-code-and-pi` and "Claude Code mod"
  (excluding history, the product-scope document, `notes/`, `.venv` and `node_modules`) — only
  unrelated matches: `mdit-py-plugins` as a dependency and GitHub's reserved `marketplace` path
  segment in `textfold/github.py`.
- Every `](#anchor)` link in both READMEs resolves against the remaining headings; no link
  points at the removed section.
- An independent verifier pass found no functional break. It noted one stale cross-reference in
  the workflow docs (the verifier is check 3 after renumbering, not check 4) — fixed — and three
  generic "agent output" claims (PyPI summary, `llms.txt` opening, README image alt). Those are
  the framing deliberately kept above and deferred to item 6, not plugin-specific claims.

## Invariants

- **Fold engines byte-identical:** retired with the code; no copy remains, and the test that
  enforced it is deleted with the feature.
- **Parsed HTML through `textfold/semantic.py`:** no parser or semantic file changed.
- **Parser change renumbers atoms:** not applicable; no parser change.
- **Persistent writes serialized per document:** no persistence code changed, so no new
  two-writer case exists.
- **UTF-8 on a Chinese Windows:** the site build wrote `zh.html` on this machine without a
  decode or encode error; the edited records and READMEs are UTF-8.
- **No new dependencies:** `requirements.txt` and the dependency lists are untouched.

## Not measured

- Zoom smoothness: it stays **unmeasured** on this machine (no `playwright`, no exported pages
  under `out/compare/`). The diff touches no reader or zoom file, but no claim is made that it is
  unaffected.
- The deleted TypeScript suites and the Pi TUI smoke test cannot be run now; their last state was
  not run for this change.
- The site was built and opened locally, not deployed; `site.yml` remains parked.
