---
name: feature
description: Add a feature to TextFold through the same workflow as /optimize — a plan built from its requirements document, an isolated worktree, independent verification, both records, and a local merge. Use when the user asks for a new feature, points at a requirements document under docs/requirements/, or types /feature.
argument-hint: the requirements document, or the feature in one sentence
---

# Adding a feature

This is the **feature mode** of the change workflow. Read
`.claude/skills/optimize/SKILL.md` in full and follow it, with these
differences:

- Phase 0 states "feature mode" in your first reply and restates the goal as
  the acceptance criteria its requirements document (`docs/requirements/<name>.md`)
  states. If there is no requirements document, ask for one before planning.
- Phase 2's plan carries the feature-mode fields the skill lists: the data
  contract, the states and transitions, each failure path, every writer of
  shared state with its lock, and each acceptance item tagged `[test]`,
  `[manual]` or `[unmeasured]`.
- A feature and the tests, UI and docs that make it verifiable are one
  change. Say so in the record.

The plan gate and the independent verifier are not optional. If the
requirements document is larger than one change, say which slice is being
done now and which is left.
