# The README and the homepage stop selling the command line and the agent interface

**Date:** 2026-10-18
**Branch:** `worktree-cli-agent-interface`

## What and why

Item 6c of the confirmed product scope. The README's "One fold, two places" and "For agents and
scripts" sections and the site's Pipeline card sold `textfold get` and the open format as an
interface for agents; the product's positioning is a reader for students reading papers and
project material. The command and `docs/format.md` stay — the desktop startup and the tests use
the CLI — but they are no longer part of the README's or the homepage's pitch.

## The change

- `README.md`, `README.zh-CN.md` — removed **One fold, two places** (both the read bullet and the
  workflow bullet), **For agents and scripts** (the `get` examples and the format explanation),
  the command-line export line in **Export**, and the October 9 "for agents" what's-new entry. The
  Python package line no longer says "for your own pipeline". The sources illustration and its
  two files (`docs/assets/sources.webp`, `sources-dark.webp`) are gone: it shows an **Agent**
  card, its generator was removed with the asset pipeline in item 2, and the two lines below it
  already list the sources in text. The zoom GIF stays.
- `site/template.html`, `site/strings.py`, `site/build.py` — the Pipeline card is now a Python
  install card (`pip install textfold`, `textfold serve`, the format link), and the nav's
  "Pipeline" is "Python" pointing at `#python` (the id was renamed from `#pipeline`). The FAQ
  entry "Can AI agents use it?" is gone, leaving four questions. The hero subtitle, the typed
  phrases, the description, the JSON-LD subcategory, feature list and keywords, and `llms.txt`
  (its opening, the "For AI agents" section, the agent link and the request that agents star the
  repository) now speak about papers and project material. The preview page's notes about what
  search engines and AI read were updated to match.
- `pyproject.toml` — the package summary no longer ends with "your agent's replies".
- `docs/requirements/product-scope.md` — item 6c ticked.

## Decisions

- Keep the Python install card instead of deleting the section: the Python package is still a
  supported way to run the reader, and a visitor on another system is pointed at it by the
  existing download logic. What goes is the `get`/agent pitch, not the installation.
- Remove the star request from `llms.txt` together with the agent section: a machine-facing
  instruction to star the repository does not belong on the reader's page.
- Remove the October 9 what's-new entry: it advertises the interface the page no longer shows,
  and its link would otherwise be dead.
- Keep `docs/format.md` and its links (README footer, site footer, Python card, the Docs list in
  `llms.txt`): the format and the CLI remain, as the scope requires.
- Rename the section id `#pipeline` to `#python` so no dead anchor remains, and update the
  non-Windows download button's target with it.
- Reword the positioning strings that named agent output (hero, typed line, description,
  JSON-LD, `llms.txt`) rather than leave the old agent framing on a page that no longer offers
  the agent interface.
- Remove the sources illustration rather than edit it: it carries an Agent card, there is no
  source file or generator left to edit it with, and the README lists the same sources in text
  directly below it.

## Rejected

- Deleting `textfold get` or `docs/format.md`: the scope keeps both; the desktop startup and the
  tests depend on the CLI.
- Removing the Python package from the site: it is an install path, not the agent interface.
- Keeping the star request without the agent section: it was addressed to agents.
- Rewriting the whole site's positioning beyond the strings that named the agent/CLI surface:
  that is a larger product decision than this item.

## What is lost

- The README and the homepage no longer tell a reader that `textfold get` exists or that an agent
  can drive it; discoverability of the CLI drops to the development docs and the format's own
  references.
- `llms.txt` no longer asks agents to star the repository, and no longer describes the CLI or the
  format as an agent interface; AI crawlers see the reader's description instead.
- The site FAQ loses the "Can AI agents use it?" answer.
- The READMEs lose the sources illustration; the sources themselves are still listed in the two
  lines under it.
- No capability, command, format, package or document is removed.

## How it was verified

- `python .claude/hooks/verify.py` — **188 tests, OK**; `git diff --check` is clean.
- `python site/build.py` — `built: ['assets', 'index.html', 'llms.txt', 'robots.txt',
  'sitemap.xml', 'zh.html'] | unfilled: []`.
- Both built pages, parsed: subcategory "Reader for research papers and project material",
  five feature-list entries, four FAQ questions, no "agent" in the keywords; `#python` present,
  no `pipeline`; no `textfold get`, "For agents" or "starred" anywhere in the built pages or
  `llms.txt`.
- An independent verifier read the diff and the built output, ran the tests and the build, and
  found that the sources illustration still carried an Agent card while the alt text no longer
  named it (the illustration and its two files are now removed), and that the new `llms.txt`
  opening repeated "free and open source" (the opening now says "a reader…", leaving the licence
  sentence once). Both fixed.
- In the preview browser at 1280×900: the English nav is Download · Python · Docs · GitHub · 中文,
  the Windows card is marked as this computer with the installer button, the Python card shows
  the two commands and the format link, and there are four questions. The Chinese page shows
  下载 · Python · 文档, four questions, Chinese card and CTA text, and its embedded non-Windows
  button points at `#python`. No agent mentions on either page.
- The Chinese strings are UTF-8 in `strings.py`, were written UTF-8 by the build, and rendered in
  the browser as written.
- Zoom smoothness: **not measured** (no `playwright`, no `out/compare/` pages on this machine).
  No reader or renderer file is touched, and no claim is made about it.

## Invariants

- **Parsed HTML through `textfold/semantic.py`:** not applicable; no parser or renderer change.
- **Parser change renumbers atoms:** not applicable.
- **Persistent writes serialized per document:** no writer added or changed.
- **UTF-8 on a Chinese Windows:** the new Chinese strings are UTF-8 and the site build writes
  UTF-8; the browser check rendered them correctly. No new file or subprocess encoding path.
- **No new dependencies:** none.

## Not measured

- The site was checked at 1280×900 only; phone widths rely on the existing media query (the nav's
  option links hide under 620 px, unchanged).
- External links (GitHub, PyPI, releases) were not followed; the removed links are the ones that
  pointed at the removed sections, and the remaining targets are unchanged.
- No automated test covers the site's copy or `llms.txt`: the suite is Python and does not build
  or parse the site, so a future edit could reintroduce an agent pitch with the suite green.
