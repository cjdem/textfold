# How TextFold changes

This is the human-readable map. The detailed, agent-facing rules are in
[`.claude/skills/optimize/SKILL.md`](../.claude/skills/optimize/SKILL.md) and
its `/feature` entry point; `/upstream` is a separate read-only skill. When
this page and the skills disagree, the skills are the detailed ones.
`docs/DEVELOPMENT.md` remains the authority on how the project is built.

## One change at a time

`CONTRIBUTING.md` asks for one change per pull request. A branch that fixes a bug,
renames a module and updates the site cannot be verified as one thing. A small
fix the requester has already specified exactly may go straight to tests and a
commit; an upstream review with no port is the same kind of short docs change.
Every other change uses the workflow below.

## Intake

- **A feature** starts as `docs/requirements/<name>.md`: the problem, who it is
  for, acceptance items tagged `[test]`, `[manual]` or `[unmeasured]`,
  non-goals, and the data, format and documentation it touches. `/feature`
  refuses to plan without it.
- **A bug** starts with a reproduction: the input, the level, the language and
  what came out. The fix adds a regression test that fails before it.
- **An upstream change** starts with `/upstream`, which only reads the
  original repository. Its output is a decision record, not a merge.

## The phases

The numbers match the headings in the optimize skill.

0. **Frame** — one sentence on what changes and what "better" means, a clean
   `main`, the baseline test count, the version.
1. **Survey** — two or three read-only `textfold-scout` agents: the code path,
   the constraints, the alternatives. Collect a ranked list; do not invent
   candidates nobody investigated.
2. **Confirm** — the plan gate. The plan names the exact files, the documents
   it changes, how it will be verified, what could go wrong and what is out of
   scope. Feature mode adds the data contract, states and failure paths, every
   writer of shared state and its lock, and each acceptance item's tag. Nothing
   is changed and no worktree is created until the plan is approved.
3. **Isolate** — `EnterWorktree`, then prove the branch is cut from local
   `main` (`git merge-base --is-ancestor main HEAD`). The worktree has no
   `papers/`, `out/` or `.venv`; the test hook uses the main clone's
   environment.
4. **Implement** — the confirmed change only. Tests, UI and behaviour docs that
   make it verifiable are part of it. Do not commit yet.
5. **Verify** — the suite (`python .claude/hooks/verify.py`), two-writer tests
   for persistence, the independent `textfold-verifier`, every rule in
   `invariants.md`, a Chinese-text pass when text or pipes change, and the
   smoothness rule answered honestly: on this machine it is unmeasured.
6. **Record** — a committed English record in
   `docs/changes/YYYY-MM-DD-<slug>.md` and a detailed Chinese log in `notes/`
   (git-ignored). The record carries decisions, concurrency, verification
   numbers, what was measured, what was not, rejected approaches, the pitfalls
   and the documents checked. The local log carries the dead ends and the
   uncertainty. Copy the local log to the main checkout before removing the
   worktree.
7. **Merge** — commit, then `git merge --ff-only` into local `main`, remove the
   worktree and the branch, and run the suite once more on `main`.

## The documents to check

Every plan names the documentation it will change, or says "none" and why.
The checklist is in the optimize skill's Phase 2; the short version:

- `README.md` / `README.zh-CN.md` — what a reader is promised
- `docs/DEVELOPMENT.md` — layout, commands, constraints
- `docs/format.md`, `docs/notes-format.md`, `docs/reading-card-format.md` — formats
- `site/` — the download page, strings, version and build
- `pyproject.toml`, `requirements.txt` — dependencies, Python and platform
- `NOTICE`, `LICENSE`, `SECURITY.md` — attribution, licence, security
- `docs/requirements/<name>.md` — the acceptance criteria
- `docs/changes/YYYY-MM-DD-<slug>.md` — the record
- `CONTRIBUTING.md`, `docs/changes/README.md`, `docs/upstream/README.md` — contribution and record formats
- `desktop-mygo/README.md`, `.claude/agents/` — the desktop and the agent prompts
- `CLAUDE.md`, `.claude/skills/`, this page — when the process itself changes

A record's **Docs checked** section says what was updated and what was
deliberately left alone.

## The verifier and the merge

`textfold-verifier` is a separate, read-only agent. It runs the tests, reads
the acceptance tags, constructs interleavings for persistence changes, checks
`invariants.md`, reads the docs list, and after the record is written reads it
against the diff; it cannot edit the branch. Findings go back to phase 4. Only
after they are resolved and the record is written is the branch merged.

**Nothing is pushed by the workflow.** The local `main` is the hand-off point;
the human reviews and pushes on their own terms. A release tag and a push are
separate, deliberate actions.

## Upstream

`upstream` is `chenxiachan/textfold`, the original project. `/upstream` fetches
it, lists what is new, classifies each change, checks it against this fork's
divergences, and writes a dated review in `docs/upstream/`. A change worth
taking gets a port note and then goes through the normal phases in a worktree —
cherry-picked or reimplemented, never merged wholesale. The review record says
what was taken, what was skipped and why, even when nothing was taken.

A review with no port is a short docs change: the record, the tests and a
single-line commit, without the plan gate, worktree or independent verifier. A
port uses the full phases.

The fork's deliberate divergences: the Electron shell is gone, the desktop is
MyGo, PDFs and pictures go to MinerU's Cloud API only, the desktop and the
Python package are Windows-only, the Python package is installed from git, not
PyPI, and the site is this fork's. Upstream work in those areas is usually a
skip or a reimplementation.

## Small fixes

A one-line fix the requester has specified exactly needs the tests and the
commit, not the full workflow. If it fixes a bug, it still gets the regression
test. When in doubt, use the process; the plan gate is cheaper than undoing a
wrong change.

## Where to read more

- [`.claude/skills/optimize/SKILL.md`](../.claude/skills/optimize/SKILL.md) — the phases in full
- [`.claude/skills/feature/SKILL.md`](../.claude/skills/feature/SKILL.md) — feature mode
- [`.claude/skills/upstream/SKILL.md`](../.claude/skills/upstream/SKILL.md) — upstream review
- [`.claude/skills/optimize/references/invariants.md`](../.claude/skills/optimize/references/invariants.md) — the rules the verification walks
- [`docs/changes/README.md`](changes/README.md) — the record format
- [`docs/upstream/README.md`](upstream/README.md) — the upstream record format
- [`docs/requirements/`](requirements/) — examples of feature documents
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — one change at a time, tests, DCO
