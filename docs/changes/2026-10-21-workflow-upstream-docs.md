# The change workflow gains upstream reviews, a docs check and pitfalls

**Date:** 2026-10-21
**Branch:** `worktree-workflow-upstream-docs`

## What and why

The workflow already covered a plan gate, a worktree, independent verification
and a local merge. It had no process for the original project: upstream could
change without anyone deciding whether a change was worth porting. Plans named
code files but not the documents a reader would see, and the committed record
had no place for the traps that cost the next change time. This adds an
upstream review skill and record format, a docs-impact checklist in the plan
and the record, and a Pitfalls section, with `docs/WORKFLOW.md` as the
human-readable map. It also brings the hand-written record format in line and
removes a stale `pyproject`-marker note from `CLAUDE.md`.

## The change

- `.claude/skills/optimize/SKILL.md` — the docs checklist and the bug
  regression-test line in Phase 2; the phase-count wording in the
  introduction; the verifier checks the documentation in Phase 5 and the
  written record in Phase 6; Pitfalls and Docs checked in Phase 6.
- `.claude/skills/feature/SKILL.md` — the description points at the same
  workflow without the "seven-phase" count.
- `.claude/skills/optimize/references/committed-record.md` — Docs checked and
  Pitfalls sections.
- `.claude/skills/upstream/SKILL.md` — a new read-only upstream review.
- `docs/upstream/README.md` — the record format, the fork's divergences and the
  review cadence.
- `docs/changes/README.md` — the hand-written record format gains Docs checked
  and Pitfalls, and points at the template.
- `docs/WORKFLOW.md` — the human-readable map.
- `CLAUDE.md` — links the map and `/upstream`, makes "do not push unless the
  user asks" a project rule, and removes the stale `sys_platform`-marker note
  (the markers went with the local engine).
- `CONTRIBUTING.md` — links the workflow.
- `docs/changes/2026-10-21-workflow-upstream-docs.md` — this record.

## Docs checked

- `README.md` / `README.zh-CN.md` — not needed; no user-facing behaviour or
  platform change.
- `docs/DEVELOPMENT.md` — not needed; the layout and constraints are unchanged.
- `site/` — not needed; no site text or build change.
- `pyproject.toml` / `requirements.txt` — not needed; no dependency or platform
  change.
- `NOTICE`, `LICENSE`, `SECURITY.md` — not needed; no attribution or security
  change.
- `CONTRIBUTING.md` — updated; links the workflow.
- `docs/changes/README.md` — updated; the hand-written record format.
- `docs/upstream/README.md` — added; the upstream record format.
- `desktop-mygo/README.md`, `.claude/agents/` — not needed; no desktop or
  agent prompt change.
- `CLAUDE.md`, `.claude/skills/`, `docs/WORKFLOW.md` — updated; this is the
  change.

## Decisions

- Upstream review is a separate read-only skill, not a third mode of
  `/optimize`: a port starts the normal workflow only after the review records
  a candidate worth taking.
- The docs checklist is in the plan, not only in the record; naming the
  documents after the code is written is too late to catch a stale promise.
- Pitfalls live in the committed record because the detailed local log is
  git-ignored and does not reach the next contributor.

## How it was verified

- `python .claude/hooks/verify.py` — 195 tests, OK.
- `git diff --check` — no whitespace errors.
- Read-through of the new skill against `docs/upstream/README.md` and the
  phases; every referenced path exists.
- An independent `textfold-verifier` read the draft; its findings were fixed
  before the commit.

## Not measured

- The workflow is prose and has no test; its next real use is the check. The
  `/upstream` skill was not run against the live upstream in this change.
- No product code, reader, zoom or rendering changed, so no smoothness claim
  arises.

## Pitfalls

- The phase count drifts easily. The skill now says "the phases are numbered
  0–7" and `docs/WORKFLOW.md` gives no count; keep it that way rather than
  reintroducing "seven phases".
- The hand-written format in `docs/changes/README.md` can lag the template.
  When a record section is added, update the README the same day; a
  hand-written record that follows the old format omits the new sections.
- A docs checklist can become a ritual. "None, because ..." is the expected
  answer when true; the record should not turn it into an empty section.
- Upstream has diverged on purpose. A commit that looks generally useful can
  still assume Electron, the local PDF engine, macOS, PyPI or the original
  site; check the divergence list before recommending a port.

## Rejected

- Folding upstream review into `/optimize` as a third mode — the survey and
  plan phases would run before anyone knew whether a candidate was worth it.
- Putting pitfalls only in the local `notes/` log — it is git-ignored, so the
  next contributor would not see them.
- A `docs/WORKFLOW.md` that repeats the skill — it is a map with links, not a
  second copy of the phases.
