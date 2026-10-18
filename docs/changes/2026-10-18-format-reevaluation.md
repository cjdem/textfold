# EPUB, MHTML and OFD stay: a decision, with the evidence behind it

**Date:** 2026-10-18
**Branch:** `worktree-format-reeval` (at `f80969e`)

## What and why

Item 8 of the confirmed product scope: re-evaluate EPUB, MHTML and OFD, decide only, and do not
delete by default. The scope had kept OFD (a Chinese standard the engine already reads) and put
EPUB and MHTML in a second batch because TextFold also reads them with its own code, not only
through the engine. This entry records the re-evaluation and its outcome. No code changes.

## The change

- `docs/requirements/product-scope.md` — the EPUB/MHTML bullets in sections 2.5 and 4 and the
  second-batch note in section 5 now record the decision; item 8 is ticked, and so is item 6,
  whose subitems 6a–6e were already ticked.
- `docs/changes/2026-10-18-format-reevaluation.md` — this decision record.
- No source, test or format reader changed.

## What was weighed

- **OFD** — TextFold has no reader of its own for it. It is one entry in `engine.FILES`; the local
  MinerU engine reads it in its fast tier, and MinerU's cloud API does not read it
  (`API_FILES`). Removing it would remove the only way to import an OFD file, for users who have
  the local engine, and would save one dictionary entry.
- **EPUB** — `office.py::_epub` is 26 lines: `zipfile`, `posixpath`, shared OPF constants, and
  the same `Flow` walker the Word and HTML readers use. It is the no-install path for e-books:
  it runs when no local engine is installed (the cloud API does not read EPUB) and as the
  fallback when the engine fails on a file. `zotero.py::READS` maps `application/epub+zip`, so
  Zotero offers an EPUB attachment as one of the files TextFold reads. The README lists EPUB
  among the files the reader takes.
- **MHTML** — `office.py::_mhtml` is 15 lines: stdlib `email` for the MIME container, then the
  same `_page` used for HTML. `_page` needs `trafilatura`, which HTML import and web pages
  already require; neither EPUB nor MHTML adds a dependency. A saved web page is a documented
  input and the format a browser's own "Save page as" produces. Like EPUB, it is the no-engine
  path and the engine's fallback.
- **Existing documents** — a document already converted from one of these kinds is stored as
  source HTML and structured content (these kinds have no PDF). Deleting its self-reader would
  not break it, but on a machine without the local engine a re-import or a re-conversion would
  lose its reader. With the engine installed, the kept original can still be re-converted
  through the engine. The scope treats the no-engine compatibility as a reason not to delete by
  default.
- **Cost of keeping** — 41 lines together in a module that already reads Word, PowerPoint,
  Excel, CSV and HTML; no dependency of its own; the shared `Flow`/`_page` code is exercised by
  the other formats.
- **Test coverage today** — none drives the EPUB or MHTML readers directly.
  `tests/test_legacy_formats.py` only asserts that they are not refused. That is a real gap, and
  it is the main risk of keeping them.

## The decision

Keep all three.

- **OFD: keep.** It costs one name in the engine's format table, adds no code, and serves a
  Chinese-standard format on machines with the local engine. If the local engine is ever dropped
  as a whole, OFD goes with it — that would be an engine decision, not a format cleanup.
- **EPUB: keep.** 26 lines, no new dependency, works with nothing installed, and it is the path
  Zotero and the README promise. Removing it would save little and take away the no-install
  route to a documented input; the engine would still read EPUB where installed.
- **MHTML: keep.** 15 lines on top of the HTML reader TextFold keeps anyway, and saved web pages
  are a documented input. Removing it would not remove a dependency, but it would take the
  saved-page route away on machines without the engine.

The scope's "second batch" for EPUB and MHTML ends here with a decision to keep, not with a
deletion deferred again.

## When to revisit

Re-open this decision, and delete the format rather than keep patching it, if any of these holds:

- a real book or saved page fails and the fix needs a new dependency, or a rewrite larger than
  the reader itself;
- Zotero stops offering EPUB attachments, or the README stops listing the format, so the promise
  it backs disappears;
- the MIME or EPUB container parsing turns into a security liability that cannot be fixed
  cheaply (both parse untrusted files; `_xml` already refuses entities and network access);
- the shared `_page` path is removed or rewritten for HTML, leaving MHTML as a fork of it.

## Rejected

- **Deleting EPUB and MHTML now** — saves 41 lines, removes no dependency, and drops the
  no-engine routes for two documented inputs: Zotero EPUB attachments and saved web pages (the
  engine would still serve them where installed). The scope's default is not to delete.
- **Deleting OFD** — saves one dictionary entry and removes import for a Chinese-standard format
  the engine already reads.
- **Deleting all three to "simplify the format list"** — the list is shared with the engine and
  the landing page; the self-readers are small and the engine kinds cost no code.
- **Adding tests in this change** — the scope item is a decision, not a code change; the missing
  smoke tests are recorded here as the risk to weigh, not silently fixed in the same commit.

## How it was verified

- `python .claude/hooks/verify.py` — **189 tests, OK**; no test changed.
- A smoke test in a temporary folder, outside the repo, through `office.convert` (the
  self-reader directly; the engine installed on this machine is not in that path):
  - a minimal valid EPUB (container, OPF, one XHTML chapter, Chinese title and body) converted
    to 2 blocks carrying `第一章 阅读的顺序` and `这是电子书正文`;
  - a minimal MHTML (one related HTML part, Chinese title and body) converted to 2 blocks
    carrying `一篇保存下来的文章` and `网页正文在这里`;
  - both output `structured_content.json` read back as UTF-8 with the Chinese intact.
- `git diff --check` — clean.
- No reader code was touched. Zoom smoothness was **not measured** (no `playwright`, no
  `out/compare/` pages on this machine), and no claim is made about it.

## What is lost

Nothing. This entry deletes no format, no code and no data.

## Not measured

- **OFD end to end.** The local MinerU engine is installed on this machine (about 2.9 GB), but
  no OFD sample was available, so no OFD file was converted. The cloud API does not read OFD.
  The decision rests on the engine's format table and its documented fast-tier support, not on
  a converted file.
- **Real-world EPUBs and MHTMLs.** The smoke test uses minimal files without DRM, fonts,
  footnotes, multiple spine items or large embedded pictures; a real book's failure modes are
  not covered.
- **The Zotero EPUB path.** The mapping is read in `zotero.py`, not driven against a Zotero
  library.
- **The reader UI.** No reader code changed, so no browser check was run and the suite's lack of
  reader tests is unchanged.
