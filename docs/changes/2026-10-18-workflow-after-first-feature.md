# The change workflow learns features, interleavings and Chinese text

**Date:** 2026-10-18

## What and why

The first feature to go through `/optimize` (the reading card) worked, but the
workflow around it was written for optimizations: Phase 0 asked what "better"
means, the record template had no place for product decisions or locks, and
the fixed test counts in the instructions went stale the moment the feature
landed. Its verifier also found three data-loss races that the 41 new tests did
not run, and the local `notes/` log had to be copied out of the worktree by
hand. This is the workflow catching up with what that run taught.

## The change

- `.claude/skills/optimize/SKILL.md` — two modes of one seven-phase workflow:
  **optimize** and **feature**. The first reply states the mode. Feature mode
  reads `docs/requirements/<name>.md` first and puts the data contract, states,
  failure paths, shared writers and locks, and `[test]` / `[manual]` /
  `[unmeasured]` acceptance tags in the plan. A feature and its tests, UI and
  docs are one change when they cannot be verified apart. Verification grew
  from five checks to seven: persistence/interleavings (a two-writer
  regression test, and the verifier asked to construct interleavings) and a
  Chinese-content pass (import, parse, save, export, static build; UTF-8 in,
  ASCII-escaped storage, UTF-8 pipes). Fixed test counts are gone. Phase 7
  copies the local log to the main checkout's `notes/` before the worktree is
  removed, and re-reads the project instructions afterwards.
- `.claude/skills/feature/SKILL.md` (new) — `/feature` enters the same workflow
  in feature mode. It points at the optimize skill rather than repeating the
  phases, so the two cannot drift apart.
- `.claude/skills/optimize/references/committed-record.md` — two optional
  sections, **Decisions** and **Concurrency and locks**, and the test count in
  the example is now a placeholder.
- `.claude/skills/optimize/references/local-log.md` — the same two sections,
  "<current count>" instead of 85, and the copy-out warning.
- `.claude/skills/optimize/references/invariants.md` — persistent writes have
  one writer at a time (the card, notes and document folder, including
  re-conversion and trash moves), and text is UTF-8 in and out on a Chinese
  Windows. `library.json` joins the ignored data.
- `.claude/agents/textfold-verifier.md` — reads acceptance tags; constructs
  interleavings for persistence changes; a persistence change without a
  two-writer test is a finding.
- `.claude/agents/textfold-scout.md` — maps the writers and the lock, not only
  the code path, and its description now covers features too.
- `CLAUDE.md` — the test count is gone (run for the current one), the section
  is **Changing TextFold**, and the short invariant list gains concurrency and
  UTF-8.
- `docs/requirements/research-reading-card.md` — the acceptance items carry
  `[test]` / `[manual]` / `[unmeasured]` as the example for future requirement
  documents; the UTF-8 constraint now names the Chinese-content pass, and
  smoothness is tagged `[unmeasured]`.
- `docs/changes/2026-10-18-reading-card.md` — backfilled with the **Decisions**
  and **Concurrency and locks** sections the run produced, so the first feature
  follows the template it helped write.

## Decisions

- One workflow with two modes, plus a thin `/feature` entry, rather than two
  copies of the seven phases. A duplicated phase list drifts the first time
  one copy is fixed.
- The plan gate and the independent verifier stay hard. The first feature's
  verifier found real data-loss paths that a green suite did not.
- A feature and the tests, UI and docs that make it verifiable are one change;
  splitting them would leave no way to verify the end-to-end behaviour.

## How it was verified

- `python .claude/hooks/verify.py` — **171 tests, OK** (7.08 s). No product
  code changed.
- `grep` over `CLAUDE.md` and `.claude/**/*.md` — no fixed test count remains.
- `git diff --check` — no whitespace errors.
- Read-through of the whole skill against the first feature's record: every
  plan field and check has a source in what that run actually had to reason
  about.

## Not measured

- The workflow itself has no test; its next real use is the check. The plans,
  records and verifier prompts are prose and were read, not executed.
- The `/feature` skill was not run end to end by this change.
- No product behaviour changed, so no smoothness claim arises from this diff.
