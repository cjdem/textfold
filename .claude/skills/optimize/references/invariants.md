# What TextFold says about itself

Rules this project has already written down. Phase 5 walks this list and gives
each one an answer — holding, failing, or **not judgeable from here**. The third
answer is allowed and must be used honestly; there is no fourth.

## Parsed HTML passes through one sanitizing boundary

`textfold/semantic.py` normalizes parsed HTML as it comes in. Nothing renders
around it, and the parsers feed it rather than each other.

*Check:* `tests/test_parse_sanitize.py`, `tests/test_latexml_safe.py`. If the
change adds a parser or an input format, ask whether it goes through the same
door.

## A parser change renumbers atoms

`docs/DEVELOPMENT.md` warns: reading more of a page inserts atoms, and every
atom after them shifts. Layers generated before the change then describe the old
numbering.

*Check:* only when parsing changed. Say what happens to already-generated
papers — regenerated, mapped by content and order, or knowingly left stale.

## No page asks another server for anything

No font service, no CDN. Fonts and KaTeX live in `textfold/web/vendor/` and are
served from `/static/vendor/`.

*Check:* `grep -rn "https://" textfold/web/` for a new external fetch. A new
`vendor/` subdirectory is the pattern to follow, not an exception.

## Serif is the author's; sans is a summary

At every level the words that survive the next zoom-out are darker, and a level
change moves each surviving word to its new place rather than swapping the text.

*Check:* this is the reader's core promise. A change to rendering, levels or the
morph either preserves it or is a change to the product, not an optimization.

## No change may make the zoom less smooth

**This machine cannot check it.** `tools/zoombench.py` measures frames from a
real GPU at 2x pixels on Windows' Direct3D 11 backend (`--use-angle=d3d11`) —
but it needs `pip install playwright`, `playwright install chromium` and an
exported page under `out/compare/`, and none of the three is on this machine.

*Check:* if the change touches the reader, zoom or rendering, the honest answer
is **unmeasured**. Write that in the record. Never "no impact on performance" —
nobody measured one. Its numbers are Windows numbers: the Metal figures recorded
before this fork went Windows-only are a different set and cannot be compared
with them. Where the tool can run, `python tools/zoombench.py 2512.23916` is what
`CONTRIBUTING.md` asks for, with numbers before and after.

## Papers and keys stay out of commits

`papers/`, `out/`, `library.json` and `~/.textfold/` hold other people's papers
and this machine's keys. All are git-ignored.

*Check:* `git status --short` before committing shows only source you meant to
change.

## The suite needs nothing beyond the requirements

`python -m unittest discover tests` runs with `requirements.txt` alone and
touches none of your papers. `TEXTFOLD_NO_MODELS=1` makes a server find no model
at all, so nothing reaches out to one by accident — the gate script sets it.
A test that needs a model, the network, or a paper on disk is not one of these.

*Check:* the suite still runs green from a clean clone.

## Persistent writes have one writer at a time

A document's card, notes and folder can be written by a save, a generation
finishing, a PDF re-conversion and a move to the trash. They must be
serialized per document — the project uses a re-entrant lock in `store.py`
around the card write and the trash move, and `pdfdoc.py` holds it while a
re-converted folder is replaced.

*Check:* a change that writes `card.json`, `notes.json` or the document folder
has a test with two writers interleaving: a save during a candidate write, a
save during a re-conversion, a save crossing the move to the trash. Reading
the code is not the check; a green suite that never runs two writers has not
tested this.

## Text is UTF-8 in and out on a Chinese Windows

Files the reader writes are UTF-8; stored caches, layers and settings are
ASCII-escaped; model and subprocess pipes are UTF-8 in both directions. A GBK
console must not turn a Chinese title into a crash, on write or on read.

*Check:* if the change reads or writes text or runs a subprocess, run a
Chinese title and Chinese card or notes content through import, parse, save,
export and the static page build, and look for `UnicodeDecodeError` and
`UnicodeEncodeError`. A test that writes Chinese and reads it back is the
durable form.

## One change per branch

`CONTRIBUTING.md`: "One change per pull request: what it changes, why, and how
you checked it." A change that also fixes two other things cannot be verified
as one thing.

*Check:* read the diff and ask whether every line serves the stated goal. Lines
that do not are a second change wearing the first one's coat.
