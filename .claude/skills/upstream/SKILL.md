---
name: upstream
description: Review chenxiachan/textfold for changes worth porting into this fork, without merging upstream wholesale. Use when the user asks to check upstream, sync with the original project, or look for upstream features or fixes.
argument-hint: the upstream ref or period to review, if narrower than everything since the last review
---

# Reviewing upstream

The upstream is `chenxiachan/textfold`; this fork is `cjdem/textfold`. The two
have diverged on purpose. This workflow reads upstream and writes a decision
record. It does not merge, cherry-pick into `main`, or push.

Read `docs/upstream/README.md` for the record format and the list of
divergences to check every candidate against.

## 1 · Establish the range

Find the last review in `docs/upstream/` and the upstream commit it names. If
there is none, start from the fork point (`git merge-base main upstream/main`)
or the last upstream release; say which and why.

If the `upstream` remote is missing:

    git remote add upstream https://github.com/chenxiachan/textfold.git

Then:

    git fetch upstream --tags --prune
    git rev-parse upstream/main
    git log --oneline --no-merges <last-reviewed>..upstream/main

Name the upstream HEAD and the tag, if any, in the record.

## 2 · Survey the changes

Read the commit list, the upstream release notes and the issues or PRs the
commits name. For each candidate that could matter:

- what it changes, in one sentence;
- whether it is a security fix, a bug fix, a feature, a documentation change,
  or a change to something this fork has deliberately replaced;
- the files it touches (`git show --stat <sha>`);
- whether it depends on Electron, the local PDF engine, macOS, PyPI publishing,
  the original project's site, or another thing this fork replaced (MyGo, the
  Windows-only scope, MinerU's Cloud API).

Do not read every commit in full. Read the ones whose subject or files could
matter, and say in the record which ones were only skimmed.

## 3 · Decide

For each candidate, one of:

- **take** — the change applies almost unchanged. Name the commit SHA and the
  files it touches.
- **reimplement** — the behaviour is worth having, but the implementation
  assumes a divergence. Say what the behaviour is and what would have to change.
- **skip** — not worth it, or conflicts with the fork's scope. Give the reason.

A candidate that is not a security or correctness fix should be weighed against
`CONTRIBUTING.md`'s one-change-at-a-time rule and the fork's current priorities.

## 4 · Record

Write `docs/upstream/YYYY-MM-DD.md` using the format in
`docs/upstream/README.md`. Include the upstream HEAD, the range, every candidate
worth mentioning, the decision and the reason, and what was not reviewed. If
nothing is worth taking, say so plainly; that is a useful result.

The record is committed with the port if there is one; a review with no port is
a short docs change, with the tests and a single-line commit, without the plan
gate, worktree or independent verifier. Do not push.

## 5 · Port

A **take** or **reimplement** is not done here. It becomes a normal change:

- a **take** starts from the upstream commit, cherry-picked into a worktree,
  with the fork's tests and invariants applied;
- a **reimplement** starts with a requirements or port note that states the
  upstream behaviour, the fork's constraints and the acceptance items;
- either way, run the phases in `.claude/skills/optimize/SKILL.md`, including
  the plan gate, the independent verifier and the local merge;
- preserve the upstream copyright and attribution; the fork's `NOTICE` and the
  new record name the source commit.

Never merge `upstream/main` into this fork. The histories diverged on purpose,
and a wholesale merge would bring back the Electron shell, the local PDF engine
and the non-Windows assumptions this fork removed.
