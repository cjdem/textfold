# The committed record

Written to `docs/changes/YYYY-MM-DD-<slug>.md`, English, dated the day it was
written. This is what a reader has six months from now, when the branch, the
worktree and the conversation are all gone.

It is short on purpose. It is not the thinking — that is the local log. It is
the part that has to survive: what changed, why, and what backs it up.

Fill it from `git diff main...HEAD`, not from memory. Every number in it must
have come from a command that was actually run.

---

```markdown
# <what changed, as a noun phrase>

**Date:** YYYY-MM-DD
**Branch:** `<branch name>`

## What and why

Two or three sentences. What was wrong or slow or tangled, and what this does
about it. If the goal was not met, say so here rather than implying it was.

## The change

The files touched, and one line each on what happened to them. Enough that a
reader can go straight to the right place:

- `textfold/foo.py` — <what changed here>
- `tests/test_foo.py` — <what was added>

## Decisions

Product choices this change makes and why — the ones the diff cannot show:
why a draft waits as a candidate instead of overwriting, why a partial
generation becomes the current card, why a feature ships as one branch. One
line each. Delete the section when there are none beyond the obvious.

## Concurrency and locks

Which operations can interleave, what serializes them (a per-document lock, a
single writer, a transaction), and the regression test that runs two writers.
Delete the section when the change writes no shared state.

## How it was verified

The commands that were run, and what they said. Not "tests pass" — the actual
result:

- `python .claude/hooks/verify.py` — <the current count> tests, OK
- <any other check, and its outcome>

## Measured

Only what was actually measured, with the number and how it was obtained.
Delete this section entirely if nothing was measured — an empty table is a
claim in itself.

| | before | after |
|---|---|---|
| | | |

## Not measured

Anything the change could plausibly affect that nobody checked here, and why.
If the change touches the reader, this section says the smoothness rule was not
measured on this machine and why. **Do not leave this out because the answer is
uncomfortable.**

## Rejected

Approaches that were considered and dropped, and the reason. One line each.
This is the part a future reader is most often missing, and the cheapest to
write now.
```

---

Keep it under a page. Decisions and Concurrency are one or two lines each when
they apply; if the whole record does not fit, the thinking belongs in the local
log and this is carrying too much.
