# The public gallery and its asset pipeline are gone; the site is a download and usage page

**Date:** 2026-10-18
**Branch:** `worktree-site-compress`

## What and why

The public demo gallery and the machinery around it — a separate papers
repository, a proofreading and fixes flow, a static-site generator, README
screenshots and animations, and four recordings on the website — were a
marketing operation, not part of reading a paper. The confirmed product scope
keeps a simple download, install and usage page and drops the rest. The site
also carried a 1200×630 share image made before the fork went Windows-only: it
still said **Download for Mac · Apple silicon · .dmg**.

## The change

- Deleted the tools: `tools/gallery.py`, `tools/gallery.json`,
  `tools/requirements-gallery.txt` (the gallery's pikepdf dependency) and
  `tools/readme_assets.py`.
- Deleted the recordings' posters `docs/assets/{levels,pdf,notes,language,word}.jpg`
  and the stale share image `site/assets/og.png`.
- `site/build.py` — no `--gallery`, gallery copy or sitemap entries; no clip
  copying; the docstring describes the two pages and their assets only; the
  Open Graph and Twitter image metas and the JSON-LD `image`/`screenshot` are
  gone (no share image until a new one is made), and `twitter:card` is
  `summary`.
- `site/template.html` — no gallery link, demo video or "See it work" clips
  section; footer keeps README, format, PyPI, releases and GitHub.
- `site/strings.py`, `site/style.css`, `site/page.js` — the strings, styles and
  clip observer for those sections removed.
- `.github/workflows-disabled/site.yml` — one checkout and `python3
  site/build.py`; no gallery clone, no clip download, no `docs/assets/**`
  trigger. Still parked; `.github/workflows-disabled/README.md` no longer says
  the trigger includes `docs/assets/**`.
- `README.md`, `README.zh-CN.md` — the "Try the demo / 试用演示" link removed.
- `docs/DEVELOPMENT.md` — the gallery section, its pikepdf/proofreading notes,
  the gallery clause in the fonts paragraph and the `tools/readme_assets.py`
  module-map line removed.
- `pyproject.toml` — the PyPI project's `Gallery` URL pointed at the deleted
  `/gallery/` page; it is now `Website`, the site's root.
- The gallery's page mode went with it: `textfold/build.py` no longer takes
  `assets` or `pdf` (nothing but the deleted `tools/gallery.py` passed them),
  and `textfold/web/reader.js` no longer has the `pdfAt` branch that read a PDF
  and PDF.js from beside such a page. Saved whole-page HTML (`saved=`) and the
  app's own PDF pane are untouched.
- `docs/requirements/product-scope.md` — item 2 ticked.

## Decisions

- Remove the gallery rather than keep a static link: its papers, licenses and
  proofreading live in another repository and its own workflow, which is
  maintenance the reading product does not need.
- Keep a one-page site with download, install, the Python/CLI usage and the
  FAQ. The marketing sections (demo, recordings) go; the page still explains
  what the product is.
- Remove the stale share image instead of shipping a Mac claim. A new 1200×630
  image can be added later without restoring the pipeline.
- Remove the gallery's page support in the reader and builder rather than leave
  it dead: `pdfAt` could no longer be set by anything, and comments naming a
  gallery would outlive the feature.
- Point the PyPI project's website at the site root instead of keeping a
  `Gallery` entry that would answer 404.

## Rejected

- Keeping the gallery pipeline but hiding its links: the papers, licenses and
  proofreading still need maintenance.
- Keeping the recordings as posters only: that still needs the clip pipeline
  and the separate gallery repository's release.
- Deleting the site entirely: the download and install path is still needed.
- Keeping `assets/og.png` with text changed in the HTML: the image itself says
  Mac.

## What is lost

- The public demos, cross-paper examples, the gallery's proofreading and
  publishing flow, README screenshot and animation production, the site's four
  recordings, the PyPI project's Gallery link, and the social share image.
- The ability to generate gallery-style standalone pages that read a PDF and
  PDF.js from beside themselves. Pages already generated are unaffected: each
  carries its own copy of the reader and its deployed PDF and PDF.js, so its
  original-pages pane still works.

## How it was verified

- `python site/build.py` — built `index.html`, `zh.html`, `assets/`, `llms.txt`,
  `robots.txt`, `sitemap.xml`; **unfilled: []**.
- In the browser (static server on the built `site/dist`):
  - English page: title and H1 correct; no video; the download CTA, the
    pipeline/copy block, the Windows card and the five FAQ entries are present.
  - Chinese page (`zh.html`): title and H1 correct; `document.querySelectorAll('video').length`
    **0**, gallery links **0**, download CTA "下载 Windows 版", 5 FAQ entries.
- `node --check site/page.js`, `node --check site/ascii.js` — clean.
- `python .claude/hooks/verify.py` — **175 tests, OK** (7.0 s).
- `grep` for `gallery`, `readme_assets`, `site-clips`, `paperfold-gallery`,
  `pdfAt`, `og.png`, `og:image`, `twitter:image` and the removed site keys from
  the repository root (excluding `.git`, `vendor`, `docs/changes` history and
  the product-scope document) — only `textfold/wiki.py`'s `.gallery` remains,
  which is Wikipedia's own CSS class and unrelated.
- A verifier pass found the PyPI `Gallery` URL, the parked-workflow README's
  trigger line and the now-dead gallery page support (`assets`/`pdf` in
  `build.py`, `pdfAt` in `reader.js`); all three were fixed and the grep above
  re-run from the repository root, not only over docs, site and tools.
- A second pass corrected this record's claim about existing gallery pages
  (they embed their own reader, so they still work) and found the unused
  `assets` entry in `site/build.py`; both were fixed.

## Not measured

- The site was built and opened locally, not deployed; `site.yml` is parked.
- Search engines and AI crawlers were not run against the new `llms.txt`,
  `sitemap.xml` or the JSON-LD.
- There is no share image now; social cards show the title and description
  only.
- The browser pane was narrow, so the desktop nav layout (where the Download,
  Pipeline and Docs links are visible) was not separately checked.
- `reader.js` changed only by removing the `pdfAt` branch, which no page could
  set after the gallery tools were deleted; the branch was not exercised in a
  browser because nothing can reach it. Zoom smoothness stays unmeasured on
  this machine (no `playwright`, no exported comparison pages), and no claim is
  made that it is unaffected.
- The static and app pages are built in the suite (`test_cards`), but no app
  document was opened in a browser in this item.
