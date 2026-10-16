# Changes

One file per optimization: what changed, why, and what backs it up.

These are written by the `/optimize` workflow in `.claude/skills/optimize/`,
which is where the template and the rules for filling it live. You do not need
to run that workflow to add one — a change made by hand deserves a record just
as much, and the format below is the whole of the requirement.

## Naming

`YYYY-MM-DD-<slug>.md`, slug in kebab-case: `2026-10-16-parse-without-lxml.md`.

The date, not a counter. A counter reads nicely in a single clone and collides
the first time two branches — or a fork and its upstream — both take the next
number. Dates do not collide, and they sort the same way.

An entry that turns out to be wrong is corrected or marked superseded, not
deleted. A record that quietly disappears is worse than one that was wrong.

## What goes in

Enough that a reader six months from now, with the branch deleted and the
conversation gone, can understand the change without re-deriving it:

- **What and why** — the problem, in two or three sentences.
- **The change** — the files touched, one line each.
- **How it was verified** — the commands actually run and what they said. Not
  "tests pass", but the numbers.
- **Measured** — only what was measured, with the number. Omit the section when
  nothing was.
- **Not measured** — what could plausibly be affected and was not checked. The
  smoothness rule needs `tools/zoombench.py` plus `playwright` and an exported
  comparison page, which this machine does not have; when a change touches the
  reader, that belongs here. Leaving this out because the answer is awkward is
  the one failure this directory exists to prevent.
- **Rejected** — what was tried and dropped, one line each. Cheapest to write
  now, most missed later.

Keep each entry under a page. The long version of the thinking belongs in the
author's own notes, not here.
