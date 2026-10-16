# The download site offers only the Windows app

**Date:** 2026-10-16
**Branch:** `worktree-site-windows-only`

## What and why

Step 5 of making this fork Windows-only. The download page offered three app
downloads — a macOS one for Apple silicon, a macOS one for Intel and a Windows
one — picked by the visitor's browser, plus a "Which Mac?" line explaining how
to tell the two Macs apart, and a JSON-LD description and an `llms.txt` that
both promised an app "for macOS and Windows". This fork ships one Windows
installer, so the page now offers that, and the Python-package route stays for
everyone else. A visitor who is not on Windows gets the Python package card
highlighted instead of a Mac download that would be wrong for them twice over.

## The change

- `site/strings.py` — `FILES` is the Windows installer alone; the eleven Mac
  keys (`cta_mac`, `cta_mac_x64`, `cta_mac_sub`, `cta_mac_x64_sub`, `which_mac`,
  `dl_mac_arm_os/for`, `dl_mac_x64_os/for`, `dl_mac_signed`, `dl_btn_dmg`) are
  deleted; `description` says "an app for Windows"; `app_meta` says "Windows 10
  and 11, 64-bit" where it said "macOS 12 or later". `cta_py`, `cta_py_sub` and
  every Python-package sentence stay.
- `site/template.html` — the two macOS cards and the `.which` line are gone; the
  hero CTA's static fallback (what a browser without JavaScript sees) is now the
  Windows download and the Windows label rather than the Apple-silicon one.
- `site/page.js` — the detection is `Windows NT ? 'win' : 'py'`; the Mac and
  Linux branches, the iPad check and the `navigator.userAgentData` architecture
  probe are gone, and `if (os) pick(os)` is `pick(os)` since `os` is never null.
- `site/build.py` — `cta()` keeps `win` and `py`; `body()`'s extras lose the two
  Mac URLs; `app_ld()`'s `operatingSystem` and `downloadUrl` are Windows-only;
  `llms()` drops the two Mac download bullets and the macOS line under
  "Systems"; the preview panel no longer counts "three download URLs".
- `site/build.py:322` (disclosed extra, see "Rejected / notes") — the build's own
  final self-check gained `encoding="utf-8"`.

## How it was verified

- **The site builds**: `python site/build.py` → `built: ['assets', 'index.html',
  'llms.txt', 'robots.txt', 'sitemap.xml', 'zh.html'] | unfilled: []`. That last
  field is the check that matters here: a `{{name}}` left in the output would
  print there. Independently, `grep -o '{{[A-Za-z0-9_]*}}'` over
  `site/dist/index.html`, `site/dist/zh.html` and `site/preview.html` finds
  nothing. A key deleted but still referenced would raise `KeyError` in `fill()`
  before the build finished; none did.
- `grep -I` over `site/dist/` for `dmg`, `mac-arm`, `mac-x64`, `macOS`,
  `Apple silicon`, `notariz`, `Intel` — no text hit. (A binary-inclusive grep
  matches nothing either; the only near-miss is the `-apple-system` font-family
  fallback in the inlined CSS, which is not download text.)
- Repo-wide grep for every deleted name (`cta_mac`, `which_mac`, `dl_mac_*`,
  `dl_btn_dmg`, `mac_arm`, `mac_x64`) — no hit outside `site/`, and none inside
  it either. Nothing outside `site/` consumes them.
- `python .claude/hooks/verify.py` — 85 tests, OK (6.0 s). There is no test for
  `site/`, so the suite proves only that nothing else broke.
- `textfold-verifier` on the diff: all four claims hold. It rebuilt the site
  itself, confirmed `page.js` can only ever ask for `'win'` or `'py'` and that
  both exist in every page's config, and confirmed the removed names are gone
  repo-wide.

## Not measured

- **Smoothness: unmeasured.** Nothing here is loaded by the Electron reader — the
  diff is static site files — but no measurement was taken, and
  `tools/zoombench.py` cannot run here (no `playwright`, no exported page).
- **The pages were not rendered in a browser.** The layout consequences below are
  read from the CSS and the built DOM, not seen.

## Rejected / notes

- **`site/style.css` was left alone, but it now has two problems the checklist
  does not cover**: `.cards` is still `repeat(3, minmax(0, 1fr))` while the row
  holds one card, so the Windows card renders about one third wide on a wide
  screen; and `.which`/`.which em` (line 99-100) now match no element — dead
  rules. Item 5's scope lists the template's cards, the strings, `page.js`'s
  detection and `build.py`'s `cta`/`app_ld`/`llms`; the stylesheet is not in it,
  and the right column count is a design choice. Flagged for the user rather than
  guessed at.
- **`site/assets/og.png` still shows the old hero CTA "Download for Mac / Apple
  silicon · .dmg"**, and it is the share image for `og:image`, `twitter:image`
  and the JSON-LD `image`/`screenshot`, so social previews and AI answers still
  advertise a Mac download. No item of the checklist names it, and it cannot be
  regenerated here — it is a screenshot of the running app. Flagged.
- **`site/build.py:9-10`'s docstring still says `python3 site/build.py`.** Item 6's
  `python3 → python` sweep lists README, CONTRIBUTING, `docs/DEVELOPMENT.md`,
  `textfold/__main__.py` and the UI JS, not this file; no item owns it. Every
  other `python3` in `site/` is the Python-package instruction the checklist
  explicitly says to keep.
- **The `encoding="utf-8"` on `site/build.py:322`** is the one line here that does
  not serve the download-page goal, and it is disclosed as such. Without it
  `python site/build.py` crashes on this machine with `UnicodeDecodeError: 'gbk'
  codec can't decode byte 0x80` — the check read the built Chinese page with the
  locale default (cp936). It is pre-existing (identical at `HEAD`, line 326) and
  every other `read_text` in the file already passed `encoding="utf-8"`. The
  item's own required verification is impossible without it, so it was fixed
  rather than reported.
- **Item 6 will make README say `python -m pip install textfold` where the site
  says `python3 -m pip install textfold`.** Item 5 keeps the site's Python text by
  instruction and item 6 changes only the README, so the two will differ. Flagged
  rather than pre-empted.
