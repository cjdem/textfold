# The fork says whose work it is, and points at itself

- Date: 2026-10-21.
- Mode: housekeeping after the MyGo migration; the branch was merged into
  `main` (fast-forward, not pushed).
- Decision: keep the upstream attribution where Apache 2.0 requires it, and
  move every project link to this fork or to a relative path.

## What changed

- `main` now carries the MyGo migration: the MyGo desktop shell, the signed
  update feed, the removal of `desktop/`, and the MinerU Cloud API-only PDF
  path.
- `NOTICE` keeps its original text and adds: this is a modified fork of
  `chenxiachan/textfold`, originally by Xia Chen, maintained by cjdem, not
  affiliated or endorsed; the changes in this fork; `Fork changes Copyright
  2026 cjdem`; and MyGo's MIT license. The original upstream URL stays, as
  Apache 2.0 §4(d) requires.
- `README.md` and `README.zh-CN.md` open with a short fork statement that
  names the original author and links to the local `NOTICE`; every project
  link now points at `cjdem/textfold` or a relative path. The Python install
  is `pip install git+https://github.com/cjdem/textfold`, not the upstream
  PyPI name.
- The site (`site/strings.py`, `site/build.py`) uses
  `https://cjdem.github.io/textfold/`, `cjdem/textfold` for its repo and
  release links, and a footer that names both the original copyright and the
  fork. Its JSON-LD says cjdem is the author, Xia Chen a contributor, and
  drops the upstream PyPI link.
- `pyproject.toml` points Homepage, Website and Issues at the fork and lists
  both authors. The distribution name stays `textfold` so imports do not
  change; it is not to be published under that name on PyPI, and the PyPI
  workflow stays parked.
- The app metadata follows: `mygo.json` identifies as
  `io.github.cjdem.textfold`, the Go module path is
  `github.com/cjdem/textfold/desktop-mygo`, and the Help menu opens the fork.
  The reader, the settings star link, the User-Agent, the notes format and
  `CONTRIBUTING.md` use the fork too.
- `LICENSE` and `NOTICE` are copied to `desktop-mygo/resources/LICENSE.txt`
  and `NOTICE.txt`, so the installer carries them. A Go test fails if the
  copies drift from the repository's files.
- `SECURITY.md` now describes MinerU Cloud API conversion instead of the
  removed local PDF engine. The README and site say WebView2 is part of
  Windows 11 and may be needed on Windows 10.

## What stays

- `LICENSE` unchanged; the original `NOTICE` text and copyright retained.
- Historical `docs/changes/` records, the original contributors' credits and
  the third-party dependency links.
- `CLAUDE.md`'s note that this checkout is a fork of `chenxiachan/textfold`
  is internal guidance, not a project link.

## Verification

- `grep -rn chenxiachan` leaves only `NOTICE`, its copy next to the app, the
  historical change records and `CLAUDE.md`.
- `python site/build.py`: built; the generated pages contain no upstream URL.
- `go test ./...` and `go vet ./...`: passed after the module path change.
- `python -m unittest discover tests`: 195 passed.
- Payload rebuilt from the cached CPython archive; `smoke.py` served
  `/api/models`; `go tool mygo build` with the signing key produced the
  installer and the signed update manifest, and the install folder has
  `LICENSE.txt` and `NOTICE.txt`.
- The packaged app started with a disposable `TEXTFOLD_DATA`, answered
  `/api/models`, and left no Python process after it was closed.

## Not done

- Nothing was pushed; the site is not deployed; the first MyGo release, its
  signing secret and GitHub Pages remain release work.
- No legal review. The NOTICE/README notices follow a common Apache 2.0
  reading; a broad public distribution may want a lawyer's check.
- `NOTICE` is the only place an upstream URL remains. If a stricter reading
  of §4(b) is wanted, per-file change notices can be added later.
