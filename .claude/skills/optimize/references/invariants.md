# What TextFold says about itself

Rules this project has already written down. Phase 5 walks this list and gives
each one an answer — holding, failing, or **not judgeable from here**. The third
answer is allowed and must be used honestly; there is no fourth.

## The two fold engines stay identical

`plugins/pi-textfold/extension/fold.ts` and `plugins/textfold/hooks/fold.ts` are
kept byte-for-byte the same — the Pi extension and the Claude Code mod fold a
reply the same way or not at all.

*Check:* `python .claude/hooks/verify.py` runs `tests/test_pi_textfold_same_fold.py`,
which fails on any drift — this one is wired up, so use it.

The plugins' own TypeScript suites are **not** wired up here: neither has its
dependencies installed, and `plugins/textfold/` has no `package.json` at all
(its tests want `claude plugin test plugins/textfold`, Claude Code 2.1.287+).
If you changed a `.ts` file, say plainly that its suite did not run.

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
real GPU at 2x pixels and hardcodes `--use-angle=metal`, and `papers/` is empty —
it needs a Mac with `pip install playwright` and `playwright install chromium`.

*Check:* if the change touches the reader, zoom or rendering, the honest answer
is **unmeasured**. Write that in the record. Never "no impact on performance" —
nobody measured one. If you can, export on a Mac and run
`python tools/zoombench.py 2512.23916`, which is what `CONTRIBUTING.md` asks for
with numbers before and after.

## Papers and keys stay out of commits

`papers/`, `out/` and `~/.textfold/` hold other people's papers and this
machine's keys. All are git-ignored.

*Check:* `git status --short` before committing shows only source you meant to
change.

## The suite needs nothing beyond the requirements

`python -m unittest discover tests` runs with `requirements.txt` alone and
touches none of your papers. `TEXTFOLD_NO_MODELS=1` makes a server find no model
at all, so nothing reaches out to one by accident — the gate script sets it.
A test that needs a model, the network, or a paper on disk is not one of these.

*Check:* the suite still runs green from a clean clone.

## One change per branch

`CONTRIBUTING.md`: "One change per pull request: what it changes, why, and how
you checked it." An optimization that also fixes two other things cannot be
verified as one thing.

*Check:* read the diff and ask whether every line serves the stated goal. Lines
that do not are a second change wearing the first one's coat.
